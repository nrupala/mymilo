---
name: simulation-engineering
description: Build simulations and harnesses that teach — models, seeds, validation against reality, scenario sweeps.
version: 1
triggers: simulation, simulate, harness, scenario sweep, model validation
category: Engineering & code
blurb: Build simulations and harnesses that teach — models, seeds, validation against reality, scenario sweeps.
archetype: knowledge
example: Build a simulation to test this system against reality.
---

# Simulation Engineering

A simulation is an argument about reality with knobs on it. State the assumptions, seed the randomness, validate against known cases — then let people learn from it.

## When to use
- Training/teaching simulators (protection, faults, controls).
- Backtest and scenario harnesses (finance, capacity, load).
- System models (architecture demos, capacity planning).

## Method
1. **Purpose → fidelity**: teaching vs predicting vs testing sets the bar; document what's modeled and what's abstracted — limits stated up front.
2. **Core discipline**: deterministic core where possible; **units explicit (SI everywhere)**; domain equations referenced (curves, constants, standards); no magic numbers.
3. **Randomness handled**: seeded and logged; stochastic runs reported as distributions (n runs, bands) not single outcomes; reproducible from the seed log.
4. **Scenario library**: parameter sweeps, boundary cases, evolving-fault libraries; **golden scenarios with expected outcomes** as regression tests.
5. **Validation**: reproduce textbook/field/reference cases; report errors honestly; version the model (no silent changes — new version, new validation).
6. **Interaction**: sane defaults, step/pause/rewind controls, overlays that explain the physics (`data-visualization`); exportable run logs.
7. **Performance**: chunk heavy compute behind workers; interactive frame budgets for live UIs.

## Quality gates
- [ ] Assumptions + limits documented; units consistent.
- [ ] Seeded reproducibility; golden scenarios pass as tests.
- [ ] Validation cases cited; model versioned.
- [ ] Run logs exportable.

## Red lines
- Never present sim output as field truth; no hidden model edits; safety-critical training tools carry warning labels.

## Related
`data-visualization` · `backtesting-validation` · `relay_sim`-class domain work → `power-distribution-equipment`.
