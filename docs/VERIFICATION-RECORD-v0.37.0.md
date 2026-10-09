# Verification Record — v0.37.0 (Token-Efficiency Engine, slice 3)

**Date:** 2026-10-09 · **Release:** PR #67, head `9940948d`, merge `c625fb26`.
**Feature:** router health gate + backpressure + ordered degradation;
summarizer in-flight guard + cumulative checkpoint coverage.

## Gate 1 — unit tests
- 152 passed (144 + 8 new in `tests/test_router_resilience.py`): gate
  opens after 2 failures and fails fast (transport untouched), gate
  recovers after cooldown, busy error when the single slot is held past
  the queue wait, concurrency defaults (local 1 / cloud 8), endpoint
  degradation for `auto`, no degradation for explicit `local`,
  summarizer cumulative coverage chaining, in-flight guard (two
  concurrent runs → one summarization).
- The test suite caught a real bug pre-ship: `covered_from=0` was
  treated as missing by an `or` fallback; fixed with an explicit
  None check.
- Fresh CI-faithful venv + GitHub CI on the exact head: green.

## Gate 2 — ruff
- Check + format clean, local venv + CI.

## Gate 3 — frontend harness
- ✅ FRONTEND VERIFIED (9/9) on the slice-3 tree.

## Gate 4 — live box behavior (public API host, device-token auth)
- `/health`: version 0.37.0; route stats now show `gated`,
  `in_flight`, `max_concurrency` (local 1, os 1, openrouter 8 —
  `max_concurrency` also written into the production TOML).
- **Backpressure, observed:** 3 concurrent long generations against
  Phi's single slot — request 1 completed 200 in 97.8s (a full-length
  answer); requests 2 and 3 each received **503 backend_busy at
  30.3s** — exactly the configured queue wait, then a clear signal
  instead of a silent pile-up. Total wall 98s: rejected requests
  consumed no backend time. This is the designed behavior; the 30s
  wait is tuned for interactive use (a caller behind a ~98s
  generation gets a truthful busy + can retry, not a 3-minute hang).
- **Checkpoint coverage fix, observed:** one session read at two
  points — after 20 turns: `covered_from=0, covered_count=14`; after
  26 turns: `covered_from=0` (unchanged), `covered_count=20` (grew),
  `summarized_up_to=176`, 52 messages total (20 covered + 20 raw-kept
  + 12 newest tail = consistent). The slice-2 wart (coverage recorded
  as 1) is fixed in production behavior.
- Test session deleted, device revoked, token files shredded.

## Not live-tested (stated plainly)
- The health gate's fail-fast path was not exercised against the
  production Phi backend — deliberately: proving it live would mean
  breaking the production model server. It is covered by unit tests
  (transport-level failure injection) and the endpoint integration
  test (degradation to cloud on a down local route, 503 for explicit
  local). If a real backend outage occurs, `/health` route stats will
  show `gated: true` and the behavior will be observable then.
