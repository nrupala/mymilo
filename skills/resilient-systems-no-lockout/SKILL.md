---
name: resilient-systems-no-lockout
category: Security & privacy
blurb: Nrupal's resilience standard — never break, never lock the user out, never fail silently, never waste money or time unnoticed.
example: Review this login flow against the no-lockout standard.
---
# Resilient Systems & No Lockout — Nrupal's Standard

The goal is not just "fast and cheap" — it is **never break, never lock out, never throw an error we cannot handle, never silently waste money or time.** Resources are finite and paid (~$3/mo cloud, free-tier edges, a single OCI ARM box). A failure in front of customers, a quota that silently starts rejecting, or a token that expires mid-task is unacceptable. This skill is the reliability counterpart to `efficient-web-builder`: that one prevents waste, this one prevents failure and lockout.

Real incidents this skill exists to prevent (all from Nrupal's own systems):
- A site failed to load in front of two customers (per-request work timing out, logged as "success").
- `esc()` / `slugify()` crashed on undefined KV fields — one bad record could take the page down.
- Token-scope walls blocked deploys mid-session (D1, Web Analytics, cache purge all 10000-errored).
- OCI ARM capacity lockout in one region with no fallback.

## 1. No unhandled errors or exceptions

Assume every input, record, upstream, and binding can be malformed, missing, or down.

- **Wrap every request path** so a single failure returns a graceful response, never a 500 or blank page. A top-level try/catch that returns a usable fallback is the floor, not the ceiling.
- **Guard every field access** on data you didn't just construct. Default undefined/null to safe values (`esc(x ?? "")`, skip records missing required keys). One corrupt record must never crash the page.
- **Validate at the boundary.** Check shape on read from KV/DB/API before using it. Skip-and-log a bad item rather than throwing.
- **No silent swallowing either** — catch, degrade gracefully for the user, but log enough to diagnose. Errors handled invisibly that hide a growing problem are their own failure.
- Prefer total functions: given any input in range, return something valid. Crashes are a last resort, never a default.

## 2. Never break the live site/service

- **Staging-first, always.** Build → deploy to a non-production URL → verify → promote to production only on explicit go. Never test on the live site. (This is also in `phased-delivery` and `efficient-web-builder` — it is load-bearing; repeat it.)
- **Atomic promote + fast rollback.** Keep the previous known-good artifact/deploy so you can revert in one step. Know the rollback command *before* you promote.
- **Fallback path on every read.** If a precomputed artifact is missing, degrade to live-render (slow but working) rather than serving nothing.
- **Health check after deploy.** Confirm the live thing actually works (status, key pages, a real request) before calling it done. Don't claim "deployed" on a 200 from the API alone.

## 3. No lockout (first-class — Nrupal has been bitten by all three kinds)

**Credential / token lockout:**
- Before any privileged operation, confirm the token has the *exact* scopes needed. A read working does not prove write/admin scope. If a scope wall is hit, name the precise missing scope and stop — do not thrash.
- Track token/key expiry. Flag anything approaching expiry before it fails silently.
- Never hard-depend on a single credential with no recovery path. Keep a documented way back in (dashboard access, recovery contact, alternate auth). Audit 2FA / platform-access config so a security control can't lock the owner out.
- Never put secrets in client code or repos — platform secrets only. A leaked secret forces a rotation that can itself cause lockout.

**Vendor / platform lockout:**
- Treat "a vendor policy change can delete my workload overnight" as a real risk (Nrupal's own principle: infrastructure shouldn't need permission). Prefer portable artifacts and reproducible deploys (CI from repo) so you can rebuild elsewhere.
- Avoid designs that only work on one proprietary feature with no escape hatch, unless the lock-in is named and accepted.

**Rate-limit / quota / capacity lockout:**
- Know the free-tier caps of every platform in play (e.g. Workers requests/day, KV reads-writes/day, API rate limits) and design well under them. The efficiency skill's "minimize calls" rule is also a lockout-prevention rule — fewer calls = more quota headroom.
- Assume quota rejection is *silent and sudden* under load (the demo-killer). Build in headroom; monitor approach to caps; have a degradation plan when a limit is hit (serve cache, queue, back off) rather than failing the user.
- For capacity-constrained resources (e.g. OCI ARM in one region), have a fallback region/shape or a documented plan B before depending on it.

## 4. No silent waste or runaway cost

- **No unbounded fan-out.** Loops that call out per item must be bounded and batched; cap concurrency. An accidental N×M loop can burn quota or money fast.
- **Retries with backoff and a ceiling.** Never retry tight or forever. Exponential backoff, max attempts, then degrade.
- **Idempotency.** Re-running a job when nothing changed should be cheap or a no-op — don't rebuild/recompute/re-send on every trigger if inputs are unchanged.
- **Don't poll when you can trigger.** Event-driven beats timer-driven beats busy-wait.

## 5. Graceful degradation everywhere

- Upstream fails → serve last-good cached value, marked stale, rather than blocking the user. Stale-but-up beats fresh-but-down.
- Partial failure → render what you have, note what's missing, keep the page usable.
- Always have a "the dependency is down" branch. The user should rarely see a hard error.

## 6. Platform notes

- **Cloudflare:** mind KV/Worker free-tier caps; use Cache API + stale-while-revalidate as both a speed and a quota-shield; protect write/rebuild endpoints with a bearer token; deploy reproducibly from repo so the live Worker never drifts from source (drift is its own failure mode).
- **OCI / self-hosted (Nrupal's ARM box):** no Docker (standing rule) — venv/pip, systemd, platform-native. A single VM is a single point of failure: put the edge/cache in front, keep a fallback region/shape in mind, and ensure systemd restarts services on failure. Monitor disk/CPU/RAM against the box's real limits (4 OCPU / 24GB / 50GB).
- Same discipline everywhere: handle every error, degrade gracefully, stay under quota, keep a way back in.

## 7. Process (ties to phased-delivery + efficient-web-builder)

1. In PLAN, list the **failure modes** of the design: what breaks it, what could lock us out, where an unhandled exception could occur, what quota/cap it leans on. Name the mitigation for each.
2. Name free-tier and single-point-of-failure fragility explicitly so Nrupal decides knowingly — never hide a trade-off behind "it's free."
3. Staging-first; verify health; keep rollback ready.
4. After shipping, confirm not just that it works, but that it *fails safely* — test a missing artifact, a malformed record, an upstream timeout where feasible.

## Quick self-check before shipping anything

- If any single input/record/upstream is bad or down, does it degrade gracefully — or crash?
- Is every privileged call backed by a token with verified scope, and is there a way back in if it fails?
- What free-tier cap or quota does this lean on? Are we comfortably under it, with a plan when it's hit?
- Can a loop/retry run away and burn quota or money? Is it bounded with backoff?
- Is there a rollback path, and do I know it before promoting?
- Did I deploy to staging, verify health, and confirm the fallback works — before touching production?
