from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AnalyzeResponse,
    DatasetSummary,
    InsightsRollup,
    UploadResponse,
    VerbatimAnalysis,
)
from app.pipeline.run import run_dataset_analysis
from app.shared_services.db import database_path, init_db
from app.config.samples import DEFAULT_SAMPLE, SAMPLE_DATASETS, SAMPLE_ROOT
from app import store

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
    from app.shared_services.llm import llm_enabled

    return {
        "status": "ok",
        "database": database_path(),
        "llm_enabled": llm_enabled(),
    }


@app.get("/datasets", response_model=list[DatasetSummary])
def get_datasets() -> list[DatasetSummary]:
    return store.list_datasets()


@app.post("/datasets/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = None,
) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")

    content = await file.read()
    try:
        rows = store.parse_csv(content, file.filename)
        dataset = store.create_dataset(name or file.filename, file.filename, rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(dataset=dataset, preview=rows[:5])


@app.post("/datasets/sample", response_model=UploadResponse)
def load_sample(sample: str = DEFAULT_SAMPLE) -> UploadResponse:
    key = sample.strip().lower()
    if key not in SAMPLE_DATASETS:
        allowed = ", ".join(SAMPLE_DATASETS)
        raise HTTPException(status_code=400, detail=f"Unknown sample '{sample}'. Use: {allowed}")

    display_name, filename = SAMPLE_DATASETS[key]
    sample_path = SAMPLE_ROOT / filename
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample CSV not found: {filename}")

    dataset = store.load_sample_dataset(sample_path, display_name)
    preview = store.list_verbatim_rows(dataset.id, limit=5)
    return UploadResponse(dataset=dataset, preview=preview)


@app.get("/datasets/{dataset_id}", response_model=DatasetSummary)
def get_dataset(dataset_id: str) -> DatasetSummary:
    try:
        return store.get_dataset(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc


@app.post("/datasets/{dataset_id}/analyze", response_model=AnalyzeResponse)
def analyze_dataset(dataset_id: str) -> AnalyzeResponse:
    try:
        store.get_dataset(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc

    rows = store.list_verbatim_rows(dataset_id, limit=10_000)
    result = run_dataset_analysis(dataset_id, rows)
    store.save_analyses(dataset_id, result.records, result.engine)

    if result.rollup is None:
        raise HTTPException(status_code=500, detail="Graph did not produce rollups")

    return AnalyzeResponse(
        dataset_id=dataset_id,
        run_id=result.run_id,
        analyzed=result.analyzed_count,
        skipped=result.skipped_count,
        engine=result.engine,
        records=result.records,
        rollup=result.rollup,
    )


@app.get("/datasets/{dataset_id}/insights", response_model=InsightsRollup)
def dataset_insights(dataset_id: str) -> InsightsRollup:
    try:
        store.get_dataset(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc

    records = store.list_analyses(dataset_id)
    if not records:
        raise HTTPException(status_code=404, detail="Run analysis first")

    from app.pipeline.rollup import build_rollup

    return build_rollup(dataset_id, records)


@app.get("/datasets/{dataset_id}/records", response_model=list[VerbatimAnalysis])
def dataset_records(dataset_id: str) -> list[VerbatimAnalysis]:
    try:
        store.get_dataset(dataset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc

    records = store.list_analyses(dataset_id)
    if not records:
        raise HTTPException(status_code=404, detail="Run analysis first")
    return records
