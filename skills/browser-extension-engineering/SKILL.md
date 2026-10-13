---
name: browser-extension-engineering
description: Build browser extensions carefully — MV3 architecture, least-privilege permissions, messaging, store review.
version: 1
triggers: browser extension, chrome extension, mv3, extension permissions
category: Engineering & code
blurb: Build browser extensions carefully — MV3 architecture, least-privilege permissions and store review.
archetype: knowledge
example: Design a browser extension that will pass store review.
---

# Browser Extension Engineering

Extensions run inside the user's browser with real privileges. Request the minimum, behave predictably, and treat store review as a quality gate — not an obstacle.

## When to use
- Building/updating extensions (readers, capture tools, utilities) for Chrome/Edge/Firefox.
- Auditing permissions or fixing store rejections.

## Method
1. **MV3 reality**: service-worker background (no persistent page), alarms instead of timers, declarative APIs where possible; no remote code execution — bundle everything.
2. **Least privilege**: request only needed permissions; narrow host patterns; optional permissions for power features; review the permission list like a security audit — reviewers do.
3. **Architecture**: content scripts isolated from page context; well-defined message passing (validate messages on both ends); storage scoped (`storage.sync` vs `local`), no secrets in extension storage.
4. **UX honesty**: popup/options pages; states for logged-out/unavailable; no drive-by DOM changes without user intent; keyboard shortcuts.
5. **Privacy**: process page data locally by default; explicit consent + clear disclosure for any telemetry; **never exfiltrate browsing data**.
6. **Distribution**: store listings (screenshots, privacy form accurate), staged rollout, version discipline; Firefox MV3 differences (`browser.*` shim).
7. **Security**: CSP discipline; sanitize any injected UI; auto-update via store only.

## Quality gates
- [ ] Each permission justified in writing; host patterns minimal.
- [ ] Messaging validated; no remote code anywhere.
- [ ] Privacy disclosure matches actual behavior (tested).
- [ ] Works across target browsers (or differences documented).

## Red lines
- No overbroad permissions; no hidden data collection; no `eval` / remote scripts; nothing sneaky — the store and users will find it.

## Related
`pwa-offline-engineering` · `frontend-engineering` · `privacy-compliance`.
