---
name: knowledge-graph-engineering
description: Build knowledge graphs that serve users — schema, provenance, immutable history, query patterns, portable exports.
version: 1
triggers: knowledge graph, graph schema, provenance, graph queries
category: Engineering & code
blurb: Build knowledge graphs that serve users — schema, provenance, immutable history, portable exports.
archetype: knowledge
example: Design a knowledge graph schema for my research notes.
---

# Knowledge Graph Engineering

A knowledge graph earns trust three ways: everything has provenance, nothing is silently rewritten, and the user can walk away with their data.

## When to use
- Personal/knowledge systems (immutable, portable graphs), PKM features.
- Entity graphs for content, agent memory layers, retrieval engines.

## Method
1. **Model deliberately**: entities/relations/attributes; start small (10–20 core types); schema changes go through migrations like a database; stable IDs everywhere.
2. **Provenance on every assertion**: source, date, confidence; distinguish user-asserted vs inferred vs imported facts — this is what makes outputs auditable (`ledger-engineering` spirit).
3. **Immutable history**: append-only event log as the source of truth; current state = projection; corrections = new events referencing the old. Time-travel comes free.
4. **Storage fit**: SQLite/Postgres with an edges table for most needs; a dedicated graph DB only when query complexity or scale demands; pair with full-text + vector indexes for retrieval.
5. **Query & retrieval**: canonical query patterns (neighborhoods, paths, temporal windows); for agents, bounded answers — counts first, expand on request (token-aware serialization); never dump the graph.
6. **Portability & ownership**: export/import formats tested round-trip (simple JSON/JSON-LD); versioned snapshots; deletion is real (plus tombstones where required).
7. **Privacy & encryption**: graphs reveal relationships — scope access, encrypt at rest; sensitive nodes redactable; never ingest third-party personal data without a lawful basis.

## Quality gates
- [ ] Schema + migration path documented; stable IDs.
- [ ] Every assertion carries provenance.
- [ ] Export/import round-trip tested.
- [ ] Agent queries bounded; access scoped.

## Red lines
- No silent edits (append or version); no unprovenanced assertions presented as fact; deletion must actually delete.

## Related
`ledger-engineering` · `data-ml-pipelines` · `zero-knowledge-systems`.
