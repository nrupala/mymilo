---
name: condition-monitoring
description: Condition monitoring for motors, drives, and transformers — vibration, thermography, ESA, DGA, and trending rules.
version: 1
triggers: condition monitoring, vibration, thermography, esa, dga, motor health, transformer health
category: Electrical & energy
blurb: Monitor motors, drives and transformers — vibration, thermography, ESA, DGA and trending rules.
archetype: knowledge
example: Build a condition-monitoring plan for our critical motors.
---

# Condition Monitoring

Assets whisper before they scream. Baseline, trend, and triage — with context — so maintenance is planned, not emergency.

## When to use
- Building or reviewing monitoring routes for rotating machines and transformers.
- Triaging alarms: is this noise, watch, or act-now?
- Post-repair baselines (verify the fix actually fixed it).

## Method
1. **Baseline everything critical**: at commissioning or repair — vibration overall + spectra, thermography images, insulation readings, currents — as-installed, under known load.
2. **Techniques by asset**:
   - **Motors/driven**: vibration overall (ISO 20816-style zone for the machine class), bearing-defect frequencies, alignment/looseness checks; IR thermography of terminations + surfaces (comparative, load-aware).
   - **Electrical**: insulation resistance/PI trends, surge/MCA, **ESA/motor current signature** (broken rotor bars, eccentricity, load issues) with load context.
   - **Transformers**: DGA screening trends, oil quality, thermal (infrared + oil temperatures).
   - **Drives**: DC-bus ripple trends, fault logs — cross-check with motor findings.
3. **Nomenclature & points**: fixed routes; same points, same method, same instrument class — comparability is the whole game.
4. **Trend + context**: log load, ambient, speed with every reading; deltas and rates-of-change beat absolute numbers; annotate charts with repair events (`electrical-test-records`).
5. **Alert bands & triage**: define watch/warning/action bands per site standard/OEM; every alarm gets a triage record — noise / watch (recheck interval) / act (work request) — with reasoning.
6. **Escalation**: suspicious findings go to the responsible engineer with the full trend pack, not a single number.

## Quality gates
- [ ] Baselines exist for critical assets; routes scheduled and executed.
- [ ] Readings carry load/ambient context.
- [ ] Alarms triaged with recorded conclusions (no orphan alarms).
- [ ] Post-repair baselines captured.

## Red lines
- Never condemn or clear equipment on one reading without context; no alarm closes without a triage note.

## Related
`electrical-machinery-engineering` · `electrical-test-records` · `drives-and-vfd-engineering`.
