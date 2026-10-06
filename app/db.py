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
SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    filetype TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embed_backend TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,
    embed_dim INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""

SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    triggered_by TEXT NOT NULL DEFAULT 'schedule',
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    result_summary TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_job ON job_runs(job_id);
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'note',
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    job_run_id INTEGER REFERENCES job_runs(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    dismissed_at TEXT
);
CREATE TABLE IF NOT EXISTS consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_name TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    granted_by TEXT NOT NULL DEFAULT 'user',
    revoked_at TEXT
);
"""

SCHEMA_V4 = """
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    model TEXT NOT NULL,
    route TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd REAL,
    latency_ms REAL,
    status TEXT NOT NULL DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS idx_ledger_ts ON ledger(ts);
CREATE INDEX IF NOT EXISTS idx_ledger_route ON ledger(route);
CREATE TABLE IF NOT EXISTS quota_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    month TEXT NOT NULL,
    threshold REAL NOT NULL,
    flagged_at TEXT NOT NULL,
    UNIQUE(route, month, threshold)
);
"""

SCHEMA_V5 = """
CREATE TABLE IF NOT EXISTS skill_files (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
"""

SCHEMA_VERSION = 5


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
            self._conn.executescript(SCHEMA_V2)
            self._conn.executescript(SCHEMA_V3)
            self._conn.executescript(SCHEMA_V4)
            self._conn.executescript(SCHEMA_V5)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
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
        allowed = {
            "name",
            "cron",
            "status",
            "last_run_at",
            "next_run_at",
            "payload_json",
        }
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

    # ── documents ──────────────────────────────────────────────

    def add_document(
        self,
        doc_id: str,
        filename: str,
        filetype: str,
        title: str,
        tags: str,
        size_bytes: int,
        chunk_count: int,
        embed_backend: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO documents
                   (id, filename, filetype, title, tags, size_bytes,
                    chunk_count, embed_backend, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc_id,
                    filename,
                    filetype,
                    title,
                    tags,
                    size_bytes,
                    chunk_count,
                    embed_backend,
                    _now(),
                ),
            )
            self._conn.commit()

    def get_document(self, doc_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def list_documents(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM documents ORDER BY uploaded_at DESC"
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            self._conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            self._conn.commit()
            return cur.rowcount > 0

    # ── chunks ─────────────────────────────────────────────────

    def add_chunks(
        self,
        doc_id: str,
        chunks: list[tuple[str, int, str, bytes, int]],
    ) -> None:
        """Add chunks as (chunk_id, chunk_index, content, embedding_bytes, dim)."""
        with self._lock:
            self._conn.executemany(
                """INSERT INTO chunks
                   (id, doc_id, chunk_index, content, embedding, embed_dim)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (cid, doc_id, idx, content, emb, dim)
                    for cid, idx, content, emb, dim in chunks
                ],
            )
            self._conn.commit()

    def get_chunks(self, doc_id: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, doc_id, chunk_index, content, embed_dim FROM chunks "
                "WHERE doc_id = ? ORDER BY chunk_index",
                (doc_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_all_chunk_embeddings(self) -> list[dict]:
        """All chunk embeddings for in-memory cosine search.

        Personal-scale design: fine for thousands of chunks; the scaling
        path (sqlite-vec / pgvector) is documented in ARCHITECTURE.md.
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT c.id AS chunk_id, c.doc_id, c.chunk_index, c.content, "
                "c.embedding, c.embed_dim, d.filename "
                "FROM chunks c JOIN documents d ON c.doc_id = d.id"
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ── Phase 3: runs, suggestions, consents ────────────────────

    def get_due_jobs(self, now_iso: str) -> list[dict]:
        """Jobs with a cron whose next run has passed and not paused."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM jobs WHERE cron IS NOT NULL AND cron != ''"
                " AND next_run_at IS NOT NULL AND next_run_at <= ?"
                " AND (status IS NULL OR status != 'paused')"
                " ORDER BY next_run_at",
                (now_iso,),
            )
            rows = cur.fetchall()
        return [self._row_to_job(r) for r in rows]

    def create_run(self, job_id: str, triggered_by: str = "schedule") -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO job_runs (job_id, triggered_by, status, started_at)"
                " VALUES (?, ?, 'running', ?)",
                (job_id, triggered_by, _now()),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def finish_run(
        self,
        run_id: int,
        status: str,
        result_summary: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE job_runs SET status = ?, finished_at = ?,"
                " result_summary = ?, error = ? WHERE id = ?",
                (status, _now(), result_summary, error, run_id),
            )
            self._conn.commit()

    def list_runs(self, job_id: str, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM job_runs WHERE job_id = ?"
                " ORDER BY started_at DESC LIMIT ?",
                (job_id, limit),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def create_suggestion(
        self,
        kind: str,
        title: str,
        body: str = "",
        job_run_id: int | None = None,
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO suggestions (kind, title, body, job_run_id, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (kind, title, body, job_run_id, _now()),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def list_suggestions(self, include_dismissed: bool = False) -> list[dict]:
        with self._lock:
            q = "SELECT * FROM suggestions"
            if not include_dismissed:
                q += " WHERE dismissed_at IS NULL"
            q += " ORDER BY created_at DESC"
            cur = self._conn.execute(q)
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def dismiss_suggestion(self, suggestion_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE suggestions SET dismissed_at = ?"
                " WHERE id = ? AND dismissed_at IS NULL",
                (_now(), suggestion_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def grant_consent(self, action_name: str, granted_by: str = "user") -> dict:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO consents (action_name, granted_at, granted_by)"
                " VALUES (?, ?, ?)",
                (action_name, _now(), granted_by),
            )
            self._conn.commit()
            row_id = cur.lastrowid
        return {
            "id": row_id,
            "action": action_name,
            "granted_by": granted_by,
        }

    def revoke_consent(self, action_name: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE consents SET revoked_at = ?"
                " WHERE action_name = ? AND revoked_at IS NULL",
                (_now(), action_name),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def consent_granted(self, action_name: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM consents WHERE action_name = ? AND revoked_at IS NULL",
                (action_name,),
            )
            return cur.fetchone() is not None

    # ── Phase 4: cost ledger ──────────────────────────────────

    def record_ledger(
        self,
        model: str,
        route: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        cost_usd: float | None,
        latency_ms: float | None,
        status: str = "ok",
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO ledger (ts, model, route, prompt_tokens,"
                " completion_tokens, cost_usd, latency_ms, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _now(),
                    model,
                    route,
                    prompt_tokens,
                    completion_tokens,
                    cost_usd,
                    latency_ms,
                    status,
                ),
            )
            self._conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    def list_ledger(self, limit: int = 100) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM ledger ORDER BY ts DESC LIMIT ?", (limit,)
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def ledger_monthly_summary(self, month: str) -> list[dict]:
        """Per-route rollup for a YYYY-MM month: calls, tokens, cost."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT route,"
                " COUNT(*) AS calls,"
                " COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,"
                " COALESCE(SUM(completion_tokens), 0) AS completion_tokens,"
                " COALESCE(SUM(cost_usd), 0.0) AS cost_usd"
                " FROM ledger WHERE substr(ts, 1, 7) = ? AND status = 'ok'"
                " GROUP BY route",
                (month,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def quota_flagged(self, route: str, month: str, threshold: float) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id FROM quota_flags"
                " WHERE route = ? AND month = ? AND threshold = ?",
                (route, month, threshold),
            )
            return cur.fetchone() is not None

    def mark_quota_flagged(self, route: str, month: str, threshold: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO quota_flags"
                " (route, month, threshold, flagged_at) VALUES (?, ?, ?, ?)",
                (route, month, threshold, _now()),
            )
            self._conn.commit()

    # ── Phase 5: skills ───────────────────────────────────────

    def upsert_skill_file(
        self,
        name: str,
        path: str,
        sha256: str,
        doc_id: str,
        description: str = "",
        version: str = "",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO skill_files"
                " (name, path, sha256, doc_id, description, version, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(name) DO UPDATE SET"
                " path=excluded.path, sha256=excluded.sha256,"
                " doc_id=excluded.doc_id, description=excluded.description,"
                " version=excluded.version, updated_at=excluded.updated_at",
                (name, path, sha256, doc_id, description, version, _now()),
            )
            self._conn.commit()

    def get_skill_file(self, name: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM skill_files WHERE name = ?", (name,)
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def list_skill_files(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM skill_files ORDER BY name")
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def delete_skill_file(self, name: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM skill_files WHERE name = ?", (name,))
            self._conn.commit()
            return cur.rowcount > 0
