# SPEC — v0.41.0 / app build 14: Skills you can see and use

**Owner's complaint (2026-10-09):** "I have still not been able to
use skills it says it has." The app announces a skill count; there
is no list, no description a person can act on, and no way to run
a skill on purpose. A feature that cannot be seen or invoked is
not a feature. This spec closes that, under the simplicity
doctrine: plain words, one obvious next action.

## Current state (read from the code, 2026-10-09)

- A skill is `skills/<name>/SKILL.md`: frontmatter `name`,
  `description`, `version`, `triggers` + an instruction body.
- Activation today is trigger matching only, inside the chat
  handler (`app/main.py`, the `if skill:` block ~line 984): the
  matched skill's body is prepended as a system message,
  `active_skill` is set, and (v0.40.0) a skill source is recorded.
- `GET /v1/skills/bundle` (auth: CF header or device token)
  already returns every skill with name, description, triggers,
  and full content — the phone syncs and caches it in Room
  (`SkillEntity`: name, description, triggers, content). Only
  ~1/4 of skills declare triggers; the rest are unmatchable by
  typing and unreachable by any UI.
- `GET /v1/skills` (Phase 5) returns registry bookkeeping
  (`SkillInfo`: name/description/version/path/doc_id/updated_at),
  has NO auth, and carries no triggers. It is not a user catalog.

## Server changes (v0.41.0)

1. **Deliberate invocation.** The chat request gains an optional
   `skill` field (skill name). When present and the skill exists,
   it is force-activated for the turn — same prepend + sources
   path as a trigger match — and takes precedence over trigger
   matching. Unknown name → ignored (normal turn), never an
   error: a stale phone catalog must not break chat.
   Implementation: resolve from the same skill source the
   matcher uses, at the point where `skill` is computed.
2. **Catalog = the bundle, reused.** No new endpoint: clients
   already hold name + description + triggers locally. The web
   UI fetches `/v1/skills/bundle` (already authenticated) and
   renders the same catalog. `GET /v1/skills` keeps its
   bookkeeping role; add the standard `_resolve_user` auth check
   to it while touching this area (it is currently open).
3. Tests: forced skill activates (response `active_skill` +
   sources contain it); forced skill beats a trigger match on a
   different skill; unknown forced skill degrades to a normal
   turn; `/v1/skills` rejects anonymous callers on the API host
   semantics used by the devices tests.

## App changes (build 14)

- **Skills screen.** Drawer gains a "Skills" entry (replacing
  the bare count line; the count moves into the screen header:
  "81 skills on this phone"). The screen lists every synced
  skill: name in plain form, its one-line description, a star
  for favorites. A search field filters by name/description.
  Data source: the Room cache the app already syncs — the
  screen works fully offline.
- **Run a skill.** Tapping a skill opens a simple sheet: the
  description, one field — "What should this skill work on?" —
  and a Run button. Run starts (or continues) a chat with the
  skill forced via the new request field; the reply's sources
  row names the skill, so the effect is visible, not magic.
- **Favorites.** Star toggles a pin stored on-device
  (settings key `pinned_skills`, comma-joined names). Pinned
  skills sort to the top of the screen under "Your favorites".
  No server state: pins are a phone preference.
- Copy rules: no word "trigger", "bundle", or "sync" on the
  surface. A skill with no description shows "No description
  yet" rather than a blank — and the fix for that is a better
  SKILL.md, filed as content debt when found.

## Web changes

- A Skills view next to Devices: the same catalog (from the
  bundle endpoint), search, and a "Use this skill" action that
  returns to chat with the skill armed for the next message —
  the composer shows "Using: <skill name> ✕" until sent or
  dismissed. Same forced-skill request field carries it.

## Gates

Standard four (RELEASE-GATE.md): unit tests, ruff, frontend
harness (web skills view exercised), live box proof — a forced
skill turn via the API host returns its source; an on-device run
from the app is the owner's walk, as with build 13.

## Out of scope (later programs)

Making skills executable tools (connectors + the agent loop are
their own specs); per-user skill enable/disable on the server;
a skill store or sharing. This spec makes the existing 81
visible, understandable, and deliberately runnable — the gap
the owner actually named.
