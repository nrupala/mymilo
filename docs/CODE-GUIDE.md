# Code guide

How MyMilo is put together, for anyone reading or changing
the code. Design background: [SHADOW-ARCHITECTURE.md](SHADOW-ARCHITECTURE.md).

## Map

| Path | What lives there |
|---|---|
| `app/main.py` | The FastAPI app: routes, chat handler, auth resolution, pages |
| `app/router.py` | Model routing — task → route, concurrency, failure gating |
| `app/skills.py` | The skill system: frontmatter parsing, trigger matching, the bundle |
| `app/context.py`, `app/context_builder.py` | Priority-ordered context assembly for each turn |
| `app/memory*.py`, `app/semantic*.py` | Episodic + semantic memory |
| `app/devices.py` | Device registry and token lifecycle |
| `app/documents.py` | Uploaded-document reading (keeps your place) |
| `app/jobs.py` | Background jobs |
| `app/mcp_server.py` | The MCP surface Milo exposes to other agents |
| `skills/` | 81 drop-a-file skills — see [SKILLS.md](SKILLS.md) |
| `templates/`, `static/` | Web UI (chat, devices, jobs, costs, documents, guide) |
| `tests/` | The pytest suite (see [QUALITY.md](QUALITY.md)) |
| `scripts/` | Repo tooling (e.g. the skills-doc generator) |

## A chat turn, end to end

1. **Auth** — `_resolve_user`: Cloudflare Access email header
   first, then a Bearer device token, else anonymous ("").
   The API host's guard turns anonymous into 401; the browser
   host serves anonymous an empty view.
2. **Skill selection** — if the request names a `skill`, that
   skill is force-activated (`get_skill_by_name`, v0.41.0) —
   including skills with no triggers. Otherwise trigger
   matching (`match_skill`) decides. The skill's body is
   prepended as a system message.
3. **Context** — memory facts, relevant past chats, and
   document chunks are assembled under the token budget by
   the Token-Efficiency Engine.
4. **Route** — the router picks a model route (`os` default,
   `local`, `openrouter`, …) with per-route concurrency and
   failure gating.
5. **Sources** — the response carries a `sources` list naming
   everything the turn actually used (skill, memory fact,
   past chat, web title+URL, live market brief, document
   chunk), deduplicated. Empty means the model answered from
   itself — stated, not hidden.

## The skill system

A skill is a directory `skills/<name>/SKILL.md`:

```markdown
---
name: my-skill
description: One line for registries (older field).
triggers: comma, separated, phrases
category: Money & markets
blurb: What it does, in plain words, a sentence or two.
example: An example prompt worth trying.
---

# My Skill

The instruction body — the know-how itself.
```

- `name` must equal the directory name.
- `triggers` are matched against the user's words,
  case-insensitively, on the server and on the phone.
- `category` / `blurb` / `example` are the catalogue fields
  (v0.42.0): they power the app's Skills screen, `/guide`,
  and [SKILLS.md](SKILLS.md). No triggers ≠ invisible: the
  bundle carries every skill, trigger-less included.
- After editing skills, regenerate the catalogue doc:
  `python scripts/generate-skills-doc.py` — a test keeps it
  honest. The running server rescans periodically and via
  `POST /v1/skills/rescan` (auth required).
- `GET /v1/skills` and `GET /v1/skills/bundle` require auth.

## Conventions

- SPDX header (AGPL-3.0) on source files.
- Ruff gates formatting and lint (`ruff check app/`,
  `ruff format --check app/ tests/`).
- Dependencies are verified in a fresh virtual environment
  before pushing — CI installs `.[dev]` bare; the ambient
  dev environment is not evidence.
- Public content stays supplier-agnostic (no OEM or model
  names in anything public-facing).

See also: [Operations manual](OPERATIONS.md) ·
[Quality & the release gates](QUALITY.md) ·
[Connectors](CONNECTORS.md)
