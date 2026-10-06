# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""MyMilo FastAPI application.

Layering (converged 2026-10-06): the model router and cost ledger ultimately
live in the agentic OS layer; MyMilo is a client of the OS's OpenAI-compatible
endpoint. Phase 1 ships a minimal in-repo router as a stand-in so the resident
works standalone — it migrates into the OS in Phase 5, at which point MyMilo's
default route simply points at the OS endpoint.
"""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__
from .config import Settings
from .db import Database
from .jobs import JobNotFoundError, JobService
from .router import (
    ModelNotFoundError,
    ModelRouter,
    UpstreamError,
    UpstreamUnavailableError,
)
from .schemas import (
    ChatCompletionRequest,
    JobCreate,
    JobUpdate,
    ModelInfo,
    ModelList,
)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(settings: Settings | None = None, transport=None) -> FastAPI:
    settings = settings or Settings.load()
    db = Database(settings.db_path)
    router = ModelRouter(settings, transport=transport)
    jobs = JobService(db)

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

    @app.get("/health")
    async def health():
        backends = {}
        for m in settings.models:
            backends[m.name] = await router.check_reachable(m)
        return {"status": "ok", "version": __version__, "backends": backends}

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
        data = await router.chat_completion(req.model, payload)
        return JSONResponse(content=data)

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
