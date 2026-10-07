# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Phase 2: Milo → Wright escalation.

When a request exceeds Milo's local capability, it packages context
and queues an escalation for Wright. Wright processes the queue
(via cron) and writes back results. Milo polls for completion.

This is the "foreman" pattern: Milo recognizes what it can't do,
Wright does the deep work, Milo delivers the result.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


class EscalationQueue:
    """File-based escalation queue. Simple, reliable, no new deps."""

    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir = self.queue_dir / "pending"
        self.done_dir = self.queue_dir / "done"
        self.pending_dir.mkdir(exist_ok=True)
        self.done_dir.mkdir(exist_ok=True)

    def submit(
        self,
        user_email: str,
        request: str,
        context: dict[str, Any],
        session_id: str,
    ) -> str:
        """Queue an escalation. Returns escalation ID."""
        esc_id = uuid.uuid4().hex[:12]
        payload = {
            "id": esc_id,
            "user_email": user_email,
            "request": request,
            "context": context,
            "session_id": session_id,
            "submitted_at": time.time(),
            "status": "pending",
        }
        (self.pending_dir / f"{esc_id}.json").write_text(json.dumps(payload, indent=2))
        return esc_id

    def get_result(self, esc_id: str) -> dict[str, Any] | None:
        """Check for a completed escalation result."""
        done_file = self.done_dir / f"{esc_id}.json"
        if done_file.exists():
            return json.loads(done_file.read_text())
        return None

    def list_pending(self) -> list[dict[str, Any]]:
        """List all pending escalations (for Wright's cron)."""
        result = []
        for f in self.pending_dir.glob("*.json"):
            try:
                result.append(json.loads(f.read_text()))
            except Exception:
                continue
        return sorted(result, key=lambda x: x.get("submitted_at", 0))

    def complete(self, esc_id: str, result: str, metadata: dict | None = None):
        """Mark an escalation as complete with Wright's result."""
        pending_file = self.pending_dir / f"{esc_id}.json"
        if not pending_file.exists():
            return False
        payload = json.loads(pending_file.read_text())
        payload["status"] = "done"
        payload["result"] = result
        payload["completed_at"] = time.time()
        if metadata:
            payload["metadata"] = metadata
        (self.done_dir / f"{esc_id}.json").write_text(json.dumps(payload, indent=2))
        pending_file.unlink()
        return True
