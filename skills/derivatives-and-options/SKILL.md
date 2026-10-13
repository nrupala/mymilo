---
name: derivatives-and-options
description: Use derivatives with eyes open — payoffs, greeks intuition, risk profiles, validation before capital.
version: 1
triggers: options, derivatives, greeks, payoffs, hedging with options
category: Money & markets
blurb: Use derivatives with eyes open — payoffs, the greeks in plain terms, and risk before capital.
archetype: knowledge
example: Explain this options spread's payoff and worst case.
---

# Derivatives & Options

Derivatives are precision tools with sharp edges: they can hedge, generate income, or quietly carry unlimited risk. Understand the payoff before the trade — always. (Process and education; decisions belong to the investor with their advisor.)

## When to use
- Evaluating any option/future strategy (income, hedge, defined-risk, or the tempting "lottery").
- Reviewing an existing options position or a proposed structure.
- Before touching anything that has margin mechanics.

## Method
1. **Payoff first**: draw the payoff diagram before considering the trade — long/short call/put basics; where does it make money, where does it lose, where is loss unbounded?
2. **Greeks intuition (not worship)**: time decay (theta) is rent you pay or collect; delta as exposure; vega as a bet on volatility itself; understand which risk you're actually taking (direction vs vol vs time).
3. **Risk profiles per structure**: covered calls / cash-secured puts / spreads = defined risk with known trade-offs; naked short options = undefined risk — by house policy: only as an explicit written decision, never casually.
4. **Assignment & mechanics**: early assignment, ex-dividend traps, pin risk near expiry, exercise settlement — know the fine print before entering.
5. **Liquidity & costs**: bid-ask spreads on options can dwarf the edge; use liquid series; model exercise/assignment fees.
6. **Sizing**: premium at risk counted as real money; defined-risk preferred; no leverage creep — the account must survive the maximum loss × 2.
7. **Validation**: backtest/paper via the validation harness (options-validation-lab style) BEFORE capital; paper gate per `backtesting-validation`.
8. **House gates**: every trade >$500 gets explicit human confirmation; settlements and roll decisions documented in the journal.

## Quality gates
- [ ] Payoff + max gain/loss written before entry.
- [ ] Structure chosen for a function (income/hedge/defined-risk), not lottery.
- [ ] Liquidity + costs checked; sizing within limits.
- [ ] Paper/backtest gate done for new structures.

## Red lines
- No naked shorts without an explicit written policy decision; no options on names you wouldn't own; no leverage creep; no trading around income events unexamined.

## Related
`backtesting-validation` · `risk-management` · `investment-decision-process`.
