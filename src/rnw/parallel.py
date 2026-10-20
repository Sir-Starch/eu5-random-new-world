"""How many threads independent work may use.

Output never depends on this number: tasks write disjoint results that are merged in a
fixed order ([ADR 0005](docs/adr/0005-native-core.md)). ``RNW_THREADS`` overrides it, for
benchmarks and for tests that compare one thread with many.
"""

# ctypes types its structure fields as Any.
# pyright: reportAny=false

from __future__ import annotations

import ctypes
import os
import sys
from typing import Final

ENVIRONMENT: Final[str] = "RNW_THREADS"
GIB: Final[int] = 1 << 30


class _MemoryStatus(ctypes.Structure):
    _fields_: tuple[tuple[str, type], ...] = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ("length", ctypes.c_ulong),
        ("load", ctypes.c_ulong),
        ("total", ctypes.c_ulonglong),
        ("available", ctypes.c_ulonglong),
        ("page_total", ctypes.c_ulonglong),
        ("page_available", ctypes.c_ulonglong),
        ("virtual_total", ctypes.c_ulonglong),
        ("virtual_available", ctypes.c_ulonglong),
        ("extended", ctypes.c_ulonglong),
    )


def available_memory() -> int | None:
    """Bytes of memory free for new allocations, or None where the system will not say."""
    if sys.platform == "win32":
        status = _MemoryStatus()
        status.length = ctypes.sizeof(_MemoryStatus)
        windll = getattr(ctypes, "windll", None)
        if windll is None or not windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.available)
    try:
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        return None


def worker_count(cap: int, *, bytes_each: int = 0) -> int:
    """Threads for memory-heavy independent tasks.

    The available cores, at most ``cap``, and, when each task needs about ``bytes_each``,
    no more than the free memory holds.
    """
    override = os.environ.get(ENVIRONMENT)
    if override is not None:
        return max(1, int(override))
    cores = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    workers = min(cap, cores)
    free = available_memory()
    if bytes_each and free is not None:
        workers = min(workers, free // bytes_each)
    return max(1, workers)
