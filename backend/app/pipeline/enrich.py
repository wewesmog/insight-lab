"""Opportunistic deep-dive: profile extra CSV columns, segment, LLM commentary."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any, Literal

from app.models import (
    ColumnProfile,
    DeepDiveInsight,
    DeepDiveReport,
    InsightsRollup,
    SegmentStat,
    SuggestedAnalysis,
    ThemeCount,
    VerbatimAnalysis,
    VerbatimRow,
)
from app.shared_services.llm import analyze_with_llm

ENRICH_SYSTEM = """You are a senior CX / CVM data analyst.
You receive: (1) core verbatim rollups, (2) profiles of EXTRA CSV columns the standard
pipeline does not always use, (3) deterministic segment stats when available.

Your job:
- Interpret what each extra column likely means in a CX context.
- Surface non-obvious findings from segment cuts (channel, product, region, tenure, etc.).
- Propose further analyses that were NOT run this time — only when they would add value
  given the available columns. Do not invent columns that do not exist.
- Prefer concrete, management-useful language. Do not restate the whole rollup.

Return JSON matching the schema exactly.
"""


def _is_numeric(values: list[str]) -> bool:
    ok = 0
    for v in values:
        try:
            float(v.replace(",", ""))
            ok += 1
        except ValueError:
            pass
    return ok >= max(1, int(0.8 * len(values)))


def _looks_datetime(values: list[str]) -> bool:
    pattern = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
    hits = sum(1 for v in values if pattern.search(v))
    return hits >= max(1, int(0.6 * len(values)))


def profile_extra_columns(verbatims: list[VerbatimRow]) -> list[ColumnProfile]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for row in verbatims:
        for key, value in (row.extras or {}).items():
            text = (value or "").strip()
            if text:
                buckets[key].append(text)

    profiles: list[ColumnProfile] = []
    for name, values in sorted(buckets.items()):
        unique = Counter(values)
        kind: Literal["categorical", "numeric", "datetime", "text", "sparse"]
        if len(values) < 3:
            kind = "sparse"
        elif _is_numeric(values):
            kind = "numeric"
        elif _looks_datetime(values):
            kind = "datetime"
        elif len(unique) <= min(25, max(2, len(values) // 2)):
            kind = "categorical"
        else:
            kind = "text"

        top = [
            ThemeCount(theme=val, count=count)
            for val, count in unique.most_common(8)
        ]
        profiles.append(
            ColumnProfile(
                name=name,
                kind=kind,
                non_null=len(values),
                unique_count=len(unique),
                top_values=top,
            )
        )
    return profiles


def build_segment_stats(
    verbatims: list[VerbatimRow],
    records: list[VerbatimAnalysis],
    profiles: list[ColumnProfile],
    *,
    max_segments_per_col: int = 8,
) -> list[SegmentStat]:
    by_id = {r.verbatim_id: r for r in records if not r.skipped}
    stats: list[SegmentStat] = []

    for profile in profiles:
        if profile.kind not in {"categorical", "numeric"}:
            continue
        if profile.unique_count < 2 or profile.unique_count > 20:
            continue

        groups: dict[str, list[VerbatimAnalysis]] = defaultdict(list)
        for row in verbatims:
            raw = (row.extras or {}).get(profile.name, "").strip()
            if not raw:
                continue
            rec = by_id.get(row.id)
            if rec is None:
                continue
            groups[raw].append(rec)

        ranked = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
        for value, group in ranked[:max_segments_per_col]:
            if len(group) < 2:
                continue
            n = len(group)
            neg = sum(1 for g in group if g.sentiment and g.sentiment.value == "negative")
            high = sum(1 for g in group if g.churn_risk and g.churn_risk.value == "high")
            prom = sum(1 for g in group if g.nps_class and g.nps_class.value == "promoter")
            stats.append(
                SegmentStat(
                    column=profile.name,
                    value=value,
                    count=n,
                    negative_pct=round(100.0 * neg / n, 1),
                    high_churn_pct=round(100.0 * high / n, 1),
                    promoter_pct=round(100.0 * prom / n, 1),
                )
            )
    return stats


def _sample_extras_rows(verbatims: list[VerbatimRow], limit: int = 40) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in verbatims:
        if not row.extras:
            continue
        out.append(
            {
                "excerpt": row.text[:120],
                "extras": row.extras,
            }
        )
        if len(out) >= limit:
            break
    return out


def generate_deep_dive(
    *,
    rollup: InsightsRollup,
    verbatims: list[VerbatimRow],
    records: list[VerbatimAnalysis],
) -> DeepDiveReport:
    profiles = profile_extra_columns(verbatims)
    segments = build_segment_stats(verbatims, records, profiles)
    analyses_run = ["column_profiling"]
    if segments:
        analyses_run.append("segment_cross_tabs")

    available = sorted({k for row in verbatims for k in (row.extras or {})})

    if not available and not segments:
        # Still ask LLM for opportunistic suggestions from core data alone
        context = {
            "available_extra_columns": [],
            "note": "No extra CSV columns were present. Suggest only analyses that use core fields.",
            "metrics": rollup.metrics.model_dump(),
            "top_themes": [t.model_dump() for t in rollup.top_themes[:8]],
            "top_issues": [t.model_dump() for t in rollup.top_issues[:8]],
        }
    else:
        context = {
            "available_extra_columns": available,
            "column_profiles": [p.model_dump() for p in profiles],
            "segment_stats": [s.model_dump() for s in segments],
            "sample_rows_with_extras": _sample_extras_rows(verbatims),
            "core_metrics": rollup.metrics.model_dump(),
            "top_issues": [t.model_dump() for t in rollup.top_themes[:6]],
            "churn_mix": rollup.churn_risk,
            "sentiment_mix": rollup.sentiment,
        }
        analyses_run.append("llm_column_interpretation")

    user_prompt = f"""Analyze this CX dataset enrichment context.

Return JSON with keys:
- column_interpretations: array of {{name, interpretation}} for each extra column (empty if none)
- insights: array of {{headline, detail, evidence, severity}} where severity is info|watch|urgent
  Focus on findings enabled by EXTRA columns / segments. Max 6.
- suggested_analyses: array of {{title, rationale, method, priority, requires_columns}}
  These are analyses NOT run this pass — prioritize ones that would unlock more value.
  Max 5. priority is high|medium|low.
- narrative: 1-2 short paragraphs for the report's "Contextual deep dive" section.

CONTEXT:
{json.dumps(context, ensure_ascii=False)}
"""

    try:
        payload = analyze_with_llm(
            text="deep-dive-enrichment",
            system_prompt=ENRICH_SYSTEM,
            user_prompt=user_prompt,
        )
    except Exception:
        return DeepDiveReport(
            available_columns=available,
            column_profiles=profiles,
            segment_stats=segments,
            analyses_run=analyses_run,
            narrative="Deep-dive commentary unavailable for this run; segment tables below are still computed in code.",
        )

    interp_map = {
        str(item.get("name")): str(item.get("interpretation") or "")
        for item in (payload.get("column_interpretations") or [])
        if isinstance(item, dict) and item.get("name")
    }
    for profile in profiles:
        if profile.name in interp_map:
            profile.interpretation = interp_map[profile.name]

    insights: list[DeepDiveInsight] = []
    for item in payload.get("insights") or []:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity") or "info"
        if severity not in {"info", "watch", "urgent"}:
            severity = "info"
        insights.append(
            DeepDiveInsight(
                headline=str(item.get("headline") or "Insight"),
                detail=str(item.get("detail") or ""),
                evidence=(str(item["evidence"]) if item.get("evidence") else None),
                severity=severity,  # type: ignore[arg-type]
            )
        )

    suggestions: list[SuggestedAnalysis] = []
    for item in payload.get("suggested_analyses") or []:
        if not isinstance(item, dict):
            continue
        priority = item.get("priority") or "medium"
        if priority not in {"high", "medium", "low"}:
            priority = "medium"
        suggestions.append(
            SuggestedAnalysis(
                title=str(item.get("title") or "Suggested analysis"),
                rationale=str(item.get("rationale") or ""),
                method=str(item.get("method") or ""),
                priority=priority,  # type: ignore[arg-type]
                requires_columns=list(item.get("requires_columns") or []),
            )
        )

    return DeepDiveReport(
        available_columns=available,
        column_profiles=profiles,
        segment_stats=segments,
        insights=insights,
        suggested_analyses=suggestions,
        narrative=str(payload.get("narrative") or ""),
        analyses_run=analyses_run,
    )
