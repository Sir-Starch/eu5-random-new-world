"""Entry point of the packaged application (PyInstaller starts this file)."""

from __future__ import annotations

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from rnw.cli import app

        del sys.argv[1]
        app()
    else:
        from rnw.gui.__main__ import main

        sys.exit(main())
