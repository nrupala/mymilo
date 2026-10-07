# MyMilo "Shadow" Architecture

**Goal:** Milo becomes Nrupal's muse — an in-house buddy that listens the way
Wright listens. Smaller, local-first, but with the same instincts: remember
what matters, push back when something's off, do the work before being asked.

**Status:** Design doc (2026-10-06). v0.10.0 (export + session memory) is the
foundation. This doc specs what comes next.

---

## 1. Smarter Local ↔ Cloud Switching

### Today
Each request picks one model via `route_for_complexity`. The choice is
per-request, binary, and the user can feel the seam.

### Target: Per-Turn Escalation with Context Carryover
- Start every chat on local (Phi-4-mini). Fast, free, private.
- When a turn scores complex (or asks for fresh info), escalate *that turn*
  to cloud. The full conversation history carries over — the cloud model
  sees everything, not just the latest message.
- Drop back to local for simple follow-ups ("thanks", "what was that number
  again?"). No manual switching, no lost thread.
- The PWA shows a subtle indicator of which model answered each turn
  (already have `routed_model` — surface it per-message, not just per-request).

### Implementation
- `route_for_complexity` already exists. Extend it to accept conversation
  history, not just the latest message — a "thanks" after a deep dive stays
  on cloud for coherence; a new simple question drops to local.
- Add `session_model_hint` to the session store: remembers which model
  handled the last turn, biases the next decision for continuity.
- Mid-turn escalation: if local returns low-confidence (short, hedged,
  "I don't know"), auto-retry that turn on cloud before responding.

---

## 2. Tiered Memory (The Spine)

### Today
- Session memory (v0.10.0): SQLite, last 10 turns per conversation.
- No cross-session recall. No learned facts. No summarization.

### Target: Four Tiers

#### Tier 1 — Working Memory (have this)
Current session, last N turns verbatim. Already built.

#### Tier 2 — Episodic Memory (next)
"What did we discuss about JPM last Tuesday?"
- Every session gets auto-summarized (one paragraph) when it closes or
  goes idle. Stored alongside the session metadata.
- Semantic search over session summaries using the existing embedding
  backend (`:7073`). A query like "JPM yen" finds the relevant past chat.
- When a match is found, the summary (not the full transcript) is injected
  as context: "You discussed JPMorgan Chase Japanese yen exposure on
  2026-10-01. Summary: ..."
- UI: search bar in the session list ("search past chats").

#### Tier 3 — Semantic Memory (later)
Milo learns facts about Nrupal over time.
- After each session, a background job extracts durable facts:
  "Nrupal is tracking VFD migration", "Prefers MD exports", "Wife: Natasha".
- Facts stored in a `facts` table with confidence + source session.
- Injected as a compact "user profile" block in the system prompt.
- UI: "What Milo knows about me" page — view, correct, delete facts.
  (Mirrors Wright's MEMORY.md pattern: user owns the record.)

#### Tier 4 — Summarization (when needed)
When a chat exceeds the local model's window:
- Oldest turns compress into a running summary (cloud model does this
  once, cheaply, in the background).
- Recent turns stay verbatim. The model sees: [summary] + [last 10 turns].
- Prevents the "lost the thread" failure on long conversations.

### Privacy
All memory lives on the Aetheris box (`/opt/mymilo/data/memory.db`).
Nothing leaves except per-turn cloud API calls (already the case).
The user can wipe any session or the entire store from the PWA.

---

## 3. Unified Context

### Today
Three separate context sources, each triggered independently:
- RAG (opt-in checkbox): searches documents.
- Web search (auto): "latest"/"news" queries hit Exa.
- Session history (auto): last 10 turns.

### Target: One Query, All Sources
"Latest on the VFD project" pulls from:
1. Past chats (episodic memory): "You discussed VFD migration on 2026-09-28."
2. Documents (RAG): relevant chunks from uploaded files.
3. Web (Exa): fresh news.

The model synthesizes. The source doesn't matter to Nrupal — Milo just knows.

### Implementation
- New `app/context.py`: a `build_context(query, session_id)` function that
  fans out to all three sources in parallel (asyncio.gather), then merges
  with source labels.
- Each source returns `[{source: "memory"|"docs"|"web", text, ...}]`.
- The system prompt gets a "Context" block with labeled sections.
- Deduplication: if the same fact appears in docs and web, prefer the
  fresher source, note both.

---

## 4. Model-Aware Context Sizing

### Problem
Phi-4-mini has a small window. Stuffing it with RAG chunks + web results +
10 turns of history degrades quality. Cloud models can handle the firehose.

### Target
- **Local:** lean context. Last 5 turns, top-3 RAG chunks, top-3 web
  results. Speed and coherence over completeness.
- **Cloud:** full context. Last 10 turns, top-5 RAG, top-5 web, episodic
  memory summary, user profile facts.
- `build_context` takes a `budget` param (token estimate). Sources are
  truncated by priority: working memory > user facts > web > docs >
  episodic. Never exceed budget.

---

## 5. "Listens Like Wright" — Behavioral Targets

These are the qualitative bars. Not features — instincts.

1. **Remember without being asked twice.** If Nrupal says "my wife" once,
   Milo knows it's Natasha going forward (semantic memory).
2. **Push back when something's off.** If a request contradicts a known
   fact ("sell my CNRL stock" when he works at CNRL), Milo flags it —
   not with a lecture, with a question.
3. **Do the work before being asked.** "Brief me on the market" → Milo
   already knows he wants S&P/Nasdaq/Dow, not a generic econ lecture.
   (Skills + memory compose here.)
4. **Admit limits honestly.** "I searched and couldn't find anything
   current" beats a hallucinated answer. (Already the pattern — keep it.)
5. **One question at a time.** When clarification is needed, ask the
   single most useful question, not five.

---

## Sequencing

| Phase | What | Depends on |
|-------|------|------------|
| v0.10.0 | Export + session memory (in progress) | — |
| v0.11.0 | Per-turn escalation + model-aware sizing | v0.10.0 |
| v0.12.0 | Episodic memory (summaries + search) | v0.10.0, embeddings |
| v0.13.0 | Unified context (`build_context`) | v0.11.0, v0.12.0 |
| v0.14.0 | Semantic memory (facts + profile UI) | v0.12.0 |
| v0.15.0 | Summarization for long chats | v0.11.0 |

Each phase ships as a PR, green CI, behavior-verified. No phase starts
until the previous one is live and working.

---

## Open Questions (for Nrupal)

1. **Fact learning:** Should Milo auto-extract facts, or ask permission
   first? (Wright auto-learns; Milo could too, with the "what I know"
   page as the safety valve.)
2. **Cloud spend:** Per-turn escalation means more cloud calls. Set a
   daily/weekly budget cap with an alert?
3. **Voice:** The PWA has dictation. Should Milo get voice *output*
   (on-device TTS reading replies)? Nrupal said no AI-generated audio —
   but on-device TTS is his phone reading, not AI synthesis.
