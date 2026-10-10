# Build guardrails — the canonical set

Every build in this program runs under these. They come from
the owner's standing rules, the ASF-grade standard, and lessons
paid for in production. One list, so nothing depends on
remembering which doc said what.

## Flow

1. **Convergence before construction** — research → propose →
   discuss → converge → build. No building before convergence.
2. **One feature at a time, done properly.** No bulk pull, no
   rush unless the owner says "rush." Fail fast and cheap on
   prototypes so discovery costs little.
3. **Read the whole app before changing any app** — every
   component, config, and doc; live vs dead vs stub mapped
   first.
4. **Backup before edit; everything in version control.**
   PR-based checkpoints, one workstream per PR. Pushes are
   verified against the pushed tree, never the local one.

## Quality gates (in order, all green before the next build)

5. **The four release gates** — unit tests 100% · ruff check
   + format · headless frontend harness · live behavior on
   the production box. See [QUALITY.md](QUALITY.md) and
   [RELEASE-GATE.md](RELEASE-GATE.md).
6. **Green merges only** — CI green on the exact PR head, or
   no merge. Never merge red.
7. **CI-faithful environments** — dependencies verified in a
   fresh virtual environment; the ambient dev env is not
   evidence. Warnings are errors; no regressions vs baseline.
8. **Per-pair gates** (Skill Pair Program) — accuracy against
   the skill's own text · precision (the run forces the
   skill, the artifact materializes) · recall (nothing the
   skill offers is missing from its layout) · density (the
   layout passes the design system).

## Verification honesty

9. **"Verified" means behavior observed** — never files
   present, a 200 status, or a commit SHA.
10. **Delegated reports are leads, not evidence.** Merges,
    CI results, and artifacts are confirmed against the
    source system directly before anything is reported or
    deployed. (Earned 2026-10-09: a phantom merge report was
    caught by an independent check before it shipped.)
11. **Split ledger in every report** — behavior-verified vs
    implemented/CI-green; warts named, not buried; wrong
    findings withdrawn fast and plainly.
12. **A verification record per release**, kept in this repo.

## Authority & safety

13. **Per-item approval** for spend, production deploys, and
    outbound sends. (Merging green PRs is the owner's standing
    grant; idle-time work stages only — it never merges,
    deploys, spends, or sends.)
14. **Credentials**: administration on the owner's accounts
    is standard-authorized — scoped, least-privilege, values
    never in chat. Trades and money movement are never
    covered.
15. **No silent data egress.** A turn that leaves the device
    or the owner's server (any third-party source) is
    disclosed at setup and at selection; Data Controls maps
    every destination.
16. **Privacy posture** — Gmail/Calendar disconnected by
    default, connected per task, nothing retained. Device
    tokens are secrets: never in chat or logs; API tokens in
    the app are write-only (rotate / replace / delete, never
    viewable).
17. **Supplier-agnostic public content** — no OEM or model
    names in anything public-facing. Ever.

## Product & design

18. **Simplicity doctrine** — design for the least technical
    customer who wants the tool. One obvious next action per
    screen; plain words in the primary UI; engineering jargon
    in the primary UI is a defect, counted like a bug.
19. **The owner's standard** — everything shipped reflects
    his capability: hostile-review grade, nothing that a
    sharp adversary could crack and laugh at; speed never
    buys a shortcut.
20. **Ship-check** — mobile views tested; agents as
    first-class users; export from sensible places; SEO
    where the surface is public.
21. **Attribution** — "Owned by Nrupal Akolkar · Built with
    X" on new IP.
22. **ASF-grade documentation** for every repo — and docs
    freshness enforced by tests, not by hope.

See also: [QUALITY.md](QUALITY.md) ·
[RELEASE-GATE.md](RELEASE-GATE.md) ·
[HUMAN-MACHINE-AGENT.md](HUMAN-MACHINE-AGENT.md)
(data-egress law) · the Skill Pair Program in the
[mymilo-native](https://github.com/nrupala/mymilo-native)
repo.

## Adopted 2026-10-09 — from the owner's OpenCode standing rules

Reviewed in full from his canonical rulebook (now kept in
the private `nrupala/opencode-configs` repo). What follows
was additive to the set above; where his rule and ours
already agreed, ours stands unchanged.

23. **No placeholders in a "done" deliverable.** No TODO /
    FIXME / stubs / dead code knowingly left; if it cannot
    be completed now, it is not called done. Leave the tree
    better than found: no scratch files, crash artifacts,
    or unrelated changes ride along.
24. **Prototype before execution for user-facing changes.**
    Visual prototype (or written layout spec) + the owner's
    approval BEFORE code. The Pair Program's
    prototypes-first rule is this guardrail applied.
25. **Plan shape (safety-critical discipline).** Every step
    of a plan carries an owner, a verifiable exit
    condition, and a rollback path. Corner cuts are
    surfaced loudly, never silently.
26. **Convergence discipline in execution.** State the
    decision, apply one edit, verify the exact gate once,
    stop. No re-polling or re-dumping the same evidence
    "to be sure." When a once-verified assertion later
    fails, suspect the probe before the system.
27. **Detached processes.** Long-running processes launch
    fully detached with output to a log file; the shell
    returns immediately; readiness is polled from a
    separate short check. A command that hangs on a daemon
    is a bug.
28. **Project content lives in the project.** Code,
    tooling, config, and dependencies a project uses stay
    inside that project's own directory/tree.
29. **Gate tracker with evidence; exemptions are earned.**
    Gates carry a status plus the evidence command and
    observed output — no evidence means FAIL. An exemption
    exists only when the owner explicitly grants it for
    that specific unit, recorded with date, scope, and
    rationale. (Our tracker: the per-release verification
    records + QUALITY.md.)
30. **Minimum docs set per project** — user guide,
    quick-start, deployment guide, install instructions,
    configuration instructions, troubleshooting/FAQ —
    accurate against actual behavior; doc drift is a
    defect, and docs freshness is CI-verified where a
    generator exists.
31. **Metered services get a usage gate.** Before calls
    against a quota'd free tier, check the budget; a BLOCK
    state stops the work — no retries, no probing, no
    silent fallback to a bigger meter. A 429 steps down to
    an independent pool; nothing free is treated as
    unlimited.
32. **Never weaken security to pass a test.** No disabling
    endpoint security, firewall, CORS, or proxy controls
    to make a check green; workarounds carry their own
    evidence matrix instead.
33. **Context budgets nest strictly.** Model context >
    orchestrator budget > usable input, with output and
    reasoning reserves subtracted first; never ship an
    oversized atomic context — compaction is bounded and
    hierarchical.
34. **Registry before reinvention.** Before writing new
    reusable code, a skill, or a method: consult the
    registries (his OpenCode registries; our skill
    catalog). What gets invented and proves out gets
    registered, append-only, with honest status — only
    evidence-backed entries claim "verified."
35. **Accessibility floor for product UI.** WCAG 2.1 AA,
    design tokens, dark/light parity — the enterprise GUI
    bar behind the simplicity doctrine.
