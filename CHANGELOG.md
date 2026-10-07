# Changelog

## 0.8.0 — 2026-10-06
- Cloud brains: DeepSeek and OpenRouter routes in config (disabled until API
  key via env var or vault file). Model picker shows them when configured.
- Auto-routing: new "auto" model (now the default) picks local for simple
  queries, cloud for complex ones (long, multi-question, research signals).
  Falls back to local when no cloud key is set. Response includes
  `routed_model`.
- Background tasks: say "in the background" / "take your time" and Milo
  creates a background job, runs it via the scheduler, and the result lands
  in the job run. New `background_task` job type with skill triggers and
  model routing.
- Orchestration: `app/orchestrate.py` — trigger detection, complexity
  routing, step planner (v1 sequential; smarter decomposition in v0.9).

## 0.7.0 — 2026-10-06
- Skills from all repos: 13 repo capabilities now live as Milo skills
  (stock-analysis, electrical-code, read-aloud, verified-code,
  article-draft, finance-content, fault-simulation, budget-engine,
  code-graph, safe-link, document-reader, financial-analytics,
  travel-fares). Each skill is a SKILL.md with trigger phrases; chat
  matches triggers deterministically and prepends the skill's expert
  instructions as a system message. Skills are always-on (independent
  of the "Use documents" RAG toggle). The UI shows the active skill
  (🛠 name) above Milo's reply. Response includes `active_skill`.

## 0.6.4 — 2026-10-06
- Honest error labeling: the Access-login detector now only fires for the
  actual login page (redirect to cloudflareaccess.com). Other HTML error
  pages (e.g. Cloudflare 502s when a backend hiccups) say "Server hiccup"
  instead of being mislabeled "Sign-in required".
- Config: box now ships `config/mymilo.toml` pointing the "local" route at
  the Phi-4-mini backend (:7072) instead of the dead :8080 default.

## 0.6.3 — 2026-10-06
- Service worker respects Cloudflare Access: page loads are now
  network-first so the Access login handshake (redirects + session
  cookies) always completes instead of being swallowed by the cached
  shell; the login page itself is never cached. Fixes the loop where
  the app UI loaded from cache while every API call bounced to login.

## 0.6.2 — 2026-10-06
- Phone UX: "Sign out" link in the header (Cloudflare Access logout),
  and a voice-dictation button in the chat composer (Web Speech API;
  hidden automatically where the browser lacks it)

## 0.6.1 — 2026-10-06
- Cloudflare Access UX: when the Access session is missing/expired, API
  calls receive the login page (HTML) instead of JSON — the frontend now
  detects this and says "Sign-in required" plainly instead of
  `Unexpected token '<'`. Health indicator, chat, and model picker all
  surface it.

## 0.6.0 — 2026-10-06
Phase 6 — PWA installability (phone as the surface):
- Installable web app: `/manifest.json` (standalone display, teal theme,
  192/512 + maskable icons), `/sw.js` service worker (app-shell caching;
  API calls always hit the network, never served stale), `theme-color` /
  `apple-touch-icon` / manifest link in the base template
- 70 tests green (1 new: PWA routes + manifest validity); live
  behavior-verified over HTTP

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
