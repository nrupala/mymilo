# Verification Record — v0.40.0 (Unified sources)

**Date:** 2026-10-09 · **PR:** #73 · **Head:** `cb0f4e29` · **Merge:** `3412afc5`

## What shipped

- Every chat response now carries a `sources` list: what the turn
  actually used, in the order gathered — the active skill,
  retrieval-tier memory facts and past-chat episodes (the tier now
  reports provenance for the items it included), live web results
  (title + URL) when a freshness search ran, the live market brief
  when one was built, and RAG document chunks when documents were
  enabled. Always present (empty list when nothing was used),
  deduplicated by (type, title). Legacy `active_skill` /
  `rag_sources` fields retained.
- Web UI renders a "Sources: …" line from the new field (replacing
  the 🛠 skill-prefix hack) and keeps it out of the history resent
  to the server.

## Gates (RELEASE-GATE.md, in order)

1. **Unit tests:** 163 passed (tier tests updated for the new
   (text, sources) return + sources-content assertions; new chat
   contract test: `sources` always present and well-formed).
2. **Ruff:** check + format clean.
3. **Frontend harness:** ✅ FRONTEND VERIFIED.
4. **Live box:** deployed from main tarball (`3412afc5`); service
   active; `/health` reports version **0.40.0**.

## Live behavior proof (box, throwaway device, API host)

- "Brief me on the market today" → 200 with **5 web sources**,
  real titles + URLs (WSJ, Barron's, GV Wire, Kiplinger,
  Briefing.com) — the freshness-search path fired and reported
  itself. The market-brief source did not appear on this prompt:
  by design it requires the stock-analysis skill to be active
  (`wants_market_brief` gates on the skill), and this prompt did
  not match that skill. Not a defect; the market source is
  covered by code path + will appear on skill-matched briefs.
- "Say hello in one short sentence." → 200, `sources: []` —
  the contract holds: nothing used, nothing claimed.
- Verify device removed afterwards (200).

## Known gap (stated, not hidden)

Background-job chat results do not carry `sources` yet — the job
envelope predates the field. Normal (synchronous) turns, which
are the default path, all carry it.
