# SPDX-License-Identifier: AGPL-3.0-or-later
"""Skill Pair Program: the bundle carries each skill's pair data.

Every skill pairs with a groomed interactive layout. The pair
data lives in the skill's own frontmatter (``archetype`` + a
one-line JSON ``layout``) and rides the bundle to clients.
Unpaired skills default to the Knowledge frame with an empty
layout — incremental adoption, nothing breaks.
"""

from pathlib import Path

from app.skills import _pair_fields, get_skill_bundle, refresh_skill_cache

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def test_pair_fields_defaults():
    assert _pair_fields({}) == {"archetype": "knowledge", "layout": {}}
    assert _pair_fields({"archetype": "engine"})["archetype"] == "engine"


def test_pair_fields_parses_layout_json():
    out = _pair_fields({"archetype": "engine", "layout": '{"steps": ["A", "B"]}'})
    assert out["layout"] == {"steps": ["A", "B"]}


def test_pair_fields_malformed_layout_degrades():
    assert _pair_fields({"layout": "not json"})["layout"] == {}
    assert _pair_fields({"layout": '["a", "list"]'})["layout"] == {}


def test_bundle_carries_prototype_pairs():
    refresh_skill_cache(SKILLS_DIR)
    bundle = get_skill_bundle()
    by_name = {s["name"]: s for s in bundle["skills"]}
    budget = by_name["budget-engine"]
    assert budget["archetype"] == "engine"
    assert budget["layout"]["steps"][0] == "Income picture"
    assert budget["layout"]["artifact"] == "document"
    stock = by_name["stock-analysis"]
    assert stock["archetype"] == "analyst"
    assert stock["layout"]["artifact"] == "brief"
    code = by_name["electrical-code"]
    assert code["archetype"] == "reference"
    assert code["layout"]["blocks"] == ["Answer", "Why", "Proof", "Limits"]


def test_bundle_defaults_for_unpaired_skills():
    refresh_skill_cache(SKILLS_DIR)
    bundle = get_skill_bundle()
    unpaired = [s for s in bundle["skills"] if s["name"] == "clarity"]
    assert unpaired and unpaired[0]["archetype"] == "knowledge"
    assert unpaired[0]["layout"] == {}
    # Every entry carries the fields — clients never guess.
    assert all("archetype" in s and "layout" in s for s in bundle["skills"])
