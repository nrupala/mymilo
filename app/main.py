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

from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import Settings
from .db import Database
from .documents import DocumentNotFoundError, DocumentService
from .embeddings import (
    EmbedderUnavailableError,
    HashEmbedder,
    LlamaCppEmbedder,
    SentenceTransformerEmbedder,
)
from .ingest import IngestionError
from .jobs import JobNotFoundError, JobService
from .rag import build_rag_messages, rag_sources, verify_citations
from .router import (
    ModelNotFoundError,
    ModelRouter,
    UpstreamError,
    UpstreamUnavailableError,
)
from .schemas import (
    ChatCompletionRequest,
    ChunkHit,
    Document,
    DocumentUploadResponse,
    JobCreate,
    JobUpdate,
    ModelInfo,
    ModelList,
    RetrieveRequest,
)

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
    router = ModelRouter(settings, transport=transport)
    jobs = JobService(db)
    docs = DocumentService(db, embedder or build_embedder(settings, transport))

    app = FastAPI(title="MyMilo", version=__version__)
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
