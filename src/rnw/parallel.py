"""How many threads and how much memory the export may use on this machine.

Output never depends on these numbers: tasks write disjoint results that are merged in a
fixed order and every band of a banded kernel carries the halo its neighbours need
([ADR 0005](docs/adr/0005-native-core.md)). They are read from the machine each time:
the cores this process may run on (affinity and container quota), and the memory that is
free now (the operating system's available figure, capped by a container limit).
``RNW_THREADS`` and ``RNW_MEMORY`` (mebibytes) override them, for benchmarks and for tests
that compare one thread or a tiny budget with many.
"""

# ctypes types its structure fields as Any.
# pyright: reportAny=false

from __future__ import annotations

import contextlib
import ctypes
import os
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Final, Self

from rnw import _native
from rnw.progress import checkpoint, run_stage

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

ENVIRONMENT: Final[str] = "RNW_THREADS"
MEMORY_ENVIRONMENT: Final[str] = "RNW_MEMORY"
GIB: Final[int] = 1 << 30
MIB: Final[int] = 1 << 20
# One core stays free for the desktop on machines that have a few; below this there is no
# core to spare.
SPARE_CORE_FROM: Final[int] = 4
# Taken as free when the system will not say; the minimum EU5 system has 16 GB.
UNKNOWN_MEMORY: Final[int] = 4 * GIB
# Share of the free memory that bands and workers may fill; the rest is headroom for the
# desktop, the file cache and estimates that are too small.
BUDGET_SHARE_PERMILLE: Final[int] = 600
CGROUP: Final[Path] = Path("/sys/fs/cgroup")
# glibc's mallopt parameter for the number of arenas and the number we allow.
M_ARENA_MAX: Final[int] = -8
MALLOC_ARENAS: Final[int] = 2


class MemoryStatus(ctypes.Structure):
    """``MEMORYSTATUSEX``: two 32-bit words and seven 64-bit counters.

    The words are ``c_uint32``, not ``c_ulong``, which is 64 bits wide on Linux and macOS.
    """

    _fields_: tuple[tuple[str, type], ...] = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ("length", ctypes.c_uint32),
        ("load", ctypes.c_uint32),
        ("total", ctypes.c_ulonglong),
        ("available", ctypes.c_ulonglong),
        ("page_total", ctypes.c_ulonglong),
        ("page_available", ctypes.c_ulonglong),
        ("virtual_total", ctypes.c_ulonglong),
        ("virtual_available", ctypes.c_ulonglong),
        ("extended", ctypes.c_ulonglong),
    )


def _read_number(path: Path) -> int | None:
    """The integer in a small system file, or None for a missing file or a word like ``max``."""
    try:
        return int(path.read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _meminfo_available() -> int | None:
    """``MemAvailable`` of ``/proc/meminfo``: free memory plus what the kernel can reclaim."""
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _cgroup_directory() -> Path:
    """The memory-controlling cgroup (v2) of this process, or the unified root."""
    try:
        for line in Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines():
            if line.startswith("0::"):
                return CGROUP / line[3:].lstrip("/")
    except OSError:
        pass
    return CGROUP


def _cgroup_headroom() -> int | None:
    """Bytes a container limit still leaves, or None where there is no limit."""
    directory = _cgroup_directory()
    limit = _read_number(directory / "memory.max")  # v2; "max" reads as None
    used = _read_number(directory / "memory.current")
    if limit is None:  # v1
        limit = _read_number(CGROUP / "memory" / "memory.limit_in_bytes")
        used = _read_number(CGROUP / "memory" / "memory.usage_in_bytes")
    if limit is None or used is None or limit >= 1 << 60:
        return None
    return max(0, limit - used)


def available_memory() -> int | None:
    """Bytes of memory free for new allocations, or None where the system will not say."""
    override = os.environ.get(MEMORY_ENVIRONMENT)
    if override is not None:
        return max(1, int(override)) * MIB
    if sys.platform == "win32":
        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        windll = getattr(ctypes, "windll", None)
        if windll is None or not windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return int(status.available)
    figures = [_meminfo_available(), _cgroup_headroom()]
    if figures[0] is None:
        with contextlib.suppress(ValueError, OSError, AttributeError):
            figures[0] = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    known = [figure for figure in figures if figure is not None]
    return min(known) if known else None


class ResourceError(RuntimeError):
    """The machine has less than a task needs."""


def require_memory(needed: int, task: str) -> None:
    """Refuse a task that needs more free memory than the machine has, before it starts.

    Where the system will not say how much is free, the task is allowed to start.
    """
    free = available_memory()
    if free is not None and free < needed:
        message = (
            f"{task} needs about {needed / GIB:.1f} GiB of free memory and this machine has "
            f"{free / GIB:.1f} GiB free; close other programs and run it again"
        )
        raise ResourceError(message)


def memory_budget() -> int:
    """Bytes the next stage may fill with working memory: a share of what is free now."""
    free = available_memory()
    return (UNKNOWN_MEMORY if free is None else free) * BUDGET_SHARE_PERMILLE // 1000


def _quota_cores() -> int | None:
    """Cores a container's CPU quota allows (rounded up), or None without a quota."""
    try:
        quota, _, period = (CGROUP / "cpu.max").read_text(encoding="ascii").partition(" ")
        if quota.strip() == "max":
            return None
        return max(1, -(-int(quota) // int(period)))
    except (OSError, ValueError):
        return None


def cores() -> int:
    """Hardware threads this process may run on: its affinity, within a container quota."""
    affinity = getattr(os, "sched_getaffinity", None)
    count = len(affinity(0)) if affinity is not None else (os.cpu_count() or 1)
    quota = _quota_cores()
    return max(1, min(count, quota) if quota is not None else count)


def thread_count() -> int:
    """Threads for the whole export: the cores, one fewer from four cores up."""
    override = os.environ.get(ENVIRONMENT)
    if override is not None:
        return max(1, int(override))
    available = cores()
    return available - 1 if available >= SPARE_CORE_FROM else available


def limit_malloc_arenas() -> None:
    """Keep glibc's allocator from giving every thread an arena of its own.

    Each arena holds on to the memory freed in it, and a pool of 30 threads that build
    and drop 100 MB buffers kept 1.5 GiB resident that nothing used; two arenas gave the
    same output and speed with a peak of 6.9 instead of 8.4 GiB [V-EXEC C102]. Other
    platforms and C libraries have no such setting and need none.
    """
    if sys.platform.startswith("linux"):
        with contextlib.suppress(OSError, AttributeError):
            _ = ctypes.CDLL(None).mallopt(M_ARENA_MAX, MALLOC_ARENAS)


def configure() -> int:
    """Size the native thread pool to ``thread_count()``; returns the size in force.

    Only the first call before a kernel has run can resize the pool, so a process that
    already ran one keeps its pool. The pool size never changes a result.
    """
    limit_malloc_arenas()
    return _native.configure_threads(thread_count())


def worker_count(cap: int, *, bytes_each: int = 0) -> int:
    """Threads for memory-heavy independent tasks.

    At most ``thread_count()`` and ``cap`` and, when each task needs about ``bytes_each``,
    no more than the memory budget holds.
    """
    workers = min(cap, thread_count())
    if bytes_each and os.environ.get(ENVIRONMENT) is None:
        workers = min(workers, memory_budget() // bytes_each)
    return max(1, workers)


def band_rows(row_bytes: int, *, workers: int, floor: int, ceiling: int, reserved: int = 0) -> int:
    """Rows per band so that ``workers`` bands in flight fit the memory budget.

    ``row_bytes`` is the working memory one row of a band takes, ``reserved`` what the
    caller holds besides the bands. The result lies in ``[floor, ceiling]``: a machine
    short of memory gets thin bands, never an error here; the preflight check reports a
    machine that cannot hold the minimum.
    """
    room = max(0, memory_budget() - reserved) // max(1, workers * row_bytes)
    return max(floor, min(ceiling, room))


# Free memory from which stages of a job may overlap: the default export peaks at 6.9 GiB
# with them and 6.3 GiB without [V-EXEC C102]; the rest is headroom for the desktop.
OVERLAP_MEMORY: Final[int] = 10 * GIB
OVERLAP_STAGES: Final[int] = 4


def stage_workers() -> int:
    """How many stages of a job may run at once on this machine (1 = one after the other).

    Overlap needs a few spare cores and the memory for the stages' working sets together;
    where the system will not say how much memory is free, stages do not overlap.
    """
    if thread_count() < OVERLAP_STAGES:
        return 1
    free = available_memory()
    if free is None or free < OVERLAP_MEMORY:
        return 1
    return OVERLAP_STAGES


class Stages:
    """Runs the independent stages of a job on a few threads, or one after the other.

    With one worker ``submit`` runs a stage at once, so the job is the plain sequence of
    its calls; with more, a stage starts when a worker is free and the job goes on. A stage
    may wait (``Future.result``) only for stages submitted before it: the pool starts
    stages in submission order, so a waited-for stage is already running or done and
    waiting cannot deadlock.
    """

    def __init__(self, workers: int) -> None:
        self._pool: ThreadPoolExecutor | None = (
            ThreadPoolExecutor(max_workers=workers) if workers > 1 else None
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=exc is not None)

    def submit[T](self, name: str, work: Callable[[], T]) -> Future[T]:
        """Start ``work`` as the stage ``name`` and return its future."""
        checkpoint()
        if self._pool is not None:
            return self._pool.submit(run_stage, name, work)
        future: Future[T] = Future()
        try:
            future.set_result(run_stage(name, work))
        except BaseException as error:  # noqa: BLE001 - re-raised by result()
            future.set_exception(error)
        return future
