"""Pipeline entry point — all analysis runs go through the LangGraph."""

from __future__ import annotations

from app.graphs.verbatim_insights.graph import run_insights_graph
from app.models import AnalysisRunRequest, AnalysisRunResponse, VerbatimRow


def run_dataset_analysis(dataset_id: str, verbatims: list[VerbatimRow]) -> AnalysisRunResponse:
    request = AnalysisRunRequest(dataset_id=dataset_id, verbatims=verbatims)
    return run_insights_graph(request)
