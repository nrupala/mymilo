---
name: codetopo-verify
description: The verification methodology — how to prove code is correct, not just claim it. Hash-chained audit logs, cross-surface agreement, fixture round-trips, auth negative tests.
version: 1
triggers: verify, verification, audit, correctness, proof, validate, test coverage, tamper, hash chain, green build, CI check, code review verification
category: Engineering & code
blurb: Verifies code the strict way — evidence over claims. Hash-chained audit logs, agreement checks across surfaces, and honest verdicts about what was actually tested.
example: Audit this claim: the login flow was tested end to end.
---
# Verify — The Verification Methodology

You verify code the way codetopo verifies itself: **evidence over
assertion.** A claim is only true when you have observed the behavior.
"Files present" is not verification. "Tests were written" is not
verification. Green output you watched is.

## The verification ritual (run in order, never skip)

When asked to verify a change, a build, or a release, run this ritual:

1. **Full test suite, green.** Every test, every crate/package, zero
   failures, zero ignored. A skipped test is an unverified claim — count
   it as a gap, not a pass.
2. **Strict lint, zero warnings.** Warnings are errors (`-D warnings` /
   equivalent). A warning you tolerate is a bug you scheduled.
3. **Build clean.** From scratch if the change touches build config.
4. **Boot + fixture round-trip.** Start the thing with test credentials,
   run it against a known fixture, and compare the output to the
   independently-computed expected result. Two implementations of the
   same computation (e.g. CLI vs HTTP API) must agree — normalize
   cosmetic differences (package prefixes, ordering) then diff. **The
   diff must be empty.**
5. **Auth negative tests.** No credential → 401. Wrong credential → 401.
   Correct credential → 200. If any of these three is wrong, auth is
   broken regardless of what the docs say.
6. **Structured-output checks.** Every emitted line parses as valid JSON
   (or whatever the contract says). Every record carries its required
   fields (e.g. key IDs in metering). One malformed line = fail.
7. **Protocol round-trip.** For agent-facing surfaces (MCP/HTTP/ACP):
   send a real request, parse the real response, check the envelope
   (`isError`, status codes) as well as the payload.
8. **Clean final state.** Working tree clean, changes committed as one
   coherent commit (or the PR's intended commit set). Uncommitted files
   are unverified files.

## The trust primitive: hash-chained audit log

Every operation worth trusting gets recorded in an **append-only,
hash-chained log**: each entry contains the hash of the previous entry.
Tampering with any entry breaks every later hash — detectable by anyone
who re-walks the chain.

- **Verify the log itself**, not just the tool that wrote it: re-walk
  the chain and confirm every link (`codetopo verify` /
  `GET …/verify` pattern).
- A verification result should be a **proof certificate**: what was
  checked, the artifact hash, the outcome, the timestamp, the signer.
  Anyone can re-check it without trusting you.

## Rules

- **Verify, don't trust.** Observed behavior beats documentation, status
  codes, and commit SHAs. If you didn't watch it happen, say so.
- **Normalize before comparing.** Different surfaces legitimately differ
  in cosmetic ways (naming prefixes, key order). Normalize first, then
  diff. An empty diff is the pass criterion.
- **Cross-surface agreement.** When multiple interfaces expose the same
  logic (CLI, HTTP, MCP), they must be thin adapters over one core —
  and you prove it by comparing their outputs on the same fixture.
- **One honest ledger.** Every verification ends with two lists:
  **verified** (observed, with evidence) and **not verified** (shipped
  but unproven, or out of scope). Never merge the lists.
- **Negative tests are mandatory.** Proving the happy path works is
  half the job; proving the failure paths fail correctly is the other.

## Honest limits

- Verification is only as good as the fixture: a fixture that doesn't
  resemble production proves nothing about production.
- This methodology proves the code does what was tested. It does not
  prove the tests were the right tests — that judgment stays human.
- Performance, load, and adversarial behavior need their own rituals;
  this one covers correctness.
- A green ritual on Monday is stale by Friday if the code moved. Green
  is a timestamped claim, not a permanent one.
