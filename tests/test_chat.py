# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Chat completions: routing, passthrough, and honest errors."""


def _chat(client, model="stub", **kw):
    payload = {"model": model, "messages": [{"role": "user", "content": "hi"}]}
    payload.update(kw)
    return client.post("/v1/chat/completions", json=payload)


def test_chat_passthrough(client):
    r = _chat(client)
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "stub-echo: hi"
    assert body["model"] == "stub"


def test_chat_unknown_model_404_with_available(client):
    r = _chat(client, model="nope")
    assert r.status_code == 404
    body = r.json()["error"]
    assert body["type"] == "model_not_found"
    assert "stub" in body["available"]


def test_chat_stream_rejected(client):
    r = _chat(client, stream=True)
    assert r.status_code == 400


def test_chat_backend_down_503(client_no_transport):
    r = _chat(client_no_transport)
    assert r.status_code == 503
    assert r.json()["error"]["type"] == "backend_unreachable"


def test_chat_validation_422(client):
    r = client.post("/v1/chat/completions", json={"model": "stub"})
    assert r.status_code == 422


def test_chat_response_always_carries_sources(client):
    """v0.40.0: the unified sources list is part of the envelope —
    clients (app sources row, web UI) rely on its presence."""
    r = _chat(client)
    assert r.status_code == 200
    body = r.json()
    assert "sources" in body
    assert isinstance(body["sources"], list)
    for s in body["sources"]:
        assert "type" in s and "title" in s


def test_chat_forced_skill_activates(client):
    """v0.41.0: naming a skill in the request runs it on purpose —
    no trigger phrase needed in the message."""
    r = _chat(client, skill="stock-analysis")
    assert r.status_code == 200
    body = r.json()
    assert body.get("active_skill") == "stock-analysis"
    assert {"type": "skill", "title": "stock-analysis"} in body["sources"]


def test_chat_forced_skill_beats_trigger_match(client):
    """A deliberate choice wins over whatever the message happens
    to trigger."""
    payload = {
        "model": "stub",
        "messages": [{"role": "user", "content": "help me with my household budget"}],
        "skill": "stock-analysis",
    }
    r = client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 200
    assert r.json().get("active_skill") == "stock-analysis"


def test_chat_unknown_forced_skill_degrades_quietly(client):
    """A stale client catalog must never break chat."""
    r = _chat(client, skill="no-such-skill")
    assert r.status_code == 200
    body = r.json()
    assert body.get("active_skill") is None
    assert all(s["type"] != "skill" for s in body["sources"])


def test_skills_registry_requires_auth(client):
    """v0.41.0: GET /v1/skills is no longer unauthenticated."""
    r = client.get("/v1/skills")
    assert r.status_code == 401
    r = client.get(
        "/v1/skills",
        headers={"cf-access-authenticated-user-email": "test@example.com"},
    )
    assert r.status_code == 200
    assert "skills" in r.json()
