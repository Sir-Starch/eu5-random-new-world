"""Threads and memory the export may use: read from the machine, bounded, overridable."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
from typing import TYPE_CHECKING, cast

import pytest

from rnw import parallel, timing

if TYPE_CHECKING:
    from concurrent.futures import Future
    from pathlib import Path


def _machine(monkeypatch: pytest.MonkeyPatch, *, cores: int, free: int | None) -> None:
    monkeypatch.delenv(parallel.ENVIRONMENT, raising=False)
    monkeypatch.delenv(parallel.MEMORY_ENVIRONMENT, raising=False)
    monkeypatch.setattr(parallel, "cores", lambda: cores)
    monkeypatch.setattr(parallel, "available_memory", lambda: free)


def test_one_core_stays_free_from_four_cores_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Small machines use every core, bigger ones leave one to the desktop."""
    for cores, expected in ((1, 1), (2, 2), (3, 3), (4, 3), (12, 11), (64, 63)):
        _machine(monkeypatch, cores=cores, free=None)
        assert parallel.thread_count() == expected


def test_workers_follow_the_threads_and_the_memory_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """The count never exceeds the cap, the threads or what the budget holds; at least one."""
    _machine(monkeypatch, cores=32, free=10 * parallel.GIB)
    assert parallel.memory_budget() == 6 * parallel.GIB
    assert parallel.worker_count(8) == 8
    assert parallel.worker_count(64) == 31
    assert parallel.worker_count(8, bytes_each=2 * parallel.GIB) == 3
    assert parallel.worker_count(8, bytes_each=64 * parallel.GIB) == 1
    _machine(monkeypatch, cores=32, free=None)
    assert parallel.memory_budget() == parallel.UNKNOWN_MEMORY * 6 // 10
    assert parallel.worker_count(8, bytes_each=parallel.GIB) == 2


def test_bands_shrink_with_the_memory_and_grow_with_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """A band holds as many rows as keep the workers inside the budget, within the limits."""
    _machine(monkeypatch, cores=8, free=10 * parallel.GIB)
    budget = parallel.memory_budget()
    row = budget // (4 * 1000)  # four workers, one thousand rows fill the budget
    assert parallel.band_rows(row, workers=4, floor=16, ceiling=5000) == 1000
    assert parallel.band_rows(row, workers=4, floor=16, ceiling=300) == 300
    assert parallel.band_rows(row, workers=4, floor=16, ceiling=5000, reserved=budget // 2) == 500
    assert parallel.band_rows(budget, workers=4, floor=16, ceiling=5000) == 16
    assert parallel.band_rows(row, workers=4, floor=16, ceiling=5000, reserved=10 * budget) == 16


def test_the_environment_overrides_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """RNW_THREADS fixes the count and RNW_MEMORY the free memory, for benchmarks and tests."""
    monkeypatch.setenv(parallel.ENVIRONMENT, "3")
    assert parallel.thread_count() == 3
    assert parallel.worker_count(8, bytes_each=1 << 50) == 3
    monkeypatch.setenv(parallel.ENVIRONMENT, "0")
    assert parallel.worker_count(8) == 1
    monkeypatch.setenv(parallel.MEMORY_ENVIRONMENT, "512")
    assert parallel.available_memory() == 512 * parallel.MIB
    assert parallel.memory_budget() == 512 * parallel.MIB * 6 // 10


def test_the_real_machine_reports_something_sane(monkeypatch: pytest.MonkeyPatch) -> None:
    """On this machine the figures are positive and the budget fits in the memory."""
    monkeypatch.delenv(parallel.ENVIRONMENT, raising=False)
    monkeypatch.delenv(parallel.MEMORY_ENVIRONMENT, raising=False)
    assert 1 <= parallel.cores() <= (os.cpu_count() or 1)
    assert parallel.thread_count() >= 1
    free = parallel.available_memory()
    assert free is None or free > 0
    assert parallel.memory_budget() > 0


def test_a_container_limit_caps_the_free_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The smaller of the system's available figure and the cgroup headroom wins."""
    _ = (tmp_path / "memory.max").write_text("8589934592\n", encoding="ascii")
    _ = (tmp_path / "memory.current").write_text("6442450944\n", encoding="ascii")
    monkeypatch.setattr(parallel, "_cgroup_directory", lambda: tmp_path)
    assert parallel._cgroup_headroom() == 2 * parallel.GIB  # pyright: ignore[reportPrivateUsage]
    _ = (tmp_path / "memory.max").write_text("max\n", encoding="ascii")
    assert parallel._cgroup_headroom() is None  # pyright: ignore[reportPrivateUsage]
    _ = (tmp_path / "cpu.max").write_text("150000 100000\n", encoding="ascii")
    monkeypatch.setattr(parallel, "CGROUP", tmp_path)
    assert parallel._quota_cores() == 2  # pyright: ignore[reportPrivateUsage]
    _ = (tmp_path / "cpu.max").write_text("max 100000\n", encoding="ascii")
    assert parallel._quota_cores() is None  # pyright: ignore[reportPrivateUsage]


def test_the_native_pool_takes_the_first_size_asked() -> None:
    """A fresh process gets the pool it asks for; a later request reports the one in force."""
    code = (
        "from rnw import _native\n"
        "print(_native.configure_threads(3), _native.configure_threads(5))\n"
    )
    done = subprocess.run(  # noqa: S603 - our own interpreter and a fixed program
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert done.stdout.split() == ["3", "3"]


def test_a_task_that_needs_more_memory_than_is_free_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal names the need and the free memory; unknown memory lets the task start."""
    monkeypatch.delenv(parallel.MEMORY_ENVIRONMENT, raising=False)
    monkeypatch.setattr(parallel, "available_memory", lambda: 5 * parallel.GIB)
    parallel.require_memory(5 * parallel.GIB, "A task")
    with pytest.raises(parallel.ResourceError, match=r"needs about 6\.0 GiB .* 5\.0 GiB free"):
        parallel.require_memory(6 * parallel.GIB, "A task")
    monkeypatch.setattr(parallel, "available_memory", lambda: None)
    parallel.require_memory(1 << 60, "A task")


def test_stages_run_in_submission_order_on_one_worker() -> None:
    """With one worker a stage has run when submit returns, so a job reads as a sequence."""
    order: list[str] = []

    def stage(name: str) -> str:
        order.append(name)
        return name

    with parallel.Stages(1) as stages:
        first = stages.submit("first", lambda: stage("first"))
        assert order == ["first"]
        second = stages.submit("second", lambda: stage("second") + first.result())
    assert order == ["first", "second"]
    assert second.result() == "secondfirst"


def test_stages_overlap_and_may_wait_for_earlier_ones() -> None:
    """Stages on several workers run at once; one may wait for a stage submitted before it."""
    started = threading.Barrier(2, timeout=10)

    def slow() -> int:
        _ = started.wait()
        return 7

    def waiting(earlier: Future[int]) -> int:
        _ = started.wait()
        return earlier.result() * 6

    with parallel.Stages(2) as stages:
        first = stages.submit("slow", slow)
        second = stages.submit("waiting", lambda: waiting(first))
    assert (first.result(), second.result()) == (7, 42)


def test_a_failing_stage_raises_where_its_result_is_read() -> None:
    """The error of a stage surfaces at result(), on one worker and on several."""

    def boom() -> int:
        message = "stage failed"
        raise ValueError(message)

    for workers in (1, 3):
        with parallel.Stages(workers) as stages:
            future = stages.submit("boom", boom)
            with pytest.raises(ValueError, match="stage failed"):
                _ = future.result()


def test_stages_overlap_only_on_a_machine_with_cores_and_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Four threads and 10 GiB free allow overlap; fewer threads, less memory or an unknown
    amount of memory run the stages one after the other."""
    _machine(monkeypatch, cores=8, free=12 * parallel.GIB)
    assert parallel.stage_workers() == parallel.OVERLAP_STAGES
    _machine(monkeypatch, cores=8, free=9 * parallel.GIB)
    assert parallel.stage_workers() == 1
    _machine(monkeypatch, cores=8, free=None)
    assert parallel.stage_workers() == 1
    _machine(monkeypatch, cores=3, free=64 * parallel.GIB)
    assert parallel.stage_workers() == 1


def test_timed_reports_a_stage_only_when_timing_is_on(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The result is the stage's result either way; the report goes to standard error."""
    monkeypatch.delenv("RNW_TIMING", raising=False)
    assert timing.timed("quiet", lambda: 5) == 5
    assert capsys.readouterr().err == ""
    monkeypatch.setenv("RNW_TIMING", "1")
    assert timing.timed("loud", lambda: 6) == 6
    assert "[timing] loud:" in capsys.readouterr().err


class _FakeKernel:
    """Stands in for ``ctypes.windll.kernel32`` and fills the memory status like Windows."""

    def __init__(self, available: int, *, succeeds: bool = True) -> None:
        self.available: int = available
        self.succeeds: bool = succeeds
        self.length_seen: int = 0

    def GlobalMemoryStatusEx(self, reference: object) -> int:  # noqa: N802 - the Windows name
        status = cast("parallel.MemoryStatus", getattr(reference, "_obj"))  # noqa: B009
        self.length_seen = int(cast("int", status.length))
        status.available = self.available
        return int(self.succeeds)


class _FakeWindll:
    def __init__(self, kernel: _FakeKernel) -> None:
        self.kernel32: _FakeKernel = kernel


def test_windows_memory_comes_from_the_global_memory_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On Windows the available physical memory is the figure of GlobalMemoryStatusEx."""
    monkeypatch.delenv(parallel.MEMORY_ENVIRONMENT, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    kernel = _FakeKernel(9 * parallel.GIB)
    monkeypatch.setattr(ctypes, "windll", _FakeWindll(kernel), raising=False)
    assert parallel.available_memory() == 9 * parallel.GIB
    assert kernel.length_seen == ctypes.sizeof(parallel.MemoryStatus)
    monkeypatch.setattr(
        ctypes, "windll", _FakeWindll(_FakeKernel(1, succeeds=False)), raising=False
    )
    assert parallel.available_memory() is None
    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert parallel.available_memory() is None


def test_the_memory_status_structure_has_the_windows_layout() -> None:
    """MEMORYSTATUSEX is 64 bytes: two 32-bit words, then seven 64-bit counters."""
    structure = parallel.MemoryStatus
    assert (structure.length.offset, structure.load.offset, structure.total.offset) == (0, 4, 8)
    assert structure.available.offset == 16
    assert structure.extended.offset == 56
    assert ctypes.sizeof(structure) == 64
