# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for web search triggers (v0.9.0)."""

from app.web_search import format_search_context, wants_search


def test_wants_search():
    assert wants_search("get me latest on JPM")
    assert wants_search("what's the news today")
    assert wants_search("current stock price")
    assert not wants_search("hello how are you")
    assert not wants_search("write a function")


def test_format_search_context():
    results = [{"title": "Test", "url": "https://example.com", "text": "Some text"}]
    ctx = format_search_context(results)
    assert "Test" in ctx
    assert "https://example.com" in ctx
    assert "[1]" in ctx


def test_format_empty():
    assert format_search_context([]) == ""
