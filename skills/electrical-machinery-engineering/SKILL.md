---
name: electrical-machinery-engineering
description: Motors and generators — application checks, specs, acceptance tests, and failure-analysis support for electrical machines.
version: 1
triggers: motors, generators, electrical machines, machine failure, acceptance tests
category: Electrical & energy
blurb: Motors and generators — application checks, specs, acceptance tests and failure analysis.
archetype: knowledge
example: Help me specify a replacement motor for a critical pump.
---

# Electrical Machinery Engineering

Rotating machines support: size it right, specify it clearly, test it by the book, and read its failures honestly. This structures the engineering; the SME makes the calls.

## When to use
- Motor/generator sizing, selection, or replacement.
- Specification/datasheet review (NEMA MG1 / IEC 60034 frames).
- Acceptance/commissioning tests; failure investigation support.

## Method
1. **Duty first**: load torque profile (constant/variable/impact), starts per hour, ambient, altitude, enclosure — duty drives selection, not habit.
2. **Sizing check**: torque and power at worst case, frame/service-factor margin, starting current vs supply capability, efficiency at actual load (not nameplate).
3. **Spec discipline**: type (induction/synchronous), insulation class, enclosure (TEFC/ODP/WPI), bearings, space heaters, RTDs, vibration limits, standards cited — reject vague specs.
4. **Test framework**: intake/acceptance checklist; insulation resistance (+PI/DAR trends), winding resistance (balance), surge comparison, no-load/load runs; criteria FROM standards and OEM, recorded with instruments + cal status (`electrical-test-records`).
5. **Failure analysis support**: organize evidence (photos, waveforms, teardown notes, operating history) into a timeline; typical modes — bearings, insulation aging/PD, rotor bars, supply/VFD interaction (`drives-and-vfd-engineering`).
6. **Trending**: per-asset baselines; compare like-for-like (same test, same conditions) — deltas mean more than absolute values.

## Quality gates
- [ ] Duty + worst-case torque documented against selected rating.
- [ ] Spec cites standards; test acceptance criteria defined before tests.
- [ ] Results recorded with units + calibration; anomalies flagged.
- [ ] Asset records updated; deviations logged with actions.

## Red lines
- Never re-energize after insulation or winding anomalies without engineering review.
- Verify nameplate/serial against documents — never assume.

## Related
`drives-and-vfd-engineering` · `condition-monitoring` · `electrical-test-records`.
