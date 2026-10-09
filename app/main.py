# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""MyMilo FastAPI application.

Layering (converged 2026-10-06): the model router and cost ledger ultimately
live in the agentic OS layer; MyMilo is a client of the OS's OpenAI-compatible
endpoint. Phase 1 ships a minimal in-repo router as a stand-in so the resident
works standalone — it migrates into the OS in Phase 5, at which point MyMilo's
default route simply points at the OS endpoint.

Phase 2 adds retrieval: documents are ingested (transferred from
nrupala/localragcoder), embedded via the configured backend (llama.cpp
``/embeddings`` by default — no heavy deps), and searched with cosine
similarity. Chat completions accept an optional ``rag`` block for
retrieval-augmented generation with citation-integrity verification.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .actions import ActionRegistry, ConsentRequired
from .config import Settings
from .cron import CronError
from .db import Database
from .documents import DocumentNotFoundError, DocumentService
from .embeddings import (
    EmbedderUnavailableError,
    HashEmbedder,
    LlamaCppEmbedder,
    SentenceTransformerEmbedder,
)
from .events import EventBus
from .ingest import IngestionError
from .jobs import JobNotFoundError, JobService
from .ledger import check_quota, current_month, month_spend, recommend
from .orchestrate import route_for_complexity, wants_background
from .planner import Planner, create_suggestion
from .rag import build_rag_messages, rag_sources, verify_citations
from .router import (
    BackendBusyError,
    ModelNotFoundError,
    ModelRouter,
    UpstreamError,
    UpstreamUnavailableError,
)
from .scheduler import (
    JobDefinitionError,
    make_job_executor,
    run_job_now,
    scheduler_loop,
)
from .schemas import (
    ActionInfo,
    ChatCompletionRequest,
    ChunkHit,
    ConsentGrant,
    Document,
    DocumentUploadResponse,
    ExportRequest,
    JobCreate,
    JobRun,
    JobUpdate,
    LedgerEntry,
    ModelInfo,
    ModelList,
    PersonaInfo,
    RetrieveRequest,
    RouteCostSummary,
    RouteInfo,
    SkillInfo,
    Suggestion,
)
from .skills import match_skill, resolve_skills_dir, scan_skills

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def build_embedder(settings: Settings, transport=None):
    """Build the configured embedding backend. Never silent on failure."""
    cfg = settings.embeddings
    if cfg.backend == "llamacpp":
        route = settings.route_for(cfg.route)
        if route is None:
            raise EmbedderUnavailableError(
                f"embedding route '{cfg.route}' is not a configured model "
                f"route — add it under [[models]] in the config."
            )
        return LlamaCppEmbedder(
            route.base_url,
            model=cfg.model,
            timeout_s=cfg.timeout_s,
            transport=transport,
        )
    if cfg.backend == "sentence-transformers":
        return SentenceTransformerEmbedder(cfg.st_model)
    if cfg.backend == "hash":
        return HashEmbedder()
    raise EmbedderUnavailableError(
        f"unknown embeddings backend '{cfg.backend}' — expected one of: "
        "llamacpp, sentence-transformers, hash"
    )


def create_app(
    settings: Settings | None = None, transport=None, embedder=None
) -> FastAPI:
    settings = settings or Settings.load()
    db = Database(settings.db_path)

    # ── Phase 3: proactive engine ──────────────────────────────
    # (bus/planner/actions are built before the router so the ledger
    # recorder can emit quota events through them)
    bus = EventBus()
    actions = ActionRegistry()
    planner = Planner(bus, actions)

    async def ledger_recorder(entry: dict) -> None:
        db.record_ledger(
            model=entry["model"],
            route=entry["route"],
            prompt_tokens=entry.get("prompt_tokens"),
            completion_tokens=entry.get("completion_tokens"),
            cost_usd=entry.get("cost_usd"),
            latency_ms=entry.get("latency_ms"),
            status=entry.get("status", "ok"),
        )
        route = settings.route_for(entry["route"])
        if route is not None:
            await check_quota(db, bus, route)

    router = ModelRouter(settings, transport=transport, ledger=ledger_recorder)
    jobs = JobService(db)
    docs = DocumentService(db, embedder or build_embedder(settings, transport))

    # ── v0.10.0: session memory spine ──────────────────────────
    from .memory import MemoryStore

    memory = MemoryStore(Path(settings.db_path).parent / "memory.db")

    # ── Phase 3: proactive engine (continued) ──────────────────
    # Event bus -> deterministic planner -> consent-gated actions.
    # The LLM never decides; it only drafts text inside job handlers.
    executor_deps = {
        "settings": settings,
        "docs": docs,
        "router": router,
        "bus": bus,
    }
    actions.register(
        "job.execute",
        make_job_executor(executor_deps),
        risk="low",
        description="Execute a job definition (briefing or reminder).",
    )
    actions.register(
        "suggestion.create",
        create_suggestion,
        risk="low",
        description="Record a suggestion for the user to read or dismiss.",
    )
    _ = planner  # the rule table lives on the bus from here on

    skills_dir = resolve_skills_dir(settings.skills.dir, BASE_DIR)
    mcp_catalog_path = BASE_DIR / "mcp" / "catalog.json"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if settings.skills.enabled:
            # Drop-a-file skills are indexed in background (v0.23.1).
            # Blocking startup on 73 skills hangs; index async instead.
            # v0.30.0: also build the in-memory trigger cache (no disk I/O per message).
            from .skills import refresh_skill_cache

            refresh_skill_cache(skills_dir)

            async def _bg_skill_scan():
                try:
                    await scan_skills(db, docs, skills_dir)
                    # Refresh the trigger cache after each background scan
                    refresh_skill_cache(skills_dir)
                    app.state.last_skill_scan = asyncio.get_event_loop().time()
                except Exception:
                    pass  # Best-effort; skills work via file matching

            asyncio.create_task(_bg_skill_scan())

        # v0.30.0: SemanticMemory singleton — eliminates file I/O per message.
        # Held in app.state, flushed to disk every 60s by background task.
        from .semantic import SemanticMemory

        app.state.semantic = SemanticMemory(Path("/opt/mymilo/data"))

        # v0.31.0: Device token store for native clients.
        from .devices import DeviceStore

        app.state.devices = DeviceStore(Path("/opt/mymilo/data/memory.db"))

        async def _bg_semantic_flush():
            while True:
                await asyncio.sleep(60)
                try:
                    app.state.semantic.save()
                except Exception:
                    pass

        asyncio.create_task(_bg_semantic_flush())

        if settings.scheduler.enabled:
            task = asyncio.create_task(scheduler_loop(app))
        yield
        # Flush semantic facts on shutdown
        try:
            app.state.semantic.save()
        except Exception:
            pass
        if task is not None:
            task.cancel()

    app = FastAPI(title="MyMilo", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.db = db
    app.state.bus = bus
    app.state.actions = actions
    app.state.docs = docs
    app.state.skills_dir = skills_dir
    app.state.last_skill_scan = 0.0

    def _resolve_user(request: Request) -> str:
        """Resolve user identity: CF Access header (browser) or
        Bearer device token (native client, v0.31.0)."""
        email = request.headers.get("cf-access-authenticated-user-email", "")
        if email:
            return email
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            try:
                resolved = app.state.devices.resolve(token)
                if resolved:
                    return resolved
            except Exception:
                pass
        return ""

    app.state.resolve_user = _resolve_user

    # ── v0.34.0: API-host guard ──────────────────────────────────
    # Native clients reach the API via mymilo-api.aimlds.org, a tunnel
    # hostname WITHOUT the browser Cloudflare Access app (Access
    # intercepts API calls with an HTML login page — found live
    # 2026-10-08). On that host the app's own auth is the only gate:
    # only /v1/* paths exist, and every request must resolve a user
    # (device token). The browser host is untouched.
    api_host = os.environ.get("MYMILO_API_HOST", "mymilo-api.aimlds.org")

    @app.middleware("http")
    async def api_host_guard(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0].lower()
        if host == api_host:
            if not request.url.path.startswith("/v1/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            if not _resolve_user(request):
                return JSONResponse(
                    {"detail": "Authentication required"}, status_code=401
                )
        return await call_next(request)

    # ── v0.13.0: MCP server (Phase 1 agentic) ────────────────────
    # Exposes Milo's tools via Model Context Protocol for agent-to-agent calls.
    try:
        from .mcp_server import create_mcp_router

        mcp_dir = Path(__file__).parent.parent / "mcp"
        if not mcp_dir.exists():
            mcp_dir = Path("/opt/mymilo/mcp")
        app.include_router(create_mcp_router(mcp_dir, lambda: app.state))
    except Exception:  # noqa: BLE001 — MCP is additive, never break the app
        pass
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # PWA entry points: served from root so the service worker's scope is "/".
    @app.get("/manifest.json", include_in_schema=False)
    async def _manifest():
        return FileResponse(
            STATIC_DIR / "manifest.json", media_type="application/manifest+json"
        )

    @app.get("/sw.js", include_in_schema=False)
    async def _service_worker():
        return FileResponse(
            STATIC_DIR / "sw.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
        )

    @app.exception_handler(ModelNotFoundError)
    async def _model_not_found(_: Request, exc: ModelNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "message": f"unknown model '{exc.name}'",
                    "type": "model_not_found",
                    "available": exc.available,
                }
            },
        )

    @app.exception_handler(UpstreamUnavailableError)
    async def _upstream_down(_: Request, exc: UpstreamUnavailableError):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": (
                        "Milo can't reach the AI model right now. "
                        "The model server may be starting up or temporarily down. "
                        "Please try again in a moment."
                    ),
                    "type": "backend_unreachable",
                    "detail": (
                        f"backend for model '{exc.model}' unreachable at {exc.base_url}"
                    ),
                }
            },
        )

    @app.exception_handler(BackendBusyError)
    async def _backend_busy(_: Request, exc: BackendBusyError):
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": (
                        "Milo's model is busy with other requests right now. "
                        "Please try again in a moment."
                    ),
                    "type": "backend_busy",
                    "detail": f"all slots for model '{exc.model}' are in use",
                }
            },
        )

    @app.exception_handler(UpstreamError)
    async def _upstream_error(_: Request, exc: UpstreamError):
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": (
                        "The AI model returned an error. "
                        "Please try again, or try a different model."
                    ),
                    "type": "backend_error",
                    "backend_status": exc.status_code,
                    "detail": exc.detail,
                }
            },
        )

    @app.exception_handler(JobNotFoundError)
    async def _job_not_found(_: Request, exc: JobNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": {"message": str(exc), "type": "job_not_found"}},
        )

    @app.exception_handler(DocumentNotFoundError)
    async def _doc_not_found(_: Request, exc: DocumentNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": {"message": str(exc), "type": "document_not_found"}},
        )

    @app.exception_handler(EmbedderUnavailableError)
    async def _embedder_down(_: Request, exc: EmbedderUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"error": {"message": str(exc), "type": "embedder_unavailable"}},
        )

    @app.exception_handler(IngestionError)
    async def _ingestion_error(_: Request, exc: IngestionError):
        return JSONResponse(
            status_code=422,
            content={"error": {"message": str(exc), "type": "ingestion_error"}},
        )

    @app.exception_handler(CronError)
    async def _cron_error(_: Request, exc: CronError):
        return JSONResponse(
            status_code=422,
            content={"error": {"message": str(exc), "type": "invalid_cron"}},
        )

    @app.exception_handler(JobDefinitionError)
    async def _job_definition_error(_: Request, exc: JobDefinitionError):
        return JSONResponse(
            status_code=422,
            content={"error": {"message": str(exc), "type": "invalid_job"}},
        )

    @app.exception_handler(ConsentRequired)
    async def _consent_required(_: Request, exc: ConsentRequired):
        return JSONResponse(
            status_code=403,
            content={"error": {"message": str(exc), "type": "consent_required"}},
        )

    @app.exception_handler(KeyError)
    async def _unknown_action(_: Request, exc: KeyError):
        return JSONResponse(
            status_code=404,
            content={"error": {"message": str(exc), "type": "unknown_action"}},
        )

    @app.get("/health")
    async def health():
        backends = {}
        for m in settings.models:
            backends[m.name] = await router.check_reachable(m)
        embeddings_ok = (
            await docs.embedder.check() if hasattr(docs.embedder, "check") else True
        )
        return {
            "status": "ok",
            "version": __version__,
            "backends": backends,
            "embeddings": {
                "backend": docs.embedder.name,
                "ok": embeddings_ok,
            },
            "routes": router.route_stats(),
        }

    @app.post("/v1/export")
    async def export_chat(req: ExportRequest):
        """Export chat messages to md, docx, html, or csv."""
        from .export import (
            extract_tables,
            tables_to_csv,
            to_docx,
            to_html,
            to_markdown,
        )

        messages = [m.model_dump() for m in req.messages]
        fmt = req.format.lower()

        if fmt == "md":
            content = to_markdown(messages)
            return Response(
                content=content,
                media_type="text/markdown",
                headers={"Content-Disposition": "attachment; filename=milo-export.md"},
            )
        elif fmt == "html":
            content = to_html(messages)
            return Response(
                content=content,
                media_type="text/html",
                headers={
                    "Content-Disposition": "attachment; filename=milo-export.html"
                },
            )
        elif fmt == "docx":
            content = to_docx(messages)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": "attachment; filename=milo-export.docx"
                },
            )
        elif fmt == "csv":
            # Extract tables from assistant messages. If no tables,
            # fall back to exporting the messages themselves.
            all_text = "\n\n".join(
                m.get("content", "") for m in messages if m.get("role") == "assistant"
            )
            tables = extract_tables(all_text)
            if tables:
                content = tables_to_csv(tables)
            else:
                # No tables: export messages as role/content rows.
                buf_csv = io.StringIO()
                w = csv.writer(buf_csv)
                w.writerow(["role", "content"])
                for m in messages:
                    w.writerow([m.get("role", ""), m.get("content", "")])
                content = buf_csv.getvalue()
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=milo-export.csv"},
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown format '{fmt}'. Use md, docx, html, or csv.",
            )

    # ── v0.10.0: session memory endpoints ──────────────────────
    # ── v0.11.0: scoped per user (Cloudflare Access email header) ──
    # ── v0.31.0: also accepts Bearer device token (native clients) ──
    def _user_email(request: Request) -> str:
        return _resolve_user(request)

    # ── v0.31.0: device registration for native clients ─────────
    @app.post("/v1/devices/register")
    async def register_device(request: Request):
        """Register a native device; returns a one-time bearer token."""
        email = request.headers.get("cf-access-authenticated-user-email", "")
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Device registration requires browser sign-in (CF Access)",
            )
        body = await request.json()
        device_id, token = app.state.devices.register(
            email,
            name=body.get("name", ""),
            platform=body.get("platform", ""),
        )
        return {"device_id": device_id, "token": token}

    @app.get("/v1/devices")
    async def list_devices(request: Request):
        email = _user_email(request)
        return {"devices": app.state.devices.list_devices(email)}

    @app.delete("/v1/devices/{device_id}")
    async def revoke_device(device_id: str, request: Request):
        email = _user_email(request)
        ok = app.state.devices.revoke(email, device_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"revoked": device_id}

    # ── v0.31.0: client config for native apps ──────────────────
    @app.get("/v1/client/config")
    async def client_config(request: Request):
        """Config the native client uses — tunable without an app release."""

        from app.skills import get_skill_bundle

        return {
            "version": __version__,
            "sync_interval_seconds": 300,
            "local_model_max_tokens": 2048,
            "complexity_threshold_chars": 500,
            "skills_bundle_version": __version__,
            "skills_bundle_hash": get_skill_bundle()["hash"],
            "features": {
                "streaming": False,
                "offline_queue": True,
                "local_skills": True,
            },
        }

    # ── v0.33.0: skills bundle (dual-homed skills) ──────────────
    @app.get("/v1/skills/bundle")
    async def skills_bundle(request: Request):
        """Full skill bundle for native clients.

        Skills are dual-homed: server is the source of truth, the app
        caches this bundle and matches triggers on-device. Authenticated
        via CF Access header or device bearer token.
        """

        from app.skills import get_skill_bundle

        email = _resolve_user(request)
        if not email:
            raise HTTPException(status_code=401, detail="Authentication required")
        bundle = get_skill_bundle()
        return {
            "version": __version__,
            "hash": bundle["hash"],
            "count": bundle["count"],
            "skills": bundle["skills"],
        }

    # ── v0.31.0: sync endpoints (offline-first) ─────────────────
    @app.get("/v1/sync/sessions")
    async def sync_sessions(request: Request, since: float = 0):
        """Sessions changed since the given timestamp (delta sync)."""
        email = _user_email(request)
        sessions = memory.list_sessions(email, limit=100)
        changed = [s for s in sessions if s["updated_at"] > since]
        out = []
        for s in changed:
            out.append(
                {
                    "id": s["id"],
                    "title": s["title"],
                    "updated_at": s["updated_at"],
                    "messages": memory.get_messages(s["id"], email),
                }
            )
        return {"sessions": out, "server_time": __import__("time").time()}

    @app.post("/v1/sync/push")
    async def sync_push(request: Request):
        """Push locally-created sessions/messages from a native client."""
        email = _user_email(request)
        body = await request.json()
        imported = 0
        for sess in body.get("sessions", []):
            sid = sess.get("id")
            if not sid:
                continue
            # Create the session server-side if it doesn't exist yet
            existing = [s["id"] for s in memory.list_sessions(email, limit=1000)]
            if sid not in existing:
                sid = memory.create_session(email, sess.get("title", "New chat"))
            for msg in sess.get("messages", []):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    memory.add_message(sid, role, content)
                    imported += 1
        return {"imported": imported}

    @app.get("/v1/sessions")
    async def list_sessions(request: Request):
        return {"sessions": memory.list_sessions(_user_email(request))}

    @app.post("/v1/sessions")
    async def create_session(request: Request):
        sid = memory.create_session(_user_email(request))
        return {"id": sid}

    @app.get("/v1/sessions/{session_id}")
    async def get_session(session_id: str, request: Request):
        email = _user_email(request)
        msgs = memory.get_messages(session_id, email)
        if not msgs:
            ids = [s["id"] for s in memory.list_sessions(email, limit=1000)]
            if session_id not in ids:
                raise HTTPException(status_code=404, detail="Session not found")
        return {"id": session_id, "messages": msgs}

    @app.delete("/v1/sessions/{session_id}")
    async def delete_session(session_id: str, request: Request):
        memory.delete_session(session_id, _user_email(request))
        return {"deleted": session_id}

    @app.get("/v1/models", response_model=ModelList)
    async def list_models():
        models = [ModelInfo(id=m.name) for m in settings.models]
        # "auto" is a virtual route: picks local vs cloud by complexity.
        models.insert(0, ModelInfo(id="auto"))
        return ModelList(data=models)

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionRequest, request: Request):
        # v0.11.0: user identity from Cloudflare Access.
        # v0.31.0: also accepts Bearer device token (native clients).
        user_email = _resolve_user(request)
        if req.stream:
            raise HTTPException(
                status_code=400, detail="streaming is not implemented in this phase"
            )
        payload = req.model_dump(exclude_none=True)
        rag_block = payload.pop("rag", None)

        # ── background trigger ─────────────────────────────────
        # "in the background" etc. → create a job, return immediately.
        user_text = req.messages[-1].content
        if wants_background(user_text):
            model = route_for_complexity(user_text, settings, default=req.model)
            job = jobs.create(
                JobCreate(
                    name=f"Background: {user_text[:60]}",
                    payload={
                        "type": "background_task",
                        "task": user_text,
                        "model": model,
                    },
                )
            )
            # Kick it off now (scheduler will also pick it up).
            asyncio.create_task(
                run_job_now(app, job.id, triggered_by="chat-background")
            )
            return JSONResponse(
                content={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": (
                                    "On it — working in the background. "
                                    "I'll drop the answer here when it's done. "
                                    f"(job {job.id[:8]})"
                                ),
                            }
                        }
                    ],
                    "background_job_id": job.id,
                    "model": model,
                }
            )

        # ── per-turn escalation to Wright (v0.20.0) ──────────────
        # Detect if this message needs Wright's help. If so, queue
        # an escalation and return immediately with a status message.
        from pathlib import Path

        from .escalation import EscalationQueue
        from .escalation_turn import should_escalate_to_wright

        should_esc, esc_reason = should_escalate_to_wright(user_text)
        if should_esc:
            queue_dir = Path("/opt/mymilo/data/escalations")
            queue = EscalationQueue(queue_dir)
            session_id_esc = req.session_id or "pending"
            esc_id = queue.submit(
                user_email=user_email,
                request=user_text,
                context={"reason": esc_reason},
                session_id=session_id_esc,
            )
            return JSONResponse(
                content={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": (
                                    "Got it — this needs Wright's help. "
                                    f"I've queued it (escalation {esc_id[:8]}). "
                                    "He'll work on it and I'll bring you "
                                    "the result."
                                ),
                            }
                        }
                    ],
                    "escalation_id": esc_id,
                    "model": req.model,
                }
            )

        # ── skills (always-on) ───────────────────────────────────
        # Match the message against skill triggers; a matched skill's
        # instructions are prepended as a system message so Milo responds
        # with that repo's methodology. Independent of the opt-in RAG.
        active_skill: str | None = None
        skill = match_skill(req.messages[-1].content, app.state.skills_dir)

        # ── v0.10.0: session memory ──────────────────────────────
        # ── v0.11.0: scoped to user ──────────────────────────────
        # Load recent turns for context; save this turn afterwards.
        # Auto-create a session if the client didn't send one.
        session_id = req.session_id or memory.create_session(user_email)
        history = memory.recent_context(session_id, max_turns=10)

        # ── v0.28.0: summarization for long chats ──────────────────
        # If the session is long, summarize old turns so the local
        # model's window doesn't choke. Runs in background — never
        # blocks the chat response. Uses existing summary if present.
        summary_context = ""
        try:
            from .summarize import get_summary_context, maybe_summarize_session

            # Fire-and-forget: summarize in background, don't wait
            asyncio.create_task(maybe_summarize_session(memory, router, session_id))
            # Use whatever summary exists right now (may be from last turn)
            summary_context = get_summary_context(memory, session_id)
        except Exception:
            pass

        # ── v0.21.0: episodic memory ─────────────────────────────
        # Pull relevant past episodes for continuity of thought.
        from .episodic import EpisodicMemory

        episodic = EpisodicMemory(memory)
        episodes = await episodic.get_relevant_history(
            user_email, user_text, max_episodes=4
        )
        # CSA retrieval tier (Engine slice 2): relevant semantic facts +
        # episode snippets, budget-capped, assembled by context_tiers.
        from .context_tiers import retrieval_tier

        profile_facts: list[dict] = []
        try:
            profile = app.state.semantic.get_profile(user_email)
            profile_facts = [f for group in profile.values() for f in group]
        except Exception:
            profile_facts = []
        retrieval_block = retrieval_tier(episodes, profile_facts, query=user_text)

        messages = [m.model_dump() for m in req.messages]
        # Insert history after any leading system messages.
        insert_at = 0
        while insert_at < len(messages) and messages[insert_at].get("role") == "system":
            insert_at += 1
        # v0.11.1: ensure a system prompt — the small local model freelances
        # without one (refusing recipes, etc.). Milo is a helpful assistant.
        if insert_at == 0:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "You are MyMilo, a helpful personal AI assistant. "
                        "Answer the user's questions directly and helpfully. "
                        "You can provide recipes, cooking advice, general "
                        "knowledge, writing help, and everyday assistance. "
                        "Be concise and friendly. "
                        "Source honesty: when you answer from your own "
                        "knowledge, say so plainly (e.g. 'from my training "
                        "knowledge'). When web search results are provided, "
                        "cite them by number [1], [2]. Never invent sources "
                        "or URLs. You DO have web search available — never "
                        "claim you cannot browse the internet. "
                        "Escalation: when a request needs deep research, "
                        "complex analysis, code changes, or anything beyond "
                        "quick answers, say 'Let me get Wright on this' and "
                        "explain what you'll have him do. You have a Wright "
                        "who handles the heavy lifting."
                    ),
                },
            )
            insert_at = 1
        messages[insert_at:insert_at] = history
        # Inject session summary (v0.28.0) before history if present
        if summary_context:
            messages.insert(
                insert_at,
                {
                    "role": "system",
                    "content": summary_context,
                },
            )
            insert_at += 1
        # Inject the retrieval tier between the summary tier and the
        # recent history (Engine slice 2 assembly order: stable prefix,
        # summary tier, retrieval tier, dynamic blocks, history, turn).
        if retrieval_block:
            messages.insert(
                insert_at,
                {"role": "system", "content": retrieval_block},
            )
        memory.add_message(session_id, "user", user_text)

        # ── v0.23.0: extract semantic facts from user message ──
        # v0.30.0: uses app.state.semantic singleton (no file I/O per message)
        from .semantic import extract_facts_simple

        try:
            sem = app.state.semantic
            facts = extract_facts_simple(user_text)
            for category, key, value in facts:
                sem.add_fact(user_email, category, key, value)
        except Exception:
            pass  # Fact extraction is best-effort
        # Current date/time: models have training cutoffs; grounding them in
        # today prevents "stuck in 2024" answers. Time in user's timezone
        # (America/Edmonton) — never leave a placeholder for the model.
        from datetime import datetime
        from zoneinfo import ZoneInfo

        _edm = ZoneInfo("America/Edmonton")
        _now = datetime.now(_edm)
        today = _now.strftime("%Y-%m-%d")
        current_time = _now.strftime("%I:%M %p %Z")
        # ── v0.10.4: memory awareness ────────────────────────────
        # Tell the model it HAS past conversations. Without this, it
        # honestly (but wrongly) claims it cannot access history.
        memory_note = (
            "You have access to the user's past conversations. "
            "The current chat's recent turns are in your context. "
            "When the user asks about previous discussions, acknowledge "
            "you can look them up via the session history."
        )
        # Dynamic per-turn blocks (Engine slice 2): collected here and
        # spliced in after the stable prefix further below, so the
        # cacheable system context stays byte-stable across turns —
        # previously this block was prepended first and its clock text
        # invalidated the whole prefix cache every minute.
        dynamic_blocks: list[dict] = [
            {
                "role": "system",
                "content": f"Today is {today}. The current time is {current_time}. "
                "Your training data may be older; "
                "do not present past events as current. If you lack current "
                "data for a question, say what you need instead of guessing. "
                "Never refuse a terse or ambiguous follow-up outright — use "
                "the conversation context to interpret it, and ask a "
                "clarifying question if you truly cannot tell. " + memory_note,
            }
        ]
        # Cross-session lookup: "what did we discuss on [date]?"
        from datetime import datetime as _dt

        _hist_triggers = [
            "past conversation",
            "previous conversation",
            "history",
            "what did we discuss",
            "what were we discussing",
            "go back to",
        ]
        if any(t in user_text.lower() for t in _hist_triggers):
            past = memory.list_sessions(user_email, limit=10)
            # Exclude the current session.
            past = [s for s in past if s["id"] != session_id][:5]
            if past:
                lines = ["Recent past conversations:"]
                for s in past:
                    d = _dt.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d")
                    lines.append(f"- {d}: {s['title']}")
                lines.append(
                    "If the user asks about a specific one, summarize what "
                    "you know from its title and offer to load it."
                )
                dynamic_blocks.append({"role": "system", "content": "\n".join(lines)})
        if skill:
            active_skill = skill["name"]
            messages = [
                {"role": "system", "content": skill["content"]},
                *messages,
            ]
        # Web search for freshness queries ("latest news on X").
        # Runs regardless of skill match — freshness is orthogonal.
        from .web_search import exa_search, format_search_context, wants_search

        if wants_search(user_text):
            exa_key = (
                settings.api_key_for(settings.route_for("exa"))
                if settings.route_for("exa")
                else None
            )
            # Fallback: check env directly.
            if not exa_key:
                import os

                exa_key = os.environ.get("MYMILO_EXA_API_KEY")
            if exa_key:
                try:
                    results = await exa_search(user_text, exa_key)
                    ctx = format_search_context(results)
                    if ctx:
                        dynamic_blocks.append({"role": "system", "content": ctx})
                except Exception:  # noqa: BLE001 — search is best-effort
                    pass
            # Live market data for "brief me on the market today".
            from .market_data import (
                fetch_indices,
                format_brief,
                wants_market_brief,
            )

            if wants_market_brief(user_text, active_skill):
                indices = await fetch_indices()
                brief = format_brief(indices)
                if brief:
                    dynamic_blocks.append({"role": "system", "content": brief})

        # Splice the dynamic blocks in after the stable system prefix
        # (Engine slice 2): everything before this point is cacheable
        # across turns; everything dynamic lands here, before history.
        if dynamic_blocks:
            from .context_tiers import dynamic_insert_index

            _dyn_at = dynamic_insert_index(messages)
            messages[_dyn_at:_dyn_at] = dynamic_blocks

        rag_sources_out: list[dict] = []
        citation_check: dict | None = None
        retrieved: list[dict] = []
        if rag_block and rag_block.get("enabled"):
            retrieved = await docs.search(
                req.messages[-1].content, top_k=rag_block.get("top_k", 5)
            )
            payload["messages"] = build_rag_messages(messages, retrieved)
            rag_sources_out = rag_sources(retrieved)
        else:
            payload["messages"] = messages

        # Resolve "auto" to the best route by complexity.
        # Skills need capable models — route to cloud when a skill is active.
        actual_model = req.model
        if req.model == "auto":
            if active_skill:
                cloud = [
                    m.name
                    for m in settings.models
                    if m.name in ("deepseek", "openrouter", "cloud")
                    and settings.api_key_for(m)
                ]
                actual_model = cloud[0] if cloud else settings.default_model
            else:
                actual_model = route_for_complexity(
                    user_text, settings, default=settings.default_model
                )
        # ── token planning (Token-Efficiency Engine, slice 1) ────
        # Plan the output budget against the route's real window.
        # Over-length conversations are trimmed (oldest non-system
        # turns first) before the backend ever sees them; if even the
        # system context plus the current turn cannot fit, refuse with
        # a plain explanation instead of a silent truncation.
        token_plan_out: dict | None = None
        route = settings.route_for(actual_model)
        if route is not None and route.context_window:
            from .tokenplan import (
                estimate_input_tokens,
                plan_max_tokens,
                trim_messages_to_fit,
            )

            est, est_source = await estimate_input_tokens(route, payload["messages"])
            plan = plan_max_tokens(
                route, est, desired=req.max_tokens, estimate_source=est_source
            )
            if not plan.fits:
                keep_budget = route.context_window - plan.margin - plan.desired_output
                trimmed, dropped = trim_messages_to_fit(
                    payload["messages"], max(keep_budget, 0)
                )
                if dropped:
                    payload["messages"] = trimmed
                    est, est_source = await estimate_input_tokens(route, trimmed)
                    plan = plan_max_tokens(
                        route,
                        est,
                        desired=req.max_tokens,
                        estimate_source=est_source,
                    )
                    plan.trimmed_messages = dropped
            if not plan.fits:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This conversation has grown too large for the "
                        "model's context window, even after trimming older "
                        "turns. Start a new chat, or ask me to summarize "
                        "where we are first."
                    ),
                )
            payload["max_tokens"] = plan.planned_max_tokens
            token_plan_out = plan.as_dict()

        degraded_from: str | None = None
        try:
            data = await router.chat_completion(actual_model, payload)
        except (UpstreamUnavailableError, BackendBusyError):
            # Ordered degradation (Engine slice 3): only "auto"
            # requests may change route — an explicit model choice is
            # honored with the honest error, never a silent swap. A
            # local route that is down/gated/busy degrades to the
            # first keyed cloud route; the local-planned max_tokens is
            # conservative on the cloud window, and the plan dict notes
            # the degradation.
            cloud = (
                [
                    m.name
                    for m in settings.models
                    if m.name in ("deepseek", "openrouter", "cloud")
                    and settings.api_key_for(m)
                ]
                if req.model == "auto"
                else []
            )
            if not cloud or cloud[0] == actual_model:
                raise
            degraded_from = actual_model
            actual_model = cloud[0]
            if token_plan_out is not None:
                token_plan_out["degraded_to"] = actual_model
            data = await router.chat_completion(actual_model, payload)
        data["routed_model"] = actual_model
        if degraded_from is not None:
            data["degraded_from"] = degraded_from
        if token_plan_out is not None:
            data["token_plan"] = token_plan_out

        if retrieved:
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citation_check = verify_citations(answer, retrieved)
            data["rag_sources"] = rag_sources_out
            data["citation_check"] = citation_check
        if active_skill:
            data["active_skill"] = active_skill
        # ── v0.10.0: save assistant reply to session memory ──
        if session_id:
            try:
                reply = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                if reply:
                    memory.add_message(session_id, "assistant", reply)
                data["session_id"] = session_id
            except Exception:
                pass
        return JSONResponse(content=data)

    # ── documents ────────────────────────────────────────────

    @app.post("/v1/documents", status_code=201, response_model=DocumentUploadResponse)
    async def upload_document(
        file: UploadFile = File(...),  # noqa: B008 — FastAPI's required idiom
        title: str | None = None,
        tags: str = "",
    ):
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="file too large")
        result = await docs.upload(
            raw, file.filename or "upload", title=title, tags=tags
        )
        await bus.emit_async(
            "DOCUMENT_ADDED",
            {
                "db": db,
                "doc_id": result["doc_id"],
                "filename": result["filename"],
                "chunks": result["chunk_count"],
            },
        )
        return result

    @app.get("/v1/documents")
    async def list_documents():
        return {"documents": [Document(**d).model_dump() for d in docs.list()]}

    @app.delete("/v1/documents/{doc_id}", status_code=204)
    async def delete_document(doc_id: str):
        docs.delete(doc_id)
        return None

    @app.post("/v1/retrieve")
    async def retrieve(req: RetrieveRequest):
        hits = await docs.search(req.query, top_k=req.top_k)
        return {"hits": [ChunkHit(**h).model_dump() for h in hits]}

    # ── jobs (Phase 1) ───────────────────────────────────────

    @app.get("/v1/jobs")
    async def list_jobs():
        return {"jobs": [j.model_dump() for j in jobs.list()]}

    @app.post("/v1/jobs", status_code=201)
    async def create_job(data: JobCreate):
        return jobs.create(data).model_dump()

    @app.get("/v1/jobs/{job_id}")
    async def get_job(job_id: str):
        return jobs.get(job_id).model_dump()

    @app.patch("/v1/jobs/{job_id}")
    async def update_job(job_id: str, data: JobUpdate):
        return jobs.update(job_id, data).model_dump()

    @app.delete("/v1/jobs/{job_id}", status_code=204)
    async def delete_job(job_id: str):
        jobs.delete(job_id)
        return None

    # ── Phase 3: proactive engine ──────────────────────────────

    @app.post("/v1/jobs/{job_id}/trigger")
    async def trigger_job(job_id: str):
        jobs.get(job_id)  # 404 if unknown
        return await run_job_now(app, job_id, triggered_by="manual")

    @app.get("/v1/jobs/{job_id}/runs")
    async def list_job_runs(job_id: str):
        jobs.get(job_id)  # 404 if unknown
        return {"runs": [JobRun(**r).model_dump() for r in db.list_runs(job_id)]}

    @app.get("/v1/suggestions")
    async def list_suggestions():
        return {
            "suggestions": [Suggestion(**s).model_dump() for s in db.list_suggestions()]
        }

    @app.post("/v1/suggestions/{suggestion_id}/dismiss")
    async def dismiss_suggestion(suggestion_id: int):
        if not db.dismiss_suggestion(suggestion_id):
            raise HTTPException(
                status_code=404, detail="unknown or already-dismissed suggestion"
            )
        return {"dismissed": suggestion_id}

    @app.get("/v1/actions")
    async def list_actions():
        return {
            "actions": [
                ActionInfo(
                    name=a.name,
                    risk=a.risk,
                    requires_confirm=a.requires_confirm,
                    description=a.description,
                    consent_granted=db.consent_granted(a.name),
                ).model_dump()
                for a in actions.list()
            ]
        }

    @app.post("/v1/consents", status_code=201)
    async def grant_consent(data: ConsentGrant):
        actions.get(data.action)  # 404 if unknown
        return db.grant_consent(data.action)

    @app.delete("/v1/consents/{action_name}", status_code=204)
    async def revoke_consent(action_name: str):
        actions.get(action_name)  # 404 if unknown
        db.revoke_consent(action_name)
        return None

    # ── Phase 4: fleet economics ───────────────────────────────

    @app.get("/v1/ledger")
    async def list_ledger(limit: int = 100):
        limit = max(1, min(limit, 1000))
        return {
            "entries": [LedgerEntry(**e).model_dump() for e in db.list_ledger(limit)]
        }

    @app.get("/v1/ledger/summary")
    async def ledger_summary(month: str | None = None):
        month = month or current_month()
        rows = db.ledger_monthly_summary(month)
        by_route = {r["route"]: r for r in rows}
        summaries = []
        for m in settings.models:
            r = by_route.get(m.name, {})
            cost = float(r.get("cost_usd", 0.0))
            quota = m.free_quota_usd
            summaries.append(
                RouteCostSummary(
                    route=m.name,
                    calls=int(r.get("calls", 0)),
                    prompt_tokens=int(r.get("prompt_tokens", 0)),
                    completion_tokens=int(r.get("completion_tokens", 0)),
                    cost_usd=cost,
                    free_quota_usd=quota,
                    quota_pct=(cost / quota * 100) if quota else None,
                ).model_dump()
            )
        return {"month": month, "routes": summaries}

    @app.get("/v1/routes")
    async def list_routes():
        """Routes with cost metadata, live spend, and recommended order.

        Informational: the chat endpoint keeps exact-name routing — this
        never reroutes anything on its own, so no silent spend.
        """
        month = current_month()
        ranked = recommend(settings.models)
        rank_of = {r.name: i for i, r in enumerate(ranked)}
        stats = router.route_stats()
        out = []
        for m in settings.models:
            spend = month_spend(db, m.name, month)
            quota = m.free_quota_usd
            out.append(
                RouteInfo(
                    name=m.name,
                    base_url=m.base_url,
                    input_usd_per_1k=m.input_usd_per_1k,
                    output_usd_per_1k=m.output_usd_per_1k,
                    free_quota_usd=quota,
                    month_spend_usd=spend,
                    quota_pct=(spend / quota * 100) if quota else None,
                    last_used_at=stats[m.name]["last_used_at"],
                    consecutive_failures=stats[m.name]["consecutive_failures"],
                    recommended_rank=rank_of[m.name],
                ).model_dump()
            )
        out.sort(key=lambda r: r["recommended_rank"])
        return {"routes": out}

    # ── Phase 5: OS platform layer ───────────────────────────

    @app.get("/v1/skills")
    async def list_skills():
        return {"skills": [SkillInfo(**s).model_dump() for s in db.list_skill_files()]}

    @app.post("/v1/skills/rescan")
    async def rescan_skills():
        return await scan_skills(db, docs, skills_dir)

    @app.get("/v1/persona")
    async def get_persona():
        return PersonaInfo(
            name=settings.persona.name,
            system_prompt=settings.persona.system_prompt,
        ).model_dump()

    # ── v0.23.0: semantic memory (facts + profile) ────────────
    @app.get("/v1/profile")
    async def get_profile(request: Request):
        """Get user's semantic profile (facts grouped by category)."""
        user_email = request.headers.get("cf-access-authenticated-user-email", "")
        sem = app.state.semantic
        return sem.get_profile(user_email)

    @app.delete("/v1/profile/facts/{fact_id}")
    async def delete_fact(fact_id: str, request: Request):
        """Delete a fact (user request)."""
        user_email = request.headers.get("cf-access-authenticated-user-email", "")
        sem = app.state.semantic
        ok = sem.delete_fact(user_email, fact_id)
        return {"deleted": ok}

    @app.get("/v1/mcp/tools")
    async def mcp_tools():
        """The MCP tool surface as data (maven transfer #8, reviewed).

        This is the contract the kernel's MCP server implements —
        the shapes, not a running server. Each tool maps to an HTTP endpoint.
        Merges github-tools.json and gmail-calendar-tools.json (Phase 3).
        """
        try:
            catalog = json.loads(mcp_catalog_path.read_text())
            # Merge GitHub tools (Phase 3)
            gh_path = mcp_catalog_path.parent / "github-tools.json"
            if gh_path.exists():
                try:
                    gh_tools = json.loads(gh_path.read_text())
                    # github-tools.json may be a list or {"tools": [...]}
                    if isinstance(gh_tools, dict):
                        gh_tools = gh_tools.get("tools", [])
                    catalog["tools"] = catalog.get("tools", []) + gh_tools
                except (OSError, json.JSONDecodeError):
                    pass
            # Merge Gmail/Calendar tools (Phase 3, privacy-first)
            gc_path = mcp_catalog_path.parent / "gmail-calendar-tools.json"
            if gc_path.exists():
                try:
                    gc_tools = json.loads(gc_path.read_text())
                    if isinstance(gc_tools, dict):
                        gc_tools = gc_tools.get("tools", [])
                    catalog["tools"] = catalog.get("tools", []) + gc_tools
                except (OSError, json.JSONDecodeError):
                    pass
            # Merge Cloudflare tools (Phase 3)
            cf_path = mcp_catalog_path.parent / "cloudflare-tools.json"
            if cf_path.exists():
                try:
                    cf_tools = json.loads(cf_path.read_text())
                    if isinstance(cf_tools, dict):
                        cf_tools = cf_tools.get("tools", [])
                    catalog["tools"] = catalog.get("tools", []) + cf_tools
                except (OSError, json.JSONDecodeError):
                    pass
            return catalog
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=503, detail="MCP catalog unavailable"
            ) from exc

    @app.get("/.well-known/mymilo.json")
    async def well_known():
        """Machine-readable instance description for agents."""
        return {
            "name": "MyMilo",
            "description": (
                "The native town-like buddy — resident interface of "
                "Nrupal's personal agentic OS."
            ),
            "version": __version__,
            "persona": settings.persona.name,
            "openai_compatible": ["/v1/chat/completions", "/v1/models"],
            "retrieval": ["/v1/documents", "/v1/retrieve"],
            "routines": ["/v1/jobs", "/v1/suggestions", "/v1/actions"],
            "economics": ["/v1/ledger", "/v1/routes"],
            "platform": [
                "/v1/skills",
                "/v1/persona",
                "/v1/mcp/tools",
                "/llms.txt",
            ],
            "os_mode": settings.os.endpoint is not None,
        }

    @app.get("/llms.txt", response_class=PlainTextResponse)
    async def llms_txt():
        """Plain-language API summary so agents are first-class users."""
        return f"""# MyMilo

MyMilo is the native town-like buddy — the resident interface of a personal
agentic OS. Version {__version__}.

## Use me

- Chat (OpenAI-compatible): POST /v1/chat/completions
  {{"model": "<name>", "messages": [{{"role": "user", "content": "..."}}],
   "rag": {{"enabled": true, "top_k": 5}}}}
  With rag enabled the answer cites sources as [S1], [S2], ... and returns
  rag_sources plus a citation_check.
- Models: GET /v1/models
- Retrieval: POST /v1/retrieve {{"query": "...", "top_k": 5}}
- Documents: POST /v1/documents (multipart file), GET /v1/documents,
  DELETE /v1/documents/{{id}}
- Routines (cron jobs): GET/POST /v1/jobs, POST /v1/jobs/{{id}}/trigger,
  GET /v1/jobs/{{id}}/runs. Payload types: briefing {{query, top_k, model}}
  and reminder {{text}}.
- Planner outbox: GET /v1/suggestions, POST /v1/suggestions/{{id}}/dismiss
- Actions & consent: GET /v1/actions, POST /v1/consents, DELETE /v1/consents/{{action}}
- Economics: GET /v1/ledger/summary, GET /v1/routes (cheapest-first ranking)
- Skills (drop-a-file): GET /v1/skills, POST /v1/skills/rescan
- Persona: GET /v1/persona
- Machine surfaces: GET /.well-known/mymilo.json, GET /v1/mcp/tools

## Rules of the house

- Decisions are made by a deterministic planner (events + rules), never by
  the model. The model drafts text; the planner decides.
- Every action declares name/risk/confirmation requirement; medium/high-risk
  actions need recorded consent.
- Routing is exact-name: nothing silently fails over to a paid route.
- Missing token usage is recorded as unknown, never estimated.
"""

    # ── HTML ─────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request, "index.html", {"version": __version__}
        )

    @app.get("/devices", response_class=HTMLResponse)
    async def devices_page(request: Request):
        """v0.32.0: device management — register/revoke native app tokens."""
        return templates.TemplateResponse(
            request, "devices.html", {"version": __version__}
        )

    @app.get("/jobs", response_class=HTMLResponse)
    async def jobs_page(request: Request):
        return templates.TemplateResponse(
            request, "jobs.html", {"version": __version__}
        )

    @app.get("/costs", response_class=HTMLResponse)
    async def costs_page(request: Request):
        return templates.TemplateResponse(
            request, "costs.html", {"version": __version__}
        )

    @app.get("/documents", response_class=HTMLResponse)
    async def documents_page(request: Request):
        return templates.TemplateResponse(
            request, "documents.html", {"version": __version__}
        )

    return app


def run() -> None:
    settings = Settings.load()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    run()
