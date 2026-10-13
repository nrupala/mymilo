---
name: correctness-verification
description: Verify and certify software correctness - specs, model checking, deductive proofs, certificates, honest scope.
version: 1
triggers: verify correctness, formal verification, prove code correct, model checking, certificates
category: Engineering & code
blurb: Verify and certify software correctness — specs, model checking, proofs and honest scope.
archetype: knowledge
example: How would I verify this component actually meets its spec?
---

# Correctness Verification

"Certified" must mean something. Correctness is a claim about a *property*, *scope*, and *evidence level* — never a vibe. This skill covers the ladder from tests to proofs and the certification artifacts that make claims checkable.

## When to use
- Making — or challenging — a "verified / certified correct" product claim.
- Choosing verification depth for a component (analysis vs model checking vs proof).
- Producing attestations, certificates, or audit packs for correctness.

## Method
1. **Claims register first**: one row per claim — property (what exactly), scope (which version/config), evidence level, expiry. No register, no claim.
2. **Evidence ladder** (cheapest that suffices):
   - L1 static analysis + strict typing + linting
   - L2 property-based testing & fuzzing
   - L3 model checking (TLA+, Alloy, SPIN) for protocols/concurrency
   - L4 deductive verification (Dafny, Frama-C, CBMC) for functional correctness
   - L5 proof assistants (Lean/Coq) for core math & critical kernels
3. **Specs before tools**: write invariants, pre/post-conditions, and liveness properties in the checker's language *before* running anything.
4. **Evidence artifacts**: counterexamples, proof scripts, solver logs, CI records — plus signed attestations binding claim → artifact → source commit (hash + signature, mirroring the provenance kit).
5. **Scope honesty**: list what is *outside* scope (dependencies, hardware, misconfiguration, side channels). Version every claim; re-verify on change — stale certificates are void.
6. **CI integration**: verification runs in the pipeline; a broken proof fails the build like a broken test.
7. **Adversarial review**: an independent pass tries to falsify the claim; only unfalsified claims are certified.

## Quality gates
- [ ] Claims register exists; each claim has a machine-checkable artifact behind it.
- [ ] Scope and exclusions written; re-verification triggers defined.
- [ ] Certificates are signed, versioned, and independently reproducible.
- [ ] No claim exceeds its evidence level (tests ≠ proof).

## Red lines
- Never say "proven", "bug-free", or "certified" without property + scope + evidence.
- Never suppress a counterexample; never certify an artifact you have not verified at its current version.
- No certificate without a reproduction recipe.

## Related
`lean4-proving` · `test-design` · `testing-strategy` · `secure-build-pattern` · `code-review-practice`.
