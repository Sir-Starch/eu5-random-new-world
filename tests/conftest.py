"""Test configuration shared by every test module."""

from __future__ import annotations

import os

# Qt windows are tested without a display (tests/test_window.py).
_ = os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
