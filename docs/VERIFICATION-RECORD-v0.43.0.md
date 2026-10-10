# Verification record — v0.43.0 (Skill Pair data in the bundle)

Released 2026-10-09. PR #81 (head `aee2ca2a`), merge
`2879760d`, deployed to the Aetheris box the same evening.

## The four gates

1. **Unit tests** — 179 passed locally in the CI-faithful
   venv (174 + 5 new pair-data tests in
   `tests/test_skill_pairs.py`).
2. **Lint/format** — `ruff check app/` clean;
   `ruff format --check app/ tests/` clean.
3. **Frontend harness** — headless Chromium suite against
   the web UI: ✅ FRONTEND VERIFIED.
4. **Live behavior** — verified on the production box after
   deploy, first-hand:
   - `/health` reports version **0.43.0**, all backends true.
   - Authenticated bundle (throwaway device): 81 skills;
     budget-engine → archetype `engine`, layout steps begin
     "Income picture", artifact `document`; stock-analysis →
     `analyst` / `brief`; electrical-code → `reference`,
     blocks [Answer, Why, Proof, Limits]; clarity (unpaired)
     → `knowledge` / {} — defaults hold fleet-wide.
   - Anonymous bundle request on the API host → **401**.
   - Throwaway device removed; 0 verify rows remain.

## Notes

- Pair data is frontmatter-authored (`archetype` + one-line
  JSON `layout`); a malformed layout degrades to {} in
  `_pair_fields` — covered by tests.
- The app half (Room v4, workspace shell, composer +) ships
  as native build 17 (v0.9.0); until then, older clients
  ignore the new bundle fields harmlessly.
