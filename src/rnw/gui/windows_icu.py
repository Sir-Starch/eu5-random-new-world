"""ICU for Qt where the system has no ``icuuc.dll``: Valve's own Proton, the Steam Deck's.

Qt6Core.dll imports its converters from ``icuuc.dll``. Windows 10 and later have that file (it
forwards to ``icu.dll``), and so do the community Proton builds; Valve's Proton ships ``icu.dll``
without it, and the classic window then stops with ``DLL load failed while importing QtWidgets``.
The hub carries a forwarder of its own in ``generator/compat`` (``packaging/icuuc``). It is put
on the DLL search path here, before Qt is imported, and only when the system lacks the file, so
a system that has one keeps using it. Nothing here imports Qt.
"""

from __future__ import annotations

import ctypes
import os
import sys
from typing import TYPE_CHECKING, Final

from rnw.app import paths

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

LIBRARY: Final[str] = "icuuc.dll"
FOLDER: Final[tuple[str, str]] = ("generator", "compat")


def forwarder_folder(program_folder: Path | None = None) -> Path:
    """The hub's folder of the forwarder, beside the interpreter's ``generator`` folder."""
    folder = paths.program_directory() if program_folder is None else program_folder
    return folder.joinpath(*FOLDER)


def _load_from_system(name: str) -> None:
    """Load ``name`` the way Qt's loader would, from the application and system folders."""
    _ = ctypes.CDLL(name)


def _add_to_search_path(folder: Path) -> None:
    if sys.platform == "win32":
        _ = os.add_dll_directory(str(folder))


def prepare(
    *,
    program_folder: Path | None = None,
    platform: str | None = None,
    load: Callable[[str], None] = _load_from_system,
    add: Callable[[Path], None] = _add_to_search_path,
) -> str:
    """Make ``icuuc.dll`` findable for Qt; the sentence for the log, or ``""`` when the system
    has the file (or this is not Windows) and nothing was needed."""
    if (sys.platform if platform is None else platform) != "win32":
        return ""
    try:
        load(LIBRARY)
    except OSError:
        pass
    else:
        return ""
    folder = forwarder_folder(program_folder)
    if not (folder / LIBRARY).is_file():
        return f"The system has no {LIBRARY} and this package has no forwarder in {folder}"
    add(folder)
    return f"The system has no {LIBRARY}: Qt uses the forwarder to icu.dll in {folder}"
