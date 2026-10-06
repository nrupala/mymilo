# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Scheduler: cron-driven job execution.

The jobs table (Phase 1) comes alive here:

- ``next_run_at`` is computed from the job's cron expression on create,
  update, and after every run.
- A background tick loop (started in the app lifespan when
  ``[scheduler] enabled = true``) scans for due jobs every
  ``tick_seconds`` and emits ``JOB_DUE`` on the event bus.
- The deterministic planner routes ``JOB_DUE`` to the ``job.execute``
  action — the scheduler never executes work itself.

Job payloads are typed. Phase 3 ships two job types:

- ``briefing`` — retrieve documents for a query, ask the model router for
  a concise digest, record it as a suggestion. The LLM *drafts* the text;
  the planner decided the briefing runs.
- ``reminder`` — a plain-text nudge recorded as a suggestion. No model
  call involved.

Unknown job types are rejected at write time (422), never silently
skipped at run time.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from . import cron as cron_mod
from .rag import build_rag_messages, verify_citations

JOB_TYPES = ("briefing", "reminder")


class JobDefinitionError(ValueError):
    """Raised when a job payload or cron expression is invalid."""


BRIEFING_SYSTEM_PROMPT = (
    "You are MyMilo, Nrupal's proactive briefing assistant. "
    "Write a concise briefing from the retrieved context below. "
    "Lead with what needs attention, keep it scannable, and never "
    "invent facts that are not in the context. If the context is thin, "
    "say so plainly."
)


# ----------------------------------------------------------------------
# Payload validation and next-run computation
# ----------------------------------------------------------------------
def validate_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a job payload; raise JobDefinitionError describing the problem."""
    if not isinstance(payload, dict):
        raise JobDefinitionError("job payload must be a JSON object")
    job_type = payload.get("type")
    if job_type not in JOB_TYPES:
        raise JobDefinitionError(
            f"job type must be one of {JOB_TYPES}, got {job_type!r}"
        )
    if job_type == "reminder" and not payload.get("text"):
        raise JobDefinitionError("reminder jobs require a 'text' field")
    if job_type == "briefing":
        payload.setdefault("query", "recent documents")
        payload.setdefault("top_k", 5)
    return payload


def validate_cron(cron_expr: str | None) -> None:
    """Raise JobDefinitionError if the cron expression is invalid."""
    if cron_expr:
        try:
            cron_mod.parse_cron(cron_expr)
        except cron_mod.CronError as exc:
            raise JobDefinitionError(str(exc)) from exc


def compute_next_run(
    cron_expr: str | None, after: datetime | None = None
) -> str | None:
    """Return the next run time as an ISO UTC string, or None if no cron."""
    if not cron_expr:
        return None
    when = cron_mod.next_run(cron_expr, after=after)
    return when.replace(tzinfo=UTC).isoformat()


# ----------------------------------------------------------------------
# Job execution (registered as the ``job.execute`` action)
# ----------------------------------------------------------------------
def make_job_executor(deps: dict[str, Any]):
    """Build the ``job.execute`` action handler with app dependencies.

    ``deps`` carries the live collaborators so tests can substitute
    stubs without touching the registry wiring:

    - ``deps["docs"]`` — DocumentService (async ``search``).
    - ``deps["router"]`` — ModelRouter (async ``chat_completion``).
    - ``deps["settings"]`` — Settings (default model name).
    - ``deps["bus"]`` — EventBus (JOB_COMPLETED / JOB_FAILED emission).
    """

    async def execute_job(
        db: Any,
        event: dict[str, Any] | None = None,
        job_id: str | None = None,
        triggered_by: str = "schedule",
    ) -> dict[str, Any]:
        if job_id is None and event is not None:
            job_id = event.get("job_id")
        if job_id is None:
            raise ValueError("job.execute requires a job_id")
        job = db.get_job(job_id)
        if job is None:
            raise KeyError(f"job {job_id} not found")

        run_id = db.create_run(job_id, triggered_by=triggered_by)
        payload = job["payload"]
        job_type = payload.get("type")
        try:
            if job_type == "briefing":
                summary = await _run_briefing(db, job, payload, deps)
            elif job_type == "reminder":
                summary = _run_reminder(payload)
            else:
                raise ValueError(f"unknown job type {job_type!r}")
            db.finish_run(run_id, "completed", result_summary=summary)
            finished = datetime.now(UTC).isoformat()
            db.update_job(
                job_id,
                last_run_at=finished,
                next_run_at=compute_next_run(job["cron"]),
            )
            bus = deps.get("bus")
            if bus is not None:
                await bus.emit_async(
                    "JOB_COMPLETED",
                    {
                        "db": db,
                        "job_id": job_id,
                        "job_name": job["name"],
                        "job_type": job_type,
                        "run_id": run_id,
                        "result_summary": summary,
                    },
                )
            return {"run_id": run_id, "status": "completed", "summary": summary}
        except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
            db.finish_run(run_id, "failed", error=f"{type(exc).__name__}: {exc}")
            bus = deps.get("bus")
            if bus is not None:
                await bus.emit_async(
                    "JOB_FAILED",
                    {
                        "db": db,
                        "job_id": job_id,
                        "run_id": run_id,
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                )
            raise

    return execute_job


def _run_reminder(payload: dict[str, Any]) -> str:
    text = payload.get("text", "")
    if not text:
        raise ValueError("reminder jobs require a 'text' field")
    return text


async def _run_briefing(
    db: Any,
    job: dict[str, Any],
    payload: dict[str, Any],
    deps: dict[str, Any],
) -> str:
    query = payload.get("query", "recent documents")
    top_k = int(payload.get("top_k", 5))
    model = payload.get("model") or deps["settings"].models[0].name

    retrieved = await deps["docs"].search(query, top_k=top_k)
    if not retrieved:
        return (
            f"Briefing '{job['name']}': no documents matched "
            f"{query!r} — nothing to summarize."
        )

    messages = build_rag_messages(
        [
            {"role": "system", "content": BRIEFING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Briefing topic: {job['name']}\n\n"
                "Write the briefing. Cite sources as [S1], [S2], ...",
            },
        ],
        retrieved,
    )
    data = await deps["router"].chat_completion(model, {"messages": messages})
    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    check = verify_citations(answer, retrieved)
    if not check["ok"]:
        answer += " (citation check flagged unresolved references)"
    return answer


# ----------------------------------------------------------------------
# Tick loop
# ----------------------------------------------------------------------
async def run_job_now(app: Any, job_id: str, triggered_by: str = "manual") -> dict:
    """Execute one job immediately through the action registry."""
    return await app.state.actions.execute_async(
        app.state.db, "job.execute", job_id=job_id, triggered_by=triggered_by
    )


async def tick(app: Any) -> int:
    """One scheduler pass: emit JOB_DUE for every due job.

    Returns the number of jobs found due. Each emission runs the planner
    synchronously (awaited), so when tick() returns the jobs have been
    executed and rescheduled.
    """
    db = app.state.db
    now_iso = datetime.now(UTC).isoformat()
    due = db.get_due_jobs(now_iso)
    for job in due:
        await app.state.bus.emit_async(
            "JOB_DUE",
            {"db": db, "job_id": job["id"], "job_name": job["name"]},
        )
    return len(due)


async def scheduler_loop(app: Any) -> None:
    """Background task: tick every ``tick_seconds`` until cancelled."""
    interval = app.state.settings.scheduler.tick_seconds
    while True:
        await asyncio.sleep(interval)
        try:
            await tick(app)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — the loop must never die
            continue
