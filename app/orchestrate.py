# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Background orchestration for Milo (v0.8.0).

Two pieces:
1. Auto-routing: pick local vs cloud based on query complexity.
2. Background tasks: long work runs as jobs, results land in chat.
"""

from __future__ import annotations

from typing import Any

# Phrases that trigger background execution.
BACKGROUND_TRIGGERS = [
    "in the background",
    "take your time",
    "when it's done",
    "when it is done",
    "research this",
    "look into this",
    "work on this",
]

# Signals that a query wants the stronger cloud brain.
CLOUD_SIGNALS = [
    "research",
    "analyze deeply",
    "thorough",
    "compare",
    "in detail",
    "comprehensive",
    "deep dive",
    # Freshness signals: local model can't know these, escalate to cloud
    # (which pairs with web search when available).
    "latest",
    "news",
    "today",
    "current",
    "real-time",
    "realtime",
]


def wants_background(message: str) -> bool:
    """Check if the user wants this run in the background."""
    lowered = message.lower()
    return any(t in lowered for t in BACKGROUND_TRIGGERS)


def route_for_complexity(message: str, settings: Any, default: str = "local") -> str:
    """Pick a model route based on query complexity.

    Simple/short -> local (fast, free, private).
    Complex/long or explicit cloud signals -> first available cloud route.
    Falls back to default when no cloud route is configured.
    """
    cloud_routes = [
        m.name
        for m in settings.models
        if m.name in ("deepseek", "openrouter", "cloud") and settings.api_key_for(m)
    ]
    if not cloud_routes:
        return default
    lowered = message.lower()
    is_complex = (
        len(message) > 300
        or any(s in lowered for s in CLOUD_SIGNALS)
        or message.count("?") > 2
    )
    if is_complex:
        return cloud_routes[0]
    return default


def plan_steps(task: str) -> list[str]:
    """Break a task into steps (simple planner v1).

    v1 is sequential and heuristic. The planner model (cloud when available)
    will do smarter decomposition in v0.9.
    """
    # For now: single-step with skill context. Multi-step decomposition
    # arrives when the planner model is wired.
    return [task]
