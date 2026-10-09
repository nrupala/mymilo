# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Configuration: TOML file with environment-variable overrides.

Secrets are never stored in the config file. A model route may name an
environment variable (``api_key_env``) whose value is read at request time;
see ``vault/README.md`` for where to keep the actual secrets.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class ModelRoute:
    name: str
    base_url: str
    api_key_env: str | None = None
    timeout_s: float = 60.0
    # Backend model ID override. When set, the router sends this as the
    # "model" field to the backend instead of the route name. Used for
    # cloud providers where the route name (e.g. "openrouter") is not a
    # valid model ID (e.g. "deepseek/deepseek-chat").
    model_id: str | None = None
    # Cost metadata (Phase 4, fleet economics). Local backends stay at the
    # zero defaults. Paid routes declare per-1k-token USD rates and an
    # optional monthly free quota in USD; the ledger flags 70% and 100%.
    input_usd_per_1k: float = 0.0
    output_usd_per_1k: float = 0.0
    free_quota_usd: float | None = None
    # Token planning registry (Token-Efficiency Engine, slice 1). All
    # optional: a route without a context window is unplanned and the
    # token planner leaves its requests untouched. Windows must match
    # the backend's actual serving config (e.g. llama.cpp --ctx-size),
    # not the model's nominal maximum.
    context_window: int | None = None
    default_max_tokens: int | None = None
    max_output_tokens: int | None = None
    # Backpressure (Engine slice 3): max in-flight requests on this
    # route. None = router default (1 for local backends, 8 for cloud).
    max_concurrency: int | None = None


@dataclass
class EmbeddingsConfig:
    backend: str = "llamacpp"  # llamacpp | sentence-transformers | hash (test only)
    route: str = "local"  # model-route name for the llamacpp backend
    model: str = "embed"  # model name sent to /embeddings
    st_model: str = "all-MiniLM-L6-v2"
    timeout_s: float = 60.0


@dataclass
class SchedulerConfig:
    enabled: bool = True
    tick_seconds: float = 30.0


@dataclass
class SkillsConfig:
    enabled: bool = True
    dir: str = "skills"
    poll_seconds: float = 300.0


@dataclass
class PersonaConfig:
    name: str = "Milo"
    system_prompt: str = (
        "You are MyMilo, Nrupal's proactive briefing assistant. "
        "Write a concise briefing from the retrieved context below. "
        "Lead with what needs attention, keep it scannable, and never "
        "invent facts that are not in the context. If the context is thin, "
        "say so plainly."
    )


@dataclass
class VaultConfig:
    # Directory holding secret files named by env-var, e.g.
    # <path>/MYMILO_CLOUD_API_KEY. Env vars always win; files are the
    # fallback. Aligned with the kalabodha-vault zero-trust pattern —
    # see docs/vault-alignment.md.
    path: str | None = None


@dataclass
class OSConfig:
    # Agentic OS OpenAI-compatible endpoint. When set, a route named
    # "os" is registered and becomes the default model — MyMilo acts as
    # a thin client of the OS. The local router stays until the OS
    # endpoint is live; its deletion is a one-PR change then.
    endpoint: str | None = None
    # Token-planning registry for the os route (Engine slice 1.1). The
    # window must match the effective window behind the endpoint (on
    # Aetheris the dispatcher upstream is Phi-4-mini at --ctx-size
    # 8192, so the os route plans against 8192).
    context_window: int | None = None
    default_max_tokens: int | None = None
    max_output_tokens: int | None = None


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8090
    db_path: str = "data/mymilo.db"
    models: list[ModelRoute] = field(default_factory=list)
    request_timeout_s: float = 90.0
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    vault: VaultConfig = field(default_factory=VaultConfig)
    os: OSConfig = field(default_factory=OSConfig)
    default_model: str = "local"
    mcp_service_tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Keep the default model routable no matter how Settings was built.
        if self.models and not self.route_for(self.default_model):
            self.default_model = self.models[0].name

    @classmethod
    def load(cls, config_path: str | None = None) -> Settings:
        path = config_path or os.environ.get("MYMILO_CONFIG", "config/mymilo.toml")
        data: dict = {}
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = tomllib.load(f)

        s = cls()
        server = data.get("server", {})
        s.host = os.environ.get("MYMILO_HOST", server.get("host", s.host))
        s.port = int(os.environ.get("MYMILO_PORT", server.get("port", s.port)))
        s.db_path = os.environ.get(
            "MYMILO_DB", data.get("database", {}).get("path", s.db_path)
        )
        s.request_timeout_s = float(
            os.environ.get(
                "MYMILO_TIMEOUT", server.get("request_timeout_s", s.request_timeout_s)
            )
        )
        emb = data.get("embeddings", {})
        s.embeddings = EmbeddingsConfig(
            backend=os.environ.get(
                "MYMILO_EMBED_BACKEND", emb.get("backend", "llamacpp")
            ),
            route=emb.get("route", "local"),
            model=emb.get("model", "embed"),
            st_model=emb.get("st_model", "all-MiniLM-L6-v2"),
            timeout_s=float(emb.get("timeout_s", 60.0)),
        )

        model_defs = data.get("models", [])
        if not model_defs:
            # llama.cpp default: `llama-server -m <model.gguf> --port 8080`
            model_defs = [{"name": "local", "base_url": "http://127.0.0.1:8080/v1"}]
        for m in model_defs:
            s.models.append(
                ModelRoute(
                    name=m["name"],
                    base_url=m["base_url"].rstrip("/"),
                    api_key_env=m.get("api_key_env"),
                    timeout_s=float(m.get("timeout_s", 60.0)),
                    model_id=m.get("model_id"),
                    input_usd_per_1k=float(m.get("input_usd_per_1k", 0.0)),
                    output_usd_per_1k=float(m.get("output_usd_per_1k", 0.0)),
                    free_quota_usd=(
                        float(m["free_quota_usd"])
                        if m.get("free_quota_usd") is not None
                        else None
                    ),
                    context_window=(
                        int(m["context_window"])
                        if m.get("context_window") is not None
                        else None
                    ),
                    default_max_tokens=(
                        int(m["default_max_tokens"])
                        if m.get("default_max_tokens") is not None
                        else None
                    ),
                    max_output_tokens=(
                        int(m["max_output_tokens"])
                        if m.get("max_output_tokens") is not None
                        else None
                    ),
                    max_concurrency=(
                        int(m["max_concurrency"])
                        if m.get("max_concurrency") is not None
                        else None
                    ),
                )
            )

        sched = data.get("scheduler", {})
        s.scheduler = SchedulerConfig(
            enabled=os.environ.get(
                "MYMILO_SCHEDULER_ENABLED", str(sched.get("enabled", True))
            ).lower()
            not in ("0", "false", "no"),
            tick_seconds=float(
                os.environ.get("MYMILO_SCHEDULER_TICK", sched.get("tick_seconds", 30.0))
            ),
        )

        skills_cfg = data.get("skills", {})
        s.skills = SkillsConfig(
            enabled=os.environ.get(
                "MYMILO_SKILLS_ENABLED", str(skills_cfg.get("enabled", True))
            ).lower()
            not in ("0", "false", "no"),
            dir=os.environ.get("MYMILO_SKILLS_DIR", skills_cfg.get("dir", "skills")),
            poll_seconds=float(
                os.environ.get(
                    "MYMILO_SKILLS_POLL", skills_cfg.get("poll_seconds", 300.0)
                )
            ),
        )

        persona_cfg = data.get("persona", {})
        s.persona = PersonaConfig(
            name=persona_cfg.get("name", "Milo"),
            system_prompt=persona_cfg.get("system_prompt", PersonaConfig.system_prompt),
        )

        vault_cfg = data.get("vault", {})
        s.vault = VaultConfig(
            path=os.environ.get("MYMILO_VAULT_PATH", vault_cfg.get("path"))
        )

        os_cfg = data.get("os", {})

        def _os_int(key: str, env_key: str) -> int | None:
            raw = os.environ.get(env_key, os_cfg.get(key))
            return int(raw) if raw is not None else None

        s.os = OSConfig(
            endpoint=os.environ.get("MYMILO_OS_ENDPOINT", os_cfg.get("endpoint")),
            context_window=_os_int("context_window", "MYMILO_OS_CONTEXT_WINDOW"),
            default_max_tokens=_os_int(
                "default_max_tokens", "MYMILO_OS_DEFAULT_MAX_TOKENS"
            ),
            max_output_tokens=_os_int(
                "max_output_tokens", "MYMILO_OS_MAX_OUTPUT_TOKENS"
            ),
        )
        if s.os.endpoint:
            s.models.append(
                ModelRoute(
                    name="os",
                    base_url=s.os.endpoint.rstrip("/"),
                    context_window=s.os.context_window,
                    default_max_tokens=s.os.default_max_tokens,
                    max_output_tokens=s.os.max_output_tokens,
                )
            )
            s.default_model = "os"
        elif not s.route_for(s.default_model) and s.models:
            s.default_model = s.models[0].name
        # v0.24.0: MCP service tokens for agent-to-agent auth (hardening).
        # Comma-separated list; empty = no token auth (CF Access only).
        raw_tokens = os.environ.get("MCP_SERVICE_TOKENS", "")
        s.mcp_service_tokens = [t.strip() for t in raw_tokens.split(",") if t.strip()]
        return s

    def route_for(self, name: str) -> ModelRoute | None:
        return next((m for m in self.models if m.name == name), None)

    def api_key_for(self, route: ModelRoute) -> str | None:
        if route.api_key_env:
            value = os.environ.get(route.api_key_env)
            if value:
                return value
            # Vault fallback (aligned with kalabodha-vault, see
            # docs/vault-alignment.md): a file named by the env var
            # inside the vault dir. Env always wins.
            if self.vault.path:
                from pathlib import Path

                candidate = Path(self.vault.path) / route.api_key_env
                try:
                    if candidate.is_file():
                        return candidate.read_text().strip() or None
                except OSError:
                    pass
        return None
