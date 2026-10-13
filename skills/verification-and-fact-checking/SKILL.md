---
name: verification-and-fact-checking
description: Verify claims before publishing - source triangulation, provenance checks, uncertainty labels, corrections.
version: 1
triggers: fact check, verify, check this claim, is this true, provenance, source check
category: Thinking & decisions
blurb: Verify claims before publishing — source triangulation, provenance checks and uncertainty labels.
archetype: knowledge
example: Fact-check these claims before I publish them.
---

# Verification & Fact-Checking

The standard: nothing checkable ships unverified; everything verified ships labeled. Verification is a pipeline, not a vibe — claim in, evidence out, with an audit trail.

## When to use
- Before publishing any content with numbers, quotes, claims, or images.
- Reviewing docs, proposals, or marketing copy for accuracy.
- Building verification features (badges, evidence panels) into a product.

## Method
1. **Claim extraction**: isolate every checkable unit — statistics, quotes, causal statements, images, "studies show". One row per claim in a checklist.
2. **Source ladder**: primary sources > established secondary > aggregators. Record for each: who, when, method, sample, conflicts of interest; check independence (two "sources" citing each other is one source).
3. **Triangulation**: material claims need ≥ 2 independent sources, or one primary + confirmation. Label: **verified / likely / contested / unverified**.
4. **Compute re-checks**: re-derive math, sanity-check units and orders of magnitude, verify dates and names spellings; reverse-image search and metadata for photos.
5. **Uncertainty language**: write outcomes in the weakest language the evidence supports; never upgrade "consistent with" to "proves".
6. **Publish with evidence**: inline citations, archived links (see link-integrity), visible methodology for big claims.
7. **Corrections**: fast, dated, visible change log; never silent edits. Track error patterns to fix upstream.

## Quality gates
- [ ] Every material claim has a label + at least one archived source.
- [ ] Math and units re-derived independently.
- [ ] Counter-case considered; "what would change our mind" noted for contested claims.
- [ ] Corrections policy published; versions retained.

## Red lines
- Never publish checkable claims without sources; no fake or hallucinated citations — ever.
- No "true/verified" without scope ("per X, as of date"); contested claims never stated flatly.
- Corrections are never silent; review copies never leak.

## Related
`research-tooling` · `critical-thinking` · `analytical-reasoning` · `semantic-analysis` · `link-integrity-and-archiving`.
