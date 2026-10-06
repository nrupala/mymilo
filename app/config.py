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
class Settings:
    host: str = "127.0.0.1"
    port: int = 8090
    db_path: str = "data/mymilo.db"
    models: list[ModelRoute] = field(default_factory=list)
    request_timeout_s: float = 90.0
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)

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
        return s

    def route_for(self, name: str) -> ModelRoute | None:
        return next((m for m in self.models if m.name == name), None)

    def api_key_for(self, route: ModelRoute) -> str | None:
        if route.api_key_env:
            return os.environ.get(route.api_key_env)
        return None
