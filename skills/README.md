# Skills — drop-a-file convention

A skill is a directory here containing a `SKILL.md` with frontmatter:

```markdown
---
name: morning-briefing
description: Drafts the morning briefing from indexed documents.
version: 1
---
# Morning briefing

Instructions the buddy should follow when running this routine...
```

## Rules

- Directory name should match `name` (frontmatter wins on conflict).
- `description` is one line — it shows up in `GET /v1/skills`.
- The whole file is indexed as a document tagged `skill:<name>`, so skills
  are searchable through retrieval like everything else.
- Drop a file → it's picked up on startup, via `POST /v1/skills/rescan`,
  or within `[skills] poll_seconds` while the scheduler runs. Edit it →
  re-indexed. Delete the directory → unindexed.
- One convention with the Skill Foundry idea, not two: this directory IS
  the foundry's inbox.

## Why files, not config

Skills are knowledge, not settings. Files are diffable, reviewable in PRs,
and syncable — config is for knobs (see `config/mymilo.example.toml`).
