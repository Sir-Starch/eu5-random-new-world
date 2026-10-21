"""Entry point of the packaged application (PyInstaller starts this file)."""

from __future__ import annotations

import sys

from rnw.gui.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
