# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""oc-bridge integration for milo (rewritten v0.47.0).

Milo as foreman: dispatch coding tasks to OpenCode on the Aetheris
box via the oc-bridge MCP server, monitor progress, report back.

The bridge (v0.4.0) is an MCP streamable-HTTP server. From the box
it is reached at ``OC_BRIDGE_URL`` (default the loopback endpoint
``http://127.0.0.1:8888/mcp`` — no Cloudflare round trip) and it
accepts the bridge bearer token: ``OC_BRIDGE_TOKEN`` is sent as
``Authorization: Bearer <token>`` on every request and never
logged. Unlike Conduit, the bridge keeps MCP sessions: the client
performs the ``initialize`` handshake once, echoes the
``Mcp-Session-Id`` header when the server issues one, and sends
``notifications/initialized`` before the first tool call. Responses
may be plain JSON or SSE (``text/event-stream``); both are unwrapped.

This replaces the v0.27.0 client, which hardcoded the public
Cloudflare URL, sent the wrong tool names (``oc_list_sessions`` /
``oc_get_session``), and never completed a real handshake. The
bridge's actual tools are the ``opencode_*`` / ``oc_*`` names in
:data:`BRIDGE_TOOLS` — nothing else is callable through here.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from .. import __version__

DEFAULT_BRIDGE_URL = "http://127.0.0.1:8888/mcp"
PROTOCOL_VERSION = "2024-11-05"

# The bridge's tool surface (oc-bridge v0.4.0). The allowlist is
# enforced client-side: call_tool refuses anything not in here, so
# a caller (or a model-written plan) can never reach past it.
BRIDGE_TOOLS: tuple[str, ...] = (
    "opencode_health",
    "opencode_list_sessions",
    "opencode_get_session",
    "opencode_mcp_status",
    "oc_status",
    "oc_send_prompt",
    "oc_job_status",
    "oc_job_result",
    "oc_run_command",
    "oc_request_deploy",
)


class OcBridgeError(RuntimeError):
    """An oc-bridge call failed (transport, HTTP, or JSON-RPC error)."""


class OcBridgeAuthError(OcBridgeError):
    """The bridge rejected the bearer token (HTTP 401/403)."""


class OcBridgeTimeoutError(OcBridgeError):
    """The bridge did not answer within the per-call timeout."""


class OcBridgeClient:
    """MCP client for the oc-bridge (OpenCode on the Aetheris box)."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.token = token or os.environ.get("OC_BRIDGE_TOKEN", "")
        if not self.token:
            raise ValueError("OC_BRIDGE_TOKEN not configured")
        self.base_url = (
            base_url or os.environ.get("OC_BRIDGE_URL") or DEFAULT_BRIDGE_URL
        )
        self.timeout_s = timeout_s
        # Test seam, same idea as ConduitClient: production passes
        # None and gets a real transport.
        self._transport = transport
        self._session_id: str | None = None
        self._initialized = False
        self._request_id = 0
        self.server_name = ""
        self.server_version = ""

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _post(
        self, payload: dict[str, Any], *, expect_reply: bool = True
    ) -> dict[str, Any] | None:
        """POST one JSON-RPC message; unwrap JSON or SSE replies."""
        try:
            async with httpx.AsyncClient(
                trust_env=False, timeout=self.timeout_s, transport=self._transport
            ) as client:
                resp = await client.post(
                    self.base_url,
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.TimeoutException as e:
            raise OcBridgeTimeoutError(
                f"oc-bridge did not answer within {self.timeout_s:g}s"
            ) from e
        except httpx.TransportError as e:
            raise OcBridgeError(f"oc-bridge unreachable: {e}") from e

        session = resp.headers.get("mcp-session-id")
        if session:
            self._session_id = session

        if resp.status_code in (401, 403):
            raise OcBridgeAuthError(
                f"oc-bridge rejected the bridge token (HTTP {resp.status_code})"
            )
        if not expect_reply:
            # Notifications are acknowledged with 200/202 and no body.
            if resp.status_code >= 400:
                raise OcBridgeError(
                    f"oc-bridge HTTP {resp.status_code} on notification"
                )
            return None
        if resp.status_code != 200:
            detail = resp.reason_phrase or "unknown error"
            try:
                body = resp.json()
                if isinstance(body, dict) and body.get("error"):
                    err = body["error"]
                    detail = (
                        err.get("message", detail)
                        if isinstance(err, dict)
                        else str(err)
                    )
            except ValueError:
                pass
            raise OcBridgeError(f"oc-bridge HTTP {resp.status_code}: {detail}")

        text = resp.text
        # SSE unwrap (same shape as the oc.py operator CLI): the
        # reply is the last data: line; plain JSON has none.
        if "data:" in text:
            lines = [
                line[5:].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            ]
            text = lines[-1] if lines else text
        try:
            data = json.loads(text)
        except ValueError as e:
            raise OcBridgeError("oc-bridge returned a non-JSON response") from e
        if not isinstance(data, dict):
            raise OcBridgeError("oc-bridge returned an unexpected response")
        if data.get("error"):
            err = data["error"] or {}
            raise OcBridgeError(
                f"oc-bridge error {err.get('code', '?')}: "
                f"{err.get('message', 'unknown error')}"
            )
        return data

    async def _ensure_initialized(self) -> None:
        """Run the MCP initialize handshake once per client."""
        if self._initialized:
            return
        self._request_id += 1
        data = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mymilo", "version": __version__},
                },
            }
        )
        result = (data or {}).get("result") or {}
        server = result.get("serverInfo") or {}
        self.server_name = str(server.get("name", ""))
        self.server_version = str(server.get("version", ""))
        # The initialized notification completes the handshake; the
        # bridge tolerates it silently (202, no body).
        await self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            expect_reply=False,
        )
        self._initialized = True

    async def _rpc(self, method: str, params: dict | None = None) -> Any:
        await self._ensure_initialized()
        self._request_id += 1
        data = await self._post(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params or {},
            }
        )
        return (data or {}).get("result")

    # ------------------------------------------------------------------
    # Tool surface
    # ------------------------------------------------------------------
    async def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        """Call one allowlisted bridge tool by its bridge name."""
        if name not in BRIDGE_TOOLS:
            raise OcBridgeError(
                f"tool {name!r} is not on the oc-bridge allowlist "
                f"({', '.join(BRIDGE_TOOLS)})"
            )
        result = await self._rpc(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
        )
        return self._parse_content(result)

    async def list_tools(self) -> list[dict]:
        result = await self._rpc("tools/list")
        if isinstance(result, dict):
            return result.get("tools", [])
        return []

    async def health(self) -> Any:
        return await self.call_tool("opencode_health")

    async def status(self) -> Any:
        return await self.call_tool("oc_status")

    async def mcp_status(self) -> Any:
        return await self.call_tool("opencode_mcp_status")

    async def list_sessions(self) -> Any:
        return await self.call_tool("opencode_list_sessions")

    async def get_session(self, session_id: str) -> Any:
        return await self.call_tool("opencode_get_session", {"session_id": session_id})

    async def send_prompt(self, session_id: str, prompt: str) -> Any:
        return await self.call_tool(
            "oc_send_prompt", {"session_id": session_id, "prompt": prompt}
        )

    async def job_status(self, job_id: str) -> Any:
        return await self.call_tool("oc_job_status", {"job_id": job_id})

    async def job_result(self, job_id: str, tail_lines: int | None = None) -> Any:
        args: dict[str, Any] = {"job_id": job_id}
        if tail_lines is not None:
            args["tail_lines"] = tail_lines
        return await self.call_tool("oc_job_result", args)

    async def run_command(
        self,
        command: str,
        session_id: str,
        timeout_s: float | None = None,
        cwd: str | None = None,
    ) -> Any:
        args: dict[str, Any] = {"command": command, "session_id": session_id}
        if timeout_s is not None:
            args["timeout_s"] = timeout_s
        if cwd:
            args["cwd"] = cwd
        return await self.call_tool("oc_run_command", args)

    async def request_deploy(self, arguments: dict | None = None) -> Any:
        return await self.call_tool("oc_request_deploy", arguments or {})

    def _parse_content(self, result: Any) -> Any:
        """Parse MCP tool result content (same shape as Conduit)."""
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict) and first.get("type") == "text":
                    text = first.get("text", "")
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, ValueError):
                        return {"text": text}
            return content
        return result
