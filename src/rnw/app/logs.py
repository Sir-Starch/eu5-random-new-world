"""The generator's own log: what it did and what failed, for the player's bug reports.

``start`` sends the ``rnw`` logger to ``generator.log`` in the data folder, rotated so it never
grows past about two megabytes. The window, the command line and the services write to it with
``get``: tasks starting and ending, each stage with its time, every failure with its traceback.
``rnw.app.diagnostics`` packs it, redacted, with the rest of what a report needs.

A log that cannot be written (a read-only folder) never stops the program; ``status`` says what
went wrong, and the diagnostics report prints it.
"""

from __future__ import annotations

import contextlib
import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, Final

from rnw import __version__, epoch

if TYPE_CHECKING:
    from pathlib import Path

NAME: Final[str] = "rnw"
FILE: Final[str] = "generator.log"
MAX_BYTES: Final[int] = 512 * 1024
BACKUPS: Final[int] = 3
FORMAT: Final[str] = "%(asctime)s %(levelname)-7s %(threadName)s %(message)s"
_state: dict[str, str] = {"folder": "", "problem": ""}


def get() -> logging.Logger:
    """The generator's logger."""
    return logging.getLogger(NAME)


def status() -> str:
    """Why there is no log file, or an empty string when there is one."""
    return _state["problem"]


def start(data: Path) -> None:
    """Write the log into ``data`` from now on, once per folder, opening with who wrote it."""
    folder = str(data)
    if _state["folder"] == folder:
        return
    logger = get()
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _state.update(folder=folder, problem="")
    try:
        data.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            data / FILE, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8"
        )
    except OSError as error:
        _state["problem"] = f"{type(error).__name__}: {error}"
        return
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    logger.info(
        "start generator %s, algorithm epoch %d, Python %s, %s%s",
        __version__,
        epoch.CURRENT,
        platform.python_version(),
        platform.platform(),
        ", packaged" if getattr(sys, "frozen", False) else "",
    )


def stop() -> None:
    """Close the log file (tests and the end of a command)."""
    logger = get()
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            with contextlib.suppress(OSError):
                handler.close()
    _state.update(folder="", problem="")
