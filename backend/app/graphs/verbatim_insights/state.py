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
        skipped=existing.skipped + new.skipped,
    )


class InsightsGraphState(TypedDict, total=False):
    run_id: str
    dataset_id: str
    analysis_id: Optional[str]
    status: Literal["pending", "running", "completed", "failed"]
    engine: str

    verbatims: list[VerbatimRow]
    pending_ids: list[str]
    current_verbatim_id: Optional[str]

    records: Annotated[list[VerbatimAnalysis], operator.add]
    errors: Annotated[list[dict], operator.add]
    stats: Annotated[RunStats, _merge_stats]
    rollup: Optional[InsightsRollup]
