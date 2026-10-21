"""Build the application as a PyInstaller folder.

Run ``uv run --group packaging python packaging/build.py``. The folder goes to
``dist/RandomNewWorld`` (ignored by git). Nothing is signed and nothing is published; see
ADR 0007 for what is still open.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
NAME: Final[str] = "RandomNewWorld"


def build() -> Path:
    """Run PyInstaller on ``rnw.spec`` and return the folder it made."""
    work = ROOT / "build" / "pyinstaller"
    dist = ROOT / "dist"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    spec = work / "rnw.spec"
    _ = shutil.copyfile(ROOT / "packaging" / "rnw.spec", spec)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist),
        "--workpath",
        str(work),
        str(spec),
    ]
    _ = subprocess.run(command, check=True, cwd=ROOT)  # noqa: S603 - our own interpreter and fixed options
    return dist / NAME


if __name__ == "__main__":
    print(build())
