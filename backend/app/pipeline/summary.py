"""Post-loop executive commentary for management reports."""

from __future__ import annotations

import json
from typing import Any

from app.models import ExecutiveSummary, InsightsRollup, VerbatimAnalysis
from app.shared_services.llm import analyze_with_llm

SUMMARY_SYSTEM = """You are a senior CX / CVM analyst writing for bank or telecom leadership.
Produce a professional management briefing from structured verbatim insights.
Do NOT invent metrics — use only the provided counts and percentages.
Do NOT dump raw theme lists; synthesize, prioritize, and comment on business impact.
Tone: clear, board-ready, decisive. Avoid hype and filler.
Return JSON matching the schema exactly.
"""


def build_summary_context(
    rollup: InsightsRollup,
    records: list[VerbatimAnalysis],
    *,
    max_items: int = 1000,
) -> dict[str, Any]:
    analyzed = [r for r in records if not r.skipped][:max_items]
    slim = []
    for r in analyzed:
        slim.append(
            {
                "sentiment": r.sentiment.value if r.sentiment else None,
                "emotion": r.emotion.value if r.emotion else None,
                "nps_class": r.nps_class.value if r.nps_class else None,
                "churn_risk": r.churn_risk.value if r.churn_risk else None,
                "themes": r.themes[:5],
                "issues": r.issues[:4],
                "delights": r.delights[:4],
                "summary": (r.summary or "")[:180],
                "quote": (r.key_quote or "")[:140],
            }
        )

    return {
        "totals": {
            "total": rollup.total,
            "analyzed": rollup.analyzed,
            "skipped": rollup.skipped,
        },
        "metrics": rollup.metrics.model_dump(),
        "sentiment_counts": rollup.sentiment,
        "nps_class_counts": rollup.nps_class,
        "churn_counts": rollup.churn_risk,
        "top_themes": [t.model_dump() for t in rollup.top_themes],
        "top_issues": [t.model_dump() for t in rollup.top_issues],
        "top_delights": [t.model_dump() for t in rollup.top_delights],
        "competitor_switch_count": rollup.competitor_switch_count,
        "mixed_sentiment_count": rollup.mixed_sentiment_count,
        "deep_dive": rollup.deep_dive.model_dump() if rollup.deep_dive else None,
        "verbatim_signals": slim,
    }


def generate_executive_summary(
    rollup: InsightsRollup,
    records: list[VerbatimAnalysis],
) -> ExecutiveSummary:
    context = build_summary_context(rollup, records)
    user_prompt = f"""Write an executive CX insights report from this structured data.

Return JSON with keys:
- title (string)
- executive_overview (string, 2-4 short paragraphs)
- key_findings (array of 5-8 strings)
- priority_issues (array of strings — each issue + why it matters)
- strengths_to_protect (array of strings)
- recommended_actions (array of strings — concrete, owner-ready)
- risk_commentary (string)
- closing_note (string)

DATA:
{json.dumps(context, ensure_ascii=False)}

If deep_dive is present, weave its strongest insights into findings/actions — do not ignore extra-column signals.
"""
    payload = analyze_with_llm(
        text="executive-summary",
        system_prompt=SUMMARY_SYSTEM,
        user_prompt=user_prompt,
    )
    return ExecutiveSummary(
        title=str(payload.get("title") or "Customer verbatim insights report"),
        executive_overview=str(payload.get("executive_overview") or ""),
        key_findings=list(payload.get("key_findings") or []),
        priority_issues=list(payload.get("priority_issues") or []),
        strengths_to_protect=list(payload.get("strengths_to_protect") or []),
        recommended_actions=list(payload.get("recommended_actions") or []),
        risk_commentary=str(payload.get("risk_commentary") or ""),
        closing_note=str(payload.get("closing_note") or ""),
    )
