# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Cloudflare integration for milo (Phase 3).

Scoped Cloudflare access: zones, DNS, Workers status.
Write operations (DNS changes, deploys) require explicit confirmation.

Auth: CLOUDFLARE_API_TOKEN env var on the box, scoped to Nrupal's zones.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

CF_API = "https://api.cloudflare.com/client/v4"


class CloudflareClient:
    """Scoped Cloudflare client for milo."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        if not self.token:
            raise ValueError("CLOUDFLARE_API_TOKEN not configured")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(trust_env=False, timeout=30) as client:
            resp = await client.get(
                f"{CF_API}{path}", headers=self._headers(), params=params
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Cloudflare API error: {data.get('errors')}")
            return data["result"]

    async def _post(self, path: str, data: dict | None = None) -> Any:
        async with httpx.AsyncClient(trust_env=False, timeout=30) as client:
            resp = await client.post(
                f"{CF_API}{path}", headers=self._headers(), json=data or {}
            )
            resp.raise_for_status()
            result = resp.json()
            if not result.get("success"):
                raise RuntimeError(f"Cloudflare API error: {result.get('errors')}")
            return result["result"]

    # ── Read operations ──────────────────────────────────

    async def list_zones(self) -> list[dict]:
        """List all zones (domains)."""
        return await self._get("/zones", {"per_page": 50})

    async def get_zone(self, zone_id: str) -> dict:
        """Get zone details."""
        return await self._get(f"/zones/{zone_id}")

    async def list_dns_records(self, zone_id: str) -> list[dict]:
        """List DNS records for a zone."""
        return await self._get(f"/zones/{zone_id}/dns_records", {"per_page": 100})

    async def list_workers(self, account_id: str) -> list[dict]:
        """List Workers for an account."""
        return await self._get(
            f"/accounts/{account_id}/workers/scripts", {"per_page": 50}
        )

    # ── Write operations (require confirmation) ──────────

    async def create_dns_record(
        self,
        zone_id: str,
        record_type: str,
        name: str,
        content: str,
        confirm: bool = False,
    ) -> dict:
        """Create a DNS record. REQUIRES explicit confirmation."""
        if not confirm:
            raise ValueError("DNS changes require explicit confirmation")
        return await self._post(
            f"/zones/{zone_id}/dns_records",
            {"type": record_type, "name": name, "content": content},
        )
