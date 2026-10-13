---
name: applied-machine-learning
description: Apply machine learning with discipline - framing, baselines, validation that holds, honest evaluation, monitoring.
version: 1
triggers: machine learning, ml model, train a model, model validation, ml monitoring
category: Engineering & code
blurb: Apply machine learning with discipline — framing, baselines, validation that holds, honest evaluation.
archetype: knowledge
example: Frame this problem for ML and set a baseline before any fancy model.
---

# Applied Machine Learning

Models are decisions dressed as math. This skill is the discipline layer: frame the decision, earn complexity, validate honestly, and monitor after deployment.

## When to use
- Any "we should use ML/AI for this" proposal (including your own).
- Building or reviewing a model that will drive real decisions.
- Writing claims about model quality for products or publication.

## Method
1. **Frame**: what decision does the model inform? What is the cost of each error type? Would rules, a simple regression, or asking a human do better? Baseline first, always.
2. **Data audit**: provenance, licensing, consent, label quality, coverage of edge cases; leakage check (temporal, group, target proxies). Splits by time and group — not just random rows.
3. **Model ladder**: majority/heuristic → linear → boosted trees → deep — climb only when evaluation justifies it, holding data and splits fixed.
4. **Evaluate on decision-aligned metrics**: costs of FP/FN, calibration, per-slice performance (not just overall), uncertainty via resampling; report what would be needed to change the conclusion.
5. **Robustness & honesty**: distribution shift, adversarial inputs, known failure modes; no cherry-picked examples; documented data limitations.
6. **Deploy & monitor**: version data+code+model together; monitor drift, live performance, feedback loops; rollback path defined; regular re-validation.
7. **Document**: model card — intended use, limits, metrics per slice, training data summary; keep it current.

## Quality gates
- [ ] Baseline defined and meaningfully beaten (or the project rightly stopped).
- [ ] Leakage audited; splits by time/group where applicable.
- [ ] Slice performance + calibration reported, not aggregate accuracy alone.
- [ ] Monitoring + rollback planned before deployment.
- [ ] Model card written and versioned.

## Red lines
- No training on data without rights/consent; PII per the privacy rules.
- No accuracy-only reporting on imbalanced or high-stakes problems.
- No "AI" claims beyond measured capability; no hiding failure modes.

## Related
`data-ml-pipelines` · `data-analytics` · `prediction` · `agent-evaluation` · `privacy-compliance`.
