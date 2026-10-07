# Cloud & Sovereign Infrastructure

Own the compute and the data; minimize lock-in; expose nothing you don't have to. The platform is **Aetheris** — Nrupal's sovereign, self-hosted cloud. Pairs with `security-zero-knowledge`, `systems-builder`, `phased-delivery`, and `aetheris-mgmt-api`.

## The Aetheris topology (know it cold)
- A single **OCI ARM instance "oracle-aetheris"** — 4x ARM OCPU, 24GB RAM, 50GB HDD, public IP `147.224.174.50` — runs all self-hosted services.
- Region: **us-chicago-1** (`airwaterclouds` tenancy, email `nru.palakolkar@gmail.com`). A separate older account (`nak01`, Montreal) had its free trial expire April 2026 and is not in use.
- Exposed via **Cloudflare Tunnel** `c12afde0-a01d-485d-aed6-3dddb3282069` (name: `oracle-aetheris`, status: healthy, 4 connections via ORD colos).
- **The tunnel + Cloudflare Access is the trust boundary** — services bind locally and are never directly internet-exposed.

## Active tunnel ingress (as of July 2026)
| Hostname | Service | Purpose |
|---|---|---|
| oracle.nrupalakolkar.com | http://localhost:9080 | Nginx reverse proxy |
| ai.nrupalakolkar.com | http://localhost:9080 | AI endpoints (via Nginx) |
| rag.nrupalakolkar.com | http://localhost:9080 | RAG pipeline (via Nginx) |
| dev.nrupalakolkar.com | http://localhost:9080 | Dev dashboard (via Nginx) |
| agents.nrupalakolkar.com | http://localhost:9080 | Agent orchestrator (via Nginx) |
| nrupalakolkar.com | https://localhost:9443 | Root domain (Nginx SSL, noTLSVerify) |
| ra-origin.nrupalakolkar.com | http://localhost:8700 | Research Analyst Python backend |
| bee.devinfo.dev | http://localhost:8800 | Budget & Economy Engine (FastAPI) |
| bee-staging.devinfo.dev | http://localhost:8800 | BEE staging |
| mgmt.nrupalakolkar.com | http://localhost:9090 | Management API (token-gated) |

**Removed (July 2026):** `ci.nrupalakolkar.com` and `git.nrupalakolkar.com` — were never backed by Nginx server blocks, caused 301 redirect loops. No CI/CD or Gitea services run on the box; GitHub Actions handles CI.

## Management API (mgmt.nrupalakolkar.com)
- Lightweight Python HTTP server on `127.0.0.1:9090`, exposed through the tunnel.
- Token-gated via `X-Mgmt-Token` header. Token stored in Milo's memory.
- Endpoints: `/health` (no auth), `/status`, `/docker-ps`, `/nginx-config`, `/logs/aetheris`, `/logs/ollama`, `POST /restart/{service}`, `POST /docker-compose-up`, `POST /ollama-models`.
- Systemd unit: `aetheris-mgmt.service`. Env file: `/etc/aetheris-mgmt.env`.
- See `aetheris-mgmt-api` skill for full operational reference.

## Cloudflare stack
- **Tunnel (cloudflared):** local services -> edge, no open inbound ports.
- **Workers / Pages:** edge compute and static hosting (devinfo.dev Worker, research-analyst Pages, etc.).
- **Access:** zero-trust auth in front of private subdomains (llm, migration, notes, kalabodha, ciphernotes). Audited by the Access Leak Audit routine (twice daily).
- **DNS / TLS, KV, R2** as needed.
- **Milo has full Cloudflare API access via OAuth** — can manage DNS records, tunnel ingress, Workers, Pages, KV. The zone for nrupalakolkar.com is `3b4bc890ba1a88784ca84af2b6947204`.
- Caveat: deploying a Worker **via API** (not wrangler) can leave the GitHub repo out of sync — reconcile afterward.

## OCI (Oracle Cloud) — billing awareness
- The `airwaterclouds` account in Chicago is **Pay-As-You-Go**, not Always Free. June 2026 invoice: 56.26 SGD (~$55 CAD) for CLOUDCM (compute). Verify the compute shape in OCI Console — if it's not `VM.Standard.A1.Flex`, it's not eligible for Always Free.
- The older `nak01` Montreal account free trial expired April 2026. ARM capacity was never available there.
- Alternative providers evaluated: Hetzner CAX31 (~$13 CAD/mo for 8 vCPU ARM, 16GB) is the strongest migration target if OCI costs remain.

## Current service state (July 2026)
- **cloudflared:** active (systemd)
- **bee:** active (systemd, FastAPI on :8800)
- **ollama:** active (systemd) but `ai_connected: false` in Aetheris core — DNS resolution failure inside Docker network (`http://ollama:11434`)
- **aetheris-core:** unhealthy (Docker container up but failing health checks)
- **nginx:** healthy (Docker container)
- **Disk:** 18G/48G (37%), **RAM:** 5.7G/23G

## Deploy discipline (no Docker)
- **No Docker for new services.** Use venv/pip + systemd units. Existing Docker services (aetheris-core, nginx, ollama) are legacy — migration to native is a phased project (Track 3).
- **Staging first; never direct-to-production** unless explicitly approved as a *named bridge with an end date* (`phased-delivery`).
- BEE is the model: pure-Python, systemd unit, tunnel ingress, no Docker.

## Secrets & deploy-time credentials
- **One canonical secret, injected at deploy time.** GitHub repo secrets for CI; systemd `EnvironmentFile` (chmod 600) for runtime.
- **GitHub Actions secrets are write-only / not runtime-readable.**
- **Never in the edge or the client.** Backend secrets live on the origin only.
- **Nrupal adds secrets himself.** SSH keys, deploy creds, and API keys go into GitHub repo secrets by Nrupal directly.

## devinfo.dev estate
- Public subdomains: root (devinfo.dev), ra, bee, aimlds.org (mirror).
- Private (Cloudflare Access-gated): llm, migration, notes.
- Backend health: `bee.devinfo.dev/api/health`, `research-analyst.fly.dev/api/health`, `research-analyst-60qp.onrender.com/api/health`.
- Monitored by **Site Monitor** (6-hourly, public + backends) and **Access Leak Audit** (twice daily, private posture).

## Monitoring & routines
- **Site Monitor & Health Check:** 6-hourly, checks public frontends + Aetheris auth endpoints + backend APIs. Does NOT check Access-gated domains (those are covered by Access Leak Audit).
- **Access Leak Audit:** twice daily, verifies private domains are gated and public domains are reachable. Emails only on issues.

## Anti-patterns to refuse
- Docker for new services; direct-to-prod without a named bridge; exposing services outside the tunnel; deploying via API then forgetting to sync the repo; treating free-tier fragility as free; monitoring bolted on as an afterthought instead of run as a routine; creating DNS/tunnel entries without corresponding Nginx server blocks (the ci/git lesson).
