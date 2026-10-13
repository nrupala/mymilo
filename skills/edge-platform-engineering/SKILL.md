---
name: edge-platform-engineering
description: Build on the edge — Cloudflare Workers/KV/D1/R2, tunnels and Access, versioned deploys, quota alarms.
version: 1
triggers: cloudflare, workers, edge, kv, d1, r2, cloudflare access, tunnels
category: Engineering & code
blurb: Build on the edge — Workers, KV, D1 and R2, tunnels and Access, versioned deploys and quota alarms.
archetype: knowledge
example: Design a Cloudflare Workers app with the right storage choices.
---

# Edge Platform Engineering

Edge platforms (Cloudflare-class) let small teams run serious infrastructure — if you respect their consistency models, limits, and deploy discipline.

## When to use
- Workers sites/APIs, KV/D1/R2 storage, Cloudflare Access + Tunnel setups.
- Edge-first apps (ops workers, shorteners, static deploys with dynamic bits).

## Method
1. **Platform fit**: Workers for request logic; static assets via Workers/Pages; **KV** for config/cache (eventually consistent!), **D1** for SQL, **R2** for objects — pick per consistency + access pattern, not habit.
2. **Local dev + deploys**: wrangler workflows; test with real bindings locally; deploy from git; versioned deploys with rollback (keep previous versions deployable).
3. **Security**: secrets via platform secret store (never in code or repos); Access in front of anything administrative; rate limits/WAF at the edge; validate all input at the boundary.
4. **Reliability**: CPU-time budgets (ms limits!), cold-start awareness; error capture + alerts (`observability-ops`); staged rules; health checks from outside.
5. **Tunnels**: cloudflared for private origins — origin stays loopback; Access policies for humans, service tokens for machines; no origin exposure "just in case".
6. **Cost & quotas**: know free-tier numbers (requests, KV ops, D1 rows, bandwidth); alarms before quotas; log-driven cost review monthly.
7. **DNS/TLS hygiene**: zones documented; certs automatic but monitored; email routing/records consistent with `network-security`.

## Quality gates
- [ ] Storage choices documented (consistency + access reasons).
- [ ] Deploys versioned with a tested rollback path; staging separated from prod.
- [ ] Secrets only in platform store; admin behind Access.
- [ ] Quota alarms set; CPU budget respected.

## Red lines
- No admin surfaces without Access; no secrets in repo or logs; never disable TLS/HTTPS because "it's just a worker".

## Related
`network-security` · `agent-infrastructure-ops` · `ci-cd-pipeline`.
