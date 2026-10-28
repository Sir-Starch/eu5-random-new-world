"""The display seam divides drainage, never creates water or truncates a river."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_biomes import CLIMATE_STEP, ClimateGrid
from rnw.eu5_canvas import Canvas
from rnw.eu5_nw_export import (
    NewWorldExportError,
    _river_basins,  # pyright: ignore[reportPrivateUsage]
)
from rnw.eu5_rivers import encode_rivers, watershed_spans
from rnw.rivers import (
    NONE,
    SOURCE,
    flow_classes,
    network_problems,
    outlet_problems,
)
from tests.test_river_raster import WIDTHS, _fork  # pyright: ignore[reportPrivateUsage]
from tests.test_rivers import _valley  # pyright: ignore[reportPrivateUsage]


def _inputs(land: np.ndarray, seam: int) -> tuple[Canvas, ClimateGrid]:
    rows, columns = land.shape
    width = columns * 2 + 100
    canvas = Canvas(
        roll=seam,
        col0=0,
        mask=np.ones(land.shape, dtype=bool),
        shape=(rows, width),
        removed=np.zeros(0, dtype=bool),
        trimmed=np.zeros(0, dtype=bool),
    )
    rain = np.full((-(-rows // CLIMATE_STEP), -(-width // CLIMATE_STEP)), 1000, dtype=np.int64)
    return canvas, ClimateGrid(rain, np.zeros_like(rain), np.zeros_like(rain))


@pytest.mark.parametrize("seed", [5, 11, 23])
@pytest.mark.parametrize("seam", [0, 1, 3, 67, 90, 179, 180, 181])
def test_generated_basins_and_placed_raster_have_real_mouths(seed: int, seam: int) -> None:
    land, height, _ = _valley(220, 180)
    canvas, climate = _inputs(land, seam)
    original_land, original_height = land.copy(), height.copy()
    rivers = _river_basins(land, height.astype(np.int32), canvas, climate, seed)
    assert np.array_equal(land, original_land)
    assert np.array_equal(height, original_height)
    assert not any(network_problems(rivers.role, ~land).values())
    for left, right in watershed_spans(land.shape[1], seam):
        assert not any(outlet_problems(rivers.role[:, left:right], ~land[:, left:right]).values())
    classes = flow_classes(rivers, (615, 239, 81, 65))
    codes, stats = encode_rivers(rivers, classes, WIDTHS, seam=seam)
    assert not any(stats.values())
    assert np.count_nonzero(codes < 16) == np.count_nonzero(rivers.role != NONE)
    # Independent consumer: assemble the actual world raster. Never mark its edges
    # as fake water to make the validation pass (the former serializer tests did).
    role = np.full(canvas.shape, NONE, dtype=np.int8)
    water = np.zeros(canvas.shape, dtype=bool)
    world_columns = (np.arange(land.shape[1], dtype=np.int64) - canvas.roll) % canvas.shape[1]
    role[:, world_columns] = rivers.role
    water[:, world_columns] = ~land
    assert np.all(role[:, (0, -1)] == NONE)
    assert not any(network_problems(role, water).values())
    assert not any(outlet_problems(role, water).values())


def test_both_sides_drain_away_from_the_divide_and_are_independent() -> None:
    rows, columns, seam = 260, 300, 151  # divide is not aligned to the coarse river grid
    r, c = np.indices((rows, columns))
    land = (c >= 20) & (c < columns - 20)
    height = np.where(land, 6000 + np.minimum(c, columns - c) * 40 + abs(r - rows // 2), 0)
    canvas, climate = _inputs(land, seam)
    rivers = _river_basins(land, height.astype(np.int32), canvas, climate, 11)
    for left, right in watershed_spans(columns, seam):
        role = rivers.role[:, left:right]
        assert np.count_nonzero(role == SOURCE) > 0
        assert not any(outlet_problems(role, ~land[:, left:right]).values())
    changed = height.copy()
    changed[:, seam + 1 :] += ((r[:, seam + 1 :] * 37 + c[:, seam + 1 :] * 19) % 23) * 1200
    other = _river_basins(land, changed.astype(np.int32), canvas, climate, 11)
    assert np.array_equal(rivers.role[:, : seam - 1], other.role[:, : seam - 1])
    assert np.array_equal(rivers.flow[:, : seam - 1], other.flow[:, : seam - 1])
    assert not np.array_equal(rivers.flow[:, seam + 1 :], other.flow[:, seam + 1 :])
    rain = climate.rain.copy()
    wet_columns = np.unique((np.arange(seam + 1, columns, dtype=np.int64) - seam) // CLIMATE_STEP)
    rain[:, wet_columns] *= 100
    wetter = _river_basins(
        land,
        height.astype(np.int32),
        canvas,
        ClimateGrid(rain, climate.coast, climate.shore),
        11,
    )
    assert np.array_equal(rivers.role[:, : seam - 1], wetter.role[:, : seam - 1])
    assert np.array_equal(rivers.flow[:, : seam - 1], wetter.flow[:, : seam - 1])
    assert not np.array_equal(rivers.flow[:, seam + 1 :], wetter.flow[:, seam + 1 :])
    assert not np.any((rivers.role != NONE) & (c == seam - 1))
    assert not np.any((rivers.role != NONE) & (c == seam))


def test_water_on_the_other_side_does_not_become_a_seam_outlet() -> None:
    land = np.ones((100, 160), dtype=bool)
    land[:, :12] = False
    canvas, climate = _inputs(land, 80)
    height = np.where(land, 8000, 0).astype(np.int32)
    with pytest.raises(NewWorldExportError, match="no water outlet"):
        _ = _river_basins(land, height, canvas, climate, 5)


def test_a_wet_tributary_does_not_excuse_a_dry_main_line_end() -> None:
    rivers = _fork()
    water = np.zeros(rivers.role.shape, dtype=bool)
    water[5, 22] = True  # touches the tributary head, while the actual main outlet is dry
    assert not any(network_problems(rivers.role, water).values())
    assert outlet_problems(rivers.role, water)["inland_mouths"] == 1
    water[20, 45] = True  # actual coast at the main-line end
    assert not any(outlet_problems(rivers.role, water).values())
