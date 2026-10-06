# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Jobs CRUD: typed payloads (Phase 3) — execution is tested in test_scheduler.py."""


def test_job_crud_roundtrip(client):
    created = client.post(
        "/v1/jobs",
        json={
            "name": "morning-briefing",
            "cron": "0 7 * * *",
            "payload": {"type": "briefing", "query": "project atlas"},
        },
    )
    assert created.status_code == 201
    job = created.json()
    assert job["name"] == "morning-briefing"
    assert job["status"] == "pending"
    assert job["next_run_at"] is not None  # cron -> next run computed
    job_id = job["id"]

    got = client.get(f"/v1/jobs/{job_id}")
    assert got.status_code == 200
    assert got.json()["payload"]["type"] == "briefing"

    listed = client.get("/v1/jobs").json()["jobs"]
    assert any(j["id"] == job_id for j in listed)

    patched = client.patch(f"/v1/jobs/{job_id}", json={"status": "paused"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "paused"

    deleted = client.delete(f"/v1/jobs/{job_id}")
    assert deleted.status_code == 204
    assert client.get(f"/v1/jobs/{job_id}").status_code == 404


def test_job_not_found(client):
    assert client.get("/v1/jobs/doesnotexist").status_code == 404
    assert client.delete("/v1/jobs/doesnotexist").status_code == 404


def test_job_create_validates_name(client):
    r = client.post("/v1/jobs", json={"name": ""})
    assert r.status_code == 422
