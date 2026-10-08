# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Device token auth for native clients (v0.31.0).

Native apps (Android) can't use the Cloudflare Access browser flow.
They register a device and get a bearer token, stored hashed server-side.

Flow:
1. User (signed in via CF Access in a browser) calls POST /v1/devices/register
   with a device name/platform → server returns a one-time plaintext token.
2. The native app stores the token (Android Keystore) and sends it as
   `Authorization: Bearer <token>` on API calls.
3. Server resolves the token → user email; all data stays user-scoped.
4. Tokens are revocable via DELETE /v1/devices/{id}.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from pathlib import Path


def _hash_token(token: str) -> str:
    """SHA-256 hash of a device token (stored server-side)."""
    return hashlib.sha256(token.encode()).hexdigest()


class DeviceStore:
    """SQLite-backed device token store."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    platform TEXT NOT NULL DEFAULT '',
                    token_hash TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_seen_at REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_device_token ON devices(token_hash)"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_device_user ON devices(user_email)"
            )

    def register(
        self, user_email: str, name: str = "", platform: str = ""
    ) -> tuple[str, str]:
        """Register a device. Returns (device_id, plaintext_token).

        The plaintext token is shown once — only its hash is stored.
        """
        device_id = secrets.token_hex(8)
        token = f"milo_{secrets.token_urlsafe(32)}"
        now = time.time()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO devices"
                " (id, user_email, name, platform, token_hash,"
                " created_at, last_seen_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    device_id,
                    user_email,
                    name,
                    platform,
                    _hash_token(token),
                    now,
                    now,
                ),
            )
        return device_id, token

    def resolve(self, token: str) -> str | None:
        """Resolve a bearer token to a user email, or None if invalid/revoked."""
        if not token:
            return None
        token_hash = _hash_token(token)
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            row = c.execute(
                "SELECT id, user_email FROM devices WHERE token_hash=? AND revoked=0",
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            # Update last_seen (best-effort)
            c.execute(
                "UPDATE devices SET last_seen_at=? WHERE id=?",
                (time.time(), row["id"]),
            )
            return row["user_email"]

    def list_devices(self, user_email: str) -> list[dict]:
        """List a user's devices (no token hashes exposed)."""
        with sqlite3.connect(self.path) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT id, name, platform, created_at, last_seen_at, revoked"
                " FROM devices WHERE user_email=? ORDER BY created_at DESC",
                (user_email,),
            ).fetchall()
            return [dict(r) for r in rows]

    def revoke(self, user_email: str, device_id: str) -> bool:
        """Revoke a device token. Returns True if a device was revoked."""
        with sqlite3.connect(self.path) as c:
            cur = c.execute(
                "UPDATE devices SET revoked=1 WHERE id=? AND user_email=?",
                (device_id, user_email),
            )
            return cur.rowcount > 0
