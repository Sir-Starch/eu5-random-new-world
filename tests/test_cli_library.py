"""The commands that do what the window does with the worlds of the library."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np
from typer.testing import CliRunner

from rnw.app import discovery, install, library, preferences
from rnw.app.discovery import GameInstall, Profile
from rnw.bundle import COVER_COPY
from rnw.cli import app
from rnw.eu5_lobby import SCRIPTED_GUI_FILE
from rnw.pictures import TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png
from tests.fakes import build_game, build_world

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from rnw.app.library import World

RUNNER = CliRunner()


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[World, Path, GameInstall]:
    """A library with one world and a kept mod, a game and a profile the commands find."""
    game = build_game(tmp_path / "game")
    data = tmp_path / "data"
    world = build_world(data, game)
    profile = tmp_path / "profile"
    (profile / "mod").mkdir(parents=True)

    def games(*_arguments: object, **_keywords: object) -> list[GameInstall]:
        return [game]

    def profiles(*_arguments: object, **_keywords: object) -> list[Profile]:
        return [Profile(profile, "linux", has_mods=True)]

    monkeypatch.setattr(discovery, "find_games", games)
    monkeypatch.setattr(discovery, "find_profiles", profiles)
    return world, data, game


def _run(*arguments: str) -> tuple[int, str]:
    result = RUNNER.invoke(app, list(arguments))
    return result.exit_code, result.output


def test_the_library_is_listed_shown_named_and_revealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """worlds, show-world, rename-world, reveal-world, settings."""
    world, data, _game = _setup(tmp_path, monkeypatch)
    code, out = _run("worlds", "--data-dir", str(data))
    assert code == 0, out
    [row] = cast("list[dict[str, object]]", json.loads(out))
    assert row["id"] == world.id
    assert row["place"] == "kept"
    assert row["has_atlas"] is True
    assert row["revealed"] is False
    assert str(row["title"]).startswith("RNW: Continents ")
    code, out = _run("show-world", world.id, "--data-dir", str(data))
    shown = cast("dict[str, object]", json.loads(out))
    assert shown["atlas"] is None
    code, out = _run("rename-world", world.code, "Vinland", "--data-dir", str(data))
    assert code == 0, out
    assert json.loads(out)["name"] == "Vinland"
    mod = library.kept(data, world)
    assert mod is not None
    metadata = cast(
        "dict[str, str]", json.loads((mod / install.METADATA).read_text(encoding="utf-8-sig"))
    )
    assert metadata["name"] == "RNW: Vinland"
    code, out = _run("reveal-world", world.id, "--data-dir", str(data))
    assert json.loads(out)["revealed"] is True
    _code, out = _run("show-world", world.id, "--data-dir", str(data))
    assert cast("dict[str, dict[str, int]]", json.loads(out))["atlas"]["countries"] == 1
    _code, out = _run("reveal-world", world.id, "--cover", "--data-dir", str(data))
    assert json.loads(out)["revealed"] is False
    code, out = _run("settings", "--show-new-world", "--data-dir", str(data))
    assert json.loads(out) == {"show_new_world": True}
    _code, out = _run("settings", "--data-dir", str(data))
    assert json.loads(out) == {"show_new_world": True}
    _code, out = _run("settings", "--hide-new-world", "--data-dir", str(data))
    assert json.loads(out) == {"show_new_world": False}
    _code, out = _run("show-world", world.id, "--data-dir", str(data))
    assert cast("dict[str, object]", json.loads(out))["show_new_world"] is False
    mod = library.kept(data, world)
    assert mod is not None
    _ = mod.rename(tmp_path / "legacy-mod")
    code, out = _run("world-visibility", world.id, "--show-new-world", "--data-dir", str(data))
    assert code == 0, out
    assert json.loads(out)["show_new_world"] is True
    code, out = _run("settings", "--hide-new-world", "--data-dir", str(data))
    assert code == 0, out
    _code, out = _run("show-world", world.id, "--data-dir", str(data))
    assert cast("dict[str, object]", json.loads(out))["show_new_world"] is True
    assert library.load_one(library.folder(data, world)) is not None
    code, out = _run("show-world", "nothing", "--data-dir", str(data))
    assert code != 0


def test_maps_and_searches_follow_the_spoiler_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A covered world refuses; --reveal or a revealed world draws and answers."""
    world, data, _game = _setup(tmp_path, monkeypatch)
    picture = tmp_path / "out" / "land.png"
    code, out = _run("draw-map", world.id, "land", str(picture), "--data-dir", str(data))
    assert code == 2
    assert "covered" in out
    code, out = _run("search-atlas", world.id, "aland", "--data-dir", str(data))
    assert code == 2
    code, out = _run(
        "draw-map", world.id, "land", str(picture), "--reveal", "--data-dir", str(data)
    )
    assert code == 0, out
    assert picture.read_bytes().startswith(b"\x89PNG")
    code, out = _run(
        "draw-map", world.id, "weather", str(picture), "--reveal", "--data-dir", str(data)
    )
    assert code == 2
    code, out = _run("search-atlas", world.id, "aland", "--reveal", "--data-dir", str(data))
    assert code == 0, out
    found = cast("list[dict[str, object]]", json.loads(out))
    assert found[0]["kind"] == "country"
    _ = library.reveal(data, world)
    code, out = _run("search-atlas", world.id, "a", "--data-dir", str(data))
    assert code == 0, out


def test_world_visibility_uses_the_saved_profile_when_several_are_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, data, _game = _setup(tmp_path, monkeypatch)
    kept = library.kept(data, world)
    assert kept is not None
    first, selected = tmp_path / "profile-first", tmp_path / "profile-selected"
    first_mod, selected_mod = first / "mod" / world.folder, selected / "mod" / world.folder
    first_mod.parent.mkdir(parents=True)
    selected_mod.parent.mkdir(parents=True)
    _ = shutil.copytree(kept, first_mod)
    _ = shutil.copytree(kept, selected_mod)
    shutil.rmtree(kept)
    for mod in (first_mod, selected_mod):
        cover = mod / SCRIPTED_GUI_FILE
        cover.parent.mkdir(parents=True, exist_ok=True)
        _ = cover.write_text("selection cover", encoding="utf-8")
    bundle = library.folder(data, world)
    picture = np.zeros((32, 64, 3), dtype=np.uint8)
    picture[:, :20] = TERRA_INCOGNITA
    _ = (bundle / library.PREVIEW_HIDDEN).write_bytes(
        encode_png(picture, color_type=COLOR_RGB, compression="zlib")
    )
    picture[:, :20] = (96, 160, 72)
    _ = (bundle / library.PREVIEW).write_bytes(
        encode_png(picture, color_type=COLOR_RGB, compression="zlib")
    )
    canonical_cover = bundle / COVER_COPY / SCRIPTED_GUI_FILE
    canonical_cover.parent.mkdir(parents=True)
    _ = canonical_cover.write_text("selection cover", encoding="utf-8")
    preferences.save(data, replace(preferences.load(data), profile_dir=str(selected)))

    def profiles(*_args: object, **_kwargs: object) -> list[Profile]:
        return [
            Profile(first, "linux", has_mods=True),
            Profile(selected, "linux", has_mods=True),
        ]

    monkeypatch.setattr(discovery, "find_profiles", profiles)

    code, output = _run("world-visibility", world.id, "--show-new-world", "--data-dir", str(data))

    assert code == 0, output
    assert not (selected_mod / SCRIPTED_GUI_FILE).exists()
    assert (selected_mod / library.THUMBNAIL).is_file()
    assert (first_mod / SCRIPTED_GUI_FILE).is_file()
    assert not (first_mod / library.THUMBNAIL).exists()


def test_a_world_is_added_removed_copied_and_deleted_by_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """add-world puts the kept mod in the profile; remove-world takes it out; copy-mod and
    delete-world work on what is there."""
    world, data, game = _setup(tmp_path, monkeypatch)
    arguments = ["--game-dir", str(game.directory), "--data-dir", str(data)]
    code, out = _run("add-world", world.id, *arguments)
    assert code == 0, out
    profile = tmp_path / "profile"
    assert [mod.name for mod in install.installed_mods(profile)] == [world.folder]
    folder = tmp_path / "mods"
    folder.mkdir()
    code, out = _run("copy-mod", world.id, str(folder), "--data-dir", str(data))
    assert code == 0, out
    assert (folder / world.folder).is_dir()
    code, out = _run("copy-mod", world.id, str(folder), "--data-dir", str(data))
    assert code == 2
    code, out = _run("remove-world", world.id, "--data-dir", str(data))
    assert code == 0, out
    assert install.installed_mods(profile) == []
    code, out = _run("delete-world", world.id, "--data-dir", str(data))
    assert code == 0, out
    assert library.load(data) == []
    code, out = _run("copy-mod", "nothing", str(folder), "--data-dir", str(data))
    assert code != 0
