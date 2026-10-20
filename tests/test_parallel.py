"""Thread counts: bounded by cores, by free memory, and overridable."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from rnw import parallel

if TYPE_CHECKING:
    import pytest


def test_workers_follow_the_cores_and_the_free_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """The count never exceeds the cap or what the free memory holds, and is at least one."""
    monkeypatch.delenv(parallel.ENVIRONMENT, raising=False)
    monkeypatch.setattr(parallel, "available_memory", lambda: 10 * parallel.GIB)
    monkeypatch.setattr(os, "cpu_count", lambda: 32)
    monkeypatch.setattr(os, "process_cpu_count", lambda: 32, raising=False)
    assert parallel.worker_count(8) == 8
    assert parallel.worker_count(8, bytes_each=4 * parallel.GIB) == 2
    assert parallel.worker_count(8, bytes_each=64 * parallel.GIB) == 1
    monkeypatch.setattr(parallel, "available_memory", lambda: None)
    assert parallel.worker_count(8, bytes_each=4 * parallel.GIB) == 8


def test_the_environment_overrides_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """RNW_THREADS fixes the count, for benchmarks and for thread-independence tests."""
    monkeypatch.setenv(parallel.ENVIRONMENT, "3")
    assert parallel.worker_count(8, bytes_each=1 << 50) == 3
    monkeypatch.setenv(parallel.ENVIRONMENT, "0")
    assert parallel.worker_count(8) == 1
