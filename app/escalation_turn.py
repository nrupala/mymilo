# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Per-turn escalation detection + model-aware context.

Milo detects during each chat turn whether the request needs Wright.
If so, it queues an escalation and tells the user.
Context is tailored to the model's capabilities (window size, etc.).
"""

from __future__ import annotations

from typing import Any

# Explicit triggers for Wright escalation
WRIGHT_TRIGGERS = [
    "ask wright",
    "get wright",
    "wright,",
    "let wright",
    "have wright",
    "wants wright",
]

# Complexity signals that suggest Wright is needed
WRIGHT_COMPLEXITY_SIGNALS = [
    "research",
    "analyze",
    "investigate",
    "deep dive",
    "write code",
    "build",
    "create a",
    "design a",
    "plan",
    "strategy",
    "compare",
    "evaluate",
]

# Model context windows (tokens)
MODEL_CONTEXT_WINDOWS = {
    "local": 4096,  # Phi-4-mini
    "deepseek": 64000,
    "openrouter": 128000,
    "cloud": 128000,
}


def should_escalate_to_wright(
    message: str, active_skill: str | None = None
) -> tuple[bool, str]:
    """Determine if a message should escalate to Wright.

    Returns (should_escalate, reason).
    """
    lowered = message.lower()

    # Explicit triggers
    for trigger in WRIGHT_TRIGGERS:
        if trigger in lowered:
            return True, f"explicit trigger: '{trigger}'"

    # Complexity: long messages with multiple questions or deep work signals
    complexity_score = 0
    if len(message) > 500:
        complexity_score += 1
    if message.count("?") > 2:
        complexity_score += 1
    for signal in WRIGHT_COMPLEXITY_SIGNALS:
        if signal in lowered:
            complexity_score += 1
            break

    # High complexity + no active skill = likely needs Wright
    if complexity_score >= 2 and not active_skill:
        return True, f"high complexity (score {complexity_score}), no active skill"

    return False, ""


def get_context_budget(model: str) -> int:
    """Get context window size for a model, reserving 20% for output."""
    window = MODEL_CONTEXT_WINDOWS.get(model, 4096)
    return int(window * 0.8)


def build_model_aware_context(
    base_context: dict[str, Any],
    model: str,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Trim context to fit the model's window.

    Prioritizes: system prompt > recent messages > skills > memory > docs
    """
    budget = max_tokens or get_context_budget(model)

    # TODO: Implement actual token counting and trimming
    # For now, return as-is with budget metadata
    base_context["_model"] = model
    base_context["_context_budget"] = budget
    return base_context
