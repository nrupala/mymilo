# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""GitHub integration for milo (Phase 3, first integration).

Scoped GitHub access: read repos, issues, PRs. Write operations
(create issue, comment) require explicit user confirmation via
the escalation path.

Auth: GITHUB_TOKEN env var on the box. Scoped per Nrupal's repos.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"


class GitHubClient:
    """Scoped GitHub client for milo."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        if not self.token:
            raise ValueError("GITHUB_TOKEN not configured")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(trust_env=False, timeout=30) as client:
            resp = await client.get(
                f"{GITHUB_API}{path}", headers=self._headers(), params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, data: dict) -> Any:
        async with httpx.AsyncClient(trust_env=False, timeout=30) as client:
            resp = await client.post(
                f"{GITHUB_API}{path}", headers=self._headers(), json=data
            )
            resp.raise_for_status()
            return resp.json()

    # ── Read operations (safe) ──────────────────────────────

    async def list_repos(self, username: str = "nrupala") -> list[dict]:
        """List user's repositories."""
        return await self._get(f"/users/{username}/repos", {"per_page": 100})

    async def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository details."""
        return await self._get(f"/repos/{owner}/{repo}")

    async def list_issues(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[dict]:
        """List issues for a repo."""
        return await self._get(
            f"/repos/{owner}/{repo}/issues", {"state": state, "per_page": 50}
        )

    async def list_prs(self, owner: str, repo: str, state: str = "open") -> list[dict]:
        """List pull requests for a repo."""
        return await self._get(
            f"/repos/{owner}/{repo}/pulls", {"state": state, "per_page": 50}
        )

    # ── Write operations (require confirmation) ─────────────

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = ""
    ) -> dict:
        """Create an issue. Caller must confirm with user first."""
        return await self._post(
            f"/repos/{owner}/{repo}/issues", {"title": title, "body": body}
        )

    async def comment_on_issue(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict:
        """Comment on an issue. Caller must confirm with user first."""
        return await self._post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments", {"body": body}
        )
