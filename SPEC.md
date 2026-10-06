# MyMilo — Constitutional Spec v0.1.0

**One product, two layers.** MyMilo is Nrupal's native town-like buddy: the
*resident interface* of his personal agentic OS. The OS (platform: sovereign
memory, persona/state engine, orchestrator, connectors, machine-readable
artifacts) lives underneath; MyMilo is its face — the buddy that runs the
routines, holds the conversations, and talks to him.

Status: Phase 1 (skeleton). This document is the constitution every later
phase is judged against.

## 1. Product thesis

Town's actual edge was never document Q&A — it was proactive routines,
connected email/calendar, suggested tasks, and memory that synthesizes across
days. A town with no routines is a search box. MyMilo is built resident-first:

1. **Routines before retrieval.** The jobs table (Phase 1) becomes the
   proactive engine (Phase 3): briefings, monitors, nudges.
2. **Local-first sovereignty.** Inference and data stay on his hardware by
   default (llama.cpp primary). Cloud is a routed fallback, never the home.
3. **Cost discipline as architecture.** Free-first routing and a per-call
   ledger are load-bearing, not accounting afterthoughts (Phase 4).
4. **Method over narrative.** Decision-critical outputs use scenarios,
   probabilities, triggers, and actions — never unstructured prose alone.

## 2. Converged layering (2026-10-06)

- The **model router and cost ledger live in the OS only**. MyMilo is a
  client of the OS's OpenAI-compatible endpoint.
- Phase 1 ships a minimal in-repo router as a stand-in so the resident works
  standalone. It migrates into the OS in Phase 5; MyMilo's default route then
  points at the OS endpoint. `config/mymilo.example.toml` shows both wirings.
- The persona must be re-derived neutrally — the v1.0 AI OS spec was
  finance-flavored by its origin thread, not by design.

## 3. Boundaries

- **KalaBodha** is the sovereign assistant product built around the
  zero-knowledge vault core. MyMilo is the resident buddy of the agentic OS.
  Overlap risk is real and must be converged explicitly before Phase 2 —
  one of them owns the "assistant" surface, or their split is drawn in this
  document. Not pretended-settled.
- **Milo (Town)** is the register reference: the buddy tone, the proactive
  posture. MyMilo replicates Town's *free* behaviors natively (routines,
  memory synthesis, connectors) — never its credit-burners. Wright keeps the
  free-vs-paid split per the standing fleet doctrine.
- Related work, not duplicated here: `nrupala/agentic-os` (OMEGA-CODE /
  Paradise Stack content needs a migration decision before building there),
  `nrupala/localragcoder` (RAG core to transfer in Phase 2, not re-derive),
  `nrupala/localllm-engine` (orchestration target).

## 4. Principles (standing)

- **Honesty over completeness.** Now / Next / Then status everywhere. Phase 1
  stores job definitions; it does not execute them, and the UI says so.
- **No credentials in the repo.** `vault/` is git-ignored; config names
  variables, never values. Nothing secret is ever logged.
- **Agents are first-class users.** Every surface ships machine-readable:
  OpenAI-compatible API, and from Phase 5 MCP + `/.well-known` + `llms.txt`.
- **Every code ships an interface.** The Jinja2 UI is not decoration — it is
  the operability contract for every endpoint.
- **Dependency-light.** stdlib first (sqlite3, tomllib); few, boring
  dependencies. Scripts beat frameworks.
- **Verified, not asserted.** Behavior-tested before any claim of "done".

## 5. Non-goals for Phase 1

Streaming responses, job execution/scheduling, retrieval/RAG, authentication
(single-user localhost), multi-user, cloud deployment. Each has a named phase.

## 6. Phase map

| Phase | Scope | Exit criterion |
|---|---|---|
| 1 | Skeleton: chat proxy, jobs CRUD, HTML UI, docs, CI | This repo: tests green, behavior-verified live |
| 2 | Retrieval by transfer from localragcoder + evals | Hit-rate / JSON-parse / citation evals pass |
| 3 | Proactive engine: scheduler executes jobs; connectors | A routine runs end-to-end on schedule |
| 4 | Fleet economics: cost router + per-call ledger | Ledger balances against provider dashboards |
| 5 | OS platform layer: router migrates; persona/state; MCP | MyMilo runs as a client of the OS endpoint |

See ROADMAP.md for detail and ARCHITECTURE.md for the build.
