---
name: drives-and-vfd-engineering
description: VFD/ASD application engineering — harmonics, motor-cable interactions, protection, commissioning, troubleshooting.
version: 1
triggers: vfd, variable frequency drive, asd, harmonics, drive commissioning, drive troubleshooting
category: Electrical & energy
blurb: Apply VFDs properly — harmonics, motor-cable effects, protection, commissioning and troubleshooting.
archetype: knowledge
example: A drive keeps tripping on overvoltage — walk me through the checks.
---

# Drives & VFD/ASD Engineering

Variable frequency drives are power electronics with opinions: they reshape the supply, stress the motor, and fail in ways that look like something else. Engineer the whole system: supply → drive → cable → motor → load.

## When to use
- Drive selection, replacement, or retrofit (DOL/soft-start → VFD).
- Power quality complaints (harmonics, flicker, nuisance trips).
- Commissioning, parameter review, or repeat drive/motor failures.

## Method
1. **Application profile**: load torque type (variable/constant torque), overload duty, speed range, starts/hour, environment — select to duty, not to marketing tables.
2. **Power quality**: estimate harmonic impact; apply IEEE 519-style limits per site standard; line reactors/DC chokes/filters; multi-pulse or active front end where justified; check capacitor-bank interactions/detuning.
3. **Motor–cable–drive interaction**: reflected wave/dv-dt vs lead length (respect OEM limits); inverter-duty motors for long leads/high switching; shaft voltage & bearing currents — shaft grounding/bearing protection on larger frames.
4. **Protection & control**: configure internal protections (overload model, ground fault, over/under voltage, stall); bypass philosophy documented; e-stop & interlock design per site standards — never softened for convenience.
5. **Commissioning**: parameter sheet completed and archived (motor data, limits, ramps, setpoints); motor ID run; test each protection logically; baseline current/DC-bus/temperature trends.
6. **Troubleshooting**: fault log first; typical — OC (jam/accel), OV (decel/regeneration), UV (supply), ground fault (cable vs motor), overtemp; cross-check mechanical/load causes; document findings.
7. **Records**: parameter backups + commissioning sheets per drive (`electrical-test-records`); note firmware version.

## Quality gates
- [ ] Lead length & motor insulation system within drive limits (documented).
- [ ] Harmonics addressed per site standard; capacitor interaction reviewed.
- [ ] Protection settings tested, not just set; e-stops verified.
- [ ] Commissioning sheet + parameter backup archived.

## Red lines
- Never hi-pot drive output terminals (drive killer); isolate electronics before insulation tests.
- Never bypass drive protections to "keep running" without documented engineering approval.

## Related
`electrical-machinery-engineering` · `power-distribution-equipment` · `electrical-test-records`.
