# Agentic Milo — Design Proposal (for convergence)

## Goal
Make Milo "muse kind": a peer agent that other agents can call, that can call
other agents, and that holds the same integration tool belt. Not a chatbot
with tools — an agent in the fleet.

## Current state
- Milo has 19 MCP tools **cataloged** (`/v1/mcp/tools`) — chat, retrieve,
  documents_*, jobs_*, suggestions_*, actions_*, consents_*, ledger_*,
  routes_*, skills_*, persona_get.
- This is shapes-only: no running MCP server speaks the protocol.
- The switchboard thread "Muse–Milo MCP/API handshake" is still open.

## Proposed phases

### Phase 1: Milo as MCP server (Milo callable by others)
- Run a real MCP server on the box (SSE transport, alongside :7071).
- Expose the 19 cataloged tools through it, mapped to existing HTTP endpoints.
- Auth: Cloudflare Access identity (same as PWA) + a service token for
  agent-to-agent calls. Every call logged to the ledger.
- Wright (or any agent) can then call `milo.chat`, `milo.retrieve`, etc.

### Phase 2: Milo calls out (Milo → Wright)
- Milo gets an "escalate" capability: when a request is beyond its scope,
  it packages context and calls Wright via the same MCP pattern.
- Wright does the deep work, returns the result, Milo delivers it.
- Auth: Milo holds a scoped token for Wright's agent interface.
- This is the "foreman" pattern Nrupal described, generalized.

### Phase 3: Skill parity (same tool belt)
- Port Wright's relevant integrations to Milo's backend: Gmail, Calendar,
  GitHub, Cloudflare, etc. — scoped to Nrupal's needs.
- Each integration is permissioned per user (Natasha doesn't get Nrupal's Gmail).
- This is ongoing, one integration at a time, queued properly.

### Phase 4: Switchboard orchestration
- Milo, Wright, and future agents coordinate through the switchboard.
- Nrupal at the center; agents as peers, not hierarchy.
- Full audit trail; cost ledger; nothing spends without his word.

## Auth model
- Human → Milo: Cloudflare Access (already live).
- Agent → Milo: service token, scoped per calling agent, logged.
- Milo → Agent: Milo holds scoped tokens per target agent.
- All agent calls appear in the ledger with caller, target, cost.

## Open questions for Nrupal
1. Should Phase 1 (MCP server) come before or with Phase 2 (Milo calls out)?
2. Which integrations first for Phase 3? (Gmail? Calendar? GitHub?)
3. Should Natasha's Milo have any agent-calling ability, or human-only?

## Non-goals
- No autonomous spending. Ever.
- No agent can see another user's data (isolation holds).
- No replacing the PWA — this is additive.
