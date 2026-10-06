# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Embedding backends for retrieval.

The default backend is llama.cpp's OpenAI-compatible ``/embeddings``
endpoint — zero new heavy dependencies, local-first, consistent with the
llama.cpp-primary decision. ``sentence-transformers`` is an optional
``rag`` extra for in-process embeddings.

There is deliberately NO silent fallback: if no encoder is available,
every embedding call raises :class:`EmbedderUnavailableError` with
instructions. Silent random vectors (as in the donor's fallback) are a
mis-issuance-grade defect — wrong results presented as real ones.
"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import anyio
import httpx
import numpy as np


class EmbedderUnavailableError(Exception):
    """Raised when no embedding backend is usable. Never silent."""


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    @property
    def name(self) -> str: ...

    async def embed(self, texts: list[str]) -> np.ndarray:
        """Return (n, dim) float32 L2-normalized vectors, one per text."""
        ...


def _normalize(mat: np.ndarray) -> np.ndarray:
    mat = mat.astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class LlamaCppEmbedder:
    """Embeddings via any OpenAI-compatible ``/embeddings`` endpoint.

    Primary backend: ``llama-server`` with an embedding model, e.g.::

        llama-server -m nomic-embed-text.gguf --embedding --port 8080
    """

    def __init__(
        self,
        base_url: str,
        model: str = "embed",
        timeout_s: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self._transport = transport
        self._dim: int | None = None

    @property
    def name(self) -> str:
        return f"llamacpp:{self.base_url}"

    @property
    def dim(self) -> int:
        if self._dim is None:
            raise EmbedderUnavailableError(
                "embedding dimension unknown — embed() has not succeeded yet"
            )
        return self._dim

    async def embed(self, texts: list[str]) -> np.ndarray:
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=self.timeout_s, trust_env=False
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    json={"input": texts, "model": self.model},
                )
        except httpx.TransportError as e:
            raise EmbedderUnavailableError(
                f"embedding backend unreachable at {self.base_url} — start "
                f"llama-server with an embedding model, e.g. "
                f"llama-server -m <embed.gguf> --embedding --port 8080. "
                f"Detail: {e}"
            ) from None
        if resp.status_code >= 400:
            raise EmbedderUnavailableError(
                f"embedding backend errored ({resp.status_code}): {resp.text[:500]}"
            )
        vecs = _normalize(
            np.array([d["embedding"] for d in resp.json()["data"]], dtype=np.float32)
        )
        self._dim = vecs.shape[1]
        return vecs

    async def check(self, timeout_s: float = 3.0) -> bool:
        """Best-effort reachability probe. Never raises."""
        try:
            old = self.timeout_s
            self.timeout_s = timeout_s
            await self.embed(["ping"])
            self.timeout_s = old
            return True
        except Exception:
            return False


class SentenceTransformerEmbedder:
    """In-process embeddings via sentence-transformers.

    Optional ``rag`` extra: ``pip install -e ".[rag]"``. Heavy (torch);
    prefer the llama.cpp backend unless there is a reason not to.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._encoder = None
        self._dim: int | None = None

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self.model_name}"

    @property
    def dim(self) -> int:
        if self._dim is None:
            raise EmbedderUnavailableError(
                "embedding dimension unknown — embed() has not succeeded yet"
            )
        return self._dim

    def _load(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise EmbedderUnavailableError(
                    "sentence-transformers is not installed — run "
                    'pip install -e ".[rag]", or use the llama.cpp backend.'
                ) from None
            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def _encode_sync(self, texts: list[str]) -> np.ndarray:
        enc = self._load()
        return _normalize(
            np.asarray(enc.encode(texts, normalize_embeddings=True), dtype=np.float32)
        )

    async def embed(self, texts: list[str]) -> np.ndarray:
        vecs = await anyio.to_thread.run_sync(self._encode_sync, texts)
        self._dim = vecs.shape[1]
        return vecs


_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Deterministic token-hash vectors. TEST ONLY — not semantic.

    Used by the unit-test suite and CI evals so the retrieval *machinery*
    (ranking, top-k, citation plumbing) is exercised without a model.
    Semantic quality numbers must come from runs with a real embedder.
    """

    DIM = 384

    @property
    def name(self) -> str:
        return "hash:test-only"

    @property
    def dim(self) -> int:
        return self.DIM

    async def embed(self, texts: list[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.DIM), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in _TOKEN_RE.findall(text.lower()):
                h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
                mat[i, h % self.DIM] += 1.0
        return _normalize(mat)
