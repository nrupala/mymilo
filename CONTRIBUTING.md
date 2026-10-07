# Contributing to MyMilo

## Workflow

1. Branch from `main`: `wright/<short-scope>`.
2. One workstream per commit; changelog entry per user-visible change.
3. Open a **draft PR** — never push to `main`, never merge. Nrupal merges.
4. Every source file carries the license header:
   `# SPDX-License-Identifier: AGPL-3.0-or-later` + copyright line.

## Gates (all must pass)

```bash
ruff check app tests && ruff format --check app tests && python -m pytest -q
```

CI runs install → lint → format → test on every push/PR. Warnings are errors.

**CI-faithful venv rule:** CI installs `.[dev]` into a bare runner — a
dependency that only exists incidentally in your ambient dev env passes
locally and fails CI. After dependency changes, reproduce in a clean venv
before pushing:

```bash
python -m venv /tmp/civenv && source /tmp/civenv/bin/activate
pip install --no-cache-dir -e ".[dev]"
ruff check app tests && ruff format --check app tests && python -m pytest -q
```

**Green-merge rule:** merge only when CI is green on the PR's exact head
SHA. Never merge red. Wright may merge under Nrupal's standing grant;
otherwise Nrupal merges.

## Behavior verification

Unit tests use `httpx.MockTransport` (no network). Before claiming anything
works, verify behavior over real HTTP:

```bash
# terminal 1: stub OpenAI-compatible backend
python3 tests/stub_backend.py   # :8081, echoes canned completion
# terminal 2: MyMilo pointed at the stub
MYMILO_CONFIG=tests/stub-config.toml mymilo
# terminal 3: assert
curl -s localhost:8090/health
curl -s localhost:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"stub","messages":[{"role":"user","content":"hi"}]}'
```

"Verified" means observed behavior, never files-present.

## Documentation bar (ASF-grade)

README (overview/quickstart/build/test/usage), ARCHITECTURE, SPEC,
ROADMAP, CHANGELOG entry per release, license headers, release notes per
release, design docs for significant work. If docs and code disagree, bring
the code up to the docs.

## Secrets

Never commit credentials. `vault/` is git-ignored; config names env vars,
not values. If you touch auth paths, double-check nothing secret reaches
logs or error responses.
