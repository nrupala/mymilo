# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for background orchestration (v0.8.0)."""

from app.orchestrate import (
    plan_steps,
    route_for_complexity,
    wants_background,
)


class FakeRoute:
    def __init__(self, name):
        self.name = name


class FakeSettings:
    def __init__(self, models, keys=None):
        self.models = [FakeRoute(n) for n in models]
        self._keys = keys or {}

    def api_key_for(self, route):
        return self._keys.get(route.name)


def test_wants_background():
    assert wants_background("research this in the background")
    assert wants_background("take your time with this analysis")
    assert not wants_background("hello how are you")


def test_routes_simple_to_local():
    s = FakeSettings(["local", "deepseek"], {"deepseek": "key"})
    assert route_for_complexity("hi", s) == "local"
    assert route_for_complexity("what is 2+2", s) == "local"


def test_routes_complex_to_cloud():
    s = FakeSettings(["local", "deepseek"], {"deepseek": "key"})
    long_q = "research the VFD migration path " * 20
    assert route_for_complexity(long_q, s) == "deepseek"
    assert route_for_complexity("give me a thorough analysis", s) == "deepseek"


def test_no_cloud_key_falls_back_to_local():
    s = FakeSettings(["local", "deepseek"], {})
    long_q = "research the VFD migration path " * 20
    assert route_for_complexity(long_q, s, default="local") == "local"


def test_plan_steps_returns_list():
    steps = plan_steps("do the thing")
    assert isinstance(steps, list) and len(steps) >= 1
