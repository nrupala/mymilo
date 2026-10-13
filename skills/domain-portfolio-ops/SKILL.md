---
name: domain-portfolio-ops
description: Operate a domain portfolio - DNS hygiene, redirects, email auth, TLS, renewals, brand architecture.
version: 1
triggers: domains, dns, domain renewal, redirects, domain portfolio, email authentication
category: Money & markets
blurb: Operate a portfolio of domains — DNS hygiene, redirects, email authentication and renewals.
archetype: knowledge
example: Audit my domains so none of them ever lapse or break.
---

# Domain Portfolio Operations

Twenty-plus domains is an estate: every one needs DNS hygiene, a defined purpose, email authentication, TLS, and a renewal guard. A lapsed personal-brand domain is a one-day catastrophe — this skill prevents it.

## When to use
- Auditing or operating a portfolio of domains (active, redirecting, parked, coming-soon).
- Adding a new domain: register → purpose → DNS → redirect/email → monitoring.
- Brand architecture work: which domain is canonical for what.

## Method
1. **Inventory (single source of truth)**: one table — domain, registrar, renewal date, DNS host, purpose/status (active / redirect / parked / coming-soon), target, owner notes. No secrets in it, ever. Version it in the repo.
2. **Brand architecture**: one canonical domain per brand cluster; spokes 301-redirect to the hub (e.g. variant personal domains → primary); keep the redirect map as code, review in diffs.
3. **DNS as code**: export zones to files under version control; TTL policy (low before changes, raise after stable); no wildcards without written justification; change protocol: preview → apply → verify → rollback plan.
4. **Email authentication**: SPF + DKIM + DMARC on every sending domain; DMARC monitoring first (p=none with rua reporting), then quarantine; block spoofing on parked/brand domains; test after every DNS change.
5. **TLS & hosting**: auto-renewing certs, HSTS once stable, dual verification after any change; monitor expiry, uptime, and redirect chains; no infinite loops.
6. **Renewals**: alerts at 60/30/7 days; auto-renew wherever possible; payment method expiry tracked; registrar lock on personal-brand names.
7. **Quarterly audit**: dead redirects, stale pages, dangling DNS records, parked domains that deserve action, expiring certs, DMARC reports review.

## Quality gates
- [ ] Inventory current; every domain has a purpose and an owner.
- [ ] Redirect map tested (status, destination, no loops).
- [ ] DMARC on all sending/receiving domains; recordings clean or explained.
- [ ] Renewal + expiry monitors live; registrar locks on brand names.
- [ ] Quarterly audit executed and logged.

## Red lines
- A personal-brand domain must never lapse — locks + auto-renew + alerts, all three.
- No redirect loops or chains beyond two hops; no wildcard DNS + wildcard cert combo without review.
- No credentials or registrar secrets in the inventory; no silent DNS changes.

## Related
`network-security` · `privacy-compliance` · `seo` · `personal-web-presence` · `edge-platform-engineering`.
