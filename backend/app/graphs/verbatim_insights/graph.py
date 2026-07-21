"""Compile and run the verbatim insights LangGraph."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graphs.verbatim_insights.nodes import (
    analyze_one,
    build_initial_state,
    enrich_batch,
    prepare,
    rollup_batch,
    route_after_analyze,
    route_after_rollup,
    summarize_batch,
)
from app.graphs.verbatim_insights.state import InsightsGraphState
from app.models import AnalysisRunRequest, AnalysisRunResponse, RunStats


@lru_cache(maxsize=1)
def get_insights_graph():
    graph = StateGraph(InsightsGraphState)
    graph.add_node("prepare", prepare)
    graph.add_node("analyze_one", analyze_one)
    graph.add_node("rollup_batch", rollup_batch)
    graph.add_node("enrich_batch", enrich_batch)
    graph.add_node("summarize_batch", summarize_batch)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "analyze_one")
    graph.add_conditional_edges(
        "analyze_one",
        route_after_analyze,
        {"analyze_one": "analyze_one", "rollup_batch": "rollup_batch"},
    )
    graph.add_conditional_edges(
        "rollup_batch",
        route_after_rollup,
        {
            "enrich_batch": "enrich_batch",
            "summarize_batch": "summarize_batch",
            "end": END,
        },
    )
    graph.add_edge("enrich_batch", "summarize_batch")
    graph.add_edge("summarize_batch", END)

    return graph.compile()


def run_insights_graph(request: AnalysisRunRequest) -> AnalysisRunResponse:
    initial = build_initial_state(
        dataset_id=request.dataset_id,
        verbatims=request.verbatims,
        analysis_id=request.analysis_id,
    )

    graph = get_insights_graph()
    n = len(request.verbatims)
    recursion_limit = max(25, n + 15)
    final = graph.invoke(initial, config={"recursion_limit": recursion_limit})

    records = final.get("records", [])
    analyzed = sum(1 for r in records if not r.skipped)
    skipped = sum(1 for r in records if r.skipped)

    return AnalysisRunResponse(
        run_id=final.get("run_id", initial["run_id"]),
        dataset_id=request.dataset_id,
        status=final.get("status", "completed"),  # type: ignore[arg-type]
        engine=final.get("engine", initial["engine"]),
        records=records,
        analyzed_count=analyzed,
        skipped_count=skipped,
        stats=final.get("stats") or RunStats(),
        rollup=final.get("rollup"),
    )
