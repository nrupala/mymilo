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
