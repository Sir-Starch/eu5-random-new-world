"""Build the application as a PyInstaller folder, with the Tauri window in its ``window`` folder.

Run ``uv run --group packaging python packaging/build.py`` (with Node.js, npm and the window's
system libraries: WebKitGTK 4.1 on Linux). The folder goes to ``dist/RandomNewWorld`` (ignored
by git). The program opens the window, which starts the program again with ``--bridge`` as its
generator; the classic Qt window opens when the window cannot. Nothing is signed and nothing is
published; see ADR 0007 and ADR 0011.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

import allowlist
import window
from notices import write_notices

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
    folder = dist / NAME
    _ = window.build(folder / "window", ROOT / "build" / "window")
    write_notices(folder)
    window.write_notices(folder)
    problems = allowlist.problems_in_folder(folder, vendored=("_internal/",))
    if problems:
        message = f"Package contains game files: {problems}"
        raise RuntimeError(message)
    return folder


if __name__ == "__main__":
    print(build())
