---
name: codebase-intelligence
description: Index once, query as data — how to answer structural codebase questions from a code graph. Deterministic intent routing, aggregate-first output, domain-blind analysis.
version: 1
triggers: codebase, code graph, who calls, what calls, dependencies, blast radius, impact analysis, callers, callees, code structure, architecture map, find usages, trace, code navigation, repo map, symbols
---
# Codebase Intelligence — Index Once, Query as Data

When asked a structural question about a codebase — *what calls this?
what breaks if I change this? how are these two modules connected?* —
**do not start reading files.** Map the structure first, answer from the
graph, read code only for what the graph can't tell you.

The pattern (from codetopo): index the repository once into a queryable
graph of symbols, calls, and references. Then every structural question
is a query against that graph — with JSON answers you can act on.

## The index

- **Index once, query many times.** Parsing is the expensive part;
  queries are cheap. Never re-scan the tree to answer one question.
- Nodes: packages, modules, files, functions, classes, externals.
  Edges: calls, references, contains, imports. Typed edges matter —
  `a --calls--> b` is a different claim than `a --imports--> b`.
- **The index is the source of truth for structure.** If the index is
  stale, say so and re-index — never answer structural questions from
  memory of the code.

## Intent routing — match the question to the query

Route every structural question to exactly one intent. Be deterministic
about it:

| They ask | You run | It answers |
|---|---|---|
| "what calls this?" / "what does this reach?" | **descendants** | everything downstream of the node |
| "what depends on this?" / "who uses this?" | **ancestors** | everything upstream of the node |
| "what breaks if I change this?" | **blast-radius** | the full failure footprint |
| "how are A and B connected?" | **path** | shortest typed path between two nodes |
| "what does this repo look like?" | **stats** | node/edge counts by kind — the shape |
| "give me the whole thing" | **snapshot** | frozen portable export of the graph |
| "can I trust this index?" | **verify** | re-walk the hash-chained audit log |

If the question doesn't fit an intent, say so — don't force it.

## Aggregate-first output

**Counts before lists. Always.**

- Default answer: the total and the shape ("14 nodes in the blast
  radius: 9 functions, 3 modules, 2 files").
- Full lists only on explicit request (`--expand` / "show me the list").
- This keeps token budgets sane and pipes composable. A 10,000-node
  dump answers nothing; a count with a breakdown answers the question.

## Domain-blind discipline

- **No scoring, no rankings, no opinions.** The graph says what the
  structure IS, never what it MEANS or whether it's good.
- Centrality, "importance," code-smell judgments, quality scores —
  all out of scope. Structure is data; meaning belongs to the agent
  and the team composing on top.
- When you catch yourself editorializing ("this is tightly coupled"),
  restate as structure ("these 6 modules all call this function").

## Rules

- Structure questions get graph answers, not file reads. Read code to
  understand *behavior*; query the graph to understand *structure*.
- State the intent you routed to ("Blast radius of X: 14 nodes").
- Typed edges in every path answer — hops without kinds are trivia.
- Cross-check when it matters: two surfaces over the same graph must
  agree (see codetopo-verify).
- Snapshot before big refactors: a frozen export is the before-photo.

## Honest limits

- The graph sees structure, not runtime: dynamic dispatch, reflection,
  dependency injection, and eval'd code are invisible or approximate.
- Extractors cover specific languages (codetopo: Rust, TypeScript /
  JavaScript). Unparsed languages are blind spots — say which.
- A stale index lies confidently. Re-index after changes, verify the
  log, then answer.
- External symbols (libraries, frameworks) appear as boundary nodes —
  the graph stops at the repo edge. It won't tell you what the
  library does inside.
