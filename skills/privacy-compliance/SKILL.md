---
name: privacy-compliance
description: Engineer privacy compliance — data maps, consent, DSARs, retention, breach readiness (GDPR/PIPEDA).
version: 1
triggers: privacy, gdpr, pipeda, consent, data retention, dsar, privacy compliance
category: Security & privacy
blurb: Engineer privacy compliance — data maps, consent, access requests, retention and breach readiness.
archetype: knowledge
example: Make my app's data handling GDPR and PIPEDA ready.
---

# Privacy Compliance (GDPR · PIPEDA)

Privacy is an engineering problem with legal stakes: know your data, minimize it, honor rights, and have a breach plan. Structure and evidence — counsel reviews and signs.

## When to use
- Launching or changing anything that touches personal data.
- Responding to access/deletion requests; preparing for audits.
- Reviewing vendors, logs, analytics, or AI inputs for privacy exposure.

## Method
1. **Data map first**: per data element — what PII, where stored, why (purpose), who sees it, retention, cross-border flows. No map, no compliance.
2. **Minimize & purpose-bind**: collect only what the purpose needs; no "just in case" fields; deletion when the purpose ends (retention schedule enforced, not aspirational).
3. **Consent & lawful basis**: consent UI where consent is the basis (granular, revocable, logged); other bases documented; cookie/tracking consent per regime.
4. **Rights handling**: access/export/correct/delete runbooks (GDPR DSAR; PIPEDA access requests) — identity verification, tracked clocks, response templates; deletion propagates to backups per policy.
5. **Privacy by design**: default private; pseudonymize analytics; encrypt personal data at rest/in transit (`cryptography-engineering`); logs scrubbed of PII by rule, not by luck.
6. **Vendors & transfers**: processors under contract with defined scope; cross-border transfer mechanism identified before data crosses borders.
7. **Breach readiness**: detection hooks, severity ladder, notification timelines + regulator/user paths per jurisdiction, comms templates (`community-support`), post-incident fixes.
8. **Assessments**: DPIA/PIA for high-risk changes; record outcomes; re-assess on scope change.

## Quality gates
- [ ] Data map current; retention schedule defined and enforced.
- [ ] DSAR/access runbook exercised (one dry run).
- [ ] No PII in logs, analytics, or test data (scan-verified).
- [ ] Breach playbook with timelines + owners.

## Red lines
- Never PII in logs/exports without necessity + safeguards; no dark-pattern consent; no collection beyond purpose. Not legal advice — counsel owns final calls.

## Related
`product-analytics` · `secrets-management` · `data-ml-pipelines`.
