from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import store
from app.models import (
    AnalysisListPage,
    AnalysisReport,
    AnalysisRunRequest,
    AnalysisRunResponse,
    UploadResponse,
)
from app.pipeline.jobs import enqueue_analysis
from app.graphs.verbatim_insights.graph import run_insights_graph
from app.shared_services.db import database_path, init_db

load_dotenv(_backend_root / ".env")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Insight Lab API",
    description="CSV upload → LangGraph verbatim insights beyond positive/negative",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | bool]:
    from app.shared_services.llm import get_model, llm_enabled

    return {
        "status": "ok",
        "database": database_path(),
        "llm_enabled": llm_enabled(),
        "llm_model": get_model(),
    }


@app.post("/analyses/upload", response_model=UploadResponse)
async def upload_and_start_analysis(
    file: UploadFile = File(...),
    name: str | None = Form(None),
) -> UploadResponse:
    """Upload CSV → create dataset + analysis job → run in background."""
    from app.shared_services.llm import llm_enabled

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    if not llm_enabled():
        raise HTTPException(
            status_code=503,
            detail="LLM is not available. Check Ollama is running and LLM_MODEL is set.",
        )

    content = await file.read()
    try:
        rows = store.parse_csv(content, file.filename)
        display_name = name or file.filename
        dataset = store.create_dataset(display_name, file.filename, rows)
        analysis = store.create_analysis(dataset.id, display_name, len(rows))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    enqueue_analysis(analysis.id)
    return UploadResponse(dataset=dataset, preview=rows[:5], analysis=analysis)


@app.get("/analyses", response_model=AnalysisListPage)
def list_analyses(page: int = 1, page_size: int = 20) -> AnalysisListPage:
    items, total = store.list_analysis_jobs(page=page, page_size=page_size)
    return AnalysisListPage(items=items, total=total, page=page, page_size=page_size)


@app.get("/analyses/{analysis_id}", response_model=AnalysisReport)
def get_analysis_report(analysis_id: str) -> AnalysisReport:
    try:
        analysis = store.get_analysis(analysis_id)
        dataset = store.get_dataset(analysis.dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Analysis not found") from exc

    rollup = store.get_analysis_rollup(analysis_id)
    # Row-level records are served via /export.csv, not embedded here.
    return AnalysisReport(
        analysis=analysis,
        dataset=dataset,
        rollup=rollup,
        records=[],
    )


@app.get("/analyses/{analysis_id}/export.csv")
def export_analysis_csv(analysis_id: str) -> StreamingResponse:
    try:
        analysis = store.get_analysis(analysis_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Analysis not found") from exc

    if analysis.status.value != "ready":
        raise HTTPException(status_code=409, detail="Analysis is not ready yet")

    records = store.list_analyses_for_dataset(analysis.dataset_id)
    csv_text = store.records_to_csv(records, analysis_name=analysis.name)
    stem = analysis.name.rsplit(".", 1)[0] if "." in analysis.name else analysis.name
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem).strip("_")
    filename = f"{safe_name or 'analysis'}_records.csv"

    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Analysis-Name": analysis.name,
        },
    )

@app.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: str) -> None:
    store.delete_analysis(analysis_id)
    return {"message": "Analysis deleted successfully"}

@app.post("/test/langgraph", response_model=AnalysisRunResponse)
def test_langgraph(body: AnalysisRunRequest) -> AnalysisRunResponse:
    """Sandbox: same request/response as the graph runner (not saved to the UI list)."""
    return run_insights_graph(body)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
