"""LangGraph nodes for verbatim insights analysis."""

from __future__ import annotations

import uuid
from typing import Literal

from langgraph.graph import END

from app.graphs.verbatim_insights.state import InsightsGraphState
from app.models import (
    ChurnRisk,
    Emotion,
    NpsClass,
    RunStats,
    Sentiment,
    SkipReason,
    VerbatimAnalysis,
    VerbatimRow,
)
from app.pipeline.rules import analyze_with_rules, rule_skip
from app.pipeline.rollup import build_rollup
from app.prompts.extract import EXTRACT_SYSTEM, build_extract_user
from app.shared_services.llm import analyze_with_llm, get_model, llm_enabled


def _verbatim_map(state: InsightsGraphState) -> dict[str, VerbatimRow]:
    return {row.id: row for row in state.get("verbatims", [])}


def build_initial_state(
    *,
    dataset_id: str,
    verbatims: list[VerbatimRow],
    run_id: str | None = None,
) -> InsightsGraphState:
    engine: Literal["rules", "llm"] = "llm" if llm_enabled() else "rules"
    return InsightsGraphState(
        run_id=run_id or str(uuid.uuid4()),
        dataset_id=dataset_id,
        status="pending",
        engine=engine,
        verbatims=verbatims,
        pending_ids=[],
        records=[],
        errors=[],
        stats=RunStats(),
        rollup=None,
    )


def prepare(state: InsightsGraphState) -> dict:
    """Batch node: seed the work queue from uploaded verbatims."""
    verbatims = state.get("verbatims", [])
    return {
        "status": "running",
        "pending_ids": [row.id for row in verbatims],
        "records": [],
        "errors": [],
        "stats": RunStats(),
    }


def analyze_one(state: InsightsGraphState) -> dict:
    """Per-verbatim node: rule gate → rules engine OR LLM extract."""
    pending = list(state.get("pending_ids", []))
    if not pending:
        return {}

    verbatim_id = pending[0]
    remaining = pending[1:]
    row = _verbatim_map(state).get(verbatim_id)

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

    skip = rule_skip(row.text)
    if skip is not None:
        record = VerbatimAnalysis(
            verbatim_id=row.id,
            text=row.text,
            star_rating=row.star_rating,
            skipped=True,
            skip_reason=skip,
            engine=state.get("engine", "rules"),
        )
        return {
            "pending_ids": remaining,
            "current_verbatim_id": verbatim_id,
            "records": [record],
            "stats": RunStats(rule_skips=1),
        }

    engine = state.get("engine", "rules")
    if engine == "llm":
        record = _extract_with_llm(row)
        return {
            "pending_ids": remaining,
            "current_verbatim_id": verbatim_id,
            "records": [record],
            "stats": RunStats(llm_calls=1),
        }

    record = analyze_with_rules(row)
    return {
        "pending_ids": remaining,
        "current_verbatim_id": verbatim_id,
        "records": [record],
        "stats": RunStats(rule_analyzed=1),
    }


def _extract_with_llm(row: VerbatimRow) -> VerbatimAnalysis:
    payload = analyze_with_llm(
        text=row.text,
        star_rating=row.star_rating,
        system_prompt=EXTRACT_SYSTEM,
        user_prompt=build_extract_user(text=row.text, star_rating=row.star_rating),
    )
    return VerbatimAnalysis(
        verbatim_id=row.id,
        text=row.text,
        star_rating=row.star_rating,
        sentiment=Sentiment(payload.get("sentiment", "neutral")),
        emotion=Emotion(payload.get("emotion", "neutral")),
        nps_class=NpsClass(payload.get("nps_class", "passive")),
        churn_risk=ChurnRisk(payload.get("churn_risk", "low")),
        themes=list(payload.get("themes") or []),
        issues=list(payload.get("issues") or []),
        delights=list(payload.get("delights") or []),
        summary=payload.get("summary"),
        key_quote=payload.get("key_quote"),
        engine="llm",
    )


def route_after_analyze(state: InsightsGraphState) -> Literal["analyze_one", "rollup_batch"]:
    if state.get("pending_ids"):
        return "analyze_one"
    return "rollup_batch"


def rollup_batch(state: InsightsGraphState) -> dict:
    """Batch node: deterministic rollups from structured per-verbatim records."""
    records = state.get("records", [])
    dataset_id = state.get("dataset_id", "")
    rollup = build_rollup(dataset_id, records)
    return {
        "status": "completed",
        "rollup": rollup,
    }


def route_after_rollup(_state: InsightsGraphState):
    return END
