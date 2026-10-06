# MyMilo — Roadmap

## Phase 1 — Skeleton (this release, v0.1.0)
Chat proxy (`/v1/chat/completions`, OpenAI-compatible), model router with
honest errors, jobs CRUD (definitions only), Jinja2 UI, SQLite, TOML+env
config, vault convention, ASF-grade docs, CI.
**Exit:** tests green + behavior-verified live over real HTTP.

## Phase 2 — Retrieval by transfer
Port `localragcoder` ingestion (chunking, embeddings, citations) as the RAG
core — transfer, don't rebuild. Wire the Perplexity spec's evals: retrieval
hit-rate, JSON-parse rate, no hallucinated citations.
**Exit:** evals pass on his document set.

## Phase 3 — Proactive engine
Scheduler executes jobs (`cron`/`next_run_at` come alive); connectors
(email/calendar under the connect-per-task privacy posture); memory synthesis
across days. This is where "town-like" starts being true.
**Exit:** a routine (e.g. morning briefing) runs end-to-end on schedule.

## Phase 4 — Fleet economics
Cost-aware routing (local-first, free-tier preference), per-call ledger,
70%-of-free-tier flags per the standing fleet doctrine.
**Exit:** ledger reconciles against provider dashboards for a week.

## Phase 5 — OS platform layer
Router + ledger migrate into the agentic OS; MyMilo becomes a thin client of
the OS's OpenAI-compatible endpoint. Persona/state engine re-derived
neutrally. Agents as first-class users: MCP, `/.well-known`, `llms.txt`.
**Exit:** MyMilo runs unchanged against the OS endpoint with the local router
deleted.

## Decision log
- 2026-10-06: name **MyMilo**; repo `nrupala/mymilo`; single product =
  agentic OS platform + MyMilo resident interface.
- 2026-10-06: license **AGPL-3.0-or-later** (default; his call to change).
- 2026-10-06: backend **llama.cpp primary** via OpenAI-compatible HTTP
  (Ollama dropped per his standing call); SQLite-first, pgvector only when
  retrieval earns it.
- 2026-10-06: router + cost ledger live in the OS; MyMilo is its client
  (converged layering; Phase 1 router is the stand-in).
- Open: KalaBodha boundary (assistant-surface ownership) — converge before
  Phase 2. Open: `nrupala/agentic-os` OMEGA-CODE/Paradise Stack migration.
