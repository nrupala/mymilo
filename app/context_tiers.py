# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Context tiers — two-tier prompt assembly (Engine slice 2).

Implements the CSA/HCA behavior split from ENGINE-SPEC-v1 §3 in the
chat path:

- **HCA tier (global summary):** the session compaction checkpoint,
  injected under a hard token budget. It is the "executive summary"
  layer — always present for long sessions, never growing.
- **CSA tier (sparse details):** per-turn retrieval — the user's
  semantic facts and past-session episodes relevant to *this* message,
  each item capped, the whole tier capped. Details the turn doesn't
  need never enter the prompt.

Assembly order in the chat endpoint (cache-stable first, so llama.cpp
prefix caching can hit): stable system/skill prefix → summary tier →
retrieval tier → dynamic per-turn blocks (date/time, search results)
→ recent history → current turn. Before slice 2 the date/time block
was prepended first and changed every minute, which invalidated the
entire prefix cache on every turn.
"""

from __future__ import annotations

from .tokenplan import CHARS_TOKEN_RATIO, estimate_tokens

# Tier budgets (tokens), from ENGINE-SPEC-v1 §3.
SUMMARY_TIER_BUDGET = 1024
RETRIEVAL_TIER_BUDGET = 2048
RETRIEVAL_ITEM_CAP = 256
FACTS_MAX_ITEMS = 6
EPISODES_MAX_ITEMS = 4

_TRUNCATION_MARK = " …"


def cap_to_tokens(text: str, budget: int) -> str:
    """Truncate text so its estimate fits the token budget.

    Cuts on a word boundary and marks the cut. Returns the text
    unchanged when it already fits.
    """
    if estimate_tokens(text) <= budget:
        return text
    # Budget for content chars, leaving room for the marker.
    char_budget = int((budget - 4) / CHARS_TOKEN_RATIO)
    if char_budget <= 0:
        return _TRUNCATION_MARK.strip()
    cut = text[:char_budget]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip() + _TRUNCATION_MARK


def summary_tier(summary_row: dict | None) -> str | None:
    """Format the compaction checkpoint as the HCA tier block.

    The header names the coverage (checkpoint v2: how many turns the
    summary replaces) so the model — and anyone auditing the prompt —
    can tell compressed context from raw history.
    """
    if not summary_row:
        return None
    text = (summary_row.get("summary") or "").strip()
    if not text:
        return None
    covered = summary_row.get("covered_count") or 0
    if covered:
        header = (
            f"[Earlier in this conversation — checkpoint covering {covered} turns: "
        )
    else:
        header = "[Earlier in this conversation: "
    body_budget = SUMMARY_TIER_BUDGET - estimate_tokens(header) - 1
    return header + cap_to_tokens(text, max(body_budget, 0)) + "]"


def _fact_entries(facts: list[dict], query: str) -> list[tuple[str, dict]]:
    """Rank semantic facts by word overlap with the query (CSA-style).

    Only facts sharing a word with the query are relevant enough to
    spend tokens on; at most FACTS_MAX_ITEMS survive. Each entry is
    (prompt line, source) — the source is what v0.40.0 reports to
    clients as one of the answer's sources.
    """
    query_words = {w for w in query.lower().split() if len(w) > 2}
    scored: list[tuple[int, str]] = []
    for fact in facts:
        key = str(fact.get("key", ""))
        value = str(fact.get("value", ""))
        category = str(fact.get("category", ""))
        haystack = f"{key} {value}".lower()
        overlap = sum(1 for w in query_words if w in haystack)
        if overlap == 0:
            continue
        line = f"- {category}/{key}: {value}" if category else f"- {key}: {value}"
        scored.append((overlap, line))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        (line, {"type": "memory", "title": line[2:][:80]})
        for _, line in scored[:FACTS_MAX_ITEMS]
    ]


def _episode_entries(episodes: list[dict]) -> list[tuple[str, dict]]:
    """Format retrieved episodes, using real preview content.

    The episodic store scores past sessions by keyword overlap and
    returns their first messages as a preview; the snippet is the
    first user turn (what that conversation was about), falling back
    to the first message of any role. Each entry is (prompt line,
    source) for the v0.40.0 sources list.
    """
    entries: list[tuple[str, dict]] = []
    for ep in episodes[:EPISODES_MAX_ITEMS]:
        title = ep.get("title", "Untitled")
        preview = ep.get("preview") or []
        snippet = ""
        for msg in preview:
            if msg.get("role") == "user" and msg.get("content"):
                snippet = msg["content"]
                break
        if not snippet and preview:
            snippet = preview[0].get("content", "")
        snippet = " ".join(snippet.split())  # collapse whitespace
        if snippet:
            line = f"[Past: {title}] {snippet}"
        else:
            line = f"[Past: {title}]"
        entries.append((line, {"type": "past chat", "title": title}))
    return entries


def retrieval_tier(
    episodes: list[dict], facts: list[dict], query: str = ""
) -> tuple[str | None, list[dict]]:
    """Assemble the CSA tier block under its budgets.

    Each item is capped at RETRIEVAL_ITEM_CAP tokens; items are added
    (facts first — they are denser) until the tier budget is reached.
    Returns (block_text, sources): the sources name the memory the
    block actually used, for the v0.40.0 response `sources` list.
    (None, []) when nothing was relevant.
    """
    items = _fact_entries(facts, query) + _episode_entries(episodes)
    if not items:
        return None, []
    header = "Relevant context from memory:"
    chosen: list[tuple[str, dict]] = []
    used = estimate_tokens(header)
    for line, source in items:
        capped = cap_to_tokens(line, RETRIEVAL_ITEM_CAP)
        cost = estimate_tokens(capped)
        if used + cost > RETRIEVAL_TIER_BUDGET:
            break
        chosen.append((capped, source))
        used += cost
    if not chosen:
        return None, []
    text = header + "\n" + "\n".join(line for line, _ in chosen)
    return text, [source for _, source in chosen]


def dynamic_insert_index(messages: list[dict]) -> int:
    """Index where dynamic per-turn blocks belong in the assembly.

    Dynamic blocks (date/time grounding, search results) go after the
    entire stable system prefix — everything cacheable stays in front
    of everything that changes per turn.
    """
    for i, msg in enumerate(messages):
        if msg.get("role") != "system":
            return i
    return len(messages)
