# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Model router: maps a model name to an OpenAI-compatible upstream backend.

Phase 1 is a transparent proxy with routing, timeouts, and honest errors.
Cost-aware routing and the per-call ledger arrive in Phase 4.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from .config import ModelRoute, Settings
from .ledger import compute_cost


class ModelNotFoundError(Exception):
    def __init__(self, name: str, available: list[str]):
        self.name = name
        self.available = available
        super().__init__(f"unknown model '{name}'")


class UpstreamUnavailableError(Exception):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url
        super().__init__(f"backend for model '{model}' unreachable at {base_url}")


class UpstreamError(Exception):
    def __init__(self, model: str, status_code: int, detail: str):
        self.model = model
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"backend for model '{model}' returned {status_code}")


class ModelRouter:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        ledger: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.settings = settings
        self._transport = transport
        # Optional per-call recorder: receives a ledger entry dict after
        # every chat_completion attempt (success or failure). It may be
        # sync or async; recording never breaks the request.
        self._ledger = ledger
        # Lifecycle discipline (Phase 4): per-route usage/failure stats.
        # last_used_at enables idle-based scale-to-zero policy upstream;
        # consecutive_failures drives the cooldown below.
        self._last_used: dict[str, str] = {}
        self._failures: dict[str, int] = {}

    def _client(self, timeout_s: float) -> httpx.AsyncClient:
        # trust_env=False: backend connections are direct and deterministic.
        # Ambient proxy variables must never reroute localhost model backends
        # (or leak backend hostnames); cloud routes needing a proxy get an
        # explicit setting in a later phase.
        return httpx.AsyncClient(
            transport=self._transport, timeout=timeout_s, trust_env=False
        )

    def _headers(self, route: ModelRoute) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = self.settings.api_key_for(route)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def chat_completion(self, model_name: str, payload: dict) -> dict:
        route = self.settings.route_for(model_name)
        if route is None:
            raise ModelNotFoundError(model_name, [m.name for m in self.settings.models])
        started = time.monotonic()
        try:
            async with self._client(route.timeout_s) as client:
                resp = await client.post(
                    f"{route.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(route),
                )
        except httpx.TransportError:
            # Any transport-level failure (refused, DNS, timeout, reset,
            # intercepted) means the backend is not usefully reachable.
            self._note_failure(route.name)
            await self._record(model_name, route, None, None, started, status="error")
            raise UpstreamUnavailableError(model_name, route.base_url) from None
        if resp.status_code >= 400:
            self._note_failure(route.name)
            await self._record(model_name, route, None, None, started, status="error")
            raise UpstreamError(model_name, resp.status_code, resp.text[:2000])
        data = resp.json()
        usage = data.get("usage") or {}
        self._note_success(route.name)
        await self._record(
            model_name,
            route,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            started,
            status="ok",
        )
        return data

    def _note_success(self, route_name: str) -> None:
        self._last_used[route_name] = datetime.now(UTC).isoformat()
        self._failures[route_name] = 0

    def _note_failure(self, route_name: str) -> None:
        self._failures[route_name] = self._failures.get(route_name, 0) + 1

    def route_stats(self) -> dict[str, dict[str, Any]]:
        """Lifecycle stats per route: last use and failure streak."""
        return {
            r.name: {
                "last_used_at": self._last_used.get(r.name),
                "consecutive_failures": self._failures.get(r.name, 0),
            }
            for r in self.settings.models
        }

    async def _record(
        self,
        model_name: str,
        route: ModelRoute,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        started: float,
        status: str,
    ) -> None:
        if self._ledger is None:
            return
        entry = {
            "model": model_name,
            "route": route.name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": compute_cost(
                prompt_tokens,
                completion_tokens,
                route.input_usd_per_1k,
                route.output_usd_per_1k,
            ),
            "latency_ms": round((time.monotonic() - started) * 1000, 1),
            "status": status,
        }
        try:
            result = self._ledger(entry)
            if inspect.isawaitable(result):
                await result
        except Exception:  # noqa: BLE001 — ledger must never break serving
            pass

    async def check_reachable(self, route: ModelRoute) -> bool:
        try:
            async with self._client(2.0) as client:
                resp = await client.get(
                    f"{route.base_url}/models", headers=self._headers(route)
                )
                return resp.status_code < 500
        except Exception:
            return False
