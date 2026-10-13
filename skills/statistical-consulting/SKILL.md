---
name: statistical-consulting
description: Run statistics engagements - problem framing, study design, assumption checks, reports clients can act on.
version: 1
triggers: statistics consulting, study design, statistical report, assumptions, analyze study
category: Thinking & decisions
blurb: Run statistics engagements — framing, study design, assumption checks and reports clients can act on.
archetype: knowledge
example: Design a study that will actually answer my question.
---

# Statistical Consulting

Statistics fails when the analysis starts before the decision is defined. This skill is the engagement discipline: frame → design → analyze → validate → deliver, with an audit trail.

## When to use
- Client/colleague work where a decision depends on data.
- Designing studies: sampling, experiments (A/B, DOE), observational analyses.
- Reviewing someone else's analysis before it drives a decision.

## Method
1. **Intake — decision first**: what decision changes with the answer? Define outcome, unit of analysis, population, timeframe, constraints. Audit the data: provenance, missingness, leakage, weirdness.
2. **Design**: experimental (randomization, factorial/DOE, blocking, sequential testing) vs observational (target estimand, confounders, matching/weighting). Power/precision analysis before collection; pre-register the analysis plan.
3. **Analyze**: EDA → assumption checks → model ladder (simple → complex, stop when complexity stops paying) → effect sizes with uncertainty (CI/credible intervals), never bare p-values.
4. **Validate**: sensitivity analyses, robustness to outliers/misspecification, multiple-comparison discipline, honest reporting of everything run.
5. **Deliver**: one-page executive summary (findings → decisions → limitations), methods memo, reproducible appendix (script + data checksums + environment).
6. **Handoff & reuse**: seal the pipeline so the analysis can be re-run when data updates; document what would change the conclusion.

## Quality gates
- [ ] Decision framed and written before analysis began.
- [ ] Analysis plan exists; deviations logged with reasons.
- [ ] Uncertainty quantified; assumptions tested, not assumed.
- [ ] Reproducible pipeline delivered (not just results).
- [ ] Limitations section present and honest.

## Red lines
- Never report significance without effect size and uncertainty; no p-hacking or selective reporting.
- No causal language from observational data without the design to back it.
- Client data is confidential: PII redacted, no unapproved reuse; no guarantees of outcomes.

## Related
`data-analytics` · `data-visualization` · `analytical-reasoning` · `forecasting` · `research-tooling`.
