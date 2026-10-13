---
name: pwa-offline-engineering
description: Build offline-first web apps — service workers, local storage, sync queues, installability, honest state UI.
version: 1
triggers: pwa, progressive web app, service worker, offline web, installable
category: Engineering & code
blurb: Build offline-first web apps — service workers, local storage, sync queues and honest state UI.
archetype: knowledge
example: Make this web app work offline as a PWA.
---

# PWA & Offline-First Engineering

The app must work when the network doesn't. Local data is primary, the network is a sync partner, and the UI always tells the truth about both.

## When to use
- Self-contained apps (vault-style), PWAs, offline-first features.
- Adding installability, sync, or local persistence to web apps.

## Method
1. **Offline-first architecture**: local store (IndexedDB for structured, OPFS for files) is the primary source for user data; the server is a sync target — or absent entirely.
2. **Service worker discipline**: pre-cache the app shell + versioned assets; never cache sensitive responses blindly; update flow explicit ("new version ready" UI, controlled skipWaiting).
3. **Storage engineering**: versioned schema migrations; quota awareness (handle storage-full gracefully); export/import so users truly own their data.
4. **Sync**: queue with retry/backoff; idempotent operations; explicit conflict rules (last-write-wins or domain-specific merge); **visible sync state** (pending / synced / failed) — no spinners-forever.
5. **Client-side encryption**: WebCrypto when zero-knowledge is claimed; keys never leave the device unencrypted; be honest about web-platform limits (secure storage constraints).
6. **Installability & UX**: manifest, icons, theming; keyboard-first usability; degraded-mode messaging when features need connectivity.
7. **Testing**: DevTools offline/throttle tests; storage-full simulation; upgrade-path tests (old data → new version); install/uninstall flows.

## Quality gates
- [ ] Core flows work fully offline; sync states visible everywhere.
- [ ] Export path exists and round-trips.
- [ ] Storage migrations tested; quota exhaustion handled.
- [ ] Update flow (new service worker) exercised.

## Red lines
- No silent data loss (quota/deletes must warn); no caching of secrets; no "offline-first" claims with network-required core flows.

## Related
`browser-extension-engineering` · `frontend-engineering` · `zero-knowledge-systems`.
