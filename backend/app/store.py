from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from app.models import (
    AnalysisStatus,
    AnalysisSummary,
    DatasetSummary,
    ExecutiveSummary,
    InsightsRollup,
    VerbatimAnalysis,
    VerbatimRow,
)
from app.shared_services.db import get_connection

TEXT_COLUMNS = ("verbatim", "text", "feedback", "comment", "message", "review")
ID_COLUMNS = ("id", "verbatim_id", "external_id")
TIME_COLUMNS = ("timestamp", "occurred_at", "created_at", "date")


def _normalize_header(header: str) -> str:
    return header.lower().strip().replace(" ", "_").replace("-", "_")


def _pick_column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {_normalize_header(h): h for h in headers}
    for candidate in candidates:
        if _normalize_header(candidate) in lowered:
            return lowered[_normalize_header(candidate)]
    return None


def parse_csv(content: bytes, filename: str) -> list[VerbatimRow]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    headers = list(reader.fieldnames)
    text_col = _pick_column(headers, TEXT_COLUMNS)
    if not text_col:
        raise ValueError(
            f"Could not find a text column. Expected one of: {', '.join(TEXT_COLUMNS)}"
        )

    id_col = _pick_column(headers, ID_COLUMNS)
    time_col = _pick_column(headers, TIME_COLUMNS)

    known = {c for c in (text_col, id_col, time_col) if c}

    rows: list[VerbatimRow] = []
    for index, raw in enumerate(reader, start=1):
        text_value = (raw.get(text_col) or "").strip()
        if not text_value:
            continue

        external_id = (raw.get(id_col) or "").strip() if id_col else None
        occurred_at = (raw.get(time_col) or "").strip() if time_col else None

        extras: dict[str, str] = {}
        for header in headers:
            if header in known:
                continue
            value = (raw.get(header) or "").strip()
            if value:
                extras[header.strip()] = value

        rows.append(
            VerbatimRow(
                id=str(uuid.uuid4()),
                external_id=external_id or f"row-{index}",
                text=text_value,
                occurred_at=occurred_at or None,
                extras=extras,
            )
        )

    if not rows:
        raise ValueError("CSV contained no non-empty verbatim rows")

    return rows


def create_dataset(name: str, filename: str, rows: list[VerbatimRow]) -> DatasetSummary:
    dataset_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO datasets (id, name, filename, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_id, name, filename, len(rows)),
        )
        conn.executemany(
            """
            INSERT INTO verbatims (
                id, dataset_id, external_id, text, star_rating, nps_score, ces_score,
                occurred_at, extras_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    dataset_id,
                    row.external_id,
                    row.text,
                    None,
                    None,
                    None,
                    row.occurred_at,
                    json.dumps(row.extras) if row.extras else None,
                )
                for row in rows
            ],
        )
    return get_dataset(dataset_id)


def get_dataset(dataset_id: str) -> DatasetSummary:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                d.id,
                d.name,
                d.filename,
                d.row_count,
                d.analyzed_at,
                d.created_at,
                COUNT(v.analysis_json) AS analyzed_count
            FROM datasets d
            LEFT JOIN verbatims v ON v.dataset_id = d.id AND v.analysis_json IS NOT NULL
            WHERE d.id = ?
            GROUP BY d.id
            """,
            (dataset_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise KeyError(dataset_id)
        return _row_to_dataset_summary(row)


def list_verbatim_rows(dataset_id: str, limit: int = 200) -> list[VerbatimRow]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT id, external_id, text, occurred_at, extras_json
            FROM verbatims
            WHERE dataset_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (dataset_id, limit),
        )
        return [
            VerbatimRow(
                id=row["id"],
                external_id=row["external_id"],
                text=row["text"],
                occurred_at=row["occurred_at"],
                extras=json.loads(row["extras_json"]) if row["extras_json"] else {},
            )
            for row in cur.fetchall()
        ]


def list_analyses_for_dataset(dataset_id: str) -> list[VerbatimAnalysis]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT analysis_json
            FROM verbatims
            WHERE dataset_id = ? AND analysis_json IS NOT NULL
            ORDER BY created_at ASC
            """,
            (dataset_id,),
        )
        return [
            VerbatimAnalysis.model_validate(json.loads(row["analysis_json"]))
            for row in cur.fetchall()
        ]


def records_to_csv(
    records: list[VerbatimAnalysis],
    *,
    analysis_name: str | None = None,
) -> str:
    """Serialize analyzed verbatims to CSV for download (not shown in the report UI)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "analysis_name",
            "verbatim_id",
            "text",
            "skipped",
            "skip_reason",
            "sentiment",
            "emotion",
            "nps_class",
            "churn_risk",
            "themes",
            "issues",
            "delights",
            "summary",
            "key_quote",
            "engine",
        ]
    )
    name = analysis_name or ""
    for record in records:
        writer.writerow(
            [
                name,
                record.verbatim_id,
                record.text,
                "yes" if record.skipped else "no",
                record.skip_reason.value if record.skip_reason else "",
                record.sentiment.value if record.sentiment else "",
                record.emotion.value if record.emotion else "",
                record.nps_class.value if record.nps_class else "",
                record.churn_risk.value if record.churn_risk else "",
                "; ".join(record.themes),
                "; ".join(record.issues),
                "; ".join(record.delights),
                record.summary or "",
                record.key_quote or "",
                record.engine,
            ]
        )
    return buffer.getvalue()


def save_analyses(dataset_id: str, records: list[VerbatimAnalysis], engine: str) -> None:
    _ = engine
    with get_connection() as conn:
        for record in records:
            conn.execute(
                """
                UPDATE verbatims
                SET analysis_json = ?
                WHERE id = ? AND dataset_id = ?
                """,
                (record.model_dump_json(), record.verbatim_id, dataset_id),
            )
        conn.execute(
            """
            UPDATE datasets
            SET analyzed_at = datetime('now')
            WHERE id = ?
            """,
            (dataset_id,),
        )


def create_analysis(dataset_id: str, name: str, total_rows: int) -> AnalysisSummary:
    analysis_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                id, dataset_id, name, status, total_rows, processed_rows
            )
            VALUES (?, ?, ?, 'queued', ?, 0)
            """,
            (analysis_id, dataset_id, name, total_rows),
        )
    return get_analysis(analysis_id)


def list_analysis_jobs(
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AnalysisSummary], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    with get_connection() as conn:
        total = int(conn.execute("SELECT COUNT(*) AS n FROM analyses").fetchone()["n"])
        cur = conn.execute(
            """
            SELECT *
            FROM analyses
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        )
        items = [_row_to_analysis_summary(row) for row in cur.fetchall()]
        return items, total


def get_analysis(analysis_id: str) -> AnalysisSummary:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(analysis_id)
        return _row_to_analysis_summary(row)


def mark_analysis_running(analysis_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analyses
            SET status = 'running', started_at = datetime('now'), error = NULL
            WHERE id = ?
            """,
            (analysis_id,),
        )


def bump_analysis_progress(analysis_id: str, processed_rows: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analyses
            SET processed_rows = ?
            WHERE id = ?
            """,
            (processed_rows, analysis_id),
        )


def complete_analysis(
    analysis_id: str,
    *,
    analyzed_count: int,
    skipped_count: int,
    rollup: InsightsRollup,
    summary: ExecutiveSummary | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analyses
            SET
                status = 'ready',
                processed_rows = total_rows,
                analyzed_count = ?,
                skipped_count = ?,
                rollup_json = ?,
                summary_json = ?,
                finished_at = datetime('now'),
                error = NULL
            WHERE id = ?
            """,
            (
                analyzed_count,
                skipped_count,
                rollup.model_dump_json(),
                summary.model_dump_json() if summary else None,
                analysis_id,
            ),
        )


def fail_analysis(analysis_id: str, error: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE analyses
            SET status = 'failed', error = ?, finished_at = datetime('now')
            WHERE id = ?
            """,
            (error, analysis_id),
        )


def get_analysis_rollup(analysis_id: str) -> InsightsRollup | None:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT rollup_json, summary_json FROM analyses WHERE id = ?",
            (analysis_id,),
        )
        row = cur.fetchone()
        if row is None or not row["rollup_json"]:
            return None
        rollup = InsightsRollup.model_validate_json(row["rollup_json"])
        if row["summary_json"]:
            rollup.executive_summary = ExecutiveSummary.model_validate_json(row["summary_json"])
        return rollup


def _row_to_dataset_summary(row: Any) -> DatasetSummary:
    analyzed_count = int(row["analyzed_count"] or 0)
    row_count = int(row["row_count"])
    return DatasetSummary(
        id=row["id"],
        name=row["name"],
        filename=row["filename"],
        row_count=row_count,
        analyzed_count=analyzed_count,
        skipped_count=max(row_count - analyzed_count, 0),
        analyzed_at=row["analyzed_at"],
        created_at=row["created_at"],
    )


def _row_to_analysis_summary(row: Any) -> AnalysisSummary:
    total = int(row["total_rows"] or 0)
    processed = int(row["processed_rows"] or 0)
    pct = (processed / total * 100.0) if total else 0.0
    if row["status"] == AnalysisStatus.ready.value:
        pct = 100.0
    return AnalysisSummary(
        id=row["id"],
        dataset_id=row["dataset_id"],
        name=row["name"],
        status=AnalysisStatus(row["status"]),
        total_rows=total,
        processed_rows=processed,
        analyzed_count=int(row["analyzed_count"] or 0),
        skipped_count=int(row["skipped_count"] or 0),
        error=row["error"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        progress_pct=round(pct, 1),
    )


def delete_analysis(analysis_id: str) -> None:
    """Remove the analysis by deleting its dataset (verbatims + analyses cascade)."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT dataset_id
            FROM analyses
            WHERE id = ?
            """,
            (analysis_id,),
        ).fetchone()
        if row is None:
            raise KeyError(analysis_id)

        conn.execute(
            """
            DELETE FROM datasets
            WHERE id = ?
            """,
            (row["dataset_id"],),
        )
