"""Wall-clock stage timing for benchmarks, printed to stderr when ``RNW_TIMING`` is set.

A line gives the stage, how long it took, when it began and the process's peak memory so far.

Nothing here reaches the generated files, so timing never changes a result.
"""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

try:  # the resource module does not exist on Windows
    import resource
except ImportError:  # pragma: no cover
    resource = None

ENVIRONMENT: Final[str] = "RNW_TIMING"
STARTED: Final[float] = time.perf_counter()


def peak_gib() -> str:
    """The process's peak resident memory as text, or nothing where the system will not say."""
    if resource is None:
        return ""
    kilobytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return f", peak {kilobytes / 1024 / 1024:.1f} GB"


def timed[T](name: str, work: Callable[[], T]) -> T:
    """Run ``work``; with timing on, print when it started and how long it took.

    Stages that run beside each other report their own start and duration, which a lap
    of one clock cannot.
    """
    if not os.environ.get(ENVIRONMENT):
        return work()
    start = time.perf_counter()
    try:
        return work()
    finally:
        took, began = time.perf_counter() - start, start - STARTED
        print(
            f"[timing] {name}: {took:.1f} s (from {began:.1f} s){peak_gib()}",
            file=sys.stderr,
            flush=True,
        )
