# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Whisper voice input (v0.48.0): POST /v1/transcribe proxies the
household Whisper engine; configuration gates the feature loudly.

The engine is never faked: unconfigured -> 503, unreachable -> 502,
and there is no fallback recognizer anywhere in the path.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import WhisperConfig
from app.main import create_app

SEEN: dict = {}


def _backend(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/transcribe":
        SEEN["auth"] = request.headers.get("authorization")
        SEEN["content_type"] = request.headers.get("content-type", "")
        return httpx.Response(
            200,
            json={
                "text": "  hello milo, dictate this  ",
                "language": "en",
                "duration": 1.25,
                "segments": [{"start": 0.0, "end": 1.25, "text": "hello"}],
            },
        )
    if request.url.path == "/v1/models":
        return httpx.Response(
            200, json={"object": "list", "data": [{"id": "stub"}]}
        )
    if request.url.path == "/v1/chat/completions":
        payload = json.loads(request.read().decode())
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-stub",
                "object": "chat.completion",
                "created": 0,
                "model": payload.get("model", "stub"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "stub-echo",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    return httpx.Response(404, json={"error": "not found"})


def _down_backend(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/transcribe":
        raise httpx.ConnectError("connection refused", request=request)
    return _backend(request)


@pytest.fixture()
def whisper_settings(settings):
    settings.whisper = WhisperConfig(
        base_url="http://whisper-stub", token_env="MYMILO_WHISPER_TOKEN"
    )
    return settings


@pytest.fixture()
def whisper_client(whisper_settings):
    app = create_app(whisper_settings, transport=httpx.MockTransport(_backend))
    with TestClient(app) as c:
        yield c


def _post_audio(client: TestClient):
    return client.post(
        "/v1/transcribe",
        files={"file": ("dictation.webm", b"fake-audio-bytes", "audio/webm")},
    )


def test_transcribe_returns_engine_text(whisper_client):
    r = _post_audio(whisper_client)
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "hello milo, dictate this"  # stripped
    assert body["language"] == "en"
    assert body["duration"] == 1.25
    assert body["segments"]
    # Multipart audio actually went upstream.
    assert "multipart/form-data" in SEEN["content_type"]


def test_transcribe_forwards_bearer_token(whisper_client, monkeypatch):
    monkeypatch.setenv("MYMILO_WHISPER_TOKEN", "dummy-test-token")
    r = _post_audio(whisper_client)
    assert r.status_code == 200
    assert SEEN["auth"] == "Bearer dummy-test-token"


def test_transcribe_unconfigured_is_a_plain_503(client):
    r = _post_audio(client)
    assert r.status_code == 503
    assert "no Whisper engine is configured" in r.json()["detail"]


def test_transcribe_engine_down_is_a_plain_502(whisper_settings):
    app = create_app(
        whisper_settings, transport=httpx.MockTransport(_down_backend)
    )
    with TestClient(app) as c:
        r = _post_audio(c)
    assert r.status_code == 502
    assert "unreachable" in r.json()["detail"]


def test_transcribe_empty_audio_is_400(whisper_client):
    r = whisper_client.post(
        "/v1/transcribe",
        files={"file": ("dictation.webm", b"", "audio/webm")},
    )
    assert r.status_code == 400


def test_client_config_reports_whisper_feature(whisper_client, whisper_settings):
    import copy

    on = whisper_client.get("/v1/client/config").json()
    assert on["features"]["whisper"] is True
    # A separate Settings object with no engine configured: the
    # shared `settings` fixture is the same object whisper_settings
    # mutated, so build the "off" app from a deep copy instead.
    off_settings = copy.deepcopy(whisper_settings)
    off_settings.whisper = WhisperConfig()
    app = create_app(off_settings, transport=httpx.MockTransport(_backend))
    with TestClient(app) as c:
        off = c.get("/v1/client/config").json()
    assert off["features"]["whisper"] is False
