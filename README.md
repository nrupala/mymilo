# MyMilo

**mymilo** — Nrupal Akolkar's personal phone assistant and agentic OS
resident. A FastAPI backend with an Apple-quality chat UI, an MCP server
so other agents can call it, a file-based escalation queue to Wright
(the human's builder agent), dual episodic + semantic memory, a
priority-ordered context builder, 81 drop-a-file skills with a
plain-language catalogue, and privacy-first
Gmail/Calendar/Cloudflare/GitHub integrations.

Local-first, on his own hardware, multi-user (Nrupal + Natasha),
no credits. Named "milo" between Nrupal and Wright.

> Owned by Nrupal Akolkar · Built with Muse by Meta

**License:** AGPL-3.0-or-later — see [LICENSE](LICENSE), [NOTICE](NOTICE),
and [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md) for the commercial
license option. Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) ·
History: [CHANGELOG.md](CHANGELOG.md).

## Features

- **Chat UI** — Apple-quality web chat (`templates/`, `static/`), OpenAI-compatible
  `/v1/chat/completions`, per-user sessions via Cloudflare Access email identity.
- **MCP server (Phase 1)** — SSE at `/mcp/sse` + `/mcp/messages`; 27 tools
  (19 core: chat, retrieve, documents, jobs, ledger, skills, …; 3 GitHub;
  3 Cloudflare; 2 Gmail/Calendar). Machine-readable surface at
  `/v1/mcp/tools` and `/.well-known/mymilo.json`.
- **Escalation queue (Phase 2)** — file-based Milo→Wright queue at
  `data/escalations/`; per-turn detection routes hard tasks to Wright mid-chat.
- **Episodic memory** — keyword search over past sessions; episode summaries
  injected into chat context.
- **Semantic memory** — durable facts extracted from conversation
  (`/v1/profile`); user-deletable.
- **Unified context builder** — system, skill, episodic, RAG, and history
  assembled in priority order under a token budget.
- **81 skills** — drop-a-file `skills/*/SKILL.md` with trigger phrases;
  matched deterministically, and every skill can also be **run on
  purpose** (chat requests may name a `skill`; the Android app has a
  tap-to-run catalogue). Each skill carries a category, a
  plain-language blurb, and an example — see
  [docs/SKILLS.md](docs/SKILLS.md).
- **Sources on every answer** — chat responses name what the turn
  used (skill, memory fact, past chat, web result, market brief,
  document chunk); nothing used, nothing claimed.
- **Devices** — per-device tokens for native clients, with rotate
  and remove; shown once, stored hashed ([/devices](docs/OPERATIONS.md#devices)).
- **Guide** — a built-in user guide at `/guide` (quick start,
  live skills catalogue, use cases, FAQ, About), mirrored in the
  Android app and in [docs/USER-GUIDE.md](docs/USER-GUIDE.md).
- **Integrations** — GitHub (live, 81 repos), Gmail/Calendar (privacy-first:
  connect per task, disconnect after, no retention), Cloudflare (zones, DNS,
  Workers).
- **Multi-user** — separate sessions and memory per user.
- **Background jobs** — cron-scheduled job types (briefing, reminder,
  background_task), consent-gated actions, planner suggestions outbox.
- **Fleet economics** — per-route cost ledger and quota flags
  (`/v1/ledger/summary`).
- **Android app** — the native client
  ([mymilo-native](https://github.com/nrupala/mymilo-native)):
  on-device skill matching, offline tools, voice, in-app updates.

## Documentation

| Doc | What it covers |
|---|---|
| [User guide](docs/USER-GUIDE.md) | What Milo can do, how to ask, FAQ — also served at `/guide` |
| [Skills catalogue](docs/SKILLS.md) | All 81 skills: what each does, an example (generated — kept honest by a test) |
| [Operations manual](docs/OPERATIONS.md) | Deployment, health, devices & tokens, configuration, deploys |
| [Code guide](docs/CODE-GUIDE.md) | Architecture map, a chat turn end to end, how to write a skill |
| [Connectors](docs/CONNECTORS.md) | What's connected, what's disconnected by default, what's next |
| [Human, machine, agent](docs/HUMAN-MACHINE-AGENT.md) | The three actors, the routing ladder, Sources & Vault |
| [Quality & gates](docs/QUALITY.md) | The four release gates, merge discipline, verification records |
| [Shadow architecture](docs/SHADOW-ARCHITECTURE.md) | The design: Milo as shadow partner |
| [Release gate](docs/RELEASE-GATE.md) | The verification doctrine in full |
| [Backlog](docs/BACKLOG.md) | Queued work and known warts |

## Architecture

```
                    +------------------- Cloudflare Access -------------------+
                    |  https://mymilo.aimlds.org  (tunnel -> 127.0.0.1:7071)  |
                    +---------------------------+---------------------------+
                                                |
                                        +-------v--------+
                                        |  app/main.py   |  FastAPI
                                        |  (routes, UI,  |
                                        |   MCP SSE)     |
                                        +---+---+---+----+
                                            |   |   |
                +---------------------------+   |   +-----------------------+
                |                               |                           |
        +-------v--------+            +---------v----------+      +---------v----------+
        | Model router   |            | Context builder    |      | Escalation queue   |
        | local (llama   |            | (priority-ordered,  |      | data/escalations/  |
        | .cpp) / cloud  |            | budget-trimmed)     |      | -> Wright          |
        +-------+--------+            +---------+----------+      +--------------------+
                |                               |
        +-------v--------+            +---------v----------+
        | Memory         |            | Skills (81)        |
        | episodic +     |            | trigger-matched    |
        | semantic facts |            | drop-a-file        |
        +----------------+            +------------------+
                |
        +-------v--------+
        | Integrations   |
        | GitHub, Gmail, |
        | Calendar, CF   |
        +----------------+
```

Key modules: `app/main.py` (FastAPI app, chat, sessions, MCP SSE,
escalation), `app/mcp_server.py` (27-tool catalog), `app/memory.py`
(episodic), `app/semantic.py` (facts + profile), `app/context_builder.py`
(context assembly), `app/skills.py` (81 skills), `app/router.py` (model
routing), `app/devices.py` (device tokens), `app/scheduler.py` +
`app/jobs.py` (background jobs),
`app/integrations/{github,gmail,calendar,cloudflare}.py`.

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

Open http://127.0.0.1:8090 for the chat UI.

**Note:** the production box serves on `127.0.0.1:7071` behind a
Cloudflare tunnel; the repo default is `127.0.0.1:8090`.

## Build

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

CI-faithful check in a clean venv (required before pushing — the ambient
dev env may hide missing deps):

```bash
python -m venv /tmp/civenv && source /tmp/civenv/bin/activate
pip install --no-cache-dir -e ".[dev]"
ruff check app tests && ruff format --check app tests && python -m pytest -q
```

## Test

```bash
python -m pytest -q                 # full suite (MockTransport — no network)
python -m pytest tests/test_memory.py -q   # one module
```

Behavior verification (real HTTP against a stub backend) — see
[CONTRIBUTING.md](CONTRIBUTING.md); "verified" means observed behavior,
never files-present.

## Usage

```bash
# health (includes per-backend reachability)
curl localhost:8090/health

# chat (OpenAI-compatible)
curl localhost:8090/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "local",
  "messages": [{"role": "user", "content": "Hello, Milo."}]
}'

# sessions (per-user; email identity from Cloudflare Access)
curl -X POST localhost:8090/v1/sessions
curl localhost:8090/v1/sessions

# MCP surface: tools list as data, SSE endpoint for agents
curl localhost:8090/v1/mcp/tools            # 27 tools
curl localhost:8090/.well-known/mymilo.json

# semantic memory: facts profile
curl localhost:8090/v1/profile
curl -X DELETE localhost:8090/v1/profile/facts/<fact_id>

# skills: list, rescan (both require auth — a device token or a
# signed-in browser session)
curl localhost:8090/v1/skills -H "Authorization: Bearer <device-token>"
curl -X POST localhost:8090/v1/skills/rescan -H "Authorization: Bearer <device-token>"

# devices: the token lifecycle (register returns the token ONCE)
curl -X POST localhost:8090/v1/devices -H "Authorization: Bearer <device-token>" \
  -H 'Content-Type: application/json' -d '{"name": "My phone"}'
curl -X POST localhost:8090/v1/devices/<id>/rotate -H "Authorization: Bearer <device-token>"
curl -X POST localhost:8090/v1/devices/<id>/remove -H "Authorization: Bearer <device-token>"

# background jobs + planner
curl localhost:8090/v1/jobs
curl -X POST localhost:8090/v1/jobs/<id>/trigger
curl localhost:8090/v1/suggestions

# documents: upload, retrieve (RAG)
curl -X POST localhost:8090/v1/documents -F "file=@report.pdf"
curl -X POST localhost:8090/v1/retrieve -H 'Content-Type: application/json' -d '{
  "query": "seal replacement interval", "top_k": 5
}'

# export a session
curl -X POST localhost:8090/v1/export -H 'Content-Type: application/json' -d '{
  "session_id": "<id>", "format": "md"
}'
```

Embeddings default to llama.cpp's `/embeddings` endpoint — run it with an
embedding model, e.g. `llama-server -m nomic-embed-text.gguf --embedding
--port 8080`. See `config/mymilo.example.toml` (`[embeddings]`) and
`evals/README.md`.

## Configuration

`config/mymilo.toml` (TOML). Env overrides win over file values.

| Env var | Purpose |
|---|---|
| `MYMILO_CONFIG` | Path to TOML config (default `config/mymilo.toml`) |
| `MYMILO_HOST` / `MYMILO_PORT` | Bind host/port |
| `MYMILO_DB` | SQLite path |
| `MYMILO_TIMEOUT` | Request timeout (s) |
| `MYMILO_VAULT_PATH` | Secrets vault directory |
| `MYMILO_SKILLS_DIR` | Skills directory (default `skills`) |
| `MYMILO_SCHEDULER_ENABLED` / `MYMILO_SCHEDULER_TICK` | Background scheduler |
| `MYMILO_OS_ENDPOINT` | AxiomSpine/OS endpoint |
| `MYMILO_EXA_API_KEY` | Exa web-search key |
| `MYMILO_SUPPORT_URL` | Support-button destination served to clients (empty hides it) |
| `MYMILO_CLOUD_API_KEY` | Cloud model key (e.g. OpenRouter) |
| `GITHUB_TOKEN` | GitHub integration token |
| `CONDUIT_API_KEY` | Conduit MCP connector key (`cndt_…`; free tier 100 calls/day) |
| `CLOUDFLARE_API_TOKEN` | Cloudflare integration token |

API keys come from the environment only — never from the config file,
never from the repo. See `vault/README.md`.

## Layout

```
app/           FastAPI: main, config, router, schemas, db, jobs, memory,
               semantic, context_builder, skills, mcp_server, integrations
mcp/           MCP tool catalog JSON (19 core + github + gmail/calendar + cf + conduit)
skills/        81 drop-a-file skills (SKILL.md each, catalogued)
templates/     Jinja2 UI (chat, devices, jobs, costs, documents, guide)
static/        local stylesheet, zero external deps
config/        example TOML
vault/         git-ignored secrets (convention doc only)
tests/         pytest suite (MockTransport — no network)
evals/         retrieval evals
docs/          the documentation set — index in Documentation above
scripts/       repo tooling (skills-doc generator)
```

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
Commercial use without AGPL obligations: [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).
