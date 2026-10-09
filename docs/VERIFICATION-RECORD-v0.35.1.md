# Verification Record — v0.35.0 / v0.35.1 (Token-Efficiency Engine, slice 1)

**Date:** 2026-10-09 · **Releases:** PR #64 (v0.35.0, head `382d9fc2`, merge
`7da94714`) and PR #65 (v0.35.1, head `0b6acf9d`, merge `60514845`).
**Feature:** per-route token registry + `plan_max_tokens()` planner +
n_ctx guard (`app/tokenplan.py`), per ENGINE-SPEC-v1 slice 1.

## Gate 1 — unit tests
- v0.35.0: 128 passed (112 pre-existing + 16 new in `tests/test_tokenplan.py`).
- v0.35.1: 129 passed (+1 os-registry test).
- Verified in a CI-faithful fresh venv (`pip install -e ".[dev]"`) and in
  GitHub CI on the exact PR heads (both runs green before merge).

## Gate 2 — ruff
- `ruff check app tests` clean; `ruff format --check app tests` clean,
  locally (fresh venv) and in CI.

## Gate 3 — frontend harness
- `pw-frontend-test.py`: ✅ FRONTEND VERIFIED on the slice-1 tree
  (9/9 checks) for both releases (0.35.1 touched no frontend code).

## Gate 4 — live box behavior (mymilo-api.aimlds.org, device-token auth)
Deployed to /opt/mymilo, production registry: local = 8192/1024/4096,
openrouter = 131072/4096/16384, os = 8192/1024/4096 ([os] section; window
matches the dispatcher upstream Phi-4-mini `--ctx-size 8192`).

- `/health`: version 0.35.0 → 0.35.1, service active, all backends up.
- No token → 401; valid token → `/v1/client/config` 200.
- Skills bundle: 81 skills.
- Oversized request (176K chars, model `local`): **400** with the plain
  refusal ("This conversation has grown too large for the model's
  context window…") — the n_ctx guard firing live.
- Chat `auto`/"hi" → routed `os`, `token_plan` present: window 8192,
  estimated_input 408 (source `estimate` — the dispatcher exposes no
  /tokenize; fallback works as designed), planned_max_tokens 1024,
  fits true, utilization 0.0498.
- Chat `local`/"hi" → `token_plan` with **estimate_source `tokenizer`**
  (estimated_input 291 counted by Phi-4-mini's own /tokenize).
- Test device tokens were created and revoked on the box; token values
  never left the box.

## Findings from verification (the gate earning its keep)
1. v0.35.0's first live check showed `auto` traffic routes to the `os`
   route (AxiomSpine dispatcher), which had no registry — the default
   path was unplanned. Fixed in v0.35.1 (OSConfig registry fields) and
   re-verified live (above).
2. Real windows on Aetheris are set by llama.cpp flags, not model
   marketing: Phi-4-mini runs `--ctx-size 8192`. The spec table was
   corrected to serving reality.

## Not verified / not claimed
- OpenRouter route planning is unit-tested and registered live, but no
  live cloud chat was run for this slice (no-spend discipline).
- Estimator calibration against actual usage (estimate vs prompt_tokens
  bias) is slice 4 telemetry, not yet built.
- Trimming of a real multi-turn session history was unit-tested; the
  live oversized case exercised the refusal branch (single huge turn).
