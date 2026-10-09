# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Phase 5 tests: OS platform layer — skills, persona, vault, OS-client
mode, and the agent surfaces (well-known, llms.txt, MCP catalog)."""

from __future__ import annotations

import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import (
    EmbeddingsConfig,
    ModelRoute,
    PersonaConfig,
    SchedulerConfig,
    Settings,
    SkillsConfig,
)
from app.embeddings import HashEmbedder
from app.main import create_app
from app.skills import parse_frontmatter


def _chat(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-p5",
            "object": "chat.completion",
            "created": 0,
            "model": "stub",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok [S1]"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )


def _base_settings(tmp_path, **kw):
    return Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "p5.db"),
        models=[ModelRoute(name="stub", base_url="http://stub/v1")],
        embeddings=EmbeddingsConfig(backend="hash", route="stub"),
        scheduler=SchedulerConfig(enabled=False),
        **kw,
    )


@pytest.fixture()
def skills_client(tmp_path):
    sdir = tmp_path / "skills" / "demo"
    sdir.mkdir(parents=True)
    (sdir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill.\nversion: 3\n---\n"
        "# Demo\n\nDo the thing.\n"
    )
    settings = _base_settings(
        tmp_path,
        skills=SkillsConfig(
            enabled=True, dir=str(tmp_path / "skills"), poll_seconds=3600
        ),
    )
    app = create_app(
        settings, transport=httpx.MockTransport(_chat), embedder=HashEmbedder()
    )
    with TestClient(
        app,
        headers={"cf-access-authenticated-user-email": "test@example.com"},
    ) as c:
        yield c, tmp_path


# ── agent surfaces ───────────────────────────────────────────


def test_well_known(skills_client):
    c, _ = skills_client
    r = c.get("/.well-known/mymilo.json")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "MyMilo"
    assert "/v1/chat/completions" in body["openai_compatible"]
    assert "/llms.txt" in body["platform"]
    assert body["os_mode"] is False


def test_llms_txt(skills_client):
    c, _ = skills_client
    r = c.get("/llms.txt")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "POST /v1/chat/completions" in r.text
    assert "deterministic planner" in r.text


def test_mcp_catalog(skills_client):
    c, _ = skills_client
    r = c.get("/v1/mcp/tools")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "mymilo"
    names = {t["name"] for t in body["tools"]}
    for expected in (
        "chat",
        "retrieve",
        "jobs_trigger",
        "suggestions_list",
        "consents_grant",
        "ledger_summary",
        "skills_rescan",
    ):
        assert expected in names, f"missing tool {expected}"
    assert all(t.get("endpoint") and t.get("input_schema") for t in body["tools"])


# ── skills ───────────────────────────────────────────────────


def test_parse_frontmatter():
    meta, body = parse_frontmatter("---\nname: x\ndescription: y\n---\n# Hi\n")
    assert meta == {"name": "x", "description": "y"}
    assert body == "# Hi\n"
    meta, body = parse_frontmatter("# no frontmatter\n")
    assert meta == {} and body == "# no frontmatter\n"


def test_skill_indexed_on_startup(skills_client):
    c, _ = skills_client
    skills = c.get("/v1/skills").json()["skills"]
    assert len(skills) == 1
    s = skills[0]
    assert s["name"] == "demo"
    assert s["description"] == "Demo skill."
    assert s["version"] == "3"


def test_skill_not_in_general_retrieve(skills_client):
    # Skills are trigger-matched in chat, not vector-searched. They must not
    # pollute document retrieval.
    c, _ = skills_client
    hits = c.post("/v1/retrieve", json={"query": "thing", "top_k": 5}).json()["hits"]
    assert not any("demo.md" in h.get("filename", "") for h in hits)


def test_skill_update_and_remove(skills_client):
    c, tmp = skills_client
    skill_md = tmp / "skills" / "demo" / "SKILL.md"
    skill_md.write_text(
        "---\nname: demo\ndescription: Demo skill v2.\nversion: 4\n---\n"
        "# Demo\n\nDo the other thing.\n"
    )
    res = c.post("/v1/skills/rescan").json()
    assert res["updated"] == ["demo"]
    assert c.get("/v1/skills").json()["skills"][0]["description"] == "Demo skill v2."

    import shutil

    shutil.rmtree(tmp / "skills" / "demo")
    res = c.post("/v1/skills/rescan").json()
    assert res["removed"] == ["demo"]
    assert c.get("/v1/skills").json()["skills"] == []


# ── persona ──────────────────────────────────────────────────


def test_persona_endpoint_and_briefing_prompt(tmp_path):
    captured = {}

    def _cap(request: httpx.Request) -> httpx.Response:
        captured["messages"] = json.loads(request.read().decode())["messages"]
        return _chat(request)

    settings = _base_settings(
        tmp_path,
        persona=PersonaConfig(name="TestMilo", system_prompt="CUSTOM MARKER PROMPT"),
    )
    app = create_app(
        settings, transport=httpx.MockTransport(_cap), embedder=HashEmbedder()
    )
    with TestClient(app) as c:
        p = c.get("/v1/persona").json()
        assert p["name"] == "TestMilo"
        assert p["system_prompt"] == "CUSTOM MARKER PROMPT"

        up = c.post(
            "/v1/documents",
            files={"file": ("n.md", b"# N\n\nSome content here.", "text/markdown")},
        )
        assert up.status_code == 201
        job = c.post(
            "/v1/jobs",
            json={"name": "b", "payload": {"type": "briefing", "query": "content"}},
        ).json()
        r = c.post(f"/v1/jobs/{job['id']}/trigger")
        assert r.status_code == 200, r.text
        assert "CUSTOM MARKER PROMPT" in captured["messages"][0]["content"]


# ── vault ────────────────────────────────────────────────────


def test_vault_file_fallback_and_env_precedence(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "MYMILO_TEST_KEY").write_text("file-secret\n")
    settings = _base_settings(tmp_path)
    settings.models = [
        ModelRoute(name="x", base_url="http://x", api_key_env="MYMILO_TEST_KEY")
    ]
    settings.vault.path = str(vault)
    assert settings.api_key_for(settings.models[0]) == "file-secret"

    os.environ["MYMILO_TEST_KEY"] = "env-secret"
    try:
        assert settings.api_key_for(settings.models[0]) == "env-secret"
    finally:
        del os.environ["MYMILO_TEST_KEY"]


# ── OS-client mode ───────────────────────────────────────────


def test_os_endpoint_registers_os_route(tmp_path):
    cfg = tmp_path / "m.toml"
    cfg.write_text(
        '[os]\nendpoint = "http://127.0.0.1:8091/v1"\n'
        '[[models]]\nname = "local"\nbase_url = "http://127.0.0.1:8080/v1"\n'
    )
    s = Settings.load(str(cfg))
    assert s.route_for("os") is not None
    assert s.route_for("os").base_url == "http://127.0.0.1:8091/v1"
    assert s.default_model == "os"


def test_default_model_without_os(tmp_path):
    s = _base_settings(tmp_path)
    assert s.default_model == "stub"  # falls back to first route
