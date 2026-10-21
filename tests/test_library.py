"""The library of worlds: records, placements, strays, names and mod-list pictures."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.app import library
from rnw.app.library import Placement, World
from rnw.eu5_map import open_png
from rnw.pictures import SIZE, TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png

if TYPE_CHECKING:
    from pathlib import Path


def _world(seed: int, created: int = 100) -> World:
    code = f"RNW1-TEST-{seed}"
    return World(
        id=library.world_id(code, "26043558"),
        code=code,
        preset="continents",
        seed=seed,
        generator="0.9.14",
        game_build="26043558",
        created=created,
        seconds=90.0,
    )


def _bundle(data: Path, world: World, *, kept: bool = True) -> Path:
    folder = library.folder(data, world)
    if kept:
        (folder / world.folder / ".metadata").mkdir(parents=True)
        _ = (folder / world.folder / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
    folder.mkdir(parents=True, exist_ok=True)
    image = np.zeros((32, 64, 3), dtype=np.uint8)
    image[:, :20] = TERRA_INCOGNITA
    _ = (folder / library.PREVIEW_HIDDEN).write_bytes(
        encode_png(image, color_type=COLOR_RGB, compression="zlib")
    )
    image[:, :20] = (96, 160, 72)
    _ = (folder / library.PREVIEW).write_bytes(
        encode_png(image, color_type=COLOR_RGB, compression="zlib")
    )
    library.save(data, world)
    return folder


def test_records_load_newest_first_and_a_damaged_one_is_skipped(tmp_path: Path) -> None:
    """World ids come from code and build; records sort by time; a broken one is left out."""
    older, newer = _world(1, created=100), _world(2, created=200)
    _ = _bundle(tmp_path, older)
    _ = _bundle(tmp_path, newer)
    assert library.world_id("A", "1") != library.world_id("A", "2")
    assert len(older.id) == library.ID_LENGTH
    assert library.load(tmp_path) == [newer, older]
    _ = (library.folder(tmp_path, older) / library.RECORD).write_text("{", encoding="utf-8")
    assert library.load(tmp_path) == [newer]


def test_placement_names_and_forgetting(tmp_path: Path) -> None:
    """Kept beside the generator, in the game, or code only; a name is saved; forget removes."""
    world = _world(3)
    _ = _bundle(tmp_path / "data", world)
    profile = tmp_path / "profile"
    (profile / "mod").mkdir(parents=True)
    assert library.placement(tmp_path / "data", profile, world) is Placement.KEPT
    kept = library.kept(tmp_path / "data", world)
    assert kept is not None
    _ = kept.rename(profile / "mod" / world.folder)
    assert library.placement(tmp_path / "data", profile, world) is Placement.IN_GAME
    renamed = library.rename(tmp_path / "data", world, "  Vinland  ")
    assert library.load(tmp_path / "data") == [renamed]
    assert renamed.name == "Vinland"
    library.forget(tmp_path / "data", renamed)
    assert library.load(tmp_path / "data") == []


def test_worlds_in_the_game_without_a_record_are_strays(tmp_path: Path) -> None:
    """A world mod of the project the library does not know is listed; the hub is not."""
    profile = tmp_path / "profile"
    for name, world_like in (("rnw_exp_new_world", True), ("rnw_exp_hub", False)):
        mod = profile / "mod" / name
        (mod / ".metadata").mkdir(parents=True)
        _ = (mod / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
        if world_like:
            (mod / library.MAP_MARKER).mkdir(parents=True)
    assert [path.name for path in library.strays(profile, [])] == ["rnw_exp_new_world"]
    assert library.strays(None, []) == []


def test_the_mod_list_picture_is_covered_unless_asked(tmp_path: Path) -> None:
    """The square is drawn from the covered or the full preview, around the covered columns."""
    world = _world(4)
    folder = _bundle(tmp_path, world)
    mod = folder / world.folder
    assert library.picture(tmp_path, world, revealed=False) == folder / library.PREVIEW_HIDDEN
    assert library.write_thumbnail(tmp_path, world, mod, revealed=False)
    covered = open_png(mod / library.THUMBNAIL, "RGB")
    assert covered.shape == (SIZE, SIZE, 3)
    assert tuple(covered[SIZE // 2, SIZE // 2]) == TERRA_INCOGNITA
    assert library.write_thumbnail(tmp_path, world, mod, revealed=True)
    shown = open_png(mod / library.THUMBNAIL, "RGB")
    assert tuple(shown[SIZE // 2, SIZE // 2]) == (96, 160, 72)
    (folder / library.PREVIEW).unlink()
    assert not library.write_thumbnail(tmp_path, world, mod, revealed=True)
