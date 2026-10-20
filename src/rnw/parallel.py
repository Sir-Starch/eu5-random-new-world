"""How many threads independent work may use.

Output never depends on this number: tasks write disjoint results that are merged in a
fixed order ([ADR 0005](docs/adr/0005-native-core.md)). ``RNW_THREADS`` overrides it, for
benchmarks and for tests that compare one thread with many.
"""

from __future__ import annotations

import os
from typing import Final

ENVIRONMENT: Final[str] = "RNW_THREADS"


def worker_count(cap: int) -> int:
    """Threads for memory-heavy independent tasks: the available cores, at most ``cap``."""
    override = os.environ.get(ENVIRONMENT)
    if override is not None:
        return max(1, int(override))
    cores = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    return max(1, min(cap, cores))
