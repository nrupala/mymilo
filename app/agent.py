# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Agent loop (v0.47.0): user tasks executed end to end.

Until now Milo could only advise in chat and run single-shot
background prompts. The agent loop closes that gap: a task the user
submits to ``POST /v1/agent/tasks`` becomes a job (payload type
``agent_task`` on the existing jobs engine — no parallel store),
a planner turns it into steps, and an executor runs the steps in
the background against an ALLOWLISTED tool registry:

- ``model``   — chat through the existing model router.
- ``skill``   — activate a skill from the skills module; its
  instructions feed the following model steps.
- ``oc_bridge`` — dispatch to OpenCode via the oc-bridge client
  (``app/integrations/opencode.py``); only the bridge's own ten
  tool names are callable.
- ``conduit`` — Conduit's SEC EDGAR tools via the existing
  integration; only the names in its TOOL_NAME_MAP are callable.

Honesty rules, enforced here rather than promised:

- Every step records what it did, which tool it used, its status,
  its real error on failure, and its EGRESS — whether the step's
  data left this server, and the destination's name when it did
  (the data-egress law: no silent egress, ever).
- Bounds come from ``[agent]`` config: a max step count, a
  per-step timeout, and a total wall-clock cap. Hitting a cap ends
  the task in state ``stopped`` with the reason recorded — never
  a hang, never a fake success.
- An unconfigured integration (no OC_BRIDGE_TOKEN, no
  CONDUIT_API_KEY) fails its step with a plain "not configured"
  error. Nothing is faked or silently skipped.
- The caller can cancel cooperatively: the executor checks the
  job row before every step and stops if cancellation was asked.

Planning: the model is asked for a JSON plan restricted to the
registry (the model proposes; the registry decides what may run —
every proposed step is validated, unknown tools are dropped). If
the model is unreachable or its plan does not parse, a
deterministic fallback plan runs instead (skill step when a skill
applies, then one model step), and the task record says which
source planned it (``plan_source``).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .integrations.conduit import TOOL_NAME_MAP, ConduitClient, ConduitError
from .integrations.opencode import BRIDGE_TOOLS, OcBridgeClient
from .orchestrate import route_for_complexity
from .skills import get_skill_by_name, match_skill, resolve_skills_dir

BASE_DIR = Path(__file__).resolve().parent.parent

TERMINAL_STATES = ("completed", "failed", "stopped")
MAX_SUMMARY_CHARS = 4000
MAX_CONTEXT_CHARS = 2000

# Registry vocabulary: tool -> allowed actions. For oc_bridge the
# actions are the bridge's tool names; for conduit they are the
# MyMilo-side conduit_* names (mapped upstream at call time).
TOOL_ACTIONS: dict[str, tuple[str, ...]] = {
    "model": ("chat",),
    "skill": ("activate",),
    "oc_bridge": BRIDGE_TOOLS,
    "conduit": tuple(TOOL_NAME_MAP),
}

_PLANNER_SYSTEM = (
    "You are MyMilo's task planner. Break the user's task into a "
    "short sequence of steps using ONLY these tools:\n"
    "- model (action: chat) — reason or write the final answer.\n"
    '- skill (action: activate, arguments: {"name": <skill name>}) '
    "— load a skill's instructions before answering.\n"
    "- oc_bridge (actions: opencode_health, opencode_list_sessions, "
    "opencode_get_session, opencode_mcp_status, oc_status, "
    "oc_send_prompt, oc_job_status, oc_job_result, oc_run_command, "
    "oc_request_deploy) — coding work via OpenCode on this server.\n"
    "- conduit (actions: the conduit_* SEC EDGAR tools, e.g. "
    "conduit_lookup_company, conduit_get_company_facts) — company "
    "filings and fundamentals.\n"
    "Reply with ONLY a JSON object, no prose, no code fence:\n"
    '{"steps": [{"tool": "...", "action": "...", '
    '"arguments": {...}, "why": "one short line"}]}\n'
    "End with a model chat step that produces the final answer "
    "from the earlier steps' results. Keep the plan as short as "
    "the task allows."
)


class AgentStepError(RuntimeError):
    """A step failed; the message is the honest, user-safe reason."""


@dataclass
class StepOutcome:
    summary: str
    egress: dict[str, Any]
    sources: list[dict] = field(default_factory=list)
    text: str = ""  # full text (model answers thread into the result)
    data: Any = None  # structured payload (skill content threads on)


# ----------------------------------------------------------------------
# Egress accounting (data-egress law: named, never silent)
# ----------------------------------------------------------------------
def egress_for_route(settings: Any, route_name: str) -> dict[str, Any]:
    """Where a model step's data goes, decided by the route's URL."""
    route = settings.route_for(route_name)
    if route is None:
        return {
            "leaves_server": False,
            "destination": f"model route '{route_name}' on this server",
        }
    host = urlparse(route.base_url).hostname or ""
    if host in ("127.0.0.1", "localhost", "::1"):
        return {
            "leaves_server": False,
            "destination": f"model route '{route_name}' on this server",
        }
    return {
        "leaves_server": True,
        "destination": f"model route '{route_name}' at {host} (outside this server)",
    }


def _egress_local(destination: str) -> dict[str, Any]:
    return {"leaves_server": False, "destination": destination}


# ----------------------------------------------------------------------
# Planning
# ----------------------------------------------------------------------
def _validate_step(raw: Any) -> dict[str, Any] | None:
    """Normalize one proposed step, or None if it is not callable."""
    if not isinstance(raw, dict):
        return None
    tool = raw.get("tool")
    action = raw.get("action")
    if tool not in TOOL_ACTIONS or action not in TOOL_ACTIONS[tool]:
        return None
    arguments = raw.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}
    return {
        "tool": tool,
        "action": action,
        "arguments": arguments,
        "why": str(raw.get("why", ""))[:200],
    }


def _extract_plan(text: str) -> list[dict[str, Any]] | None:
    """Pull the first JSON object with a steps list out of model text."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("steps"), list):
            return obj["steps"]
    return None


def _fallback_steps(
    task: str, skill_name: str | None, skills_dir: Any
) -> list[dict[str, Any]]:
    """Deterministic plan: skill (when one applies) + one model step."""
    steps: list[dict[str, Any]] = []
    name = skill_name
    if not name and skills_dir is not None:
        matched = match_skill(task, skills_dir)
        if matched:
            name = matched["name"]
    if name:
        steps.append(
            {
                "tool": "skill",
                "action": "activate",
                "arguments": {"name": name},
                "why": "Load the skill's instructions for this task",
            }
        )
    steps.append(
        {
            "tool": "model",
            "action": "chat",
            "arguments": {},
            "why": "Carry out the task and produce the answer",
        }
    )
    return steps


async def plan_steps(
    router: Any,
    settings: Any,
    task: str,
    skill_name: str | None,
    skills_dir: Any,
) -> tuple[list[dict[str, Any]], str]:
    """Plan a task: model-proposed when possible, else deterministic.

    Returns (steps, plan_source) where plan_source is "model" or
    "deterministic" — recorded on the task either way.
    """
    fallback = _fallback_steps(task, skill_name, skills_dir)
    model = route_for_complexity(task, settings, default=settings.default_model)
    try:
        data = await asyncio.wait_for(
            router.chat_completion(
                model,
                {
                    "messages": [
                        {"role": "system", "content": _PLANNER_SYSTEM},
                        {"role": "user", "content": f"Task: {task}"},
                    ]
                },
            ),
            timeout=60.0,
        )
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        raw_steps = _extract_plan(text)
    except Exception:  # noqa: BLE001 — planning must degrade, not die
        raw_steps = None
    if not raw_steps:
        return fallback, "deterministic"

    steps = [s for s in (_validate_step(r) for r in raw_steps) if s is not None]
    if not steps:
        return fallback, "deterministic"
    # An explicitly requested skill is force-activated first, the
    # same rule chat applies (v0.41.0) — a plan may not drop it.
    if skill_name and not any(
        s["tool"] == "skill" and s["arguments"].get("name") == skill_name for s in steps
    ):
        steps.insert(
            0,
            {
                "tool": "skill",
                "action": "activate",
                "arguments": {"name": skill_name},
                "why": "Load the skill's instructions for this task",
            },
        )
    # The task's answer comes from a model step: if the plan gathers
    # with tools but never synthesizes, append the synthesis step.
    if steps[-1]["tool"] != "model":
        steps.append(
            {
                "tool": "model",
                "action": "chat",
                "arguments": {},
                "why": "Produce the final answer from the step results",
            }
        )
    return steps, "model"


# ----------------------------------------------------------------------
# Task state (persisted in the job payload — the jobs store is the
# record; there is no parallel agent store)
# ----------------------------------------------------------------------
class _TaskState:
    def __init__(self, db: Any, job_id: str, payload: dict[str, Any]):
        self.db = db
        self.job_id = job_id
        self.payload = payload

    def save(self) -> None:
        self.db.update_job(self.job_id, payload_json=json.dumps(self.payload))

    def set(self, **fields: Any) -> None:
        self.payload.update(fields)
        self.save()

    def fresh_payload(self) -> dict[str, Any]:
        row = self.db.get_job(self.job_id)
        return (row or {}).get("payload") or {}

    def cancel_requested(self) -> bool:
        return bool(self.fresh_payload().get("cancel_requested"))


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _summarize(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, indent=2, default=str)
    return text[:MAX_SUMMARY_CHARS]


# ----------------------------------------------------------------------
# Step runners (one per registry tool)
# ----------------------------------------------------------------------
async def _run_model_step(
    step: dict[str, Any],
    task: str,
    payload: dict[str, Any],
    context: list[str],
    skill_content: str | None,
    deps: dict[str, Any],
) -> StepOutcome:
    settings = deps["settings"]
    router = deps["router"]
    model = (
        step["arguments"].get("model")
        or payload.get("model")
        or route_for_complexity(task, settings, default=settings.default_model)
    )
    messages: list[dict[str, str]] = []
    if skill_content:
        messages.append({"role": "system", "content": skill_content})
    messages.append(
        {
            "role": "system",
            "content": (
                "You are MyMilo carrying out a task for your user. "
                "Use the step results provided below; be accurate "
                "and concise; never invent facts that are not in "
                "them or in your own knowledge — say which."
            ),
        }
    )
    user = task
    if context:
        user += "\n\nResults from earlier steps:\n" + "\n\n".join(context)
    messages.append({"role": "user", "content": user})
    data = await router.chat_completion(model, {"messages": messages})
    text = (
        data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    ).strip()
    sources = data.get("sources")
    return StepOutcome(
        summary=_summarize(text),
        egress=egress_for_route(settings, model),
        sources=sources if isinstance(sources, list) else [],
        text=text,
    )


async def _run_skill_step(
    step: dict[str, Any],
    task: str,
    payload: dict[str, Any],
    skills_dir: Any,
) -> StepOutcome:
    name = step["arguments"].get("name") or payload.get("skill")
    skill = None
    if skills_dir is not None:
        if name:
            # A named skill resolves by name only: silently swapping
            # in a different, trigger-matched skill would not be the
            # work the user asked for.
            skill = get_skill_by_name(str(name), skills_dir)
        else:
            skill = match_skill(task, skills_dir)
    if skill is None:
        raise AgentStepError(
            f"skill '{name}' was not found on this server"
            if name
            else "no skill matched this task"
        )
    return StepOutcome(
        summary=_summarize(
            f"Skill '{skill['name']}' activated: {skill.get('description', '')}"
        ),
        egress=_egress_local("skill instructions stored on this server"),
        sources=[{"type": "skill", "title": skill["name"]}],
        text=skill["name"],
        data=skill["content"],
    )


async def _run_bridge_step(
    step: dict[str, Any], deps: dict[str, Any], step_timeout_s: float
) -> StepOutcome:
    factory = deps.get("oc_bridge_factory")
    try:
        client = factory() if factory else OcBridgeClient(timeout_s=step_timeout_s)
    except ValueError as e:
        raise AgentStepError(f"oc-bridge is not configured on this server ({e})") from e
    result = await client.call_tool(step["action"], step["arguments"])
    return StepOutcome(
        summary=_summarize(result),
        egress=_egress_local("oc-bridge on this server (OpenCode)"),
        text=_summarize(result),
        data=result,
    )


async def _run_conduit_step(step: dict[str, Any], deps: dict[str, Any]) -> StepOutcome:
    factory = deps.get("conduit_factory")
    try:
        client = factory() if factory else ConduitClient()
    except ValueError as e:
        raise AgentStepError(f"Conduit is not configured on this server ({e})") from e
    upstream = TOOL_NAME_MAP[step["action"]]
    try:
        result = await client.call_tool(upstream, step["arguments"])
    except ConduitError as e:
        raise AgentStepError(str(e)) from e
    return StepOutcome(
        summary=_summarize(result),
        egress={
            "leaves_server": True,
            "destination": (
                "Conduit — Filings & Fundamentals (SEC EDGAR), "
                "a service outside this server"
            ),
        },
        sources=[{"type": "conduit", "title": step["action"]}],
        text=_summarize(result),
        data=result,
    )


# ----------------------------------------------------------------------
# Executor (registered through the jobs engine as agent_task)
# ----------------------------------------------------------------------
async def run_agent_task(
    db: Any, job: dict[str, Any], payload: dict[str, Any], deps: dict[str, Any]
) -> str:
    """Execute one agent task job; returns the run summary.

    Raises on step failure so the jobs engine records the run as
    failed with the real error — the task record carries the same
    error, so neither layer can claim a success that did not happen.
    """
    settings = deps["settings"]
    cfg = settings.agent
    skills_dir = deps.get("skills_dir") or resolve_skills_dir(
        settings.skills.dir, BASE_DIR
    )
    state = _TaskState(db, job["id"], dict(payload))
    task = str(payload.get("task", "")).strip()
    if not task:
        raise ValueError("agent_task payload requires a 'task' field")

    if state.cancel_requested() or payload.get("state") == "stopped":
        state.set(state="stopped", stop_reason="cancelled by user")
        return "Stopped: cancelled by user"

    state.set(state="running", steps=[])
    started = time.monotonic()

    steps, plan_source = await plan_steps(
        deps["router"], settings, task, payload.get("skill"), skills_dir
    )
    clamped = len(steps) > cfg.max_steps
    if clamped:
        steps = steps[: cfg.max_steps]
    state.set(plan_source=plan_source, plan_clamped=clamped)

    context: list[str] = []
    skill_content: str | None = None
    sources: list[dict] = []
    result_text = ""

    for index, step in enumerate(steps):
        if state.cancel_requested():
            state.set(state="stopped", stop_reason="cancelled by user")
            return "Stopped: cancelled by user"
        if time.monotonic() - started >= cfg.total_timeout_s:
            reason = f"the task time limit ({cfg.total_timeout_s:g}s) was reached"
            state.set(state="stopped", stop_reason=reason)
            return f"Stopped: {reason}"

        record: dict[str, Any] = {
            "index": index,
            "tool": step["tool"],
            "action": step["action"],
            "why": step.get("why", ""),
            "status": "running",
            "started_at": _now(),
        }
        state.payload.setdefault("steps", []).append(record)
        state.save()
        step_started = time.monotonic()
        try:
            if step["tool"] == "model":
                outcome = await asyncio.wait_for(
                    _run_model_step(step, task, payload, context, skill_content, deps),
                    timeout=cfg.step_timeout_s,
                )
            elif step["tool"] == "skill":
                outcome = await asyncio.wait_for(
                    _run_skill_step(step, task, payload, skills_dir),
                    timeout=cfg.step_timeout_s,
                )
            elif step["tool"] == "oc_bridge":
                outcome = await asyncio.wait_for(
                    _run_bridge_step(step, deps, cfg.step_timeout_s),
                    timeout=cfg.step_timeout_s,
                )
            else:  # conduit — the registry is closed; no other tool exists
                outcome = await asyncio.wait_for(
                    _run_conduit_step(step, deps),
                    timeout=cfg.step_timeout_s,
                )
        except TimeoutError:
            error = f"step timed out after {cfg.step_timeout_s:g}s"
            record.update(
                status="failed",
                error=error,
                finished_at=_now(),
                duration_s=round(time.monotonic() - step_started, 3),
            )
            state.set(state="failed", error=error)
            raise AgentStepError(f"step {index} ({step['tool']}): {error}") from None
        except Exception as exc:  # noqa: BLE001 — recorded verbatim, then raised
            error = f"{type(exc).__name__}: {exc}"
            record.update(
                status="failed",
                error=error,
                finished_at=_now(),
                duration_s=round(time.monotonic() - step_started, 3),
            )
            state.set(state="failed", error=error)
            raise

        record.update(
            status="completed",
            egress=outcome.egress,
            result_summary=outcome.summary,
            finished_at=_now(),
            duration_s=round(time.monotonic() - step_started, 3),
        )
        state.save()
        for src in outcome.sources:
            if src not in sources:
                sources.append(src)
        if step["tool"] == "skill" and isinstance(outcome.data, str):
            skill_content = outcome.data
        if step["tool"] == "model":
            result_text = outcome.text
        label = f"[{step['tool']}:{step['action']}]"
        context.append(f"{label} {outcome.summary[:MAX_CONTEXT_CHARS]}")

    if not result_text and context:
        result_text = context[-1]
    state.set(
        state="completed",
        result=result_text,
        sources=sources,
        error=None,
    )
    _append_to_session(deps, payload, task, result_text)
    return result_text or "Task completed."


def _append_to_session(
    deps: dict[str, Any], payload: dict[str, Any], task: str, result: str
) -> None:
    """Land the task + result in the caller's chat session, if one
    was named — the same "results land in chat" contract the
    background-task path follows. Best-effort by design: a session
    that is not the owner's is never written to."""
    memory = deps.get("memory")
    session_id = payload.get("session_id")
    owner = payload.get("owner", "")
    if memory is None or not session_id or not result:
        return
    try:
        ids = [s["id"] for s in memory.list_sessions(owner, limit=1000)]
        if session_id not in ids:
            return
        memory.add_message(session_id, "user", task)
        memory.add_message(session_id, "assistant", result)
    except Exception:  # noqa: BLE001 — chat landing must not fail the task
        pass
