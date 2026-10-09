# MyMilo Backlog — Nrupal's Feature Queue

**Rule (his words):** Features get queued and done properly, one by one.
No rushing unless he says "rush." No shaky deliveries.

*Refreshed 2026-10-09 to match reality — the shipped list is
summarized; the full history lives in the CHANGELOG and the
[verification records](QUALITY.md).*

## 🏃 In Progress
- **App build 16 (v0.8.1) — device walk (owner).** In-app update
  14→16, Room v3 migration on a real phone, Skills catalogue,
  Guide, About. Gates the next build (verify-before-next-build).

## 📋 Queued (prioritized)
1. **Sources & Vault** (app): write-only token vault (rotate /
   replace / delete per source, never viewable), Aetheris as
   Source #1, OpenRouter / OpenCode Zen / custom endpoints,
   brain picker, origin labels. Spec: `SPEC-SOURCES-VAULT.md`
   in the mymilo-native repo. See
   [HUMAN-MACHINE-AGENT.md](HUMAN-MACHINE-AGENT.md).
2. **Local model packs**: hardware probe (CPU/GPU/RAM) →
   recommended Gemma / Qwen / Llama pack → llama.cpp engine.
   Offline answers with the app staying ~2 MB.
3. **Sign-in pairing**: app Connect via the normal web sign-in;
   the server hands the device token over a one-time pairing
   handoff — no copy-paste. (Server half designed with v0.39.0.)
4. **Connectors exposed**: `GET /v1/connectors` + app screen +
   web view — live built-ins, connectable accounts under the
   disconnect-by-default posture, on-device capabilities.
   See [CONNECTORS.md](CONNECTORS.md).
5. **Agent loop**: multi-step tasks with visible progress,
   oc-bridge + MCP behind Aetheris.
6. **Device actions + permissions screen** (roadmap build 11):
   alarms/timers, call/text by name, calendar read/create,
   location answers; every permission listed with its why and
   grant state. Sends: the assistant prepares, the owner taps
   (standing rule).
7. **Notifications intelligence** (roadmap build 13): "what
   did I miss" — read + summarize. Scope (read-only vs
   reply-capable) is the owner's call.
8. **Presence** (roadmap build 14 remainder): home-screen
   widget + Quick Settings tile.
9. **v1.0 hardening + Play**: a week of real use as the test
   suite; Play closed track decision is the owner's.

## 🔭 Known warts (tracked, not forgotten)
- Health: the nested embeddings probe can read `ok:false`
  while the route is up (see [OPERATIONS.md](OPERATIONS.md)).
- Background-job chat replies carry no `sources` list yet.
- Assistant invocation on the owner's phone historically
  produced no screen/voice; panel hardened since — the
  "Last assistant activity" readout will name what remains.
- CI screenshot job for the Android app is still owed.

## ✅ Shipped (modern era; earlier history in CHANGELOG)
- v0.35–v0.38.1: Token-Efficiency Engine, slices 1–4.
- v0.39.0: device lifecycle — rotate/remove + simpler /devices.
- v0.40.0: unified sources on every chat response.
- v0.41.0: skills runnable on purpose (named-skill requests).
- v0.42.0: skills catalogue content + `/guide` page +
  server-set support link.
- App (mymilo-native): builds 11–16 — release signing, sources
  display, thread management, voice panel hardening, the
  updater fix, Skills catalogue + Guide + About screens.
- Docs program: README hub + user guide, generated skills
  catalogue, operations, code guide, connectors,
  human/machine/agent, quality — all cross-referenced.
