"""The window's controller: choices, the library and the work, without a display."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from rnw.app import controls, library, service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.library import Placement
from rnw.app.worldcode import WorldCode, encode, new_code
from rnw.gui.controller import NEW, SEED_MAX, STRAY, Controller, Phase, Task

if TYPE_CHECKING:
    from pathlib import Path

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
    assert not controller.revealed
    assert controller.picture(world) == library.picture(controller.data, world, revealed=False)
    controller.set_revealed(True)
    assert controller.picture(world) == library.picture(controller.data, world, revealed=True)
    assert controller.placement(world) is Placement.IN_GAME
    assert controller.remove_selected() is None
    _finish(controller)
    assert controller.placement(world) is Placement.CODE_ONLY
    assert controller.add_selected() is None
    _finish(controller)
    assert controller.placement(world) is Placement.IN_GAME
    controller.rename(world, "Vinland")
    assert controller.name(controller.worlds[0]) == "Vinland"
    assert controller.delete_selected() is None
    _finish(controller)
    assert controller.worlds == []
    assert controller.selection == NEW
    assert changes


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


def test_the_mod_list_pictures_follow_the_players_choice(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Changing the choice redraws the picture of every world with a mod and is remembered."""
    controller = _controller(tmp_path, fake_export)
    _ = controller.start()
    _finish(controller)
    [world] = controller.worlds
    mod = tmp_path / "profile" / "mod" / world.folder
    controller.set_reveal_thumbnails(True)
    assert (mod / library.THUMBNAIL).is_file()
    again = Controller(data=controller.data)
    assert again.preferences.reveal_thumbnails
