from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_DB_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        Path(__file__).resolve().parents[2] / "data" / "insight_lab.db",
    )
)


def get_connection() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                row_count INTEGER NOT NULL DEFAULT 0,
                analyzed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS verbatims (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                external_id TEXT,
                text TEXT NOT NULL,
                star_rating REAL,
                occurred_at TEXT,
                analysis_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_verbatims_dataset
                ON verbatims(dataset_id);
            """
        )


def database_path() -> str:
    return str(_DB_PATH)
