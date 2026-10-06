"""In-process event bus.

Events are plain dicts with a ``type`` key. The bus is synchronous and
in-process: it exists so the deterministic planner (not the LLM) decides
what happens when something occurs. There is no hidden async delivery and
no persistence — events that matter are recorded as job runs or
suggestions in the database by their handlers.

Standard event types (see planner for the rules that consume them):

- ``JOB_DUE``        — a job's ``next_run_at`` has been reached.
- ``JOB_COMPLETED``  — a job finished; payload carries the run record.
- ``JOB_FAILED``     — a job raised; payload carries the error.
- ``DOCUMENT_ADDED`` — a document was ingested.
- ``SUGGESTION_CREATED`` — a suggestion was recorded.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

Handler = Callable[[dict[str, Any]], None]


class EventBus:
    """Tiny synchronous pub/sub bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}

    def on(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit_async(
        self, event_type: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Emit an event, awaiting handlers that return awaitables."""
        event: dict[str, Any] = {"type": event_type}
        if payload:
            event.update(payload)
        for handler in self._handlers.get(event_type, []):
            result = handler(event)
            if inspect.isawaitable(result):
                await result
        return event

    def emit(
        self, event_type: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        event: dict[str, Any] = {"type": event_type}
        if payload:
            event.update(payload)
        for handler in self._handlers.get(event_type, []):
            handler(event)
        return event

    def clear(self) -> None:
        self._handlers.clear()
