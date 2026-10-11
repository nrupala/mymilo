# Connectors

What MyMilo connects to, what it deliberately does not, and
where connections are headed. Posture first: **connections
are per-purpose and revocable.** Accounts stay disconnected
by default; a connection is made for a task and dropped when
the task ends, and nothing read for a task is retained.

## Live today

| Connection | What it does | Notes |
|---|---|---|
| Web search | Fresh facts with titles + URLs, cited as sources | Server-side |
| Live market data | The market brief behind `stock-analysis` | Fires only when the skill is active and a brief is asked for |
| GitHub | Repo work — reads, issues, pull requests | Via scoped tokens, server-side |
| oc-bridge (MCP) | Dispatches coding tasks to OpenCode on Aetheris; Milo acts as foreman | `https://oc.aimlds.org/mcp` behind Cloudflare Access; see [HUMAN-MACHINE-AGENT.md](HUMAN-MACHINE-AGENT.md) |
| Conduit (MCP) | SEC EDGAR filings & fundamentals as 24 upstream tools (`conduit_*`) | Conduit's hosted connector on Cloudflare Workers; `CONDUIT_API_KEY` (metered, free tier 100 calls/day) |
| MCP server | MyMilo itself exposes an MCP surface so other agents can call it | `app/mcp_server.py` |
| Device API | The Android app: chat, sync, skills bundle, client config | Device-token auth — see [OPERATIONS.md](OPERATIONS.md#devices) |

## Disconnected by default

- **Gmail and Google Calendar** stay disconnected. They are
  connected only when a specific task needs them and
  disconnected immediately after; nothing read for the task
  is kept. This is the operator's standing privacy rule, not
  a missing feature.

## On the roadmap

- **A connectors screen in the app** — one place showing
  built-in live status, connectable accounts (under the same
  disconnect-by-default posture), and on-device capabilities,
  so what Milo *can* reach is visible instead of implied.
- **Sources & Vault** — the app's own connections: API
  sources (Aetheris, OpenRouter, OpenCode Zen, custom
  endpoints) whose tokens live in a write-only on-device
  vault. See [HUMAN-MACHINE-AGENT.md](HUMAN-MACHINE-AGENT.md).

See also: [Operations manual](OPERATIONS.md) ·
[Code guide](CODE-GUIDE.md)
