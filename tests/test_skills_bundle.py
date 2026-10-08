"""v0.33.0: skills bundle endpoint — dual-homed skills for native clients."""

import pytest

from app.skills import get_skill_bundle, refresh_skill_cache


@pytest.fixture()
def bundle(tmp_path):
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill\n"
        "triggers: demo, test skill\n---\n# Demo\nDo demo things.\n"
    )
    refresh_skill_cache(tmp_path)
    return get_skill_bundle()


def test_bundle_shape(bundle):
    assert bundle["count"] == 1
    assert len(bundle["hash"]) == 64  # sha256 hex
    skill = bundle["skills"][0]
    assert skill["name"] == "demo-skill"
    assert skill["triggers"] == ["demo", "test skill"]
    assert "Do demo things." in skill["content"]


def test_bundle_hash_stable(bundle):
    again = get_skill_bundle()
    assert again["hash"] == bundle["hash"]
