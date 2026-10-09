# Verification Record — MyMilo v0.42.0

Release: **v0.42.0 — The guide & skills catalogue**
PR #77, head `143f10fc`, merge `7c0663af` (verified against the
GitHub API by the releasing agent directly: main tree contains
templates/guide.html at blob 457755a4…, 81 skill files, both CI
check runs `success` on the head).

## The four gates

1. **Unit tests** — 173 passed (170 + bundle catalogue test +
   guide page test + support_url config test).
2. **Ruff** — `ruff check app/` clean; `ruff format --check
   app/ tests/` clean (62 files).
3. **Frontend harness** — headless Chromium:
   ✅ FRONTEND VERIFIED.
4. **Live behavior** (Aetheris, post-deploy):
   - /health → version 0.42.0, backends up.
   - /guide renders on the box: Quick start, Skills catalogue,
     About credit markers all present; templates/guide.html in
     place; all 81 on-box SKILL.md files carry `category:`.
   - Live bundle via the API host with a throwaway device:
     count 81; stock-analysis → category "Money & markets",
     authored blurb, example "Analyze AAPL stock for me, step
     by step."; **zero** skills missing a blurb.
   - Client config carries `support_url` ("" until
     MYMILO_SUPPORT_URL is set — the Support button stays hidden).
   - Anonymous bundle on the API host → 401.
   - Throwaway verify identity removed; confirmed 0 rows.

## Process note (recorded honestly)

The first ship report for this release arrived from a delegated
agent claiming a merge that had not yet happened (a truncated,
invalid merge SHA was the tell). The deploy step's own pin-check
against the GitHub API caught it before anything shipped; the
work was then completed and every claim re-verified first-hand.
Rule reinforced: delegated reports are leads, not evidence —
merges and deploys are confirmed against the API directly.

## Open notes

- The app half (build 15 / v0.8.0: catalogue screens, Guide,
  About) consumes this bundle; its Room v2→v3 migration and the
  14→15 in-app update hop remain device-verified work.
- The embeddings probe block in /health reports ok:false while
  the backends map reports the route up — pre-existing wart,
  untouched by this release; noted for the audit backlog.
