# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Job service: CRUD over job definitions.

Deliberately no execution here — running jobs is the Phase 3 proactive
engine. Phase 1 stores definitions so routines can be authored early.
"""

from __future__ import annotations

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
        return Job(**self.db.create_job(data.name, data.cron, data.payload))

    def list(self) -> list[Job]:
        return [Job(**row) for row in self.db.list_jobs()]

    def get(self, job_id: str) -> Job:
        row = self.db.get_job(job_id)
        if row is None:
            raise JobNotFoundError(job_id)
        return Job(**row)

    def update(self, job_id: str, data: JobUpdate) -> Job:
        row = self.db.update_job(
            job_id, **data.model_dump(exclude_unset=True, exclude_none=False)
        )
        if row is None:
            raise JobNotFoundError(job_id)
        return Job(**row)

    def delete(self, job_id: str) -> None:
        if not self.db.delete_job(job_id):
            raise JobNotFoundError(job_id)
