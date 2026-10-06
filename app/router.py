# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Model router: maps a model name to an OpenAI-compatible upstream backend.

Phase 1 is a transparent proxy with routing, timeouts, and honest errors.
Cost-aware routing and the per-call ledger arrive in Phase 4.
"""

from __future__ import annotations

import httpx

from .config import ModelRoute, Settings


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
        self, settings: Settings, transport: httpx.BaseTransport | None = None
    ):
        self.settings = settings
        self._transport = transport

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
            raise UpstreamUnavailableError(model_name, route.base_url) from None
        if resp.status_code >= 400:
            raise UpstreamError(model_name, resp.status_code, resp.text[:2000])
        return resp.json()

    async def check_reachable(self, route: ModelRoute) -> bool:
        try:
            async with self._client(2.0) as client:
                resp = await client.get(
                    f"{route.base_url}/models", headers=self._headers(route)
                )
                return resp.status_code < 500
        except Exception:
            return False
