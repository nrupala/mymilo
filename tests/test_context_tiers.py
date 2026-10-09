# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Context tier tests (Token-Efficiency Engine, slice 2).

Covers the tier formatters and budgets, the compaction checkpoint v2
(coverage metadata + migration from the v1 schema), and — through a
capturing stub backend — the actual prompt assembly order: stable
prefix, summary tier, retrieval tier, dynamic blocks, history, turn.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

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
from app.context_tiers import (
    RETRIEVAL_TIER_BUDGET,
    SUMMARY_TIER_BUDGET,
    cap_to_tokens,
    dynamic_insert_index,
    retrieval_tier,
    summary_tier,
)
from app.main import create_app
from app.memory import MemoryStore
from app.summarize import get_summary_context
from app.tokenplan import estimate_tokens


# ----------------------------------------------------------------------
# cap_to_tokens
# ----------------------------------------------------------------------
def test_cap_leaves_short_text_alone():
    assert cap_to_tokens("hello world", 100) == "hello world"


def test_cap_truncates_to_budget_with_marker():
    text = "word " * 2000
    capped = cap_to_tokens(text, 100)
    assert estimate_tokens(capped) <= 100
    assert capped.endswith("…")
    assert len(capped) < len(text)


# ----------------------------------------------------------------------
# Summary tier (HCA)
# ----------------------------------------------------------------------
def test_summary_tier_checkpoint_header():
    row = {"summary": "Discussed budgets.", "covered_count": 12}
    out = summary_tier(row)
    assert out is not None
    assert "checkpoint covering 12 turns" in out
    assert "Discussed budgets." in out


def test_summary_tier_legacy_row_plain_header():
    out = summary_tier({"summary": "Old style."})
    assert out is not None
    assert out.startswith("[Earlier in this conversation: ")


def test_summary_tier_budget_enforced():
    row = {"summary": "word " * 5000, "covered_count": 40}
    out = summary_tier(row)
    assert out is not None
    assert estimate_tokens(out) <= SUMMARY_TIER_BUDGET


def test_summary_tier_empty():
    assert summary_tier(None) is None
    assert summary_tier({"summary": "  "}) is None


# ----------------------------------------------------------------------
# Retrieval tier (CSA)
# ----------------------------------------------------------------------
def test_retrieval_tier_facts_ranked_by_relevance():
    facts = [
        {"category": "identity", "key": "name", "value": "Nrupal"},
        {"category": "food", "key": "diet", "value": "vegan"},
    ]
    out, sources = retrieval_tier([], facts, query="what diet am I on")
    assert out is not None
    assert "food/diet: vegan" in out
    assert "Nrupal" not in out  # zero-overlap fact is not retrieved
    assert sources == [{"type": "memory", "title": "food/diet: vegan"}]


def test_retrieval_tier_episode_uses_preview_snippet():
    episodes = [
        {
            "title": "Trip planning",
            "preview": [
                {"role": "user", "content": "Plan   a trip\n to Banff"},
                {"role": "assistant", "content": "Sure..."},
            ],
        }
    ]
    out, sources = retrieval_tier(episodes, [], query="trip")
    assert out is not None
    assert "[Past: Trip planning] Plan a trip to Banff" in out
    assert sources == [{"type": "past chat", "title": "Trip planning"}]


def test_retrieval_tier_item_and_tier_caps():
    big = "x" * 5000
    episodes = [
        {"title": f"S{i}", "preview": [{"role": "user", "content": big}]}
        for i in range(20)
    ]
    out, _sources = retrieval_tier(episodes, [], query="x")
    assert out is not None
    assert estimate_tokens(out) <= RETRIEVAL_TIER_BUDGET
    for line in out.splitlines()[1:]:
        assert estimate_tokens(line) <= 256


def test_retrieval_tier_empty():
    assert retrieval_tier([], []) == (None, [])


# ----------------------------------------------------------------------
# Dynamic insert index
# ----------------------------------------------------------------------
def test_dynamic_insert_index():
    msgs = [
        {"role": "system", "content": "a"},
        {"role": "system", "content": "b"},
        {"role": "user", "content": "hi"},
    ]
    assert dynamic_insert_index(msgs) == 2
    assert dynamic_insert_index([{"role": "system", "content": "a"}]) == 1
    assert dynamic_insert_index([]) == 0


# ----------------------------------------------------------------------
# Checkpoint v2 (memory store)
# ----------------------------------------------------------------------
def test_checkpoint_v2_round_trip(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    sid = store.create_session("u@example.com")
    store.save_summary(
        sid,
        "They planned a budget.",
        summarized_up_to=30,
        covered_from=0,
        covered_count=12,
        model="local",
    )
    row = store.get_summary(sid)
    assert row is not None
    assert row["covered_from"] == 0
    assert row["covered_count"] == 12
    assert row["model"] == "local"


def test_checkpoint_v2_migrates_v1_schema(tmp_path):
    path = tmp_path / "memory.db"
    with sqlite3.connect(path) as c:
        c.execute(
            "CREATE TABLE session_summaries ("
            " session_id TEXT PRIMARY KEY, summary TEXT NOT NULL,"
            " summarized_up_to INTEGER NOT NULL DEFAULT 0,"
            " created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        c.execute(
            "INSERT INTO session_summaries VALUES ('s1', 'old summary', 9, 1.0, 1.0)"
        )
    store = MemoryStore(path)  # _init must migrate without losing the row
    row = store.get_summary("s1")
    assert row is not None
    assert row["summary"] == "old summary"
    assert row["covered_count"] == 0


def test_summary_context_uses_checkpoint_format(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    sid = store.create_session("u@example.com")
    store.save_summary(sid, "Budget talks.", 30, covered_count=12)
    ctx = get_summary_context(store, sid)
    assert "checkpoint covering 12 turns" in ctx
    assert "Budget talks." in ctx


# ----------------------------------------------------------------------
# Assembly order through the real endpoint (capturing backend)
# ----------------------------------------------------------------------
def test_chat_assembly_order(tmp_path):
    captured: list[list[dict]] = []

    def backend(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"object": "list", "data": []})
        if request.url.path == "/v1/chat/completions":
            payload = json.loads(request.read().decode())
            captured.append(payload["messages"])
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-stub",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "stub",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 5},
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    settings = Settings(
        host="127.0.0.1",
        port=8090,
        db_path=str(tmp_path / "test.db"),
        models=[ModelRoute(name="stub", base_url="http://stub-backend/v1")],
        embeddings=EmbeddingsConfig(backend="llamacpp", route="stub"),
        scheduler=SchedulerConfig(enabled=False),
        skills=SkillsConfig(enabled=False),
        persona=PersonaConfig(system_prompt="You are Milo."),
    )
    # Seed a session with history + a compaction checkpoint, in the
    # same memory.db the app will use.
    store = MemoryStore(Path(settings.db_path).parent / "memory.db")
    sid = store.create_session("someone@example.com")
    store.add_message(sid, "user", "alpha topic")
    store.add_message(sid, "assistant", "beta reply")
    store.save_summary(
        sid, "They discussed alpha at length.", 2, covered_count=2, model="local"
    )

    app = create_app(settings, transport=httpx.MockTransport(backend))
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "stub",
                "session_id": sid,
                "messages": [{"role": "user", "content": "gamma question"}],
            },
        )
    assert r.status_code == 200
    assert captured, "backend never received a payload"
    msgs = captured[-1]
    contents = [m.get("content", "") for m in msgs]

    def idx_of(fragment: str) -> int:
        return next(i for i, c in enumerate(contents) if fragment in c)

    i_summary = idx_of("checkpoint covering 2 turns")
    i_time = idx_of("Today is")
    i_history = idx_of("alpha topic")
    # Stable prefix first: the summary tier precedes the dynamic
    # date/time block, which precedes raw history; the current turn
    # is last. (Before slice 2 the clock block was message 0.)
    assert i_summary < i_time < i_history
    assert contents[-1] == "gamma question"
    assert not contents[0].startswith("Today is")
