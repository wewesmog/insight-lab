from __future__ import annotations

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any

from app.models import DatasetSummary, VerbatimAnalysis, VerbatimRow
from app.shared_services.db import get_connection

TEXT_COLUMNS = ("verbatim", "text", "feedback", "comment", "message", "review")
RATING_COLUMNS = ("star_rating", "rating", "stars", "score")
ID_COLUMNS = ("id", "verbatim_id", "external_id")
TIME_COLUMNS = ("timestamp", "occurred_at", "created_at", "date")


def _pick_column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {h.lower().strip(): h for h in headers}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
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
    rating_col = _pick_column(headers, RATING_COLUMNS)
    time_col = _pick_column(headers, TIME_COLUMNS)

    rows: list[VerbatimRow] = []
    for index, raw in enumerate(reader, start=1):
        text_value = (raw.get(text_col) or "").strip()
        if not text_value:
            continue

        external_id = (raw.get(id_col) or "").strip() if id_col else None
        rating_raw = (raw.get(rating_col) or "").strip() if rating_col else ""
        rating = float(rating_raw) if rating_raw else None
        occurred_at = (raw.get(time_col) or "").strip() if time_col else None

        rows.append(
            VerbatimRow(
                id=str(uuid.uuid4()),
                external_id=external_id or f"row-{index}",
                text=text_value,
                star_rating=rating,
                occurred_at=occurred_at or None,
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
            INSERT INTO verbatims (id, dataset_id, external_id, text, star_rating, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.id,
                    dataset_id,
                    row.external_id,
                    row.text,
                    row.star_rating,
                    row.occurred_at,
                )
                for row in rows
            ],
        )
    return get_dataset(dataset_id)


def load_sample_dataset(sample_path: Path, name: str | None = None) -> DatasetSummary:
    content = sample_path.read_bytes()
    rows = parse_csv(content, sample_path.name)
    label = name or sample_path.stem.replace("_", " ")
    return create_dataset(label, sample_path.name, rows)


def list_datasets() -> list[DatasetSummary]:
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
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """
        )
        return [_row_to_dataset_summary(row) for row in cur.fetchall()]


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
            SELECT id, external_id, text, star_rating, occurred_at
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
                star_rating=row["star_rating"],
                occurred_at=row["occurred_at"],
            )
            for row in cur.fetchall()
        ]


def list_analyses(dataset_id: str) -> list[VerbatimAnalysis]:
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
        records: list[VerbatimAnalysis] = []
        for row in cur.fetchall():
            payload = json.loads(row["analysis_json"])
            records.append(VerbatimAnalysis.model_validate(payload))
        return records


def save_analyses(dataset_id: str, records: list[VerbatimAnalysis], engine: str) -> None:
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
