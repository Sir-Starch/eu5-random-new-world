"""A moved island group takes its decal pixels, mountain stamps, instances and water with it."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np

from rnw import eu5_terrain
from rnw.eu5_islands import Moved
from rnw.eu5_objects import InstanceSet, carry_records
from rnw.eu5_terrain import DECAL_CACHE, Decal, DecalStore, ShiftedStore, disable_decals
from rnw.eu5_water import carry_pixels
from rnw.terrain_tiles import LayerFormat

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

WIDTH = 64


def _moved(across: int = 20) -> Moved:
    """One 2 x 2 group at rows 10-11, columns 8-9, moved 5 rows down and ``across`` columns."""
    rows = np.array([10, 10, 11, 11], dtype=np.int64)
    columns = np.array([8, 9, 8, 9], dtype=np.int64)
    return Moved(
        rows,
        columns,
        np.full(4, 5, dtype=np.int64),
        np.full(4, across, dtype=np.int64),
        WIDTH,
        rows * WIDTH + columns,
    )


def test_moved_pixels_are_found_and_reported_at_their_new_places() -> None:
    moved = _moved()
    found, down, across = moved.find(np.array([10, 11, 12]), np.array([9, 8, 8]))
    assert found.tolist() == [True, True, False]
    assert (down.tolist(), across.tolist()) == ([5, 5, 0], [20, 20, 0])
    assert moved.new_rows.tolist() == [15, 15, 16, 16]
    assert moved.new_columns.tolist() == [28, 29, 28, 29]


def test_a_decal_store_shows_the_moved_group_at_its_new_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / DECAL_CACHE
    cache.parent.mkdir(parents=True)
    _ = cache.write_text("[]", encoding="utf-8")
    store = ShiftedStore(tmp_path, (32, WIDTH), _moved(40))
    store.decals = [Decal("left", 0, 0, 32, 32), Decal("right", 0, 32, 32, 32)]
    images = {
        "left": np.arange(64 * 64, dtype=np.uint16).reshape(64, 64),
        "right": np.zeros((64, 64), dtype=np.uint16),
    }

    def vanilla(_self: DecalStore, decal: str, _kind: str) -> tuple[LayerFormat, np.ndarray]:
        return LayerFormat(64, 64, "<u2"), images[decal].copy()

    monkeypatch.setattr(DecalStore, "layer", vanilla)
    _, right = store.layer("right", "height")
    # Location pixel (15, 48) stands in the right decal at decal pixels (30..31, 32..33); its
    # values are those of the old pixel (10, 8): decal pixels (20..21, 16..17) of the left decal.
    for sub_row in range(2):
        for sub_column in range(2):
            assert (
                right[30 + sub_row, 32 + sub_column]
                == images["left"][20 + sub_row, 16 + sub_column]
            )
    assert (store.layer("left", "height")[1] == images["left"]).all()
    assert right[0, 0] == 0


def test_a_mountain_stamp_on_a_moved_island_moves_instead_of_being_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_edges(_store: DecalStore) -> tuple[dict[str, dict[str, object]], dict[str, bytes]]:
        return {}, {}

    monkeypatch.setattr(eu5_terrain, "_wrapped_heightmaps", no_edges)
    cache = tmp_path / DECAL_CACHE
    cache.parent.mkdir(parents=True)
    entry = {
        "decal_name": "mountain_01",
        "decal_transform": {"position": {"x": 8 * 4 + 2, "y": (31 - 10) * 4 + 1}},
    }
    _ = cache.write_text(json.dumps([entry]), encoding="utf-8")
    folder = tmp_path / eu5_terrain.TERRAIN / "decals" / "mountain_01" / "instances"
    folder.mkdir(parents=True)
    text = '{\n\t"position.x":\t34,\n\t"position.y":\t85,\n\t"disabled":\tfalse\n}'
    _ = (folder / "a.json").write_text(text, encoding="utf-8")
    store = ShiftedStore(tmp_path, (32, WIDTH), _moved())
    codes = np.zeros((32, WIDTH), dtype=np.int8)
    files, kept = disable_decals(store, codes, _moved())
    relative = "in_game/gfx/terrain2/decals/mountain_01/instances/a.json"
    moved_text = files[relative].decode("utf-8")
    assert '"position.x":\t114' in moved_text
    assert '"position.y":\t65' in moved_text
    assert '"disabled":\tfalse' in moved_text
    position = json.loads(kept.decode("utf-8-sig"))[0]["decal_transform"]["position"]
    assert position == {"x": 8 * 4 + 2 + 80, "y": (31 - 10) * 4 + 1 - 20}
    plain, dropped = disable_decals(store, codes)
    assert '"disabled":\ttrue' in plain[relative].decode("utf-8")
    assert json.loads(dropped.decode("utf-8-sig")) == []


def test_instances_on_a_moved_island_move_with_it() -> None:
    records = np.zeros((3, 10), dtype=np.float32)
    records[:, 0] = [4.6, 4.6, 40.0]
    records[:, 2] = [21.4, 3.0, 3.0]
    found = carry_records(InstanceSet("p", "n", records), _moved(), 32, WIDTH)
    assert found is None
    records[:, 0] = [8.6, 4.6, 40.0]
    records[:, 2] = [21.4, 21.4, 3.0]
    found = carry_records(InstanceSet("p", "n", records), _moved(), 32, WIDTH)
    assert found is not None
    assert found.records[0, 0] == np.float32(28.6)
    assert found.records[0, 2] == np.float32(16.4)
    assert found.records[1, 0] == np.float32(4.6)
    assert found.records[2, 0] == np.float32(40.0)


def test_water_texture_pixels_of_a_moved_island_move_with_it() -> None:
    image = np.zeros((16, 32, 4), dtype=np.uint8)
    image[5, 4] = (9, 8, 7, 6)
    placed = carry_pixels(image, _moved(), 2)
    assert placed is not None
    assert tuple(image[7, 14]) == (9, 8, 7, 6)
    assert placed[7, 14]
    assert carry_pixels(image, None, 2) is None
