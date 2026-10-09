# Verification Record — v0.36.0 (Token-Efficiency Engine, slice 2)

**Date:** 2026-10-09 · **Release:** PR #66, head `9d217883`, merge `6a509e1a`.
**Feature:** two-tier context assembly (`app/context_tiers.py`) + compaction
checkpoint v2 (coverage columns on `session_summaries`).

## Gate 1 — unit tests
- 144 passed (129 pre-existing + 15 new in `tests/test_context_tiers.py`),
  including an endpoint test with a capturing stub backend that asserts the
  assembled prompt order (summary tier → dynamic time block → history →
  current turn) and a v1→v2 schema migration test.
- Verified in the CI-faithful fresh venv and in GitHub CI on the exact head.

## Gate 2 — ruff
- `ruff check` and `ruff format --check` clean, local venv + CI.

## Gate 3 — frontend harness
- `pw-frontend-test.py`: ✅ FRONTEND VERIFIED (9/9) on the slice-2 tree.

## Gate 4 — live box behavior (public API host, device-token auth)
- `/health`: version 0.36.0, service active, all backends up.
- Production DB migration observed: `session_summaries` gained
  `covered_from`, `covered_count`, `model` after restart.
- **Long-session run:** 32 scripted turns (model `local`, one session)
  through `https://mymilo-api.aimlds.org` — all 200; 64 messages stored.
- **Checkpoint v2 written by the real summarizer:** row present with
  `covered_from=112`, `covered_count=1`, `model='local'`,
  `summarized_up_to=114`, non-empty summary (38 chars — the synthetic
  content compresses to a line).
- **Post-compaction turn (33):** asked for the code word from turn 3 —
  answered correctly ("falcon-3") from compacted context.
  `token_plan`: estimated_input **655 tokens**, utilization **0.08** on a
  66-message session — the window stays bounded as designed.
- **Prefix cache observed working:** llama.cpp `timings` on turn 33 show
  `cache_n=178` of `prompt_n=430` — 178 stable-prefix tokens were reused
  from the KV cache instead of reprocessed. This is the slice-2
  cache-stability fix (dynamic clock block moved behind the stable
  prefix), visible in the backend's own counters. (Prompt processing
  itself ran slow during the run — the test's own 32 turns plus
  background summarizers loading a 4-OCPU box; correctness unaffected.)

## Finding (wart, recorded honestly)
- The incremental summarizer fires as a background task per turn; racing
  runs chain off each other's checkpoints, so `covered_count` recorded
  the **final slice's** count (1), not cumulative coverage, and the
  checkpoint lagged the session head at snapshot time
  (`summarized_up_to=114` of ~176). It keeps advancing on later turns and
  the summary *content* was correct (turn-33 recall proved it), but the
  coverage metadata is slice-local where it should be cumulative.
- **Queued fix:** cumulative coverage accounting (preserve the first
  checkpoint's `covered_from`; `covered_count` = messages folded so
  far) + a per-session in-flight guard for the summarizer. Rides the
  next release.

## Cleanup
- Verify session deleted (messages + summary row), test device revoked,
  token files shredded on the box.
