# MyMilo

**MyMilo** — Nrupal's native town-like buddy: the resident interface of his
personal agentic OS. One product, two layers: the OS (sovereign memory,
persona/state, orchestrator, connectors) underneath; MyMilo as its face —
the buddy that runs routines, holds conversations, and talks to him. Local
first, on his hardware, no credits.

Constitution: [SPEC.md](SPEC.md) · Build: [ARCHITECTURE.md](ARCHITECTURE.md) ·
Plan: [ROADMAP.md](ROADMAP.md) · Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp config/mymilo.example.toml config/mymilo.toml   # edit routes as needed
mymilo                                            # serves on 127.0.0.1:8090
```

Point the default `local` route at llama.cpp:

```bash
llama-server -m <model.gguf> --port 8080
```

Open http://127.0.0.1:8090 for the chat UI, `/jobs` for job definitions.

## Usage

```bash
# health (includes per-backend reachability)
curl localhost:8090/health

# chat (OpenAI-compatible)
curl localhost:8090/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "local",
  "messages": [{"role": "user", "content": "Hello, Milo."}]
}'

# jobs: definitions only in Phase 1 — nothing executes yet
curl localhost:8090/v1/jobs
curl -X POST localhost:8090/v1/jobs -H 'Content-Type: application/json' -d '{
  "name": "morning-briefing", "cron": "0 7 * * *", "payload": {}
}'

# documents: upload, list, retrieve (Phase 2)
curl -X POST localhost:8090/v1/documents -F "file=@report.pdf"
curl localhost:8090/v1/documents
curl -X POST localhost:8090/v1/retrieve -H 'Content-Type: application/json' -d '{
  "query": "seal replacement interval", "top_k": 5
}'

# RAG chat: set "rag": {"enabled": true} — answer cites (source: file, chunk N)
curl localhost:8090/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "local",
  "messages": [{"role": "user", "content": "What is the seal interval?"}],
  "rag": {"enabled": true, "top_k": 5}
}'
```

Embeddings default to llama.cpp's `/embeddings` endpoint — run it with an
embedding model, e.g. `llama-server -m nomic-embed-text.gguf --embedding
--port 8080`. See `config/mymilo.example.toml` (`[embeddings]`) and
`evals/README.md` for the eval story.

## Configuration

`config/mymilo.toml` (TOML) with env overrides: `MYMILO_CONFIG`,
`MYMILO_HOST`, `MYMILO_PORT`, `MYMILO_DB`, `MYMILO_TIMEOUT`. API keys come
from the environment only (see `api_key_env` + `vault/README.md`) — never
from the config file, never from the repo.

## Layout

```
app/         FastAPI: main, config, router, schemas, db, jobs
templates/   Jinja2 UI (chat, jobs) — every endpoint ships an interface
static/      local stylesheet, zero external deps
config/      example TOML
vault/       git-ignored secrets (convention doc only)
tests/       pytest suite (MockTransport — no network)
```

## Status

**Now:** Phase 2 retrieval — document ingestion, llama.cpp embeddings,
cosine search, RAG chat with citation verification, evals.
**Next:** Phase 3 proactive engine (deterministic planner, consent-gated
actions, scheduler/digest design — maven transfers).
**Then:** fleet economics, OS platform layer.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
