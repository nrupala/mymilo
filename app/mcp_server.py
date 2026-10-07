# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Milo MCP server (Phase 1 of agentic Milo).

Exposes Milo's 19 cataloged tools via Model Context Protocol (SSE transport).
Other agents (starting with Wright) can call Milo's capabilities as tools.

Auth: service token in Authorization header, or Cloudflare Access identity.
All calls are logged to the ledger.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# MCP protocol version
MCP_VERSION = "2024-11-05"

# Active SSE sessions: session_id -> queue
_sessions: dict[str, asyncio.Queue] = {}


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = {}


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any = None
    error: dict[str, Any] | None = None


def load_catalog(mcp_dir: Path) -> dict:
    """Load the tool catalog."""
    catalog_path = mcp_dir / "catalog.json"
    if catalog_path.exists():
        return json.loads(catalog_path.read_text())
    return {"tools": []}


def create_mcp_router(mcp_dir: Path, get_app_state) -> APIRouter:
    """Create the MCP router with SSE transport."""
    router = APIRouter(prefix="/mcp")
    catalog = load_catalog(mcp_dir)

    def _check_auth(authorization: str | None, cf_email: str | None) -> str:
        """Verify agent identity. Returns caller ID."""
        # Cloudflare Access (human or agent via Access)
        if cf_email:
            return f"cf:{cf_email}"
        # Service token for agent-to-agent
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            # TODO: validate against configured service tokens
            # For now, accept any non-empty token and log it
            if token:
                return f"token:{token[:8]}..."
        raise HTTPException(status_code=401, detail="Unauthorized")

    @router.get("/sse")
    async def sse_endpoint(
        request: Request,
        authorization: str | None = Header(None),
    ):
        """SSE endpoint for MCP clients."""
        cf_email = request.headers.get("cf-access-authenticated-user-email")
        _check_auth(authorization, cf_email)  # raises 401 if invalid

        session_id = uuid.uuid4().hex[:12]
        queue: asyncio.Queue = asyncio.Queue()
        _sessions[session_id] = queue

        async def event_stream():
            # Send endpoint URL first (MCP SSE convention)
            yield f"event: endpoint\ndata: /mcp/messages?session_id={session_id}\n\n"
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = await asyncio.wait_for(queue.get(), timeout=30)
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                    except TimeoutError:
                        # Keepalive
                        yield ": ping\n\n"
            finally:
                _sessions.pop(session_id, None)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @router.post("/messages")
    async def messages_endpoint(
        req: JsonRpcRequest,
        request: Request,
        session_id: str,
        authorization: str | None = Header(None),
    ):
        """Receive JSON-RPC messages from MCP clients."""
        cf_email = request.headers.get("cf-access-authenticated-user-email")
        caller = _check_auth(authorization, cf_email)

        queue = _sessions.get(session_id)
        if not queue:
            raise HTTPException(status_code=404, detail="Session not found")

        # Handle MCP methods
        if req.method == "initialize":
            result = {
                "protocolVersion": MCP_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mymilo", "version": "0.13.0"},
            }
        elif req.method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "inputSchema": t.get("input_schema", {}),
                    }
                    for t in catalog.get("tools", [])
                ]
            }
        elif req.method == "tools/call":
            result = await _call_tool(req.params, get_app_state, caller)
        elif req.method == "escalate":
            # Phase 2: Milo → Wright escalation
            result = await _escalate(req.params, get_app_state, caller)
        else:
            return JsonRpcResponse(
                id=req.id,
                error={"code": -32601, "message": f"Unknown method: {req.method}"},
            )

        response = JsonRpcResponse(id=req.id, result=result)
        await queue.put(response.model_dump())
        return {"ok": True}

    return router


async def _escalate(
    params: dict[str, Any], get_app_state, caller: str
) -> dict[str, Any]:
    """Phase 2: Queue an escalation for Wright.

    Milo calls this when a request exceeds its local capability.
    Wright processes the queue and writes back results.
    """
    from .escalation import EscalationQueue

    state = get_app_state()
    queue_dir = Path(getattr(state, "data_dir", "/opt/mymilo/data")) / "escalations"
    queue = EscalationQueue(queue_dir)

    user_email = params.get("user_email", caller)
    request_text = params.get("request", "")
    context = params.get("context", {})
    session_id = params.get("session_id", "")

    if not request_text:
        return {
            "content": [{"type": "text", "text": "Escalation requires a request"}],
            "isError": True,
        }

    esc_id = queue.submit(user_email, request_text, context, session_id)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Escalated to Wright (id: {esc_id}). Poll for result.",
            }
        ],
        "escalation_id": esc_id,
    }


async def _call_tool(
    params: dict[str, Any], get_app_state, caller: str
) -> dict[str, Any]:
    """Execute a tool call by mapping to Milo's HTTP endpoints."""
    tool_name = params.get("name", "")
    # args = params.get("arguments", {})  # wired in Phase 1b

    # Log to ledger (TODO: integrate with actual ledger)
    print(f"[mcp] {caller} -> {tool_name}")

    # For Phase 1, support the core tools via direct function calls.
    # Full HTTP mapping comes in Phase 1b.
    if tool_name == "chat":
        # Delegate to chat completion
        # TODO: wire to actual chat handler
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Chat tool called (wiring in progress)",
                }
            ]
        }

    return {
        "content": [
            {
                "type": "text",
                "text": f"Tool '{tool_name}' not yet wired in Phase 1",
            }
        ],
        "isError": True,
    }
