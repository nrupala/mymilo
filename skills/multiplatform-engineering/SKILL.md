# Multiplatform Engineering

One portable **core**, many thin surfaces. Share the logic, crypto, and data model — not the UI. Get the core right once and each platform becomes an adapter.

## Architecture
- A portable core (Rust/Python) holds logic, crypto, and the data model. Platform layers are thin adapters that translate to native conventions.
- Define one internal API the core exposes; every surface consumes the same contract.

## Surfaces
- **Web / PWA:** installable, offline-capable (service worker), responsive. His no-framework `pwa-creator` pattern.
- **Mobile:** PWA-first where it suffices; native/APK when truly needed (his `apk-creator` — Gradle direct, no heavyweight toolchain).
- **Desktop / CLI:** single static binary where possible (Rust/Go — `zerok-cli`, `zerok-rs`). Good `--help`, correct exit codes, pipe-friendly output.
- **API:** one typed contract any surface consumes.

## Local-first / offline (fits his ethos)
Source of truth on the device; sync is an enhancement, not a requirement. Local-first pairs naturally with zero-knowledge and sovereignty — the user's data and keys stay on their hardware.

## Portability discipline
- Isolate platform-specific code behind interfaces; minimize per-platform forks.
- One design system across surfaces, but **respect each platform's conventions** — don't ship a lowest-common-denominator UX.

## Packaging & distribution
- Reproducible, signed builds; no Docker. Decide store vs sideload vs direct per surface.

## Testing
- Test the shared core thoroughly once; smoke-test each surface for integration and platform quirks.

## Reference example
**LocalForge** — one multi-agent engine, three faces (VS Code extension, CLI, Web UI). Core logic shared; each face is a thin adapter.

## Anti-patterns to refuse
- Rewriting core logic per platform; lowest-common-denominator UX; ignoring platform conventions; online-only when offline genuinely matters.