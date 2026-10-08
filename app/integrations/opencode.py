# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""OpenCode bridge integration for milo (v0.27.0).

Milo as foreman: dispatch coding tasks to OpenCode on the Aetheris box
via the oc-bridge MCP server, monitor progress, report back.

The oc-bridge is an MCP server at https://oc.aimlds.org/mcp fronting
OpenCode's local HTTP API. It requires Cloudflare Access auth via
service token.

Auth: OC_BRIDGE_TOKEN env var on the box (Cloudflare Access service token).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

OC_BRIDGE_URL = "https://oc.aimlds.org/mcp"


class OpenCodeBridgeClient:
    """MCP client for the oc-bridge."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("OC_BRIDGE_TOKEN", "")
        if not self.token:
            raise ValueError("OC_BRIDGE_TOKEN not configured")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    async def _mcp_call(self, method: str, params: dict | None = None) -> Any:
        """Make a JSON-RPC call to the oc-bridge MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "id": "milo-1",
            "method": method,
            "params": params or {},
        }
        async with httpx.AsyncClient(trust_env=False, timeout=60) as client:
            # MCP SSE: POST to /mcp/messages, but many bridges also accept
            # direct POST to /mcp. Try the standard endpoint first.
            resp = await client.post(
                OC_BRIDGE_URL,
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"oc-bridge error: {data['error']}")
            return data.get("result")

    async def list_sessions(self) -> list[dict]:
        """List active OpenCode sessions."""
        result = await self._mcp_call(
            "tools/call",
            {
                "name": "oc_list_sessions",
                "arguments": {},
            },
        )
        return self._parse_content(result)

    async def dispatch_task(
        self,
        task: str,
        repo: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Dispatch a coding task to OpenCode.

        Args:
            task: Clear description of what to do
            repo: Repository name (e.g., "mymilo")
            context: Additional context (files, errors, constraints)
        """
        prompt = task
        if repo:
            prompt = f"[Repo: {repo}]\n\n{prompt}"
        if context:
            ctx_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            prompt = f"{prompt}\n\nContext:\n{ctx_str}"

        result = await self._mcp_call(
            "tools/call",
            {
                "name": "oc_send_prompt",
                "arguments": {"prompt": prompt},
            },
        )
        return self._parse_content(result)

    async def get_session_status(self, session_id: str) -> dict:
        """Get the status of an OpenCode session."""
        result = await self._mcp_call(
            "tools/call",
            {
                "name": "oc_get_session",
                "arguments": {"session_id": session_id},
            },
        )
        return self._parse_content(result)

    def _parse_content(self, result: Any) -> Any:
        """Parse MCP tool result content."""
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict) and first.get("type") == "text":
                    text = first.get("text", "")
                    # Try to parse as JSON, fall back to raw text
                    import json

                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, ValueError):
                        return {"text": text}
            return content
        return result
