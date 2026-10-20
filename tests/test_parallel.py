"""Threads and memory the export may use: read from the machine, bounded, overridable."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from rnw import parallel

if TYPE_CHECKING:
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
