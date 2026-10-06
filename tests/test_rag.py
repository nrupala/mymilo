# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Phase 2 tests: ingestion, retrieval machinery, citation integrity, evals.

Retrieval tests use the deterministic HashEmbedder (test-only) so CI needs
no model. This exercises the machinery — chunking, indexing, ranking,
citation plumbing. Semantic quality numbers come from runs with a real
embedding backend (see evals/README.md).
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.embeddings import (
    EmbedderUnavailableError,
    HashEmbedder,
    LlamaCppEmbedder,
)
from app.ingest import IngestionError, chunk_text, ingest_bytes
from app.main import create_app
from app.rag import extract_citations, verify_citations

EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"
CORPUS_DIR = EVALS_DIR / "corpus"


def _load_questions() -> list[dict]:
    return [
        json.loads(line)
        for line in (EVALS_DIR / "questions.jsonl").read_text().splitlines()
        if line.strip()
    ]


@pytest.fixture()
def rag_client(settings):
    """App with HashEmbedder and a canned chat backend."""
    answer_box = {"text": "canned"}

    def _chat(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-rag",
                "object": "chat.completion",
                "created": 0,
                "model": "stub",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": answer_box["text"],
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    app = create_app(
        settings,
        transport=httpx.MockTransport(_chat),
        embedder=HashEmbedder(),
    )
    with TestClient(app) as c:
        yield c, answer_box


def _upload(client, filename: str) -> dict:
    raw = (CORPUS_DIR / filename).read_bytes()
    r = client.post("/v1/documents", files={"file": (filename, raw, "text/markdown")})
    assert r.status_code == 201, r.text
    return r.json()


def _upload_all(client):
    for f in sorted(CORPUS_DIR.glob("*.md")):
        _upload(client, f.name)


# ── ingestion ────────────────────────────────────────────────


def test_ingest_txt():
    res = ingest_bytes(b"hello world", "notes.txt")
    assert res["filetype"] == "txt"
    assert res["chunk_count"] == 1
    assert "hello world" in res["text"]


def test_ingest_markdown_strips_markup():
    res = ingest_bytes(b"# Title\n\nSome **bold** text.", "doc.md")
    assert res["filetype"] == "md"
    assert "Title" in res["text"]


def test_ingest_json_and_csv():
    res = ingest_bytes(b'{"a": 1}', "data.json")
    assert res["filetype"] == "json"
    res = ingest_bytes(b"a,b\n1,2\n", "data.csv")
    assert res["filetype"] == "csv"
    assert "1 | 2" in res["text"]


def test_ingest_empty_rejected():
    with pytest.raises(IngestionError):
        ingest_bytes(b"", "empty.txt")


def test_ingest_pdf_without_parser_gives_install_hint():
    with pytest.raises(IngestionError, match="pip install"):
        ingest_bytes(b"%PDF-1.4 fake", "doc.pdf")


def test_chunking_overlap():
    words = [f"w{i}" for i in range(100)]
    chunks = chunk_text(" ".join(words), chunk_size=30, overlap=10)
    assert len(chunks) > 1
    # overlap: last 10 words of chunk 0 start chunk 1
    assert chunks[1].split()[:10] == chunks[0].split()[20:30]


# ── document lifecycle ───────────────────────────────────────


def test_document_crud(rag_client):
    client, _ = rag_client
    up = _upload(client, "pump-maintenance.md")
    assert up["chunk_count"] >= 1
    doc_id = up["doc_id"]

    listed = client.get("/v1/documents").json()["documents"]
    assert any(d["id"] == doc_id for d in listed)
    assert listed[0]["embed_backend"] == "hash:test-only"

    assert client.delete(f"/v1/documents/{doc_id}").status_code == 204
    assert client.delete(f"/v1/documents/{doc_id}").status_code == 404
    assert client.get("/v1/documents").json()["documents"] == []


def test_upload_oversize_rejected(rag_client):
    client, _ = rag_client
    big = b"x" * (51 * 1024 * 1024)
    r = client.post("/v1/documents", files={"file": ("big.txt", big)})
    assert r.status_code == 413


def test_retrieve_empty(rag_client):
    client, _ = rag_client
    r = client.post("/v1/retrieve", json={"query": "anything", "top_k": 3})
    assert r.status_code == 200
    assert r.json()["hits"] == []


# ── retrieval eval (hit rate) ────────────────────────────────


def test_eval_hit_rate(rag_client):
    """Every eval question must rank its expected document first."""
    client, _ = rag_client
    _upload_all(client)
    questions = _load_questions()
    assert len(questions) >= 6
    hits = 0
    for q in questions:
        r = client.post("/v1/retrieve", json={"query": q["question"], "top_k": 3})
        assert r.status_code == 200
        results = r.json()["hits"]
        assert results, f"no hits for: {q['question']}"
        if results[0]["filename"] == q["expected_file"]:
            hits += 1
        else:
            print(f"MISS: {q['question']} -> {results[0]['filename']}")
    rate = hits / len(questions)
    print(f"hit rate: {hits}/{len(questions)} = {rate:.0%}")
    assert rate >= 0.8, f"hit rate {rate:.0%} below 80% target"
    assert hits == len(questions)


# ── citation integrity ───────────────────────────────────────


def test_extract_citations():
    text = (
        "It works (source: pump-maintenance.md, chunk 0) "
        "and (source: a b.pdf, chunk 12)."
    )
    assert extract_citations(text) == [
        ("pump-maintenance.md", 0),
        ("a b.pdf", 12),
    ]
    assert extract_citations("no citations here") == []


def test_citation_verification_ok():
    retrieved = [
        {"filename": "pump-maintenance.md", "chunk_index": 0},
        {"filename": "vfd-cooling.md", "chunk_index": 2},
    ]
    ans = "Replace at 18000 hours (source: pump-maintenance.md, chunk 0)."
    check = verify_citations(ans, retrieved)
    assert check["ok"] is True
    assert check["unresolved"] == []


def test_citation_verification_catches_hallucination():
    retrieved = [{"filename": "pump-maintenance.md", "chunk_index": 0}]
    ans = (
        "Replace at 18000 hours (source: pump-maintenance.md, chunk 0), "
        "and also see (source: secret-report.pdf, chunk 9)."
    )
    check = verify_citations(ans, retrieved)
    assert check["ok"] is False
    assert check["unresolved"] == [{"filename": "secret-report.pdf", "chunk": 9}]


# ── RAG chat end to end ──────────────────────────────────────


def test_rag_chat_end_to_end(rag_client):
    client, answer_box = rag_client
    _upload(client, "pump-maintenance.md")
    answer_box["text"] = (
        "The interval is 18000 operating hours (source: pump-maintenance.md, chunk 0)."
    )
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "stub",
            "messages": [{"role": "user", "content": "seal replacement interval?"}],
            "rag": {"enabled": True, "top_k": 3},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rag_sources"], "expected rag_sources in response"
    assert body["citation_check"]["ok"] is True


def test_rag_chat_flags_hallucinated_citation(rag_client):
    client, answer_box = rag_client
    _upload(client, "pump-maintenance.md")
    answer_box["text"] = "See (source: nowhere.pdf, chunk 99)."
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "stub",
            "messages": [{"role": "user", "content": "seal interval?"}],
            "rag": {"enabled": True, "top_k": 3},
        },
    )
    assert r.status_code == 200
    check = r.json()["citation_check"]
    assert check["ok"] is False
    assert check["unresolved"] == [{"filename": "nowhere.pdf", "chunk": 99}]


def test_chat_without_rag_has_no_rag_fields(client):
    r = client.post(
        "/v1/chat/completions",
        json={"model": "stub", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    assert "rag_sources" not in r.json()


# ── embedder failures are loud ───────────────────────────────


def test_llamacpp_embedder_unreachable_raises():
    import anyio

    emb = LlamaCppEmbedder("http://127.0.0.1:9/v1", timeout_s=2.0)
    with pytest.raises(EmbedderUnavailableError, match="unreachable"):
        anyio.run(emb.embed, ["hello"])


def test_upload_without_embedder_is_503(client_no_transport):
    # client_no_transport points the llamacpp embedder at an unreachable host.
    r = client_no_transport.post("/v1/documents", files={"file": ("a.txt", b"hello")})
    assert r.status_code == 503
    assert r.json()["error"]["type"] == "embedder_unavailable"


def test_health_reports_embeddings(rag_client):
    client, _ = rag_client
    body = client.get("/health").json()
    assert body["embeddings"]["backend"] == "hash:test-only"
    assert body["embeddings"]["ok"] is True


def test_documents_page_renders(rag_client):
    client, _ = rag_client
    r = client.get("/documents")
    assert r.status_code == 200
    assert "Upload &amp; indexing" in r.text or "Upload" in r.text
