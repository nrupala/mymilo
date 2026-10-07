# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Health and model listing."""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["backends"] == {"stub": True}


def test_health_backend_down_reports_false(client_no_transport):
    r = client_no_transport.get("/health")
    assert r.status_code == 200
    assert r.json()["backends"] == {"stub": False}


def test_models_list(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert [m["id"] for m in body["data"]] == ["auto", "stub"]


def test_index_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "MyMilo" in r.text
    assert "<form" in r.text


def test_jobs_page_renders(client):
    r = client.get("/jobs")
    assert r.status_code == 200
    assert "Routines" in r.text
