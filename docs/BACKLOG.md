# MyMilo Backlog — Nrupal's Feature Queue

**Rule (his words):** Features get queued and done properly, one by one.
No rushing unless he says "rush." No shaky deliveries.

## 🏃 In Progress
- **v0.11.0 — Multi-user (Natasha)**: User isolation via Cloudflare Access
  email. Separate sessions/memory per user. Add natasha.g.nayyar@gmail.com
  to Access policy.

## 📋 Queued (prioritized)
1. **Per-turn escalation + model-aware context** (shadow v0.11):
   Start local, escalate complex turns to cloud with full history, drop
   back for simple follow-ups. Lean context for local, full for cloud.
2. **Episodic memory** (shadow v0.12): Auto-summarize sessions, semantic
   search over past chats. "What did we discuss about X last week?"
3. **Unified context** (shadow v0.13): One query fans out to past chats +
   documents + web. `build_context()` merges with source labels.
4. **Semantic memory** (shadow v0.14): Milo learns facts about Nrupal.
   "What Milo knows about me" page — view/correct/delete.
5. **OpenCode bridge skill**: "Fix this bug" from phone → dispatch to
   OpenCode on Oracle box → Milo reports back. Milo as foreman.
6. **Summarization for long chats** (shadow v0.15): Compress old turns
   so local model's window doesn't choke.

## 🔭 North Star (not queued — vision only)
- **Android native assistant**: Fully offline-capable, cloud fallback to
  Aetheris, phone search integration. "AI native device."

## ✅ Shipped
- v0.6.x: PWA, logout, dictation, Access-aware SW
- v0.7.0: 13 skills
- v0.8.x: Auto-routing, background jobs, market data, OpenRouter
- v0.8.3: Date grounding
- v0.9.x: Web search (Exa), escalation triggers
- v0.10.0: Export (md/docx/html/csv), session memory spine
- v0.10.1: CSV fallback, toolbar redesign
- v0.10.2: HTML export hiccup fix
- v0.10.3: Per-message UI, Apple-style picker
- v0.10.4: Model memory awareness, CSS cache-bust, cross-session lookup
