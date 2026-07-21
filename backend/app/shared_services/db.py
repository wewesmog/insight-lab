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
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
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
                nps_score REAL,
                ces_score REAL,
                occurred_at TEXT,
                extras_json TEXT,
                analysis_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_verbatims_dataset
                ON verbatims(dataset_id);

            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                total_rows INTEGER NOT NULL DEFAULT 0,
                processed_rows INTEGER NOT NULL DEFAULT 0,
                analyzed_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                rollup_json TEXT,
                summary_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                started_at TEXT,
                finished_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_created
                ON analyses(created_at DESC);
            """
        )
        _migrate_columns(conn)


def _migrate_columns(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(verbatims)").fetchall()}
    if "nps_score" not in cols:
        conn.execute("ALTER TABLE verbatims ADD COLUMN nps_score REAL")
    if "ces_score" not in cols:
        conn.execute("ALTER TABLE verbatims ADD COLUMN ces_score REAL")
    if "extras_json" not in cols:
        conn.execute("ALTER TABLE verbatims ADD COLUMN extras_json TEXT")


def database_path() -> str:
    return str(_DB_PATH)
