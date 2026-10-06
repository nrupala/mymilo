# MyMilo — Architecture (Phase 1)

```
 Browser ──GET /─────────► Jinja2 chat UI ──fetch──► POST /v1/chat/completions
   │                                                        │
   │                        ┌───────────────────────────────┘
   │                        ▼
   │                 ModelRouter ──► llama.cpp :8080/v1 (default route "local")
   │                        │       (Phase 5: OS endpoint; router migrates up)
   │                        ▼
   │                 SQLite (jobs, runs, suggestions, consents)
   │
   └──GET /jobs──────► Jinja2 jobs UI ──fetch──► /v1/jobs CRUD
```

## Components

| Module | Responsibility |
|---|---|
| `app/main.py` | App factory, routes, exception → HTTP mapping, HTML pages |
| `app/config.py` | TOML + env-var settings; model routes; secret *names* only |
| `app/router.py` | Model name → OpenAI-compatible upstream; timeouts; honest errors |
| `app/schemas.py` | Pydantic v2 request/response models (OpenAI-compatible chat) |
| `app/db.py` | stdlib sqlite3, WAL mode, schema migrations (v3: jobs, documents, chunks, job_runs, suggestions, consents) |
| `app/jobs.py` | Job CRUD + scheduling bookkeeping: payload/cron validation, `next_run_at` computation |
| `app/cron.py` | Dependency-free 5-field cron parser/matcher (Vixie semantics) |
| `app/events.py` | In-process event bus (sync + async emission) |
| `app/actions.py` | Consent-gated action registry (name/risk/requires_confirm) |
| `app/planner.py` | Deterministic planner: event → rule table → actions; suggestion recorder |
| `app/scheduler.py` | Tick loop, due-job scan, `job.execute` (briefing/reminder) |
| `templates/` | `base.html`, `index.html` (chat), `jobs.html` (routines + runs + suggestions), `documents.html` |
| `static/style.css` | Local stylesheet; zero external dependencies |
| `config/` | `mymilo.example.toml` — copy to `mymilo.toml`, never commit secrets |
| `vault/` | Git-ignored secrets dir; env vars preferred |

## Request flows

**Chat:** `POST /v1/chat/completions` → validate (`stream=true` → 400, not
implemented) → router resolves model → `POST {base_url}/chat/completions`
with optional `Authorization: Bearer <env key>` → upstream JSON passed
through. Backend connections are direct (`trust_env=False`): ambient proxy
variables never reroute or observe model-backend traffic. Unknown model →
404 with available list. Backend down/timeout → 503. Backend 4xx/5xx → 502
with backend status preserved.

**Health:** `GET /health` → `{status, version, backends: {name: bool}}` via
best-effort `GET {base_url}/models` (2s timeout, never raises).

**Jobs:** CRUD at `/v1/jobs`; `PATCH` for name/cron/status/payload.
`POST /v1/jobs/{id}/trigger` runs a job now (manual); `GET /v1/jobs/{id}/runs`
lists run history. `JobNotFoundError` → 404; bad payload/cron → 422.

## Data model

`jobs(id, name, cron, payload_json, status, last_run_at, next_run_at,
created_at, updated_at)`. Statuses: `pending` (default, scheduled),
`paused` (skipped by the tick). `job_runs(id, job_id, triggered_by,
status, started_at, finished_at, result_summary, error)` records every
execution. `suggestions(id, kind, title, body, job_run_id, created_at,
dismissed_at)` is the planner's outbox. `consents(id, action_name,
granted_at, granted_by, revoked_at)` remembers confirm-once decisions.

`documents(id, filename, filetype, title, tags, size_bytes, chunk_count,
embed_backend, uploaded_at)` + `chunks(id, doc_id, chunk_index, content,
embedding BLOB, embed_dim)`. Embeddings live in the same SQLite file —
no pickle sidecars. Personal-scale design: search loads all embeddings
into memory for numpy cosine similarity (fine for thousands of chunks);
the scaling path is sqlite-vec / pgvector when retrieval earns it.

## Configuration & secrets

Precedence: `MYMILO_CONFIG` path → `config/mymilo.toml` → built-in defaults.
Env overrides: `MYMILO_HOST`, `MYMILO_PORT`, `MYMILO_DB`, `MYMILO_TIMEOUT`.
API keys live only in the environment (named by `api_key_env`); `vault/`
documents the convention. Nothing secret is logged — error paths truncate
backend bodies to 2000 chars and never include headers.

## Testing strategy

`pytest` with `httpx.MockTransport` standing in for backends — no network in
unit tests. `create_app(settings, transport)` is the seam. CI: install →
`ruff check` → `ruff format --check` → `pytest`. Behavior verification is
separate: boot uvicorn against a stub OpenAI-compatible server and assert
over real HTTP (see CONTRIBUTING).

## Extension points (later phases)

- `ModelRouter` → migrates into the OS layer (Phase 5); add cost hooks here
  in Phase 4 without changing the route interface.
- `ActionRegistry` → Phase 5 registers `shell.exec`, `browser.*` as
  `high`-risk actions; the consent policy already governs them.
- Event bus taxonomy → Phase 5 generalizes (`EMAIL_RECEIVED`,
  `CALENDAR_APPROACHING`, `MARKET_TRIGGER`, …); rules stay data.
- `POST /v1/chat/completions` → Phase 2 retrieval injects context before
  routing; the endpoint signature does not change.

## Proactive engine (Phase 3)
```
tick (every tick_seconds) ──► get_due_jobs ──► bus.emit(JOB_DUE)
    ──► planner rule "run-due-job" ──► actions.execute("job.execute")
        ──► briefing: docs.search ──► build_rag_messages ──► router
                ──► job_runs(completed) ──► bus.emit(JOB_COMPLETED)
        ──► reminder: text ──► job_runs(completed) ──► bus.emit(JOB_COMPLETED)
    ──► planner rule "<type>-to-suggestion" ──► actions.execute("suggestion.create")
        ──► suggestions row (read/dismiss in the Routines UI)

POST /v1/documents ──► bus.emit(DOCUMENT_ADDED)
    ──► planner rule "document-added-note" ──► suggestion ("note")
```

Design rules: the LLM drafts text inside the briefing handler but never
decides — events, rules, and the consent registry are plain code. Cron is
parsed by `app/cron.py` (no croniter dependency). All scheduler times are
naive-UTC ISO strings. The background loop must never die: tick exceptions
are swallowed per-pass (runs still record failures individually).

## Retrieval (Phase 2)

```
POST /v1/documents (multipart) ──► ingest.py ──► chunks ──► embeddings.py ──► SQLite
POST /v1/retrieve {query, top_k} ──► cosine search ──► ranked ChunkHits
POST /v1/chat/completions {"rag": {"enabled": true}}
    ──► retrieve ──► build_rag_messages ──► router ──► verify_citations
```

- `app/ingest.py` — multi-format extraction + word chunking, adapted from
  `nrupala/localragcoder`. Optional parsers (PDF/DOCX/HTML/MD) degrade with
  a clear install hint, never silently.
- `app/embeddings.py` — `Embedder` protocol. Default `LlamaCppEmbedder`
  (OpenAI-compatible `/embeddings`, zero heavy deps); optional
  `SentenceTransformerEmbedder` (`rag` extra); `HashEmbedder` is test-only
  and deterministic. No silent fallbacks — unavailable backends raise
  `EmbedderUnavailableError` (→ HTTP 503) with instructions.
- `app/documents.py` — upload lifecycle + cosine search over SQLite-stored
  embeddings. Chunks whose `embed_dim` doesn't match the active embedder
  are skipped with a warning (re-ingest after changing backends).
- `app/rag.py` — context builder with `[n] (source: file, chunk i)`
  markers, citation instruction system prompt, and `verify_citations`:
  every citation in the answer must resolve to a retrieved chunk, or the
  response flags it (`citation_check.ok: false`) instead of presenting it
  as sourced.
- Evals live in `evals/` (fixture corpus + questions) and run in
  `tests/test_rag.py`: retrieval hit-rate (target >80%), citation
  integrity. CI uses `HashEmbedder` (machinery, deterministic); semantic
  quality numbers come from runs with a real embedding backend.

## Fleet economics (Phase 4)

```
chat_completion ──► router ──► ledger recorder ──► ledger table
                                          └─► check_quota ──► bus.emit(QUOTA_WARNING/QUOTA_EXHAUSTED)
                                                              ──► planner ──► suggestion (kind=quota)
```

- `ModelRoute` carries `input_usd_per_1k`, `output_usd_per_1k`,
  `free_quota_usd` (all optional; zero defaults = local/free).
- The recorder is wired in `create_app` and also covers briefing jobs
  (they go through the same `router.chat_completion`). Recording is
  best-effort: it never breaks serving.
- Cost math lives in `app/ledger.py`; `recommend()` ranks routes
  free → free-quota → paid-by-rate for `GET /v1/routes`. The chat
  endpoint keeps exact-name routing — cost-awareness informs, the human
  (or a future OS policy) decides. No silent failover to paid, ever.
- Lifecycle: the router tracks `last_used_at` / `consecutive_failures`
  per route (visible in `/health`); idle timestamps are the input a
  deployment-level scale-to-zero policy would key on. MyMilo does not
  manage backend processes itself.
