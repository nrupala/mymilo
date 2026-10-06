# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Deterministic proactive planner.

The planner is the *only* decision-maker for autonomous behavior. It is a
rule table, not a model:

- Events arrive on the :class:`EventBus` (job due, document added, ...).
- Rules match ``(event type, predicate)`` pairs deterministically.
- Matching rules invoke named actions from the consent-gated registry.

The LLM is a *reasoner*, never the decider: a briefing job may ask the
model to draft the digest text, but whether the briefing runs, when it
runs, and what it is allowed to do are all decided here, in plain code
that can be read, tested, and audited.

Suggested-but-not-taken behavior surfaces as ``SUGGESTION_CREATED``
events, which become rows in the ``suggestions`` table for the user to
accept or dismiss. Nothing autonomous hides.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .actions import ActionRegistry
from .events import EventBus

Predicate = Callable[[dict[str, Any]], bool]


@dataclass
class Rule:
    name: str
    event_type: str
    predicate: Predicate
    action_name: str
    action_params: dict[str, Any] = field(default_factory=dict)

    def matches(self, event: dict[str, Any]) -> bool:
        return event["type"] == self.event_type and self.predicate(event)


def _always(_event: dict[str, Any]) -> bool:
    return True


class Planner:
    """Holds the rule table and routes events to consent-gated actions."""

    def __init__(self, bus: EventBus, actions: ActionRegistry) -> None:
        self.bus = bus
        self.actions = actions
        self.rules: list[Rule] = []
        self._wire_defaults()
        for rule in self.rules:
            bus.on(rule.event_type, self._make_handler(rule))

    # ------------------------------------------------------------------
    # Rule table
    # ------------------------------------------------------------------
    def _wire_defaults(self) -> None:
        # A due job is executed — through the action registry, so consent
        # policy applies even to the scheduler's own work.
        self.rules.append(
            Rule(
                name="run-due-job",
                event_type="JOB_DUE",
                predicate=_always,
                action_name="job.execute",
            )
        )
        # A finished briefing or reminder becomes a suggestion to read.
        for job_type in ("briefing", "reminder"):
            self.rules.append(
                Rule(
                    name=f"{job_type}-to-suggestion",
                    event_type="JOB_COMPLETED",
                    predicate=lambda e, jt=job_type: e.get("job_type") == jt,
                    action_name="suggestion.create",
                )
            )
        # A newly indexed document is worth a quiet heads-up, not an
        # interruption: a suggestion, never an autonomous action.
        self.rules.append(
            Rule(
                name="document-added-note",
                event_type="DOCUMENT_ADDED",
                predicate=_always,
                action_name="suggestion.create",
                action_params={"kind": "note"},
            )
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def _make_handler(self, rule: Rule):
        async def handler(event: dict[str, Any]) -> None:
            if not rule.matches(event):
                return
            db = event["db"]
            params = dict(rule.action_params)
            params["event"] = event
            await self.actions.execute_async(db, rule.action_name, **params)

        return handler

    def add_rule(self, rule: Rule) -> None:
        """Add a rule at runtime (used by tests and future config)."""
        self.rules.append(rule)
        self.bus.on(rule.event_type, self._make_handler(rule))


def create_suggestion(
    db: Any,
    title: str = "",
    body: str = "",
    kind: str = "",
    job_run_id: int | None = None,
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``suggestion.create`` action handler: record a suggestion row.

    When invoked by the planner the event carries everything needed, so
    rules can pass only ``kind`` (or nothing at all).
    """
    event = event or {}
    etype = event.get("type", "")
    if etype == "DOCUMENT_ADDED":
        kind = kind or "note"
        title = title or "Document indexed"
        chunks = event.get("chunks", 0)
        body = body or (
            f"{event.get('filename', 'A document')} was indexed "
            f"({chunks} chunks) and is now searchable."
        )
    elif etype == "JOB_COMPLETED":
        kind = kind or str(event.get("job_type") or "briefing")
        title = title or f"{event.get('job_name', 'Job')} finished"
        body = body or str(event.get("result_summary") or "")
        if job_run_id is None:
            job_run_id = event.get("run_id")
    kind = kind or "note"
    title = title or "Suggestion"
    suggestion_id = db.create_suggestion(
        kind=kind, title=title, body=body, job_run_id=job_run_id
    )
    return {"id": suggestion_id, "kind": kind, "title": title}
