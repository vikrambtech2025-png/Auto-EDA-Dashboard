import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, ensure_dirs


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                rows INTEGER NOT NULL,
                columns INTEGER NOT NULL,
                size_bytes INTEGER NOT NULL,
                quality_score REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                dataset_id INTEGER PRIMARY KEY,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            )
            """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_datasets_created_at ON datasets(created_at DESC)"
        )


def create_dataset(
    *,
    name: str,
    original_filename: str,
    stored_path: Path,
    rows: int,
    columns: int,
    size_bytes: int,
    quality_score: float,
    report: dict[str, Any],
) -> int:
    created_at = now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO datasets
                (name, original_filename, stored_path, rows, columns, size_bytes, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                original_filename,
                str(stored_path),
                rows,
                columns,
                size_bytes,
                quality_score,
                created_at,
            ),
        )
        dataset_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO reports (dataset_id, report_json, created_at)
            VALUES (?, ?, ?)
            """,
            (dataset_id, json.dumps(report), created_at),
        )
        return dataset_id


def list_datasets(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, original_filename, rows, columns, size_bytes, quality_score, created_at
            FROM datasets
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_report(dataset_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT d.id, d.name, d.original_filename, d.rows, d.columns, d.size_bytes,
                   d.quality_score, d.created_at, r.report_json
            FROM datasets d
            JOIN reports r ON r.dataset_id = d.id
            WHERE d.id = ?
            """,
            (dataset_id,),
        ).fetchone()
    if row is None:
        return None
    payload = dict(row)
    payload["report"] = json.loads(payload.pop("report_json"))
    return payload
