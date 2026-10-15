# Verification Record — v0.47.0 → v0.47.3 (Agent Loop)

**Batch:** the agent loop — MyMilo stops only advising and starts doing multi-step tasks.
**Releases:** v0.47.0 (PR #94, merge `69b93346`), v0.47.1 (PR #95, merge `fa33435d`),
v0.47.2 (PR #96, merge `8c9fd855`), v0.47.3 (PR #97, merge `b547c0da`).
**Final live version:** 0.47.3 on the Aetheris box, deployed 2026-10-15.
**Status under the RC doctrine (2026-10-15): RELEASE CANDIDATE — soak 2026-10-15 → 2026-10-22.**

## What shipped

- `app/agent.py` (new): tasks submitted to `POST /v1/agent/tasks` become jobs on the
  existing jobs engine; a planner proposes steps, a closed allowlist registry decides
  what may run (`model`, `skill`, `oc_bridge`, `conduit`); every step records its tool,
  status, real error, and egress (`leaves_server` + named destination). Bounds:
  max steps 8, per-step timeout 300 s, total wall clock 900 s — a cap ends the task
  `stopped` with the reason, never a hang. Cooperative cancel via a flag in the job row.
- `app/integrations/opencode.py` rewritten against oc-bridge v0.4.0 (MCP streamable
  HTTP, Bearer from `OC_BRIDGE_TOKEN`, initialize handshake, ten-tool client-side
  allowlist, typed errors, fail-closed when unconfigured). The stale client is deleted.
- Endpoints: create (201), list (owner-scoped), get (404 across users — existence is
  not leaked), cancel (200 / 409 on terminal). Unresolvable user = 401 on every host.
- v0.47.1: deterministic fallback adds ONE read-only bridge probe (`opencode_health`)
  when a task clearly signals bridge intent — dispatch-class actions are never added
  by keyword matching.
- v0.47.2: a watcher polls the cancel flag (~2 s) during each step and interrupts it.
- v0.47.3: `_TaskState.save()` merges onto the fresh stored payload (concurrent-writer
  fix, below); the executor's start check reads the fresh payload.

## Gates

1. **Unit tests:** 196 baseline → **238 passed** (final tree, run by the verifier in
   `~/civenv`, not only by the builders). Ruff: `ruff check app tests` clean;
   `ruff format --check app/ tests/` clean. CI green on the exact head of every PR.
   Every merge's branch-vs-main diff was mechanically asserted to equal the intended
   file set before merging.
2. **Release gate (local-release-gate skill):** machine pass **PASS** on the final
   tree (0 secrets in code, 0 known-vulnerable dependencies, no MUST failures).
   Deep review by the verifier: auth resolution shared with chat; owner scoping on
   every read path; egress values derived from the actual route host for model steps
   and named for Conduit; no secret material in code, tests, or logs. Considered
   surface, recorded deliberately: a model-planned task may propose the bridge's
   dispatch-class tools (`oc_send_prompt`, `oc_run_command`) — tasks are
   owner-authenticated, the bridge enforces its own policy, and this is the
   commissioned dispatch capability. NOT RUN, named: browser page-level proof
   (API-only batch, no UI changed); offensive benches (no new public surface —
   the endpoints sit behind the existing device-token/Access auth).
3. **Frontend harness:** not applicable — zero templates/static files in the batch.
4. **Live behavior (gate 4, production box, through the public API host): 11/11.**
   - No token → 401; bad token → 401.
   - Real task ("Check whether OpenCode is healthy using the bridge status tool"):
     steps `skill activate → oc_bridge opencode_health → model chat`, all completed;
     result "OpenCode is healthy on this server." — derived from the real bridge call;
     egress recorded `leaves_server: false` ("oc-bridge on this server (OpenCode)").
   - Second user reading the first user's task → 404.
   - Cancel of a running task → 200, task lands `stopped`, reason "cancelled by user".
   - Deployed bridge client called directly: `opencode_health` →
     `{'healthy': True, 'version': '1.18.21'}`.
   - Conduit with no key on the box fails closed: "CONDUIT_API_KEY not configured" —
     never a fabricated answer.

## Defects found by gate 4 and fixed inside the batch

1. **Weak-planner reach (v0.47.0):** the resident planner (Phi-4-mini via the `os`
   route) failed to emit a valid JSON plan for the bridge task; the deterministic
   fallback answered without touching the bridge. Fixed in v0.47.1 (read-only
   planner-independent probe above). The planning ceiling is the resident model's —
   recorded as a known wart, not hidden: `plan_source` is stored on every task.
2. **Cancel clobber (v0.47.0–0.47.2):** the executor saved progress from a snapshot
   dict, overwriting the cancel endpoint's flag — cancel silently lost in production
   while every unit test passed (single-writer tests). Found by gate 4 twice; root
   cause identified from the code; fixed in v0.47.3 (merge-on-save). Regression tests
   use a genuine second writer and fail on the pre-fix code (verified by the builder
   against a pristine v0.47.2 copy, and by the final live probe).

## Known warts carried forward

- Planner quality is bounded by the resident model; tool-rich plans will improve
  when the box memory question (Qwen3 switch) is settled or a stronger planner
  route is configured. The deterministic fallback covers the common bridge checks.
- The `os` route's dispatcher can return refusal strings as content (observed
  2026-10-15: "refused: no valid proposal within 3 attempts" as a step result) —
  an upstream behavior of the default route, visible in step logs, not masked.
- `CONDUIT_API_KEY` is not yet provisioned on the box (operator step); Conduit
  steps fail honestly until it is.
- The phone apps do not yet surface agent tasks (no agent view in Android build 37
  or iOS v1) — the loop is API-live; app surfacing is the next app builds' work.
- Background-job sources gap (pre-existing, v0.40.0) unchanged by this batch.

## Timing note

Deployed the morning of 2026-10-15 (Moon Scorpio/Jyeshtha, no Chandrashtama for
either chart, all acts completed before Rahu Kaal 14:42–16:02 MDT).
