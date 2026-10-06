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
