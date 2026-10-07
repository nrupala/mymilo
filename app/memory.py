# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Session memory spine for Milo (v0.10.0, multi-user in v0.11.0).

Every conversation is a session, scoped to a user (by email from
Cloudflare Access). Two users = two separate memories, two IDs.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path


class MemoryStore:
    """SQLite-backed session store, isolated per user."""

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
                    user_email TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT 'New chat',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            # Migrate v0.10.x DBs that lack user_email.
            cols = [r[1] for r in c.execute("PRAGMA table_info(sessions)")]
            if "user_email" not in cols:
                c.execute(
                    "ALTER TABLE sessions ADD COLUMN "
                    "user_email TEXT NOT NULL DEFAULT ''"
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
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_sess_user "
                "ON sessions(user_email, updated_at DESC)"
            )

    def create_session(self, user_email: str = "", title: str = "New chat") -> str:
        sid = uuid.uuid4().hex[:12]
        now = time.time()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO sessions (id, user_email, title, created_at, updated_at)"
                " VALUES (?,?,?,?,?)",
                (sid, user_email, title, now, now),
            )
        return sid

    def list_sessions(self, user_email: str = "", limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT id, title, created_at, updated_at FROM sessions"
                " WHERE user_email=? ORDER BY updated_at DESC LIMIT ?",
                (user_email, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_messages(
        self, session_id: str, user_email: str = "", limit: int = 100
    ) -> list[dict]:
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            # Verify the session belongs to this user.
            owner = c.execute(
                "SELECT user_email FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not owner or owner["user_email"] != user_email:
                return []
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

    def delete_session(self, session_id: str, user_email: str = "") -> None:
        with sqlite3.connect(self.path) as c:
            # Only delete if owned by this user.
            owner = c.execute(
                "SELECT user_email FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not owner or owner[0] != user_email:
                return
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
