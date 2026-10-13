---
name: pump-conveyor-systems
description: Driven equipment support — pumps (curves, affinity) and conveyors (torque dynamics) viewed from the electrical side.
version: 1
triggers: pumps, conveyors, pump curves, affinity laws, conveyor torque, driven equipment
category: Electrical & energy
blurb: Pumps and conveyors from the electrical side — curves, affinity laws and torque dynamics.
archetype: knowledge
example: Check whether this motor suits the conveyor's starting torque.
---

# Pump & Conveyor Systems

The load defines the duty: read the pump curve or conveyor profile before sizing the motor or setting the drive. Electrical problems are often load problems in disguise.

## When to use
- Sizing/replacing motors or drives for pumps or conveyors.
- Performance complaints: flow loss, overheating, nuisance trips, poor speed control.
- Baseline/performance trending of driven equipment.

## Method
1. **Pumps — curves first**: pump curve vs system curve → operating point; power from flow × head; affinity laws for speed control (careful with static head); NPSH margin noted (cavitation destroys more than pumps); minimum-flow protection respected.
2. **Pumps — checks**: impeller wear/fouling shows as head/flow loss at the same speed — trend it; VFD control (pressure/flow) reviewed for resonance and minimum speed; soft starts avoid water-hammer transients.
3. **Conveyors — dynamics**: loaded starts, incline/holdback, belt stretch; starting torque ≫ running torque; multi-drive load sharing (VFD droop/torque control); backstops and brake interlocks.
4. **Conveyors — checks**: sequence and interlock review (start/stop order, pull-cord e-stops per site); belt slip vs overload tradeoffs; current signature for jam detection.
5. **Baselines**: record flow/head/current/pressure per operating mode at commissioning; compare later readings at the SAME conditions — deltas are the signal.
6. **Interface discipline**: mechanical↔electrical data shared (coupling, ratios, sheave diameters) — one source of truth; changes on either side re-validated.

## Quality gates
- [ ] Operating point documented and within equipment limits.
- [ ] Starting study considered (conveyors) / min-flow protection set (pumps).
- [ ] Commissioning baselines recorded per mode.
- [ ] Mechanical data (ratios/diameters) in the asset record.

## Red lines
- No protection changes (min flow, overload class) without engineering review.
- No "it runs, so sizing is fine" — verify against the curve/profile.

## Related
`electrical-machinery-engineering` · `drives-and-vfd-engineering` · `condition-monitoring`.
