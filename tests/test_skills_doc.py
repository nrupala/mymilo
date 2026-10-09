# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""The committed skills catalogue doc must match a fresh render
of the skills' frontmatter — docs cannot silently drift."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_skills_doc_is_current():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate-skills-doc.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
