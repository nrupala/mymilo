# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Episodic memory: session summaries + search.

Milo remembers what happened in past sessions, not just the current one.
Summaries are generated when sessions end or grow long.
Search finds relevant past episodes.
"""

from __future__ import annotations

from typing import Any


class EpisodicMemory:
    """Session summaries and cross-session search."""

    def __init__(self, memory_store: Any):
        self.store = memory_store

    async def summarize_session(self, session_id: str, model_client: Any = None) -> str:
        """Generate a summary of a session's key points.

        Uses the local model if available, otherwise extracts key sentences.
        """
        messages = self.store.get_messages(session_id, limit=100)
        if not messages:
            return "Empty session."

        # Extract user questions and key assistant responses
        key_points = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")[:200]  # Truncate
            if role == "user":
                key_points.append(f"Q: {content}")
            elif role == "assistant" and len(content) > 50:
                # Only substantive responses
                key_points.append(f"A: {content[:150]}...")

        # Simple extractive summary (v1)
        # TODO: Use model for abstractive summary when available
        summary = f"Session with {len(messages)} messages. "
        summary += f"Key topics: {', '.join(key_points[:5])}"
        return summary[:1000]

    def search_sessions(
        self, user_email: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Search past sessions for relevant episodes.

        v1: keyword matching. v2: vector search when embeddings stable.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        sessions = self.store.list_sessions(user_email, limit=50)
        scored = []

        for session in sessions:
            session_id = session["id"]
            messages = self.store.get_messages(session_id, limit=50)

            # Score by keyword overlap
            text = " ".join(m.get("content", "").lower() for m in messages)
            text_words = set(text.split())
            overlap = len(query_words & text_words)

            if overlap > 0:
                scored.append((overlap, session, messages[:3]))

        # Sort by score, return top
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "session_id": s["id"],
                "title": s.get("title", "Untitled"),
                "score": score,
                "preview": msgs,
            }
            for score, s, msgs in scored[:limit]
        ]

    async def get_relevant_history(
        self,
        user_email: str,
        current_message: str,
        max_episodes: int = 3,
    ) -> list[dict]:
        """Get past episodes relevant to the current message."""
        episodes = self.search_sessions(user_email, current_message, limit=max_episodes)

        # Add summaries for each
        for ep in episodes:
            # TODO: Cache summaries in DB
            ep["summary"] = f"Past session: {ep['title']}"

        return episodes
