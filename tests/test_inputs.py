"""Recording the game files a job reads, hashing them and comparing them with a manifest."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from rnw import inputs
from rnw.record import Manifest

if TYPE_CHECKING:
    from pathlib import Path


def _game(tmp_path: Path) -> Path:
    game = tmp_path / "game_install"
    for relative, text in (
        ("game/in_game/map_data/default.map", "map"),
        ("game/main_menu/setup/a.txt", "a"),
        ("game/main_menu/setup/b.txt", "b"),
        ("jomini/x.fxh", "x"),
    ):
        target = game / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(text, encoding="utf-8")
    return game


def test_a_new_file_in_a_directory_the_export_scanned_changes_the_inputs(tmp_path: Path) -> None:
    game = _game(tmp_path)
    directory = game / "game/main_menu/setup"
    with inputs.recording(game) as recorder:
        for path in directory.glob("*.txt"):
            _ = path.read_bytes()
        manifest = recorder.manifest(game, workers=1)
    assert inputs.compare(game, manifest, workers=1).same
    _ = (directory / "new.txt").write_text("new script", encoding="utf-8")
    changed = inputs.compare(game, manifest, workers=1)
    assert not changed.same
    assert "game/main_menu/setup/" in changed.changed
    assert Manifest.from_json(manifest.to_json()) == manifest


@pytest.mark.parametrize("name", ["../outside", "/etc/passwd", "C:/secret", "game/../../outside"])
def test_an_input_manifest_cannot_point_outside_the_game(name: str) -> None:
    from rnw.record import RecordError  # noqa: PLC0415

    with pytest.raises(RecordError):
        _ = Manifest.from_json({"format": 1, "files": {name: "f" * 64}})


def test_every_read_under_the_game_folder_is_recorded_whoever_makes_it(tmp_path: Path) -> None:
    """Path.read_text, open, read_bytes and a thread all show; other folders and writes do not."""
    game = _game(tmp_path)
    elsewhere = tmp_path / "elsewhere.txt"
    _ = elsewhere.write_text("x", encoding="utf-8")
    with inputs.recording(game) as recorder:
        _ = (game / "game/in_game/map_data/default.map").read_text(encoding="utf-8")
        with (game / "game/main_menu/setup/a.txt").open("rb") as handle:
            _ = handle.read()
        worker = threading.Thread(target=(game / "jomini/x.fxh").read_bytes)
        worker.start()
        worker.join()
        _ = elsewhere.read_text(encoding="utf-8")
        _ = (tmp_path / "out.txt").write_text("written", encoding="utf-8")
        with (game / "game/main_menu/setup/b.txt").open("a", encoding="utf-8") as handle:
            _ = handle.write("not a read")
        seen = recorder.freeze()
    assert seen == [
        "game/in_game/map_data/default.map",
        "game/main_menu/setup/a.txt",
        "jomini/x.fxh",
    ]


def test_nothing_is_recorded_outside_the_block_and_two_recordings_do_not_mix(
    tmp_path: Path,
) -> None:
    """A recording ends with its block; each sees the files under its own folder."""
    game, other = _game(tmp_path), _game(tmp_path / "other")
    with inputs.recording(game) as first, inputs.recording(other) as second:
        _ = (game / "jomini/x.fxh").read_bytes()
        _ = (other / "jomini/x.fxh").read_bytes()
        assert first.freeze() == ["jomini/x.fxh"]
        assert second.freeze() == ["jomini/x.fxh"]
    _ = (game / "game/main_menu/setup/a.txt").read_bytes()
    with inputs.recording(game) as third:
        assert third.freeze() == []


def test_a_new_game_file_after_the_end_of_the_recording_fails_loudly(tmp_path: Path) -> None:
    """The record would miss it; files already seen may be read again, as hashing does."""
    game = _game(tmp_path)
    with inputs.recording(game) as recorder:
        _ = (game / "jomini/x.fxh").read_bytes()
        _ = recorder.freeze()
        _ = (game / "jomini/x.fxh").read_bytes()
        with pytest.raises(inputs.InputsFrozenError, match=r"setup/a\.txt"):
            _ = (game / "game/main_menu/setup/a.txt").read_bytes()


def test_the_manifest_hashes_files_and_the_comparison_names_what_changed(tmp_path: Path) -> None:
    """Equal files compare equal; an edited and a deleted file are named, a new one is not seen."""
    game = _game(tmp_path)
    names = ["game/main_menu/setup/a.txt", "game/main_menu/setup/b.txt", "jomini/x.fxh"]
    manifest = inputs.hash_files(game, names, workers=2)
    assert set(manifest.files) == set(names)
    assert manifest.files["jomini/x.fxh"] == inputs.file_hash(game / "jomini/x.fxh")
    assert inputs.compare(game, manifest, workers=2).same
    _ = (game / "game/main_menu/setup/a.txt").write_text("edited", encoding="utf-8")
    (game / "jomini/x.fxh").unlink()
    _ = (game / "game/main_menu/setup/new.txt").write_text("new", encoding="utf-8")
    comparison = inputs.compare(game, manifest, workers=2)
    assert not comparison.same
    assert comparison.changed == ["game/main_menu/setup/a.txt"]
    assert comparison.missing == ["jomini/x.fxh"]
    assert isinstance(manifest, Manifest)
