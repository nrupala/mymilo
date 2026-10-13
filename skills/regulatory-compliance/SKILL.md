---
name: regulatory-compliance
description: Build compliance tooling and evidence — control mappings, audit trails, assessments, regulator-ready packs.
version: 1
triggers: regulatory compliance, compliance tooling, control mapping, audit evidence, regulator
category: Money & markets
blurb: Build compliance tooling and evidence — control mappings, audit trails and regulator-ready packs.
archetype: knowledge
example: Prepare an evidence pack for a compliance audit.
---

# Regulatory Compliance (engineering side)

Compliance is a data problem with legal stakes: know the requirements, generate the evidence by design, and keep claims precisely as strong as the paperwork behind them.

## When to use
- Building compliance-driven systems (NERC/AESO-class, NIST/CISA claims, safety-critical SDLC).
- Preparing for audits; responding to findings.
- Any "compliant"/"certified" statement going into docs or marketing.

## Method
1. **Map the regime**: which rules apply (jurisdiction × industry) with exact citations; maintain a living **requirements register** — the compliance source of truth.
2. **Evidence by design**: make the system emit its own evidence as it operates — logs, approvals, test records, change history; hash-chain or sign audit records where tampering is the threat (`secure-build-pattern`).
3. **Control mappings**: requirement ↔ control ↔ evidence table; named owner per control; gaps tracked openly with remediation dates.
4. **Assessments**: readiness review before external audits; internal mock audits; findings triaged and closed with records.
5. **Change control for regulated scope**: changes touching regulated functions follow documented change management (`engineering-work-packages`); re-assessment triggers defined.
6. **Claims discipline**: "compliant / certified" only with the attestation on file (`legal-licensing`); public pages audited against reality.
7. **Retention**: hold evidence for mandated periods; audit logs immutable; disposal policies documented.

## Quality gates
- [ ] Requirements register current with citations.
- [ ] Control ↔ evidence mapping complete; owners assigned.
- [ ] Mock audit run before the real one.
- [ ] Every public compliance claim has its certificate/attestation.

## Red lines
- Never fabricate evidence (illegal and career-ending); no claims without attestation; compliance documents stay inside authorized scope (privacy).

## Related
`privacy-compliance` · `engineering-work-packages` · `legal-licensing`.
