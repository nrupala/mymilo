---
name: agent-safety-guardrails
description: Guard the agents — injection defense, tool least-privilege, approvals, sandboxes, kill switches.
version: 1
triggers: agent guardrails, prompt injection, tool permissions, agent sandbox, kill switch, agent safety
category: How Milo works
blurb: Guard agents properly — injection defence, least-privilege tools, approvals and kill switches.
archetype: knowledge
example: What guardrails should I put around an agent that can run tools?
---

# Agent Safety & Guardrails

Agents mix untrusted input with real capabilities — the exact recipe for damage. Assume the content they read will attack them, and build accordingly.

## When to use
- Any agent with tools, network, filesystem, or the ability to spend/send/delete.
- Reviewing autonomy levels before expanding them.
- After any agent-caused incident.

## Method
1. **Treat all external content as hostile data**: web pages, emails, tool outputs, documents — data, never instructions. Strip/annotate before model use; flag suspicious imperatives.
2. **Tool least-privilege**: each agent gets only the tools its job needs; read tools before write tools; destructive tools gated (approval or explicit scope); no shell passthrough without sandbox.
3. **Approval gates (HITL)**: deploys, payments, deletions, external sends, credential changes — human confirms; the guardrail is not configurable away by the agent.
4. **Sandboxing**: run untrusted code/tooling in isolation (`non-docker-isolation`); filesystem scope minimal; egress restricted; resource caps enforced.
5. **Budgets + circuit breakers**: token/cost/time caps; loop detection (same action N times → stop + escalate); kill switch per agent.
6. **Output validation**: schema-check what agents produce before acting on it; never `eval` model output; parameterize everything downstream.
7. **Secrets never in context**: agents reference credential handles, not values; exfiltration paths (rendering, URLs, logs) considered in tests.
8. **Red-team the interface**: injection suites (instructions hidden in content), jailbreak attempts, canary tokens for leak detection; findings become regression tests.

## Quality gates
- [ ] Injection test suite exists and passes on the agent's inputs.
- [ ] Destructive actions require approval (verified, not assumed).
- [ ] Sandbox + egress + resource caps verified with an abuse test.
- [ ] Kill switch tested; budgets alert before cap.

## Red lines
- Never disable guardrails "to make it work"; no unbounded autonomy on destructive surfaces; no secrets or PII in agent context by default.

## Related
`non-docker-isolation` · `zero-trust-architecture` · `agent-evaluation` (safety tests) · `mcp-engineering` (tool rails).
