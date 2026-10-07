# Decision Intelligence (Cassie Kozyrkov)

From Cassie Kozyrkov's discipline (former Chief Decision Scientist, Google): make decisions reliably under uncertainty by **engineering the decision process**, not by worshipping data. This is the intellectual core of PAE's decision-intelligence module and the "tool calculates, user decides" line.

## Core tenets
- **Decide how to decide *before* you see the data.** Set your decision criteria, default action, and thresholds in advance. This is the most important moment in decision-making — it's what stops post-hoc rationalization and confirmation bias.
- **Default action + change-my-mind threshold.** Know what you'll do by default, and pre-commit to exactly what evidence would flip it. "What would change my mind?" answered *before* looking.
- **Decisions ≠ outcomes.** Judge a decision by the process and information available *at the time*, not by how it turned out. A good decision can have a bad outcome (and vice versa). Avoid resulting / outcome bias.
- **Frame the loss function.** What does being wrong cost — in *each* direction? Asymmetric costs move the threshold. Optimize for what actually matters, not for a tidy metric.
- **Right-size the rigor.** Match effort to stakes and reversibility. Reversible (two-way-door) decisions: decide fast, default to action. Irreversible/expensive (one-way-door): slow down, gather more.
- **Data-driven vs data-inspired.** Exploratory analysis generates hypotheses (inspiration, no conclusions). Confirmatory analysis tests a *pre-registered* hypothesis. Never draw a conclusion from the same data that inspired it — that's how you fool yourself (and p-hack).
- **Don't be a data-driven fool.** If no possible data could change the action, the data is decoration. Demand that evidence has the power to change the decision.
- **Keep roles clear.** The decision-maker frames the decision and defines what matters and the thresholds; the analyst informs it. Don't let analysis quietly make the call.

## Process checklist
1. Name the decision and the real options.
2. Identify the decision-maker and what they actually care about (the objective / loss function).
3. Set the **default action** and the **evidence threshold to change it** — before any data.
4. Decide how much data/analysis is worth gathering, given stakes and reversibility.
5. Gather, then act per the pre-set criteria.
6. Review decision quality **separately** from the outcome.

## Tie-in for Nrupal
PAE should help users *pre-set their criteria, see trade-offs, and stress-test thresholds* — and never make the call for them. That's decision intelligence delivered as a tool, staying on the right side of "calculates, not advises."