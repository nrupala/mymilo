# Changelog

## 0.2.0 — 2026-10-06
Phase 2 — retrieval by transfer from nrupala/localragcoder:
- Document ingestion: multi-format extraction (txt/md/json/csv/html/odt/rtf
  stdlib; pdf/docx need the `rag` extra) + word chunking (512/64)
- Embeddings: `Embedder` protocol; llama.cpp `/embeddings` default (zero
  heavy deps), sentence-transformers optional, test-only HashEmbedder;
  no silent fallbacks — unavailable backends fail loudly (503)
- Endpoints: `POST /v1/documents` (multipart upload), `GET /v1/documents`,
  `DELETE /v1/documents/{id}`, `POST /v1/retrieve`; chat completions accept
  `{"rag": {"enabled": true, "top_k": 5}}` and return `rag_sources` +
  `citation_check`
- Citation-integrity verification: every `(source: file, chunk N)` must
  resolve to a retrieved chunk or the response flags it
- Evals: `evals/` fixture corpus + questions; hit-rate and citation tests
  in `tests/test_rag.py` (33 tests green); `/documents` HTML page; RAG
  toggle on the chat page

## 0.1.0 — 2026-10-06
Initial Phase 1 skeleton:
- FastAPI app: `GET /health` (per-backend reachability), OpenAI-compatible
  `POST /v1/chat/completions` (non-streaming), `GET /v1/models`
- Model router → any OpenAI-compatible backend (llama.cpp default);
  honest errors: 404 unknown model, 503 backend unreachable, 502 backend error
- Jobs CRUD (`/v1/jobs`) — definitions only; execution arrives in Phase 3
- Jinja2 UI: chat page + jobs page; local stylesheet, zero external deps
- SQLite (stdlib, WAL) with schema migrations; TOML+env config; vault convention
- Constitutional docs: SPEC / ARCHITECTURE / ROADMAP; CI (ruff + pytest)
