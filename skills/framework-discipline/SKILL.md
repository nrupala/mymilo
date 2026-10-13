---
name: framework-discipline
description: Adopt, structure, and upgrade frameworks deliberately — ADR for new ones, keep core framework-free, plan exits.
version: 1
triggers: frameworks, adopt a framework, upgrade framework, framework-free core
category: Engineering & code
blurb: Adopt, structure and upgrade frameworks deliberately — an ADR for new ones and an exit plan.
archetype: knowledge
example: Should we adopt this framework? Give me the disciplined answer.
---

# Framework Discipline

Frameworks accelerate and entangle in equal measure. Choose them deliberately, keep the core free of them, and always know the exit.

## When to use
- Choosing a framework for a new project or component.
- Introducing one into an existing codebase (requires an ADR).
- Planning framework upgrades or dealing with deprecations.

## Method
1. **Choose by fit**: team familiarity, maintenance health, ecosystem, performance, and **exit cost**. Boring and stable beats fashionable.
2. **Conform to the house stack**: one framework per layer; don't mix directions mid-project (change = ADR + migration plan).
3. **Framework-free core**: business logic lives in plain functions/modules; the framework sits at the edges (ports & adapters).
4. **Pin and plan upgrades**: exact versions; read changelogs; batch updates; use codemods; run the full suite; never jump majors blind.
5. **Avoid magic**: prefer explicit configuration; understand what the framework does at runtime (lifecycle, DI, caching).
6. **Plugin discipline**: plugins are dependencies — review, pin, and remove unused ones (`dependency-governance`).
7. **Deprecations**: track warnings; migrate on schedule; no zombie code paths waiting to break.

## Quality gates
- [ ] New framework = logged ADR (alternatives + exit cost).
- [ ] Core logic imports no framework code.
- [ ] Versions pinned; major upgrades have a written plan + full-suite run.
- [ ] No deprecated APIs on the hot path.

## Red lines
- No framework-hopping mid-project without an approved migration plan.
- No unpinned "latest" from CDNs or tags in production.

## Related
`architecture-decisions` · `dependency-governance` · `typescript-engineering`.
