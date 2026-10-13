---
name: test-design
description: Design test cases that find real bugs — partitioning, boundaries, decision tables, state machines, pairwise.
version: 1
triggers: test design, test cases, boundary testing, decision tables, pairwise
category: Engineering & code
blurb: Design test cases that find real bugs — partitioning, boundaries, decision tables, state machines.
archetype: knowledge
example: Design tests that would actually catch bugs in this feature.
---

# Test Design

Good testing is designed, not improvised. Choose techniques by risk, write cases before execution, and trace them to requirements.

## When to use
- Turning requirements/PRDs into test cases.
- Reviewing existing suites for blind spots.
- Planning coverage before a build or regression run.

## Method
1. **Equivalence partitioning**: group inputs into classes; one representative + the edges per class — not every value.
2. **Boundary value analysis**: test just-below / at / just-above each boundary (0, 1, max, max+1; empty, one, many).
3. **Decision tables**: enumerate condition combinations; cover the interesting rules, including the awkward ones.
4. **State transition testing**: model the states; test allowed transitions, forbidden transitions, and interrupts.
5. **Pairwise / combinatorial**: for many config axes, cover all pairs instead of the full cross-product.
6. **Negative + error guessing**: invalid inputs, wrong order, retries, partial failure — accidents and attackers live here.
7. **Risk-based selection**: rank by (damage × likelihood); highest first; state explicitly what is NOT tested.
8. **Case format**: id, level, preconditions, steps, expected result — written BEFORE running; traceable to requirements.

## Quality gates
- [ ] Every requirement traced to at least one case.
- [ ] Boundaries and negatives present (not just happy paths).
- [ ] Expected results written before execution.
- [ ] Coverage gaps stated explicitly.

## Red lines
- No case without an expected result; no copy-paste suites that re-test the same path five times.

## Related
`testing-strategy` · `user-acceptance-testing` · `poc-validation`.
