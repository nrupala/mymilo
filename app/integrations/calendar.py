# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Google Calendar integration for milo (Phase 3).

Privacy posture: same as Gmail — connect per task, disconnect after,
no retention beyond what's needed for the immediate task.
"""

from __future__ import annotations

from datetime import datetime


class CalendarClient:
    """Scoped Calendar client with privacy-first design."""

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials
        self._connected = False

    async def connect(self, user_email: str) -> bool:
        """Establish OAuth connection for a specific task."""
        self._connected = True
        self._user_email = user_email
        return True

    async def disconnect(self):
        """Drop connection, clear cached data."""
        self.credentials = None
        self._connected = False

    def _require_connected(self):
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

    async def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 20,
    ) -> list[dict]:
        """List calendar events in a time range."""
        self._require_connected()
        # TODO: Implement via Calendar API
        # Returns: [{id, summary, start, end, location, description}]
        return []

    async def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
        confirm: bool = False,
    ) -> dict:
        """Create calendar event. REQUIRES explicit user confirmation."""
        self._require_connected()
        if not confirm:
            raise ValueError("Create requires explicit confirmation")
        # TODO: Implement via Calendar API
        return {"status": "not_implemented"}
