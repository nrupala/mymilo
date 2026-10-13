---
name: smart-grid-engineering
description: Design and analyze smart-grid systems - ADMS/SCADA, DER integration, IEC 61850, AMI, microgrids, cyber.
version: 1
triggers: smart grid, adms, scada, der integration, iec 61850, ami, microgrids
category: Electrical & energy
blurb: Design and analyze smart-grid systems — ADMS and SCADA, DER integration, AMI and microgrids.
archetype: knowledge
example: Explain how DER integration changes protection on a feeder.
---

# Smart Grid Engineering

Modern grid = power engineering + communications + software + security. The failure mode is treating any layer in isolation. This skill spans measurement (AMI), operations (SCADA/ADMS), DER and microgrids, and OT security.

## When to use
- Smart-grid modernization, DER interconnection, or microgrid work.
- Specifying utility communications, telemetry, or grid platforms.
- Explaining grid technology (content, proposals, pilots) with engineering accuracy.

## Method
1. **Layer the architecture**: primary equipment → protection & control (IEDs, RTUs) → communications (fiber, radio, PLC) → platforms (SCADA, ADMS/DMS, DERMS, OMS) → programs & markets (DR, rates). Keep a single-line + comms diagram pair.
2. **Standards map**: IEEE 1547 (interconnection), IEC 61850 (substation), IEEE 2030.5 / OpenADR (DER & DR), CIM (models), NERC-CIP-style cyber controls. Cite clause-level where claims matter.
3. **Model before points**: network model (GIS + power flow) → telemetry point list → control loops. Every point has a purpose, units, latency class, and owner.
4. **DER & microgrids**: hosting capacity, protection coordination under inverter dominance, ride-through, islanding/island formation, black-start needs.
5. **Latency tiers**: protection (ms) vs control (s) vs analytics (min+) — budgets per loop; never mix tier traffic on one path without justification.
6. **Cybersecurity**: Purdue-style segmentation, unidirectional gateways for telemetry egress, key management, patching window realities, incident fallback to safe state.
7. **Pilot discipline**: define measurable outcomes and exit criteria before deployment; stage capabilities; always specify the safe fallback behavior.
8. **Economics & regulation**: cost stack, rate treatment, incentives, and who-opens-the-breaker (operational authority) clarified in writing.

## Quality gates
- [ ] Single-line + communications architecture reviewed by a qualified P.Eng.
- [ ] Protection coordination studied across min/max DER conditions.
- [ ] Latency budget stated per control loop; point list complete.
- [ ] Cyber posture documented against a recognized framework.
- [ ] Pilot KPIs + fallback behavior defined before energization.

## Red lines
- No protection setting changes without a coordination study; never disable safety for demos.
- No flat IT/OT networks; no field changes without switching authority clarity.
- No vendor lock-in without data export + exit plan; no customer data without consent.

## Related
`power-distribution-equipment` · `electrical-safety` · `condition-monitoring` · `simulation-engineering` · `network-security` · `regulatory-compliance`.
