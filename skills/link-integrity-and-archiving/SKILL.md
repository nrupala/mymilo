---
name: link-integrity-and-archiving
description: Keep links stable and provable - link-rot scans, WARC archiving, canonicalization, notarized captures.
version: 1
triggers: link rot, broken links, warc, archiving, citations, link checking
category: Engineering & code
blurb: Keep links stable and provable — rot scans, archiving at cite time, canonicalization, notarized captures.
archetype: knowledge
example: Set up link checking and archiving for my site's citations.
---

# Link Integrity & Archiving

A link is a promise; the web breaks promises constantly. This skill keeps citations stable and provable: detect rot, archive what was seen, canonicalize, and notarize captures so a third party can verify them.

## When to use
- Publishing citations, references, or source claims (any content that outlives the page).
- Building bookmark/reader products: dedupe, metadata, archive-on-save.
- Standing up link health checks for a site or knowledge base.

## Method
1. **Detect**: scheduled scans (HEAD/GET with status + content hash) for internal and external links; flag: dead, moved, soft-404, paywalled, hijacked (domain changed owner).
2. **Archive at cite time**: capture to WARC/SingleFile when saved — not later; store capture hash + timestamp alongside the URL. Fallback chain: original → archive.org → other public archives.
3. **Canonicalize & dedupe**: normalize URLs (strip trackers, resolve redirects), dedupe by content hash, assign stable internal IDs so links survive URL changes.
4. **Notarize**: hash the artifact (SHA-256), timestamp it (RFC 3161 TSA or transparency log), bundle evidence = URL + capture + hashes + time + tool versions; publish a verification recipe (anyone can re-hash and check).
5. **Serve honestly**: reader/playback of captures, "as-seen" views, live-vs-archive diff; provenance badge showing capture date and verification status.
6. **Repair loop**: rotted links get archived copy, updated canonical, or a dated removal note — never silently dropped; log all repairs.
7. **Respect the web**: honor robots/ToS for fetching, rate limits, and copyright — archive for evidence, link rather than republish.

## Quality gates
- [ ] Scans scheduled; dashboard lists dead/moved/hijacked links with owners.
- [ ] Every published citation has an archived capture with hash + timestamp.
- [ ] Verification recipe reproducible by a third party.
- [ ] Repairs logged; no broken citation ships.

## Red lines
- No fabricated or synthetic captures; timestamps must come from a real TSA/log.
- Never present archived content as current; never strip a page's authorship while archiving.
- No scraping at volumes that harm the target; no bypassing access controls.

## Related
`research-tooling` · `retrieval-engineering` · `secure-build-pattern` · `knowledge-graph-engineering` · `verification-and-fact-checking`.
