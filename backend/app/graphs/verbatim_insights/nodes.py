"""LangGraph nodes for verbatim insights analysis."""

from __future__ import annotations

import uuid
from typing import Literal

from app.graphs.verbatim_insights.state import InsightsGraphState
from app.models import (
    ChurnRisk,
    Emotion,
    NpsClass,
    RunStats,
    Sentiment,
    VerbatimAnalysis,
    VerbatimRow,
)
from app.pipeline.rollup import build_rollup
from app.pipeline.skip import should_skip
from app.pipeline.summary import generate_executive_summary
from app.prompts.extract import EXTRACT_SYSTEM, build_extract_user
from app.shared_services.llm import analyze_with_llm, get_model


def _verbatim_map(state: InsightsGraphState) -> dict[str, VerbatimRow]:
    out: dict[str, VerbatimRow] = {}
    for raw in state.get("verbatims", []):
        row = raw if isinstance(raw, VerbatimRow) else VerbatimRow.model_validate(raw)
        out[row.id] = row
    return out


def build_initial_state(
    *,
    dataset_id: str,
    verbatims: list[VerbatimRow],
    run_id: str | None = None,
    analysis_id: str | None = None,
) -> InsightsGraphState:
    return InsightsGraphState(
        run_id=run_id or str(uuid.uuid4()),
        dataset_id=dataset_id,
        analysis_id=analysis_id,
        status="pending",
        engine=get_model(),
        verbatims=verbatims,
        pending_ids=[],
        records=[],
        errors=[],
        stats=RunStats(),
        rollup=None,
    )


def prepare(state: InsightsGraphState) -> dict:
    """Batch node: seed the work queue from uploaded verbatims."""
    verbatims = [
        row if isinstance(row, VerbatimRow) else VerbatimRow.model_validate(row)
        for row in state.get("verbatims", [])
    ]
    return {
        "status": "running",
        "pending_ids": [row.id for row in verbatims],
        "verbatims": verbatims,
        "records": [],
        "errors": [],
        "stats": RunStats(),
    }


def analyze_one(state: InsightsGraphState) -> dict:
    """Per-verbatim node: skip gate → LLM extract."""
    pending = list(state.get("pending_ids", []))
    if not pending:
        return {}

    verbatim_id = pending[0]
    remaining = pending[1:]
    row = _verbatim_map(state).get(verbatim_id)
    total = len(state.get("verbatims", []))
    done = total - len(remaining)

    analysis_id = state.get("analysis_id")
    if analysis_id:
        from app import store

        store.bump_analysis_progress(analysis_id, done)

    if row is None:
        return {
            "pending_ids": remaining,
            "current_verbatim_id": verbatim_id,
            "errors": [
                {
                    "verbatim_id": verbatim_id,
                    "node": "analyze_one",
                    "message": "verbatim not found in state",
                }
            ],
        }

    skip = should_skip(row.text)
    if skip is not None:
        record = VerbatimAnalysis(
            verbatim_id=row.id,
            text=row.text,
            skipped=True,
            skip_reason=skip,
            engine=get_model(),
        )
        return {
            "pending_ids": remaining,
            "current_verbatim_id": verbatim_id,
            "records": [record],
            "stats": RunStats(skipped=1),
        }

    record = _extract_with_llm(row)
    return {
        "pending_ids": remaining,
        "current_verbatim_id": verbatim_id,
        "records": [record],
        "stats": RunStats(llm_calls=1),
    }


def _extract_with_llm(row: VerbatimRow) -> VerbatimAnalysis:
    payload = analyze_with_llm(
        text=row.text,
        system_prompt=EXTRACT_SYSTEM,
        user_prompt=build_extract_user(text=row.text),
    )

    return VerbatimAnalysis(
        verbatim_id=row.id,
        text=row.text,
        sentiment=Sentiment(payload.get("sentiment", "neutral")),
        emotion=Emotion(payload.get("emotion", "neutral")),
        nps_class=NpsClass(payload.get("nps_class", "passive")),
        churn_risk=ChurnRisk(payload.get("churn_risk", "low")),
        themes=list(payload.get("themes") or []),
        issues=list(payload.get("issues") or []),
        delights=list(payload.get("delights") or []),
        summary=payload.get("summary"),
        key_quote=payload.get("key_quote"),
        engine=get_model(),
    )


def route_after_analyze(state: InsightsGraphState) -> Literal["analyze_one", "rollup_batch"]:
    if state.get("pending_ids"):
        return "analyze_one"
    return "rollup_batch"


def rollup_batch(state: InsightsGraphState) -> dict:
    """Deterministic countable KPIs from structured per-verbatim records."""
    records = list(state.get("records", []))
    dataset_id = state.get("dataset_id", "")
    rollup = build_rollup(dataset_id, records)
    # If everything was skipped, this is the last node — mark complete here.
    if not any(not r.skipped for r in records):
        return {"rollup": rollup, "status": "completed"}
    return {"rollup": rollup}


def _has_extra_columns(state: InsightsGraphState) -> bool:
    for raw in state.get("verbatims", []):
        extras = raw.extras if isinstance(raw, VerbatimRow) else (raw.get("extras") or {})
        if extras:
            return True
    return False


def route_after_rollup(
    state: InsightsGraphState,
) -> Literal["enrich_batch", "summarize_batch", "end"]:
    """After KPIs: enrich only if extras exist; else summarize; all-skipped → end."""
    if not any(not record.skipped for record in state.get("records", [])):
        return "end"
    if _has_extra_columns(state):
        return "enrich_batch"
    return "summarize_batch"


def enrich_batch(state: InsightsGraphState) -> dict:
    """Read extra CSV columns, run opportunistic segment cuts, LLM deep-dive."""
    from app.pipeline.enrich import generate_deep_dive

    records = state.get("records", [])
    verbatims = state.get("verbatims", [])
    rollup = state.get("rollup")
    if rollup is None:
        return {}

    try:
        deep_dive = generate_deep_dive(
            rollup=rollup,
            verbatims=verbatims,
            records=records,
        )
        rollup.deep_dive = deep_dive
        return {
            "rollup": rollup,
            "stats": RunStats(llm_calls=1),
        }
    except Exception as exc:
        return {
            "rollup": rollup,
            "errors": [
                {
                    "node": "enrich_batch",
                    "message": str(exc),
                }
            ],
        }


def summarize_batch(state: InsightsGraphState) -> dict:
    """LLM management commentary after numeric rollups + deep dive are known."""
    records = state.get("records", [])
    rollup = state.get("rollup")
    if rollup is None:
        return {"status": "completed"}

    try:
        summary = generate_executive_summary(rollup, records)
        rollup.executive_summary = summary
    except Exception as exc:  # keep report usable if summary fails
        return {
            "status": "completed",
            "rollup": rollup,
            "errors": [
                {
                    "node": "summarize_batch",
                    "message": str(exc),
                }
            ],
        }

    return {
        "status": "completed",
        "rollup": rollup,
    }
