"""Where the application keeps its own files: generated worlds, history and settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

FOLDER: Final[str] = "RandomNewWorld"
LINUX_FOLDER: Final[str] = "random-new-world"
WORKSPACE: Final[str] = "generated"


def data_directory(
    *,
    system: str | None = None,
    home: Path | None = None,
    variables: Mapping[str, str] | None = None,
) -> Path:
    """The application's data folder (not created): ``%LOCALAPPDATA%\\RandomNewWorld`` on
    Windows, ``$XDG_DATA_HOME/random-new-world`` elsewhere (``~/.local/share`` by default),
    ``~/Library/Application Support/RandomNewWorld`` on macOS."""
    system = sys.platform if system is None else system
    home = Path.home() if home is None else home
    variables = dict(os.environ) if variables is None else variables
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
