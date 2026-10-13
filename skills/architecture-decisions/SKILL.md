---
name: architecture-decisions
description: Make and record architecture decisions (ADRs) with interface contracts and honest trade-offs before code.
version: 1
triggers: architecture, adr, architecture decision, system design, interface contract, trade-offs
category: Engineering & code
blurb: Make and record architecture decisions with interface contracts and honest trade-offs, before code.
archetype: knowledge
example: Write an ADR for choosing our database.
---

# Architecture Decisions — the architect seat

Design before build: boundaries, interfaces, and the reasoning trail. Decisions live in ADRs — written once, **superseded** (never silently rewritten).

## When to use
- New system/service/module, or any change touching boundaries or contracts.
- Choosing tech, storage, protocols, or deployment shape.
- Any decision that is expensive to reverse.

## Method
1. **NFRs first**: performance, scale, availability, security, cost — quantified where possible.
2. **Boundaries**: draw contexts/modules; keep the core small; put clear interfaces at the seams.
3. **Contracts before code**: define API/module contracts (inputs, outputs, errors); version them.
4. **Options**: list 2–3 real alternatives with trade-offs; prefer boring, replaceable tech; no new dependency without a reason (see `dependency-governance`).
5. **ADR format**: Context → Decision → Consequences (positive/negative/risks) → Status. One page max.
6. **Reversibility**: prefer choices that are cheap to undo; isolate the expensive ones behind interfaces.
7. **Security by design**: map data flows; encrypt/verify per the `secure-build-pattern`.

## Artifacts
- `docs/adr/NNNN-title.md` (numbered), contract specs, context diagram (text or diagram-as-code).

## Quality gates
- [ ] NFRs written and agreed before design freeze.
- [ ] Interfaces documented and versioned.
- [ ] At least one serious alternative considered per major decision.
- [ ] Superseded ADRs link to their replacements.

## Red lines
- No "we'll figure it out later" for irreversible decisions.
- No hidden coupling across boundaries; no backdoor paths around the contracts.

## Related
`delivery-planning` (phasing) · `backend-engineering` (contracts in practice) · `secure-build-pattern` (security floor).
