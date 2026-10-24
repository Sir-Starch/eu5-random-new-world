"""The window's controller: choices, the library and the work, without a display."""

from __future__ import annotations

import json
import shutil
import threading
from dataclasses import replace
from typing import TYPE_CHECKING

from rnw import epoch, worldname
from rnw.app import controls, install, library, preferences, service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.library import Placement
from rnw.app.worldcode import WorldCode, decode, encode, new_code
from rnw.eu5_lobby import SCRIPTED_GUI_FILE
from rnw.gui.controller import NEW, SEED_MAX, STRAY, Controller, Phase, Task
from rnw.record import Verdict

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from rnw.app.service import Exporter
    from rnw.progress import Progress


def _controller(tmp_path: Path, export: Exporter) -> Controller:
    def generator(request: service.Request, progress: Progress | None = None) -> service.Result:
        return service.generate(request, progress, export)

    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    controller = Controller(data=tmp_path / "data", environment=environment, generator=generator)
    (tmp_path / "game" / "game" / "in_game" / "map_data").mkdir(parents=True)
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    (tmp_path / "profile" / "mod").mkdir(parents=True)
    controller.profile = Profile(tmp_path / "profile", "linux", has_mods=True)
    return controller


def _finish(controller: Controller) -> None:
    controller.wait(10)
    assert controller.phase is Phase.FINISHED, controller.message


def test_queued_worlds_keep_their_own_settings_and_run_in_order(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    controller = _controller(tmp_path, fake_export)
    controller.install = False
    _ = controller.set_seed("10")
    assert controller.enqueue() is None
    _ = controller.set_seed("20")
    controller.set_value("natives.empire_permille", 800)
    assert controller.enqueue() is None
    assert controller.start_queue() is None
    _finish(controller)
    assert controller.queue_done == 2
    assert controller.queue == []
    assert {world.seed for world in controller.worlds} == {10, 20}
    second = next(world for world in controller.worlds if world.seed == 20)
    assert decode(second.code).settings().natives.empire_permille == 800


def test_a_failed_queue_keeps_the_failed_job_and_the_following_jobs(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    controller = _controller(tmp_path, fake_export)
    original = controller.generator

    def generate(request: service.Request, progress: Progress | None = None) -> service.Result:
        if request.code.seed == 20:
            message = "second job failed"
            raise OSError(message)
        return original(request, progress)

    controller.generator = generate
    controller.install = False
    for seed in (10, 20, 30):
        _ = controller.set_seed(str(seed))
        assert controller.enqueue() is None
    assert controller.start_queue() is None
    controller.wait(10)
    assert controller.phase is Phase.FAILED
    assert controller.queue_done == 1
    assert [job.code.seed for job in controller.queue] == [20, 30]
    assert {world.seed for world in controller.worlds} == {10}
    controller.generator = original
    assert controller.start_queue() is None
    _finish(controller)
    assert {world.seed for world in controller.worlds} == {10, 20, 30}


def test_undo_restores_the_previous_roll_in_the_game_without_forgetting_either_world(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    controller = _controller(tmp_path, fake_export)
    assert controller.start() is None
    _finish(controller)
    original = controller.selected_world()
    assert original is not None
    assert controller.reroll_selected("peoples") is None
    _finish(controller)
    variant = controller.selected_world()
    assert variant is not None
    assert variant.parent == original.id
    assert controller.undo_selected() is None
    _finish(controller)
    restored = controller.selected_world()
    assert restored is not None
    assert restored.id == original.id
    assert controller.placement(restored) is Placement.IN_GAME
    assert controller.placement(variant) is not Placement.IN_GAME
    assert {item.id for item in controller.worlds} == {original.id, variant.id}


def test_choices_are_validated_and_a_type_resets_its_values(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Seeds, codes and values are checked; choosing a type gives back its own values."""
    controller = _controller(tmp_path, fake_export)
    assert controller.set_seed("12345") is None
    assert controller.seed == 12345
    for bad in ("-1", "x", str(SEED_MAX + 1)):
        assert controller.set_seed(bad) is not None
    assert controller.seed == 12345
    controller.set_value("new_world.land_permille", 5)
    assert controller.value("new_world.land_permille") == 150
    controller.set_value("natives.state_spread_permille", 300)
    assert set(controller.changes) == {"new_world.land_permille", "natives.state_spread_permille"}
    code = controller.code
    controller.set_preset("islands")
    assert controller.changes == {}
    assert controller.value("new_world.land_permille") == 180
    assert controller.use_code(code) is None
    assert controller.preset == "continents"
    assert controller.value("natives.state_spread_permille") == 300
    other = encode(WorldCode("continents", 5, "0.1.0"))
    assert controller.use_code(other) is None
    assert "0.1.0" in controller.notice
    wild = encode(new_code("continents", 5, {"new_world": {"land_permille": 800}}))
    assert controller.use_code(wild) is not None
    controller.reset_values()
    assert controller.changes == {}


def test_a_quick_answer_sets_the_controls_and_travels_in_the_code(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Choosing an answer changes its controls; the world code carries it and brings it back."""
    controller = _controller(tmp_path, fake_export)
    assert controller.quick_level("land") == "normal"
    assert controller.quick_level("empires") == "seldom"
    assert controller.changes == {}
    controller.set_quick("empires", "often")
    controller.set_quick("land", "much")
    controller.set_quick("wealth", "rich")
    assert controller.quick_level("empires") == "often"
    assert controller.value("natives.empire_permille") == 800
    assert controller.value("new_world.land_permille") > 400
    assert controller.value("new_world.location_px") > 46
    code = controller.code
    controller.set_preset("islands")
    assert controller.quick_level("empires") == "seldom"
    assert controller.use_code(code) is None
    assert controller.preset == "continents"
    assert [controller.quick_level(n) for n in ("empires", "land", "wealth")] == [
        "often",
        "much",
        "rich",
    ]
    controller.set_quick("empires", "seldom")
    controller.set_quick("land", "normal")
    controller.set_quick("wealth", "normal")
    assert controller.changes == {}
    controller.set_value("natives.empire_permille", 333)
    assert controller.quick_level("empires") is None


def test_generate_is_refused_beyond_the_location_budget(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Much land in small locations would exceed the engine's limit, so it cannot start."""
    controller = _controller(tmp_path, fake_export)
    assert controller.problem() is None
    controller.set_preset("supercontinent")
    controller.set_value("new_world.land_permille", 600)
    controller.set_value("new_world.location_px", 40)
    assert controller.estimated_locations() > controls.LOCATION_BUDGET
    problem = controller.problem()
    assert problem is not None
    assert "locations" in problem
    assert controller.start() == problem


def test_a_world_is_made_selected_hidden_and_managed(tmp_path: Path, fake_export: Exporter) -> None:
    """The new world is selected with its New World hidden; removing, adding and deleting work."""
    controller = _controller(tmp_path, fake_export)
    changes: list[int] = []
    controller.subscribe(lambda: changes.append(1))
    assert controller.start() is None
    _finish(controller)
    [world] = controller.worlds
    assert controller.selection == world.id
    assert controller.picture(world) == library.picture(controller.data, world, revealed=False)
    assert controller.placement(world) is Placement.IN_GAME
    assert controller.remove_selected() is None
    _finish(controller)
    assert controller.placement(world) is Placement.CODE_ONLY
    assert controller.add_selected() is None
    _finish(controller)
    assert controller.placement(world) is Placement.IN_GAME
    assert controller.rename(world, "Vinland") is None
    assert controller.name(controller.worlds[0]) == "Vinland"
    assert controller.delete_selected() is None
    _finish(controller)
    assert controller.worlds == []
    assert controller.selection == NEW
    assert changes


def test_batch_removal_handles_installed_kept_and_stray_without_the_game(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    for seed, installed in ((11, True), (22, True), (33, False)):
        controller.install = installed
        _ = controller.set_seed(str(seed))
        assert controller.start() is None
        _finish(controller)
    stray = tmp_path / "profile/mod/rnw_exp_older"
    (stray / ".metadata").mkdir(parents=True)
    _ = (stray / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
    (stray / "in_game/map_data").mkdir(parents=True)
    unrelated = tmp_path / "profile/mod/another_mod/keep.txt"
    unrelated.parent.mkdir()
    _ = unrelated.write_text("untouched", encoding="utf-8")
    controller.refresh_library()
    worlds = tuple(controller.worlds)
    selected = (NEW, *(world.id for world in worlds), f"{STRAY}{stray.name}", worlds[0].id)
    controller.game = None
    assert len(controller.removable_entries(selected)) == 3
    assert controller.remove_entries(selected) is None
    _finish(controller)
    assert len(controller.worlds) == 3
    assert not controller.strays
    assert not stray.exists()
    assert unrelated.read_text(encoding="utf-8") == "untouched"
    for world in worlds:
        assert controller.placement(world) is (
            Placement.KEPT if world.seed == 33 else Placement.CODE_ONLY
        )
        assert library.folder(controller.data, world).is_dir()
    runs = controller.runs
    assert controller.remove_entries(selected) is None
    assert controller.runs == runs


def test_batch_delete_stops_on_error_and_keeps_unprocessed_records(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _controller(tmp_path, fake_export)
    for seed in (11, 22, 33):
        _ = controller.set_seed(str(seed))
        assert controller.start() is None
        _finish(controller)
    first, second, third = controller.worlds
    original = shutil.rmtree

    def remove_tree(path: Path, *, ignore_errors: bool = False) -> None:
        if path == library.folder(controller.data, second):
            if ignore_errors:
                return
            message = "permission denied"
            raise PermissionError(message)
        original(path, ignore_errors=ignore_errors)

    monkeypatch.setattr(shutil, "rmtree", remove_tree)
    controller.game = None
    assert controller.delete_entries(tuple(world.id for world in controller.worlds)) is None
    controller.wait(10)
    assert controller.phase is Phase.FAILED
    assert controller.name(second) in controller.message
    assert "after deleting 1 worlds" in controller.message
    assert "permission denied" in controller.message
    assert {world.id for world in controller.worlds} == {second.id, third.id}
    assert controller.placement(third) is Placement.IN_GAME
    assert not library.folder(controller.data, first).exists()


def test_library_deletion_needs_neither_game_nor_profile_and_refuses_busy_work(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    controller.install = False
    assert controller.start() is None
    _finish(controller)
    [world] = controller.worlds
    controller.game = controller.profile = None
    controller.phase = Phase.RUNNING
    assert controller.delete_entries((world.id,)) is not None
    assert controller.remove_entries((world.id,)) is not None
    controller.phase = Phase.IDLE
    assert controller.remove_entries((world.id,)) is not None
    assert controller.delete_entries((NEW, world.id, world.id, "unknown")) is None
    _finish(controller)
    assert not controller.worlds


def test_finished_is_published_only_after_the_new_world_is_in_the_library(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _controller(tmp_path, fake_export)
    refreshing, release = threading.Event(), threading.Event()
    refresh = controller.refresh_library

    def paused_refresh() -> None:
        refreshing.set()
        assert release.wait(10)
        refresh()

    monkeypatch.setattr(controller, "refresh_library", paused_refresh)
    assert controller.start() is None
    try:
        assert refreshing.wait(10)
        assert controller.phase is Phase.RUNNING
        assert controller.selected_world() is None
    finally:
        release.set()
        controller.wait(10)
    assert controller.phase is Phase.FINISHED
    assert controller.selected_world() is not None


def test_like_this_takes_type_and_values_with_a_new_seed(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """'New world with these settings' fills the form from a world and picks a fresh seed."""
    controller = _controller(tmp_path, fake_export)
    controller.set_preset("archipelago")
    controller.set_value("natives.population_permille", 2000)
    _ = controller.start()
    _finish(controller)
    [world] = controller.worlds
    controller.set_preset("continents")
    controller.like(world)
    assert (controller.preset, controller.selection) == ("archipelago", NEW)
    assert controller.value("natives.population_permille") == 2000
    assert controller.seed != world.seed
    assert controller.changed_count(world) == 1


def test_cancel_stops_the_work_and_says_so(tmp_path: Path, fake_export: Exporter) -> None:
    """A cancel while the generator runs ends in CANCELLED, with nothing recorded."""
    started = threading.Event()

    def hang(request: service.Request, progress: Progress | None = None) -> service.Result:
        del request
        assert progress is not None
        started.set()
        while True:
            progress.checkpoint()
            _ = threading.Event().wait(0.005)

    controller = _controller(tmp_path, fake_export)
    controller.generator = hang
    assert controller.start() is None
    assert started.wait(5)
    assert controller.task is Task.GENERATE
    controller.cancel()
    controller.wait(10)
    assert controller.phase is Phase.CANCELLED
    assert controller.worlds == []


def test_a_failure_is_explained_and_logged(tmp_path: Path, fake_export: Exporter) -> None:
    """The message reaches the window and the traceback a file in the data folder."""

    def broken(request: service.Request, progress: Progress | None = None) -> service.Result:
        del request, progress
        message = "the map is gone"
        raise RuntimeError(message)

    controller = _controller(tmp_path, fake_export)
    controller.generator = broken
    _ = controller.start()
    controller.wait(10)
    assert (controller.phase, controller.message) == (Phase.FAILED, "the map is gone")
    assert "RuntimeError" in (controller.data / "last-error.log").read_text(encoding="utf-8")


def test_strays_are_listed_and_can_be_removed(tmp_path: Path, fake_export: Exporter) -> None:
    """A world of an earlier version in the game shows as a stray and can be taken out."""
    controller = _controller(tmp_path, fake_export)
    stray = tmp_path / "profile" / "mod" / "rnw_exp_new_world"
    (stray / ".metadata").mkdir(parents=True)
    _ = (stray / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
    (stray / "in_game" / "map_data").mkdir(parents=True)
    controller.refresh_library()
    assert controller.strays == [stray]
    controller.select(f"{STRAY}rnw_exp_new_world")
    assert controller.selected_stray() == stray
    assert controller.remove_selected() is None
    controller.wait(10)
    assert controller.strays == []


def test_world_visibility_changes_only_that_existing_mod_without_generation(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    _ = controller.start()
    _finish(controller)
    first = controller.selected_world()
    assert first is not None
    _ = controller.set_seed("20")
    _ = controller.start()
    _finish(controller)
    second = controller.selected_world()
    assert second is not None
    first_mod = tmp_path / "profile" / "mod" / first.folder
    second_mod = tmp_path / "profile" / "mod" / second.folder
    first_cover = first_mod / SCRIPTED_GUI_FILE
    second_cover = second_mod / SCRIPTED_GUI_FILE
    original_cover = first_cover.read_bytes()
    runs = controller.runs
    assert not controller.shown(first)
    assert not controller.shown(second)

    assert controller.set_world_visibility(first, show=True) is None

    assert controller.runs == runs
    assert controller.shown(controller.worlds[0]) or controller.shown(controller.worlds[1])
    shown = next(world for world in controller.worlds if world.id == first.id)
    hidden = next(world for world in controller.worlds if world.id == second.id)
    assert controller.shown(shown)
    assert not controller.shown(hidden)
    assert not first_cover.exists()
    assert second_cover.is_file()
    assert controller.picture(shown) == library.picture(controller.data, shown, revealed=True)
    assert controller.set_world_visibility(shown, show=False) is None
    assert first_cover.read_bytes() == original_cover

    controller.set_show_new_world(True)
    assert controller.preferences.show_new_world
    assert not controller.shown(hidden)
    assert second_cover.is_file()


def test_new_world_visibility_default_does_not_override_existing_worlds(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    _ = controller.start()
    _finish(controller)
    [world] = controller.worlds
    mod = tmp_path / "profile" / "mod" / world.folder
    cover = mod / SCRIPTED_GUI_FILE
    assert cover.is_file()
    controller.set_show_new_world(True)
    assert not controller.shown(world)
    assert cover.is_file()
    again = Controller(data=controller.data)
    assert again.preferences.show_new_world
    assert not again.shown(world)


def test_a_world_can_be_shown_when_its_mod_is_kept_without_regeneration(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _controller(tmp_path, fake_export)
    controller.install = False
    assert controller.start() is None
    _finish(controller)
    [world] = controller.worlds
    mod = library.kept(controller.data, world)
    assert mod is not None
    cover = mod / SCRIPTED_GUI_FILE
    assert cover.is_file()
    runs = controller.runs

    assert controller.set_world_visibility(world, show=True) is None

    assert controller.runs == runs
    assert not cover.exists()
    assert controller.shown(controller.worlds[0])


def test_the_game_lists_the_world_by_the_name_the_window_shows(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The default is the type and the tag; a rename, in the game or kept, rewrites the title."""
    controller = _controller(tmp_path, fake_export)
    assert controller.start() is None
    _finish(controller)
    [world] = controller.worlds
    tag = worldname.tag_of(world.id)
    assert controller.name(world) == f"Continents {tag}"
    metadata = tmp_path / "profile/mod" / world.folder / ".metadata/metadata.json"
    assert json.loads(metadata.read_text("utf-8"))["name"] == f"RNW: Continents {tag}"
    assert controller.rename(world, "  Vinland   ") is None
    assert json.loads(metadata.read_text("utf-8-sig"))["name"] == "RNW: Vinland"
    assert controller.name(controller.worlds[0]) == "Vinland"
    assert controller.rename(controller.worlds[0], f"Continents {tag}") is None
    assert controller.worlds[0].name == ""
    assert json.loads(metadata.read_text("utf-8-sig"))["name"] == f"RNW: Continents {tag}"
    assert controller.rename(controller.worlds[0], "x" * 60) is None
    assert len(controller.worlds[0].name) == worldname.MAX_NAME


def test_a_name_the_game_does_not_let_us_write_is_saved_and_the_player_is_told(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """When the metadata cannot be replaced the name is kept, and a notice says when it shows."""
    controller = _controller(tmp_path, fake_export)
    assert controller.start() is None
    _finish(controller)
    [world] = controller.worlds
    metadata = tmp_path / "profile/mod" / world.folder / ".metadata/metadata.json"
    _ = metadata.write_text("{", encoding="utf-8")
    problem = controller.rename(world, "Vinland")
    assert problem is not None
    assert "name is saved" in problem
    assert controller.worlds[0].name == "Vinland"


def _checked_controller(
    tmp_path: Path, fake_export: Exporter, found: service.Check | None
) -> tuple[Controller, list[str]]:
    """A controller with one made world whose checker answers ``found`` and notes its calls."""
    calls: list[str] = []

    def checker(
        world: library.World,
        *,
        game: GameInstall,
        data: Path,
        progress: Progress | None = None,
    ) -> service.Check:
        del game, data, progress
        calls.append(world.id)
        if found is None:
            message = "no way"
            raise service.CheckError(message)
        return found

    controller = _controller(tmp_path, fake_export)
    controller.checker = checker
    assert controller.start() is None
    _finish(controller)
    return controller, calls


def test_what_is_known_of_a_world_being_made_again_follows_its_record(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Without a check, the record tells the algorithm; a world with no record says so."""
    controller, _calls = _checked_controller(tmp_path, fake_export, None)
    [world] = controller.worlds
    assert world.record is not None
    assert "byte for byte" in controller.reproduction(world)
    other = replace(world, record=replace(world.record, algorithm=epoch.CURRENT + 1))
    assert "differs from this one" in controller.reproduction(other)
    assert world.record.release in controller.reproduction(other)
    assert "before worlds kept a record" in controller.reproduction(replace(world, record=None))


def _answer(
    verdict: Verdict,
    *,
    reproduced: bool | None,
    changed: list[str] | None = None,
    differing: list[str] | None = None,
) -> service.Check:
    return service.Check(verdict, reproduced, changed or [], differing or [], 1.0)


def test_a_check_runs_in_the_background_and_its_answer_is_kept(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The three answers (reproduced, different, game changed) each have their sentence."""
    answers = (
        (_answer(Verdict.IDENTICAL, reproduced=True), "files are the same"),
        (_answer(Verdict.OTHER_INPUTS, reproduced=False, differing=["a.txt", "b.txt"]), "a.txt"),
        (_answer(Verdict.OTHER_INPUTS, reproduced=None, changed=["game/x"]), "files have changed"),
    )
    for number, (found, sentence) in enumerate(answers):
        controller, calls = _checked_controller(tmp_path / str(number), fake_export, found)
        [world] = controller.worlds
        assert controller.check_selected() is None
        assert controller.task is Task.CHECK
        controller.wait(10)
        assert controller.phase is Phase.FINISHED
        assert calls == [world.id]
        assert sentence in controller.reproduction(controller.worlds[0]), sentence


def test_a_check_is_refused_without_a_game_or_a_record_and_a_failure_is_shown(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Needs the game, not the profile; a world with no record has nothing to check."""
    controller, calls = _checked_controller(tmp_path, fake_export, None)
    [world] = controller.worlds
    controller.game = None
    assert controller.check_selected() is not None
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    controller.worlds = [replace(world, record=None)]
    assert "before worlds kept a record" in (controller.check_selected() or "")
    assert calls == []
    controller.worlds = [world]
    assert controller.check_selected() is None
    controller.wait(10)
    assert controller.phase is Phase.FAILED
    assert "no way" in controller.message


def test_a_failed_task_is_logged_with_its_traceback_and_a_report_can_be_saved(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The log file has the failure; the diagnostics file is written beside it, or says why not."""

    def broken(request: service.Request, progress: Progress | None = None) -> service.Result:
        del request, progress
        message = "the generator broke"
        raise RuntimeError(message)

    controller = _controller(tmp_path, fake_export)
    controller.generator = broken
    assert controller.start() is None
    controller.wait(10)
    assert controller.phase is Phase.FAILED
    log = (tmp_path / "data" / "generator.log").read_text(encoding="utf-8")
    assert "task failed: the generator broke" in log
    assert "Traceback" in log
    output = tmp_path / "out" / "report.zip"
    assert controller.save_diagnostics(output) is None
    assert output.is_file()
    assert controller.save_diagnostics(tmp_path) is not None


def _made(tmp_path: Path, fake_export: Exporter) -> Controller:
    controller = _controller(tmp_path, fake_export)
    assert controller.start() is None
    _finish(controller)
    return controller


def test_a_new_peoples_replaces_the_world_in_the_game_and_leaves_the_land_alone(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The version has the parent's seed and one more roll; it goes in, the parent comes out."""
    controller = _made(tmp_path, fake_export)
    [first] = controller.worlds
    assert controller.placement(first) is Placement.IN_GAME
    assert controller.reroll_selected("peoples") is None
    assert controller.task is Task.REROLL
    _finish(controller)
    version = next(world for world in controller.worlds if world.id != first.id)
    assert (version.parent, version.part, version.seed) == (first.id, "peoples", first.seed)
    assert decode(version.code).settings().rolls.peoples == 1
    assert controller.selection == version.id
    assert controller.placement(version) is Placement.IN_GAME
    assert controller.placement(first) is Placement.CODE_ONLY
    assert controller.parent_of(version) == first
    assert controller.parent_of(first) is None
    assert [depth for _world, depth in controller.listed()] == [0, 1]


def test_both_versions_stay_in_the_game_when_asked_and_a_kept_world_stays_out(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Keep both leaves the parent in the game; a world that was not in the game is not added."""
    controller = _made(tmp_path, fake_export)
    [first] = controller.worlds
    assert controller.reroll_selected("resources", keep_both=True) is None
    _finish(controller)
    assert controller.placement(first) is Placement.IN_GAME
    assert len(install.installed_mods(tmp_path / "profile")) == 2
    assert controller.remove_selected() is None
    _finish(controller)
    kept_parent = controller.selected_world()
    assert kept_parent is not None
    assert controller.placement(kept_parent) is Placement.CODE_ONLY
    assert controller.reroll_selected("peoples") is None
    _finish(controller)
    newest = controller.selected_world()
    assert newest is not None
    assert controller.placement(newest) is Placement.KEPT
    assert len(install.installed_mods(tmp_path / "profile")) == 1


def test_a_reroll_is_refused_without_a_game_or_while_busy_or_for_a_bad_part(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The refusals say why, and nothing is started."""
    controller = _made(tmp_path, fake_export)
    assert controller.reroll_selected("weather") is None
    assert controller.phase is Phase.FINISHED
    controller.game = None
    assert controller.reroll_selected("peoples") is not None
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    controller.selection = NEW
    assert controller.reroll_selected("peoples") is None
    assert controller.task is Task.GENERATE


def test_the_settings_of_a_world_open_on_the_new_world_page_with_its_seed_and_rolls(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Edit keeps the seed and the rolls; a new seed, typed or random, or New world, drops them."""
    controller = _made(tmp_path, fake_export)
    assert controller.reroll_selected("peoples") is None
    _finish(controller)
    version = controller.selected_world()
    assert version is not None
    controller.edit_selected()
    assert controller.selection == NEW
    assert controller.seed == version.seed
    assert decode(controller.code).settings().rolls.peoples == 1
    assert controller.changed_count(version) == 0
    assert controller.set_seed("12") is None
    assert decode(controller.code).settings().rolls.peoples == 0
    assert controller.use_code(version.code) is None
    assert "version of its continent" in controller.notice
    assert "peoples 1" in controller.notice
    assert "does not show" not in controller.notice
    controller.randomize()
    assert decode(controller.code).settings().rolls.peoples == 0
    controller.like(version)
    assert decode(controller.code).settings().rolls.peoples == 0
    assert controller.seed != version.seed


def test_a_world_is_covered_until_it_is_revealed_and_its_maps_can_be_saved(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Covered by default; the setting or a reveal shows it; saving a covered world is refused."""
    controller = _made(tmp_path, fake_export)
    [world] = controller.worlds
    assert controller.atlas(world) is not None
    assert not controller.revealed(world)
    assert controller.maps_to_compare() == []
    assert "covered" in (controller.save_map(world, "land", tmp_path / "x.png") or "")
    assert "countries" in controller.summary(world)
    controller.reveal_world(world)
    [shown] = controller.worlds
    assert controller.revealed(shown)
    assert [found.id for found, _atlas in controller.maps_to_compare()] == [shown.id]
    output = tmp_path / "maps" / "land.png"
    output.parent.mkdir()
    assert controller.save_map(shown, "land", output) is None
    assert output.read_bytes().startswith(b"\x89PNG")
    assert controller.save_map(shown, "weather", output) is not None
    preview = tmp_path / "maps" / "preview.png"
    assert controller.save_preview(shown, preview) is None
    shown_picture = controller.picture(shown)
    assert shown_picture is not None
    assert preview.read_bytes() == shown_picture.read_bytes()
    assert controller.save_preview(shown, tmp_path / "missing" / "p.png") is not None


def test_the_new_world_default_does_not_change_visibility_of_saved_worlds(
    tmp_path: Path, fake_export: Exporter
) -> None:
    controller = _made(tmp_path, fake_export)
    [world] = controller.worlds
    controller.set_show_new_world(True)
    assert not controller.shown(world)
    assert not controller.revealed(world)


def test_a_world_file_is_taken_in_and_written_out_by_the_controller(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Export writes a compact file; import in another library lists the world and selects it."""
    controller = _made(tmp_path, fake_export)
    [world] = controller.worlds
    output = tmp_path / "out" / "w.rnworld"
    assert controller.export_file(world, output) is None
    assert output.is_file()
    assert controller.export_file(world, tmp_path) is not None
    other = _controller(tmp_path / "other", fake_export)
    assert other.import_file(output) is None
    assert other.selection == world.id
    assert other.last_import is not None
    assert other.last_import.created
    assert [item.id for item in other.worlds] == [world.id]
    assert other.import_file(output) is None
    assert other.last_import is not None
    assert not other.last_import.created
    junk = tmp_path / "junk.rnworld"
    _ = junk.write_bytes(b"not a zip")
    assert "not a world file" in (other.import_file(junk) or "")
    assert other.import_file(tmp_path / "notes.txt") is not None
    assert [item.id for item in other.worlds] == [world.id]


def test_a_built_world_is_written_and_taken_in_as_a_task(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Send runs in the background; the other side needs a game, and takes it in as a task too."""

    def fingerprint(_directory: Path) -> tuple[()]:
        return ()

    def digest(_records: tuple[()]) -> str:
        return "f" * 64

    monkeypatch.setattr("rnw.app.transfer.fingerprint", fingerprint)
    monkeypatch.setattr("rnw.app.transfer.aggregate_digest", digest)
    controller = _made(tmp_path, fake_export)
    [world] = controller.worlds
    output = tmp_path / "out" / "w.rnworld-mod"
    assert controller.send_built(world, output) is None
    assert controller.task is Task.SEND
    controller.wait(10)
    assert controller.phase is Phase.FINISHED, controller.message
    assert output.is_file()
    other = _controller(tmp_path / "other", fake_export)
    other.game = None
    assert other.import_file(output) is not None
    other.game = GameInstall(tmp_path / "game", None, "26043558")
    assert other.import_file(output) is None
    assert other.task is Task.RECEIVE
    other.wait(10)
    assert other.phase is Phase.FINISHED, other.message
    assert other.selection == world.id
    assert [item.id for item in other.worlds] == [world.id]
    assert controller.remove_selected() is None
    _finish(controller)
    controller.worlds = [replace(world, id="zzzzzzzzzz")]
    assert controller.send_built(controller.worlds[0], output) is not None


def test_a_folder_chosen_by_hand_is_remembered_and_found_again(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The game and the profile the player chose are asked for once: the next start uses them."""
    controller = _controller(tmp_path, fake_export)
    other = tmp_path / "other_game"
    (other / "game" / "in_game" / "map_data").mkdir(parents=True)
    profile = tmp_path / "other_profile"
    (profile / "mod").mkdir(parents=True)
    assert controller.choose_game(other) is None
    assert controller.choose_profile(profile) is None
    saved = preferences.load(controller.data)
    assert (saved.game_dir, saved.profile_dir) == (str(other), str(profile))
    again = Controller(
        data=controller.data,
        environment=Environment(system="linux", home=tmp_path / "home2", variables={}),
    )
    again.discover()
    assert again.game is not None
    assert again.game.directory == other
    assert again.profile is not None
    assert again.profile.directory == profile
    assert controller.choose_game(tmp_path / "nothing") is not None
    controller.set_show_new_world(True)
    assert preferences.load(controller.data).game_dir == str(other)


def _land_picture(path: Path) -> Path:
    """A picture of land and sea for the controller to take."""
    import io  # noqa: PLC0415 - only this test draws

    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    grey = np.zeros((96, 88), dtype=np.uint8)
    grey[24:72, 22:66] = 255
    buffer = io.BytesIO()
    Image.fromarray(grey).save(buffer, format="PNG")
    _ = path.write_bytes(buffer.getvalue())
    return path


def test_the_land_can_be_drawn_in_an_image_and_the_world_is_made_on_it(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The image's id goes into the code and the image into the request; clearing undoes it."""
    seen: list[service.Request] = []

    def capture(request: service.Request, progress: Progress | None = None) -> service.Result:
        seen.append(request)
        return service.generate(request, progress, fake_export)

    controller = _controller(tmp_path, fake_export)
    controller.generator = capture
    picture = _land_picture(tmp_path / "land.png")
    assert controller.choose_land_image(picture) is None
    assert controller.land_mask is not None
    mask_id = controller.land_mask.id
    assert decode(controller.code).settings().mask.id == mask_id
    assert controller.problem() is None
    assert (
        controller.changed_count(
            library.World(  # a world with this code
                id="abcdefghij",
                code=controller.code,
                preset="continents",
                seed=1,
                generator="x",
                game_build="1",
                created=1,
                seconds=1.0,
            )
        )
        == 0
    )
    assert controller.start() is None
    _finish(controller)
    assert seen[0].land_mask is not None
    assert seen[0].land_mask.id == mask_id
    controller.clear_land_image()
    assert controller.land_mask is None
    assert decode(controller.code).settings().mask.id == 0
    assert controller.choose_land_image(tmp_path / "missing.png") is not None
    junk = tmp_path / "junk.png"
    _ = junk.write_bytes(b"x")
    assert "cannot be read" in (controller.choose_land_image(junk) or "")


def test_a_code_that_names_an_image_cannot_be_made_without_it(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Pasting such a code warns, and Generate says what is missing until the image is chosen."""
    controller = _controller(tmp_path, fake_export)
    picture = _land_picture(tmp_path / "land.png")
    assert controller.choose_land_image(picture) is None
    code = controller.code
    controller.clear_land_image()
    assert controller.use_code(code) is None
    assert "land image" in controller.notice
    assert "land image" in (controller.problem() or "")
    assert controller.choose_land_image(picture) is None
    assert controller.problem() is None
