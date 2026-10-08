# MyMilo Android-Native Integration — Design

**Status:** Design for v0.31.0 server-side prep
**North star:** Android-native, offline-first. Suitable work runs locally on the
phone; heavier work goes through cloud MyMilo on Aetheris.

## Architecture

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│   Android phone (native)    │         │   Aetheris (cloud MyMilo)   │
│                             │  HTTPS  │                             │
│  • Local model (llama.cpp)  │ ◄─────► │  • Full MyMilo v0.31+       │
│  • Local skills (cached)    │  sync   │  • 82 skills (source)       │
│  • Local SQLite (sessions,  │         │  • Cloud models (OpenRouter)│
│    messages, facts)         │         │  • Wright escalation        │
│  • Offline queue            │         │  • Web search, integrations │
└─────────────────────────────┘         └─────────────────────────────┘
```

### What runs where

| Capability | Phone (offline) | Cloud (online) |
|---|---|---|
| Simple chat | ✅ local model | ✅ |
| Skill matching | ✅ cached triggers | ✅ source of truth |
| Sessions/history | ✅ local SQLite | ✅ synced backup |
| Semantic facts | ✅ local copy | ✅ synced |
| Complex reasoning | ❌ | ✅ cloud models |
| Web search | ❌ | ✅ Exa |
| Code tasks | ❌ | ✅ OpenCode bridge |
| Escalation to Wright | ❌ | ✅ |

### Routing rule on the phone

The phone's local router mirrors MyMilo's complexity routing:
- Simple/short query + offline → local model
- Complex query or needs tools → cloud MyMilo (when online)
- Offline + complex → queue for later, tell the user it's queued

## Server-side prep (v0.31.0)

### 1. Token auth for native clients

Cloudflare Access is browser-based; a native app needs token auth.

- `POST /v1/devices/register` — register a device (name, platform),
  returns a device token (stored hashed server-side).
- Auth: `Authorization: Bearer <device-token>` accepted on all `/v1/*`
  endpoints as an alternative to the CF Access email header.
- The token maps to the user's email; all data stays user-scoped.
- Tokens are revocable: `DELETE /v1/devices/{id}`.

### 2. Sync endpoints (offline-first)

- `GET /v1/sync/state` — server sync watermark: latest session/message/fact
  timestamps for the user.
- `GET /v1/sync/sessions?since=<ts>` — sessions changed since `<ts>`,
  with their messages (delta).
- `POST /v1/sync/push` — phone pushes locally-created sessions/messages/facts;
  server merges (last-write-wins per record, server keeps tombstones for deletes).
- Conflict rule: server is source of truth for skills; phone is source of
  truth for offline-created messages until pushed; after push, server wins.

### 3. Streaming chat (SSE)

- `POST /v1/chat/completions` with `"stream": true` returns
  `text/event-stream`, yielding tokens as the upstream produces them.
- Non-streaming path unchanged (fallback for older clients).
- The native client renders tokens progressively — perceived latency drops
  from "full round trip" to "first token."

### 4. Client config endpoint

- `GET /v1/client/config` — returns the sync intervals, model routing
  thresholds, skill bundle version, and feature flags the native client
  should use. Lets us tune phone behavior without an app release.

## Android client (future, not in v0.31.0)

- Kotlin + Jetpack Compose, Room (SQLite), WorkManager (background sync).
- Local inference: llama.cpp Android build with a small GGUF model
  (Qwen 2.5 3B class) for offline chat.
- Skills bundled as assets, updated via sync.
- Auth: device token in Android Keystore.

## Phasing

1. **v0.31.0 (this prep):** device tokens, sync endpoints, streaming, client config.
2. **Next:** minimal Android client — chat + sync + offline queue.
3. **Later:** on-device model, local skill execution, push notifications
   for escalation results.

## Honest limits

- iPhone: assistant capabilities on iOS remain constrained (no default
  assistant replacement, stricter background limits). Android first.
- On-device models are small — quality gap vs cloud is real. Routing must
  be honest about which brain answered.
- Sync conflicts are inevitable; the merge rules above are v1-simple
  (last-write-wins) and will need refinement with real usage.
