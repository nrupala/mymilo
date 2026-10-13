---
name: analytical-reasoning
description: Reason rigorously — deduction, induction, abduction, hypothesis trees, root cause, quantified conclusions.
version: 1
triggers: analytical reasoning, root cause, hypothesis, deduction, induction, analyze this
category: Thinking & decisions
blurb: Reason rigorously — deduction, induction, hypothesis trees, root cause and quantified conclusions.
archetype: knowledge
example: Take this problem apart with a proper hypothesis tree.
---

# Analytical Reasoning

Thinking is a skill with methods. Use the right inference for the question, structure it, and quantify where it matters.

## When to use
- Complex problems: decompose before solving.
- Root-cause hunts (incidents, anomalies, "why is this off?").
- Arguments that will drive decisions — structure them first.

## Method
1. **Classify the inference**: deduction (premises → necessary conclusion), induction (observed → general), abduction (best explanation for evidence) — know which you're doing and the confidence each earns.
2. **Structure it**: MECE decomposition (no overlaps, no gaps); hypothesis tree — rank branches by likelihood × cost to test.
3. **Root cause**: 5-whys or fishbone toward the *controllable* cause; distinguish trigger vs root; verify by reverting/testing the cause — plausible candidates don't count until tested.
4. **Evidence discipline**: tier evidence (measurements > logs > reports > opinions); base rates first; update on new evidence (how much should this change my view?).
5. **Quantify**: magnitudes and ranges (Fermi-style); ballpark beats hand-waving; state units + assumptions.
6. **Falsify your conclusion**: strongest counterargument; data that would contradict; what would change your mind — written down.
7. **Land it**: conclusion, confidence, basis, revision conditions.

## Quality gates
- [ ] Problem decomposed (MECE/tree) before answering.
- [ ] Inference type + evidence tiers explicit.
- [ ] Root cause verified, not just plausible.
- [ ] Counterarguments + revision conditions stated.

## Red lines
- No conclusions from unverified single sources; no post-hoc storytelling; never confuse plausible with proven.

## Related
`critical-thinking` · `decision-making` · `data-analytics`.
