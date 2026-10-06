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
import json
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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
from .planner import Planner, create_suggestion
from .rag import build_rag_messages, rag_sources, verify_citations
from .router import (
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
from .skills import resolve_skills_dir, scan_skills

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
            # Drop-a-file skills are indexed before serving.
            await scan_skills(db, docs, skills_dir)
            app.state.last_skill_scan = asyncio.get_event_loop().time()
        if settings.scheduler.enabled:
            task = asyncio.create_task(scheduler_loop(app))
        yield
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
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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
                        f"backend for model '{exc.model}' unreachable at {exc.base_url}"
                    ),
                    "type": "backend_unreachable",
                }
            },
        )

    @app.exception_handler(UpstreamError)
    async def _upstream_error(_: Request, exc: UpstreamError):
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": f"backend for model '{exc.model}' errored",
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

    @app.get("/v1/models", response_model=ModelList)
    async def list_models():
        return ModelList(data=[ModelInfo(id=m.name) for m in settings.models])

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionRequest):
        if req.stream:
            raise HTTPException(
                status_code=400, detail="streaming is not implemented in this phase"
            )
        payload = req.model_dump(exclude_none=True)
        rag_block = payload.pop("rag", None)

        rag_sources_out: list[dict] = []
        citation_check: dict | None = None
        retrieved: list[dict] = []
        if rag_block and rag_block.get("enabled"):
            retrieved = await docs.search(
                req.messages[-1].content, top_k=rag_block.get("top_k", 5)
            )
            payload["messages"] = build_rag_messages(
                [m.model_dump() for m in req.messages], retrieved
            )
            rag_sources_out = rag_sources(retrieved)

        data = await router.chat_completion(req.model, payload)

        if retrieved:
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citation_check = verify_citations(answer, retrieved)
            data["rag_sources"] = rag_sources_out
            data["citation_check"] = citation_check
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

    @app.get("/v1/mcp/tools")
    async def mcp_tools():
        """The MCP tool surface as data (maven transfer #8, reviewed).

        This is the contract the kernel's MCP server implements — the
        shapes, not a running server. Each tool maps to an HTTP endpoint.
        """
        try:
            return json.loads(mcp_catalog_path.read_text())
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
