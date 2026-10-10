# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Skills convention (Phase 5, maven transfer #5).

Drop-a-markdown-file: a skill is a directory under ``skills/`` containing
a ``SKILL.md`` with frontmatter::

    ---
    name: morning-briefing
    description: Drafts the morning briefing from indexed documents.
    version: 1
    triggers: morning briefing, daily briefing
    ---
    # Morning briefing
    ...instructions...

Skills activate by trigger matching: the chat endpoint checks the user's
message against each skill's ``triggers`` (case-insensitive) and prepends
the first match's instructions as a system message. Trigger matching is
always-on and independent of the "Use documents" RAG toggle.

The scanner ingests each skill as a document tagged ``skill:<name>`` for
bookkeeping, but skills are EXCLUDED from vector search so they never
pollute document retrieval. New/changed/deleted files are picked up on
startup, on demand (``POST /v1/skills/rescan``), and periodically while
the scheduler runs (``[skills] poll_seconds`` — mtime/sha polling, no
watchdog dependency).

One convention with the Skill Foundry idea, not two.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split ``---`` frontmatter from body; minimal ``key: value`` subset."""
    meta: dict[str, str] = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key, value = key.strip(), value.strip().strip("'\"")
                    if key:
                        meta[key] = value
            return meta, text[end + 4 :].lstrip("\n")
    return meta, text


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def scan_skills(
    db: Any, docs: Any, skills_dir: str | Path
) -> dict[str, list[str]]:
    """Reconcile the skills dir with the documents index.

    Returns ``{"added": [...], "updated": [...], "removed": [...]}``
    of skill names.
    """
    root = Path(skills_dir)
    result: dict[str, list[str]] = {"added": [], "updated": [], "removed": []}
    seen: set[str] = set()
    if root.is_dir():
        for skill_md in sorted(root.glob("*/SKILL.md")):
            name = skill_md.parent.name
            raw = skill_md.read_bytes()
            meta, _body = parse_frontmatter(raw.decode("utf-8", "replace"))
            name = meta.get("name", name)
            seen.add(name)
            digest = _sha256(raw)
            existing = db.get_skill_file(name)
            if existing and existing["sha256"] == digest:
                continue
            if existing:
                _remove_skill(db, docs, existing)
                result["updated"].append(name)
            else:
                result["added"].append(name)
            uploaded = await docs.upload(
                raw,
                f"{name}.md",
                title=meta.get("name", name),
                tags=f"skill:{name}",
            )
            db.upsert_skill_file(
                name=name,
                path=str(skill_md),
                sha256=digest,
                doc_id=uploaded["doc_id"],
                description=meta.get("description", ""),
                version=meta.get("version", ""),
            )
    for row in db.list_skill_files():
        if row["name"] not in seen:
            _remove_skill(db, docs, row)
            result["removed"].append(row["name"])
    return result


def _remove_skill(db: Any, docs: Any, row: dict[str, Any]) -> None:
    try:
        docs.delete(row["doc_id"])
    except Exception:  # noqa: BLE001 — keep reconciling other skills
        pass
    db.delete_skill_file(row["name"])


def _pair_fields(meta: dict) -> dict:
    """Skill Pair Program: the data that pairs a skill with its
    groomed interactive layout (archetype frame + layout block).

    Frontmatter-authored (``archetype:`` + a one-line JSON
    ``layout:``). Defaults keep unpaired skills usable: the
    Knowledge frame and an empty layout, so the fleet adopts
    pairs incrementally and nothing breaks on a missing block.
    A malformed layout degrades to {} — never an exception.
    """
    import json as _json

    layout: dict = {}
    raw_layout = meta.get("layout", "")
    if raw_layout:
        try:
            parsed = _json.loads(raw_layout)
            if isinstance(parsed, dict):
                layout = parsed
        except ValueError:
            layout = {}
    return {
        "archetype": meta.get("archetype", "") or "knowledge",
        "layout": layout,
    }


def resolve_skills_dir(configured: str | Path, base_dir: str | Path) -> Path:
    p = Path(configured)
    return p if p.is_absolute() else Path(base_dir) / p


# v0.30.0: in-memory skill trigger cache — eliminates 82 file reads per message.
# Built once at startup, refreshed by the background skill scan.
_skill_cache: list[dict] = []
_skill_cache_dir: str | None = None


def refresh_skill_cache(skills_dir: str | Path) -> int:
    """Build the in-memory trigger cache from SKILL.md files.

    Returns the number of skills cached. Called at startup and by the
    background skill scan after each poll.
    """
    global _skill_cache, _skill_cache_dir
    root = Path(skills_dir)
    _skill_cache_dir = str(root)
    cache = []
    if root.is_dir():
        for skill_md in sorted(root.glob("*/SKILL.md")):
            try:
                raw = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue
            meta, body = parse_frontmatter(raw)
            triggers = meta.get("triggers", "")
            if not triggers:
                continue
            trigger_list = [t.strip().lower() for t in triggers.split(",") if t.strip()]
            if trigger_list:
                cache.append(
                    {
                        "name": meta.get("name", skill_md.parent.name),
                        "description": meta.get("description", ""),
                        "content": body,
                        "triggers": trigger_list,
                        "category": meta.get("category", "More skills"),
                        "blurb": meta.get("blurb", meta.get("description", "")),
                        "example": meta.get("example", ""),
                        **_pair_fields(meta),
                    }
                )
    _skill_cache = cache
    return len(cache)


def get_skill_bundle() -> dict:
    """v0.33.0: the full skill bundle for native clients (dual-homing).

    Skills live on the server AND in the app: clients download this
    bundle, cache it locally, and match triggers on-device. The hash
    lets a client detect changes cheaply.

    v0.33.1: the bundle contains ALL skills, not just those with
    triggers — only ~a quarter of skills declare trigger phrases, and
    the rest still belong on the device (for the local model and for
    browsing). Trigger-less skills ship with an empty triggers list.
    """
    import hashlib
    import json as _json

    skills: list[dict] = []
    root = Path(_skill_cache_dir) if _skill_cache_dir else None
    if root and root.is_dir():
        for skill_md in sorted(root.glob("*/SKILL.md")):
            try:
                raw = skill_md.read_text(encoding="utf-8")
            except OSError:
                continue
            meta, body = parse_frontmatter(raw)
            trigger_list = [
                t.strip().lower()
                for t in meta.get("triggers", "").split(",")
                if t.strip()
            ]
            skills.append(
                {
                    "name": meta.get("name", skill_md.parent.name),
                    "description": meta.get("description", ""),
                    "triggers": trigger_list,
                    "content": body,
                    # v0.42.0: the catalogue fields — what the skill
                    # does in plain words, where it shelves, and an
                    # example to try. Frontmatter-authored; the
                    # description is the honest fallback.
                    "category": meta.get("category", "More skills"),
                    "blurb": meta.get("blurb", meta.get("description", "")),
                    "example": meta.get("example", ""),
                    **_pair_fields(meta),
                }
            )
    else:
        # Fall back to the trigger cache if the dir is unknown.
        skills = [
            {
                "name": s["name"],
                "description": s["description"],
                "triggers": s["triggers"],
                "content": s["content"],
                "category": s.get("category", "More skills"),
                "blurb": s.get("blurb", s["description"]),
                "example": s.get("example", ""),
                "archetype": s.get("archetype", "knowledge"),
                "layout": s.get("layout", {}),
            }
            for s in _skill_cache
        ]
    payload = _json.dumps(skills, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return {"hash": digest, "count": len(skills), "skills": skills}


def get_skill_by_name(name: str, skills_dir: str | Path) -> dict[str, str] | None:
    """v0.41.0: deliberate invocation — fetch one skill by name.

    Mirrors match_skill's cache-then-disk strategy but matches the
    skill NAME (case-insensitive), including skills that declare no
    triggers — the majority, and unreachable by trigger matching.
    Returns {"name", "description", "content"} or None.
    """
    wanted = name.strip().lower()
    if not wanted:
        return None
    if _skill_cache and _skill_cache_dir == str(skills_dir):
        for skill in _skill_cache:
            if skill["name"].lower() == wanted:
                return {
                    "name": skill["name"],
                    "description": skill["description"],
                    "content": skill["content"],
                }
        return None
    root = Path(skills_dir)
    if not root.is_dir():
        return None
    for skill_md in sorted(root.glob("*/SKILL.md")):
        try:
            raw = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(raw)
        skill_name = meta.get("name", skill_md.parent.name)
        if skill_name.lower() == wanted:
            return {
                "name": skill_name,
                "description": meta.get("description", ""),
                "content": body,
            }
    return None


def match_skill(message: str, skills_dir: str | Path) -> dict[str, str] | None:
    """Match a chat message against skill triggers (case-insensitive).

    Returns {"name": ..., "description": ..., "content": ...} for the first
    skill whose trigger phrase appears in the message, or None. Deterministic:
    skills are checked in sorted directory order so matches are stable.

    v0.30.0: uses the in-memory cache (no disk I/O). Falls back to direct
    scan if the cache is empty or for a different directory.
    """
    # Use cache if it's for this directory
    if _skill_cache and _skill_cache_dir == str(skills_dir):
        lowered = message.lower()
        for skill in _skill_cache:
            for trigger in skill["triggers"]:
                if trigger and trigger in lowered:
                    return {
                        "name": skill["name"],
                        "description": skill["description"],
                        "content": skill["content"],
                    }
        return None

    # Fallback: direct disk scan (cache miss or different dir)
    root = Path(skills_dir)
    if not root.is_dir():
        return None
    lowered = message.lower()
    for skill_md in sorted(root.glob("*/SKILL.md")):
        try:
            raw = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(raw)
        triggers = meta.get("triggers", "")
        if not triggers:
            continue
        for trigger in triggers.split(","):
            trigger = trigger.strip().lower()
            if trigger and trigger in lowered:
                return {
                    "name": meta.get("name", skill_md.parent.name),
                    "description": meta.get("description", ""),
                    "content": body,
                }
    return None
