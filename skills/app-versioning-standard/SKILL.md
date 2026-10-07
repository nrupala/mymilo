# App Versioning Standard — Nrupal's Way of Working

Use this skill WHENEVER building, packaging, releasing, or reviewing ANY app for Nrupal — plain web app, PWA, Android APK, or iOS native. It defines the one, non-negotiable way every app carries a version, so releases stay consistent, updatable, and never lose their history.

## Principle
One version, one source of truth, stamped onto every surface. Never hand-edit a version per file; never ship an app whose internal version does not match the release.

## Source of truth
- `package.json` `"version"` (SemVer `X.Y.Z`) is canonical. (Non-JS repos: a top-level `VERSION` file.)
- A release == a git tag. Canonical `v<X.Y.Z>`; APK-only builds may also use `apk-v<X.Y.Z>`.
- The tag MUST equal `package.json` version. CI fails the build otherwise.

## Every surface derives from that one version
| Surface | Field | Value |
|---|---|---|
| Web | on-page footer / `<meta>` marker | `X.Y.Z` |
| PWA | manifest `version` | `X.Y.Z` |
| PWA | service-worker cache name | `<app>-v<X.Y.Z>` (bump invalidates old caches) |
| Android | `versionName` | `X.Y.Z` |
| Android | `versionCode` | `MAJOR*10000 + MINOR*100 + PATCH` (monotonic; Play/F-Droid safe) |
| iOS | `CFBundleShortVersionString` | `X.Y.Z` |
| iOS | `CFBundleVersion` | same integer as Android `versionCode` |

versionCode: `0.2.1 -> 201`, `0.3.0 -> 300`, `1.0.0 -> 10000`. MINOR and PATCH must each stay `< 100` (else switch repo-wide to `M*1000000 + m*1000 + p`).

## Two moving parts (reference impl: `nrupala/research-analyst`)
- **Author time — `scripts/bump-version.mjs <X.Y.Z>`**: writes the version into every committed web/PWA surface (package.json, footer, manifest, SW cache) and promotes the CHANGELOG `Unreleased` section.
- **Build time — `scripts/stamp-app-version.sh`**: in CI, derives the version from the tag and stamps the generated native projects (Android `build.gradle`, iOS `Info.plist`). Native folders are generated per build, so they MUST be stamped in CI or they reset to Capacitor defaults (`versionCode 1` / `versionName "1.0"`).

## Release history is durable
- Maintain `CHANGELOG.md` (Keep a Changelog).
- Build workflow sets `generate_release_notes: true` so each tag's GitHub Release auto-lists merged PRs.

## CI enforcement
- **Version guard**: fail the build if the tag != `package.json` version.
- **Stamp step**: run `scripts/stamp-app-version.sh` after `cap add`/`cap sync`, before the native build.
- Workflow files under `.github/workflows/` are pasted via the GitHub web editor when the token lacks `workflow` scope; keep a ready-to-paste copy in `deploy/github-actions/`.

## Adopting in a new repo
Copy the two scripts + `CHANGELOG.md` + `docs/VERSIONING.md`, point the bump script's selectors at the repo's real paths (footer marker, manifest, SW cache constant), add the guard + stamp steps to the build workflow, set `package.json` version, tag. Done.

Applies under phased-delivery: branch + PR, never direct-to-main, no Docker.
