#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Generate docs/SKILLS.md from the skills' own frontmatter.

The catalogue's source of truth is each SKILL.md (category /
blurb / example / triggers). This script renders it as a
readable document; tests/test_skills_doc.py fails if the
committed document drifts from a fresh render, so the docs
cannot quietly go stale.

Usage: python scripts/generate-skills-doc.py [--check]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills import parse_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "SKILLS.md"

CATEGORY_ORDER = [
    "Money & markets",
    "Engineering & code",
    "Electrical & energy",
    "Thinking & decisions",
    "Mind & personal growth",
    "Everyday life",
    "Writing & documents",
    "Security & privacy",
    "How Milo works",
    "More skills",
]


def human(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split("-"))


def render() -> str:
    skills = []
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        meta, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        skills.append(
            {
                "name": meta.get("name", skill_md.parent.name),
                "category": meta.get("category", "More skills"),
                "blurb": meta.get(
                    "blurb", meta.get("description", "")
                ),
                "example": meta.get("example", ""),
                "triggers": meta.get("triggers", ""),
            }
        )
    by_cat: dict[str, list[dict]] = {}
    for s in skills:
        by_cat.setdefault(s["category"], []).append(s)
    ordered = [c for c in CATEGORY_ORDER if c in by_cat]
    ordered += sorted(c for c in by_cat if c not in CATEGORY_ORDER)

    lines = [
        "# Skills catalogue",
        "",
        "Every skill MyMilo carries, what each one does in plain",
        "words, and an example worth trying. Generated from the",
        "skills' own `SKILL.md` frontmatter by",
        "`scripts/generate-skills-doc.py` — do not edit by hand;",
        "edit the skill and regenerate. The same data powers the",
        "in-app Skills screen and the web [guide](USER-GUIDE.md).",
        "",
        f"**{len(skills)} skills, {len(ordered)} categories.**",
        "",
    ]
    for cat in ordered:
        group = by_cat[cat]
        lines.append(f"## {cat} · {len(group)}")
        lines.append("")
        for s in group:
            lines.append(f"### {human(s['name'])} (`{s['name']}`)")
            lines.append("")
            lines.append(s["blurb"])
            lines.append("")
            if s["example"]:
                lines.append(f"*Try: “{s['example']}”*")
                lines.append("")
            if s["triggers"]:
                lines.append(f"Starts on: {s['triggers']}")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    content = render()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            print("docs/SKILLS.md is stale — regenerate it.")
            return 1
        print("docs/SKILLS.md is current.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
