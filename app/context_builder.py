# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Unified context builder.

Assembles all context sources into a coherent prompt for the model:
1. System prompt (highest priority, never trimmed)
2. Active skill instructions
3. Current session history (recent turns)
4. Episodic memory (relevant past sessions)
5. RAG documents (if enabled)
6. Current user message

Budget-aware: trims lower-priority sources to fit the model's window.
"""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    """Builds unified context for model calls."""

    def __init__(self, budget_tokens: int = 3200):
        self.budget = budget_tokens
        # Rough token estimates (v1: char/4)
        self.system_reserve = 800
        self.skill_reserve = 600

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate. v1: chars/4. TODO: use tiktoken."""
        return len(text) // 4

    def build(
        self,
        system_prompt: str,
        user_message: str,
        history: list[dict] | None = None,
        skill_instructions: str | None = None,
        episodes: list[dict] | None = None,
        rag_docs: list[dict] | None = None,
    ) -> list[dict]:
        """Build the message list for the model.

        Returns messages in order, trimmed to budget.
        """
        messages = []

        # 1. System prompt (never trimmed)
        messages.append({"role": "system", "content": system_prompt})
        used = self.estimate_tokens(system_prompt)

        # 2. Skill instructions (high priority)
        if skill_instructions:
            skill_tokens = self.estimate_tokens(skill_instructions)
            if used + skill_tokens < self.budget:
                messages.append(
                    {"role": "system", "content": f"Skill: {skill_instructions}"}
                )
                used += skill_tokens

        # 3. Episodic memory (past sessions)
        if episodes:
            for ep in episodes:
                ep_text = f"[Past: {ep.get('title', '?')}] {ep.get('summary', '')}"
                ep_tokens = self.estimate_tokens(ep_text)
                if used + ep_tokens < self.budget * 0.9:  # Reserve 10% for history+msg
                    messages.append({"role": "system", "content": ep_text})
                    used += ep_tokens
                else:
                    break

        # 4. RAG documents
        if rag_docs:
            for doc in rag_docs:
                doc_text = doc.get("content", "")[:500]
                doc_tokens = self.estimate_tokens(doc_text)
                if used + doc_tokens < self.budget * 0.85:
                    messages.append(
                        {"role": "system", "content": f"Document: {doc_text}"}
                    )
                    used += doc_tokens
                else:
                    break

        # 5. History (recent turns, trimmed from oldest)
        if history:
            # Add from most recent backwards until budget
            hist_to_add = []
            for msg in reversed(history):
                msg_tokens = self.estimate_tokens(msg.get("content", ""))
                if used + msg_tokens < self.budget * 0.95:
                    hist_to_add.insert(0, msg)
                    used += msg_tokens
                else:
                    break
            # Insert after system messages
            insert_at = len([m for m in messages if m["role"] == "system"])
            messages[insert_at:insert_at] = hist_to_add

        # 6. Current user message (always included)
        messages.append({"role": "user", "content": user_message})

        return messages

    def get_stats(self) -> dict[str, Any]:
        """Return builder configuration."""
        return {
            "budget_tokens": self.budget,
            "system_reserve": self.system_reserve,
            "skill_reserve": self.skill_reserve,
        }
