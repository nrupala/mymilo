# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Session memory spine for Milo (v0.10.0).

Every conversation is a session. Sessions persist in SQLite; the PWA
lists them and resumes them. Recent turns are injected as context so
Milo remembers what was just discussed.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path


class MemoryStore:
    """SQLite-backed session store."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT 'New chat',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, id)"
            )

    def create_session(self, title: str = "New chat") -> str:
        sid = uuid.uuid4().hex[:12]
        now = time.time()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at)"
                " VALUES (?,?,?,?)",
                (sid, title, now, now),
            )
        return sid

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT id, title, created_at, updated_at FROM sessions"
                " ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_messages(self, session_id: str, limit: int = 100) -> list[dict]:
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT role, content, created_at FROM messages"
                " WHERE session_id=? ORDER BY id ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_message(self, session_id: str, role: str, content: str) -> None:
        now = time.time()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO messages (session_id, role, content, created_at)"
                " VALUES (?,?,?,?)",
                (session_id, role, content, now),
            )
            c.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, session_id))
            # Auto-title from the first user message.
            if role == "user":
                count = c.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id=?",
                    (session_id,),
                ).fetchone()[0]
                if count == 1:
                    title = content[:60] + ("…" if len(content) > 60 else "")
                    c.execute(
                        "UPDATE sessions SET title=? WHERE id=?",
                        (title, session_id),
                    )

    def delete_session(self, session_id: str) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            c.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def recent_context(self, session_id: str, max_turns: int = 10) -> list[dict]:
        """Last N messages formatted for model context."""
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT role, content FROM messages"
                " WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, max_turns * 2),
            ).fetchall()
            msgs = [dict(r) for r in reversed(rows)]
        return [
            {"role": m["role"], "content": m["content"]}
            for m in msgs
            if m["role"] in ("user", "assistant")
        ]
