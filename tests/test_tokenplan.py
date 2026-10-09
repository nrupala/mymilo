# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Token planner tests (Token-Efficiency Engine, slice 1).

Covers the registry (config), the planning formula, the estimator, the
backend tokenizer path, history trimming, the router backstop, and the
chat endpoint's behavior: planned requests succeed with a token_plan,
oversized ones are refused with a plain explanation.
"""

from __future__ import annotations

import asyncio
import json

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
from app.main import create_app
from app.router import ModelRouter
from app.tokenplan import (
    count_tokens_backend,
    estimate_messages_tokens,
    estimate_tokens,
    plan_max_tokens,
    trim_messages_to_fit,
)


def _route(**kw) -> ModelRoute:
    base = {"name": "r", "base_url": "http://127.0.0.1:9999/v1"}
    base.update(kw)
    return ModelRoute(**base)


# ----------------------------------------------------------------------
# Estimator
# ----------------------------------------------------------------------
def test_estimate_tokens_empty_and_ratio():
    assert estimate_tokens("") == 0
    # 0.30 tokens/char, ceiling: 100 chars -> 30 tokens.
    assert estimate_tokens("x" * 100) == 30
    assert estimate_tokens("x" * 101) == 31


def test_estimate_messages_includes_overhead():
    msgs = [{"role": "user", "content": "x" * 100}]
    # 30 content tokens + 4 overhead.
    assert estimate_messages_tokens(msgs) == 34


# ----------------------------------------------------------------------
# Planning formula
# ----------------------------------------------------------------------
def test_plan_no_window_is_passthrough():
    plan = plan_max_tokens(_route(), estimated_input=10**9)
    assert plan.fits is True
    assert plan.window is None
    assert plan.planned_max_tokens == 1024  # DEFAULT_DESIRED_OUTPUT


def test_plan_normal_case_uses_route_default():
    route = _route(context_window=8192, default_max_tokens=1024, max_output_tokens=4096)
    plan = plan_max_tokens(route, estimated_input=1000)
    # margin = max(256, ceil(8192*0.05)=410) = 410
    assert plan.margin == 410
    assert plan.fits is True
    assert plan.planned_max_tokens == 1024
    assert plan.utilization == pytest.approx(1000 / 8192, abs=1e-4)


def test_plan_clamps_to_route_cap():
    route = _route(context_window=8192, default_max_tokens=1024, max_output_tokens=4096)
    plan = plan_max_tokens(route, estimated_input=100, desired=99999)
    assert plan.planned_max_tokens == 4096


def test_plan_squeezes_to_remaining():
    route = _route(context_window=8192, default_max_tokens=1024, max_output_tokens=4096)
    plan = plan_max_tokens(route, estimated_input=7500)
    # remaining = 8192 - 7500 - 410 = 282
    assert plan.fits is True
    assert plan.planned_max_tokens == 282


def test_plan_refuses_when_window_full():
    route = _route(context_window=8192, default_max_tokens=1024, max_output_tokens=4096)
    plan = plan_max_tokens(route, estimated_input=8000)
    assert plan.fits is False
    assert plan.planned_max_tokens == 0


# ----------------------------------------------------------------------
# Trimming
# ----------------------------------------------------------------------
def test_trim_drops_oldest_non_system_first():
    big = "x" * 1000  # 300 tokens each
    msgs = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": big},
        {"role": "assistant", "content": big},
        {"role": "user", "content": big},
        {"role": "user", "content": "current question"},
    ]
    trimmed, dropped = trim_messages_to_fit(msgs, token_budget=400)
    assert dropped == 2
    assert trimmed[0]["role"] == "system"
    assert trimmed[-1]["content"] == "current question"
    assert estimate_messages_tokens(trimmed) <= 400


def test_trim_never_drops_system_or_last():
    msgs = [
        {"role": "system", "content": "x" * 5000},
        {"role": "user", "content": "x" * 5000},
    ]
    trimmed, dropped = trim_messages_to_fit(msgs, token_budget=10)
    assert dropped == 0
    assert trimmed == msgs


# ----------------------------------------------------------------------
# Backend tokenizer
# ----------------------------------------------------------------------
def test_count_tokens_backend_uses_tokenize_endpoint():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tokenize"
        return httpx.Response(200, json={"tokens": [10, 20, 30, 40]})

    route = _route(base_url="http://127.0.0.1:7072/v1")
    count = asyncio.run(
        count_tokens_backend(route, "hello", transport=httpx.MockTransport(handler))
    )
    assert count == 4


def test_count_tokens_backend_fails_soft():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "nope"})

    route = _route(base_url="http://127.0.0.1:7072/v1")
    count = asyncio.run(
        count_tokens_backend(
            route, "hello world", transport=httpx.MockTransport(handler)
        )
    )
    assert count is None


def test_count_tokens_backend_skips_cloud_routes():
    route = _route(name="openrouter", base_url="https://openrouter.ai/api/v1")
    count = asyncio.run(count_tokens_backend(route, "hello"))
    assert count is None


# ----------------------------------------------------------------------
# Registry (config loading)
# ----------------------------------------------------------------------
def test_settings_load_token_registry(tmp_path):
    cfg = tmp_path / "mymilo.toml"
    cfg.write_text(
        "[[models]]\n"
        'name = "local"\n'
        'base_url = "http://127.0.0.1:7072/v1"\n'
        "context_window = 8192\n"
        "default_max_tokens = 1024\n"
        "max_output_tokens = 4096\n"
    )
    settings = Settings.load(str(cfg))
    route = settings.route_for("local")
    assert route is not None
    assert route.context_window == 8192
    assert route.default_max_tokens == 1024
    assert route.max_output_tokens == 4096


# ----------------------------------------------------------------------
# Router backstop
# ----------------------------------------------------------------------
def test_router_backstop_sets_default_and_clamps():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    route = _route(
        name="stub",
        base_url="http://stub-backend/v1",
        default_max_tokens=512,
        max_output_tokens=2048,
    )
    settings = Settings(models=[route], db_path=":memory:")
    router = ModelRouter(settings, transport=httpx.MockTransport(handler))

    asyncio.run(
        router.chat_completion(
            "stub", {"messages": [{"role": "user", "content": "hi"}]}
        )
    )
    assert seen[-1]["max_tokens"] == 512

    asyncio.run(
        router.chat_completion(
            "stub",
            {
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 99999,
            },
        )
    )
    assert seen[-1]["max_tokens"] == 2048


# ----------------------------------------------------------------------
# Chat endpoint integration
# ----------------------------------------------------------------------
def _planned_client(tmp_path, **route_kw) -> TestClient:
    def backend(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": []})
        if request.url.path == "/v1/chat/completions":
            payload = json.loads(request.read().decode())
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-stub",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "stub",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "echo max_tokens="
                                + str(payload.get("max_tokens")),
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 5},
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    route_kw.setdefault("name", "stub")
    route_kw.setdefault("base_url", "http://stub-backend/v1")
    settings = Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[ModelRoute(**route_kw)],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="stub"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        persona=PersonaConfig(system_prompt="You are Milo."),
    )
    app = create_app(settings, transport=httpx.MockTransport(backend))
    return TestClient(app)


def test_chat_endpoint_plans_max_tokens(tmp_path):
    client = _planned_client(
        tmp_path,
        context_window=4096,
        default_max_tokens=200,
        max_output_tokens=400,
    )
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={"model": "stub", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["token_plan"]["fits"] is True
    assert body["token_plan"]["planned_max_tokens"] == 200
    assert body["token_plan"]["window"] == 4096
    assert "max_tokens=200" in body["choices"][0]["message"]["content"]


def test_chat_endpoint_refuses_oversized(tmp_path):
    client = _planned_client(
        tmp_path,
        context_window=512,
        default_max_tokens=128,
        max_output_tokens=256,
    )
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "stub",
                "messages": [{"role": "user", "content": "x" * 20000}],
            },
        )
    assert r.status_code == 400
    assert "too large" in r.json()["detail"]
