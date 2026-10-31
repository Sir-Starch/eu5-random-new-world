"""Deterministic replay of parallel, cached, slow and stalled generation clocks."""

from __future__ import annotations

import json
from itertools import pairwise
from typing import TYPE_CHECKING, cast

import pytest

from rnw.app import estimates
from rnw.eta import DEPENDENCIES, REFERENCE_SECONDS, Estimate
from rnw.progress import STAGES, Progress

if TYPE_CHECKING:
    from pathlib import Path


def _model() -> Estimate:
    return Estimate(0.0)


def _schedule(*, speed: float = 1.0) -> list[tuple[float, bool, str]]:
    """An ideal pipeline, including stages submitted before their inputs are ready."""
    ends: dict[str, float] = {}
    events: list[tuple[float, bool, str]] = []
    for name, dependencies in DEPENDENCIES.items():
        ready = max((ends[dep] for dep in dependencies), default=0.0)
        end = ready + REFERENCE_SECONDS[name] * speed
        ends[name] = end
        # Real identities and climate stages start before their inputs finish.
        start = 6.0 * speed if name in {"vanilla climate", "identities"} else ready
        events.extend(((start, False, name), (end, True, name)))
        if name == "generate world":
            events.append((start, False, "land cells"))
    return sorted(events, key=lambda event: (event[0], not event[1]))


def _replay(model: Estimate, events: list[tuple[float, bool, str]]) -> list[float]:
    errors: list[float] = []
    end = max(time for time, _, _ in events)
    for time, finished, name in events:
        if finished:
            model.finish(name, time, completed=True)
        else:
            model.begin(name, time)
        errors.append(abs(model.remaining(time) - (end - time)))
    return errors


def test_eta_graph_covers_every_weighted_stage_without_nested_double_counting() -> None:
    seen: set[str] = set()
    for name, dependencies in DEPENDENCIES.items():
        assert set(dependencies) <= seen
        seen.add(name)
    assert {name for name, info in STAGES.items() if info.weight} == seen - {"install"}
    assert "terrain" not in seen
    assert "relief" not in seen
    assert _model().remaining(0) < sum(REFERENCE_SECONDS.values())


def test_parallel_reference_replay_and_learning_exclude_input_waits() -> None:
    model = _model()
    model.configure({}, install=True)
    errors = _replay(model, _schedule())
    assert max(errors) < 5
    assert model.costs["identities"] == REFERENCE_SECONDS["identities"]
    assert model.costs["vanilla climate"] == REFERENCE_SECONDS["vanilla climate"]
    assert model.remaining(10000) == 0


def test_machine_history_improves_a_slower_run_from_the_first_prediction() -> None:
    events = _schedule(speed=3)
    trained = _model()
    trained.configure({}, install=True)
    _ = _replay(trained, events)
    cold = _model()
    cold.configure({}, install=True)
    learned = _model()
    learned.configure(trained.costs, install=True)
    expected = max(time for time, _, _ in events)
    assert abs(learned.remaining(0) - expected) < 0.01
    assert cold.remaining(0) < expected / 2
    assert max(_replay(learned, events)) < 5


def test_polling_counts_down_and_overdue_corrections_do_not_grow_every_second() -> None:
    model = _model()
    model.begin("load map", 0)
    first = model.remaining(0)
    for time in range(1, 10):
        assert model.remaining(time) == pytest.approx(first - time)
    values = [model.remaining(float(time)) for time in range(10, 100)]
    increases = sum(right > left for left, right in pairwise(values))
    assert 0 < increases < 10
    assert all(value > 0 for value in values)


def test_cancelled_or_failed_stage_does_not_train_and_reset_forgets_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr("rnw.progress.time.monotonic", lambda: clock[0])
    job = Progress()
    job.begin("load map")
    clock[0] = 10
    job.finish("load map", completed=False)
    assert not job.stage_costs()
    clock[0] = 100
    job.reset_stages()
    assert job.estimated_remaining() == pytest.approx(_model().remaining(0))
    assert not job.stage_costs()


def test_training_is_bounded_robust_and_ignores_cached_worlds(tmp_path: Path) -> None:
    for index in range(9):
        estimates.save(tmp_path, "machine", {"write files": 4, "generate world": 25 + index})
    estimates.save(tmp_path, "machine", {"write files": 4, "generate world": 0.1})
    assert estimates.load(tmp_path, "machine")["generate world"] == 31
    estimates.save(tmp_path, "machine", {"load map": 400})  # incomplete run
    assert "load map" not in estimates.load(tmp_path, "machine")
    assert not list(tmp_path.glob(".*.new"))
    for index in range(estimates.CONTEXTS + 3):
        estimates.save(tmp_path, str(index), {"write files": 4})
    raw = cast("dict[str, object]", json.loads((tmp_path / estimates.FILE).read_text()))
    assert len(raw) == estimates.CONTEXTS
    assert "machine" not in raw


@pytest.mark.parametrize("content", ["[]", "null", "{", '{"machine": []}'])
def test_broken_timing_history_is_optional(tmp_path: Path, content: str) -> None:
    _ = (tmp_path / estimates.FILE).write_text(content)
    assert estimates.load(tmp_path, "machine") == {}


def test_invalid_samples_and_outliers_do_not_poison_the_median(tmp_path: Path) -> None:
    _ = (tmp_path / estimates.FILE).write_text(
        '{"machine": {"load map": [true, -1, "bad", NaN, 2, 3, 9999], "bogus": [2]}}'
    )
    assert estimates.load(tmp_path, "machine") == {"load map": 3}


def test_storage_failure_does_not_fail_the_generated_world(tmp_path: Path) -> None:
    _ = (tmp_path / estimates.FILE).mkdir()
    estimates.save(tmp_path, "machine", {"write files": 4})
    assert estimates.load(tmp_path, "machine") == {}


def test_cache_hit_and_game_lock_wait_do_not_train_expensive_work() -> None:
    model = _model()
    model.begin("load map", 0)
    model.finish("load map", 3, completed=True)
    model.begin("select canvas", 3)
    model.finish("select canvas", 9, completed=True)
    model.begin("generate world", 9)
    model.finish("generate world", 13, completed=True)
    assert "generate world" not in model.costs
    assert "generate world" in model.ends
    trained = _model()
    trained.configure({}, install=True)
    for time, finished, name in _schedule():
        if name == "install" and not finished:
            trained.begin("waiting for the game", time)
        if finished:
            trained.finish(name, time, completed=True)
        else:
            trained.begin(name, time)
    assert "install" not in trained.costs
    assert "write files" in trained.costs


def test_history_separates_presets_and_game_builds() -> None:
    assert estimates.key("one", "continents") != estimates.key("two", "continents")
    assert estimates.key("one", "continents") != estimates.key("one", "wall")
