---
name: json-data-interchange
description: Use JSON safely and predictably — schemas, canonical forms, versioning, parse limits, big-number care.
version: 1
triggers: json, json schema, data interchange, canonical json, parse json safely
category: Engineering & code
blurb: Use JSON safely and predictably — schemas, canonical forms, versioning and parse limits.
archetype: knowledge
example: Design a JSON format that won't break as it evolves.
---

# JSON Data Interchange

JSON is the lingua franca — and a minefield of ambiguity. Be strict when writing, tolerant when reading, and explicit about both.

## When to use
- Any API payload, config file, event message, or stored document.
- Reviewing parsing/serialization code; debugging interop issues.

## Method
1. **Schema-first**: a JSON Schema (or typed schema in TS/Python) for every external payload; validate at the boundary.
2. **Strict writer / tolerant reader**: emit exactly your schema; accept documented variations; reject the rest loudly.
3. **Canonical form when hashing/signing**: fixed key ordering + number formatting; floats are IEEE-754 — **money/big integers as strings**; document the canonical rules next to the schema.
4. **Versioning**: a version field on everything persisted or sent; additive changes by default; breaking changes = new version.
5. **Parsing safety**: size + depth limits on untrusted input; no `eval`; handle duplicate keys deliberately; UTF-8 only, escapes normalized.
6. **Streaming & scale**: NDJSON for logs/events; streaming parsers for large files; don't pretty-print megabytes for storage (pretty for humans, compact for machines).
7. **Ops**: jq for inspection; diffs in reviews; keep sample fixtures per schema.

## Quality gates
- [ ] Every external payload has a schema + sample.
- [ ] Canonicalization documented wherever hashes/signatures cover JSON.
- [ ] Parse errors on bad input are explicit (not silent defaults).
- [ ] No float usage for money or >2^53 integers.

## Red lines
- No unbounded parsing of untrusted input (DoS).
- No "it's just JSON" config edits without schema validation in CI.

## Related
`api contracts` (`backend-engineering`) · `cryptography-engineering` (signing canonical bytes) · `secure-build-pattern`.
