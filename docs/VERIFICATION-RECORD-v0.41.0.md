# Verification Record — v0.41.0 (Skills runnable on purpose)

**Date:** 2026-10-09 · **PR:** #75 · **Head:** `11c3a2d8` · **Merge:** `02e9a840`
**Spec:** `docs/SPEC-v0.41.0-skills-catalog.md` (server half shipped here)

## What shipped

- Chat requests accept an optional `skill` name: the named skill
  is force-activated for the turn (instructions lead; reported in
  `active_skill` and the v0.40.0 sources list), taking precedence
  over trigger matching. Unknown names degrade quietly to a
  normal turn. New `get_skill_by_name` reaches skills by name —
  including the trigger-less majority that matching cannot reach.
- `GET /v1/skills` and `POST /v1/skills/rescan` now require
  authentication (both were open; rescan changes indexed state).
  The two pre-existing platform tests that consumed the listing
  now sign in via their client fixture, as real callers do.

## Gates (RELEASE-GATE.md, in order)

1. **Unit tests:** 170 passed (3 new lookup tests incl. a
   trigger-less skill in a tmp dir; 4 new endpoint tests: forced
   activation, precedence over a trigger match, unknown-name
   degradation, registry auth).
2. **Ruff:** check + format clean.
3. **Frontend harness:** ✅ FRONTEND VERIFIED (no template
   changes in this release; gate run anyway).
4. **Live box:** deployed from main tarball (`02e9a840`);
   `/health` reports **0.41.0**.

## Live behavior proof (box, throwaway device, API host)

- `GET /v1/skills` anonymous → **401**; with device token →
  200, **81 skills** listed.
- Chat with `skill: "stock-analysis"` + "brief me on the market
  today" → `active_skill: "stock-analysis"`; sources =
  [skill: stock-analysis, 5 web results with URLs,
  **market: "Live market brief"**]. The market brief fired
  because the skill was active — closing the gap recorded in
  the v0.40.0 verification record, where the same prompt
  without the skill correctly produced no market source.
- Chat with `skill: "no-such-skill"` → 200, `active_skill`
  null, `sources: []` — quiet degradation as specified.
- Verify device removed afterwards (200).

## Remaining half (build 14, gated on the owner's build-13 walk)

App Skills screen (catalog from the on-device bundle cache,
tap-to-run sheet, on-device favorite pins) and the web Skills
view (bundle-backed, "Using: <skill>" composer state).
