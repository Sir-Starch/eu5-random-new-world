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
    assert preferences.load(tmp_path) == preferences.Preferences(reveal_thumbnails=False)
    preferences.save(tmp_path, preferences.Preferences(reveal_thumbnails=True))
    assert preferences.load(tmp_path).reveal_thumbnails
    _ = (tmp_path / preferences.FILE).write_text("{ not json", encoding="utf-8")
    assert not preferences.load(tmp_path).reveal_thumbnails
