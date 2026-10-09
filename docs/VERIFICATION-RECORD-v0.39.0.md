# Verification Record — v0.39.0 (Device lifecycle)

**Date:** 2026-10-09 · **PR:** #71 · **Head:** `79157279` · **Merge:** `aaf329b0`

## What shipped

- `DeviceStore.rotate()` — same device row, new token hash; the old
  token stops working immediately. Exposed as
  `POST /v1/devices/{id}/rotate` (one-time plaintext token returned).
- `DeviceStore.delete()` — permanent removal of a device row, active
  or revoked. Exposed as `POST /v1/devices/{id}/remove`.
- Revoke (`DELETE /v1/devices/{id}`) unchanged.
- `/devices` page rewritten to the simplicity standard (owner's
  directive, 2026-10-09): plain words ("Your devices", "New token",
  "Disconnect", "Remove"), consequences on the button itself with
  two-tap inline confirms (no browser prompt/confirm dialogs), human
  connection status ("connected · used today"), inline name field,
  friendly empty state. Motivation: revoke-only UI forced a fresh
  registration for every token refresh, piling up dead rows.

## Gates (RELEASE-GATE.md, in order)

1. **Unit tests:** 162 passed (was 160; +1 store test covering
   rotate/delete/revoke interplay, +1 endpoint test). One test bug
   found and fixed during the gate: the endpoint test initially
   asserted a 401 for a dead token on the browser host, where the
   pre-existing semantics return an empty list (200); the auth guard
   (401) lives on the API host. The test now exercises the real
   native-client path with an API-host Host header.
2. **Ruff:** `ruff check app/` clean; `ruff format --check app/
   tests/` clean (62 files).
3. **Frontend harness:** ✅ FRONTEND VERIFIED (headless Chromium,
   4 journeys / 9 checks).
4. **Live box:** deployed from main tarball (`aaf329b`); service
   active; `/health` reports version **0.39.0**, all backends up.

## Live behavior proof (box, throwaway identity)

Through the real HTTP endpoints on the production service:

- register → 200; token authenticates on the API host → 200.
- rotate → 200; new token differs; **old token → 401** on the API
  host; **new token → 200**.
- device list shows exactly one row for the device (no pile-up).
- remove → 200; list empty for that device; its token → 401;
  second remove → 404.
- The legacy leftovers of earlier verification runs (7 revoked test
  devices) were then deleted through `DeviceStore.delete()` — the
  verify identity is back to 0 rows.
- `GET /devices` serves the new page (markers: "Your devices",
  "New token", "Disconnect", "No devices yet").

## Known wart (noted, not fixed — out of scope)

`app.state.devices` and the semantic store are constructed with a
hardcoded `/opt/mymilo/data` path in the app lifespan; tests
override `app.state.devices` directly. Portability cleanup for a
future release.
