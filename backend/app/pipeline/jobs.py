"""Background analysis runner (in-process — fine for single-user tester demos)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app import store
from app.pipeline.run import run_dataset_analysis

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)


def enqueue_analysis(analysis_id: str) -> None:
    _executor.submit(_run_analysis_job, analysis_id)


def _run_analysis_job(analysis_id: str) -> None:
    try:
        analysis = store.get_analysis(analysis_id)
        store.mark_analysis_running(analysis_id)
        rows = store.list_verbatim_rows(analysis.dataset_id, limit=10_000)
        result = run_dataset_analysis(
            analysis.dataset_id,
            rows,
            analysis_id=analysis_id,
        )
        store.save_analyses(analysis.dataset_id, result.records, result.engine)
        if result.rollup is None:
            raise RuntimeError("Graph did not produce rollups")
        store.complete_analysis(
            analysis_id,
            analyzed_count=result.analyzed_count,
            skipped_count=result.skipped_count,
            rollup=result.rollup,
            summary=result.rollup.executive_summary,
        )
    except Exception as exc:
        logger.exception("Analysis %s failed", analysis_id)
        store.fail_analysis(analysis_id, str(exc))
