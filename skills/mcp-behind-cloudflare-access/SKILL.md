---
name: mcp-behind-cloudflare-access
description: Playbook for exposing a self-hosted/headless MCP server to Town (or any non-browser MCP client) through Cloudflare Access + Cloudflare Tunnel, and for debugging why such a bridge won't connect. Use this WHENEVER wiring Town/Milo to an MCP bridge behind Cloudflare Access (the Aetheris oc-bridge Town→OpenCode, the planned local-OpenCode target, mcp.aimlds.org, or any future one), or WHENEVER an MCP server authenticates (oauthStatus valid) but shows 0 tools, returns 421 Misdirected Request, or hangs/times out on write calls while reads work. Covers the three sequential gates (Cloudflare Access binding-cookie edge, MCP DNS-rebinding transport security, and the write-tool async/elicitation handler) plus the layer-localization diagnostic method.
category: How Milo works
blurb: The playbook for connecting Milo to tools behind Cloudflare Access — and for debugging the three gates where such bridges usually fail.
example: My MCP bridge shows zero tools — walk the three gates.
---

# MCP server behind Cloudflare Access — connection playbook

Getting a self-hosted MCP server reachable by Town (or any non-browser MCP client) through Cloudflare Access + Tunnel fails at up to three *sequential, independent* gates. Each gate has a distinct symptom, and a later gate only becomes visible once the earlier one is open. Fix them in order. Learned the hard way bringing the Aetheris oc-bridge (Town → OpenCode) live.

## The mental model: three gates
Client → **[Gate 1: CF Access edge]** → tunnel → **[Gate 2: MCP transport security]** → **[Gate 3: write-tool handler]** → execution.
Reads exercise Gates 1–2 only; writes add Gate 3. So "reads work, writes hang" localizes to Gate 3.

## Gate 1 — Cloudflare Access edge (non-browser clients)
**Symptom:** the MCP server shows `oauthStatus: valid` but `toolCount: 0`, no error. Browser login (email OTP) succeeds; the headless client never enumerates tools. Reconnecting does nothing.
**Cause:** `enable_binding_cookie` and/or `http_only_cookie_attribute` are ON. The `CF_Binding` cookie is a browser-only anti-theft mechanism — the edge rejects any request that lacks it. A headless OAuth-token client has no cookie jar, so its token POSTs are rejected at the edge *before the tunnel* — nothing reaches the origin.
**Cloudflare's own rule:** do NOT enable binding cookie or HttpOnly for non-browser tools (SSH/RDP/MCP).
**Fix (API):** GET the Access app, flip `enable_binding_cookie=false` and `http_only_cookie_attribute=false`, PUT the *full* object back — preserve `oauth_configuration`, DCR `allowed_uris`, and all policies (omitting fields clears them). Spread the GET result, drop read-only fields (`id`/`uid`/`aud`/timestamps), flip the two booleans, remap policies to their writable subset.
**Setup that is correct and should be preserved:** self-hosted app + Managed OAuth (`oauth_configuration.enabled`), DCR with the client's callback host allowlisted (Town: `https://www.town.com/*` + `town.com` + `app.town.com`; exact callback `https://www.town.com/api/mcp/oauth/callback`). JWT-only auth is fine — CF Access is the trust boundary; a separate write-path bearer is redundant.

## Gate 2 — MCP transport security / DNS-rebinding (the 421)
**Symptom:** once requests reach the bridge, the client gets `421 Misdirected Request`.
**Cause:** the MCP Python SDK / FastMCP Streamable-HTTP app enables DNS-rebinding protection by default and accepts only `Host: localhost / 127.0.0.1 / [::1]`. FastMCP auto-enables this whenever it binds `127.0.0.1` — exactly how a tunnel-fronted bridge binds. Behind a real hostname every request is 421, and the reason is *only in the server log*.
**Fix:** `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=["<host>", "<host>:*", "127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"], allowed_origins=["https://<host>", "https://<host>:*"])`. `allowed_hosts` entries are exact strings — list the bare host AND `:*`. Restart the service. If you then get `403 Invalid Origin header`, add the client's `Origin` to `allowed_origins`.

## Gate 3 — write-tool handler (reads work, writes hang)
**Symptom:** reads return instantly; write tools hang until the client's MCP timeout (Town = 60s), across retries and even a clean reconnect.
**Two causes, both real — check both:**
1. **Synchronous blocking** — the tool waits for the whole build/turn. Fix: make write tools **async** — return `{job_id, status:"started"}` immediately; the caller polls a tiny `job_status` and a bounded `job_result`. Keeps Town cost flat too (control plane, not data plane).
2. **Blocking approval/elicitation gate** — the handler calls `ctx.elicit` (or an approval prompt) *before* submitting the job, and a headless/background client never answers → hang. Fix: for a JWT-authenticated caller, **the JWT is the authorization** — never block on elicitation on this lane. Keep an optional `APPROVAL_MODE` env flag default OFF; write-safety lives in box-side guardrails (cwd allowlist, hard timeout+kill, output caps, append-only audit, concurrency=1, no-lockout).
**Critical test gap:** verify through an *actual* MCP client that advertises the same capabilities as the target (or replay its `initialize`) — NOT the on-box service user. A direct on-box call skips both the edge and the elicitation path, so it passes while the real client hangs.

## Diagnostic method — localize the layer before fixing
- A bare `curl <endpoint>` returning `401 invalid_token` with a `resource_metadata` pointer is the **designed** Managed-OAuth challenge, not a misconfig. Don't "fix" it.
- Read the bridge/origin log: **zero requests arriving** ⇒ Gate 1 (edge). A concrete HTTP error arriving (`421`) ⇒ Gate 2. Request arrives + handler stalls ⇒ Gate 3.
- Confirm from the real client's vantage (Town `list_mcp_servers` → `toolCount`; a read round-trip like `opencode_health`), not just on-box.
- Each fix opens the next gate — expect the symptom to *change* (silent 0 → 421 → hang → green). A changing symptom is progress, not regression.
- Re-verify CF routing when a `421`/`5xx` appears: DNS proxied CNAME → tunnel (healthy) → ingress `http://127.0.0.1:<port>`; no conflicting custom hostnames; SSL `full`.

## Reference: oc-bridge live state (2026-08-24)
Endpoint `https://oc.aimlds.org/mcp` (canonical; `oc.devinfo.dev` retired — `.dev` is corp-blocked). Bridge FastMCP on `127.0.0.1:8888` via the `oracle-aetheris` tunnel; `opencode` runs on-box. JWT-only (AUD `22cdf4c6…`). 8 tools: writes/jobs `oc_run_command` / `oc_send_prompt` / `oc_job_status` / `oc_job_result`; reads `opencode_*`. Full detail and locked decisions live in the "oc-bridge Slice 2 — Read-Write Plan" Town doc.
