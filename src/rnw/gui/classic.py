"""The classic Qt window (ADR 0007): kept beside the Tauri window, which opens first, for when
that window cannot open or the classic one is chosen (``rnw.gui.start``).

Its self-test opens the window without showing it, checks that the native kernels and the world
codes work, and exits with 0.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from rnw import __version__, _native
from rnw.app import logs, paths
from rnw.app.worldcode import decode, encode, new_code
from rnw.gui.controller import Controller
from rnw.gui.text import TITLE, set_language
from rnw.gui.window import MainWindow

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType

WIDTH, HEIGHT = 1080, 760
SELF_TEST = "--self-test"


def self_test(application: QApplication, controller: Controller) -> int:
    """Check the parts a broken package would miss; returns the exit code."""
    window = MainWindow(controller)
    application.processEvents()
    code = new_code("continents", 42)
    if decode(encode(code)) != code:
        return 1
    if _native.configure_threads(1) < 1:
        return 1
    _ = window.close()
    print(f"{TITLE} {__version__}: window, native kernels and world codes work")
    return 0


def _log_uncaught(
    kind: type[BaseException], value: BaseException, trace: TracebackType | None
) -> None:
    """Put an error nothing caught into the log, with its traceback, then let Python print it."""
    logs.get().critical("uncaught %s", kind.__name__, exc_info=(kind, value, trace))
    sys.__excepthook__(kind, value, trace)


def _log_thread(arguments: threading.ExceptHookArgs) -> None:
    value = arguments.exc_value
    if arguments.exc_type is not SystemExit and value is not None:
        logs.get().critical(
            "uncaught %s in thread %s",
            arguments.exc_type.__name__,
            arguments.thread.name if arguments.thread else "?",
            exc_info=(arguments.exc_type, value, arguments.exc_traceback),
        )


def main(argv: Sequence[str] | None = None, *, instead: str = "") -> int:
    """Open the window, look for the game and profile, run until it is closed. ``instead`` is
    why the Tauri window did not open, for the log."""
    arguments = list(sys.argv if argv is None else argv)
    application = QApplication(arguments)
    application.setApplicationName(TITLE)
    sys.excepthook = _log_uncaught
    threading.excepthook = _log_thread
    if SELF_TEST in arguments:
        with TemporaryDirectory(prefix="rnw-self-test-") as temporary:
            try:
                return self_test(application, Controller(data=Path(temporary)))
            finally:
                logs.stop()  # Windows cannot remove the folder while the log is open.
    controller = Controller(program_folder=paths.program_directory())
    if instead:
        logs.get().info("the classic window opens: %s", instead)
    set_language(controller.window_language())
    window = MainWindow(controller)
    window.resize(WIDTH, HEIGHT)
    controller.discover()
    window.show()
    return application.exec()
