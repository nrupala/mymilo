---
name: dependency-governance
description: Govern third-party dependencies — minimalism, pinning, audits, license checks, SBOM, and verified sources.
version: 1
triggers: dependencies, supply chain, sbom, pin dependencies, audit packages, license check
category: Security & privacy
blurb: Govern third-party dependencies — minimal, pinned, audited and licensed, with an SBOM.
archetype: knowledge
example: Audit my dependency list for risk and license problems.
---

# Dependency Governance — the supply-chain seat

Every dependency is a liability with a feature. Add few, pin them, verify them, keep them healthy.

## When to use
- Adding any new library, tool, CI action, or container image.
- Routine hygiene: audits, updates, license reviews.
- Investigating supply-chain risk (CVEs, typosquatting, abandoned packages).

## Method
1. **Justify**: what does it do that the platform or existing code can't? Prefer the standard library; prefer boring, maintained, small.
2. **Verify sources**: official registries/repos; check publisher, release signing where available; checksums for binaries (`secure-build-pattern`).
3. **Pin**: exact versions + lockfiles committed; CI installs from the lock; pin CI actions/images to commit hashes.
4. **Audit cadence**: automated audit in the normal workflow; review bot bumps — do not blind-merge them.
5. **Licenses**: permissive (MIT/Apache/BSD) by default; copyleft or commercial goes to an explicit human decision; update NOTICE when required.
6. **SBOM**: generate per release where feasible; keep with release artifacts.
7. **Update policy**: batch updates, run the suite, retire unused deps; flag anything with no release in ~2 years.

## Artifacts
- Lockfiles, audit reports, license list / NOTICE, SBOM entries, dependency decisions in the log.

## Quality gates
- [ ] New dependency justified in the PR (what/why/alternatives).
- [ ] Lockfile updated in the same change.
- [ ] License checked; NOTICE updated when required.
- [ ] No unpinned CI actions or images.

## Red lines
- No dependencies from unknown sources; no unpinned "latest".
- No auto-merge of dependency bumps without a green suite.

## Related
`secure-build-pattern` (verified artifacts) · `ci-cd-pipeline` (where pins run) · `code-review-practice` (review gate).
