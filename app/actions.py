# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Consent-gated action registry.

Every side-effecting capability MyMilo exposes is declared here with:

- ``name`` — stable identifier (e.g. ``job.execute``).
- ``risk`` — one of ``low``, ``medium``, ``high``.
- ``requires_confirm`` — whether first use needs explicit consent.
- ``handler`` — the callable performing the work (sync or async).

Policy:

- ``low``-risk actions run freely.
- ``medium``/``high``-risk actions, and any action with
  ``requires_confirm=True``, need a consent row in the ``consents`` table.
  Consent is *confirm-once*: granting it once remembers the decision until
  revoked.

The LLM never executes an action directly: it may *propose* one, but the
deterministic planner (``app/planner.py``) is the only caller of
:func:`execute_async`, and it consults this registry's policy first.

This is the seam Phase 5's riskier tools (``shell.exec``, ``browser.*``)
will plug into — they will register here as ``high`` risk.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

VALID_RISKS = ("low", "medium", "high")

Handler = Callable[..., Any]


class ConsentRequired(Exception):
    """Raised when an action needs consent that has not been granted."""


@dataclass
class Action:
    name: str
    risk: str
    requires_confirm: bool
    description: str
    handler: Handler = field(repr=False)


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(
        self,
        name: str,
        handler: Handler,
        risk: str = "low",
        requires_confirm: bool = False,
        description: str = "",
    ) -> Action:
        if risk not in VALID_RISKS:
            raise ValueError(f"risk must be one of {VALID_RISKS}, got {risk!r}")
        action = Action(
            name=name,
            risk=risk,
            requires_confirm=requires_confirm,
            description=description,
            handler=handler,
        )
        self._actions[name] = action
        return action

    def get(self, name: str) -> Action:
        try:
            return self._actions[name]
        except KeyError:
            raise KeyError(f"unknown action {name!r}") from None

    def list(self) -> list[Action]:
        return sorted(self._actions.values(), key=lambda a: a.name)

    def check_policy(self, db: Any, action: Action) -> None:
        """Raise ConsentRequired if policy blocks execution."""
        if action.risk == "low" and not action.requires_confirm:
            return
        if not db.consent_granted(action.name):
            raise ConsentRequired(
                f"action {action.name!r} (risk={action.risk}) requires consent; "
                "grant it via POST /v1/consents first"
            )

    async def execute_async(self, db: Any, name: str, **params: Any) -> Any:
        """Policy-check then run the handler, awaiting it if async."""
        action = self.get(name)
        self.check_policy(db, action)
        result = action.handler(db=db, **params)
        if inspect.isawaitable(result):
            result = await result
        return result
