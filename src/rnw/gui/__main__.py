"""Start the application: ``rnw-gui``, ``python -m rnw.gui`` or the packaged program.

``--self-test`` opens the window without showing it, checks that the native kernels and
the world codes work, and exits with 0: the packaging jobs run it on the built folder.
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
from rnw.gui.text import TITLE
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


def main(argv: Sequence[str] | None = None) -> int:
    """Open the window, look for the game and profile, run until it is closed."""
    arguments = list(sys.argv if argv is None else argv)
    application = QApplication(arguments)
    application.setApplicationName(TITLE)
    sys.excepthook = _log_uncaught
    threading.excepthook = _log_thread
    if SELF_TEST in arguments:
        with TemporaryDirectory(prefix="rnw-self-test-") as temporary:
            return self_test(application, Controller(data=Path(temporary)))
    controller = Controller(program_folder=paths.program_directory())
    window = MainWindow(controller)
    window.resize(WIDTH, HEIGHT)
    controller.discover()
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
