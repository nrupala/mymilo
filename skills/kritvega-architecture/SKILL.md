# Kritvega — architecture, vocabulary, and build state

Use this WHENEVER doing any Kritvega work — code, specs, PRs, roadmap — or answering what Kritvega is. Repo: `github.com/nrupala/kritvega` (private). Python-first, **stdlib-only core, no Docker**, ruff + pytest, branch → PR → green CI.

## The one-sentence thesis
**The engine — not the model — is where intelligence lives.** Kritvega makes weak local quantized models (Q3/Q4, 7B–14B on a 16GB-VRAM RTX 3080 + 96GB RAM) produce production-grade output by moving structure, verification, and reversibility OUT of the model and INTO a deterministic engine. Convergence is measured by verification checks, never by the model's self-report.

## Canonical vocabulary — do NOT conflate these
- **Model** — the raw LLM weights (Qwen, DeepSeek, Claude, GPT). Capability, nothing more.
- **Provider adapter** — the client that reaches one model over an API/runtime. Kritvega has `LocalProvider` (llama.cpp GBNF), `OpenRouterProvider` (unified cloud gateway), `AnthropicProvider` (direct), `EchoProvider` (tests). All satisfy ONE `Provider` protocol: `capability() -> Capability`; `generate(prompt, *, grammar, max_tokens, stop) -> GenerationResult`. Every call is recorded on the `Ledger` as `CallMetrics` (tokens, latency, cost).
- **Router** — the POLICY that PICKS which provider/model handles a given task or sub-step, from `Capability` + cost + difficulty + budget. Local-first; escalate to cloud/MCP only when needed and only within a budget ceiling. It is **one component** (Slice 5), not the whole product.
- **Engine / runtime** — the loop that OWNS the work: plan-graph decomposition (DAG of steps), grammar-constrained decoding, act → verify → converge, deterministic reversible patch application, memory, retrieval. **This is Kritvega.** The router lives inside it.

**Kritvega is the engine, not the router.** "Build the router" = build Slice 5 (the provider-selection policy), a part.

## How Kritvega differs from Codex / Copilot / Claude Code / Cursor / OpenCode
Those are agent **harnesses** or **editors** — some with a model-picker/router inside. They put intelligence in the MODEL and orchestrate around it, and most assume a strong cloud model plus connectivity. Kritvega inverts it: intelligence in the ENGINE, so a weak LOCAL model suffices — sovereign, offline-capable, deterministic, reversible. Codegen is the beachhead, not the ceiling. **Endgame: Kritvega replaces opencode/codex/cursor as the engine Nrupal runs on his own box.**

## Slice map (PLAN.toml is source of truth)
- Slice 1 — runtime spine: provider interface + observability + grammar-constrained act/verify/converge loop.
- Slice 2 — real local backend: llama.cpp GBNF decode for Q3/Q4. (v0.2.0)
- Slice 3 — plan-graph decomposition + deterministic reversible patch applier. (PR #2, v0.3.0)
- Providers — OpenRouter unified + Anthropic direct cloud adapters. (PR #3, v0.4.0, stacked on #2)
- Slice 5 (next) — two-tier Router: local-first, budget-escalate.
- MCP surface — expose Kritvega as one MCP server so Town/Claude/opencode/codex call it (integration becomes plumbing once this exists).
- Slice 4 — retrieval + context compaction. Then ACP + external connectors; live cloud smoke with keys on the box.

## Build conventions (hard rules)
- stdlib-only core (zero runtime deps); no Docker.
- ruff (E/F/I/UP/B, line 100, py311) + pytest; every slice lands green before the next begins.
- `VERSION` is the single source of truth — must equal pyproject `version` and `__init__.__version__`.
- branch → PR → green CI. Town's GitHub token lacks `workflow` scope, so any change under `.github/workflows/` goes via the box (box PAT has full repo + workflow rights). CI kept ultra-minimal; the box is the primary green gate.
- Heavy builds route to OpenCode-on-Aetheris (`mcp oconaetheris`). Files containing `!` must be authored via `town_write` to VFS or written free of `!` (the sandbox shell mangles `!`); `github_commit_files` commits `sandbox://` or `vfs://` bytes verbatim.
