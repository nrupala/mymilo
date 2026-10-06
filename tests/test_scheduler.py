# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Phase 3 tests: proactive engine.

Cron parsing, job validation, scheduler tick, the deterministic planner,
and the consent-gated action registry. Retrieval-dependent paths use the
deterministic HashEmbedder (test-only) plus a canned chat backend — this
exercises the machinery, not semantic quality.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.actions import ActionRegistry, ConsentRequired
from app.cron import CronError, matches, next_run, parse_cron
from app.embeddings import HashEmbedder
from app.main import create_app
from app.scheduler import (
    JobDefinitionError,
    compute_next_run,
    tick,
    validate_cron,
    validate_job_payload,
)


@pytest.fixture()
def sched_client(settings):
    """App with HashEmbedder and a canned chat backend, scheduler loop off."""

    def _chat(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-sched",
                "object": "chat.completion",
                "created": 0,
                "model": "stub",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": (
                                "Briefing draft: standup notes cover "
                                "the atlas milestone. [S1]"
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    app = create_app(
        settings,
        transport=httpx.MockTransport(_chat),
        embedder=HashEmbedder(),
    )
    with TestClient(app) as c:
        yield c


# ── cron ─────────────────────────────────────────────────────


def test_parse_basic():
    sched = parse_cron("0 7 * * *")
    assert matches(sched, datetime(2026, 10, 6, 7, 0))
    assert not matches(sched, datetime(2026, 10, 6, 7, 1))
    assert not matches(sched, datetime(2026, 10, 6, 8, 0))


def test_parse_steps_lists_ranges():
    sched = parse_cron("*/15 9-17 * * 1-5")
    assert matches(sched, datetime(2026, 10, 6, 9, 30))  # Tuesday
    assert not matches(sched, datetime(2026, 10, 6, 9, 31))
    assert not matches(sched, datetime(2026, 10, 10, 9, 30))  # Saturday
    sched2 = parse_cron("0 0 1,15 * *")
    assert matches(sched2, datetime(2026, 10, 1, 0, 0))
    assert matches(sched2, datetime(2026, 10, 15, 0, 0))
    assert not matches(sched2, datetime(2026, 10, 2, 0, 0))


def test_parse_dom_dow_or_semantics():
    # Restricted dom AND dow: match when EITHER matches (Vixie cron).
    sched = parse_cron("0 0 1 * 0")
    assert matches(sched, datetime(2026, 11, 1, 0, 0))  # 1st of month (Sunday)
    assert matches(sched, datetime(2026, 10, 11, 0, 0))  # a Sunday, not the 1st
    assert matches(sched, datetime(2026, 10, 1, 0, 0))  # 1st (Thursday)
    assert not matches(sched, datetime(2026, 10, 2, 0, 0))  # neither


def test_parse_invalid():
    with pytest.raises(CronError):
        parse_cron("0 7 * *")
    with pytest.raises(CronError):
        parse_cron("61 * * * *")
    with pytest.raises(CronError):
        parse_cron("nope * * * *")


def test_next_run():
    after = datetime(2026, 10, 6, 1, 0)
    assert next_run("0 7 * * *", after=after) == datetime(2026, 10, 6, 7, 0)
    assert next_run("0 7 * * *", after=datetime(2026, 10, 6, 7, 0)) == datetime(
        2026, 10, 7, 7, 0
    )
    assert compute_next_run("0 7 * * *", after=after).startswith("2026-10-06T07:00")
    assert compute_next_run(None) is None


# ── job validation ───────────────────────────────────────────


def test_validate_job_payload():
    assert (
        validate_job_payload({"type": "reminder", "text": "hi"})["type"] == "reminder"
    )
    brief = validate_job_payload({"type": "briefing"})
    assert brief["query"] == "recent documents"
    assert brief["top_k"] == 5
    with pytest.raises(JobDefinitionError):
        validate_job_payload({"type": "webhook"})
    with pytest.raises(JobDefinitionError):
        validate_job_payload({"type": "reminder"})
    with pytest.raises(JobDefinitionError):
        validate_job_payload({"no": "type"})
    validate_cron("0 7 * * *")
    with pytest.raises(JobDefinitionError):
        validate_cron("bogus")


def test_create_job_rejects_bad_definition(sched_client):
    r = sched_client.post("/v1/jobs", json={"name": "x", "payload": {"type": "nope"}})
    assert r.status_code == 422
    r = sched_client.post(
        "/v1/jobs",
        json={
            "name": "x",
            "cron": "bogus",
            "payload": {"type": "reminder", "text": "t"},
        },
    )
    assert r.status_code == 422


# ── scheduler tick + trigger ─────────────────────────────────


def _make_job(client, **kw):
    base = {"name": "test-job", "payload": {"type": "reminder", "text": "drink water"}}
    base.update(kw)
    r = client.post("/v1/jobs", json=base)
    assert r.status_code == 201, r.text
    return r.json()


def test_trigger_reminder_creates_run_and_suggestion(sched_client):
    job = _make_job(sched_client)
    r = sched_client.post(f"/v1/jobs/{job['id']}/trigger")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["summary"] == "drink water"

    runs = sched_client.get(f"/v1/jobs/{job['id']}/runs").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["triggered_by"] == "manual"

    suggestions = sched_client.get("/v1/suggestions").json()["suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["kind"] == "reminder"
    assert "drink water" in suggestions[0]["body"]

    d = sched_client.post(f"/v1/suggestions/{suggestions[0]['id']}/dismiss")
    assert d.status_code == 200
    assert sched_client.get("/v1/suggestions").json()["suggestions"] == []


def test_tick_runs_due_job_and_reschedules(sched_client):
    job = _make_job(sched_client, cron="* * * * *")
    db = sched_client.app.state.db
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    db.update_job(job["id"], next_run_at=past)

    fired = asyncio.run(tick(sched_client.app))
    assert fired == 1

    runs = sched_client.get(f"/v1/jobs/{job['id']}/runs").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["triggered_by"] == "schedule"

    updated = sched_client.get(f"/v1/jobs/{job['id']}").json()
    assert updated["last_run_at"] is not None
    assert updated["next_run_at"] > past  # rescheduled into the future


def test_tick_skips_paused_job(sched_client):
    job = _make_job(sched_client, cron="* * * * *")
    sched_client.patch(f"/v1/jobs/{job['id']}", json={"status": "paused"})
    db = sched_client.app.state.db
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    db.update_job(job["id"], next_run_at=past)

    assert asyncio.run(tick(sched_client.app)) == 0
    runs = sched_client.get(f"/v1/jobs/{job['id']}/runs").json()["runs"]
    assert runs == []


def test_failed_job_records_error(sched_client):
    # A briefing naming an unknown model fails honestly: the run is
    # recorded as failed and the 404 from the router propagates.
    up = sched_client.post(
        "/v1/documents",
        files={
            "file": ("notes.md", b"# Notes\n\nSomething to summarize.", "text/markdown")
        },
    )
    assert up.status_code == 201, up.text
    job = _make_job(
        sched_client,
        payload={"type": "briefing", "query": "summarize", "model": "does-not-exist"},
    )
    r = sched_client.post(f"/v1/jobs/{job['id']}/trigger")
    assert r.status_code == 404  # ModelNotFoundError from the router
    runs = sched_client.get(f"/v1/jobs/{job['id']}/runs").json()["runs"]
    assert runs[0]["status"] == "failed"
    assert "does-not-exist" in (runs[0]["error"] or "")


# ── briefing end-to-end ──────────────────────────────────────


def test_briefing_runs_rag_and_suggests(sched_client):
    up = sched_client.post(
        "/v1/documents",
        files={
            "file": (
                "notes.md",
                b"# Standup\n\nAtlas milestone is on track.",
                "text/markdown",
            )
        },
    )
    assert up.status_code == 201, up.text

    job = _make_job(
        sched_client,
        name="morning-briefing",
        payload={"type": "briefing", "query": "atlas milestone"},
    )
    r = sched_client.post(f"/v1/jobs/{job['id']}/trigger")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"

    suggestions = sched_client.get("/v1/suggestions").json()["suggestions"]
    kinds = {s["kind"] for s in suggestions}
    assert "briefing" in kinds
    assert "note" in kinds  # DOCUMENT_ADDED planner rule fired on upload
    briefing = next(s for s in suggestions if s["kind"] == "briefing")
    assert "Briefing draft" in briefing["body"]


# ── consent-gated actions ────────────────────────────────────


def test_consent_gating(sched_client):
    actions: ActionRegistry = sched_client.app.state.actions
    db = sched_client.app.state.db

    async def _handler(db=None):
        return {"ok": True}

    actions.register(
        "test.risky",
        _handler,
        risk="medium",
        description="test-only medium-risk action",
    )
    with pytest.raises(ConsentRequired):
        asyncio.run(actions.execute_async(db, "test.risky"))

    r = sched_client.post("/v1/consents", json={"action": "test.risky"})
    assert r.status_code == 201
    assert asyncio.run(actions.execute_async(db, "test.risky")) == {"ok": True}

    listed = sched_client.get("/v1/actions").json()["actions"]
    entry = next(a for a in listed if a["name"] == "test.risky")
    assert entry["risk"] == "medium"
    assert entry["consent_granted"] is True

    d = sched_client.delete("/v1/consents/test.risky")
    assert d.status_code == 204
    with pytest.raises(ConsentRequired):
        asyncio.run(actions.execute_async(db, "test.risky"))


def test_consent_unknown_action_404(sched_client):
    r = sched_client.post("/v1/consents", json={"action": "nope.nothing"})
    assert r.status_code == 404


def test_low_risk_actions_need_no_consent(sched_client):
    actions: ActionRegistry = sched_client.app.state.actions
    db = sched_client.app.state.db
    # job.execute and suggestion.create are low-risk: they just work.
    assert all(a.risk == "low" for a in actions.list())
    assert (
        asyncio.run(
            actions.execute_async(db, "suggestion.create", title="t", body="b")
        )["title"]
        == "t"
    )
