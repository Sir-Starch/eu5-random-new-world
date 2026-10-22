"""The application's data folder and the preferences it keeps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.app import paths, preferences

if TYPE_CHECKING:
    from pathlib import Path


def test_data_folders_follow_each_platform(tmp_path: Path) -> None:
    """LOCALAPPDATA on Windows, XDG_DATA_HOME or ~/.local/share on Linux, Library on macOS."""
    home = tmp_path / "me"
    assert (
        paths.data_directory(
            system="win32", home=home, variables={"LOCALAPPDATA": str(tmp_path / "L")}
        )
        == tmp_path / "L" / "RandomNewWorld"
    )
    assert paths.data_directory(system="win32", home=home, variables={}) == (
        home / "AppData" / "Local" / "RandomNewWorld"
    )
    assert paths.data_directory(system="linux", home=home, variables={}) == (
        home / ".local" / "share" / "random-new-world"
    )
    assert (
        paths.data_directory(
            system="linux", home=home, variables={"XDG_DATA_HOME": str(tmp_path / "x")}
        )
        == tmp_path / "x" / "random-new-world"
    )
    assert paths.data_directory(system="darwin", home=home, variables={}) == (
        home / "Library" / "Application Support" / "RandomNewWorld"
    )
    assert paths.workspace(home).name == "generated"


def test_preferences_keep_the_new_world_hidden_until_changed(tmp_path: Path) -> None:
    """The default hides the New World; a saved choice comes back; damage gives the default."""
    assert preferences.load(tmp_path) == preferences.Preferences(show_new_world=False)
    preferences.save(tmp_path, preferences.Preferences(show_new_world=True))
    chosen = preferences.Preferences(show_new_world=False, game_dir="/g", profile_dir="/p")
    preferences.save(tmp_path / "second", chosen)
    assert preferences.load(tmp_path / "second") == chosen
    assert preferences.load(tmp_path).show_new_world
    _ = (tmp_path / preferences.FILE).write_text("{ not json", encoding="utf-8")
    assert not preferences.load(tmp_path).show_new_world


def test_the_data_folder_can_be_chosen_by_a_variable_or_kept_beside_the_program(
    tmp_path: Path,
) -> None:
    """RNW_DATA wins; a portable.txt beside the program keeps the data there; else the system's."""
    plain = paths.data_directory(system="linux", home=tmp_path / "home", variables={})
    assert plain == tmp_path / "home" / ".local/share/random-new-world"
    program = tmp_path / "program"
    program.mkdir()
    assert (
        paths.data_directory(system="linux", home=tmp_path / "home", variables={}, program=program)
        == plain
    )
    _ = (program / paths.PORTABLE).write_text("", encoding="utf-8")
    beside = paths.data_directory(
        system="linux", home=tmp_path / "home", variables={}, program=program
    )
    assert beside == program / paths.PORTABLE_FOLDER
    chosen = tmp_path / "mine"
    both = paths.data_directory(
        system="win32",
        home=tmp_path / "home",
        variables={paths.ENV_DATA: str(chosen)},
        program=program,
    )
    assert both == chosen
    assert (
        paths.data_directory(
            system="win32", home=tmp_path / "home", variables={"LOCALAPPDATA": str(tmp_path / "la")}
        )
        == tmp_path / "la" / "RandomNewWorld"
    )
