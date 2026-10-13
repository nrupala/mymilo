---
name: typescript-engineering
description: Write production TypeScript — strict mode, no any, typed boundaries with schemas, small honest modules.
version: 1
triggers: typescript, ts, strict mode, typed, write typescript
category: Engineering & code
blurb: Write production TypeScript — strict mode, no any, typed boundaries with schemas, small honest modules.
archetype: knowledge
example: Convert this JavaScript to strict, production TypeScript.
---

# TypeScript Engineering

Types are executable documentation: make illegal states unrepresentable, validate at the edges, and trust the compiler inside.

## When to use
- Any TS codebase (frontend, Node services, tooling).
- Migrating JS to TS or tightening an existing TS project.

## Method
1. **Strict, always**: `"strict": true` plus `noUncheckedIndexedAccess`; `tsc --noEmit` in the loop.
2. **No `any`**: use `unknown` and narrow; avoid `as` casts (justify any that remain); no non-null `!` chains.
3. **Typed boundaries**: validate external input (API, storage, env) with a schema (zod/valibot) — parse, don't trust.
4. **Model states as unions**: discriminated unions for status machines; exhaustive `switch` with a `never` check.
5. **Modules**: small files, deep imports over barrel files that hide cycles; explicit public surfaces.
6. **Async**: all promises awaited or handled (lint rule); no floating promises; `AbortController` for cancellable work.
7. **Tests**: unit tests for logic (vitest); integration at the module edges; types tested by compilation.
8. **Build**: tsc for types, esbuild/vite for bundling; source maps on; deps pinned.

## Quality gates
- [ ] `tsc --noEmit` clean under strict.
- [ ] No `any` in `src/`; no unexplained casts.
- [ ] Boundary schemas exist and are tested.
- [ ] No floating promises; lint clean.

## Red lines
- No `ts-ignore`/`ts-expect-error` without a tracked reason.
- No runtime shapes assumed that weren't validated.

## Related
`javascript-engineering` · `frontend-engineering` · `backend-engineering`.
