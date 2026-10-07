# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Live market data for the stock-analysis skill (v0.8.2).

Fetches major index levels from Yahoo Finance (no API key needed).
Used to ground "brief me on the market today" with real numbers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
}

_YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MyMilo/1.0)"}


async def fetch_indices() -> dict[str, dict]:
    """Fetch latest close + previous close for major indices."""
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
        for symbol, name in INDICES.items():
            try:
                resp = await client.get(
                    _YAHOO_URL.format(symbol),
                    params={"interval": "1d", "range": "5d"},
                    headers=_HEADERS,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                result = data["chart"]["result"][0]
                closes = [
                    c
                    for c in result["indicators"]["quote"][0]["close"]
                    if c is not None
                ]
                if len(closes) < 2:
                    continue
                latest, prev = closes[-1], closes[-2]
                pct = (latest - prev) / prev * 100
                out[name] = {
                    "price": round(latest, 2),
                    "prev_close": round(prev, 2),
                    "change_pct": round(pct, 2),
                }
            except Exception as exc:  # noqa: BLE001 — one index failing
                logger.warning("index fetch failed for %s: %s", symbol, exc)
    return out


def format_brief(indices: dict[str, dict]) -> str:
    """Format index data as context for the model."""
    if not indices:
        return ""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [f"Live market data ({today}):"]
    for name, d in indices.items():
        arrow = "▲" if d["change_pct"] >= 0 else "▼"
        lines.append(f"- {name}: {d['price']:,} ({arrow} {d['change_pct']:+.2f}%)")
    lines.append(
        "\nUse these real numbers in your brief. Do not claim knowledge "
        "beyond what is listed here; for anything else, say what you'd need."
    )
    return "\n".join(lines)


def wants_market_brief(message: str, skill_name: str | None) -> bool:
    """Check if this is a 'brief me on the market today' style request."""
    if skill_name != "stock-analysis":
        return False
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in [
            "brief me",
            "market today",
            "market update",
            "how is the market",
            "how's the market",
            "stocks today",
        ]
    )
