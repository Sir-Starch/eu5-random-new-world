"""Diagnostics cover worker work and nested spans without changing the result."""

# JSON rows are deliberately inspected dynamically.
# pyright: reportAny=false
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from rnw.timing import measured, span, timed

if TYPE_CHECKING:
    from pathlib import Path


@measured
def _answer() -> int:
    return 42


def test_trace_is_optional(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RNW_TRACE", raising=False)
    monkeypatch.delenv("RNW_PROFILE", raising=False)
    assert timed("outer", _answer) == 42
    assert not list(tmp_path.iterdir())


def test_nested_worker_spans_and_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    trace = tmp_path / "trace.jsonl"
    monkeypatch.setenv("RNW_TRACE", str(trace))
    with span("main"), ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(timed, "worker", _answer) for _ in range(2)]
        assert [future.result() for future in futures] == [42, 42]
        message = "test"
        with pytest.raises(ValueError, match="test"), span("failed"):
            raise ValueError(message)
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len(rows) == 6
    assert len({row["id"] for row in rows}) == 6
    assert all(0 <= row["exclusive_seconds"] <= row["seconds"] for row in rows)
    assert all(row["thread_cpu_seconds"] >= 0 for row in rows)
    failed = next(row for row in rows if row["name"] == "failed")
    main = next(row for row in rows if row["name"] == "main")
    assert not failed["completed"]
    assert failed["parent"] == main["id"]
