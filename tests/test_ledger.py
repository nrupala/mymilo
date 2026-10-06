# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Phase 4 tests: fleet economics — ledger, cost math, quota flags, ranking."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ModelRoute, Settings
from app.ledger import compute_cost, current_month, recommend
from app.main import create_app


def _settings(tmp_path, models):
    from app.config import EmbeddingsConfig, SchedulerConfig

    return Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "ledger.db"),
        models=models,
        embeddings=EmbeddingsConfig(backend="hash", route="stub"),
        scheduler=SchedulerConfig(enabled=False),
    )


def _chat_with_usage(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-ledger",
            "object": "chat.completion",
            "created": 0,
            "model": "stub",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hi"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
        },
    )


@pytest.fixture()
def econ_client(tmp_path):
    models = [
        ModelRoute(name="local", base_url="http://stub/v1"),
        ModelRoute(
            name="cloud",
            base_url="http://stub/v1",
            input_usd_per_1k=0.15,
            output_usd_per_1k=0.60,
            free_quota_usd=1.0,
        ),
    ]
    app = create_app(
        _settings(tmp_path, models),
        transport=httpx.MockTransport(_chat_with_usage),
    )
    with TestClient(app) as c:
        yield c


# ── cost math ────────────────────────────────────────────────


def test_compute_cost():
    assert compute_cost(1000, 500, 0.15, 0.60) == pytest.approx(0.45)
    assert compute_cost(1000, 500, 0.0, 0.0) == 0.0  # local: free, always
    assert compute_cost(None, 500, 0.15, 0.60) is None  # unknown: never guessed
    assert compute_cost(None, None, 0.0, 0.0) == 0.0


def test_recommend_ranks_free_first():
    paid = ModelRoute(
        name="paid", base_url="x", input_usd_per_1k=1.0, output_usd_per_1k=2.0
    )
    quota = ModelRoute(
        name="quota",
        base_url="x",
        input_usd_per_1k=0.5,
        output_usd_per_1k=0.5,
        free_quota_usd=5.0,
    )
    free = ModelRoute(name="free", base_url="x")
    assert [r.name for r in recommend([paid, quota, free])] == [
        "free",
        "quota",
        "paid",
    ]


# ── ledger recording ─────────────────────────────────────────


def test_chat_call_is_recorded_with_cost(econ_client):
    r = econ_client.post(
        "/v1/chat/completions",
        json={"model": "cloud", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    entries = econ_client.get("/v1/ledger").json()["entries"]
    assert len(entries) == 1
    e = entries[0]
    assert e["route"] == "cloud"
    assert e["prompt_tokens"] == 1000
    assert e["completion_tokens"] == 500
    assert e["cost_usd"] == pytest.approx(0.45)
    assert e["status"] == "ok"
    assert e["latency_ms"] is not None


def test_local_call_costs_zero(econ_client):
    econ_client.post(
        "/v1/chat/completions",
        json={"model": "local", "messages": [{"role": "user", "content": "hi"}]},
    )
    e = econ_client.get("/v1/ledger").json()["entries"][0]
    assert e["cost_usd"] == 0.0


def test_ledger_summary_rolls_up(econ_client):
    for _ in range(2):
        econ_client.post(
            "/v1/chat/completions",
            json={"model": "cloud", "messages": [{"role": "user", "content": "hi"}]},
        )
    body = econ_client.get("/v1/ledger/summary").json()
    assert body["month"] == current_month()
    cloud = next(r for r in body["routes"] if r["route"] == "cloud")
    assert cloud["calls"] == 2
    assert cloud["cost_usd"] == pytest.approx(0.90)
    assert cloud["free_quota_usd"] == 1.0
    assert cloud["quota_pct"] == pytest.approx(90.0)


def test_routes_endpoint_ranking_and_spend(econ_client):
    econ_client.post(
        "/v1/chat/completions",
        json={"model": "cloud", "messages": [{"role": "user", "content": "hi"}]},
    )
    routes = econ_client.get("/v1/routes").json()["routes"]
    assert [r["name"] for r in routes] == ["local", "cloud"]  # free first
    cloud = routes[1]
    assert cloud["month_spend_usd"] == pytest.approx(0.45)
    assert cloud["quota_pct"] == pytest.approx(45.0)
    assert cloud["last_used_at"] is not None
    assert cloud["consecutive_failures"] == 0


# ── quota flags ──────────────────────────────────────────────


def test_quota_thresholds_flag_once_each(econ_client):
    db = econ_client.app.state.db

    def quota_suggestions():
        suggestions = econ_client.get("/v1/suggestions").json()["suggestions"]
        return [s for s in suggestions if s["kind"] == "quota"]

    def call():
        econ_client.post(
            "/v1/chat/completions",
            json={"model": "cloud", "messages": [{"role": "user", "content": "hi"}]},
        )

    # Two calls at $0.45 each = $0.90 of the $1.00 quota -> crosses 70%.
    call()
    call()
    quota = quota_suggestions()
    assert len(quota) == 1
    assert "70%" in quota[0]["title"]
    assert db.quota_flagged("cloud", current_month(), 0.7)

    # Third call = $1.35 -> crosses 100%: a second, distinct suggestion.
    call()
    quota = quota_suggestions()
    assert len(quota) == 2
    assert any("exhausted" in s["title"] for s in quota)

    # Fourth call crosses no new threshold: no duplicates.
    call()
    assert len(quota_suggestions()) == 2


def test_quota_exhausted_flag(econ_client):
    for _ in range(3):  # $1.35 of $1.00 -> crosses 100%
        econ_client.post(
            "/v1/chat/completions",
            json={"model": "cloud", "messages": [{"role": "user", "content": "hi"}]},
        )
    suggestions = econ_client.get("/v1/suggestions").json()["suggestions"]
    titles = [s["title"] for s in suggestions if s["kind"] == "quota"]
    assert any("exhausted" in t for t in titles)


# ── lifecycle stats ──────────────────────────────────────────


def test_health_exposes_route_stats(econ_client):
    body = econ_client.get("/health").json()
    assert body["routes"]["cloud"]["consecutive_failures"] == 0
    assert body["routes"]["cloud"]["last_used_at"] is None  # no calls yet here


def test_failed_backend_records_error_and_failure_streak(tmp_path):
    models = [
        ModelRoute(
            name="dead",
            base_url="http://127.0.0.1:9/v1",
            input_usd_per_1k=0.15,
            output_usd_per_1k=0.60,
        )
    ]
    app = create_app(_settings(tmp_path, models))  # no transport: refused
    with TestClient(app) as c:
        r = c.post(
            "/v1/chat/completions",
            json={"model": "dead", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert r.status_code == 503
        entries = c.get("/v1/ledger").json()["entries"]
        assert len(entries) == 1
        assert entries[0]["status"] == "error"
        assert entries[0]["cost_usd"] is None
        stats = c.get("/health").json()["routes"]
        assert stats["dead"]["consecutive_failures"] == 1
