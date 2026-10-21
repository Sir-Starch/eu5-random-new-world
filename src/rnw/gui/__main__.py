"""Start the application: ``rnw-gui``, ``python -m rnw.gui`` or the packaged program.

``--self-test`` opens the window without showing it, checks that the native kernels and
the world codes work, and exits with 0: the packaging jobs run it on the built folder.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from rnw import __version__, _native
from rnw.app.worldcode import decode, encode, new_code
from rnw.gui.controller import Controller
from rnw.gui.text import TITLE
from rnw.gui.window import MainWindow

if TYPE_CHECKING:
    from collections.abc import Sequence

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


def main(argv: Sequence[str] | None = None) -> int:
    """Open the window, look for the game and profile, run until it is closed."""
    arguments = list(sys.argv if argv is None else argv)
    application = QApplication(arguments)
    application.setApplicationName(TITLE)
    controller = Controller()
    if SELF_TEST in arguments:
        return self_test(application, controller)
    window = MainWindow(controller)
    window.resize(WIDTH, HEIGHT)
    controller.discover()
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
