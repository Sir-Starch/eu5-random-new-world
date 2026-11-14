"""Epoch 64: the rivers wear the land down to their graded beds (``rnw.basins``)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false, reportPrivateUsage=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import basins
from rnw.fields import PERMILLE, block_mean, upsample
from rnw.relief import COAST_HEIGHT, HINT_STEP, ReliefHints, generate_relief
from rnw.rivers import STEP
from rnw.watersheds import plan_drainage

if TYPE_CHECKING:
    from rnw.watersheds import DrainagePlan


def _land(seed: int, shape: tuple[int, int]) -> np.ndarray:
    generator = np.random.default_rng(seed)
    coarse = generator.integers(0, 1000, (shape[0] // 80 + 2, shape[1] // 80 + 2))
    land = upsample(coarse, 80, shape) > 380
    land[:8] = False
    land[-8:] = False
    land[:, :8] = False
    land[:, -8:] = False
    return land


def _world(
    seed: int, shape: tuple[int, int] = (320, 480), seam: int | None = 241
) -> tuple[np.ndarray, np.ndarray, DrainagePlan]:
    land = _land(seed, shape)
    lakes = np.zeros_like(land)
    relief = generate_relief(land, seed=seed, lakes=lakes, margins=True)
    plan = plan_drainage(land, relief, lakes=lakes, seam=seam, seed=seed)
    return land, relief, plan


def _hints(shape: tuple[int, int], mountains: np.ndarray | None = None) -> ReliefHints:
    grid = (-(-shape[0] // HINT_STEP) + 1, -(-shape[1] // HINT_STEP) + 1)
    empty = np.zeros(grid, dtype=np.int32)
    painted = empty if mountains is None else mountains.astype(np.int32)
    return ReliefHints(painted, empty.copy(), empty.copy(), empty.copy())


def test_the_land_is_only_worn_down_and_the_sea_is_untouched() -> None:
    land, relief, plan = _world(7)
    worn = relief.copy()
    basins.shape_relief(worn, land, plan, seed=7)
    again = relief.copy()
    basins.shape_relief(again, land, plan, seed=7)
    assert np.array_equal(worn, again)
    assert np.array_equal(worn[~land], relief[~land])
    assert np.all(worn[land] <= relief[land])
    assert np.all(worn[land] >= COAST_HEIGHT)
    assert np.count_nonzero(worn[land] < relief[land] - 500) > land.sum() // 20


def test_painted_mountains_are_not_worn() -> None:
    land, relief, plan = _world(7)
    shape = (int(land.shape[0]), int(land.shape[1]))
    whole = _hints(shape, np.full(_hints(shape).mountains.shape, PERMILLE))
    worn = relief.copy()
    basins.shape_relief(worn, land, plan, seed=7, hints=whole)
    assert np.array_equal(worn, relief)


def test_a_column_of_cells_between_the_spans_takes_the_bed_beside_it() -> None:
    land = np.zeros((320, 480), dtype=bool)
    land[40:280, 60:420] = True
    lakes = np.zeros_like(land)
    relief = generate_relief(land, seed=5, lakes=lakes, margins=True)
    seam = 4 * 60 + 1  # the spans leave a column of cells between them
    plan = plan_drainage(land, relief, lakes=lakes, seam=seam, seed=5)
    grid = basins._grid(*land.shape, plan)
    assert grid.between == ((seam + 2) // STEP,)
    column = grid.between[0]
    change = basins.basin_change(relief, land, plan, seed=5)
    rows = slice(40 // STEP + 4, 280 // STEP - 4)
    beside = np.stack([change[rows, column - 1], change[rows, column + 1]])
    # Within the smoothing's reach of its neighbours, not a ditch along the seam.
    assert np.all(change[rows, column] >= beside.min(axis=0) - 50)


def _climbs(height: np.ndarray, plan: DrainagePlan) -> int:
    """Steps of the larger rivers of ``plan`` whose next cell stands 500 above them."""
    rows, columns = (int(size) for size in height.shape)
    grid = basins._grid(rows, columns, plan)
    padded = np.pad(height, ((0, -rows % STEP), (0, -columns % STEP)), mode="edge")
    coarse = block_mean(padded.astype(np.int64), STEP)
    coarse = np.pad(coarse, ((0, 0), (0, grid.over.shape[1] - coarse.shape[1])))
    flat = coarse.ravel()
    river = grid.over.ravel() & (grid.links >= 0) & (grid.catchment.ravel() >= 40)
    cells = np.flatnonzero(river)
    cells = cells[grid.over.ravel()[grid.links[cells]]]
    return int(np.count_nonzero(flat[grid.links[cells]] - flat[cells] > 500))


def test_the_larger_rivers_climb_no_more_often_than_on_the_planned_relief() -> None:
    for seed in (3, 11):
        land, relief, plan = _world(seed)
        worn = relief.copy()
        basins.shape_relief(worn, land, plan, seed=seed)
        assert _climbs(worn, plan) <= _climbs(relief, plan)


def test_every_landmass_draws_its_fall_and_its_share_of_shields() -> None:
    over = np.zeros((400, 600), dtype=bool)
    over[20:380, 20:280] = True
    over[20:380, 320:580] = True
    settings = basins.BASINS
    shares: list[int] = []
    for seed in range(6):
        fall, softness = basins._landmass_draws(over, seed, settings)
        for window in (slice(20, 280), slice(320, 580)):
            values = np.unique(fall[20:380, window])
            assert values.size == 1
            assert settings.gradient[0] <= int(values[0]) <= settings.gradient[1]
            shares.append(int(np.count_nonzero(softness[20:380, window] < PERMILLE // 2)))
        assert np.all(softness[~over] == PERMILLE)
    assert len(set(shares)) > 3


def _with_spread(seed: int) -> tuple[np.ndarray, np.ndarray, DrainagePlan, np.ndarray]:
    land = _land(seed, (320, 480))
    lakes = np.zeros_like(land)
    spread = np.zeros(land.shape, dtype=np.int16)
    relief = generate_relief(land, seed=seed, lakes=lakes, margins=True, spread=spread)
    plan = plan_drainage(land, relief, lakes=lakes, seam=241, seed=seed)
    return land, relief, plan, spread


def test_the_hills_roughen_outside_the_valley_floors_and_the_rivers_keep_their_climbs() -> None:
    low, _, _, top = basins.BASINS.hill_band
    for seed in (3, 11):
        land, relief, plan, spread = _with_spread(seed)
        worn = relief.copy()
        basins.shape_relief(worn, land, plan, seed=seed)
        rough = relief.copy()
        basins.shape_relief(rough, land, plan, seed=seed, spread=spread)
        assert np.array_equal(rough[~land], relief[~land])
        assert np.all(rough[land] >= COAST_HEIGHT)
        moved = np.abs(rough.astype(np.int64) - worn) > 300
        assert np.count_nonzero(moved) > land.sum() // 50
        # Coastal plains stay flat, and the high ground keeps the hills it has.
        outside = land & ((worn < low) | (worn >= top))
        assert np.array_equal(rough[outside], worn[outside])
        assert _climbs(rough, plan) <= _climbs(relief, plan)


def test_a_river_keeps_no_hills_on_its_valley_floor() -> None:
    land, _, plan = _world(3)
    rows, columns = (int(size) for size in land.shape)
    grid = basins._grid(rows, columns, plan)
    kept = basins.valley_floors(grid, basins.BASINS)
    river = grid.over & (grid.catchment >= basins.BASINS.valley_catchment)
    assert river.any()
    assert np.all(kept[river] == 0)
    assert np.all((kept >= 0) & (kept <= PERMILLE))
    assert np.count_nonzero(kept[grid.over] == PERMILLE) > grid.over.sum() // 10
