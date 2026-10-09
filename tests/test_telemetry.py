# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Engine telemetry tests (Token-Efficiency Engine, slice 4).

Covers the record/rollup round trip in the Database, the rollup
shaping math (savings vs full-history baseline, cache reuse,
estimator bias + calibration warning), and the endpoint wiring: a
chat writes a telemetry row, oversize refusals are counted, and the
rollup endpoint + /health engine block report it.
"""

from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.config import (
    EmbeddingsConfig,
    ModelRoute,
    PersonaConfig,
    SchedulerConfig,
    Settings,
    SkillsConfig,
)
from app.db import Database
from app.main import create_app
from app.telemetry import build_chat_record, shape_rollup

SINCE = "2000-01-01T00:00:00+00:00"


def _db(tmp_path) -> Database:
    return Database(str(tmp_path / "telemetry.db"))


def test_record_and_rollup_savings_math(tmp_path):
    db = _db(tmp_path)
    for _ in range(2):
        db.record_telemetry(
            route="local",
            estimate_source="tokenizer",
            estimated_input=500,
            actual_prompt=400,
            actual_completion=50,
            full_history_tokens=1000,
            cache_n=160,
            prompt_n=400,
            utilization=0.1,
        )
    raw = db.telemetry_rollup(SINCE)
    out = shape_rollup(raw, 7)
    assert out["requests"] == 2
    assert out["prompt_tokens"] == 800
    # Baseline 2000 vs actual 800 on those rows → 1200 saved, 60%.
    assert out["full_history_baseline_tokens"] == 2000
    assert out["tokens_saved_vs_full_history"] == 1200
    assert out["savings_pct"] == 60.0
    # Cache: 320 of 800 prompt tokens served from cache.
    assert out["cache_reuse_pct"] == 40.0
    assert out["routes"][0]["route"] == "local"
    assert out["routes"][0]["requests"] == 2


def test_estimator_bias_and_calibration_warning(tmp_path):
    db = _db(tmp_path)
    # 25 estimator rows overestimating by 20% → warning.
    for _ in range(25):
        db.record_telemetry(
            route="os",
            estimate_source="estimate",
            estimated_input=100,
            actual_prompt=80,
        )
    # Tokenizer rows are exact by construction — excluded from bias.
    db.record_telemetry(
        route="local",
        estimate_source="tokenizer",
        estimated_input=50,
        actual_prompt=999,
    )
    out = shape_rollup(db.telemetry_rollup(SINCE), 7)
    assert out["estimator_samples"] == 25
    assert out["estimator_bias_pct"] == 20.0
    assert out["calibration_warning"] is True


def test_no_calibration_warning_below_sample_floor(tmp_path):
    db = _db(tmp_path)
    for _ in range(5):
        db.record_telemetry(
            route="os",
            estimate_source="estimate",
            estimated_input=100,
            actual_prompt=50,
        )
    out = shape_rollup(db.telemetry_rollup(SINCE), 7)
    assert out["estimator_bias_pct"] == 50.0
    assert out["calibration_warning"] is False  # only 5 samples


def test_refusals_and_degradation_counted(tmp_path):
    db = _db(tmp_path)
    db.record_telemetry(route="local", status="refused_oversize", utilization=1.4)
    db.record_telemetry(route="openrouter", degraded_from="local", actual_prompt=10)
    out = shape_rollup(db.telemetry_rollup(SINCE), 7)
    assert out["refused_oversize"] == 1
    assert out["degraded"] == 1
    assert out["over_utilization_requests"] == 1


def test_build_chat_record():
    rec = build_chat_record(
        route="local",
        plan={
            "estimated_input": 321,
            "estimate_source": "tokenizer",
            "planned_max_tokens": 1024,
            "utilization": 0.16,
            "trimmed_messages": 2,
        },
        data={
            "usage": {"prompt_tokens": 322, "completion_tokens": 40},
            "timings": {"cache_n": 100, "prompt_n": 322},
            "choices": [{"finish_reason": "stop"}],
        },
        full_history_tokens=5000,
    )
    assert rec["actual_prompt"] == 322
    assert rec["cache_n"] == 100
    assert rec["finish_reason"] == "stop"
    assert rec["trimmed_messages"] == 2
    assert rec["full_history_tokens"] == 5000


# ----------------------------------------------------------------------
# Endpoint wiring
# ----------------------------------------------------------------------
def _planned_client(tmp_path, window: int = 8192) -> TestClient:
    def backend(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/tokenize":
            payload = json.loads(request.read().decode())
            return httpx.Response(
                200, json={"tokens": [1] * (len(payload["content"]) // 3)}
            )
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": []})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "stub",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "stub reply"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 5},
                "timings": {"cache_n": 40, "prompt_n": 100},
            },
        )

    settings = Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[
            ModelRoute(
                name="local",
                base_url="http://llama-backend:8080/v1",
                context_window=window,
                default_max_tokens=128,
                max_output_tokens=512,
            )
        ],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="local"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        persona=PersonaConfig(system_prompt="You are Milo."),
    )
    app = create_app(settings, transport=httpx.MockTransport(backend))
    return TestClient(app)


def test_chat_writes_telemetry_and_rollup_reports_it(tmp_path):
    client = _planned_client(tmp_path)
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={"model": "local", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert r.status_code == 200
        rollup = client.get("/v1/engine/rollup", params={"days": 7}).json()
        assert rollup["requests"] == 1
        assert rollup["prompt_tokens"] == 100
        assert rollup["cache_reuse_pct"] == 40.0
        health = client.get("/health").json()
        assert health["engine"] is not None
        assert health["engine"]["requests"] == 1


def test_oversize_refusal_is_counted(tmp_path):
    client = _planned_client(tmp_path, window=300)
    with client:
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "local",
                "messages": [{"role": "user", "content": "y" * 5000}],
            },
        )
        assert r.status_code == 400
        rollup = client.get("/v1/engine/rollup").json()
        assert rollup["refused_oversize"] == 1
        assert rollup["requests"] == 0
