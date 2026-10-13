---
name: zero-knowledge-systems
description: Design systems that can't see user data — client-side E2EE, metadata honesty, ZKP only where justified.
version: 1
triggers: zero knowledge, e2ee, end to end encryption, private by design, zkp
category: Security & privacy
blurb: Design systems that can't see user data — client-side encryption and honest metadata claims.
archetype: knowledge
example: Design my notes app so the server can never read the notes.
---

# Zero-Knowledge Systems

"Zero-knowledge" is an architecture, not a slogan: keys live with the user, the server holds ciphertext, and claims match reality — precisely.

## When to use
- Apps where the provider must never see content (notes, ledgers, vaults, messaging).
- Designing sync, storage, or sharing for sensitive data.
- Auditing ZK claims in docs, marketing, or specs.

## Method
1. **Define the trust model**: state exactly what the server can and cannot see — content, metadata, access patterns. Metadata is data; address it explicitly.
2. **Client-side encryption**: derive keys on the client (Argon2id/OPAQUE for passwords); server stores only ciphertext + envelopes (`cryptography-engineering`).
3. **ZKP only where it pays**: proof systems (SNARK/STARK-class) are powerful and expensive — use for specific claims (e.g., "I know a secret satisfying X") and budget for circuit work; most products need E2EE, not ZKPs.
4. **Auth without exposure**: PAKE/OPAQUE-style flows so passwords never reach the server.
5. **Sharing**: per-share key wrapping; revocation designed in; re-encryption paths documented.
6. **Recovery trade-offs**: any recovery mechanism (escrow, social, phrase) weakens the model — choose consciously and document it.
7. **Limits**: encrypted search/query is a spectrum — be honest about what the server can still infer.
8. **Claims audit**: every "zero-knowledge / E2EE / ZK" statement must map to a mechanism in the threat model. No orphans.

## Quality gates
- [ ] Threat model states what the server sees (content + metadata).
- [ ] Password/key flows use PAKE-grade or client-side derivation — no plaintext credentials server-side.
- [ ] Claims ↔ mechanisms audit completed before publishing any ZK language.
- [ ] Recovery path documented with its weakening effects.

## Red lines
- No "zero-knowledge" without describing key custody exactly.
- No ZKP marketing without an actual proof system; no plaintext sensitive data in logs, ever.

## Related
`cryptography-engineering` · `secure-build-pattern` · `architecture-decisions`.
