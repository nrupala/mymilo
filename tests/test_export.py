# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Tests for export (v0.10.0)."""

from app.export import (
    extract_tables,
    tables_to_csv,
    to_docx,
    to_html,
    to_markdown,
)


def sample():
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


def test_to_markdown():
    md = to_markdown(sample())
    assert "# Milo Export" in md
    assert "## You" in md
    assert "## Milo" in md
    assert "Hello" in md


def test_to_html():
    h = to_html(sample())
    assert "<html>" in h
    assert "Hello" in h
    assert "Hi there!" in h


def test_to_docx():
    data = to_docx(sample())
    assert data[:4] == b"PK\x03\x04"  # zip magic


def test_extract_tables():
    text = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    tables = extract_tables(text)
    assert len(tables) == 1
    assert tables[0] == [["A", "B"], ["1", "2"], ["3", "4"]]


def test_tables_to_csv():
    tables = [[["A", "B"], ["1", "2"]]]
    csv_out = tables_to_csv(tables)
    assert "A,B" in csv_out
    assert "1,2" in csv_out


def test_no_tables():
    assert extract_tables("no tables here") == []
