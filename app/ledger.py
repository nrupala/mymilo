# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Fleet economics: cost math, quota flags, cost-aware route ranking.

Phase 4 (maven transfer #6 — lifecycle/economics discipline, re-homed).

- Every model call is recorded in the ``ledger`` table with token usage
  (when the backend reports it) and computed USD cost. Missing usage is
  stored as NULL — never estimated silently.
- Routes may declare a monthly free quota (USD). Crossing 70% raises a
  ``QUOTA_WARNING`` event (once per threshold per month); crossing 100%
  raises ``QUOTA_EXHAUSTED``. The planner turns these into suggestions.
- :func:`recommend` ranks routes local-first, then free-tier with remaining
  quota, then paid by rate. It *informs* — the chat endpoint keeps
  exact-name routing, so nothing ever silently spends.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

QUOTA_WARN_THRESHOLD = 0.7
QUOTA_EXHAUSTED_THRESHOLD = 1.0


def current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def compute_cost(
    prompt_tokens: int | None,
    completion_tokens: int | None,
    input_usd_per_1k: float,
    output_usd_per_1k: float,
) -> float | None:
    """USD cost for a call, or None when usage is unknown.

    Zero-rate routes always cost exactly 0.0 (even with unknown usage —
    local inference is free regardless of token counts).
    """
    if input_usd_per_1k == 0.0 and output_usd_per_1k == 0.0:
        return 0.0
    if prompt_tokens is None or completion_tokens is None:
        return None
    return (
        prompt_tokens / 1000 * input_usd_per_1k
        + completion_tokens / 1000 * output_usd_per_1k
    )


def month_spend(db: Any, route_name: str, month: str | None = None) -> float:
    month = month or current_month()
    for row in db.ledger_monthly_summary(month):
        if row["route"] == route_name:
            return float(row["cost_usd"])
    return 0.0


async def check_quota(db: Any, bus: Any, route: Any) -> dict[str, Any] | None:
    """Flag free-quota thresholds; emit planner events on first crossing.

    Returns the flag dict when a new threshold was crossed, else None.
    """
    quota = route.free_quota_usd
    if not quota or quota <= 0:
        return None
    month = current_month()
    spent = month_spend(db, route.name, month)
    ratio = spent / quota
    crossed: float | None = None
    if ratio >= QUOTA_EXHAUSTED_THRESHOLD:
        crossed = QUOTA_EXHAUSTED_THRESHOLD
    elif ratio >= QUOTA_WARN_THRESHOLD:
        crossed = QUOTA_WARN_THRESHOLD
    if crossed is None or db.quota_flagged(route.name, month, crossed):
        return None
    db.mark_quota_flagged(route.name, month, crossed)
    event_type = "QUOTA_EXHAUSTED" if crossed >= 1.0 else "QUOTA_WARNING"
    await bus.emit_async(
        event_type,
        {
            "db": db,
            "route": route.name,
            "month": month,
            "spent_usd": round(spent, 4),
            "quota_usd": quota,
            "pct": round(ratio * 100, 1),
            "title": (
                f"Free quota exhausted on '{route.name}'"
                if crossed >= 1.0
                else f"Free quota 70% used on '{route.name}'"
            ),
            "body": (
                f"Route '{route.name}' has spent ${spent:.4f} of its "
                f"${quota:.2f} monthly free quota ({ratio * 100:.1f}%). "
                "Further calls may bill at the paid rate."
                if crossed >= 1.0
                else f"Route '{route.name}' has used {ratio * 100:.1f}% of its "
                f"${quota:.2f} monthly free quota (${spent:.4f} spent). "
                "Heads-up before it starts billing."
            ),
        },
    )
    return {"route": route.name, "threshold": crossed, "pct": round(ratio * 100, 1)}


def recommend(routes: list[Any]) -> list[Any]:
    """Rank routes: free first, then free-quota remaining, then paid by rate.

    Informational only — callers (UI, future OS scheduler) choose; the
    chat endpoint never reroutes on its own.
    """

    def rank(route: Any) -> tuple:
        free = route.input_usd_per_1k == 0.0 and route.output_usd_per_1k == 0.0
        if free:
            return (0, 0.0, route.name)
        if route.free_quota_usd:
            return (1, 0.0, route.name)
        rate = route.input_usd_per_1k + route.output_usd_per_1k
        return (2, rate, route.name)

    return sorted(routes, key=rank)
