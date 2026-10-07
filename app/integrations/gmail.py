# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Gmail integration for milo (Phase 3).

Privacy posture (Nrupal's rule): connect only when a task needs it,
disconnect immediately after. No retention of message content.
Only metadata needed for the task survives; everything else is dropped.

Auth: OAuth tokens via secure storage. Never in code or logs.
"""

from __future__ import annotations


class GmailClient:
    """Scoped Gmail client with privacy-first design."""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials
        self._connected = False

    async def connect(self, user_email: str) -> bool:
        """Establish OAuth connection for a specific task.

        Returns True if connected. Caller must call disconnect() when done.
        """
        # TODO: OAuth flow via secure storage
        # For now, this is a stub that enforces the connect/disconnect pattern
        self._connected = True
        self._user_email = user_email
        return True

    async def disconnect(self):
        """Drop the connection and clear any cached data."""
        self.credentials = None
        self._connected = False
        # No retention: nothing persists beyond the task

    def _require_connected(self):
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search emails. Returns metadata only, not full bodies."""
        self._require_connected()
        # TODO: Implement via Gmail API
        # Returns: [{id, threadId, subject, from, date, snippet}]
        return []

    async def get_thread(self, thread_id: str) -> dict:
        """Get a specific thread. Caller must have explicit need."""
        self._require_connected()
        # TODO: Implement via Gmail API
        return {}

    async def send(
        self, to: str, subject: str, body: str, confirm: bool = False
    ) -> dict:
        """Send email. REQUIRES explicit user confirmation.

        Never send without Nrupal's explicit approval for that specific email.
        """
        self._require_connected()
        if not confirm:
            raise ValueError("Send requires explicit confirmation")
        # TODO: Implement via Gmail API
        return {"status": "not_implemented"}
