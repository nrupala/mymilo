---
name: user-acceptance-testing
description: Run UAT that means something — business scenarios, realistic data, sign-off criteria, clean feedback loops.
version: 1
triggers: uat, user acceptance, acceptance testing, sign-off, business scenarios
category: Engineering & code
blurb: Run UAT that means something — business scenarios, realistic data and real sign-off criteria.
archetype: knowledge
example: Plan a UAT round that would actually catch business problems.
---

# User Acceptance Testing

UAT is the business saying "this is what we asked for". Run it as a real gate: scenarios from acceptance criteria, realistic data, explicit sign-off.

## When to use
- Before releasing to real users, or handing over a deliverable.
- After major changes to critical flows.
- Whenever "done" needs a definition beyond "tests pass".

## Method
1. **Scope**: map every acceptance criterion to a UAT scenario — end-to-end business flow, not clicks.
2. **Environment**: staging that mirrors production; realistic but **anonymized** data — never live personal data.
3. **People**: business owner owns/executes; the team supports; one scribe.
4. **Scripts**: scenario, steps, expected outcome, pass/fail; timeboxed; deviations logged as defects with severity.
5. **Triage daily**: fix now / accept with note / defer with a date. No silent scope edits mid-UAT.
6. **Sign-off**: explicit — pass, or conditional pass listing open items. Sign-off is an artifact, not a vibe.
7. **After fixes**: re-test changed scenarios + regression on touched flows.

## Quality gates
- [ ] All acceptance criteria mapped to scenarios.
- [ ] Sign-off recorded (or conditional with a named owner).
- [ ] Defects classified and dispositioned.
- [ ] Re-test + regression completed after any UAT fix.

## Red lines
- No UAT on production data without anonymization.
- No "passed" while blockers are open.

## Related
`product-requirements` (criteria source) · `test-design` · `release-management` (the ship gate).
