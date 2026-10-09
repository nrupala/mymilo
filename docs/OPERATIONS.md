# Operations manual

Running MyMilo in production: what the moving parts are, how
to check health, and how to change things safely.

## Shape of the deployment

- **Host:** the Aetheris box; service `mymilo.service`
  (systemd), install at `/opt/mymilo`, data at
  `/opt/mymilo/data`, internal port `127.0.0.1:7071`.
- **Public entry:** Cloudflare tunnel `oracle-aetheris`.
  - `https://mymilo.aimlds.org` — browser host, behind
    Cloudflare Access (signed-in users).
  - `https://mymilo-api.aimlds.org` — API host for native
    clients, **no Access app**; device-token auth is the gate.
    Behavior differs by host: an unresolvable token yields
    **401 on the API host** (guard middleware) and an empty
    result set on the browser host.
- **Models on the box:** llama.cpp servers — Phi-4-mini
  (chat, :7072), Qwen3-Embedding (:7073); the AxiomSpine
  dispatcher on :7070 is the default route (`os`).

## Health

`GET /health` (unauthenticated, safe to poll) returns:

- `status`, `version` — the running build.
- `backends` — per-route reachability (local, embeddings,
  openrouter, os).
- `routes` — per-route last use, consecutive failures, gating,
  in-flight count, concurrency caps.
- `engine` — Token-Efficiency Engine telemetry: requests,
  prompt/completion tokens, cache reuse, tokens saved versus
  full-history, estimator bias.

**Known wart:** the nested `embeddings` probe block can read
`ok:false` while `backends.embeddings` reads true. The route
works; the probe is stricter than the path it probes. Tracked
in the audit backlog — do not chase it as an outage.

## Devices

Native clients authenticate with per-device tokens.

- Register, list, rotate, and remove devices on the
  **`/devices`** page (browser host, signed in), or via
  `POST /v1/devices`, `POST /v1/devices/{id}/rotate`,
  `POST /v1/devices/{id}/remove`.
- A token is shown **once**, at creation or rotation. Only its
  hash is stored. Rotation kills the old token immediately;
  removal deletes the row and the token with it.
- Tokens are secrets: create and revoke them on the box or
  the devices page, never in chat, tickets, or logs.

## Configuration

- The server config lives at `/opt/mymilo/config/mymilo.toml`
  — **deploys never overwrite it.** The example file
  (`config/mymilo.example.toml`) documents every key.
- Environment (`.env`, preserved across deploys) carries
  credentials and endpoints.
- `MYMILO_SUPPORT_URL` — where the Support button points (in
  the app's About screen and on `/guide`). Served to clients
  as `support_url` in `GET /v1/client/config`, so it can
  change any time with a service restart — no app release.
  Empty hides the button everywhere.

## Deploying

1. Work lands by pull request; CI must be green on the exact
   head before merge (see [QUALITY.md](QUALITY.md)).
2. Deploy the merged main: replace `app templates static
   tests docs mcp skills` plus the example config and
   CHANGELOG from the release tarball; preserve `.env` and
   `config/mymilo.toml`; reinstall into the venv; restart.
3. Verify `/health` reports the new version and the release's
   behavior proofs pass against the live box (gate 4 — see
   the release's verification record).

## Data

- `data/mymilo.db` — application state.
- `data/memory.db` — sessions and the device registry.
- `data/semantic_facts.json` — remembered facts.
- Chats and memory belong to the operator. Nothing is sold;
  there are no ads and no third-party analytics.

See also: [Code guide](CODE-GUIDE.md) ·
[Quality & the release gates](QUALITY.md) ·
[Connectors](CONNECTORS.md)
