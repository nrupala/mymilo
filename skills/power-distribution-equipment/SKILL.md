---
name: power-distribution-equipment
description: MCC, switchgear, transformers — ratings, protection basics, testing, condition checks, safe work discipline.
version: 1
triggers: mcc, switchgear, transformers, distribution equipment, protection basics
category: Electrical & energy
blurb: MCCs, switchgear and transformers — ratings, protection basics, testing and condition checks.
archetype: knowledge
example: What condition checks should we run on this switchgear lineup?
---

# Power Distribution Equipment (MCC · Switchgear · Transformers)

The backbone layer: ratings must match reality, protection must work, tests must be traceable, and work on it happens only inside the safety system (`electrical-safety`).

## When to use
- MCC/switchgear modifications, additions, or replacements.
- Transformer loading, paralleling, or condition questions.
- Reviewing test plans, maintenance scopes, or fault investigations.

## Method
1. **Ratings against reality**: voltage class, continuous current, interrupting rating vs available fault current, bus bracing — from a current short-circuit study, not memory; document gaps.
2. **MCC specifics**: section/bus rating, starter types (DOL/soft/VFD buckets), segregation and barriers, heat load, planned spare capacity; labeling matches the line-up drawing.
3. **Switchgear specifics**: breaker/relay schemes, CT ratios + wiring checks, trip tests (primary/secondary injection per plan), interlock function tests, torque checks per OEM; records archived.
4. **Transformers**: loading per nameplate with temperature context (top-oil/winding trends); K-factor for harmonic-rich loads; impedance ↔ fault current ↔ coordination; paralleling requires matching vector group/ratio/impedance — verify, never assume; record tap position.
5. **Condition awareness**: transformer oil/DGA screening on schedule; IR scans of terminations/bus; audible/corona observations logged vs baseline.
6. **Coordination & arc-flash**: keep settings, labels, and the study aligned; when equipment changes → flag a study refresh.

## Quality gates
- [ ] Ratings verified vs current fault study; gaps listed.
- [ ] Test/inspection records complete with instruments + calibration.
- [ ] Labels, settings, and drawings consistent after changes.
- [ ] Transformer loading/temperature within limits; tap position recorded.

## Red lines
- No energized work outside the site permit/PPE system — see `electrical-safety`.
- No torque specs from memory; OEM procedures only.

## Related
`electrical-safety` · `drives-and-vfd-engineering` · `condition-monitoring`.
