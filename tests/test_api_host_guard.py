# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""v0.34.0: API-host guard — native clients use mymilo-api.aimlds.org
(no browser Access app); on that host only /v1/* exists and every
request must carry a valid device token."""

API_HOST = {"host": "mymilo-api.aimlds.org"}


def test_api_host_blocks_non_api_paths(client):
    r = client.get("/", headers=API_HOST)
    assert r.status_code == 404


def test_api_host_requires_auth_for_api(client):
    r = client.get("/v1/client/config", headers=API_HOST)
    assert r.status_code == 401


def test_api_host_rejects_bad_token(client):
    r = client.get(
        "/v1/client/config",
        headers={**API_HOST, "authorization": "Bearer milo_bogus"},
    )
    assert r.status_code == 401


def test_api_host_accepts_valid_token(client):
    # Register directly against the app's device store.
    from app.main import create_app  # noqa: F401  (import sanity)

    app = client.app
    device_id, token = app.state.devices.register(
        "guard@example.com", name="t", platform="android"
    )
    r = client.get(
        "/v1/client/config",
        headers={**API_HOST, "authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    app.state.devices.revoke("guard@example.com", device_id)


def test_browser_host_unaffected(client):
    r = client.get("/v1/client/config")
    assert r.status_code == 200
    r = client.get("/")
    assert r.status_code == 200
