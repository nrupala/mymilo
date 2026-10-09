---
name: efficient-web-builder
category: Engineering & code
blurb: Builds websites as if bandwidth and compute are paid for — because they are. Fast, light pages that still look like a million dollars.
example: Make this landing page load fast on a cheap plan without losing polish.
---
# Efficient Web Builder — Nrupal's Standard

Build and render every site as if compute, bandwidth, energy, and storage are finite and paid — because for Nrupal they are (~$3/mo cloud, free-tier edges). Efficiency is a hard constraint, not a polish step. The same discipline applies on Cloudflare's edge and on Nrupal's own OCI box. Performance and energy move together: a faster site is almost always a cheaper, greener site.

A site failed to load in front of two customers because it re-rendered and made 21 KV calls on every request. That is the failure mode this skill exists to prevent. Name the cost of a design *before* building it.

## The one rule that matters most

**Do work once, not per request.** If a result is the same for every visitor until content changes, compute it at publish/build time, store the finished artifact, and serve it with a single read. Never recompute per request what you can precompute once.

- Render pages at publish/build time → store finished HTML → serve 1 read per request.
- Trigger the rebuild on the event that changes content (the publisher), not on a timer and not per visitor.
- Always keep a live-render fallback so a missing artifact degrades to slow-but-working, never blank.

This is the publish-time rendering pattern. It collapsed devinfo.dev from 21 calls/page to 1.

## Minimize calls (server, API, DB, KV)

- **Count the calls in any design and state the number** before building. "This path is N calls" is a required line in every plan.
- Precompute and cache anything stable. Prefer 1 read of a pre-built blob over N reads + assembly.
- **Never `await` in a loop** when calls are independent — batch with `Promise.all` so they run concurrently, or (better) avoid the N calls entirely by precomputing.
- For search/filter over a dataset: build one small index blob at publish time; load it in 1 call and filter in memory. Don't fan out to per-item reads.
- Coalesce duplicate work: one upstream fetch shared across consumers, not one per consumer.

## Caching, layered cheapest-first

1. **Edge/CDN cache** (cheapest) — static assets and unauthenticated responses. Use `Cache-Control: public, max-age=..., stale-while-revalidate=...` so a cached copy serves instantly while a fresh one is fetched async. `stale-while-revalidate` (RFC 5861) is the highest-leverage, most-underused lever — it eliminates the "first visitor pays" penalty.
2. **App cache** (mid) — only for authenticated/personalized data that can't live at the edge.
3. **DB/query cache** (most expensive) — materialized views / indexed queries only for genuinely dynamic data.
- Hashed static assets: `Cache-Control: max-age=31536000, immutable`.
- On upstream failure, serve the last good cached value marked stale rather than blocking the user.

## Minimize bytes, energy, and code (compression — net, not blind)

Smaller payloads cost less bandwidth, less device CPU, less energy. But compression must be a *net* win — don't spend more energy/time compressing than you save.

- **Server-side compression on all text** (HTML, CSS, JS, JSON, SVG): Brotli preferred (15–25% better than gzip), gzip fallback. ~60–80% reduction, zero code change. Do NOT re-compress already-compressed media (images, audio, video, fonts).
- **Minify JS/CSS at build time** (20–40%). Strip whitespace/comments/dead code from shipped artifacts. Keep readable source in the repo; ship the minified build.
- **JavaScript is the costliest byte** — it costs 2–5× more energy in parse/compile/execute than in transfer. Prefer zero or minimal client JS. devinfo.dev's "no client-side JS" stance is the gold standard; honor it wherever the site doesn't truly need interactivity.
- **Remove dead code.** 40–60% of typical JS bundles is unused. Ship only what runs.
- **Compression-level trade-off:** highest levels (e.g. Brotli 11) for static assets compressed once at build time; lower levels for anything compressed on-the-fly per request, where CPU time would otherwise delay delivery. Match the level to how often the artifact is compressed vs. served.
- **Payload budget:** keep interactive JS ≤ ~300–400KB gzipped; for content sites aim far lower. Images as AVIF/WebP, responsive sizes, lazy-loaded.
- Inline critical CSS; defer the rest. Avoid frameworks when a Worker + a renderer will do — Nrupal's sites favor "no framework, no bloat."

## Speed (render + delivery)

- **Edge-first.** Serve from the nearest POP. Edge SSR/static delivers TTFB in tens of ms; monolithic origin SSR (hundreds of ms) is obsolete for this use.
- Static shell first; stream/defer the slow parts rather than blocking the whole response on the slowest dependency.
- Target sub-millisecond server CPU for content pages. If CPU P99 is in the multi-ms range for a static site, the architecture is wrong — find the per-request work and move it to build time.

## Security (non-negotiable baseline)

Apply on every response, via shared middleware/headers:
- `Content-Security-Policy` (tightest that works), `Strict-Transport-Security` (HSTS), `X-Content-Type-Options: nosniff`, `X-Frame-Options` / frame-ancestors, `Referrer-Policy`.
- HTTPS only. No secrets in client code or repos — use platform secrets. Protect write/rebuild endpoints with a bearer token.
- Escape all user/content-derived output (guard against undefined fields so one bad record can't crash the page — devinfo.dev learned this the hard way).
- Least privilege on tokens and bindings.

## Platform notes

- **Cloudflare Workers/Pages:** KV for read-mostly artifacts; Cache API + `stale-while-revalidate`; Cron Triggers (free) only as a backstop, not the primary rebuild trigger; deploy reproducibly (prefer CI from the repo so the live Worker never drifts from source).
- **OCI / self-hosted (Nrupal's ARM box):** no Docker (Nrupal's standing rule) — direct Python (venv/pip), systemd, platform-native. Put a cache/static layer in front; don't make a single VM render per request. A single VM is a single point of failure — keep the edge in front of it where possible.
- Same principle everywhere: precompute, cache, compress, ship minimal, secure by default.

## Process (ties to phased-delivery)

1. In the PLAN phase, **state the call count and the per-request work** of the proposed design, and the cheaper alternative if one exists.
2. Name any free-tier or single-VM fragility explicitly so Nrupal can decide knowingly — don't hide the trade-off.
3. **Staging first.** Build → deploy to a non-production URL → verify speed/correctness (check call count and CPU in analytics) → promote to production only on explicit go. Never test on the live site.
4. After shipping, confirm the efficiency actually improved (calls down, CPU down, bytes down) — don't claim "optimized" without the numbers.

## Quick self-check before shipping any site

- How many calls per page load? Is it the minimum? (Precompute if it isn't.)
- Is anything recomputed per request that could be done once at publish/build?
- Are text assets compressed (Brotli/gzip) and minified? Is media in efficient formats?
- Is there any dead/unused code or JS being shipped that isn't needed?
- Are security headers present on every response?
- Is there a fast cache path AND a safe fallback?
- Did I deploy to staging and verify before touching production?
