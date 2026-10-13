# Verification record — v0.46.0 (Support row: both links)

Released 2026-10-12. PR #91 (final head `0ec66f3c`), merge
`d5f42571`, deployed to the Aetheris box the same evening.

Implements the owner's 2026-10-12 decision: the Support row
carries both existing links — Buy Me a Coffee primary,
PayPal second — with no new account. Client config returns
`support_links`; `support_url` keeps mirroring the primary
for older clients; the guide page renders one button per
link under "Support MyMilo".

## The four gates

1. **Unit tests** — 196 passed locally in the CI-faithful
   venv on the final tree (incl. new
   `test_client_config_support_links`); CI `build-and-test`
   green on the exact PR head.
2. **Lint/format** — `ruff check app/` clean;
   `ruff format --check app/ tests/` clean.
3. **Frontend harness** — ✅ FRONTEND VERIFIED.
4. **Live behavior** — verified on the production box after
   deploy, first-hand (throwaway device, removed after):
   - `/health` reports version **0.46.0**, all backends true.
   - `GET /v1/client/config`: support_url =
     https://buymeacoffee.com/nrupalakolt; support_links =
     [{Buy Me a Coffee, BMC URL}, {PayPal,
     https://paypal.me/nrupalakolkar}] — exactly the decided
     pair, in order.
   - `GET /guide` serves the support-links container and the
     script that renders both buttons from the config.
   - Production .env updated at deploy (backup kept
     box-side); the GitHub Sponsors URL is retired as the
     button's destination.

## Notes

- **Process incident, caught by the gates:** the first CI
  run on this PR failed `tests/test_conduit.py` — the local
  build tree was stale (it predated the v0.44.0 Conduit
  merge), so the pushed `app/main.py` lacked the Conduit
  tools merge. Local gates had passed against the stale
  tree. Fix: rebuilt the tree from current main, re-applied
  only the intended delta, re-ran all gates (196 tests),
  pushed a corrective commit; the merge then asserted the
  branch's total diff vs main was exactly the five intended
  files. Standing fix recorded in AGENTS.md: whole-file
  pushes are preceded by a fresh-main diff, and merges
  assert the branch-vs-main diff equals the intended delta.
- The Android app's About section renders both links when
  the next app build ships; today's app already lands on
  Buy Me a Coffee via the mirrored `support_url`.
