---
name: multi-agent-orchestration
description: Run agent fleets — routing, handoff contracts, fallbacks, budgets, shared state, audit trails.
version: 1
triggers: agent fleet, multi agent, orchestrate agents, agent routing, agent teams
category: How Milo works
blurb: Run a fleet of agents — routing, handoffs, budgets, shared state and audit trails.
archetype: knowledge
example: How do I coordinate several agents on one project without chaos?
---

# Multi-Agent Orchestration

One agent is a tool; a fleet is a system. Route work deliberately, contract every handoff, and keep the whole thing observable and bounded.

## When to use
- Running more than one agent/model on real work (orchestrator + workers).
- Connecting laptop/box/cloud lanes (Jack ⇄ Milo ⇄ box pattern).
- When handoffs get lost, duplicated, or expensive.

## Method
1. **Roles**: orchestrator (plans, routes, verifies), workers (execute narrow tasks), verifier (independent check on critical outputs). Small teams beat swarms.
2. **Routing**: task → best lane by capability, cost, latency. Define a **fallback chain** per route (primary → secondary → local) so one failing provider never kills the job.
3. **Handoff contract**: every delegation states goal, constraints, acceptance criteria, report-back point — terse, copy-pasteable, versioned.
4. **Shared state with one truth**: mailboxes/repos/databases with explicit ownership — one writer per resource; sequence numbers to dedupe; async-tolerant (works when a member is offline).
5. **Budgets + limits**: token/cost/time cap per task; max retries then escalate; kill switch per lane; alert at 80% of a budget.
6. **Idempotent tasks**: design retries safe; agents ack and re-ack without double effects.
7. **Observability**: every handoff logged (who, what, outcome); per-lane status; anomaly alerts (loops, cost spikes).
8. **Human gates**: deploys, payments, deletions, external sends → HITL; the fleet prepares, humans approve.

## Quality gates
- [ ] Every handoff uses the contract fields.
- [ ] Fallback chain configured and tested (fail the primary once, on purpose).
- [ ] Budgets set; kill switch verified.
- [ ] Audit trail can reconstruct any task end-to-end.

## Red lines
- No two agents mutating the same resource without ownership; no unbounded loops; no silent lane failures (heartbeats or it didn't happen).

## Related
`agent-interoperability` · `agent-safety-guardrails` · `observability-ops`.
