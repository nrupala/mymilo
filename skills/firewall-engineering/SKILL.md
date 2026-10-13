---
name: firewall-engineering
description: Design firewalls that hold — default deny, least-privilege rules, explicit egress, tested and reviewed.
version: 1
triggers: firewall, firewall rules, egress, default deny, network rules
category: Security & privacy
blurb: Design firewalls that hold — default deny, least-privilege rules and tested egress.
archetype: knowledge
example: Write firewall rules for a small server that only needs web and SSH.
---

# Firewall Engineering

A firewall is policy made executable: default-deny, every allowance justified, every change tested and reversible.

## When to use
- Setting up or reviewing host firewalls, cloud security groups, or edge rules.
- Debugging "it can't connect" (is it policy or the app?).
- Auditing rules that have grown without review.

## Method
1. **Default deny, both directions**: inbound and outbound start closed; open only what services need, in the direction they need.
2. **Per-service least privilege**: scope by source, destination, port, protocol — prefer service-scoped rules over host-wide; no `any-any` in production, ever.
3. **Explicit egress**: outbound allowlists (DNS, NTP, package mirrors, APIs the service actually calls); alert on denies to spot misconfig and compromise.
4. **Platform layers**: know your stack — nftables/ufw (Linux), Windows Defender Firewall (laptop/box), cloud security groups + NACLs; keep layers consistent (no conflicting opens).
5. **No NAT/port-forward by default**: tunnels (authenticated) or overlays instead of publishing ports; port-forwards are inventory items with reviews.
6. **Change management**: every rule has a comment with why + owner + date; changes reviewed like code; old rules retired on a schedule.
7. **Test, don't assume**: after changes verify the allowed path works and a blocked path fails; keep a smoke matrix per service.
8. **Log + review**: denials logged with rate-limits to avoid noise floods; review top denied flows monthly.

## Quality gates
- [ ] Default-deny baseline in all zones; zero any-any rules in prod.
- [ ] Every allow entry has reason + owner comment.
- [ ] Post-change test: allowed path passes, disallowed fails.
- [ ] Rule review performed on schedule; stale rules removed.

## Red lines
- No "open it while we debug" left behind — temporary means a ticket with a date.
- No direct exposure of databases, admin panels, or agent control planes.

## Related
`network-security` · `non-docker-isolation` · `zero-trust-architecture`.
