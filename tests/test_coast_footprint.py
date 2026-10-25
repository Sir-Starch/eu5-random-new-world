"""A replaced island includes its visual shelf without consuming retained land."""

# pyright: reportAny=false

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import numpy as np
import pytest

from rnw.eu5_terrain import (
    COAST_APRON,
    SHORE_HEIGHT,
    WATER_PROFILE,
    Decal,
    TerrainInputs,
    _rebuild_decal,  # pyright: ignore[reportPrivateUsage]
    _touches_coast,  # pyright: ignore[reportPrivateUsage]
    coast_codes,
)
from rnw.terrain_tiles import LayerFormat, parse_info, read_level0
from tests.test_terrain_bands import FakeStore, _world  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("shift", [0, 150])
@pytest.mark.parametrize("band", [13, 120])
def test_removed_island_has_no_original_shelf_rim(shift: int, band: int) -> None:
    """The old subpixel shore is removed, including across the wrap; old land is exact."""
    rows, columns = 120, 192
    removed = np.zeros((rows, columns), dtype=bool)
    removed[40:70, 25:55] = True
    old_water = np.ones_like(removed)
    old_water[removed] = False
    old_water[40:70, 120:150] = False
    codes = np.full(removed.shape, -1, dtype=np.int8)
    codes[removed] = 0
    # A synthetic original coast extends into pixels classified as water, as in TR46.
    original = np.full((rows * 2, columns * 2), WATER_PROFILE[-1][1], dtype=np.uint16)
    original[76:144, 46:114] = SHORE_HEIGHT + 400
    original[80:140, 240:300] = 18_000
    original = np.roll(original, shift * 2, axis=1)
    codes = np.roll(codes, shift, axis=1)
    old_water = np.roll(old_water, shift, axis=1)
    removed = np.roll(removed, shift, axis=1)
    original_codes = codes.copy()
    source = TerrainInputs(
        codes=codes,
        vanilla_water=old_water,
        relief=lambda rs, cs: np.zeros((rs.stop - rs.start, cs.stop - cs.start), dtype=np.int32),
        labels=np.where(old_water | removed, 0, 1).astype(np.int32),
        rivers=np.zeros_like(removed),
    )
    _, defaults = _world(3)
    water = np.ones_like(defaults.water)
    water[1] = False
    tables = replace(defaults, water=water)
    decal = Decal("synthetic", 0, 0, rows, columns)
    store = FakeStore(decal=decal)
    store.layers["height"] = (LayerFormat(columns * 2, rows * 2, "<u2"), original)
    with ThreadPoolExecutor(max_workers=2) as pool:
        files, _ = _rebuild_decal(
            decal,
            store,  # pyright: ignore[reportArgumentType]
            source,
            tables,
            seed=3,
            pool=pool,
            band=band,
        )
    layer, spans = parse_info(files["in_game/synthetic_height.info"].decode())
    result = read_level0(layer, spans, files["in_game/synthetic_height.bin"])
    old_land = np.repeat(np.repeat(~old_water & ~removed, 2, axis=0), 2, axis=1)
    assert np.array_equal(result[old_land], original[old_land])
    rim = (original >= SHORE_HEIGHT) & ~old_land
    assert np.all(result[rim] == WATER_PROFILE[-1][1])
    assert np.array_equal(codes, original_codes)


def test_unchanged_shore_does_not_expand_the_visual_footprint() -> None:
    water = np.ones((40, 50), dtype=bool)
    water[10:30, 20:30] = False
    codes = np.full(water.shape, -1, dtype=np.int8)
    codes[10:30, 20:30] = 1
    assert np.array_equal(coast_codes(codes, water), codes)


def test_adjacent_and_opposite_edge_decals_include_changed_coast_support() -> None:
    codes = np.full((80, 200), -1, dtype=np.int8)
    codes[30, 100] = 0
    assert _touches_coast(Decal("next", 0, 101, 80, 40), codes)
    assert not _touches_coast(Decal("far", 0, 101 + COAST_APRON, 80, 40), codes)
    codes[30, -1] = 0
    assert _touches_coast(Decal("wrap", 0, 0, 80, 40), codes)
