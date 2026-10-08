# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Semantic memory: facts and user profile.

Extracts durable facts from conversations (preferences, personal info,
project details) and stores them structured. Provides profile UI data.

Unlike episodic memory (what happened), semantic memory is what IS true.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class SemanticMemory:
    """Fact extraction and user profile management."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.facts_file = data_dir / "semantic_facts.json"
        self.facts: dict[str, dict] = self._load()
        self._dirty = False  # v0.30.0: batch saves instead of per-fact

    def _load(self) -> dict[str, dict]:
        if self.facts_file.exists():
            try:
                return json.loads(self.facts_file.read_text())
            except Exception:
                pass
        return {}

    def _save(self):
        self.facts_file.write_text(json.dumps(self.facts, indent=2))
        self._dirty = False

    def save(self):
        """Flush pending changes to disk (v0.30.0: batched)."""
        if self._dirty:
            self._save()

    def add_fact(
        self,
        user_email: str,
        category: str,
        key: str,
        value: str,
        source: str = "conversation",
        confidence: float = 0.8,
    ) -> str:
        """Add or update a fact. Returns fact ID."""
        fact_id = f"{category}:{key}"
        if user_email not in self.facts:
            self.facts[user_email] = {}

        self.facts[user_email][fact_id] = {
            "category": category,
            "key": key,
            "value": value,
            "source": source,
            "confidence": confidence,
            "updated_at": time.time(),
        }
        # v0.30.0: mark dirty instead of saving immediately (batched flush)
        self._dirty = True
        return fact_id

    def get_fact(self, user_email: str, category: str, key: str) -> dict | None:
        """Get a specific fact."""
        fact_id = f"{category}:{key}"
        return self.facts.get(user_email, {}).get(fact_id)

    def get_profile(self, user_email: str) -> dict[str, list[dict]]:
        """Get all facts grouped by category for profile UI."""
        user_facts = self.facts.get(user_email, {})
        grouped: dict[str, list[dict]] = {}
        for fact_id, fact in user_facts.items():
            cat = fact["category"]
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append({**fact, "id": fact_id})
        return grouped

    def search_facts(self, user_email: str, query: str) -> list[dict]:
        """Search facts by keyword."""
        query_lower = query.lower()
        results = []
        for fact_id, fact in self.facts.get(user_email, {}).items():
            text = f"{fact['key']} {fact['value']}".lower()
            if query_lower in text:
                results.append({**fact, "id": fact_id})
        return results

    def delete_fact(self, user_email: str, fact_id: str) -> bool:
        """Delete a fact (user request)."""
        if fact_id in self.facts.get(user_email, {}):
            del self.facts[user_email][fact_id]
            self._dirty = True  # v0.30.0: batched save
            return True
        return False


# Fact extraction patterns (v1: rule-based)
FACT_PATTERNS = [
    # "my name is X" -> personal:name
    (r"my name is (\w+)", "personal", "name"),
    # "I live in X" -> personal:location
    (r"i live in ([^.,]+)", "personal", "location"),
    # "I prefer X" -> preference:general
    (r"i prefer ([^.,]+)", "preference", "general"),
    # "my wife is X" / "my wife's name is X"
    (r"my wife(?:'s name)? is ([^.,]+)", "personal", "spouse"),
]


def extract_facts_simple(text: str) -> list[tuple[str, str, str]]:
    """Extract facts using simple patterns. Returns [(category, key, value)]."""
    import re

    facts = []
    text_lower = text.lower()
    for pattern, category, key in FACT_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            value = match.group(1).strip()
            facts.append((category, key, value))
    return facts
