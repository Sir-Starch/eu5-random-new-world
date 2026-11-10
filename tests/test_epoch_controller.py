"""The experimental features in the controller: the box, the epoch chosen, and what it makes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from rnw import __version__, epoch
from rnw.app import library, preferences
from rnw.app.worldcode import decode, encode, new_code
from rnw.gui.controller import Phase
from rnw.gui.text import text
from tests.test_controller import (
    _controller,  # pyright: ignore[reportPrivateUsage]
    _finish,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.service import Exporter
    from rnw.gui.controller import Controller
    from rnw.landmask import LandMask
    from rnw.progress import Progress
    from rnw.settings import Settings
    from rnw.worldname import Label

OLDER = epoch.CURRENT - 1


def _noting(fake_export: Exporter, asked: list[int]) -> Exporter:
    """The fake export, noting the epoch it is asked for and recording it as the real one does."""

    def export(  # noqa: PLR0913 - the export's own signature
        game_dir: Path,
        output: Path,
        *,
        seed: int,
        settings: object,
        accept_build: str | None = None,
        settings_file: str | None = None,
        replace: bool = False,
        check_memory: bool = True,
        progress: Progress | None = None,
        world_code: str | None = None,
        world_label: Label | None = None,
        land_mask: LandMask | None = None,
        cache_dir: Path | None = None,
    ) -> dict[str, object]:
        algorithm = cast("Settings", settings).algorithm
        asked.append(algorithm)
        report = fake_export(
            game_dir,
            output,
            seed=seed,
            settings=settings,
            accept_build=accept_build,
            settings_file=settings_file,
            replace=replace,
            check_memory=check_memory,
            progress=progress,
            world_code=world_code,
            world_label=world_label,
            land_mask=land_mask,
            cache_dir=cache_dir,
        )
        record = dict(cast("dict[str, object]", report["record"]))
        record["algorithm"] = algorithm
        return {**report, "record": record}

    return export


def _older_world(tmp_path: Path, fake_export: Exporter) -> tuple[Controller, list[int]]:
    """A controller with experimental features on, holding one world made by the older epoch."""
    asked: list[int] = []
    controller = _controller(tmp_path, _noting(fake_export, asked))
    controller.set_experimental(True)
    assert controller.set_algorithm(OLDER) is None
    assert controller.start() is None
    _finish(controller)
    return controller, asked


def test_the_features_are_off_until_ticked_and_the_choice_is_remembered(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    assert not controller.preferences.experimental
    assert controller.algorithms() == (epoch.CURRENT,)
    assert controller.epoch_choices() == []
    refusal = controller.set_algorithm(OLDER)
    assert refusal is not None
    assert str(OLDER) in refusal
    assert controller.algorithm == epoch.CURRENT
    controller.set_experimental(True)
    assert preferences.load(controller.data).experimental
    assert controller.algorithms() == epoch.selectable()
    controller.set_experimental(False)
    assert not preferences.load(controller.data).experimental


def test_the_choices_list_every_selectable_epoch_newest_first_with_its_release(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    controller.set_experimental(True)
    choices = controller.epoch_choices()
    assert [number for number, _label in choices] == list(reversed(epoch.selectable()))
    labels = dict(choices)
    assert labels[epoch.CURRENT] == text(
        "epoch.choice.current", epoch=epoch.CURRENT, release=__version__
    )
    assert "release 1.2.1" in labels[62]
    assert "release 1.2.0" in labels[61]
    assert controller.set_algorithm(epoch.OLDEST_SELECTABLE - 1) is not None
    assert controller.set_algorithm(epoch.CURRENT + 1) is not None


def test_the_code_of_the_new_world_is_stamped_with_the_release_of_its_epoch(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """A code names the release that made its world, so a 1.2.1 generator makes the same one."""
    controller = _controller(tmp_path, fake_export)
    assert decode(controller.code).generator == __version__
    controller.set_experimental(True)
    assert controller.set_algorithm(62) is None
    assert decode(controller.code).generator == "1.2.1"
    assert epoch.epoch_of(decode(controller.code).generator) == 62
    assert controller.set_algorithm(epoch.CURRENT) is None
    assert decode(controller.code).generator == __version__


def test_unticking_the_features_makes_new_worlds_of_the_current_epoch_again(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    controller.set_experimental(True)
    assert controller.set_algorithm(OLDER) is None
    controller.set_experimental(False)
    assert controller.algorithm == epoch.CURRENT
    assert decode(controller.code).generator == __version__
    assert controller.epoch_choices() == []


def test_a_world_is_made_by_the_epoch_chosen_and_its_record_says_so(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller, asked = _older_world(tmp_path, fake_export)
    assert asked == [OLDER]
    [world] = controller.worlds
    assert world.record is not None
    assert world.record.algorithm == OLDER
    assert decode(world.code).generator == epoch.stamp_of(OLDER)
    assert controller.world_epoch(world) == OLDER


def test_a_world_of_an_older_epoch_has_its_versions_made_by_that_epoch(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller, asked = _older_world(tmp_path, fake_export)
    [world] = controller.worlds
    assert controller.version_problem(world) is None
    assert controller.reroll_selected("peoples") is None
    _finish(controller)
    assert asked == [OLDER, OLDER]
    version = next(item for item in controller.worlds if item.id != world.id)
    assert (version.parent, version.part) == (world.id, "peoples")
    assert decode(version.code).settings().rolls.peoples == 1
    assert decode(version.code).generator == epoch.stamp_of(OLDER)
    assert version.record is not None
    assert version.record.algorithm == OLDER


def test_editing_a_world_of_an_older_epoch_keeps_its_epoch_on_the_page(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller, _asked = _older_world(tmp_path, fake_export)
    controller.set_experimental(False)
    assert controller.edit_selected() is not None
    controller.set_experimental(True)
    assert controller.edit_selected() is None
    assert controller.algorithm == OLDER


def test_without_the_features_a_world_of_an_older_epoch_has_no_versions(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller, asked = _older_world(tmp_path, fake_export)
    [world] = controller.worlds
    controller.set_experimental(False)
    problem = controller.version_problem(world)
    assert problem is not None
    assert "would not be on the same land" in problem
    assert controller.reroll_selected("peoples") == problem
    assert asked == [OLDER]
    assert controller.phase is Phase.FINISHED


def test_a_code_of_an_older_epoch_is_followed_only_with_the_features(
    tmp_path: Path, fake_export: Exporter
) -> None:
    code = encode(replace(new_code("continents", 5), generator=epoch.stamp_of(OLDER)))
    controller = _controller(tmp_path, fake_export)
    assert controller.use_code(code) is None
    assert controller.algorithm == epoch.CURRENT
    assert epoch.stamp_of(OLDER) in controller.notice
    assert controller.notice != text("epoch.followed", release=epoch.stamp_of(OLDER), epoch=OLDER)
    controller.set_experimental(True)
    assert controller.use_code(code) is None
    assert controller.algorithm == OLDER
    assert controller.notice == text("epoch.followed", release=epoch.stamp_of(OLDER), epoch=OLDER)
    assert controller.code == code
    current = encode(new_code("continents", 6))
    assert controller.use_code(current) is None
    assert controller.algorithm == epoch.CURRENT


def test_a_world_waiting_in_the_queue_keeps_the_epoch_it_was_chosen_with(
    tmp_path: Path, fake_export: Exporter
) -> None:
    asked: list[int] = []
    controller = _controller(tmp_path, _noting(fake_export, asked))
    controller.install = False
    controller.set_experimental(True)
    _ = controller.set_seed("10")
    assert controller.set_algorithm(OLDER) is None
    assert controller.enqueue() is None
    _ = controller.set_seed("20")
    assert controller.set_algorithm(epoch.CURRENT) is None
    assert controller.enqueue() is None
    assert [job.algorithm for job in controller.queue] == [OLDER, epoch.CURRENT]
    assert controller.start_queue() is None
    _finish(controller)
    assert asked == [OLDER, epoch.CURRENT]
    by_seed = {world.seed: world for world in controller.worlds}
    assert by_seed[10].record is not None
    assert by_seed[10].record.algorithm == OLDER
    assert decode(by_seed[10].code).generator == epoch.stamp_of(OLDER)
    assert decode(by_seed[20].code).generator == __version__


def test_the_library_keeps_the_stamp_the_world_was_made_under(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller, _asked = _older_world(tmp_path, fake_export)
    [world] = controller.worlds
    stored = library.load(controller.data)
    assert [item.code for item in stored] == [world.code]
    assert epoch.epoch_of(decode(stored[0].code).generator) == OLDER
