---
name: marketplace-platforms
description: Design two-sided marketplaces - supply and demand, trust and safety, matching, payouts, cold start.
version: 1
triggers: marketplace, two-sided market, platform business, cold start, payouts
category: Money & markets
blurb: Design two-sided marketplaces — supply and demand, trust and safety, matching and payouts.
archetype: knowledge
example: Pressure-test my marketplace idea's cold-start problem.
---

# Marketplace Platforms

Marketplaces die from the empty side. This skill covers the mechanics: liquidity before features, trust before growth, honest money flows — whether the participants are humans, agents, or both.

## When to use
- Designing or reviewing any two-sided platform (services, goods, agents/connectors).
- Fixing a marketplace that has supply or demand but no transactions.
- Adding payments, reputation, or disputes to an existing platform.

## Method
1. **Sides & jobs**: who supplies, who demands, why each shows up. Define the liquidity unit ("N completed transactions in M weeks in one category × geography").
2. **Cold start**: pick a wedge (narrow category, one region, one agent-tool family); seed the harder side manually; subsidies only with exit criteria; measure fill rate and time-to-match from day one.
3. **Trust & safety**: identity (verified badges, KYC where money moves), reputation (reviews with anti-fraud controls), escrow or staged payment, dispute flow with SLAs, prohibition list, fraud loops closed.
4. **Matching & ranking**: quality + fairness signals; avoid rich-get-richer collapse; monitor concentration (top-1% share); ranking change log.
5. **Money**: take rate design, payout rails and schedules, refunds/chargebacks, tax basics per jurisdiction; programmatic payers (API buyers, agents) treated as first-class.
6. **Operations**: support paths, policy enforcement ladder, sensitive categories with extra controls, incident drills.
7. **Metrics with honesty**: GMV, take rate, repeat rate, liquidity, dispute rate, time-to-first-match; no vanity totals; segment before celebrating.

## Quality gates
- [ ] Liquidity target defined and instrumented before launch.
- [ ] Trust flows (identity, reviews, disputes) designed end-to-end.
- [ ] Payout accounting reconciles to the cent; refund policy written.
- [ ] Fraud monitoring live; concentration dashboard exists.
- [ ] Cold-start wedge with exit criteria.

## Red lines
- No fake supply, fake reviews, or inflated metrics — the ecosystem audits itself.
- No hidden fees or payout surprises; disputes never ignored.
- Payment flows get regulatory review; user funds never commingle.

## Related
`payments-and-billing` · `revenue-management` · `authentication-authorization` · `crm` · `policy-as-code`.
