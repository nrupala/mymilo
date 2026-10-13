---
name: backend-engineering
description: Implement backend with production standards — API contracts, validation, idempotency, jobs, errors, safe migrations.
version: 1
triggers: backend, api, server, idempotency, migrations, backend engineering
category: Engineering & code
blurb: Implement backends to production standards — contracts, validation, idempotency and safe data changes.
archetype: knowledge
example: Build this API endpoint the production way, not the demo way.
---

# Backend Engineering

Build the engine: contracts, correctness, and failure behavior. Interfaces first, then implementation; every boundary validated.

## When to use
- APIs, services, workers, integrations, data pipelines.
- Changes to contracts, jobs, or persistence.

## Method
1. **Contract first**: define endpoints/queues — input, output, errors, versioning — before code; keep contracts in the repo.
2. **Validate at boundaries**: reject bad input early with specific errors; never trust clients (including your own frontend).
3. **Idempotency**: make retries safe (idempotency keys on mutating operations; no double-sends, no double-charges).
4. **Error taxonomy**: validation vs not-found vs conflict vs retryable vs fatal — structured, consistent, tested.
5. **Jobs & queues**: retries with backoff + jitter, dead-letter path, no lost work, observable status.
6. **Data**: migrations reversible or backed-up; enforce constraints in the database, not just the app; no plaintext secrets at rest (`secure-build-pattern`).
7. **Observability hooks**: structured logs (ids, timings), metrics at edges, trace ids propagated (`observability-ops`).

## Artifacts
- API/queue contracts, handlers, migration files, failure-mode tests.

## Quality gates
- [ ] Contract documented and versioned.
- [ ] Validation + error paths tested (not just the happy path).
- [ ] Retry/idempotency behavior verified.
- [ ] No secrets or PII in logs.

## Red lines
- No unreviewed migrations on live data; no direct-to-prod changes.
- No silent catch-all — failing loudly beats corrupting quietly.

## Related
`architecture-decisions` (boundaries) · `testing-strategy` (failure tests) · `dependency-governance` (supply chain).
