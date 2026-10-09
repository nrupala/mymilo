# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Request/response schemas. Chat endpoints are OpenAI-compatible by design."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class RAGParams(BaseModel):
    enabled: bool = False
    top_k: int = 5


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    stream: bool = False
    rag: RAGParams = Field(default_factory=RAGParams)
    session_id: str | None = None
    # v0.41.0: deliberate skill invocation (tap-to-run). When set and
    # the skill exists, it is force-activated for this turn, taking
    # precedence over trigger matching. Unknown names are ignored.
    skill: str | None = None


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cron: str | None = None
    payload: dict = Field(default_factory=dict)


class JobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    cron: str | None = None
    status: str | None = None
    payload: dict | None = None


class ExportRequest(BaseModel):
    """Export chat messages to a file. Format: md, docx, html, csv."""

    messages: list[ChatMessage]
    format: str = "md"


class Job(BaseModel):
    id: str
    name: str
    cron: str | None
    payload: dict
    status: str
    last_run_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str


class JobRun(BaseModel):
    id: int
    job_id: str
    triggered_by: str
    status: str
    started_at: str
    finished_at: str | None
    result_summary: str | None
    error: str | None


class Suggestion(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    job_run_id: int | None
    created_at: str
    dismissed_at: str | None


class ConsentGrant(BaseModel):
    action: str = Field(min_length=1)


class ActionInfo(BaseModel):
    name: str
    risk: str
    requires_confirm: bool
    description: str
    consent_granted: bool


class SkillInfo(BaseModel):
    name: str
    description: str
    version: str
    path: str
    doc_id: str
    updated_at: str


class PersonaInfo(BaseModel):
    name: str
    system_prompt: str


class LedgerEntry(BaseModel):
    id: int
    ts: str
    model: str
    route: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    latency_ms: float | None
    status: str


class RouteCostSummary(BaseModel):
    route: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    free_quota_usd: float | None
    quota_pct: float | None


class RouteInfo(BaseModel):
    name: str
    base_url: str
    input_usd_per_1k: float
    output_usd_per_1k: float
    free_quota_usd: float | None
    month_spend_usd: float
    quota_pct: float | None
    last_used_at: str | None
    consecutive_failures: int
    recommended_rank: int


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "mymilo"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class Document(BaseModel):
    id: str
    filename: str
    filetype: str
    title: str
    tags: str
    size_bytes: int
    chunk_count: int
    embed_backend: str
    uploaded_at: str


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    filetype: str
    chunk_count: int


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class ChunkHit(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    text: str
