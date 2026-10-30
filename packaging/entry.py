"""Entry point of the packaged application (PyInstaller starts this file).

``--cli`` runs the command line, ``--bridge`` serves the Tauri window in ``window/`` (it starts
the program so), and anything else opens a window (``rnw.gui``).
"""

from __future__ import annotations

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from rnw.cli import app

        del sys.argv[1]
        app()
    elif len(sys.argv) > 1 and sys.argv[1] == "--bridge":
        from rnw.gui.bridge import main as bridge

        sys.exit(bridge(sys.argv[2:]))
    else:
        from rnw.gui.__main__ import main

        sys.exit(main())
