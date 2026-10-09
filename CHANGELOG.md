# Changelog

## 0.36.0 — 2026-10-09
- Token-Efficiency Engine, slice 2 (`app/context_tiers.py`): two-tier
  context assembly in the chat path. HCA tier: the session compaction
  checkpoint is injected under a hard 1024-token budget with a header
  naming its coverage. CSA tier: per-turn retrieval — semantic facts
  ranked by relevance plus past-session episode snippets built from
  real preview content (replacing the "[Past: title] Past session:
  title" stub) — each item capped at 256 tokens, the tier at 2048.
- Cache-stable assembly order: stable system/skill prefix → summary
  tier → retrieval tier → dynamic per-turn blocks → recent history →
  current turn. The date/time block (which changes every minute) was
  previously prepended first, invalidating llama.cpp's prefix cache on
  every turn; it now lands with the other dynamic blocks (search
  results, market briefs, past-session notes) after the stable prefix.
- Compaction checkpoint v2: `session_summaries` gains `covered_from`,
  `covered_count`, and `model` (migrated in place); the summarizer
  records what each checkpoint replaced.

## 0.35.1 — 2026-10-09
- Token planner now covers the default path: the `os` route (AxiomSpine
  dispatcher) carries registry fields from the `[os]` config section or
  `MYMILO_OS_*` env vars. Found by live verification of 0.35.0 — "auto"
  traffic routed to `os`, which had no window registered and was
  therefore unplanned. On Aetheris the dispatcher's upstream is
  Phi-4-mini (`--ctx-size 8192`), so the os route plans against 8192.

## 0.35.0 — 2026-10-09
- Token-Efficiency Engine, slice 1 (`app/tokenplan.py`): per-route token
  planning registry in config (`context_window`, `default_max_tokens`,
  `max_output_tokens` — the window must match the backend's real serving
  config, e.g. llama.cpp `--ctx-size`). Every chat request now leaves
  with an explicit `max_tokens` planned as
  `min(desired, cap, window − estimated_input − margin)`; estimation uses
  the backend's own tokenizer (llama.cpp `/tokenize`) for local routes
  with a calibrated character-estimator fallback. The n_ctx guard trims
  the oldest non-system turns of over-length conversations before
  sending and refuses with a plain explanation when nothing can be
  trimmed — llama.cpp never silently truncates again. Responses carry a
  `token_plan` block (estimate, source, margin, utilization). The router
  applies route defaults/caps as a backstop for non-chat callers
  (scheduler, summarizer).

## 0.24.0–0.34.0 — 2026-10-07/08
- Agentic Milo, per-turn escalation, episodic + semantic memory, unified
  context, summarization, OpenCode bridge, Codetopo + repo-distilled
  skills, device-token auth, API host guard, skills bundle endpoint,
  Android-native prep. (Entries summarized; see git history and the
  per-release verification records in docs/.)

## 0.23.1 — 2026-10-07
- Startup hang fixed: the skill scan (`scan_skills`) blocked startup and
  hung with 73 skills; it now runs in the background via
  `asyncio.create_task`. Skills work via file matching immediately; the
  vector index builds async.

## 0.23.0 — 2026-10-07
- Semantic memory: durable facts extracted from conversation
  (`app/semantic.py` — name, location, preferences, spouse patterns),
  stored per user, grouped by category. `GET /v1/profile` returns the
  profile for UI; `DELETE /v1/profile/facts/{fact_id}` removes a fact.

## 0.22.0 — 2026-10-07
- Unified context builder (`app/context_builder.py`): system prompt,
  skill instructions, episodic memory, RAG docs, history, and user
  message assembled in priority order under a token budget, with
  budget-aware trimming.

## 0.21.0 — 2026-10-07
- Episodic memory (`app/episodic.py`): keyword search over past sessions;
  extractive episode summaries injected into chat context.

## 0.20.0 — 2026-10-07
- Per-turn escalation (`app/escalation_turn.py`): Milo auto-detects
  mid-chat when a request needs Wright and queues an escalation.
  Model-context budget foundation.

## 0.19.0 — 2026-10-07
- 57 Town skills ported unchanged from `nrupala/milo-skill-map`
  (73 skills total: 16 core + 57 Town).

## 0.18.0 — 2026-10-07
- Cloudflare integration (`app/integrations/cloudflare.py`): zones, DNS,
  Workers read tools; 27 MCP tools. Writes need confirmation.
  Needs `CLOUDFLARE_API_TOKEN`.

## 0.17.0 — 2026-10-07
- Gmail + Calendar integration (`app/integrations/gmail.py`,
  `app/integrations/calendar.py`): privacy-first — connect per task,
  disconnect after, no retention. 24 MCP tools.

## 0.16.0 — 2026-10-07
- `milo-inc-os` and `aiorg-sdse` skills (COO patterns, SDSE methodology).

## 0.15.1 — 2026-10-07
- Fixed `/v1/mcp/tools` to include the GitHub tools (22 total).

## 0.15.0 — 2026-10-07
- GitHub integration (`app/integrations/github.py`): `github_list_repos`,
  `github_list_issues`, `github_list_prs` MCP tools.

## 0.14.0 — 2026-10-07
- Phase 2 escalation: Milo→Wright via file-based queue at
  `data/escalations/`; MCP `escalate` method; system prompt guides Milo
  to escalate complex tasks.

## 0.13.0 — 2026-10-07
- Phase 1 MCP server: SSE at `/mcp/sse` + `/mcp/messages`; 19 tools via
  `tools/list` (calls stubbed in Phase 1).

## 0.12.3 — 2026-10-06
- Skills route to the cloud route (deepseek/openrouter) instead of local
  Phi-4-mini; broader stock-analysis triggers.

## 0.12.2 — 2026-10-06
- Dictation text clears correctly on submit (iPhone fix).

## 0.12.1 — 2026-10-06
- Apple-quality CSS pass; MyMilo branding; iPhone dictation hardening.

## 0.11.0 — 2026-10-06
- Per-user sessions: separate Nrupal/Natasha sessions and memory, keyed
  by Cloudflare Access email identity. Helpful default system prompt;
  source-honesty prompt.

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
