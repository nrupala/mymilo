---
name: frontend-engineering
description: Implement frontend with production standards — components, state, data fetching, responsive layouts, accessibility, performance.
version: 1
triggers: frontend, ui code, components, state management, responsive, web performance
category: Engineering & code
blurb: Implement frontends to production standards — components, state, data fetching, accessibility, performance.
archetype: knowledge
example: Build this screen with full state coverage, not just the happy path.
---

# Frontend Engineering

Build the human surface: components, states, responsiveness, and speed. Follow the project's stack and styles; no new framework without an ADR.

## When to use
- Any UI implementation task (pages, components, interactions).
- Fixes for layout, state, performance, or accessibility issues.

## Method
1. **Structure**: semantic HTML first; small components with single responsibilities; data down, events up; no god components.
2. **States always**: implement loading, empty, error, and success for every data view; disable buttons while submitting; no dead controls.
3. **Data layer**: fetch through one small client per app; retries with backoff for transient errors; never block the whole screen for one widget.
4. **Responsive**: fluid grids, wrap-safe text, stable dimensions; test 360px → desktop; no overflow, no overlap, nothing hidden behind fixed bars.
5. **Accessibility**: labels on all fields, logical focus order, `aria-live` for async results, fully keyboard operable.
6. **Performance**: budget first (bundle size, first paint); lazy-load below the fold; avoid layout shift; cache static assets.
7. **Errors are UI**: human-readable messages in the interface; details go to logs/telemetry — not into the user's face.

## Artifacts
- Components + styles (token usage), implemented state matrix, smoke/tests for key flows.

## Quality gates
- [ ] Every data view has loading / empty / error / success implemented.
- [ ] Keyboard-only pass of the primary journey.
- [ ] Mobile + desktop widths verified (no overflow/overlap).
- [ ] Performance budget checked (bundle + first paint on slow throttle).

## Red lines
- No console spam; no "nothing happened" failures.
- No secrets or keys in frontend code — ever.

## Related
`ux-ui-design` (specs to implement) · `multi-surface-webapp` (app blueprint) · `testing-strategy` (verification).
