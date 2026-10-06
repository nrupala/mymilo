# MyMilo — Roadmap

## Phase 1 — Skeleton (shipped, v0.1.0, on main)
Chat proxy (`/v1/chat/completions`, OpenAI-compatible), model router with
honest errors, jobs CRUD (definitions only), Jinja2 UI, SQLite, TOML+env
config, vault convention, ASF-grade docs, CI.
**Exit:** tests green + behavior-verified live over real HTTP. Done.

## Phase 2 — Retrieval by transfer (shipped, v0.2.0)
Ingestion (multi-format extract + chunk, adapted from localragcoder),
embeddings via llama.cpp `/embeddings` by default (no heavy deps;
sentence-transformers optional), SQLite-backed cosine search, RAG chat
with citation-integrity verification, evals (hit-rate + citation checks).
**Exit:** evals pass — 6/6 fixture questions rank the right document first;
citation verifier catches hallucinated citations.

## Phase 3 — Proactive engine (shipped, v0.3.0, maven transfers #1, #2, #4)
Scheduler executes jobs (`cron`/`next_run_at` come alive) over typed
payloads: `briefing` (RAG digest drafted by the model) and `reminder`
(plain nudge) — maven's scheduler/automation design, re-homed to the box.
The daily-digest pattern becomes the morning/evening briefing routine.
**Deterministic planner** (maven transfer #1 — reimplemented, never ported):
event bus + rule table; the LLM is the reasoner, never the decision-maker;
JOB_COMPLETED briefings/reminders and DOCUMENT_ADDED notes surface as
`suggestions`. **Consent-gated action registry** (transfer #2): every action
declares name/risk/requires_confirm; confirm-once consent remembered in the
`consents` table — the policy model for Phase 5's `shell.exec`/`browser.*`.
New endpoints: `POST /v1/jobs/{id}/trigger`, `GET /v1/jobs/{id}/runs`,
`GET /v1/suggestions`, `POST /v1/suggestions/{id}/dismiss`, `GET /v1/actions`,
`POST /v1/consents`, `DELETE /v1/consents/{action}`; `/jobs` page rebuilt as
Routines (schedule, run-now, pause/resume, runs, suggestions).
**Exit:** a briefing ran end-to-end on the scheduler tick over real HTTP —
verified live 2026-10-06.

## Phase 4 — Fleet economics (shipped, v0.4.0, maven transfer #6)
Cost-aware routing (local-first, free-tier preference), per-call ledger,
70%-of-free-tier flags per the standing fleet doctrine.
**Ledger**: every model call recorded with token usage (when reported) and
computed USD cost — missing usage stored as NULL, never estimated.
**Quota flags**: routes declare `free_quota_usd`; crossing 70% / 100% emits
planner events → suggestions (once per threshold per month, never blocks).
**Cost-aware routing**: `GET /v1/routes` ranks local-first → free-quota →
paid; the chat endpoint keeps exact-name routing — nothing ever silently
fails over to a paid route (spend stays human-approved).
**Lifecycle discipline** (transfer #6): per-route `last_used_at` /
`consecutive_failures` in the router, exposed via `/health`; idle tracking
enables scale-to-zero policy upstream. `/costs` HTML page: monthly summary,
route ranking, recent calls.
**Exit:** ledger reconciles against provider dashboards for a week —
verified live 2026-10-06 (stub usage backend: costs, quota suggestion,
ranking all observed over HTTP).

## Phase 5 — OS platform layer (maven transfers #5, #7, #8)
Router + ledger migrate into the agentic OS; MyMilo becomes a thin client of
the OS's OpenAI-compatible endpoint. Persona/state engine re-derived
neutrally. Agents as first-class users: MCP, `/.well-known`, `llms.txt`.
**Skills convention** (transfer #5): drop-a-markdown-file, file-watch
auto-ingest — one convention with the Skill Foundry idea, not two.
**Vault alignment** (transfer #7): zero-trust pattern shared with
kalabodha-vault — align, don't invent.
**MCP tool catalog** (transfer #8): maven's 22+ tool shapes as the checklist
when defining the kernel's MCP surface; review the list, don't port code.
**Exit:** MyMilo runs unchanged against the OS endpoint with the local
router deleted.

## Mobile story (decided 2026-10-06)
Maven proved phone-as-server fails: the OS kills background processes, and
CPU-only inference ran ~2.3 tok/s behind an unresolved upstream GPU bug. So
the server lives on the box (always-on); the phone is the surface — a PWA
client against the OS API now (installable, no store; the Jinja2 UI is the
desktop surface, the PWA the phone surface, both thin clients of the same
API). A thin native shell later ONLY for what a PWA cannot do (notification
ingest, exact alarms, background TTS). Never re-host the server on the
phone. Maven's 20-action device catalog is the phone-surface requirements
doc, not code to port.

## Stays behind (from maven — do not transfer)
Termux-on-phone runtime, Android shell, phone-hosted inference, hardcoded
`/root` paths and proot-mirror workflow, maven's RAG (superseded by
localragcoder), cloud-first routing order (inverts the local-first law),
the unbuilt AOSP-system-service vision.

## Decision log
- 2026-10-06: name **MyMilo**; repo `nrupala/mymilo`; single product =
  agentic OS platform + MyMilo resident interface.
- 2026-10-06: license **AGPL-3.0-or-later** (default; his call to change).
- 2026-10-06: backend **llama.cpp primary** via OpenAI-compatible HTTP
  (Ollama dropped per his standing call); SQLite-first, pgvector only when
  retrieval earns it.
- 2026-10-06: router + cost ledger live in the OS; MyMilo is a client of the
  OS's OpenAI-compatible endpoint (converged layering; Phase 1 router is the
  stand-in).
- 2026-10-06: maven-assistant intersection folded in — 8 transfers mapped to
  phases above (full doc: `workspace/agentic-os-kernel/`
  `maven-mymilo-intersection.md`); reimplement patterns, never port Node
  code; no IP barrier (his repo, his code).
- 2026-10-06: KalaBodha boundary **CONVERGED** — MyMilo = the resident buddy
  (routines, chat, proactive intelligence); KalaBodha = the vault it keeps
  secrets in.
- 2026-10-06: mobile story decided — server on the box, phone as surface
  (PWA now; thin native shell later only if earned, never re-host server on
  phone).
- Open: `nrupala/agentic-os` OMEGA-CODE/Paradise Stack migration.
