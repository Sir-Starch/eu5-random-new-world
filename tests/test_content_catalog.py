"""The public reference must cover the current definitions, without a game install."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_content_reference_matches_current_definitions() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(  # noqa: S603 - repository-owned documentation builder
        [sys.executable, str(root / "docs/build_content_reference.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
