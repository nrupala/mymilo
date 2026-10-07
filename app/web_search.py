# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Web search for Milo via Exa (v0.9.0).

When the user asks for "latest", "news", "today", Milo searches the web
and injects results. Works with any model (local or cloud) because the
search happens in Milo's backend.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_EXA_URL = "https://api.exa.ai/search"

# Phrases that indicate the user wants fresh information.
SEARCH_TRIGGERS = [
    "latest",
    "news",
    "today",
    "current",
    "real-time",
    "realtime",
    "right now",
    "this week",
    "yesterday",
]


def wants_search(message: str) -> bool:
    """Check if the message asks for fresh/web information."""
    lowered = message.lower()
    return any(t in lowered for t in SEARCH_TRIGGERS)


async def exa_search(query: str, api_key: str, num_results: int = 5) -> list[dict]:
    """Search via Exa. Returns [{title, url, text}]."""
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        resp = await client.post(
            _EXA_URL,
            json={
                "query": query,
                "type": "auto",
                "numResults": num_results,
                "contents": {"text": {"maxCharacters": 2000}},
            },
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
            },
        )
        if resp.status_code != 200:
            logger.warning("exa search failed: %s", resp.status_code)
            return []
        data = resp.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "text": (r.get("text") or "")[:2000],
            }
            for r in data.get("results", [])
        ]


def format_search_context(results: list[dict]) -> str:
    """Format search results as context for the model."""
    if not results:
        return ""
    lines = ["Live web search results:"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n[{i}] {r['title']}\n{r['url']}\n{r['text'][:500]}")
    lines.append(
        "\nUse these results to answer. Cite sources by number [1], [2]. "
        "Do not invent details beyond what is shown."
    )
    return "\n".join(lines)
