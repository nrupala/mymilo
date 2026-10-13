---
name: product-requirements
description: Turn a fuzzy idea into an approved PRD — user stories, acceptance criteria, scope boundaries, and priorities.
version: 1
triggers: prd, product requirements, user stories, acceptance criteria, scope, spec
category: Engineering & code
blurb: Turn a fuzzy idea into an approved PRD — user stories, acceptance criteria and scope boundaries.
archetype: knowledge
example: Turn this idea into a PRD with acceptance criteria.
---

# Product Requirements — the PM seat

Convert a problem or idea into a buildable, testable specification. Nothing enters build without an approved spec (phased delivery).

## When to use
- A new product/feature/change is proposed ("build X", "add Y").
- Scope is drifting or ambiguous mid-build.
- Priorities must be set, defended, or re-cut.

## Method
1. **Problem first**: state the problem, who has it, and why now — five sentences or fewer.
2. **Outcome over output**: define the observable change (behavior or metric), not just the feature.
3. **Stories**: `As a <role>, I want <capability>, so that <benefit>` — one per behavior.
4. **Acceptance criteria**: testable and binary per story (given/when/then is fine). If it can't be tested, it's not a criterion.
5. **Scope fences**: an explicit **out-of-scope** list; deferrals go to a "later" list — never silently inside.
6. **Prioritize**: P0 (must ship) / P1 (should) / P2 (could). Resolve conflicts with the decision owner; log the decision.
7. **Open questions**: tracked explicitly; block build only on questions that change architecture.

## Artifacts
- `PRD.md`: problem, outcome, stories, acceptance criteria, out-of-scope, priorities, open questions.

## Quality gates
- [ ] Every story has testable acceptance criteria.
- [ ] Out-of-scope list exists; no "misc" bucket.
- [ ] P0 items are shippable alone.
- [ ] Key decisions logged (see `delivery-planning`).

## Red lines
- No build before an approved spec (exceptions: timeboxed spikes, labeled as such).
- Never widen scope mid-phase without updating the PRD and re-approval.

## Related
`delivery-planning` (phases + gates) · `architecture-decisions` (feasibility) · `ux-ui-design` (flows from stories).
