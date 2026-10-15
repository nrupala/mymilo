# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Agent loop (v0.47.0): planning, execution, bounds, honesty.

Executor tests drive the jobs engine directly with stub tools —
a fake router (which also plays the planner), a fake oc-bridge,
and a fake Conduit — so step mechanics, egress accounting, caps,
and failure recording are all exercised without any network.
HTTP tests then cover auth, owner isolation, and the happy path
end to end on the stub backend.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from app import agent as agent_module
from app.agent import _extract_plan, _fallback_steps, _validate_step, egress_for_route
from app.config import (
    AgentConfig,
    EmbeddingsConfig,
    ModelRoute,
    SchedulerConfig,
    Settings,
    SkillsConfig,
)
from app.db import Database
from app.scheduler import make_job_executor

OWNER = {"cf-access-authenticated-user-email": "owner@example.com"}
OTHER = {"cf-access-authenticated-user-email": "other@example.com"}


# ── Stubs ────────────────────────────────────────────────────


class FakeRouter:
    """Router stub: plans when asked as planner, answers otherwise."""

    def __init__(self, plan_text: str = "not json", answer: str = "agent answer"):
        self.plan_text = plan_text
        self.answer = answer
        self.calls: list[tuple[str, dict]] = []

    async def chat_completion(self, model: str, payload: dict) -> dict:
        self.calls.append((model, payload))
        system = payload["messages"][0]["content"] if payload["messages"] else ""
        if "task planner" in system:
            content = self.plan_text
        else:
            content = self.answer
        return {"choices": [{"message": {"role": "assistant", "content": content}}]}


class SlowRouter(FakeRouter):
    """Answers execution calls very slowly (planner stays fast)."""

    async def chat_completion(self, model: str, payload: dict) -> dict:
        system = payload["messages"][0]["content"] if payload["messages"] else ""
        if "task planner" not in system:
            await asyncio.sleep(30)
        return await super().chat_completion(model, payload)


class CancellingRouter(FakeRouter):
    """Sets the job's cancel flag from inside its execution
    call, then hangs — the user pressing stop while a long
    step is already running."""

    def __init__(self, db: Database, job_id: str):
        super().__init__()
        self._db = db
        self._job_id = job_id

    async def chat_completion(self, model: str, payload: dict) -> dict:
        system = payload["messages"][0]["content"] if payload["messages"] else ""
        if "task planner" not in system:
            updated = dict(self._db.get_job(self._job_id)["payload"])
            updated["cancel_requested"] = True
            self._db.update_job(self._job_id, payload_json=json.dumps(updated))
            await asyncio.sleep(30)
        return await super().chat_completion(model, payload)


class ExplodingRouter(FakeRouter):
    """Execution calls fail with a genuine error shortly after
    starting, while the cancel watcher is polling."""

    async def chat_completion(self, model: str, payload: dict) -> dict:
        system = payload["messages"][0]["content"] if payload["messages"] else ""
        if "task planner" not in system:
            await asyncio.sleep(0.05)
            raise RuntimeError("router exploded")
        return await super().chat_completion(model, payload)


class FakeBridge:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        return {"ok": True, "tool": name}


class FakeConduit:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        return {"ticker": arguments.get("ticker", ""), "name": "Stub Corp"}


def _settings(tmp_path, **agent_kw) -> Settings:
    return Settings(
        db_path=str(tmp_path / "agent.db"),
        models=[ModelRoute(name="local", base_url="http://127.0.0.1:9999/v1")],
        embeddings=EmbeddingsConfig(backend="hash"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        agent=AgentConfig(**agent_kw),
    )


def _deps(settings, router, **extra):
    deps = {
        "settings": settings,
        "router": router,
        "docs": None,
        "bus": None,
    }
    deps.update(extra)
    return deps


def _make_job(db: Database, payload: dict) -> str:
    full = {"type": "agent_task", "owner": "owner@example.com", "steps": []}
    full.update(payload)
    return db.create_job("Agent task", None, full)["id"]


def _payload(db: Database, job_id: str) -> dict:
    return db.get_job(job_id)["payload"]


def _run(db: Database, deps: dict, job_id: str):
    executor = make_job_executor(deps)
    return asyncio.run(executor(db, job_id=job_id, triggered_by="test"))


def _skills_dir(tmp_path):
    root = tmp_path / "skills"
    skill_dir = root / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: test-skill\n"
        "description: A skill used by the agent-loop tests.\n"
        "---\n"
        "SKILL BODY: always answer with the test marker.\n"
    )
    return root


# ── Planner units ────────────────────────────────────────────


def test_validate_step_drops_unknown_tools_and_actions():
    assert _validate_step({"tool": "model", "action": "chat"}) is not None
    assert _validate_step({"tool": "shell", "action": "exec"}) is None
    assert _validate_step({"tool": "conduit", "action": "conduit_nope"}) is None
    assert _validate_step({"tool": "oc_bridge", "action": "oc_status"}) is not None
    assert _validate_step({"tool": "oc_bridge", "action": "rm_rf"}) is None
    assert _validate_step("not a dict") is None


def test_extract_plan_finds_json_in_prose_and_fences():
    text = 'Plan: ```json\n{"steps": [{"tool": "model", "action": "chat"}]}\n``` done'
    steps = _extract_plan(text)
    assert steps == [{"tool": "model", "action": "chat"}]
    assert _extract_plan("no json here") is None


def test_egress_for_route_names_the_destination():
    settings = Settings(
        models=[
            ModelRoute(name="local", base_url="http://127.0.0.1:8080/v1"),
            ModelRoute(name="openrouter", base_url="https://openrouter.ai/api/v1"),
        ]
    )
    local = egress_for_route(settings, "local")
    assert local["leaves_server"] is False
    cloud = egress_for_route(settings, "openrouter")
    assert cloud["leaves_server"] is True
    assert "openrouter.ai" in cloud["destination"]


# ── Fallback planning ────────────────────────────────────────

_HEALTH_STEP = {
    "tool": "oc_bridge",
    "action": "opencode_health",
    "arguments": {},
    "why": "Check the OpenCode bridge directly",
}

_MODEL_STEP = {
    "tool": "model",
    "action": "chat",
    "arguments": {},
    "why": "Carry out the task and produce the answer",
}


def test_fallback_adds_bridge_health_probe_for_bridge_tasks():
    # The live 2026-10-15 task text: the planner model failed,
    # so the fallback must still reach the bridge — one
    # read-only health probe, final model step last.
    steps = _fallback_steps(
        "Check whether OpenCode is healthy on this server using "
        "the bridge status tool, then answer in one sentence",
        None,
        None,
    )
    assert steps == [_HEALTH_STEP, _MODEL_STEP]
    # When a skill step applies it stays first; the probe
    # follows it and the model step stays last.
    with_skill = _fallback_steps("Is the OC bridge up?", "test-skill", None)
    assert [s["tool"] for s in with_skill] == ["skill", "oc_bridge", "model"]
    assert with_skill[1] == _HEALTH_STEP


def test_fallback_unchanged_for_non_bridge_tasks():
    assert _fallback_steps("Write a haiku about servers", None, None) == [_MODEL_STEP]
    steps = _fallback_steps("Do the test thing", "test-skill", None)
    assert [s["tool"] for s in steps] == ["skill", "model"]


def test_fallback_never_adds_dispatch_class_bridge_actions():
    # Even when the task text asks for dispatch work, keyword
    # matching may only ever add the read-only health probe —
    # dispatch-class actions stay model-planned only.
    steps = _fallback_steps(
        "Use OpenCode to run a command on the server and deploy it",
        None,
        None,
    )
    bridge_steps = [s for s in steps if s["tool"] == "oc_bridge"]
    assert bridge_steps == [_HEALTH_STEP]
    actions = {s["action"] for s in steps}
    assert not actions & {"oc_send_prompt", "oc_run_command", "oc_request_deploy"}


def test_fallback_bridge_task_runs_the_health_step(tmp_path):
    router = FakeRouter(plan_text="planner output that is not json")
    bridge = FakeBridge()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    job_id = _make_job(
        db,
        {
            "task": "Check whether OpenCode is healthy on this server "
            "using the bridge status tool, then answer in one sentence"
        },
    )
    out = _run(
        db,
        _deps(
            settings,
            router,
            skills_dir=empty_skills,
            oc_bridge_factory=lambda: bridge,
        ),
        job_id,
    )
    assert out["status"] == "completed"
    payload = _payload(db, job_id)
    assert payload["plan_source"] == "deterministic"
    assert bridge.calls == [("opencode_health", {})]
    steps = payload["steps"]
    assert [s["tool"] for s in steps] == ["oc_bridge", "model"]
    assert steps[0]["action"] == "opencode_health"
    assert steps[0]["status"] == "completed"
    # The probe's egress is local: the bridge lives on this server.
    assert steps[0]["egress"]["leaves_server"] is False
    assert "oc-bridge" in steps[0]["egress"]["destination"]
    assert payload["result"] == "agent answer"


# ── Executor: happy paths ────────────────────────────────────


def test_model_planned_task_runs_steps_and_records_egress(tmp_path):
    plan = json.dumps(
        {
            "steps": [
                {
                    "tool": "conduit",
                    "action": "conduit_lookup_company",
                    "arguments": {"ticker": "AAPL"},
                    "why": "resolve the company",
                },
                {"tool": "model", "action": "chat", "arguments": {}, "why": "answer"},
            ]
        }
    )
    router = FakeRouter(plan_text=plan)
    conduit = FakeConduit()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Look up AAPL and summarize"})
    out = _run(db, _deps(settings, router, conduit_factory=lambda: conduit), job_id)

    assert out["status"] == "completed"
    payload = _payload(db, job_id)
    assert payload["state"] == "completed"
    assert payload["plan_source"] == "model"
    assert payload["result"] == "agent answer"
    assert conduit.calls == [("lookup_company", {"ticker": "AAPL"})]

    steps = payload["steps"]
    assert [s["tool"] for s in steps] == ["conduit", "model"]
    assert all(s["status"] == "completed" for s in steps)
    # Egress honesty: Conduit leaves the server and says where;
    # the local model step does not leave.
    assert steps[0]["egress"]["leaves_server"] is True
    assert "Conduit" in steps[0]["egress"]["destination"]
    assert steps[1]["egress"]["leaves_server"] is False
    assert {"type": "conduit", "title": "conduit_lookup_company"} in payload["sources"]


def test_deterministic_fallback_when_model_cannot_plan(tmp_path):
    router = FakeRouter(plan_text="I cannot format that, sorry")
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Write a haiku about servers"})
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    out = _run(db, _deps(settings, router, skills_dir=empty_skills), job_id)
    assert out["status"] == "completed"
    payload = _payload(db, job_id)
    assert payload["plan_source"] == "deterministic"
    assert [s["tool"] for s in payload["steps"]] == ["model"]
    assert payload["result"] == "agent answer"


def test_skill_step_feeds_the_model(tmp_path):
    skills_dir = _skills_dir(tmp_path)
    router = FakeRouter()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Do the test thing", "skill": "test-skill"})
    _run(db, _deps(settings, router, skills_dir=skills_dir), job_id)

    payload = _payload(db, job_id)
    assert payload["state"] == "completed"
    assert [s["tool"] for s in payload["steps"]] == ["skill", "model"]
    assert payload["steps"][0]["egress"]["leaves_server"] is False
    # The model step received the skill body as a system message.
    execution_call = router.calls[-1][1]
    system_texts = [
        m["content"] for m in execution_call["messages"] if m["role"] == "system"
    ]
    assert any("SKILL BODY" in t for t in system_texts)


def test_bridge_step_dispatches_through_allowlist(tmp_path):
    plan = json.dumps(
        {
            "steps": [
                {
                    "tool": "oc_bridge",
                    "action": "oc_status",
                    "arguments": {},
                    "why": "check the bridge",
                },
                {"tool": "model", "action": "chat", "arguments": {}, "why": "answer"},
            ]
        }
    )
    router = FakeRouter(plan_text=plan)
    bridge = FakeBridge()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Is OpenCode up?"})
    _run(db, _deps(settings, router, oc_bridge_factory=lambda: bridge), job_id)
    payload = _payload(db, job_id)
    assert payload["state"] == "completed"
    assert bridge.calls == [("oc_status", {})]
    assert payload["steps"][0]["egress"]["leaves_server"] is False
    assert "oc-bridge" in payload["steps"][0]["egress"]["destination"]


# ── Executor: failure honesty ────────────────────────────────


def test_unconfigured_conduit_fails_the_step_honestly(tmp_path):
    plan = json.dumps(
        {
            "steps": [
                {
                    "tool": "conduit",
                    "action": "conduit_lookup_company",
                    "arguments": {"ticker": "AAPL"},
                    "why": "resolve the company",
                },
                {"tool": "model", "action": "chat", "arguments": {}, "why": "answer"},
            ]
        }
    )

    def unconfigured():
        raise ValueError("CONDUIT_API_KEY not configured")

    router = FakeRouter(plan_text=plan)
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Look up AAPL"})
    with pytest.raises(Exception, match="not configured"):
        _run(db, _deps(settings, router, conduit_factory=unconfigured), job_id)

    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert "not configured" in payload["error"]
    assert payload["steps"][0]["status"] == "failed"
    assert "not configured" in payload["steps"][0]["error"]
    run = db.list_runs(job_id)[0]
    assert run["status"] == "failed"
    assert "not configured" in run["error"]


def test_unconfigured_bridge_fails_the_step_honestly(tmp_path):
    plan = json.dumps(
        {
            "steps": [
                {
                    "tool": "oc_bridge",
                    "action": "oc_status",
                    "arguments": {},
                    "why": "check the bridge",
                },
                {"tool": "model", "action": "chat", "arguments": {}, "why": "answer"},
            ]
        }
    )

    def unconfigured():
        raise ValueError("OC_BRIDGE_TOKEN not configured")

    router = FakeRouter(plan_text=plan)
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Is OpenCode up?"})
    with pytest.raises(Exception, match="not configured"):
        _run(db, _deps(settings, router, oc_bridge_factory=unconfigured), job_id)
    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert payload["steps"][0]["status"] == "failed"


def test_unknown_named_skill_fails_honestly(tmp_path):
    skills_dir = _skills_dir(tmp_path)
    router = FakeRouter()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Do it", "skill": "no-such-skill"})
    with pytest.raises(Exception, match="no-such-skill"):
        _run(db, _deps(settings, router, skills_dir=skills_dir), job_id)
    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert payload["steps"][0]["tool"] == "skill"
    assert payload["steps"][0]["status"] == "failed"


# ── Executor: bounds ─────────────────────────────────────────


def test_step_cap_clamps_the_plan(tmp_path):
    steps = [
        {"tool": "oc_bridge", "action": "oc_status", "arguments": {}, "why": "1"},
        {
            "tool": "conduit",
            "action": "conduit_lookup_company",
            "arguments": {"ticker": "AAPL"},
            "why": "2",
        },
        {"tool": "oc_bridge", "action": "opencode_health", "arguments": {}, "why": "3"},
        {"tool": "model", "action": "chat", "arguments": {}, "why": "4"},
    ]
    router = FakeRouter(plan_text=json.dumps({"steps": steps}))
    settings = _settings(tmp_path, max_steps=2)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Do many things"})
    _run(
        db,
        _deps(
            settings,
            router,
            oc_bridge_factory=lambda: FakeBridge(),
            conduit_factory=lambda: FakeConduit(),
        ),
        job_id,
    )
    payload = _payload(db, job_id)
    assert payload["plan_clamped"] is True
    assert len(payload["steps"]) == 2


def test_total_timeout_stops_before_the_first_step(tmp_path):
    router = FakeRouter()
    settings = _settings(tmp_path, total_timeout_s=0.0)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Anything"})
    out = _run(db, _deps(settings, router), job_id)
    assert out["summary"].startswith("Stopped:")
    payload = _payload(db, job_id)
    assert payload["state"] == "stopped"
    assert "time limit" in payload["stop_reason"]
    assert payload["steps"] == []


def test_step_timeout_fails_the_step(tmp_path):
    router = SlowRouter()
    settings = _settings(tmp_path, step_timeout_s=0.05)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Slow task"})
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    with pytest.raises(Exception, match="timed out"):
        _run(db, _deps(settings, router, skills_dir=empty_skills), job_id)
    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert "timed out" in payload["steps"][0]["error"]


def test_cancel_requested_before_start_stops_cleanly(tmp_path):
    router = FakeRouter()
    settings = _settings(tmp_path)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Anything", "cancel_requested": True})
    out = _run(db, _deps(settings, router), job_id)
    assert out["summary"] == "Stopped: cancelled by user"
    payload = _payload(db, job_id)
    assert payload["state"] == "stopped"
    assert payload["steps"] == []
    assert router.calls == []  # not even the planner ran


# ── Executor: cancel while a step runs ───────────────────────


def test_cancel_during_a_step_stops_it_promptly(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "CANCEL_POLL_INTERVAL_S", 0.02)
    settings = _settings(tmp_path, step_timeout_s=30.0)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Long task"})
    router = CancellingRouter(db, job_id)
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    started = time.monotonic()
    out = _run(db, _deps(settings, router, skills_dir=empty_skills), job_id)
    elapsed = time.monotonic() - started
    # The step hangs for 30s and the step timeout is 30s; the
    # cancel flag interrupts it within a poll interval instead.
    assert elapsed < 5
    assert out["summary"] == "Stopped: cancelled by user"
    payload = _payload(db, job_id)
    assert payload["state"] == "stopped"
    assert payload["stop_reason"] == "cancelled by user"
    assert payload["steps"][0]["status"] == "stopped"
    assert payload["steps"][0]["error"] == "cancelled by user"


def test_hanging_step_without_cancel_still_times_out(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "CANCEL_POLL_INTERVAL_S", 0.02)
    router = SlowRouter()
    settings = _settings(tmp_path, step_timeout_s=0.3)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Slow task"})
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    started = time.monotonic()
    with pytest.raises(Exception, match="timed out"):
        _run(db, _deps(settings, router, skills_dir=empty_skills), job_id)
    elapsed = time.monotonic() - started
    # The watcher must not turn a real timeout into a stop: the
    # step ran to its own deadline, not to a poll tick.
    assert elapsed >= 0.25
    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert payload["steps"][0]["status"] == "failed"
    assert "timed out" in payload["steps"][0]["error"]


def test_step_error_during_cancel_watch_still_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "CANCEL_POLL_INTERVAL_S", 0.02)
    router = ExplodingRouter()
    settings = _settings(tmp_path, step_timeout_s=30.0)
    db = Database(settings.db_path)
    job_id = _make_job(db, {"task": "Exploding task"})
    empty_skills = tmp_path / "no-skills"
    empty_skills.mkdir()
    with pytest.raises(Exception, match="router exploded"):
        _run(db, _deps(settings, router, skills_dir=empty_skills), job_id)
    payload = _payload(db, job_id)
    assert payload["state"] == "failed"
    assert payload["steps"][0]["status"] == "failed"
    assert "router exploded" in payload["steps"][0]["error"]


# ── HTTP surface ─────────────────────────────────────────────


def _poll_task(client, task_id: str, headers: dict, deadline_s: float = 20.0) -> dict:
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        r = client.get(f"/v1/agent/tasks/{task_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("completed", "failed", "stopped"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not reach a terminal state")


def test_agent_endpoints_require_auth(client):
    assert client.post("/v1/agent/tasks", json={"task": "x"}).status_code == 401
    assert client.get("/v1/agent/tasks").status_code == 401
    assert client.get("/v1/agent/tasks/abc").status_code == 401
    assert client.post("/v1/agent/tasks/abc/cancel").status_code == 401


def test_agent_task_happy_path_over_http(client):
    r = client.post(
        "/v1/agent/tasks", json={"task": "Say hello to the test"}, headers=OWNER
    )
    assert r.status_code == 201
    task_id = r.json()["id"]
    body = _poll_task(client, task_id, OWNER)
    assert body["status"] == "completed"
    assert "stub-echo" in body["result"]
    assert body["steps"], "the step log must not be empty"
    for step in body["steps"]:
        assert step["status"] == "completed"
        assert "egress" in step  # every step names its egress
    listed = client.get("/v1/agent/tasks", headers=OWNER).json()["tasks"]
    assert any(t["id"] == task_id for t in listed)


def test_agent_task_owner_isolation(client):
    r = client.post("/v1/agent/tasks", json={"task": "Private task"}, headers=OWNER)
    task_id = r.json()["id"]
    _poll_task(client, task_id, OWNER)
    assert client.get(f"/v1/agent/tasks/{task_id}", headers=OTHER).status_code == 404
    assert (
        client.post(f"/v1/agent/tasks/{task_id}/cancel", headers=OTHER).status_code
        == 404
    )
    other_list = client.get("/v1/agent/tasks", headers=OTHER).json()["tasks"]
    assert all(t["id"] != task_id for t in other_list)


def test_agent_task_unknown_skill_fails_over_http(client):
    r = client.post(
        "/v1/agent/tasks",
        json={"task": "Do the thing", "skill": "definitely-not-a-skill"},
        headers=OWNER,
    )
    assert r.status_code == 201
    body = _poll_task(client, r.json()["id"], OWNER)
    assert body["status"] == "failed"
    assert "definitely-not-a-skill" in (body["error"] or "")


def test_agent_task_cancel_after_completion_is_conflict(client):
    r = client.post("/v1/agent/tasks", json={"task": "Quick task"}, headers=OWNER)
    task_id = r.json()["id"]
    _poll_task(client, task_id, OWNER)
    assert (
        client.post(f"/v1/agent/tasks/{task_id}/cancel", headers=OWNER).status_code
        == 409
    )


def test_agent_task_create_validates_body(client):
    assert (
        client.post("/v1/agent/tasks", json={"task": ""}, headers=OWNER).status_code
        == 422
    )
    assert client.post("/v1/agent/tasks", json={}, headers=OWNER).status_code == 422


def test_jobs_api_rejects_agent_task_without_task(client):
    r = client.post(
        "/v1/jobs",
        json={"name": "bad", "payload": {"type": "agent_task"}},
    )
    assert r.status_code == 422
