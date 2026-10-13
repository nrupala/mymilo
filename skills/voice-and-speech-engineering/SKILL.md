---
name: voice-and-speech-engineering
description: Build local voice & speech stacks — TTS/STT selection, cloning consent, latency, audio quality, accessibility.
version: 1
triggers: voice, tts, stt, text to speech, speech to text, voice cloning, transcription
category: Engineering & code
blurb: Build local voice and speech stacks — engine choice, consent for cloning, latency and accessibility.
archetype: knowledge
example: Pick a local text-to-speech stack for my reader app.
---

# Voice & Speech Engineering

Voice is accessibility, content, and interface at once. Run it local where it matters, measure latency honestly, and treat cloned voices as the sensitive thing they are.

## When to use
- Read-aloud readers, assistants, dubbing, transcription features.
- Selecting/benchmarking local TTS or STT engines.
- Any voice cloning or synthetic audio production.

## Method
1. **Pipeline first**: TTS (synthesis), STT (transcription), or both; streaming vs file output; device-side vs server (local-first by default).
2. **Engine selection**: quality vs latency vs footprint (CPU/GPU); license cleared for the intended use (commercial!); language coverage; evaluate on YOUR golden sentences — not vendor demos.
3. **Cloning ethics & law**: explicit, recorded consent for any real-person voice; no impersonation; synthetic-audio disclosure where required; voice profiles encrypted at rest; deletion honored.
4. **Audio engineering**: sample-rate/format choices (wav/opus), loudness normalization, chunking for long text (keep-alive + pauses), caching synthesized segments for repeat text.
5. **Latency budgets**: time-to-first-audio target for interactive use; chunked synthesis; interruption/barge-in handling for assistants.
6. **Accessibility**: speed/pitch controls, captions/transcripts from STT, keyboard-operable players — audio users are users.
7. **Testing**: golden-audio regressions (hash + human spot-checks); noisy-input STT tests; pronunciation dictionaries for names/numbers/code.

## Quality gates
- [ ] Consent recorded for cloned voices; licenses cleared.
- [ ] Latency measured against a stated budget.
- [ ] Accessibility controls present; transcripts/captions wired.
- [ ] Golden-sample regressions in the test loop.

## Red lines
- Never clone without consent; no covert recording; disclose synthetic audio where context demands it.

## Related
`pwa-offline-engineering` · `ux-ui-design` · `local-llm-serving`.
