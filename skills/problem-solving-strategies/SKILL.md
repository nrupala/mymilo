# Problem-Solving Strategies

When effort alone isn't working, reach for a strategy. Polya gives the umbrella; Engel gives the heavy-hitting techniques.

## Polya's umbrella (How to Solve It)
1. **Understand the problem** — restate it; identify the givens, the unknown, and the constraints.
2. **Devise a plan** — pick a strategy (below) or an analogous solved problem.
3. **Carry it out** — execute carefully, checking each step.
4. **Look back** — verify the answer, then generalize and look for a cleaner route.

## Engel's strategy toolkit (the heavy hitters)
- **Invariance principle:** find a quantity or property unchanged by the allowed moves — it bounds what's reachable. Ideal for "is state X reachable?" and process problems.
- **Extremal principle:** consider the largest/smallest/most-extreme object; extremes often force structure or a contradiction.
- **Box / pigeonhole principle:** n+1 items in n boxes forces a collision — powerful for existence proofs.
- **Coloring / parity arguments:** color cells or assign parity to expose impossibility (classic for tiling/covering).
- **Induction:** prove a base case and the inductive step; use strong induction when the step needs all prior cases.
- **Symmetry:** exploit it to collapse cases or reveal structure.
- **Counting two ways:** count the same set two ways to produce an identity or a bound.

## General heuristics
Simplify (solve a smaller or special case), look for patterns, introduce good notation, draw a picture, try the contrapositive, relax or tighten a constraint, work backwards from the goal, and find an analogous problem you've already solved.

## How to use
Understand -> scan the toolkit for the fitting lever (invariant? extremal? pigeonhole? induction?) -> execute carefully -> look back, verify, and generalize.

## For Nrupal
Directly useful for algorithm design (`algorithmic-implementer`), quant derivations (`quant-and-applied-math`), and engineering puzzles. Pairs with `first-principles-thinking` — reduce to fundamentals, then apply this structured toolkit on top.

## Anti-patterns to refuse
- Brute-forcing with no strategy; planning before understanding; skipping the look-back/verification; abandoning a promising strategy too early — or clinging to a dead one too long.