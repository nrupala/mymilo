---
name: backtesting-validation
description: Validate strategies before capital — in/out-of-sample, costs, walk-forward, overfit detection, paper gates.
version: 1
triggers: backtest, backtesting, strategy validation, walk-forward, overfitting, paper trading
category: Money & markets
blurb: Validate a strategy before risking capital — in and out of sample, real costs, overfit checks.
archetype: knowledge
example: Backtest this trading idea and tell me if the result is believable.
---

# Backtesting & Strategy Validation

A backtest is a claim, not evidence — until it survives out-of-sample, costs, and paper trading. Capital comes last, after the harness earns trust.

## When to use
- Any strategy before real money (screens, rules, options structures).
- Reviewing a backtest someone presents ("+300% since 2022!").
- Building or upgrading the validation harness (e.g., an options-validation-lab).

## Method
1. **Harness standards**: deterministic runs, versioned data snapshots, correct point-in-time universes, **no look-ahead** (signals use only what was known then), realistic fills (next-open or worse for illiquid names).
2. **Protocol**: hypothesis → in-sample development → **out-of-sample holdout** (untouched until the end) → walk-forward windows; report all three, not just the shiny one.
3. **Costs & frictions**: commissions, spreads, slippage, borrow, financing, taxes where material — model them from day one, not as an afterthought.
4. **Overfit detection**: parameter sensitivity (smooth plateaus, not sharp peaks), params-vs-data ratio, "best of N" awareness; if it only works at exactly 14/3/7, it doesn't work.
5. **Fragility checks**: single-name dominance, regime dependence (works only in bull markets?), capacity/liquidity (can the size actually trade?).
6. **Paper gate**: paper-trade (or tiny size with explicit sign-off) for a defined period/fill count; compare live vs model behavior (slippage, signal timing) before scaling.
7. **Live monitoring**: track live-vs-backtest divergence; define kill criteria (drawdown, divergence, invalidation) in advance (`risk-management`).
8. **House gates**: no live trade without explicit confirmation; >$500 trades need a clear yes; paper first.

## Quality gates
- [ ] OOS + walk-forward results reported with in-sample, side by side.
- [ ] Costs modeled; sensitivity shown; fragility checks done.
- [ ] Paper gate completed (or consciously waived with written reason + approval).
- [ ] Kill criteria defined before scaling.

## Red lines
- No curve-fit parameters; no skipped costs; no "the backtest says so" as a substitute for live confirmation discipline.

## Related
`quant-research` · `risk-management` · `derivatives-and-options`.
