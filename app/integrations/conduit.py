# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Conduit integration for milo (v0.44.0).

Conduit is Nrupal's MCP connector marketplace; its first connector,
"Filings & Fundamentals", serves SEC EDGAR filings and fundamentals
as 24 tools from a Cloudflare Worker. This client lets Milo call
those tools upstream instead of re-implementing EDGAR locally.

The Conduit server is stateless Streamable HTTP: every call is a
self-contained JSON-RPC POST to /mcp (no initialize handshake, no
session). Every authenticated request is metered against the key's
quota — free keys get 100 calls/day, paid tiers a monthly window —
so a tools/list costs one unit exactly like a tools/call.

Auth: CONDUIT_API_KEY env var on the box (a self-service `cndt_…`
key from Conduit's POST /v1/keys, or a paid-tier key). Sent as
`Authorization: Bearer <key>` on every request; never logged.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

CONDUIT_MCP_URL = "https://conduit-filings-fundamentals.nrupalakolkar.workers.dev/mcp"

# MyMilo tool name -> upstream Conduit tool name. The catalog in
# mcp/conduit-tools.json is generated from Conduit's TOOL_DEFS
# (m1/worker/src/tools.js + m2tools.js); keep this map in step.
TOOL_NAME_MAP: dict[str, str] = {
    "conduit_lookup_company": "lookup_company",
    "conduit_get_company_facts": "get_company_facts",
    "conduit_list_filings": "list_filings",
    "conduit_get_financial_ratios": "get_financial_ratios",
    "conduit_search_filings": "search_filings",
    "conduit_get_company_profile": "get_company_profile",
    "conduit_get_ticker_search": "get_ticker_search",
    "conduit_get_company_concept": "get_company_concept",
    "conduit_get_quarterly_trend": "get_quarterly_trend",
    "conduit_get_annual_growth": "get_annual_growth",
    "conduit_get_financial_statement": "get_financial_statement",
    "conduit_get_segment_data": "get_segment_data",
    "conduit_get_debt_breakdown": "get_debt_breakdown",
    "conduit_get_shares_outstanding": "get_shares_outstanding",
    "conduit_get_dividend_payments": "get_dividend_payments",
    "conduit_get_peer_comparison": "get_peer_comparison",
    "conduit_compare_companies": "compare_companies",
    "conduit_get_filing_documents": "get_filing_documents",
    "conduit_get_filing_text": "get_filing_text",
    "conduit_get_8k_summary": "get_8k_summary",
    "conduit_get_insider_filings": "get_insider_filings",
    "conduit_get_filing_counts": "get_filing_counts",
    "conduit_get_filing_amendments": "get_filing_amendments",
    "conduit_get_10q_facts": "get_10q_facts",
}


class ConduitError(RuntimeError):
    """A Conduit call failed (transport, HTTP, or JSON-RPC error)."""


class ConduitAuthError(ConduitError):
    """Conduit rejected the API key (HTTP 401)."""


class ConduitQuotaError(ConduitError):
    """The key's Conduit quota is exhausted (HTTP 429).

    Carries the server's own counters so the caller can tell the
    user exactly where the key stands instead of guessing.
    """

    def __init__(self, message: str, *, usage: dict[str, Any] | None = None):
        super().__init__(message)
        self.usage = usage or {}


class ConduitClient:
    """MCP client for the Conduit Filings & Fundamentals connector."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.api_key = api_key or os.environ.get("CONDUIT_API_KEY", "")
        if not self.api_key:
            raise ValueError("CONDUIT_API_KEY not configured")
        self.base_url = (
            base_url or os.environ.get("CONDUIT_BASE_URL") or CONDUIT_MCP_URL
        )
        # Test seam, same idea as create_app(settings, transport):
        # production passes None and gets a real transport.
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _mcp_call(self, method: str, params: dict | None = None) -> Any:
        """Make a JSON-RPC call to the Conduit MCP server.

        Conduit's non-RPC failures are plain JSON bodies, not the
        JSON-RPC envelope: 401 {"error": "missing or invalid API key"},
        429 the quota body from quotaExceededBody, 503 the owner kill
        switch. Map each to a typed error; never leak a raw httpx
        exception or a silent None to the caller.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": "milo-1",
            "method": method,
            "params": params or {},
        }
        try:
            async with httpx.AsyncClient(
                trust_env=False, timeout=60, transport=self._transport
            ) as client:
                resp = await client.post(
                    self.base_url,
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.TransportError as e:
            raise ConduitError(f"Conduit unreachable: {e}") from e

        if resp.status_code != 200:
            body: dict[str, Any] = {}
            try:
                parsed = resp.json()
                if isinstance(parsed, dict):
                    body = parsed
            except ValueError:
                pass
            detail = body.get("error") or resp.reason_phrase or "unknown error"
            if resp.status_code == 401:
                raise ConduitAuthError(f"Conduit rejected the API key (401): {detail}")
            if resp.status_code == 429:
                window = body.get("window", "day")
                used = body.get(f"used_{'month' if window == 'month' else 'today'}")
                quota = body.get(f"quota_{'month' if window == 'month' else 'today'}")
                resets = body.get("resets_at")
                raise ConduitQuotaError(
                    f"Conduit {detail}: {used}/{quota} calls used this "
                    f"{window}; quota resets at {resets}.",
                    usage=body,
                )
            raise ConduitError(f"Conduit HTTP {resp.status_code}: {detail}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ConduitError("Conduit returned a non-JSON response") from e
        if "error" in data:
            err = data["error"] or {}
            raise ConduitError(
                f"Conduit error {err.get('code', '?')}: "
                f"{err.get('message', 'unknown error')}"
            )
        return data.get("result")

    async def list_tools(self) -> list[dict]:
        """List Conduit's tools (costs one metered unit, like any call)."""
        result = await self._mcp_call("tools/list")
        if isinstance(result, dict):
            return result.get("tools", [])
        return []

    async def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        """Call one upstream Conduit tool by its upstream name."""
        result = await self._mcp_call(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        return self._parse_content(result)

    def _parse_content(self, result: Any) -> Any:
        """Parse MCP tool result content (same shape as oc-bridge)."""
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict) and first.get("type") == "text":
                    text = first.get("text", "")
                    # Conduit returns the tool result as a JSON string;
                    # parse it back so callers get structured data.
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, ValueError):
                        return {"text": text}
            return content
        return result
