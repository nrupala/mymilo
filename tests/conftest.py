# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Shared fixtures: app instances backed by temp DBs and a fake upstream."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import EmbeddingsConfig, ModelRoute, Settings
from app.main import create_app


def _fake_backend(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/models":
        return httpx.Response(200, json={"object": "list", "data": [{"id": "stub"}]})
    if request.url.path == "/v1/chat/completions":
        body = request.read().decode()
        import json as _json

        payload = _json.loads(body)
        user_text = payload["messages"][-1]["content"]
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
                            "content": f"stub-echo: {user_text}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[ModelRoute(name="stub", base_url="http://stub-backend/v1")],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="stub"),
    )


@pytest.fixture()
def client(settings):
    transport = httpx.MockTransport(_fake_backend)
    app = create_app(settings, transport=transport)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client_no_transport(settings):
    # No mock transport: backend is genuinely unreachable -> 503 paths.
    app = create_app(settings)
    with TestClient(app) as c:
        yield c
