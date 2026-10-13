---
name: javascript-engineering
description: Modern JavaScript done right — ESM, no implicit globals, async discipline, XSS-safe DOM, bundle awareness.
version: 1
triggers: javascript, js, esm, async, xss-safe, node
category: Engineering & code
blurb: Modern JavaScript done right — modules, async discipline, XSS-safe DOM work and bundle awareness.
archetype: knowledge
example: Review this JavaScript for async and XSS traps.
---

# JavaScript Engineering

Prefer TypeScript for anything that grows (`typescript-engineering`). When plain JS is the right call (tiny scripts, no-build pages), keep it disciplined.

## When to use
- Small scripts, quick tools, no-build browser pages, legacy JS maintenance.
- Node utilities where a compile step isn't worth it.

## Method
1. **Modules**: ESM (`import`/`export`) everywhere; no implicit globals; `const` by default, `let` when reassigned, never `var`.
2. **Strictness**: use strict (implicit in modules); JSDoc types for anything reused without TS.
3. **Async discipline**: `async/await` with real error handling; every promise handled or explicitly `.catch`ed; timeouts via `AbortController`.
4. **DOM safety**: build nodes with `textContent`/`createElement`; never inject user input via `innerHTML`; sanitize when HTML is truly needed.
5. **Environment split**: no DOM APIs in Node code; feature-detect when shared.
6. **Bundle awareness**: know what ships — no huge deps for small jobs; code-split anything optional.
7. **Tests**: unit-test pure logic (vitest/node:test); manual smoke for UI; keep logic out of event handlers so it's testable.

## Quality gates
- [ ] No implicit globals; no `var`.
- [ ] All promises handled; network calls have timeouts.
- [ ] No XSS-prone injection (`innerHTML` with input).
- [ ] Logic extracted from handlers and tested.

## Red lines
- Never `eval` / `Function` on untrusted input.
- No secrets in client-side code — assume it's public.

## Related
`typescript-engineering` · `frontend-engineering` · `html-craft`.
