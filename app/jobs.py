# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Job service: CRUD over job definitions plus scheduling bookkeeping.

Phase 3 brings the jobs table alive: payloads are validated against the
typed job kinds (``scheduler.validate_job_payload``), cron expressions
are checked, and ``next_run_at`` is computed on create, on cron change,
and after every run. Execution itself lives in ``app/scheduler.py`` and
is driven by the deterministic planner — never called from here.
"""

from __future__ import annotations

import json

from . import scheduler as scheduler_mod
from .db import Database
from .schemas import Job, JobCreate, JobUpdate


class JobNotFoundError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"unknown job '{job_id}'")


class JobService:
    def __init__(self, db: Database):
        self.db = db

    def create(self, data: JobCreate) -> Job:
        payload = scheduler_mod.validate_job_payload(dict(data.payload or {}))
        scheduler_mod.validate_cron(data.cron)
        row = self.db.create_job(data.name, data.cron, payload)
        self.db.update_job(
            row["id"], next_run_at=scheduler_mod.compute_next_run(data.cron)
        )
        return self.get(row["id"])

    def list(self) -> list[Job]:
        return [Job(**row) for row in self.db.list_jobs()]

    def get(self, job_id: str) -> Job:
        row = self.db.get_job(job_id)
        if row is None:
            raise JobNotFoundError(job_id)
        return Job(**row)

    def update(self, job_id: str, data: JobUpdate) -> Job:
        fields = data.model_dump(exclude_unset=True, exclude_none=False)
        payload = fields.pop("payload", None)
        if payload is not None:
            validated = scheduler_mod.validate_job_payload(dict(payload))
            fields["payload_json"] = json.dumps(validated)
        if "cron" in fields:
            scheduler_mod.validate_cron(fields["cron"])
            fields["next_run_at"] = scheduler_mod.compute_next_run(fields["cron"])
        row = self.db.update_job(job_id, **fields)
        if row is None:
            raise JobNotFoundError(job_id)
        return Job(**row)

    def delete(self, job_id: str) -> None:
        if not self.db.delete_job(job_id):
            raise JobNotFoundError(job_id)
