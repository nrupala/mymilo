# Predictive Maintenance

The intersection of Nrupal's two strengths — safety-critical electrical/industrial engineering and AI/ML. Goal: predict and prevent equipment failure before it happens, minimizing unplanned downtime *without* over-maintaining. Pairs with `electrical-machines-sme`, `ai-ml-ds-engineer`, and `quant-and-applied-math`.

## The maintenance-strategy ladder
1. **Reactive (run-to-failure):** fix on breakdown. Fine only for non-critical, cheap-to-replace assets.
2. **Preventive (time/usage-based):** fixed schedule. Cuts failures but over-maintains healthy parts and still misses random failures.
3. **Predictive (condition-based, PdM):** act on the asset's **actual condition**, predicted from data — maintain just before failure. The sweet spot for critical assets.
4. **Prescriptive:** PdM + recommended/automated actions optimized against cost and risk.
Match strategy to asset criticality and failure cost — not everything deserves PdM.

## The P-F curve (core mental model)
Between the point a failure becomes **detectable (P)** and **functional failure (F)** lies a window. PdM detects early in that window and acts before F. Earlier, more reliable detection = longer planning runway.

## Condition-monitoring techniques (what to sense)
- **Vibration analysis** — bearings, imbalance, misalignment, looseness (rotating machinery).
- **Thermography / temperature** — hot connections, windings, transformers, panels.
- **Motor Current Signature Analysis (MCSA) / electrical signature** — broken rotor bars, eccentricity, winding faults (Nrupal's electrical domain).
- **Oil / lubricant analysis** — wear particles, contamination; **DGA** for transformer oil.
- **Acoustic / ultrasonic** — partial discharge, leaks, early bearing defects.
- **Operating parameters** — load, pressure, temperature, electrical params via SCADA/IoT.

## ML for prediction (the AI layer)
- **Anomaly detection** on streaming data — baseline "healthy," flag deviations (statistical limits, isolation forest, autoencoders).
- **Remaining Useful Life (RUL)** — regression / survival / sequence models (LSTM, temporal) on degradation signals.
- **Fault classification** — supervised mapping of signatures to fault types; failure labels are usually scarce, so handle class imbalance honestly.
- Data discipline (`ai-ml-ds-engineer`): watch leakage, label scarcity, and drift; baseline first; report uncertainty. Tune precision/recall against the **cost of a missed failure vs a false alarm** — an alert that cries wolf gets ignored.

## Reliability engineering frame
- **FMEA** — enumerate failure modes and effects; prioritize by severity x occurrence x detectability (RPN).
- **RCM** — choose the right strategy per failure mode, driven by consequence.
- Track **MTBF / MTTR**, availability, and downtime cost to justify PdM investment.

## Industrial integration
Sensors/IoT -> data platform -> models -> work orders, closed back into the CMMS/EAM (e.g. **SAP PM/PP** — the source paper embedded AI PdM into SAP S/4HANA PP, reporting ~47% less unplanned downtime and ~39% better maintenance planning). Decide edge vs cloud inference. Sensor quality and calibration are foundational — garbage sensors, garbage predictions.

## For Nrupal
Squarely his P.Eng. + AI niche: condition monitoring of motors/transformers/drives, electrical signature analysis, and protection-adjacent reliability (ties to `electrical-machines-sme` and his relay_sim work). A natural fit for a sovereign, data-owned PdM tool.

## Anti-patterns to refuse
- PdM on assets that don't justify it; "classifying" faults with no failure labels; alert thresholds set without regard to false-alarm cost; ignoring sensor quality/calibration; replacing FMEA and engineering judgment with a black box.