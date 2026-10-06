# MyMilo — Architecture (Phase 1)

```
 Browser ──GET /─────────► Jinja2 chat UI ──fetch──► POST /v1/chat/completions
   │                                                        │
   │                        ┌───────────────────────────────┘
   │                        ▼
   │                 ModelRouter ──► llama.cpp :8080/v1 (default route "local")
   │                        │       (Phase 5: OS endpoint; router migrates up)
   │                        ▼
   │                 SQLite (jobs table — definitions only, Phase 1)
   │
   └──GET /jobs──────► Jinja2 jobs UI ──fetch──► /v1/jobs CRUD
```

## Components

| Module | Responsibility |
|---|---|
| `app/main.py` | App factory, routes, exception → HTTP mapping, HTML pages |
| `app/config.py` | TOML + env-var settings; model routes; secret *names* only |
| `app/router.py` | Model name → OpenAI-compatible upstream; timeouts; honest errors |
| `app/schemas.py` | Pydantic v2 request/response models (OpenAI-compatible chat) |
| `app/db.py` | stdlib sqlite3, WAL mode, schema migrations, jobs table |
| `app/jobs.py` | Job CRUD service (no execution — Phase 3) |
| `templates/` | `base.html`, `index.html` (chat), `jobs.html` (definitions) |
| `static/style.css` | Local stylesheet; zero external dependencies |
| `config/` | `mymilo.example.toml` — copy to `mymilo.toml`, never commit secrets |
| `vault/` | Git-ignored secrets dir; env vars preferred |

## Request flows

**Chat:** `POST /v1/chat/completions` → validate (`stream=true` → 400, not
implemented) → router resolves model → `POST {base_url}/chat/completions`
with optional `Authorization: Bearer <env key>` → upstream JSON passed
through. Backend connections are direct (`trust_env=False`): ambient proxy
variables never reroute or observe model-backend traffic. Unknown model →
404 with available list. Backend down/timeout → 503. Backend 4xx/5xx → 502
with backend status preserved.

**Health:** `GET /health` → `{status, version, backends: {name: bool}}` via
best-effort `GET {base_url}/models` (2s timeout, never raises).

**Jobs:** CRUD at `/v1/jobs`; `PATCH` for name/cron/status; `DELETE` → 204.
`JobNotFoundError` → 404.

## Data model

`jobs(id, name, cron, payload_json, status, last_run_at, next_run_at,
created_at, updated_at)` + `schema_migrations(version, applied_at)`.
Statuses today: `pending` (default). `running`/`done`/`failed` are reserved
for the Phase 3 executor.

## Configuration & secrets

Precedence: `MYMILO_CONFIG` path → `config/mymilo.toml` → built-in defaults.
Env overrides: `MYMILO_HOST`, `MYMILO_PORT`, `MYMILO_DB`, `MYMILO_TIMEOUT`.
API keys live only in the environment (named by `api_key_env`); `vault/`
documents the convention. Nothing secret is logged — error paths truncate
backend bodies to 2000 chars and never include headers.

## Testing strategy

`pytest` with `httpx.MockTransport` standing in for backends — no network in
unit tests. `create_app(settings, transport)` is the seam. CI: install →
`ruff check` → `ruff format --check` → `pytest`. Behavior verification is
separate: boot uvicorn against a stub OpenAI-compatible server and assert
over real HTTP (see CONTRIBUTING).

## Extension points (later phases)

- `ModelRouter` → migrates into the OS layer (Phase 5); add cost hooks here
  in Phase 4 without changing the route interface.
- `jobs` table → Phase 3 scheduler reads `cron`/`next_run_at`; add an
  executor column family then, not now.
- `POST /v1/chat/completions` → Phase 2 retrieval injects context before
  routing; the endpoint signature does not change.
