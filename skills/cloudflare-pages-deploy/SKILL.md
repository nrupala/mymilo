---
name: cloudflare-pages-deploy
category: Engineering & code
blurb: Deploys a static site or web app to Cloudflare Pages with a custom domain, the minimum-steps, verify-everything way.
example: Deploy this site to Cloudflare Pages on my domain.
---
# cloudflare-pages-deploy

Deploy a static site or a vanilla-JS/TS PWA to Cloudflare Pages with a custom domain, using Nrupal's connected Cloudflare tooling — the minimum-calls, verify-everything way. Use this WHENEVER shipping a site/app to Cloudflare Pages (git-integrated), attaching a `*.devinfo.dev` (or other owned-zone) custom domain, or debugging a Pages deploy/domain that is stuck.

## Tooling & auth (get this right first)
- Two Cloudflare MCP servers are connected:
  - **Personal header-token** (`mcp_cloudflare_api_execute`): has Pages + zone-list scope. Does NOT have DNS-write or full Zone scope — DNS record reads/writes throw a `10000` auth error. Also fails on D1 and Workers AI REST.
  - **Team OAuth** (`mcp_v97ftr667zd9dbvcmaf96cvksh8aypcq_cloudflare_execute`): broader access — use it for DNS record create/read and Zero-Trust/Access.
- Account id: `2edd59d09fd816187b47afbb9ea43af1`. devinfo.dev zone id: `59962b2817f7f1d2f700973776e1affc`.
- Rule of thumb: **Pages ops → personal token is fine; DNS / Access ops → team token.**

## Git-integrated Pages project (auto-deploy)
1. Create the project bound to the GitHub repo: production branch `main`, build command (e.g. `npm ci && npm run build`), **root dir** (e.g. `app` when the app lives under `app/`), **output dir** (e.g. `dist`). The repo id auto-resolves from `owner/name`.
   - Creating the project does NOT auto-trigger the first build.
2. Deploy by pushing to `main` (production branch) — the push auto-builds and deploys. Or trigger a production deployment via the API.
3. Every later push to `main` rebuilds + deploys. No manual step.

## Custom domain (subdomain of a zone you control)
1. Add the domain to the Pages project (`.../pages/projects/<name>/domains`). Adding it again returns `8000018` "already added" — harmless.
2. Create a **proxied CNAME** in the zone: `<sub>` → `<project>.pages.dev` (use the **team token** — the personal token 10000s on DNS).
3. Domain status progression: `verification_data.status` flips to `active` once the CNAME is detected; `validation_data.status` (HTTP/SSL) finishes a little later. The edge often serves the site over valid HTTPS BEFORE the API's `validation_data` flips — so **a successful HTTPS fetch is the real signal**, not the API status.

## Verification discipline (do not trust "success")
- Poll `.../pages/projects/<name>/deployments` and confirm the newest deployment's stages reach `build:success` then `deploy:success` for YOUR commit hash. A failed build keeps the previous version live (safe) — a broken commit never breaks the live site, but you MUST confirm the new one actually deployed.
- Verify the LIVE site by fetching the real URL. `web_fetch` returns EXTRACTED content and misses static chrome (e.g. a footer below an SPA) — for exact-string checks, `curl` the raw HTML in the sandbox (`allow_internet: true`) and grep. Cache-bust with `?cb=$(date +%s)`.
- To confirm TypeScript actually compiled and shipped, grep the built JS bundle (e.g. `/app.js`) for string literals you added — literals survive minification, so their presence proves the source compiled into the bundle.

## Gotchas learned
- **Empty repo**: `github_commit_files` needs an existing branch. Seed one file first (e.g. `github_create_or_update_file` a README on `main`) to initialize the branch, THEN commit the full tree.
- **town_grep is unreliable** in this environment: it can silently report `totalFilesSearched: 0` or skip files. For correctness-critical checks (brand-string sweeps, verifying an edit landed), read files directly with `town_read` — never conclude "absent" from a grep miss.
- `github_commit_files` reads file bytes straight from `vfs://` / `content://` / `sandbox://` via `source_uri` — you don't paste file contents; you map `source_uri` → `github_path`.
- Production sites (devinfo.dev Worker, etc.) follow **chat → plan → build → deploy(preview) → test → merge; never direct-to-prod** — commit to a feature branch and open a PR; Nrupal merges. Pages-project apps that are pure teasers can auto-deploy on `main`, but still verify live after.

## PWA rebrand checklist (renaming a whole app cleanly)
When rebranding a vanilla-TS PWA (e.g. KalaVault → CipherNotes), change the brand string in ALL of:
- `manifest.webmanifest` (name, short_name, description)
- `index.html` (title, description meta, noscript)
- `sw.js` (comment + cache name, e.g. `ciphernotes-shell-v1`)
- `package.json` + `package-lock.json` (name, description)
- UI source (every visible string + the `brand()` logo text)
- **IndexedDB database name (`DB_NAME`)** — easy to miss
- Type/format literals: the vault-header `app` field, the export `format` string, and any header/error literals ("This is not a &lt;Brand&gt; encrypted backup.")
- `README.md`
Then verify by READING every file (grep is unreliable), and confirm on the deployed bundle + raw HTML.

## Never
- Never enable `*.workers.dev` / Preview URLs to view a preview (Nrupal keeps them off) — review via `wrangler dev` / dashboard Preview, or the deployments API + the live custom domain.
- Never put a KV `list()` or any O(all-records) scan on a per-request hot path (cache an index blob; read with a single `get` — see the devinfo.dev `papers:index` pattern).

---
*Authored by Milo 2026-08-30, distilled from the CipherNotes build + deploy (the KalaVault ZK-notes MVP rebranded and shipped as a free teaser at notes.devinfo.dev). Reusable for any Cloudflare Pages deploy.*
