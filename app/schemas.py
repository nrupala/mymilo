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


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cron: str | None = None
    payload: dict = Field(default_factory=dict)


class JobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    cron: str | None = None
    status: str | None = None


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
