# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Conduit integration: client, error mapping, MCP dispatch, catalog.

All transport is mocked (httpx.MockTransport) — no network, and the
only key anywhere is an obvious fake. Response shapes mirror the
live Conduit worker (m1/worker/src/index.js + keys.js): tools/call
results are JSON-RPC with the payload as a JSON text block; auth
and quota failures are plain JSON bodies with HTTP 401 / 429.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.integrations.conduit import (
    TOOL_NAME_MAP,
    ConduitAuthError,
    ConduitClient,
    ConduitError,
    ConduitQuotaError,
)
from app.mcp_server import _call_tool, load_catalog

FAKE_KEY = "cndt_test_fake_key_not_real"
MCP_DIR = Path(__file__).parent.parent / "mcp"


def _conduit_handler(captured: list[httpx.Request]):
    """A MockTransport handler that behaves like the Conduit worker."""

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        payload = json.loads(request.content)
        method = payload.get("method")
        params = payload.get("params") or {}

        if method == "tools/list":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": "lookup_company",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    },
                },
            )

        if method == "tools/call":
            args = params.get("arguments") or {}
            ticker = args.get("ticker", "")
            if ticker == "QUOTA":
                # quotaExceededBody (free tier, daily window)
                return httpx.Response(
                    429,
                    json={
                        "error": "daily quota exceeded",
                        "tier": "free",
                        "window": "day",
                        "used_today": 100,
                        "quota_today": 100,
                        "resets_at": "2026-10-11T00:00:00Z",
                    },
                )
            if ticker == "BADKEY":
                return httpx.Response(401, json={"error": "missing or invalid API key"})
            if ticker == "KILLED":
                return httpx.Response(
                    503,
                    json={"error": "service temporarily disabled by the owner"},
                )
            if ticker == "BROKEN":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "error": {"code": -32602, "message": "Invalid params"},
                    },
                )
            result = {"ticker": ticker, "cik": "0000320193", "name": "Apple Inc."}
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    },
                },
            )

        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            },
        )

    return handler


def _client(captured: list[httpx.Request]) -> ConduitClient:
    return ConduitClient(
        api_key=FAKE_KEY,
        base_url="https://conduit.test/mcp",
        transport=httpx.MockTransport(_conduit_handler(captured)),
    )


# ── Client: configuration ────────────────────────────────────


def test_client_requires_key(monkeypatch):
    monkeypatch.delenv("CONDUIT_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CONDUIT_API_KEY not configured"):
        ConduitClient()


def test_client_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("CONDUIT_API_KEY", FAKE_KEY)
    client = ConduitClient()
    assert client.api_key == FAKE_KEY
    assert client.base_url.endswith("/mcp")


# ── Client: dispatch + auth header ───────────────────────────


def test_call_tool_sends_bearer_and_parses_result():
    captured: list[httpx.Request] = []
    client = _client(captured)
    result = asyncio.run(client.call_tool("lookup_company", {"ticker": "AAPL"}))

    assert result == {"ticker": "AAPL", "cik": "0000320193", "name": "Apple Inc."}
    assert len(captured) == 1
    req = captured[0]
    assert str(req.url) == "https://conduit.test/mcp"
    assert req.headers["authorization"] == f"Bearer {FAKE_KEY}"
    body = json.loads(req.content)
    assert body["jsonrpc"] == "2.0"
    assert body["method"] == "tools/call"
    assert body["params"] == {
        "name": "lookup_company",
        "arguments": {"ticker": "AAPL"},
    }


def test_list_tools():
    captured: list[httpx.Request] = []
    client = _client(captured)
    tools = asyncio.run(client.list_tools())
    assert [t["name"] for t in tools] == ["lookup_company"]


# ── Client: error mapping ────────────────────────────────────


def test_quota_429_maps_to_typed_error_with_counters():
    client = _client([])
    with pytest.raises(ConduitQuotaError) as exc:
        asyncio.run(client.call_tool("lookup_company", {"ticker": "QUOTA"}))
    assert "100/100" in str(exc.value)
    assert "resets at 2026-10-11T00:00:00Z" in str(exc.value)
    assert exc.value.usage["window"] == "day"
    assert exc.value.usage["tier"] == "free"


def test_auth_401_maps_to_typed_error():
    client = _client([])
    with pytest.raises(ConduitAuthError, match="rejected the API key"):
        asyncio.run(client.call_tool("lookup_company", {"ticker": "BADKEY"}))


def test_kill_switch_503_maps_to_clean_error():
    client = _client([])
    with pytest.raises(ConduitError, match="temporarily disabled"):
        asyncio.run(client.call_tool("lookup_company", {"ticker": "KILLED"}))


def test_rpc_error_maps_to_clean_error():
    client = _client([])
    with pytest.raises(ConduitError, match="Invalid params"):
        asyncio.run(client.call_tool("lookup_company", {"ticker": "BROKEN"}))


def test_transport_failure_maps_to_clean_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = ConduitClient(
        api_key=FAKE_KEY,
        base_url="https://conduit.test/mcp",
        transport=httpx.MockTransport(boom),
    )
    with pytest.raises(ConduitError, match="unreachable"):
        asyncio.run(client.call_tool("lookup_company", {"ticker": "AAPL"}))


# ── MCP dispatch (app.mcp_server._call_tool) ─────────────────


def _dispatch(name: str, args: dict) -> dict:
    return asyncio.run(
        _call_tool({"name": name, "arguments": args}, lambda: None, "token:test")
    )


def test_dispatch_unconfigured_fails_closed(monkeypatch):
    monkeypatch.delenv("CONDUIT_API_KEY", raising=False)
    out = _dispatch("conduit_lookup_company", {"ticker": "AAPL"})
    assert out["isError"] is True
    assert "not configured" in out["content"][0]["text"]


def test_dispatch_forwards_and_returns_result(monkeypatch):
    captured: list[httpx.Request] = []
    real_client = _client(captured)
    monkeypatch.setattr("app.integrations.conduit.ConduitClient", lambda: real_client)
    out = _dispatch("conduit_lookup_company", {"ticker": "AAPL"})
    assert "isError" not in out
    assert "Apple Inc." in out["content"][0]["text"]
    body = json.loads(captured[0].content)
    assert body["params"]["name"] == "lookup_company"  # prefix stripped


def test_dispatch_quota_is_clean_error_not_crash(monkeypatch):
    real_client = _client([])
    monkeypatch.setattr("app.integrations.conduit.ConduitClient", lambda: real_client)
    out = _dispatch("conduit_lookup_company", {"ticker": "QUOTA"})
    assert out["isError"] is True
    assert "quota exceeded" in out["content"][0]["text"]


def test_dispatch_unknown_conduit_tool(monkeypatch):
    monkeypatch.setenv("CONDUIT_API_KEY", FAKE_KEY)
    out = _dispatch("conduit_nope", {})
    assert out["isError"] is True
    assert "Unknown Conduit tool" in out["content"][0]["text"]


# ── Catalog wiring ───────────────────────────────────────────


def test_catalog_includes_all_conduit_tools():
    catalog = load_catalog(MCP_DIR)
    names = {t["name"] for t in catalog["tools"]}
    assert set(TOOL_NAME_MAP) <= names
    conduit_tools = [t for t in catalog["tools"] if t["name"].startswith("conduit_")]
    assert len(conduit_tools) == 24
    for tool in conduit_tools:
        assert tool["endpoint"] == "mcp://conduit"
        assert tool["input_schema"]["type"] == "object"
    # No name collisions anywhere in the merged catalog.
    all_names = [t["name"] for t in catalog["tools"]]
    assert len(all_names) == len(set(all_names))


def test_tool_defs_match_upstream_schemas():
    raw = json.loads((MCP_DIR / "conduit-tools.json").read_text())
    by_name = {t["name"]: t for t in raw}
    assert set(by_name) == set(TOOL_NAME_MAP)
    lookup = by_name["conduit_lookup_company"]
    assert lookup["input_schema"]["required"] == ["ticker"]
    compare = by_name["conduit_compare_companies"]
    assert compare["input_schema"]["required"] == ["tickers"]
    filing_text = by_name["conduit_get_filing_text"]
    assert filing_text["input_schema"]["required"] == ["ticker", "accession_number"]


def test_tools_surface_includes_conduit(client):
    r = client.get("/v1/mcp/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert set(TOOL_NAME_MAP) <= names
