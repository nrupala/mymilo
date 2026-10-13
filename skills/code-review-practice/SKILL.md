---
name: code-review-practice
description: Review changes properly — small PRs, a real checklist, blocking vs non-blocking feedback, green gates before approval.
version: 1
triggers: code review, review my pr, pull request, review checklist, feedback
category: Engineering & code
blurb: Review changes properly — small PRs, a real checklist, and feedback that separates blocking from polish.
archetype: knowledge
example: Review this pull request against a proper checklist.
---

# Code Review Practice — the reviewer seat

Review is a quality gate and a teaching loop. The reviewer catches what tests can't, keeps the codebase coherent, and stays kind and concrete.

## When to use
- Every change before merge. No self-merged unreviewed work (emergency hotfixes get post-review).
- When giving or receiving review feedback.

## Method
1. **Size**: keep PRs small (aim ≤ ~400 changed lines); split large changes logically so they can be reviewed.
2. **PR description**: what / why / how-to-test; link the spec or issue; screenshots for UI changes.
3. **Checklist**: correctness (logic, edge cases) · security (inputs, secrets, dependencies) · tests (coverage, determinism) · readability (names, structure) · docs (README/changelog when behavior changed).
4. **Feedback etiquette**: label comments — `must:` (blocking), `nit:` (non-blocking), `q:` (question); explain the why; propose, don't dictate.
5. **Respond / resolve**: authors answer every comment; resolve only when addressed; never re-litigate resolved nits.
6. **Approval gates**: green CI + resolved comments + reviewer sign-off. Approve only what you'd ship.

## Artifacts
- Review comments with labels, approvals, a repo review checklist where the team wants one.

## Quality gates
- [ ] CI green before approval — red means no merge.
- [ ] At least one reviewer for non-trivial changes.
- [ ] Behavior-changing PRs update docs + changelog.

## Red lines
- No force-push over someone else's review without telling them.
- No rubber-stamping; no unexplained blocking.

## Related
`testing-strategy` (what CI runs) · `ci-cd-pipeline` (merge gates) · `technical-writing` (docs in the PR).
