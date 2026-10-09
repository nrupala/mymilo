# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Summarization for long chats (v0.28.0).

When a chat gets long, old turns compress into a summary so the local
model's small window doesn't choke. The summary is stored per-session
and injected as context instead of the raw old messages.

Threshold: summarize when a session exceeds 30 messages.
Keep the most recent 20 messages raw; summarize everything older.
"""

from __future__ import annotations

from typing import Any

# Summarize when a session has more than this many messages
SUMMARIZE_THRESHOLD = 30
# Keep this many recent messages raw (not summarized)
RECENT_KEEP = 20


# Sessions with a summarization currently running (Engine slice 3).
# The chat endpoint fires this as a background task on every turn of a
# long session; without the guard, concurrent runs chain off each
# other's checkpoints and the coverage accounting degrades.
_IN_FLIGHT: set[str] = set()


async def maybe_summarize_session(
    memory: Any,
    router: Any,
    session_id: str,
) -> dict | None:
    """Check if a session needs summarization, and do it if so.

    Returns the summary dict if a new summary was created, None
    otherwise — including when a run for this session is already in
    flight (the next turn picks up whatever remains).
    """
    if session_id in _IN_FLIGHT:
        return None
    _IN_FLIGHT.add(session_id)
    try:
        return await _summarize_once(memory, router, session_id)
    finally:
        _IN_FLIGHT.discard(session_id)


async def _summarize_once(
    memory: Any,
    router: Any,
    session_id: str,
) -> dict | None:
    count = memory.count_messages(session_id)
    if count < SUMMARIZE_THRESHOLD:
        return None

    existing = memory.get_summary(session_id)
    max_id = memory.get_max_message_id(session_id)

    # If we already summarized up to near the current max, skip
    if existing and existing["summarized_up_to"] >= max_id - RECENT_KEEP:
        return None

    # Get the messages to summarize: everything older than the recent window
    # Find the cutoff: the id of the (RECENT_KEEP)th message from the end
    cutoff_id = max_id - RECENT_KEEP
    if cutoff_id <= 0:
        return None

    # If we have an existing summary, only summarize the new unsummarized part
    start_from = existing["summarized_up_to"] if existing else 0
    if start_from >= cutoff_id:
        return None

    old_messages = memory.get_messages_before(session_id, cutoff_id, limit=100)
    # Filter to only the unsummarized portion
    old_messages = [m for m in old_messages if m["id"] > start_from]
    if not old_messages:
        return None

    # Build the summarization prompt
    transcript = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in old_messages)

    prev_summary = ""
    if existing:
        prev_summary = f"Previous summary:\n{existing['summary']}\n\n"

    prompt = (
        f"{prev_summary}Summarize the following conversation turns concisely. "
        "Capture the key topics discussed, decisions made, and important facts. "
        "Be brief but complete — this summary replaces the full transcript "
        "in the model's context.\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Summary:"
    )

    try:
        result = await router.chat_completion(
            "local",
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You summarize conversations concisely.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
            },
        )
        summary_text = (
            result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        )
        if not summary_text:
            return None

        # Checkpoint v2 coverage is cumulative (slice 3 fix): chain
        # from the previous checkpoint so the recorded coverage always
        # states how many turns the current summary embodies in total,
        # not just the latest slice.
        prev_from = (existing or {}).get("covered_from")
        if prev_from is None:
            prev_from = start_from
        prev_count = (existing or {}).get("covered_count") or 0
        memory.save_summary(
            session_id,
            summary_text,
            cutoff_id,
            covered_from=prev_from,
            covered_count=prev_count + len(old_messages),
            model="local",
        )
        return {
            "summary": summary_text,
            "summarized_up_to": cutoff_id,
        }
    except Exception:
        # Summarization is best-effort; never break the chat flow
        return None


def get_summary_context(memory: Any, session_id: str) -> str:
    """Get the summary as a context string for injection, or empty.

    Formatted as the HCA tier (Engine slice 2): checkpoint header with
    coverage, hard-capped at the tier budget.
    """
    from .context_tiers import summary_tier

    summary = memory.get_summary(session_id)
    if not summary:
        return ""
    return summary_tier(summary) or ""
