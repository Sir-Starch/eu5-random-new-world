"""The phases the windows list while a world is made (``rnw.gui.phases``)."""

from __future__ import annotations

from rnw.export_stages import SKIPPED
from rnw.gui import phases
from rnw.gui.phases import EXPORT, PHASES, UNLISTED, Kind, expected, kind_of, members, rows
from rnw.progress import STAGES, Progress, Update
from rnw.settings import Settings, build_settings


def _america() -> Settings:
    return build_settings("continents", None)


def _composed() -> Settings:
    return build_settings("continents", {"continents": {"africa": True, "oceania": True}})


def _real() -> Settings:
    return build_settings("continents", {"new_world": {"keep_geography": 1}})


def _real_with_africa() -> Settings:
    return build_settings(
        "continents", {"new_world": {"keep_geography": 1}, "continents": {"africa": True}}
    )


def test_every_stage_has_a_phase_or_is_deliberately_unlisted() -> None:
    listed = {name for info in PHASES.values() for name in info.stages}
    assert listed <= set(STAGES)
    assert set(STAGES) - listed == UNLISTED
    assert not listed & UNLISTED


def test_each_kind_lists_every_stage_it_counts() -> None:
    for settings in (_america(), _composed(), _real(), _real_with_africa()):
        kind = kind_of(settings)
        listed = {name for phase in PHASES for name in members(phase, kind)}
        assert expected(settings, install=True) <= listed


def test_kinds_follow_the_continents() -> None:
    assert kind_of(_america()) is Kind.AMERICA
    assert kind_of(_composed()) is Kind.COMPOSED
    assert kind_of(_real()) is Kind.REAL
    assert kind_of(_real_with_africa()) is Kind.COMPOSED


def test_a_world_of_several_continents_joins_them_after_generating() -> None:
    assert members("land", Kind.COMPOSED)[-1] == "select canvas"
    assert "select canvas" not in members("map", Kind.COMPOSED)
    assert "select canvas" in members("map", Kind.AMERICA)


def test_rows_count_only_what_the_world_runs() -> None:
    settings = _america()
    found = rows(settings, install=False, running=(), finished=())
    assert [row.phase for row in found] == [phase for phase in PHASES if phase != "install"]
    assert all(row.state == "waiting" and row.done == 0 for row in found)
    assert sum(row.total for row in found) == len(EXPORT)

    done = rows(settings, install=True, running=(), finished=expected(settings, install=True))
    assert [row.phase for row in done][-1] == "install"
    assert all(row.state == "done" and row.done == row.total for row in done)


def test_the_geography_parts_are_steps_not_counted() -> None:
    found = {
        row.phase: row
        for row in rows(
            _america(),
            install=False,
            running=("generate world", "land cells"),
            finished=("load map", "select canvas", "relief"),
        )
    }
    land = found["land"]
    assert land.state == "running"
    assert land.steps == ("land cells",)
    assert (land.done, land.total) == (0, 1)
    assert found["map"].state == "done"


def test_a_phase_whose_next_stage_waits_is_partly_done() -> None:
    found = {
        row.phase: row
        for row in rows(
            _america(), install=False, running=(), finished=("vanilla localization keys",)
        )
    }
    assert found["game"].state == "partial"


def test_a_world_that_keeps_the_real_americas_lists_no_geography() -> None:
    settings = _real()
    found = rows(settings, install=False, running=(), finished=())
    assert [row.phase for row in found] == ["map", "game", "peoples", "mod"]
    finished = {*SKIPPED, *expected(settings, install=False)}
    assert all(
        row.state == "done" for row in rows(settings, install=False, running=(), finished=finished)
    )


def test_the_optional_wait_is_shown_but_not_counted() -> None:
    found = rows(_america(), install=True, running=("waiting for the game",), finished=())
    install = found[-1]
    assert install.phase == "install"
    assert install.steps == ("waiting for the game",)
    assert install.total == 1
    assert "waiting for the game" in phases.OPTIONAL


def test_skipped_stages_are_told_as_finished_once() -> None:
    heard: list[Update] = []
    job = Progress(heard.append)
    job.skip(("generate world", "identities", "generate world"))
    job.skip(("identities",))
    assert [(update.stage, update.finished, update.skipped) for update in heard] == [
        ("generate world", True, True),
        ("identities", True, True),
    ]
