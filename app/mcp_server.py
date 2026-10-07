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
    tools = []
    if catalog_path.exists():
        tools = json.loads(catalog_path.read_text()).get("tools", [])

    # Add GitHub integration tools (Phase 3)
    github_tools_path = mcp_dir / "github-tools.json"
    if github_tools_path.exists():
        try:
            github_tools = json.loads(github_tools_path.read_text())
            tools.extend(github_tools)
        except Exception:
            pass

    # Add Gmail/Calendar tools (Phase 3, privacy-first)
    gc_tools_path = mcp_dir / "gmail-calendar-tools.json"
    if gc_tools_path.exists():
        try:
            gc_tools = json.loads(gc_tools_path.read_text())
            tools.extend(gc_tools)
        except Exception:
            pass

    # Add Cloudflare tools (Phase 3)
    cf_tools_path = mcp_dir / "cloudflare-tools.json"
    if cf_tools_path.exists():
        try:
            cf_tools = json.loads(cf_tools_path.read_text())
            if isinstance(cf_tools, dict):
                cf_tools = cf_tools.get("tools", [])
            tools.extend(cf_tools)
        except Exception:
            pass

    return {"tools": tools}


def create_mcp_router(mcp_dir: Path, get_app_state) -> APIRouter:
    """Create the MCP router with SSE transport."""
    router = APIRouter(prefix="/mcp")
    catalog = load_catalog(mcp_dir)

    def _check_auth(authorization: str | None, cf_email: str | None) -> str:
        """Verify agent identity. Returns caller ID."""
        # Cloudflare Access (human or agent via Access)
        if cf_email:
            return f"cf:{cf_email}"
        # Service token for agent-to-agent (v0.24.0 hardening).
        # Tokens must be listed in MCP_SERVICE_TOKENS env var.
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            valid_tokens = getattr(get_app_state().settings, "mcp_service_tokens", [])
            if token and token in valid_tokens:
                return f"token:{token[:8]}..."
            # Unknown or missing token = 401, no exceptions.
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


async def _memory_tool(
    tool_name: str, args: dict[str, Any], caller: str, get_app_state
) -> dict[str, Any]:
    """Execute semantic memory tools via direct function calls."""
    from .semantic import SemanticMemory

    state = get_app_state()
    data_dir = Path(getattr(state, "data_dir", "/opt/mymilo/data"))
    sem = SemanticMemory(data_dir)

    # Caller format is "cf:email" or "token:..."; default to caller.
    user_email = args.get("user_email", "")
    if not user_email and caller.startswith("cf:"):
        user_email = caller[3:]

    def _ok(text: str, extra: dict | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
        if extra:
            result.update(extra)
        return result

    if tool_name == "memory_get_profile":
        profile = sem.get_profile(user_email)
        return _ok(
            f"Profile for {user_email or 'caller'}: {len(profile)} categories.",
            {"profile": profile},
        )

    if tool_name == "memory_search_facts":
        query = args.get("query", "")
        results = sem.search_facts(user_email, query)
        return _ok(
            f"Found {len(results)} facts matching '{query}'.", {"facts": results}
        )

    if tool_name == "memory_add_fact":
        fact_id = sem.add_fact(
            user_email,
            args.get("category", "general"),
            args.get("key", ""),
            args.get("value", ""),
            source=f"mcp:{caller}",
        )
        return _ok(f"Fact stored: {fact_id}.", {"fact_id": fact_id})

    if tool_name == "memory_delete_fact":
        ok = sem.delete_fact(user_email, args.get("fact_id", ""))
        return _ok(f"Fact deleted: {ok}.", {"deleted": ok})

    return _ok(f"Unknown memory tool: {tool_name}", {"isError": True})


async def _escalation_result_tool(
    args: dict[str, Any], get_app_state
) -> dict[str, Any]:
    """Poll for a Wright-processed escalation result (closes the loop)."""
    from .escalation import EscalationQueue

    state = get_app_state()
    data_dir = Path(getattr(state, "data_dir", "/opt/mymilo/data"))
    esc_id = args.get("escalation_id", "")

    # Sanitize: escalation IDs are hex (uuid4[:12]).
    if not esc_id or not all(c.isalnum() or c in "-_" for c in esc_id):
        return {
            "content": [{"type": "text", "text": "Invalid escalation ID."}],
            "isError": True,
        }

    queue = EscalationQueue(data_dir / "escalations")

    result = queue.get_result(esc_id)
    if result is not None:
        return {
            "content": [{"type": "text", "text": f"Result ready for {esc_id}."}],
            "status": "complete",
            "result": result,
        }
    if (queue.pending_dir / f"{esc_id}.json").exists():
        return {
            "content": [{"type": "text", "text": f"Escalation {esc_id} is pending."}],
            "status": "pending",
        }
    return {
        "content": [{"type": "text", "text": f"Escalation {esc_id} not found."}],
        "status": "not_found",
        "isError": True,
    }


async def _cloudflare_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute Cloudflare integration tools."""
    from .integrations.cloudflare import CloudflareClient

    try:
        client = CloudflareClient()
    except ValueError:
        return {
            "content": [
                {"type": "text", "text": "Cloudflare not configured (token missing)"}
            ],
            "isError": True,
        }

    try:
        if tool_name == "cf_list_zones":
            zones = await client.list_zones()
            summary = "\n".join(f"- {z['name']} ({z['status']})" for z in zones[:20])
            return {"content": [{"type": "text", "text": summary or "No zones"}]}

        elif tool_name == "cf_list_dns":
            records = await client.list_dns_records(args["zone_id"])
            summary = "\n".join(
                f"- {r['type']} {r['name']} -> {r['content']}" for r in records[:30]
            )
            return {"content": [{"type": "text", "text": summary or "No records"}]}

        elif tool_name == "cf_list_workers":
            workers = await client.list_workers(args["account_id"])
            summary = "\n".join(f"- {w['id']}" for w in workers[:20])
            return {"content": [{"type": "text", "text": summary or "No workers"}]}

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Cloudflare error: {e}"}],
            "isError": True,
        }


async def _gmail_calendar_tool(
    tool_name: str, args: dict[str, Any], caller: str
) -> dict[str, Any]:
    """Gmail/Calendar tools with privacy-first connect/disconnect."""
    from .integrations.calendar import CalendarClient
    from .integrations.gmail import GmailClient

    # Extract user email from caller (format: "cf:email" or "token:...")
    user_email = caller.split(":", 1)[1] if ":" in caller else caller

    try:
        if tool_name == "gmail_search":
            client = GmailClient()
            await client.connect(user_email)
            try:
                results = await client.search(
                    args["query"], args.get("max_results", 10)
                )
                summary = "\n".join(
                    f"- {r.get('subject', 'no subject')} ({r.get('from', '?')})"
                    for r in results
                )
                return {"content": [{"type": "text", "text": summary or "No results"}]}
            finally:
                await client.disconnect()

        elif tool_name == "calendar_list_events":
            from datetime import datetime

            client = CalendarClient()
            await client.connect(user_email)
            try:
                events = await client.list_events(
                    datetime.fromisoformat(args["time_min"]),
                    datetime.fromisoformat(args["time_max"]),
                    args.get("max_results", 20),
                )
                summary = "\n".join(
                    f"- {e.get('summary', '?')} ({e.get('start', '?')})" for e in events
                )
                return {"content": [{"type": "text", "text": summary or "No events"}]}
            finally:
                await client.disconnect()

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "isError": True,
        }


async def _github_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute GitHub integration tools."""
    from .integrations.github import GitHubClient

    try:
        client = GitHubClient()
    except ValueError:
        return {
            "content": [
                {"type": "text", "text": "GitHub not configured (GITHUB_TOKEN missing)"}
            ],
            "isError": True,
        }

    try:
        if tool_name == "github_list_repos":
            repos = await client.list_repos(args.get("username", "nrupala"))
            summary = "\n".join(
                f"- {r['full_name']}: {r.get('description', 'no description')}"
                for r in repos[:20]
            )
            return {"content": [{"type": "text", "text": summary}]}

        elif tool_name == "github_list_issues":
            issues = await client.list_issues(
                args["owner"], args["repo"], args.get("state", "open")
            )
            summary = "\n".join(f"#{i['number']}: {i['title']}" for i in issues[:20])
            return {"content": [{"type": "text", "text": summary or "No issues"}]}

        elif tool_name == "github_list_prs":
            prs = await client.list_prs(
                args["owner"], args["repo"], args.get("state", "open")
            )
            summary = "\n".join(f"#{p['number']}: {p['title']}" for p in prs[:20])
            return {"content": [{"type": "text", "text": summary or "No PRs"}]}

        else:
            return {
                "content": [
                    {"type": "text", "text": f"Unknown GitHub tool: {tool_name}"}
                ],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"GitHub error: {e}"}],
            "isError": True,
        }


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
    args = params.get("arguments", {})

    # Log to ledger (TODO: integrate with actual ledger)
    print(f"[mcp] {caller} -> {tool_name}")

    # ── GitHub integration (Phase 3) ─────────────────────────
    if tool_name.startswith("github_"):
        return await _github_tool(tool_name, args)

    # ── Gmail/Calendar (Phase 3, privacy-first) ────────────────
    if tool_name.startswith("gmail_") or tool_name.startswith("calendar_"):
        return await _gmail_calendar_tool(tool_name, args, caller)

    # ── Cloudflare (Phase 3) ─────────────────────────────────
    if tool_name.startswith("cf_"):
        return await _cloudflare_tool(tool_name, args)

    # ── Semantic memory (v0.24.3) ────────────────────────────
    if tool_name.startswith("memory_"):
        return await _memory_tool(tool_name, args, caller, get_app_state)

    # ── Escalation result polling (v0.24.3: closes the loop) ──
    if tool_name == "escalation_result":
        return await _escalation_result_tool(args, get_app_state)

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
