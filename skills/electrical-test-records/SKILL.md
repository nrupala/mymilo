---
name: electrical-test-records
description: Keep test sheets, trends, and plots that survive audits — standard templates, clean data, honest charts.
version: 1
triggers: test records, test sheets, insulation test, audit-ready records, trending plots
category: Electrical & energy
blurb: Keep test sheets, trends and plots that survive audits — standard templates and honest charts.
archetype: knowledge
example: Design a test-record template our auditors will accept.
---

# Electrical Test Records (test sheets · trending · plotting)

If the record is messy, the test didn't happen. Standard sheets, clean data, honest charts — built so the next engineer (or auditor) trusts them.

## When to use
- Recording any test, inspection, or commissioning reading.
- Building or fixing templates (motors, drives, switchgear, transformers, MCC).
- Trending performance and preparing plots for reports.

## Method
1. **Test sheets — standardized per equipment class**: asset ID, date/time, ambient, load/condition, instrument + calibration status, test method reference, readings with units, acceptance criteria, verdict, tester, reviewer. "N/A" needs a reason; blank fields are defects.
2. **Data hygiene**: consistent asset IDs; SI units with conversions noted; ISO timestamps; one source of truth (file/DB); raw data stays RAW (never overwrite — add derived columns); photos attached and named.
3. **Machine-readable first**: one header row; tidy/long format (asset, date, point, value, unit, load) — plots and analysis become trivial, pivots painless.
4. **Trending**: same point + method + instrument class across time; plot vs time AND vs load where load varies; annotate repairs/changes on charts; control bands from limits or baseline.
5. **Plotting discipline**: labeled axes with units; version + date on every chart; no dual-axis tricks to tell a story; out-of-band points highlighted; summary sheet per asset (latest values + verdict).
6. **Retention & audit**: archived, findable in 60 seconds, retention per policy; superseded revisions retained (marked); corrections via dated revision notes — never silent edits.

## Quality gates
- [ ] Template fields complete; reviewer sign-off on critical tests.
- [ ] Trends updated on cadence; anomalies flagged with an action.
- [ ] Charts labeled, versioned, honest.
- [ ] Records findable and intact after supersession.

## Red lines
- No retrospective edits without a revision note; no unit soup; never destroy raw data.

## Related
`condition-monitoring` · `engineering-work-packages` (deliverable evidence) · `technical-writing`.
