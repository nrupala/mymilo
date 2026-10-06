# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Skills convention (Phase 5, maven transfer #5).

Drop-a-markdown-file: a skill is a directory under ``skills/`` containing
a ``SKILL.md`` with frontmatter::

    ---
    name: morning-briefing
    description: Drafts the morning briefing from indexed documents.
    version: 1
    ---
    # Morning briefing
    ...instructions...

The scanner ingests each skill as a document tagged ``skill:<name>`` so
skills are searchable through the same retrieval machinery as everything
else. New/changed/deleted files are picked up on startup, on demand
(``POST /v1/skills/rescan``), and periodically while the scheduler runs
(``[skills] poll_seconds`` — mtime/sha polling, no watchdog dependency).

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


def resolve_skills_dir(configured: str | Path, base_dir: str | Path) -> Path:
    p = Path(configured)
    return p if p.is_absolute() else Path(base_dir) / p


def match_skill(message: str, skills_dir: str | Path) -> dict[str, str] | None:
    """Match a chat message against skill triggers (case-insensitive).

    Returns {"name": ..., "description": ..., "content": ...} for the first
    skill whose trigger phrase appears in the message, or None. Deterministic:
    skills are checked in sorted directory order so matches are stable.
    """
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
