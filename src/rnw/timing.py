"""Wall-clock stage timing for benchmarks, printed to stderr when ``RNW_TIMING`` is set.

Nothing here reaches the generated files, so timing never changes a result.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Final

ENVIRONMENT: Final[str] = "RNW_TIMING"


class Clock:
    """Reports the time since the previous lap, or since creation, under a stage name."""

    __slots__: tuple[str, ...] = ("_last", "_on")

    def __init__(self) -> None:
        self._on: bool = bool(os.environ.get(ENVIRONMENT))
        self._last: float = time.perf_counter()

    def lap(self, name: str) -> None:
        """Print the seconds since the last lap when timing is on."""
        now = time.perf_counter()
        if self._on:
            print(f"[timing] {name}: {now - self._last:.1f} s", file=sys.stderr, flush=True)
        self._last = now
