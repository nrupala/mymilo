---
name: cryptography-engineering
description: Apply cryptography correctly — vetted primitives only, AEAD, disciplined key management, no home-made schemes.
version: 1
triggers: cryptography, encryption, aead, key management, crypto
category: Security & privacy
blurb: Apply cryptography correctly — proven primitives, real encryption, disciplined keys, no home-made schemes.
archetype: knowledge
example: Check that I'm using encryption correctly in this design.
---

# Cryptography Engineering

Cryptography is load-bearing: use vetted primitives exactly as specified, manage keys like money, and never improvise a scheme.

## When to use
- Adding encryption, signing, hashing, or authentication to anything.
- Reviewing code that touches keys, nonces, or protocols.
- Designing key storage, rotation, or recovery.

## Method
1. **Never invent primitives or compose your own scheme** — use libsodium / WebCrypto / Node `crypto` / RustCrypto / platform keystores.
2. **Right primitive for the job**: AEAD for confidentiality (AES-256-GCM or XChaCha20-Poly1305); signatures (Ed25519/ECDSA-P256); key agreement (X25519); hashes (SHA-256/3, BLAKE3); passwords via Argon2id/scrypt (never raw SHA); derive keys with HKDF.
3. **Nonce discipline**: AEAD nonces never reused — random 96-bit or a strict counter; document the choice.
4. **Key management**: generate in-app or in keystore/HSM; purpose-separated keys; rotation plan; encrypted at rest; backups tested; never in code, logs, or repos.
5. **Envelope encryption** for data at rest: per-item data keys wrapped by a master key.
6. **Transport**: TLS everywhere (`secure-build-pattern`); verify certificates; no plaintext fallbacks.
7. **Protocol hygiene**: forward secrecy (no static shared secrets), replay protection, constant-time comparisons (`timingSafeEqual`).
8. **Test with vectors**: known-answer tests from RFCs; tamper tests (auth tags must fail closed).

## Quality gates
- [ ] Only vetted libraries and standard parameters.
- [ ] Nonce/key lifecycle documented and tested.
- [ ] Auth failures fail closed; negatives tested.
- [ ] No key material in code, config, or logs.

## Red lines
- No ECB, no MD5/SHA-1 for security, no custom crypto, no nonce reuse, no "encryption" without authentication.

## Related
`zero-knowledge-systems` · `secure-build-pattern` (provenance/signing) · `backend-engineering`.
