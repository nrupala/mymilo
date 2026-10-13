---
name: local-first-engineering
description: Build local-first apps - offline data, CRDT sync, conflict handling, E2EE multi-device, honest state UI.
version: 1
triggers: local-first, offline-first, crdt, sync, offline data, multi-device
category: Engineering & code
blurb: Build local-first apps — offline data, CRDT sync, conflict handling and honest state UI.
archetype: knowledge
example: Design offline-first sync for this app without data loss.
---

# Local-First Engineering

Local-first: the device holds the truth, the network is an enhancement. Data works offline, syncs when possible, merges without loss, and stays encrypted in transit — the foundation under vault, reader, and note products.

## When to use
- Building apps where data must work offline (documents, vaults, notes, readers).
- Adding multi-device sync to an app with local storage.
- Designing merge/conflict behavior for collaborative or personal data.

## Method
1. **Local truth**: device store (IndexedDB/SQLite) is authoritative; the server is a relay + backup, not a gate. Design flows airplane-mode-first.
2. **Data model**: CRDTs (or OT) for mergeable state; per-field merge semantics; stable document/entity IDs; tombstones + compaction policy.
3. **Sync protocol**: delta sync over WebSocket/WebRTC, causal ordering, resumability, bandwidth budgets; store-and-forward for intermittent peers; vector clocks/version vectors for causality.
4. **Encryption**: E2EE before upload — keys never leave devices (see zero-knowledge); per-device keys, key hierarchy, recovery UX that is tested like a feature.
5. **Conflicts**: automatic merges (CRDT) for text & counters; explicit UI only for semantic conflicts; never silent last-write-wins on user prose; always no-data-loss.
6. **State UI**: honest indicators — offline / queued / syncing / synced / conflict; export & import escape hatches; sync diagnostics.
7. **Testing**: chaos scenarios (offline, clock skew, concurrent edits, device loss), property tests for merge invariants (commutative, associative, idempotent), real device matrices.

## Quality gates
- [ ] Core flows work fully offline; sync resumes cleanly after long offline periods.
- [ ] Merge invariants property-tested; no user edit can be lost.
- [ ] E2EE verified; key recovery exercised end-to-end.
- [ ] Export/import tested on real data volumes.
- [ ] State UI tells the truth in every sync state.

## Red lines
- No silent data loss, ever; no last-write-wins on user prose.
- No sync of personal data without encryption (per product class).
- No "sync" badge without real multi-device round-trip tests.

## Related
`pwa-offline-engineering` · `zero-knowledge-systems` · `mobile-native` · `secure-build-pattern` · `multi-surface-webapp`.
