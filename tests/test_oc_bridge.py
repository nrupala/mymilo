# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""oc-bridge client (v0.47.0 rewrite): handshake, tools, errors.

All transport is mocked (httpx.MockTransport) — no network, and the
only token anywhere is an obvious fake. The fake bridge mirrors
oc-bridge v0.4.0's streamable-HTTP shape: initialize returns a
session id header, notifications are acknowledged with 202, and
tool results arrive as JSON-RPC (plain JSON or SSE-wrapped).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.integrations.opencode import (
    BRIDGE_TOOLS,
    OcBridgeAuthError,
    OcBridgeClient,
    OcBridgeError,
    OcBridgeTimeoutError,
)

FAKE_TOKEN = "bridge_test_fake_token_not_real"
BRIDGE_URL = "http://bridge.test/mcp"


def _bridge_handler(captured: list[httpx.Request], *, sse: bool = False):
    """A MockTransport handler that behaves like oc-bridge v0.4.0."""

    def wrap(payload: dict) -> httpx.Response:
        if sse:
            body = "event: message\ndata: " + json.dumps(payload) + "\n\n"
            return httpx.Response(
                200, text=body, headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(200, json=payload)

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.headers.get("authorization") != f"Bearer {FAKE_TOKEN}":
            return httpx.Response(401, json={"error": "unauthorized"})
        payload = json.loads(request.content) if request.content else {}
        method = payload.get("method")
        params = payload.get("params") or {}

        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {"name": "oc-bridge", "version": "0.4.0"},
                    },
                },
                headers={"mcp-session-id": "sess-1"},
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            return wrap(
                {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {"tools": [{"name": n} for n in BRIDGE_TOOLS]},
                }
            )
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name == "oc_send_prompt" and args.get("prompt") == "RPC-FAIL":
                return wrap(
                    {
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "error": {"code": -32603, "message": "session exploded"},
                    }
                )
            result = {"tool": name, "arguments": args, "ok": True}
            return wrap(
                {
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    },
                }
            )
        return wrap(
            {
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )

    return handler


def _client(captured: list[httpx.Request], **kw) -> OcBridgeClient:
    return OcBridgeClient(
        token=FAKE_TOKEN,
        base_url=BRIDGE_URL,
        transport=httpx.MockTransport(_bridge_handler(captured, **kw)),
    )


# ── Configuration ────────────────────────────────────────────


def test_client_requires_token(monkeypatch):
    monkeypatch.delenv("OC_BRIDGE_TOKEN", raising=False)
    with pytest.raises(ValueError, match="OC_BRIDGE_TOKEN not configured"):
        OcBridgeClient()


def test_client_defaults_to_loopback_and_reads_env(monkeypatch):
    monkeypatch.setenv("OC_BRIDGE_TOKEN", FAKE_TOKEN)
    monkeypatch.delenv("OC_BRIDGE_URL", raising=False)
    client = OcBridgeClient()
    assert client.base_url == "http://127.0.0.1:8888/mcp"
    monkeypatch.setenv("OC_BRIDGE_URL", "http://127.0.0.1:9999/mcp")
    assert OcBridgeClient().base_url == "http://127.0.0.1:9999/mcp"


# ── Handshake + tool calls ───────────────────────────────────


def test_initialize_handshake_then_tool_call():
    captured: list[httpx.Request] = []
    client = _client(captured)
    result = asyncio.run(client.send_prompt("sess-42", "fix the flaky test"))
    assert result == {
        "tool": "oc_send_prompt",
        "arguments": {"session_id": "sess-42", "prompt": "fix the flaky test"},
        "ok": True,
    }
    methods = [json.loads(r.content)["method"] for r in captured]
    assert methods == ["initialize", "notifications/initialized", "tools/call"]
    # Every request carries the bearer token; the session id issued
    # by initialize is echoed on the requests that follow it.
    assert all(r.headers["authorization"] == f"Bearer {FAKE_TOKEN}" for r in captured)
    assert captured[-1].headers["mcp-session-id"] == "sess-1"
    assert client.server_name == "oc-bridge"
    assert client.server_version == "0.4.0"


def test_handshake_happens_once_across_calls():
    captured: list[httpx.Request] = []
    client = _client(captured)

    async def two_calls():
        await client.health()
        await client.status()

    asyncio.run(two_calls())
    methods = [json.loads(r.content)["method"] for r in captured]
    assert methods.count("initialize") == 1
    assert methods.count("tools/call") == 2


def test_sse_wrapped_replies_are_unwrapped():
    captured: list[httpx.Request] = []
    client = _client(captured, sse=True)
    result = asyncio.run(client.job_status("job-9"))
    assert result["tool"] == "oc_job_status"
    assert result["arguments"] == {"job_id": "job-9"}


def test_typed_helpers_send_bridge_argument_shapes():
    captured: list[httpx.Request] = []
    client = _client(captured)

    async def exercise():
        await client.run_command("ls", "sess-1", timeout_s=30, cwd="/repo")
        await client.job_result("job-1", tail_lines=25)
        await client.get_session("sess-7")

    asyncio.run(exercise())
    calls = [
        json.loads(r.content)["params"]
        for r in captured
        if json.loads(r.content)["method"] == "tools/call"
    ]
    assert calls[0] == {
        "name": "oc_run_command",
        "arguments": {
            "command": "ls",
            "session_id": "sess-1",
            "timeout_s": 30,
            "cwd": "/repo",
        },
    }
    assert calls[1] == {
        "name": "oc_job_result",
        "arguments": {"job_id": "job-1", "tail_lines": 25},
    }
    assert calls[2] == {
        "name": "opencode_get_session",
        "arguments": {"session_id": "sess-7"},
    }


def test_allowlist_refuses_unknown_tools_before_any_http():
    captured: list[httpx.Request] = []
    client = _client(captured)
    with pytest.raises(OcBridgeError, match="allowlist"):
        asyncio.run(client.call_tool("oc_delete_everything"))
    assert captured == []


# ── Error mapping ────────────────────────────────────────────


def test_rpc_error_maps_to_clean_error():
    client = _client([])
    with pytest.raises(OcBridgeError, match="session exploded"):
        asyncio.run(client.send_prompt("s", "RPC-FAIL"))


def test_bad_token_maps_to_auth_error():
    captured: list[httpx.Request] = []
    client = OcBridgeClient(
        token="wrong-token",
        base_url=BRIDGE_URL,
        transport=httpx.MockTransport(_bridge_handler(captured)),
    )
    with pytest.raises(OcBridgeAuthError, match="rejected the bridge token"):
        asyncio.run(client.health())


def test_unreachable_maps_to_clean_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = OcBridgeClient(
        token=FAKE_TOKEN,
        base_url=BRIDGE_URL,
        transport=httpx.MockTransport(boom),
    )
    with pytest.raises(OcBridgeError, match="unreachable"):
        asyncio.run(client.health())


def test_timeout_maps_to_typed_error():
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    client = OcBridgeClient(
        token=FAKE_TOKEN,
        base_url=BRIDGE_URL,
        timeout_s=5,
        transport=httpx.MockTransport(slow),
    )
    with pytest.raises(OcBridgeTimeoutError, match="did not answer within 5s"):
        asyncio.run(client.health())
