---
name: zero-trust-architecture
description: Verify every hop — identity-first access, least privilege, short-lived credentials, no implicit network trust.
version: 1
triggers: zero trust, verify every request, least privilege access, short-lived credentials
category: Security & privacy
blurb: Verify every hop — identity-first access, least privilege and short-lived credentials.
archetype: knowledge
example: Apply zero-trust thinking to my small team's tools.
---

# Zero-Trust Architecture

The network is hostile; location proves nothing. Every request is authenticated, authorized, and logged — humans and workloads alike.

## When to use
- Designing service-to-service, admin, or CI/CD access.
- Hardening an architecture that trusts "internal" networks.
- Reviewing identity, secrets, and audit design.

## Method
1. **Identity-first**: strong identities for users and workloads; short-lived credentials (tokens, certs) — no shared or static long-lived secrets.
2. **Authenticate + authorize every hop**: mTLS or signed requests east-west; a policy layer (e.g., OPA/Rego) decides, not network position.
3. **Least privilege**: scoped tokens, just-in-time elevation, deny by default; permissions reviewed and revoked routinely.
4. **Segment**: blast-radius boundaries between services/envs; no flat trusted LAN; egress restricted and monitored.
5. **Attest**: device/server posture checks where feasible (attestation, inventory) before trusting a node.
6. **Encrypt** in transit and at rest (`cryptography-engineering`); end-to-end where the model demands it (`zero-knowledge-systems`).
7. **Audit everything**: privileged actions logged immutably; alerts on anomalies; audit trails survive the component they describe.
8. **Break-glass**: a documented, ceremony-gated emergency path — because zero-trust without a brake fails at the worst time.

## Quality gates
- [ ] Every service call authenticated + authorized (no anonymous east-west).
- [ ] Secrets short-lived, scoped, and rotated; none long-lived wide-scope.
- [ ] Egress + privilege changes audited.
- [ ] Break-glass path documented and tested once.

## Red lines
- No "it's on the internal network, so it's fine".
- No shared credentials across services or people; no unrevocable access.

## Related
`cryptography-engineering` · `observability-ops` · `ci-cd-pipeline` (tokens in automation).
