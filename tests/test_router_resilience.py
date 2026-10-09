# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Router resilience tests (Token-Efficiency Engine, slice 3).

Covers the health gate (fail fast during failure cooldown), the
backpressure semaphore (bounded concurrency, bounded queue wait,
BackendBusyError), endpoint degradation (auto requests fall back to a
keyed cloud route; explicit choices never silently change route), and
the summarizer's in-flight guard + cumulative checkpoint coverage.
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
from app.memory import MemoryStore
from app.router import BackendBusyError, ModelRouter, UpstreamUnavailableError
from app.summarize import maybe_summarize_session

_OK = {
    "choices": [{"message": {"role": "assistant", "content": "ok"}}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
}


def _router(transport, routes=None, **kw) -> ModelRouter:
    routes = routes or [ModelRoute(name="stub", base_url="http://backend/v1")]
    settings = Settings(models=routes, db_path=":memory:")
    return ModelRouter(settings, transport=transport, **kw)


# ----------------------------------------------------------------------
# Health gate
# ----------------------------------------------------------------------
def test_gate_opens_after_threshold_and_fails_fast():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("down", request=request)

    router = _router(httpx.MockTransport(handler))
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    for _ in range(2):
        with pytest.raises(UpstreamUnavailableError):
            asyncio.run(router.chat_completion("stub", payload))
    assert calls["n"] == 2
    # Third call: gated — the transport is never touched.
    with pytest.raises(UpstreamUnavailableError):
        asyncio.run(router.chat_completion("stub", payload))
    assert calls["n"] == 2
    assert router.route_stats()["stub"]["gated"] is True


def test_gate_recovers_after_cooldown():
    state = {"down": True, "n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["down"]:
            raise httpx.ConnectError("down", request=request)
        return httpx.Response(200, json=_OK)

    router = _router(httpx.MockTransport(handler), gate_cooldown_s=0.05)
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    for _ in range(2):
        with pytest.raises(UpstreamUnavailableError):
            asyncio.run(router.chat_completion("stub", payload))
    state["down"] = False

    async def after_cooldown():
        await asyncio.sleep(0.07)
        return await router.chat_completion("stub", payload)

    data = asyncio.run(after_cooldown())
    assert data["choices"][0]["message"]["content"] == "ok"
    assert router.route_stats()["stub"]["consecutive_failures"] == 0
    assert router.route_stats()["stub"]["gated"] is False


# ----------------------------------------------------------------------
# Backpressure
# ----------------------------------------------------------------------
class _SlowTransport(httpx.AsyncBaseTransport):
    def __init__(self, release: asyncio.Event):
        self.release = release
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        await self.release.wait()
        return httpx.Response(200, json=_OK)


def test_backpressure_busy_when_slots_full_and_queue_expires():
    async def scenario():
        release = asyncio.Event()
        transport = _SlowTransport(release)
        route = ModelRoute(name="stub", base_url="http://backend/v1", max_concurrency=1)
        router = _router(transport, routes=[route], queue_wait_s=0.2)
        payload = {"messages": [{"role": "user", "content": "hi"}]}
        first = asyncio.create_task(router.chat_completion("stub", payload))
        await asyncio.sleep(0.05)
        assert router.route_stats()["stub"]["in_flight"] == 1
        with pytest.raises(BackendBusyError):
            await router.chat_completion("stub", payload)
        release.set()
        data = await first
        assert data["choices"][0]["message"]["content"] == "ok"
        assert router.route_stats()["stub"]["in_flight"] == 0

    asyncio.run(scenario())


def test_concurrency_defaults_local_one_cloud_eight():
    router = _router(httpx.MockTransport(lambda r: httpx.Response(200, json=_OK)))
    local = ModelRoute(name="l", base_url="http://127.0.0.1:7072/v1")
    cloud = ModelRoute(name="c", base_url="https://openrouter.ai/api/v1")
    assert router._concurrency_for(local) == 1
    assert router._concurrency_for(cloud) == 8


# ----------------------------------------------------------------------
# Endpoint degradation
# ----------------------------------------------------------------------
def _degradation_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("TEST_CLOUD_KEY", "test-key")

    def backend(request: httpx.Request) -> httpx.Response:
        if request.url.host == "down-backend":
            raise httpx.ConnectError("down", request=request)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": []})
        payload = json.loads(request.read().decode())
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-cloud",
                "object": "chat.completion",
                "created": 0,
                "model": "openrouter",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "cloud answer",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
                "echo_max_tokens": payload.get("max_tokens"),
            },
        )

    settings = Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[
            ModelRoute(
                name="local",
                base_url="http://down-backend/v1",
                context_window=8192,
                default_max_tokens=128,
                max_output_tokens=512,
            ),
            ModelRoute(
                name="openrouter",
                base_url="https://cloud-backend/v1",
                api_key_env="TEST_CLOUD_KEY",
            ),
        ],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="local"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        persona=PersonaConfig(system_prompt="You are Milo."),
    )
    app = create_app(settings, transport=httpx.MockTransport(backend))
    return TestClient(app)


def test_auto_request_degrades_to_cloud_when_local_down(tmp_path, monkeypatch):
    client = _degradation_client(tmp_path, monkeypatch)
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "cloud answer"
    assert body["routed_model"] == "openrouter"
    assert body["degraded_from"] == "local"


def test_explicit_local_request_never_degrades(tmp_path, monkeypatch):
    client = _degradation_client(tmp_path, monkeypatch)
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "local",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert r.status_code == 503
    assert r.json()["error"]["type"] == "backend_unreachable"


# ----------------------------------------------------------------------
# Summarizer: in-flight guard + cumulative coverage (slice 2 wart fix)
# ----------------------------------------------------------------------
class _FakeRouter:
    def __init__(self, delay: float = 0.0):
        self.calls = 0
        self.delay = delay

    async def chat_completion(self, model, payload):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return {"choices": [{"message": {"content": f"summary-{self.calls}"}}]}


def _fill(store: MemoryStore, sid: str, n: int) -> None:
    for i in range(n):
        store.add_message(sid, "user" if i % 2 == 0 else "assistant", f"msg {i}")


def test_summarize_cumulative_coverage(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    sid = store.create_session("u@example.com")
    _fill(store, sid, 35)
    router = _FakeRouter()
    result = asyncio.run(maybe_summarize_session(store, router, sid))
    assert result is not None
    row = store.get_summary(sid)
    assert row is not None
    # 35 messages, keep last 20 raw: ids 1..14 folded (cutoff id 15).
    assert row["covered_count"] == 14
    assert row["covered_from"] == 0
    assert row["summarized_up_to"] == 15

    _fill(store, sid, 10)
    result = asyncio.run(maybe_summarize_session(store, router, sid))
    assert result is not None
    row = store.get_summary(sid)
    # Second slice folds ids 16..24 (9 more) on top of the first 14.
    assert row["covered_count"] == 23
    assert row["covered_from"] == 0
    assert row["summarized_up_to"] == 25


def test_summarize_in_flight_guard(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    sid = store.create_session("u@example.com")
    _fill(store, sid, 35)
    router = _FakeRouter(delay=0.3)

    async def both():
        return await asyncio.gather(
            maybe_summarize_session(store, router, sid),
            maybe_summarize_session(store, router, sid),
        )

    results = asyncio.run(both())
    # Exactly one run did the work; the other stood down.
    assert router.calls == 1
    assert sum(1 for r in results if r is not None) == 1
