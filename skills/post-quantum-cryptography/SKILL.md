---
name: post-quantum-cryptography
description: Prepare for quantum risk — ML-KEM/ML-DSA hybrids, crypto inventory, migration mapping, honest timelines.
version: 1
triggers: post quantum, ml-kem, ml-dsa, quantum risk, crypto migration
category: Security & privacy
blurb: Prepare for quantum risk — modern hybrid algorithms, a crypto inventory and a migration map.
archetype: knowledge
example: What should I do now about post-quantum cryptography?
---

# Post-Quantum Cryptography

Quantum computers will break today's asymmetric crypto — "harvest now, decrypt later" makes long-lived secrets urgent. Migrate with hybrids and agility, not heroics.

## When to use
- New security designs (signatures, key exchange, trust roots) on long horizons.
- Long-lived data whose confidentiality must outlast ~2030s.
- Compliance timelines (NIST migration guidance) reaching the stack.

## Method
1. **Inventory asymmetrics**: TLS, code/firmware signing, agent trust roots, at-rest envelopes, PKI — where RSA/ECC lives and how long each must survive. Data shelf-life × migration horizon = priority order.
2. **Standard family**: track NIST PQC — ML-KEM (FIPS 203), ML-DSA (204), SLH-DSA (205); use **hybrid mode** during transition (classical + PQC together) so a break in either doesn't break you.
3. **Agility first**: abstract algorithms behind interfaces (crypto-agile layers); no hardcoded key sizes in protocol code; test PQ paths in staging before they're mandatory.
4. **Engineering realities**: PQ keys/signatures are larger — handshake size, storage (certificates!), and performance budgets change; embedded constraints matter; document measurements.
5. **Where it hits first**: long-lived archives (data at rest for decades), firmware/signing roots (need to remain valid), inter-agent trust (agent ecosystems live long).
6. **Don't**: invent schemes, mix security levels carelessly, or "upgrade" symmetric crypto (AES-256 is fine — it's the asymmetric side that breaks).
7. **Track & decide**: ecosystem timelines (browsers, OpenSSL, HSMs), record choices as ADRs (`architecture-decisions`), assign owners per surface.

## Quality gates
- [ ] Crypto inventory exists with shelf-life priorities.
- [ ] Agility layer in place (algorithms swappable without app rewrite).
- [ ] Hybrid PQ path passing test vectors in staging.
- [ ] Migration plan with owners + dates.

## Red lines
- No home-rolled PQC — vetted libraries only; no silent downgrades; never claim "quantum-resistant" without verified hybrid/PQ algorithms.

## Related
`cryptography-engineering` · `confidential-computing` · `architecture-decisions`.
