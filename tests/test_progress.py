"""Stage progress, weights and cancellation of a long job."""

from __future__ import annotations

import threading

import pytest

from rnw import progress
from rnw.parallel import Stages
from rnw.progress import STAGES, TOTAL_WEIGHT, Cancelled, Progress, Update


def _collect() -> tuple[Progress, list[Update]]:
    updates: list[Update] = []
    return Progress(updates.append), updates


def test_stages_report_start_end_running_set_and_weighted_share() -> None:
    """The share is the weight of finished stages; the running labels are the open stages."""
    job, updates = _collect()
    with progress.active(job):
        assert progress.run_stage("generate world", lambda: 5) == 5
        with progress.running("write files"):
            assert job.fraction == pytest.approx(STAGES["generate world"].weight / TOTAL_WEIGHT)
    assert [(u.stage, u.finished) for u in updates] == [
        ("generate world", False),
        ("generate world", True),
        ("write files", False),
        ("write files", True),
    ]
    assert updates[0].running == ("generate world",)
    assert updates[0].label == STAGES["generate world"].label
    assert updates[-1].running == ()
    expected = (STAGES["generate world"].weight + STAGES["write files"].weight) / TOTAL_WEIGHT
    assert updates[-1].fraction == pytest.approx(expected)


def test_a_stage_that_fails_does_not_count_as_done() -> None:
    """An error ends the stage without adding its weight to the share."""
    job, updates = _collect()

    def fail() -> None:
        message = "boom"
        raise ValueError(message)

    with progress.active(job), pytest.raises(ValueError, match="boom"):
        progress.run_stage("texts", fail)
    assert updates[-1].finished
    assert updates[-1].fraction == 0.0
    assert updates[-1].running == ()


def test_the_whole_table_adds_up_to_a_full_bar() -> None:
    """When every known stage has finished the bar is full, and unknown names add nothing."""
    job = Progress()
    for name in STAGES:
        job.begin(name)
        job.finish(name)
    job.begin("something unlisted")
    job.finish("something unlisted")
    assert job.fraction == 1.0


def test_eta_counts_down_and_adjusts_when_a_stage_takes_longer_than_expected() -> None:
    """The ETA starts from the reference run and adapts to the live weighted stage pace."""
    job = Progress()
    job.begin("generate world")
    started = job._stage_started["generate world"]
    early = job.estimated_remaining(now=started + 4)
    later = job.estimated_remaining(now=started + 8)
    overrun = job.estimated_remaining(now=started + 45)

    assert later < early
    assert overrun > later


def test_cancel_stops_at_the_next_checkpoint_or_stage_start() -> None:
    """After cancel(), a checkpoint raises, a new stage does not start, and stages stop running."""
    job, updates = _collect()
    progress.checkpoint()  # no active job: nothing happens
    with progress.active(job):
        progress.checkpoint()
        job.cancel()
        assert job.cancelled
        with pytest.raises(Cancelled):
            progress.checkpoint()
        started: list[str] = []
        with pytest.raises(Cancelled):
            progress.run_stage("texts", lambda: started.append("texts"))
        assert started == []
    assert not updates  # a stage that never began was never announced
    progress.checkpoint()


def test_cancel_reaches_stages_on_other_threads() -> None:
    """A stage waiting in a pool raises Cancelled where its result is read."""
    job = Progress()
    release = threading.Event()

    def loop() -> None:
        while True:
            _ = release.wait(0.005)
            progress.checkpoint()

    with progress.active(job), Stages(2) as stages:
        running = stages.submit("texts", loop)
        job.cancel()
        with pytest.raises(Cancelled):
            running.result(timeout=10)
        with pytest.raises(Cancelled):
            _ = stages.submit("script remap", lambda: None)


def test_every_stage_the_code_announces_has_a_label_and_a_weight() -> None:
    """A stage name used in the source but missing from the table would show as raw text."""
    import re  # noqa: PLC0415 - only this test reads the source
    from pathlib import Path  # noqa: PLC0415

    pattern = re.compile(r'(?:run_stage|running|stages\.submit)\(\s*"([^"]+)"')
    used: set[str] = set()
    for path in Path(progress.__file__).parent.rglob("*.py"):
        used.update(pattern.findall(path.read_text(encoding="utf-8")))
    assert {"generate world", "texts", "write files", "terrain decals"} <= used
    assert used - set(STAGES) == set()
    assert set(STAGES) - used == set()
