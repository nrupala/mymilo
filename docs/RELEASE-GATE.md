# MyMilo Release Gate (standing rule, 2026-10-07)

**Build − verification = patched product.** No build ships until all four gates are green. No exceptions.

## The four gates

Run in order. Every gate must pass before the next build starts.

### Gate 1: Backend unit tests
```bash
cd ~/workspace/mymilo-build
python3 -m pytest tests/ -q
```
Must be 100% pass. Fix failures in the working tree before pushing.

### Gate 2: Lint
```bash
python3 -m ruff check app/
python3 -m ruff format --check app/ tests/
```
Both must be clean. `ruff check` catches errors; `ruff format --check` catches
formatting. CI runs both — the gate must match CI exactly.

### Gate 3: Frontend (headless Chromium)
```bash
~/workspace/pw-test/bin/python ~/workspace/mymilo-book/pw-frontend-test.py
```
Loads the real Jinja templates in headless Chromium, stubs the API,
and runs the full user journeys:
- send message → session set
- export → picker appears → md downloads
- delete → session cleared, backend deleted, log fresh
- new chat after delete

Must print `✅ FRONTEND VERIFIED`. Any JS runtime error fails the gate.
This is the gate that catches what syntax checks and curl cannot —
the three frontend bugs Nrupal found live (2026-10-07) were all
runtime errors no backend test could see.

Harness source: `~/workspace/mymilo-book/pw-frontend-test.py`
Playwright venv: `~/workspace/pw-test/`

### Gate 4: Live box behavior
After deploy, confirm on the box:
```bash
ssh ubuntu@147.224.174.50 'curl -s -m 8 http://127.0.0.1:7071/health'
sudo systemctl is-active mymilo.service
```
Version must match the release. Skills count must match. Service active.

## The rule

**Verify every build before building next.** A release is "done" only
when all four gates are green on the exact head that ships. "CI green"
alone is not enough — CI runs gates 1 and 2. Gates 3 and 4 are the
human-verified layers that make it the Muse way.
