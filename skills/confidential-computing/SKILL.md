---
name: confidential-computing
description: Use enclaves and TEEs properly — threat models, attestation, sealed data, honest claims, hybrid designs.
version: 1
triggers: confidential computing, enclaves, tee, attestation, sealed data
category: Security & privacy
blurb: Use enclaves and trusted execution honestly — threat models, attestation and sealed data.
archetype: knowledge
example: Should I use confidential computing for this workload?
---

# Confidential Computing

Hardware-enforced isolation (TEEs/enclaves) protects data *in use* — the last gap after at-rest and in-transit encryption. Use it with a threat model, or it's expensive theater.

## When to use
- Sensitive compute that even the host operator shouldn't see (enclave-based security pipelines).
- Evaluating "runs in a secure enclave" claims (vendors, components).
- Designing sealed-key workflows and attestation flows.

## Method
1. **Threat model first**: write what the TEE protects against (host access, operator poking, co-tenants) and what it does NOT (side channels, supply chain, flawed enclave code, unsealed inputs/outputs). No model → no claim.
2. **Know the technologies**: VM-level (Intel TDX, AMD SEV-SNP) vs process-level (SGX) vs ARM CCA/TZ distinctions; choose by workload shape and available hardware.
3. **Attestation is the point**: verify quotes (measurement + nonce, fresh!) before trusting an enclave; a TEE without verified attestation is a vibe, not a guarantee.
4. **Enclave patterns**: sealed storage (keys bound to enclave identity/measurement), secure channels (attested TLS), minimal enclave surface area (small trusted codebase), debug disabled everywhere in prod.
5. **Engineering discipline**: reproducible builds + signed enclave images; version and pin measurements; simulator in dev, real attestation in CI/staging where possible; documented fallback if hardware is absent (explicit downgrade, never silent).
6. **Key management**: root keys never stored unsealed beside the enclave; rotation and recovery designed (don't brick user data if enclave dies); document measurement changes that invalidate seals.
7. **Claims discipline**: marketing ↔ mechanism audit; list exclusions publicly ("what the enclave doesn't cover"); pair with `regulatory-compliance` where required.

## Quality gates
- [ ] Threat model documented (protects / doesn't protect).
- [ ] Attestation verification implemented + tested (fresh nonce).
- [ ] Sealed keys tested incl. recovery path; debug disabled in prod.
- [ ] Claims match evidence; exclusions listed.

## Red lines
- No production debug mode; no unverifiable "secure enclave" claims; root keys never kept unsealed.

## Related
`post-quantum-cryptography` · `cryptography-engineering` · `non-docker-isolation`.
