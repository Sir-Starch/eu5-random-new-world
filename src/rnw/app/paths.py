"""Where the application keeps its own files: generated worlds, history and settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# A folder for the data chosen by the player or a script (``rnw`` commands, a portable copy).
ENV_DATA: Final[str] = "RNW_DATA"
# A file beside the program that keeps its data in a folder beside it too: a copy on a stick, or
# in a folder of its own, leaves nothing elsewhere on the machine.
PORTABLE: Final[str] = "portable.txt"
PORTABLE_FOLDER: Final[str] = "data"
FOLDER: Final[str] = "RandomNewWorld"
LINUX_FOLDER: Final[str] = "random-new-world"
WORKSPACE: Final[str] = "generated"


def program_directory() -> Path:
    folder = Path(sys.executable).resolve().parent
    if folder.name == "python" and folder.parent.name == "generator":
        return folder.parent.parent
    return folder


def data_directory(
    *,
    system: str | None = None,
    home: Path | None = None,
    variables: Mapping[str, str] | None = None,
    program: Path | None = None,
) -> Path:
    """The application's data folder (not created).

    ``$RNW_DATA`` when it is set; else ``data`` beside the program when a ``portable.txt`` lies
    there (a portable copy); else ``%LOCALAPPDATA%\\RandomNewWorld`` on Windows,
    ``$XDG_DATA_HOME/random-new-world`` elsewhere (``~/.local/share`` by default) and
    ``~/Library/Application Support/RandomNewWorld`` on macOS.
    """
    system = sys.platform if system is None else system
    home = Path.home() if home is None else home
    variables = dict(os.environ) if variables is None else variables
    program = program_directory() if program is None else program
    chosen = variables.get(ENV_DATA)
    if chosen:
        return Path(chosen)
    if (program / PORTABLE).is_file():
        return program / PORTABLE_FOLDER
    if system == "win32":
        base = variables.get("LOCALAPPDATA")
        return (Path(base) if base else home / "AppData" / "Local") / FOLDER
    if system == "darwin":
        return home / "Library" / "Application Support" / FOLDER
    base = variables.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / LINUX_FOLDER


def workspace(data: Path) -> Path:
    """The folder worlds are generated in; ``check_new_output`` only writes under ``generated``."""
    return data / WORKSPACE
