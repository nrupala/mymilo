---
name: payments-and-billing
description: Integrate payments and subscriptions safely — processors, entitlements, dunning, webhooks, reconciliation.
version: 1
triggers: payments, subscriptions, billing, webhooks, dunning, checkout, refunds
category: Money & markets
blurb: Integrate payments safely — hosted checkout, verified webhooks, entitlements and reconciliation.
archetype: knowledge
example: Add subscriptions to my product without payment headaches.
---

# Payments & Billing

Money moving through software demands boring rigor: hosted checkout, verified webhooks, entitlements you own, and a ledger that reconciles. Never clever, always auditable.

## When to use
- Adding payments, subscriptions, or credits to a product.
- Debugging failed renewals, chargebacks, or entitlement drift.
- Designing trial/downgrade/refund flows.

## Method
1. **Model the money**: one-time vs subscription vs usage/credits; **entitlements live in YOUR system** (processor handles money, you handle access); state machine explicit (trialing/active/past_due/canceled/refunded).
2. **Processor integration**: hosted checkout first — touch raw card data never (PCI surface ~zero); secrets in secret stores; SDK versions pinned.
3. **Webhooks are the contract**: verify signatures, handlers idempotent and replay-safe, queue + retry; poll/reconcile as backstop — webhook loss must not corrupt entitlements.
4. **Dunning & failure UX**: retry schedule, grace period, in-app banners before lockouts; downgrade path preserves user data; communicate clearly at every state change.
5. **Refunds & credits**: encoded policy flows with audit trail; no ad-hoc money moves outside the ledger (`ledger-engineering`).
6. **Tax & compliance awareness**: digital-goods taxes differ by jurisdiction — use processor tax features; keep records for the accountant (not tax advice).
7. **Reconciliation**: processor payouts vs internal ledger monthly; in-flight/failed/chargeback lists owned; variances explained, never ignored.
8. **Testing**: test mode + webhook fixtures; proration math tested explicitly (upgrade/downgrade mid-cycle).

## Quality gates
- [ ] Entitlement model + state machine documented; source of truth named.
- [ ] Webhook verification + idempotency tested (replays!).
- [ ] Reconciliation cadence running; refunds audited.
- [ ] Failure/dunning flows exercised in test mode.

## Red lines
- Never store card data; no unverified webhooks; no silent charges or price changes; refunds need audit trails.

## Related
`ledger-engineering` · `revenue-management` · `secrets-management`.
