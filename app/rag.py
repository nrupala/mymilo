# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Retrieval-augmented chat: retrieve → context → generate → verify citations.

Adapted from nrupala/localragcoder ``engine/rag.py`` (his repo — transfer,
don't rebuild). MyMilo generates through its own model router instead of
Ollama, and adds a citation-integrity check: every ``(source: file, chunk
N)`` citation in the answer must resolve to a retrieved chunk. A citation
that doesn't resolve is a hallucinated citation, and the response says so
instead of presenting it as sourced.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

RAG_SYSTEM_TEMPLATE = """You are MyMilo, answering with the help of retrieved documents.
Answer the user's question based ONLY on the provided context. If the context
doesn't contain enough information, say so — do not make up information.

Cite every factual claim with the document filename and chunk index in
parentheses, exactly like: (source: report.pdf, chunk 3). Use only the
sources listed below.

Context:
{context}
"""

# Matches: (source: report.pdf, chunk 3)
CITATION_RE = re.compile(r"\(source:\s*([^,)]+?)\s*,\s*chunk\s*(\d+)\)", re.IGNORECASE)


def build_context(chunks: list[dict]) -> str:
    """Build the context block with numbered, citable sources."""
    parts = []
    for i, ch in enumerate(chunks):
        header = f"[{i + 1}] (source: {ch['filename']}, chunk {ch['chunk_index']})"
        parts.append(f"{header}\n{ch['text']}")
    return "\n\n".join(parts)


def extract_citations(answer: str) -> list[tuple[str, int]]:
    """Parse (source: file, chunk N) citations from an answer."""
    return [
        (filename.strip(), int(index))
        for filename, index in CITATION_RE.findall(answer)
    ]


def verify_citations(answer: str, retrieved: list[dict]) -> dict:
    """Check every citation resolves to a retrieved chunk.

    Returns {"ok": bool, "citations": [...], "unresolved": [...] }.
    ``ok`` is False when any citation names a (filename, chunk) pair that
    was not retrieved — i.e. a hallucinated citation.
    """
    valid = {(c["filename"], c["chunk_index"]) for c in retrieved}
    citations = extract_citations(answer)
    unresolved = [c for c in citations if c not in valid]
    return {
        "ok": not unresolved,
        "citations": [{"filename": f, "chunk": n} for f, n in citations],
        "unresolved": [{"filename": f, "chunk": n} for f, n in unresolved],
    }


def build_rag_messages(
    messages: list[dict], chunks: list[dict], template: str | None = None
) -> list[dict]:
    """Prepend the RAG system prompt with retrieved context."""
    system = (template or RAG_SYSTEM_TEMPLATE).format(context=build_context(chunks))
    return [{"role": "system", "content": system}, *messages]


def rag_sources(chunks: list[dict]) -> list[dict]:
    """Machine-readable source list for the response envelope."""
    return [
        {
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "score": c["score"],
            "doc_id": c["doc_id"],
        }
        for c in chunks
    ]
