---
name: agent-interoperability
description: Work with all sorts of agents — MCP/ACP/A2A landscape, bridge patterns, handoff contracts, agent auth.
version: 1
triggers: mcp, acp, a2a, agent bridges, talk to other agents, handoff contract, agent protocols
category: How Milo works
blurb: Work across agents and protocols — MCP, ACP and A2A — with clean handoff contracts.
archetype: knowledge
example: How should my agents hand work to each other without losing context?
---

# Agent Interoperability

Agents come in species: editors, cloud assistants, local runtimes, box servers, third-party services. Speak standard protocols, bridge them deliberately, and give every handoff a contract.

## When to use
- Connecting your agent(s) to another system: editor, cloud assistant, agent fleet, SaaS.
- Choosing a protocol for a new integration.
- Debugging "the agents can't talk to each other".

## Method
1. **Pick by counterparty, not fashion**:
   - Tools/resources for models → **MCP**
   - Editor ↔ agent sessions → **Agent Client Protocol (ACP, stdio)**
   - Agent ↔ agent runs / services → **Agent Communication Protocol (ACP, REST)** or **A2A** (cross-org collaboration, agent cards/tasks)
   - Humans, scripts, anything → **REST/CLI/web** (the universal fallback)
2. **Bridge, don't fork**: one core, many protocol adapters (`multi-surface-webapp` pattern). Never implement business logic per protocol.
3. **Gateway pattern** for remote/untrusted agents: a single authenticated broker (mTLS/tokens), audited, rate-limited — not N direct doors.
4. **Handoff contracts**: every cross-agent message states goal, constraints, acceptance criteria, report-back location — terse and copy-pasteable (Milo⇄Jack style).
5. **Identity between agents**: each agent has its own credential; least privilege; short-lived; revocable; no shared "service-to-service forever" keys.
6. **Versioning + discovery**: publish capabilities (tools list, agent card, version); negotiate; degrade gracefully when the counterparty is older/newer.
7. **Audit everything**: message log with provenance (who asked, what ran, what changed); history is the dispute resolver.
8. **Test the handshake**: scripted counterparty tests per protocol (smoke suites), not just "it worked once in the demo".

## Quality gates
- [ ] Protocol choice documented per integration + why.
- [ ] Handshake test exists and passes (both directions).
- [ ] Agent credentials scoped + revocable; broker in front of remote paths.
- [ ] Handoff contracts used for non-trivial coordination.

## Red lines
- No unsandboxed third-party agents hitting your systems (`agent-safety-guardrails`).
- No secrets or private data in agent-to-agent messages by default.

## Related
`mcp-engineering` · `acp-engineering` · `multi-agent-orchestration` · `zero-trust-architecture`.
