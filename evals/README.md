# MyMilo evals

Deterministic, CI-safe evaluation of the retrieval machinery. The corpus
(`corpus/`) is small fixture documents with distinctive facts;
`questions.jsonl` maps each question to the document that must rank first.

## Metrics (from the original spec, adapted honestly)

1. **Retrieval hit rate** — fraction of eval questions whose expected
   document ranks #1 in the top-k results. Target: >80%.
   Measured in `tests/test_rag.py::test_eval_hit_rate` with the
   deterministic `HashEmbedder`. This tests the *machinery* (chunking,
   indexing, ranking, top-k plumbing) — not semantic quality.
2. **Citation integrity (no hallucinated citations)** — every
   `(source: file, chunk N)` citation in a RAG answer must resolve to a
   retrieved chunk. Tested as a pure function in
   `tests/test_rag.py::test_citation_verification_catches_hallucination`,
   and end-to-end through `/v1/chat/completions` with `rag.enabled`.
3. **JSON parse rate** — not applicable in Phase 2: there is no strict-JSON
   output mode yet. It will be wired when structured output lands.

## What CI measures vs what it doesn't

CI (HashEmbedder): machinery correctness — ingestion round-trips, ranking
orders by token overlap, citations resolve, documents CRUD. Deterministic,
no model needed.

Semantic quality (real hit-rate numbers with the llama.cpp embedding
backend): run locally —
`MYMILO_EVAL_LLM=1` gates are not needed for retrieval; point the config at
a real embedding backend and run `pytest tests/test_rag.py -k hit_rate`.
The fixture questions are written so a real embedder should score 6/6.

## Running

```bash
python -m pytest tests/test_rag.py -q
```
