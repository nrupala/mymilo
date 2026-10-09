# Quality & the release gates

"Verified" means behavior was observed working — never that
files exist, a status was 200, or a commit landed. Every
release passes four gates, in order, all green before the
next build starts. The full doctrine is in
[RELEASE-GATE.md](RELEASE-GATE.md).

## The four gates

1. **Unit tests** — the full pytest suite, 100% pass.
2. **Lint & format** — `ruff check app/` and
   `ruff format --check app/ tests/`, both clean, verified in
   a fresh virtual environment (CI installs `.[dev]` bare).
3. **Frontend harness** — headless Chromium journeys against
   the web UI must verify.
4. **Live behavior** — the deployed build, exercised on the
   production box: health, the release's own behavior proofs,
   and honest cleanup of any test artifacts.

## Merging

CI green on the exact PR head → merge. Never merge red.
Delegated or automated work is verified against the target
system directly (the API, the artifact, the live box) before
it is reported as done — a report is a lead, not evidence.

## Verification records

Each release keeps its record — gates, proofs, and open
notes, including what did **not** verify:

- [v0.42.0](VERIFICATION-RECORD-v0.42.0.md) — guide & skills catalogue
- [v0.41.0](VERIFICATION-RECORD-v0.41.0.md) — skills runnable on purpose
- [v0.40.0](VERIFICATION-RECORD-v0.40.0.md) — unified sources
- [v0.39.0](VERIFICATION-RECORD-v0.39.0.md) — device lifecycle
- [v0.38.1](VERIFICATION-RECORD-v0.38.1.md) — engine savings metric fix
- [v0.37.0](VERIFICATION-RECORD-v0.37.0.md) — engine slice 3
- [v0.36.0](VERIFICATION-RECORD-v0.36.0.md) — engine slice 2
- [v0.35.1](VERIFICATION-RECORD-v0.35.1.md) — engine slice 1
- [v0.26.0](VERIFICATION-RECORD-v0.26.0.md)

## Documentation freshness

Docs are gated too: the skills catalogue doc is generated
from the skills themselves, and a test fails if it drifts
(`tests/test_skills_doc.py`). Claims in these documents are
expected to match the code they describe; when code and docs
disagree, the code is brought up to the docs — or the doc is
corrected in the same change.

See also: [Code guide](CODE-GUIDE.md) ·
[Operations manual](OPERATIONS.md)
