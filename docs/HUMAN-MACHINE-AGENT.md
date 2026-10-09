# Human, machine, agent

MyMilo is built for three actors sharing one conversation:

- **Human** — the owner. Talks or types, decides, approves
  anything irreversible. Authority is never delegated away.
- **Machine** — the phone and the server doing what machines
  do instantly and locally: calculations, conversions,
  on-device skill matching, offline answers, and (soon)
  on-device models fitted to the phone's hardware.
- **Agent** — longer, multi-step work: Milo on the server
  planning and executing, coding agents behind the
  [oc-bridge](CONNECTORS.md), and assistant-class agents
  reachable over MCP — each step visible, each answer
  labeled with where it came from.

The design rule that holds the three together: **the human
always knows which actor answered, and anything that spends,
sends, or deploys waits for the human.**

## Where answers come from (the router)

A question travels a ladder, cheapest first:

1. **On-device tools** — instant, offline (calculator, units).
2. **On-device skill match + packs** — skills are matched on
   the phone from the synced bundle; downloaded model packs
   (Gemma / Qwen / Llama, sized to the device) answer fully
   offline.
3. **Aetheris (the MyMilo server)** — the default brain: local
   models behind the Token-Efficiency Engine, memory, live
   web and market data, and the agent loop.
4. **Your own API sources** — frontier models reached with
   your keys, when you choose them. Never by silent default:
   spend is always a visible choice.

Every answer keeps its origin label — *on this phone*,
*Aetheris*, *your key · \<model\>* — and its sources.

## Sources & Vault (the app's connection model)

One vault, many sources, one router:

- **Sources** — Aetheris is source #1 (the owner's own
  cloud). OpenRouter, OpenCode Zen, and any OpenAI-compatible
  endpoint sit beside it as equals.
- **The vault** — every token lives in the phone's
  hardware-backed secure storage. A token **can never be
  viewed after entry** — only rotated, replaced, or deleted,
  per source. Unlimited entries; never synced, never logged.
- **Agents behind sources** — Aetheris carries the agent
  loop and the oc-bridge; a source is a door, and what stands
  behind it is labeled like everything else.

Full app-side spec:
`SPEC-SOURCES-VAULT.md` in the
[mymilo-native](https://github.com/nrupala/mymilo-native)
repo. Background: [SHADOW-ARCHITECTURE.md](SHADOW-ARCHITECTURE.md),
[AGENTIC-PROPOSAL.md](AGENTIC-PROPOSAL.md).

See also: [Connectors](CONNECTORS.md) ·
[User guide](USER-GUIDE.md) · [Code guide](CODE-GUIDE.md)
