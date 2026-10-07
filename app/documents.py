# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Document lifecycle: ingest → chunk → embed → persist → search.

Adapted from nrupala/localragcoder ``engine/document_manager.py`` and
``engine/vector_store.py`` (his repo — transfer, don't rebuild). Changes
for MyMilo: embeddings live in the same SQLite DB (no pickle files),
the embedder is injected (llama.cpp default), and there is no silent
fallback — embedding failures raise loudly.
"""

from __future__ import annotations

import logging
import uuid

import numpy as np

from .db import Database
from .embeddings import Embedder, EmbedderUnavailableError
from .ingest import IngestionError, ingest_bytes

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class DocumentNotFoundError(Exception):
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        super().__init__(f"unknown document '{doc_id}'")


class DocumentService:
    def __init__(self, db: Database, embedder: Embedder):
        self.db = db
        self.embedder = embedder

    async def upload(
        self,
        raw: bytes,
        filename: str,
        title: str | None = None,
        tags: str = "",
    ) -> dict:
        if len(raw) > MAX_UPLOAD_BYTES:
            raise IngestionError(
                f"file too large ({len(raw)} bytes > {MAX_UPLOAD_BYTES})"
            )
        result = ingest_bytes(raw, filename, CHUNK_SIZE, CHUNK_OVERLAP)
        texts = result["chunks"]
        try:
            vecs = await self.embedder.embed(texts)
        except EmbedderUnavailableError:
            raise
        dim = vecs.shape[1]
        doc_id = uuid.uuid4().hex[:12]
        self.db.add_document(
            doc_id=doc_id,
            filename=result["filename"],
            filetype=result["filetype"],
            title=title or result["filename"],
            tags=tags,
            size_bytes=result["size_bytes"],
            chunk_count=len(texts),
            embed_backend=self.embedder.name,
        )
        self.db.add_chunks(
            doc_id,
            [
                (
                    f"{doc_id}_{i}",
                    i,
                    text,
                    vecs[i].tobytes(),
                    dim,
                )
                for i, text in enumerate(texts)
            ],
        )
        logger.info(
            "Document ingested: %s (%s, %d chunks)",
            doc_id,
            result["filename"],
            len(texts),
        )
        return {
            "doc_id": doc_id,
            "filename": result["filename"],
            "filetype": result["filetype"],
            "chunk_count": len(texts),
        }

    def list(self) -> list[dict]:
        # Skills are managed via /v1/skills, not as user documents.
        return [
            d for d in self.db.list_documents() if "skill:" not in (d.get("tags") or "")
        ]

    def get(self, doc_id: str) -> dict:
        doc = self.db.get_document(doc_id)
        if doc is None:
            raise DocumentNotFoundError(doc_id)
        return doc

    def delete(self, doc_id: str) -> None:
        if not self.db.delete_document(doc_id):
            raise DocumentNotFoundError(doc_id)

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search over ingested chunks, cosine similarity."""
        rows = self.db.get_all_chunk_embeddings()
        if not rows:
            return []
        try:
            qvec = (await self.embedder.embed([query]))[0]
        except EmbedderUnavailableError:
            raise
        qdim = qvec.shape[0]
        usable = [
            r
            for r in rows
            if r["embed_dim"] == qdim
            and r["embedding"]
            and "skill:" not in (r.get("tags") or "")
        ]
        if not usable:
            logger.warning(
                "No chunks with matching embedding dim %d — re-ingest documents "
                "after changing the embedding backend.",
                qdim,
            )
            return []
        mat = np.stack(
            [np.frombuffer(r["embedding"], dtype=np.float32) for r in usable]
        )
        scores = mat @ qvec
        top_idx = np.argsort(scores)[-top_k:][::-1]
        return [
            {
                "chunk_id": usable[i]["chunk_id"],
                "doc_id": usable[i]["doc_id"],
                "filename": usable[i]["filename"],
                "chunk_index": usable[i]["chunk_index"],
                "score": float(scores[i]),
                "text": usable[i]["content"],
            }
            for i in top_idx
        ]
