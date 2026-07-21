"""Pipeline entry point — all analysis runs go through the LangGraph."""

from __future__ import annotations

from app.graphs.verbatim_insights.graph import run_insights_graph
from app.models import AnalysisRunRequest, AnalysisRunResponse, VerbatimRow


def run_dataset_analysis(
    dataset_id: str,
    verbatims: list[VerbatimRow],
    *,
    analysis_id: str | None = None,
) -> AnalysisRunResponse:
    request = AnalysisRunRequest(
        dataset_id=dataset_id,
        verbatims=verbatims,
        analysis_id=analysis_id,
    )
    return run_insights_graph(request)
