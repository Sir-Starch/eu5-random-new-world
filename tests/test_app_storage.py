"""The application's data folder and its history file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.app import history, paths

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


def test_history_keeps_the_newest_first_and_survives_damage(tmp_path: Path) -> None:
    """Entries come back newest first, are capped, and a damaged file reads as empty."""
    assert history.load(tmp_path) == []
    for number in range(history.LIMIT + 5):
        _ = history.record(
            tmp_path, history.Entry(f"RNW1-{number}", number, "26043558", "installed")
        )
    entries = history.load(tmp_path)
    assert len(entries) == history.LIMIT
    assert entries[0].code == f"RNW1-{history.LIMIT + 4}"
    assert entries[0].outcome == "installed"
    _ = (tmp_path / history.FILE).write_text("{ not json", encoding="utf-8")
    assert history.load(tmp_path) == []
    _ = (tmp_path / history.FILE).write_text('{"schema": 99, "entries": []}', encoding="utf-8")
    assert history.load(tmp_path) == []
    again = history.record(tmp_path, history.Entry("RNW1-X", 1, "", "failed", "boom"))
    assert [entry.note for entry in again] == ["boom"]
    assert history.now() > 1_700_000_000
