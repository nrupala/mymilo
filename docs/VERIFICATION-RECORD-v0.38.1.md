# Verification Record — v0.38.0 + v0.38.1 (Token-Efficiency Engine, slice 4)

**Date:** 2026-10-09 · **Releases:** PR #68 (v0.38.0, head `d083b9ef`,
merge `551bc890`) and PR #69 (v0.38.1, head `336a4457`, merge
`59948d8f`).
**Feature:** engine telemetry (`engine_telemetry`, schema v6 → v7),
`GET /v1/engine/rollup`, `/health` engine summary — and a
definition fix to the savings metric caught by the first live data.

## Gate 1 — unit tests
- v0.38.0: 159 passed (7 new in `tests/test_telemetry.py`).
  v0.38.1: 160 passed (savings-math reworked + a regression test that
  pre-fix rows without `conversation_tokens` are excluded from the
  comparison). Fresh CI-faithful venv + GitHub CI on both exact
  heads: green.

## Gate 2 — ruff
- Check + format clean for both releases, local + CI.

## Gate 3 — frontend harness
- ✅ FRONTEND VERIFIED (9/9) on both trees.

## Gate 4 — live box behavior (public API host, device-token auth)
- v0.38.0 deploy: `/health` reports 0.38.0 with a live `engine`
  block; `engine_telemetry` table created (schema 6).
- **Telemetry from real traffic:** two scripted sessions (9 + 18
  turns, all server-completed; one response was cut by the tunnel
  with a 524 while the server finished and recorded the turn) plus a
  3-turn confirmation on v0.38.1 — 30 requests recorded day-one.
- **Estimator accuracy, observed:** the tokenizer-based estimate
  tracked actual prompt tokens within ~2% on every recorded turn
  (e.g. 1109 est / 1102 actual; 312 / 307).
- **Cache reuse, observed:** rollup `cache_reuse_pct` 10.9% → 13.0%
  as same-session turns accumulated. Per-turn rows show `cache_n`
  pinned at 176 tokens on the first session — only the persona
  prefix is being reused, because Phi's single slot is shared with
  other traffic (the OS dispatcher path and other sessions
  interleave and truncate prefix matching). Recorded as the next
  optimization target (slot discipline), with numbers.
- **Metric definition error — caught and fixed (v0.38.1):** the
  first rollup reported **−48.7% "savings"** because v0.38.0 compared
  a transcript-only baseline against the whole actual prompt (fixed
  overhead included). The comparison is now conversation-only on
  both sides (`full_history_tokens` vs the new `conversation_tokens`
  column, schema v7 via guarded ALTER — verified applied on the
  production DB). On the 3-turn confirmation session the corrected
  figure reads −13.7% over 300 baseline tokens: conversation-sent
  includes per-message overhead and the retrieval tier, which the
  raw-transcript baseline does not — the expected small-session
  behavior. Structural savings appear as sessions lengthen (slice 2
  evidence: a 66-message session served at 655 estimated input
  tokens, 8% window utilization).
- Estimator bias: `null` with 0 samples — correct: bias is computed
  only over estimator-sourced rows; all live rows so far are
  tokenizer-sourced (exact by construction).
- Test sessions deleted, devices revoked, token files shredded after
  every run (one harness timeout in run 1 left a device + token
  file behind; both were cleaned in the follow-up pass before any
  further work).

## Engine program status
All four slices of ENGINE-SPEC-v1 are live: registry + planner +
n_ctx guard (v0.35.x), two-tier assembly + compaction checkpoints
(v0.36.0), router resilience (v0.37.0), telemetry + rollup
(v0.38.x). The engine now plans every prompt against the real
serving window, assembles context in cache-stable tiers, degrades
honestly under failure or load, and measures itself.
