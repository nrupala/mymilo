# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Token planner — DeepSeek-style token discipline for local backends.

Implements the planning formula from the Token-Efficiency Engine spec
(docs: ENGINE-SPEC-v1, slice 1):

    remaining = window - estimated_input - margin
    planned_max_tokens = min(desired_output, route_cap, remaining)

Rules the planner enforces:

- Every chat request leaves with an explicit ``max_tokens`` — never a
  backend default.
- A request whose estimated input cannot fit the route's context
  window is reshaped (oldest non-system turns trimmed) or refused
  *before* sending, so llama.cpp never silently truncates an
  over-length prompt (the n_ctx guard).
- Estimation prefers the backend's own tokenizer (llama.cpp
  ``/tokenize``) for local routes and falls back to a calibrated
  character estimator everywhere else. Calibration of the estimator
  against actual usage lands with the telemetry slice.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import httpx

from .config import ModelRoute

# Estimator constants (DeepSeek doc ratios: ~0.3 token per English
# character). Code and dense formatting tokenize heavier; the planning
# margin below is what absorbs that error until calibration lands.
CHARS_TOKEN_RATIO = 0.30
MESSAGE_OVERHEAD_TOKENS = 4
MARGIN_FLOOR_TOKENS = 256
MARGIN_WINDOW_FRACTION = 0.05
MIN_USEFUL_OUTPUT_TOKENS = 64
DEFAULT_DESIRED_OUTPUT = 1024

_TOKENIZE_CACHE: dict[tuple[str, str], int] = {}
_TOKENIZE_CACHE_MAX = 1024


def estimate_tokens(text: str) -> int:
    """Character-based token estimate for one text blob."""
    if not text:
        return 0
    return math.ceil(len(text) * CHARS_TOKEN_RATIO)


def _content_text(content: object) -> str:
    """Extract text from a message content (str or part list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    return ""


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate the prompt token count of a chat message list."""
    total = 0
    for msg in messages:
        total += estimate_tokens(_content_text(msg.get("content")))
        total += MESSAGE_OVERHEAD_TOKENS
    return total


def _tokenize_root(base_url: str) -> str:
    """llama.cpp serves /tokenize at the server root, not under /v1."""
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    return root


def _is_local_route(route: ModelRoute) -> bool:
    url = route.base_url
    return "127.0.0.1" in url or "localhost" in url


async def count_tokens_backend(
    route: ModelRoute,
    text: str,
    transport: httpx.BaseTransport | None = None,
) -> int | None:
    """Exact token count from the backend tokenizer, or None.

    Only attempted for local routes (llama.cpp /tokenize). Results are
    cached by content hash; any failure returns None so the caller can
    fall back to the estimator — counting must never break a request.
    """
    if not text or not _is_local_route(route):
        return None
    key = (route.name, hashlib.sha256(text.encode()).hexdigest())
    cached = _TOKENIZE_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=1.5, trust_env=False
        ) as client:
            resp = await client.post(
                f"{_tokenize_root(route.base_url)}/tokenize",
                json={"content": text, "with_pieces": False},
            )
        if resp.status_code != 200:
            return None
        tokens = resp.json().get("tokens")
        if not isinstance(tokens, list):
            return None
        count = len(tokens)
    except Exception:  # noqa: BLE001 — counting is best-effort
        return None
    if len(_TOKENIZE_CACHE) >= _TOKENIZE_CACHE_MAX:
        _TOKENIZE_CACHE.clear()
    _TOKENIZE_CACHE[key] = count
    return count


async def estimate_input_tokens(
    route: ModelRoute,
    messages: list[dict],
    transport: httpx.BaseTransport | None = None,
) -> tuple[int, str]:
    """Best available input estimate: (count, source).

    Source is "tokenizer" when the backend counted exactly, else
    "estimate". The tokenizer path counts the joined message text;
    per-message overhead is added either way.
    """
    joined = "\n".join(_content_text(m.get("content")) for m in messages)
    exact = await count_tokens_backend(route, joined, transport=transport)
    overhead = MESSAGE_OVERHEAD_TOKENS * len(messages)
    if exact is not None:
        return exact + overhead, "tokenizer"
    return estimate_messages_tokens(messages), "estimate"


@dataclass
class TokenPlan:
    route: str
    window: int | None
    estimated_input: int
    estimate_source: str
    margin: int
    desired_output: int
    planned_max_tokens: int
    fits: bool
    trimmed_messages: int = 0

    @property
    def utilization(self) -> float | None:
        """Estimated share of the window the input occupies (0..1)."""
        if not self.window:
            return None
        return round(self.estimated_input / self.window, 4)

    def as_dict(self) -> dict:
        return {
            "route": self.route,
            "window": self.window,
            "estimated_input": self.estimated_input,
            "estimate_source": self.estimate_source,
            "margin": self.margin,
            "desired_output": self.desired_output,
            "planned_max_tokens": self.planned_max_tokens,
            "fits": self.fits,
            "trimmed_messages": self.trimmed_messages,
            "utilization": self.utilization,
        }


def plan_max_tokens(
    route: ModelRoute,
    estimated_input: int,
    desired: int | None = None,
    estimate_source: str = "estimate",
) -> TokenPlan:
    """Apply the planning formula for one request on one route.

    Routes without a configured window are unplanned: the desired
    output (or route default) passes through and everything "fits" —
    the planner only guards windows it knows.
    """
    desired_output = desired or route.default_max_tokens or DEFAULT_DESIRED_OUTPUT
    window = route.context_window
    if not window:
        return TokenPlan(
            route=route.name,
            window=None,
            estimated_input=estimated_input,
            estimate_source=estimate_source,
            margin=0,
            desired_output=desired_output,
            planned_max_tokens=desired_output,
            fits=True,
        )
    margin = max(MARGIN_FLOOR_TOKENS, math.ceil(window * MARGIN_WINDOW_FRACTION))
    remaining = window - estimated_input - margin
    cap = route.max_output_tokens or desired_output
    fits = remaining >= MIN_USEFUL_OUTPUT_TOKENS
    planned = min(desired_output, cap, remaining) if fits else 0
    return TokenPlan(
        route=route.name,
        window=window,
        estimated_input=estimated_input,
        estimate_source=estimate_source,
        margin=margin,
        desired_output=desired_output,
        planned_max_tokens=planned,
        fits=fits,
    )


def trim_messages_to_fit(
    messages: list[dict], token_budget: int
) -> tuple[list[dict], int]:
    """Drop oldest droppable turns until the estimate fits the budget.

    System messages are never dropped (they carry rules and skills),
    and the final message (the current user turn) is never dropped.
    Chat payloads here are plain role/content turns — there are no
    tool call/result pairs to keep atomic on this surface.
    Returns (messages, dropped_count). If nothing droppable remains,
    returns what is left; the caller re-plans and refuses if needed.
    """
    result = list(messages)
    dropped = 0
    while estimate_messages_tokens(result) > token_budget:
        idx = next(
            (i for i, m in enumerate(result[:-1]) if m.get("role") != "system"),
            None,
        )
        if idx is None:
            break
        result.pop(idx)
        dropped += 1
    return result, dropped
