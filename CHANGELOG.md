# Changelog

## 0.5.0 — 2026-10-06
Phase 5 — OS platform layer (maven transfers #5, #7, #8):
- OS-client seam: `[os] endpoint` registers an `os` route and makes it the
  default model (briefings follow); local router retained until the OS
  endpoint is live — its deletion is a one-PR change then
- Agents as first-class users: `/.well-known/mymilo.json`, `/llms.txt`,
  `GET /v1/mcp/tools`
- MCP tool catalog (`mcp/catalog.json`): 19-tool surface as data — the
  contract the kernel's MCP server implements; reviewed, not ported
- Skills convention: drop `skills/<name>/SKILL.md` (frontmatter
  name/description/version); indexed on startup, on-demand rescan, and
  every `[skills] poll_seconds`; skills are retrievable documents
- Vault alignment (`docs/vault-alignment.md`): env wins,
  `<vault-path>/<NAME>` file fallback; secrets never in config/logs
- Persona: `[persona]` name/system_prompt + `GET /v1/persona`; briefings
  use it with the standard `(source: file, chunk N)` citation convention
- 69 tests green (11 new); live behavior-verified over HTTP
Phase 4 — fleet economics (maven transfer #6):
- Per-route cost metadata (`input_usd_per_1k`, `output_usd_per_1k`,
  `free_quota_usd`; local defaults stay zero)
- Cost ledger: every model call recorded (tokens when reported, computed
  USD cost, latency, ok/error status); unknown usage → NULL, never guessed
- Quota flags: 70% warning / 100% exhausted emitted once per threshold per
  month as planner suggestions — informs, never blocks or reroutes
- `GET /v1/ledger`, `GET /v1/ledger/summary` (per-route monthly rollup +
  quota %), `GET /v1/routes` (cost metadata, live spend, recommended
  cheapest-first ranking)
- Lifecycle discipline in the router: per-route `last_used_at` /
  `consecutive_failures`, exposed via `/health`
- `/costs` HTML page (summary, ranking, recent calls); nav link added
- 58 tests green (10 new); live behavior-verified over HTTP
Phase 3 — proactive engine (maven transfers #1, #2, #4):
- Scheduler: dependency-free 5-field cron parser (`app/cron.py`, Vixie
  day-of-month/day-of-week OR semantics), `next_run_at` computed on
  create/update/every run; background tick loop in the app lifespan
  (`[scheduler] enabled`, `tick_seconds`, default 30s)
- Typed job payloads: `{"type": "briefing", "query", "top_k", "model"}` and
  `{"type": "reminder", "text"}`; unknown types rejected at write time (422)
- Deterministic planner: in-process event bus + rule table
  (`JOB_DUE`/`JOB_COMPLETED`/`JOB_FAILED`/`DOCUMENT_ADDED`); the LLM drafts
  briefing text but never decides — rules and the action registry do
- Consent-gated action registry: every action declares name/risk
  (`low`/`medium`/`high`)/`requires_confirm`; confirm-once consent in the
  `consents` table; the seam Phase 5's `shell.exec`/`browser.*` will use
- `job_runs` table (status, triggered_by, result_summary/error), `suggestions`
  table (briefings, reminders, document notes; dismissible)
- Endpoints: `POST /v1/jobs/{id}/trigger`, `GET /v1/jobs/{id}/runs`,
  `GET /v1/suggestions`, `POST /v1/suggestions/{id}/dismiss`,
  `GET /v1/actions`, `POST /v1/consents`, `DELETE /v1/consents/{action}`
- `/jobs` page rebuilt as Routines: schedule/run-now/pause/resume, run
  history, suggestions inbox
- 48 tests green (15 new); live behavior-verified: briefing fired by the
  real scheduler tick over HTTP against stub chat+embeddings backends
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
