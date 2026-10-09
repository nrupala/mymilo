# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for repo skill trigger matching."""

from pathlib import Path

from app.skills import get_skill_by_name, match_skill, parse_frontmatter

SKILLS_DIR = Path(__file__).parent.parent / "skills"

EXPECTED_SKILLS = [
    "stock-analysis",
    "electrical-code",
    "read-aloud",
    "verified-code",
    "article-draft",
    "finance-content",
    "fault-simulation",
    "budget-engine",
    "code-graph",
    "safe-link",
    "document-reader",
    "financial-analytics",
    "travel-fares",
]


def test_all_13_skill_files_exist():
    for name in EXPECTED_SKILLS:
        p = SKILLS_DIR / name / "SKILL.md"
        assert p.is_file(), f"missing {p}"


def test_skill_frontmatter_has_triggers():
    for name in EXPECTED_SKILLS:
        raw = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        assert meta.get("name") == name, f"{name}: frontmatter name mismatch"
        assert meta.get("triggers"), f"{name}: no triggers"
        assert len(body) > 200, f"{name}: body too short to be useful"


def test_stock_skill_triggers():
    r = match_skill("analyze AAPL stock for me", SKILLS_DIR)
    assert r and r["name"] == "stock-analysis"


def test_electrical_code_triggers():
    r = match_skill("what does CEC section 18 say?", SKILLS_DIR)
    assert r and r["name"] == "electrical-code"


def test_no_false_positive_on_greeting():
    assert match_skill("hello how are you today", SKILLS_DIR) is None


def test_budget_triggers():
    r = match_skill("help me with my household budget", SKILLS_DIR)
    assert r and r["name"] == "budget-engine"


def test_opencode_triggers():
    r = match_skill("fix this bug in mymilo", SKILLS_DIR)
    assert r and r["name"] == "opencode-bridge"


def test_travel_triggers():
    r = match_skill("find me a cheap flight to Delhi", SKILLS_DIR)
    assert r and r["name"] == "travel-fares"


def test_get_skill_by_name_exact_and_case_insensitive():
    r = get_skill_by_name("stock-analysis", SKILLS_DIR)
    assert r and r["name"] == "stock-analysis"
    assert r["content"]  # the instruction body rides along
    r2 = get_skill_by_name("Stock-Analysis", SKILLS_DIR)
    assert r2 and r2["name"] == "stock-analysis"


def test_get_skill_by_name_unknown_and_blank():
    assert get_skill_by_name("no-such-skill", SKILLS_DIR) is None
    assert get_skill_by_name("", SKILLS_DIR) is None
    assert get_skill_by_name("  ", SKILLS_DIR) is None


def test_get_skill_by_name_finds_triggerless_skill(tmp_path):
    """The point of deliberate invocation: most skills declare no
    triggers and are unreachable by matching — by-name lookup must
    still find them."""
    d = tmp_path / "quiet-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\n"
        "name: quiet-skill\n"
        "description: A skill with no triggers.\n"
        "---\n"
        "Do the quiet thing.\n",
        encoding="utf-8",
    )
    r = get_skill_by_name("quiet-skill", tmp_path)
    assert r and r["name"] == "quiet-skill"
    assert "Do the quiet thing" in r["content"]
    # …and trigger matching indeed cannot reach it:
    assert match_skill("do the quiet thing", tmp_path) is None
