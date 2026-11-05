"""Mods of the playset that can hide a world's files, on synthetic profiles (Workshop report W1)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from rnw.app import diagnostics, install, playset, session
from rnw.app.diagnostics import Snapshot
from rnw.app.discovery import GameInstall, Profile
from rnw.app.library import World
from rnw.gui import view
from rnw.gui.controller import Controller
from rnw.gui.text import text

if TYPE_CHECKING:
    from pathlib import Path

TEMPLATES = "in_game/map_data/location_templates.txt"
WORLD_FILES = (
    TEMPLATES,
    "in_game/map_data/definitions.txt",
    "main_menu/localization/english/a.yml",
)


def _mod(root: Path, folder: str, files: tuple[str, ...] = (), name: str | None = None) -> Path:
    mod = root / folder
    (mod / ".metadata").mkdir(parents=True)
    title = name if name is not None else folder
    _ = (mod / install.METADATA).write_text(json.dumps({"name": title}), encoding="utf-8-sig")
    for relative in files:
        target = mod / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text("x", encoding="utf-8")
    return mod


def _playset(profile: Path, *entries: tuple[str, bool]) -> None:
    """The active playset, in order; each entry is a path as the game writes it."""
    mods: list[dict[str, object]] = [{"path": path, "isEnabled": on} for path, on in entries]
    payload = {"playsets": [{"isActive": True, "orderedListMods": mods}]}
    _ = (profile / session.PLAYSETS).write_text(json.dumps(payload), encoding="utf-8-sig")


def _local(folder: str) -> tuple[str, bool]:
    return (
        f"C:/users/someone/Documents/Paradox Interactive/Europa Universalis V/mod/{folder}/",
        True,
    )


@pytest.fixture
def profile(tmp_path: Path) -> Path:
    folder = tmp_path / "profile"
    (folder / "mod").mkdir(parents=True)
    _ = _mod(folder / "mod", "rnw_exp_world_aaaa", WORLD_FILES, name="Mine")
    return folder


def _check(profile: Path, workshop: Path | None = None) -> playset.Check | None:
    return playset.check(profile, "rnw_exp_world_aaaa", workshop=workshop)


def test_a_later_mod_with_the_templates_file_replaces_the_worlds_file(profile: Path) -> None:
    """The reported symptom: another mod's file at the world's path is read, not the world's."""
    _ = _mod(profile / "mod", "maps", (TEMPLATES, "in_game/map_data/other.txt"), name="Maps")
    _playset(profile, _local("rnw_exp_world_aaaa"), _local("maps"))
    found = _check(profile)
    assert found is not None
    assert found.other_worlds == ()
    assert [(item.folder, item.title, item.files) for item in found.replacements] == [
        ("maps", "Maps", (TEMPLATES,))
    ]
    assert not found.clear


def test_a_mod_before_the_world_or_unticked_or_with_other_files_hides_nothing(
    profile: Path,
) -> None:
    """Order decides; an unticked mod is not loaded; files of other names are no collision."""
    _ = _mod(profile / "mod", "before", (TEMPLATES,))
    _ = _mod(profile / "mod", "off", (TEMPLATES,))
    _ = _mod(profile / "mod", "elsewhere", ("in_game/map_data/unrelated.txt", "readme.txt"))
    _playset(
        profile,
        _local("before"),
        _local("rnw_exp_world_aaaa"),
        (_local("off")[0], False),
        _local("elsewhere"),
    )
    found = _check(profile)
    assert found is not None
    assert found.clear
    assert found.unread == ()


def test_paths_are_compared_without_case_and_metadata_is_never_a_collision(
    profile: Path,
) -> None:
    """A case-blind file system reads ``IN_GAME/Map_Data/Location_Templates.TXT`` as the same."""
    _ = _mod(profile / "mod", "shouting", ("IN_GAME/Map_Data/Location_Templates.TXT",))
    _playset(profile, _local("rnw_exp_world_aaaa"), _local("shouting"))
    found = _check(profile)
    assert found is not None
    assert [item.files for item in found.replacements] == [(TEMPLATES,)]


def test_other_worlds_are_found_before_and_after_and_are_not_replacements(profile: Path) -> None:
    """Two worlds write the same files, wherever the second stands in the order."""
    _ = _mod(profile / "mod", "rnw_exp_world_bbbb", WORLD_FILES, name="Second")
    _ = _mod(profile / "mod", "rnw_exp_world_cccc", WORLD_FILES, name="Third")
    _playset(
        profile,
        _local("rnw_exp_world_bbbb"),
        _local("rnw_exp_world_aaaa"),
        _local("rnw_exp_world_cccc"),
    )
    found = _check(profile)
    assert found is not None
    assert found.other_worlds == ("Second", "Third")
    assert found.replacements == ()
    assert not found.clear


def test_there_is_nothing_to_say_for_a_world_that_is_not_ticked_or_a_playset_not_read(
    profile: Path,
) -> None:
    """No check without an active playset that holds the world, and none for an absent mod."""
    assert _check(profile) is None
    _playset(profile, _local("maps"))
    assert _check(profile) is None
    _playset(profile, (_local("rnw_exp_world_aaaa")[0], False))
    assert _check(profile) is None
    _playset(profile, _local("rnw_exp_world_aaaa"))
    assert playset.check(profile, "rnw_exp_world_gone") is None
    found = _check(profile)
    assert found is not None
    assert found.clear


def test_a_mod_whose_folder_is_not_found_is_counted_as_unread_not_as_clear(profile: Path) -> None:
    """The check does not claim what it could not see."""
    _playset(profile, _local("rnw_exp_world_aaaa"), _local("lost"), ("C:/steam/3599543453/", True))
    found = _check(profile)
    assert found is not None
    assert found.unread == ("lost", "3599543453")
    assert found.replacements == ()


def test_a_workshop_mod_is_read_where_the_games_library_keeps_it(
    profile: Path, tmp_path: Path
) -> None:
    """Windows paths of the playset are found again by folder: profile ``mod/``, then Workshop."""
    library = tmp_path / "lib"
    workshop = playset.workshop_root(
        GameInstall(library / "steamapps" / "common" / "g", library, "1")
    )
    assert workshop == library / "steamapps" / "workshop" / "content" / "3450310"
    assert workshop is not None
    _ = _mod(workshop, "3599543453", (TEMPLATES,), name="Terrain Mod")
    _playset(
        profile,
        _local("rnw_exp_world_aaaa"),
        ("C:/Program Files (x86)/Steam/steamapps/workshop/content/3450310/3599543453/", True),
    )
    found = _check(profile, workshop=workshop)
    assert found is not None
    assert [(item.folder, item.title) for item in found.replacements] == [
        ("3599543453", "Terrain Mod")
    ]
    assert playset.workshop_root(None) is None
    assert playset.workshop_root(GameInstall(tmp_path, None, "1")) is None
    unread = _check(profile)
    assert unread is not None
    assert unread.unread == ("3599543453",)


def _controller(tmp_path: Path, profile: Path) -> tuple[Controller, World]:
    controller = Controller(data=tmp_path / "data")
    assert controller.choose_profile(profile) is None
    world = World("aaaa", "RNW1-x", "continents", 1, "1.1.0", "26211608", 0, 1.0)
    assert world.folder == "rnw_exp_world_aaaa"
    controller.worlds = [world]
    return controller, world


def test_the_window_names_the_mod_that_replaces_the_world_and_the_other_ticked_worlds(
    tmp_path: Path, profile: Path
) -> None:
    """Both windows read these texts from the controller, in the window's language."""
    controller, world = _controller(tmp_path, profile)
    _ = _mod(profile / "mod", "rnw_exp_world_bbbb", WORLD_FILES, name="Second")
    _ = _mod(profile / "mod", "maps", (TEMPLATES, "in_game/map_data/definitions.txt"), name="Maps")
    _playset(profile, _local("rnw_exp_world_aaaa"))
    assert controller.playset_warnings(world) == []
    _playset(profile, _local("rnw_exp_world_aaaa"), _local("maps"), _local("rnw_exp_world_bbbb"))
    assert controller.playset_warnings(world) == []  # the answer is kept for a few seconds
    controller._playset.clear()  # pyright: ignore[reportPrivateUsage]
    warnings = controller.playset_warnings(world)
    assert warnings == [
        text(
            "playset_replaced",
            mod="Maps",
            files="in_game/map_data/definitions.txt, in_game/map_data/location_templates.txt",
        ),
        text("playset_worlds", names="Second"),
    ]
    assert "Clay" in warnings[0]
    assert "Maps" in warnings[0]


def test_a_world_in_the_game_shows_the_warnings_on_its_page(tmp_path: Path, profile: Path) -> None:
    """The Tauri window's world state carries them; a clean playset carries none."""
    controller, world = _controller(tmp_path, profile)
    _ = _mod(profile / "mod", "maps", (TEMPLATES,), name="Maps")
    _playset(profile, _local("rnw_exp_world_aaaa"), _local("maps"))
    controller.select(world.id)
    shown = cast("dict[str, object]", view.state(controller, view.Choices())["world"])
    assert cast("list[str]", shown["playset"]) == controller.playset_warnings(world)
    assert len(cast("list[str]", shown["playset"])) == 1
    controller._playset.clear()  # pyright: ignore[reportPrivateUsage]
    _playset(profile, _local("rnw_exp_world_aaaa"))
    shown = cast("dict[str, object]", view.state(controller, view.Choices())["world"])
    assert shown["playset"] == []


def test_the_report_lists_the_load_order_and_what_replaces_the_worlds_files(
    tmp_path: Path, profile: Path
) -> None:
    """The diagnostics file names each later mod with every file and what could not be read."""
    _ = _mod(profile / "mod", "maps", (TEMPLATES, "in_game/map_data/definitions.txt"), name="Maps")
    _ = _mod(profile / "mod", "rnw_exp_world_bbbb", WORLD_FILES, name="Second")
    _playset(
        profile,
        _local("rnw_exp_world_aaaa"),
        _local("maps"),
        _local("rnw_exp_world_bbbb"),
        _local("lost"),
    )
    snapshot = Snapshot(data=tmp_path / "data", profile=Profile(profile, "linux", has_mods=True))
    lines = diagnostics.report_text(snapshot)
    assert "in load order" in lines
    assert "rnw_exp_world_aaaa, maps, rnw_exp_world_bbbb, lost" in lines
    assert "rnw_exp_world_aaaa: ticked, position 1 of 4" in lines
    assert "other worlds ticked: Second" in lines
    assert (
        f"maps (Maps) comes later and has 2 files at its paths: "
        f"in_game/map_data/definitions.txt, {TEMPLATES}"
    ) in lines
    assert "later mods whose folders were not found: lost" in lines
    _playset(profile, _local("rnw_exp_world_aaaa"))
    clear = diagnostics.report_text(snapshot)
    assert "no later mod has files at its paths; no other world is ticked" in clear
    (profile / session.PLAYSETS).unlink()
    assert "unknown, the playset could not be read" in diagnostics.report_text(snapshot)
