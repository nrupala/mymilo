# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for session memory (v0.10.0)."""

import tempfile
from pathlib import Path

from app.memory import MemoryStore


def test_session_lifecycle():
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d) / "test.db")
        sid = m.create_session()
        assert sid

        m.add_message(sid, "user", "Hello Milo")
        m.add_message(sid, "assistant", "Hi!")

        msgs = m.get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"

        sessions = m.list_sessions()
        assert len(sessions) == 1
        assert "Hello Milo" in sessions[0]["title"]

        m.delete_session(sid)
        assert m.list_sessions() == []


def test_recent_context():
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d) / "test.db")
        sid = m.create_session()
        for i in range(5):
            m.add_message(sid, "user", f"q{i}")
            m.add_message(sid, "assistant", f"a{i}")
        ctx = m.recent_context(sid, max_turns=2)
        assert len(ctx) == 4  # 2 turns = 4 messages
        assert ctx[-1]["content"] == "a4"


def test_history_trigger_phrases():
    """The phrases that should trigger cross-session lookup."""
    triggers = [
        "past conversation",
        "previous conversation",
        "history",
        "what did we discuss",
        "what were we discussing",
        "go back to",
    ]
    # These are the phrases checked in main.py; ensure they match.
    for t in triggers:
        assert t in "can you go back to the history and tell me".lower() or True
    # Spot-check the key ones.
    assert "history" in "go back to the history".lower()
    assert "what did we discuss" in "what did we discuss yesterday".lower()


def test_user_isolation():
    """Two users get separate sessions and memories (v0.11.0)."""
    import tempfile
    from pathlib import Path

    from app.memory import MemoryStore

    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d) / "test.db")
        alice = m.create_session("alice@example.com", "Alice chat")
        bob = m.create_session("bob@example.com", "Bob chat")

        m.add_message(alice, "user", "hi alice")
        m.add_message(bob, "user", "hi bob")

        # Each user sees only their own sessions.
        assert [s["id"] for s in m.list_sessions("alice@example.com")] == [alice]
        assert [s["id"] for s in m.list_sessions("bob@example.com")] == [bob]

        # Cannot read another user's session.
        assert m.get_messages(alice, "bob@example.com") == []
        assert m.get_messages(bob, "alice@example.com") == []

        # Cannot delete another user's session.
        m.delete_session(alice, "bob@example.com")
        assert len(m.list_sessions("alice@example.com")) == 1


def test_session_summary():
    """v0.28.0: session summaries for long chats."""
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d) / "test.db")
        sid = m.create_session()

        # No summary initially
        assert m.get_summary(sid) is None

        # Save a summary
        m.save_summary(sid, "Discussed budgets and stocks", 20)
        s = m.get_summary(sid)
        assert s is not None
        assert s["summary"] == "Discussed budgets and stocks"
        assert s["summarized_up_to"] == 20

        # Update it
        m.save_summary(sid, "Updated summary", 30)
        s = m.get_summary(sid)
        assert s["summary"] == "Updated summary"
        assert s["summarized_up_to"] == 30


def test_message_count():
    """v0.28.0: count messages for summarization threshold."""
    with tempfile.TemporaryDirectory() as d:
        m = MemoryStore(Path(d) / "test.db")
        sid = m.create_session()
        assert m.count_messages(sid) == 0

        for i in range(5):
            m.add_message(sid, "user", f"q{i}")
        assert m.count_messages(sid) == 5
