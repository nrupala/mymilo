---
name: retrieval-engineering
description: Build search & RAG that answers — indexing, hybrid retrieval, reranking, retrieval evals, access-scoped filters.
version: 1
triggers: rag, retrieval, search, indexing, reranking, vector search, embeddings
category: Engineering & code
blurb: Build search and RAG that answers — indexing, hybrid retrieval, reranking and retrieval evals.
archetype: knowledge
example: Fix my RAG so it stops returning irrelevant chunks.
---

# Retrieval Engineering

Retrieval is where AI systems get their facts. Index deliberately, retrieve hybrid (lexical + vector), rerank with budget, and evaluate before tuning — always.

## When to use
- Search features (Solr-class indexes, vector stores), RAG pipelines.
- Agent retrieval layers (knowledge graphs, document bases).
- Fixing "the model answers wrong" that is actually "retrieval returned junk".

## Method
1. **Corpus first**: what's indexed, freshness requirements, dedup rules, per-document provenance; **chunking strategy** (semantic units, overlap discipline, stable chunk ids) — chunking is 80% of RAG quality.
2. **Hybrid retrieval**: BM25/lexical for exact terms (codes, names, numbers) + vector kNN for meaning; combine scores with tuned weights; embed model version pinned (reindex plan for any model change).
3. **Rerank with budget**: top-K → reranker (cross-encoder-class or LLM with token budget) → top-N for context; **filters (time, type, access scope) applied before ranking or hard-enforced in queries** — never leak filtered documents.
4. **Index hygiene**: incremental updates + tombstones; periodic full rebuild drill; index size/quota budgets monitored.
5. **Evaluation before tuning**: golden queries with labeled relevant docs; measure recall@k / MRR / nDCG; regression gates on every index/pipeline change; log real queries (privacy-scoped) to find gaps.
6. **Serving**: latency budgets per stage (embed, search, rerank); cache hot queries; degradation path (lexical-only fallback) when vectors are unavailable.
7. **Privacy**: query-time access scopes; sensitive content excluded or encrypted-at-rest unless explicitly indexed; prefer local embeddings for private corpora (`local-llm-serving`).

## Quality gates
- [ ] Golden-set evals with thresholds, run in CI/regression.
- [ ] Filters enforced pre-rank; scope leakage tested.
- [ ] Embedding model + index versioned; rebuild drill done.
- [ ] Latency budget measured; fallback path exists.

## Red lines
- No tuning without evals; no cross-scope leakage; no unbounded context dumps to models — budget the tokens.

## Related
`knowledge-graph-engineering` · `local-llm-serving` · `data-ml-pipelines`.
