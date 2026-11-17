"""Wall-clock stage timing for benchmarks, printed to stderr when ``RNW_TIMING`` is set.

A line gives the stage, how long it took, when it began and the process's peak memory so far.

Nothing here reaches the generated files, so timing never changes a result.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

try:  # the resource module does not exist on Windows
    import resource
except ImportError:  # pragma: no cover
    resource = None

ENVIRONMENT: Final[str] = "RNW_TIMING"
STARTED: Final[float] = time.perf_counter()
TRACE: Final[str] = "RNW_TRACE"
_LOCAL: Final[threading.local] = threading.local()
_LOCK: Final[threading.Lock] = threading.Lock()
_IDS: Final = count()


@dataclass
class _Span:
    number: int
    children: float = 0.0
    child_cpu: float = 0.0


@contextmanager
def span(name: str) -> Generator[None]:
    """Optional nested JSONL wall/thread-CPU spans, including workers in strip pools.

    Thread CPU excludes rayon's other threads; wall time includes native work and waits.
    Exclusive values subtract synchronous children on this thread only. The timestamps
    expose overlap; they must not be summed as elapsed generation time.
    """
    trace = os.environ.get(TRACE)
    if not trace:
        yield
        return
    stack: list[_Span] = getattr(_LOCAL, "stack", [])
    _LOCAL.stack = stack
    parent = stack[-1] if stack else None
    with _LOCK:
        current = _Span(next(_IDS))
    stack.append(current)
    start, cpu = time.perf_counter(), time.thread_time()
    completed = False
    try:
        yield
        completed = True
    finally:
        wall, cpu = time.perf_counter() - start, time.thread_time() - cpu
        _ = stack.pop()
        if parent is not None:
            parent.children += wall
            parent.child_cpu += cpu
        if trace:
            row = {
                "id": current.number,
                "parent": None if parent is None else parent.number,
                "name": name,
                "thread": threading.get_ident(),
                "start": start - STARTED,
                "seconds": wall,
                "exclusive_seconds": wall - current.children,
                "thread_cpu_seconds": cpu,
                "exclusive_thread_cpu_seconds": cpu - current.child_cpu,
                "completed": completed,
                "peak_gib": peak_gib(),
            }
            with _LOCK:
                path = Path(trace)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as stream:
                    _ = stream.write(json.dumps(row) + "\n")


def measured[**P, T](work: Callable[P, T]) -> Callable[P, T]:
    """Trace a hot function without changing its arguments or generated data."""
    name = f"{work.__module__}.{work.__qualname__}"

    @wraps(work)
    def call(*args: P.args, **kwargs: P.kwargs) -> T:
        if not os.environ.get(TRACE):
            return work(*args, **kwargs)
        with span(name):
            return work(*args, **kwargs)

    return call


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
        with span(name):
            return work()
    start = time.perf_counter()
    try:
        with span(name):
            return work()
    finally:
        took, began = time.perf_counter() - start, start - STARTED
        print(
            f"[timing] {name}: {took:.1f} s (from {began:.1f} s){peak_gib()}",
            file=sys.stderr,
            flush=True,
        )
