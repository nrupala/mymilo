# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for device token auth (v0.31.0)."""

import tempfile
from pathlib import Path

from app.devices import DeviceStore


def test_device_lifecycle():
    with tempfile.TemporaryDirectory() as d:
        store = DeviceStore(Path(d) / "test.db")
        device_id, token = store.register(
            "nrupal@example.com", name="Pixel 8", platform="android"
        )
        assert device_id
        assert token.startswith("milo_")

        # Token resolves to the user
        assert store.resolve(token) == "nrupal@example.com"

        # Wrong token doesn't resolve
        assert store.resolve("milo_wrongtoken") is None
        assert store.resolve("") is None

        # Device lists without token hash
        devices = store.list_devices("nrupal@example.com")
        assert len(devices) == 1
        assert devices[0]["name"] == "Pixel 8"
        assert "token_hash" not in devices[0]

        # Revoke works, then token no longer resolves
        assert store.revoke("nrupal@example.com", device_id) is True
        assert store.resolve(token) is None

        # Can't revoke another user's device
        device_id2, _ = store.register("other@example.com")
        assert store.revoke("nrupal@example.com", device_id2) is False


def test_device_rotate_and_delete():
    with tempfile.TemporaryDirectory() as d:
        store = DeviceStore(Path(d) / "test.db")
        device_id, old_token = store.register(
            "nrupal@example.com", name="S25", platform="android"
        )

        # Rotate: same device, new token, old token dies immediately.
        new_token = store.rotate("nrupal@example.com", device_id)
        assert new_token is not None and new_token != old_token
        assert store.resolve(old_token) is None
        assert store.resolve(new_token) == "nrupal@example.com"
        # Still exactly one device row — no redo pile-up.
        assert len(store.list_devices("nrupal@example.com")) == 1

        # Another user's rotate/delete attempts fail.
        assert store.rotate("other@example.com", device_id) is None
        assert store.delete("other@example.com", device_id) is False

        # Revoked devices cannot rotate.
        assert store.revoke("nrupal@example.com", device_id) is True
        assert store.rotate("nrupal@example.com", device_id) is None

        # Delete removes the row permanently (even revoked rows).
        assert store.delete("nrupal@example.com", device_id) is True
        assert store.list_devices("nrupal@example.com") == []
        assert store.resolve(new_token) is None
        assert store.delete("nrupal@example.com", device_id) is False


def test_device_endpoints_rotate_and_remove(tmp_path):
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
    from app.main import create_app

    def backend(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"object": "list", "data": []})

    settings = Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[ModelRoute(name="local", base_url="http://backend/v1")],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="local"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        persona=PersonaConfig(system_prompt="You are Milo."),
    )
    app = create_app(settings, transport=httpx.MockTransport(backend))
    app.state.devices = DeviceStore(tmp_path / "memory.db")
    headers = {"cf-access-authenticated-user-email": "test@example.com"}
    with TestClient(app) as client:
        r = client.post(
            "/v1/devices/register",
            json={"name": "Phone", "platform": "android"},
            headers=headers,
        )
        assert r.status_code == 200
        device_id = r.json()["device_id"]
        old_token = r.json()["token"]

        r = client.post(f"/v1/devices/{device_id}/rotate", headers=headers)
        assert r.status_code == 200
        new_token = r.json()["token"]
        assert new_token != old_token

        # Old token is dead; new token authenticates. Checked on the
        # API host, where the auth guard lives (native-client path):
        # an unresolvable token gets a 401 there.
        api = {"host": "mymilo-api.aimlds.org"}
        r = client.get(
            "/v1/devices", headers={"Authorization": f"Bearer {old_token}", **api}
        )
        assert r.status_code == 401
        r = client.get(
            "/v1/devices", headers={"Authorization": f"Bearer {new_token}", **api}
        )
        assert r.status_code == 200
        assert any(d["id"] == device_id for d in r.json()["devices"])

        # Remove permanently: row gone, token dead, second remove 404s.
        r = client.post(f"/v1/devices/{device_id}/remove", headers=headers)
        assert r.status_code == 200
        r = client.get("/v1/devices", headers=headers)
        assert all(d["id"] != device_id for d in r.json()["devices"])
        r = client.get(
            "/v1/devices", headers={"Authorization": f"Bearer {new_token}", **api}
        )
        assert r.status_code == 401
        r = client.post(f"/v1/devices/{device_id}/remove", headers=headers)
        assert r.status_code == 404
