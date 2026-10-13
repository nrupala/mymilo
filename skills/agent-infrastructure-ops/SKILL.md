---
name: agent-infrastructure-ops
description: Keep agent stacks running — processes, autostart, tunnels, health checks, upgrades, secrets, HITL deploys.
version: 1
triggers: agent stack down, autostart, tunnels, agent health check, keep agents running, agent ops
category: How Milo works
blurb: Keep agent stacks running — what runs where, health checks, autostart and safe upgrades.
archetype: knowledge
example: Why is my agent stack down, and how do I keep it from happening again?
---

# Agent Infrastructure Ops

Agents are only as good as the stack under them. Know what runs where, keep it healthy from the outside, and make every change reversible.

## When to use
- Running agent stacks on laptop/box/server (gateways, MCP bridges, tunnels, workers).
- Setting up autostart, monitoring, or upgrades for agent infrastructure.
- When "why is Jack down?" happens.

## Method
1. **Inventory**: one table — what runs where, ports, owners, health endpoints, restart policy. If it isn't inventoried, it isn't operated.
2. **Process management**: systemd units (Linux) or services + scheduled tasks (Windows); hardening per `non-docker-isolation`; auto-restart with sane limits; logs to files with rotation.
3. **Autostart chains**: idempotent start scripts (tolerate already-running), ordered (wait for gateway health before dependents), fully logged; verify the chain after any change (fire it manually).
4. **Network posture**: loopback binds by default; remote access only via authenticated tunnels (cloudflared-class); no open admin ports (`firewall-engineering`); Access policies for humans, service tokens for machines.
5. **Health & observability**: health endpoints + heartbeats; external monitors (site-monitor pattern) for "is it up from outside?"; actionable alerts with owners (`observability-ops`).
6. **Upgrades**: pinned versions; runway = backup → update → verify → rollback path; never upgrade during an incident; changelog per stack change.
7. **Secrets**: token files with tight ACLs; rotation calendar; never in repos/logs/chats (`secrets-management`); separate credentials per service.
8. **HITL**: deploys and config changes get human approval — automation prepares, humans approve; scheduled tasks documented and reviewable.

## Quality gates
- [ ] Stack inventory current; health checked from outside.
- [ ] Autostart chain tested end-to-end after changes.
- [ ] Restore/rollback drill executed at least once.
- [ ] Secrets rotation scheduled; no loopback leaks to the network.

## Red lines
- No unauthenticated remote surfaces; no silent config drift (all changes recorded); never disable monitoring to hide a problem.

## Related
`observability-ops` · `non-docker-isolation` · `secrets-management` · `local-llm-serving`.
