# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""SQLite persistence (stdlib only).

Holds the ``jobs`` table — the seed of the proactive engine. Job *execution*
arrives in Phase 3; Phase 1 stores, lists, and deletes job definitions only.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cron TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    last_run_at TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: str):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(p), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            cur = self._conn.execute(
                "SELECT COUNT(*) AS n FROM schema_migrations WHERE version = ?",
                (SCHEMA_VERSION,),
            )
            if cur.fetchone()["n"] == 0:
                self._conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _now()),
                )
            self._conn.commit()

    def _row_to_job(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["payload"] = json.loads(d.pop("payload_json"))
        return d

    def create_job(
        self, name: str, cron: str | None = None, payload: dict | None = None
    ) -> dict:
        job_id = uuid.uuid4().hex[:12]
        now = _now()
        with self._lock:
            self._conn.execute(
                """INSERT INTO jobs
                   (id, name, cron, payload_json, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
                (job_id, name, cron, json.dumps(payload or {}), now, now),
            )
            self._conn.commit()
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [self._row_to_job(r) for r in rows]

    def update_job(self, job_id: str, **fields: str | None) -> dict | None:
        allowed = {"name", "cron", "status", "last_run_at", "next_run_at"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_job(job_id)
        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        with self._lock:
            cur = self._conn.execute(
                f"UPDATE jobs SET {set_clause} WHERE id = ?",
                (*updates.values(), job_id),
            )
            self._conn.commit()
            if cur.rowcount == 0:
                return None
        return self.get_job(job_id)

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            self._conn.commit()
            return cur.rowcount > 0
