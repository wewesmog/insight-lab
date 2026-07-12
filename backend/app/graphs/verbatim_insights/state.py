"""LangGraph state for the verbatim insights pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional

from typing_extensions import TypedDict

from app.models import InsightsRollup, RunStats, VerbatimAnalysis, VerbatimRow


def _merge_stats(existing: Optional[RunStats], new: Optional[RunStats]) -> RunStats:
    if existing is None:
        return new or RunStats()
    if new is None:
        return existing
    return RunStats(
        llm_calls=existing.llm_calls + new.llm_calls,
        rule_skips=existing.rule_skips + new.rule_skips,
        rule_analyzed=existing.rule_analyzed + new.rule_analyzed,
    )


class InsightsGraphState(TypedDict, total=False):
    run_id: str
    dataset_id: str
    status: Literal["pending", "running", "completed", "failed"]
    engine: Literal["rules", "llm"]

    verbatims: list[VerbatimRow]
    pending_ids: list[str]
    current_verbatim_id: Optional[str]

    records: Annotated[list[VerbatimAnalysis], operator.add]
    errors: Annotated[list[dict], operator.add]
    stats: Annotated[RunStats, _merge_stats]
    rollup: Optional[InsightsRollup]
