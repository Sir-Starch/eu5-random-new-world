"""The sea route round the world: whether one exists, and the least that opens it."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.circuit import CircuitError, cheapest_opening, has_route
from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world, turned_to_sea
from rnw.watersheds import DrainagePlan

LAND = 4


def _ring(*cells: int) -> np.ndarray:
    """Three rows of land with a row of sea locations between them, two columns each."""
    sea = np.repeat(np.array(cells, dtype=np.int32), 2)
    land = np.full_like(sea, LAND)
    return np.stack((land, sea, land))


def test_a_row_of_water_across_the_wrap_is_a_route() -> None:
    labels = _ring(0, 1, 2)
    assert has_route(labels, [True, True, True, False, False])
    assert cheapest_opening(labels, [0, 0, 0, None, None]) == ()


def test_a_closed_location_breaks_the_route_and_is_the_one_to_open() -> None:
    labels = _ring(0, 1, 2)
    assert not has_route(labels, [True, False, True, False, False])
    assert cheapest_opening(labels, [0, 7, 0, None, None]) == (1,)


def test_the_cheaper_of_two_blocks_is_opened() -> None:
    labels = np.stack(
        (
            np.full(6, LAND, dtype=np.int32),
            np.array([0, 0, 1, 1, 2, 2], dtype=np.int32),
            np.array([0, 0, 3, 3, 2, 2], dtype=np.int32),
            np.full(6, LAND, dtype=np.int32),
        )
    )
    # The upper way is blocked by location 1 at 9, the lower one by location 3 at 5.
    assert cheapest_opening(labels, [0, 9, 0, 5, None]) == (3,)


def test_a_location_over_the_wrap_alone_is_no_route() -> None:
    # Location 0 stands at both edges and joins its two pieces over the wrap; with the middle
    # closed it is a bay at each edge, not a way round the world.
    labels = _ring(0, 1, 0)
    assert not has_route(labels, [True, False, False, False, False])
    assert has_route(labels, [True, True, False, False, False])


def test_nothing_opens_a_world_without_an_allowed_location() -> None:
    labels = _ring(0, 1, 2)
    with pytest.raises(CircuitError):
        _ = cheapest_opening(labels, [0, None, 0, None, None])


def test_the_opening_is_the_same_every_time() -> None:
    labels = _ring(0, 1, 2, 3)
    costs = [0, 3, 3, 0, None]
    assert cheapest_opening(labels, costs) == (1, 2)
    assert cheapest_opening(labels, costs) == cheapest_opening(labels, costs)


def _island_world() -> NewWorld:
    """Sixteen by sixteen pixels: a land cell (0) beside a wasteland cell (1) that reaches the
    bottom edge, and the sea (2), with a plan that drains the land into the sea."""
    labels = np.full((16, 16), 2, dtype=np.int32)
    labels[:, 4:12] = 0
    labels[8:, 12:] = 1
    elevation = np.where(labels < 2, 100, 0).astype(np.int32)
    world = derive_world(labels, (CellClass.LAND, CellClass.WASTELAND, CellClass.SEA), elevation)
    # Coarse blocks are four pixels square: land drains west into the sea in column 0, and the
    # wasteland's blocks (rows 2 and 3 of column 3) drain through the land beside them.
    parent = np.full((4, 4), -1, dtype=np.int32)
    for row in range(4):
        parent[row, 1:3] = [row * 4, row * 4 + 1]
    parent[2:, 3] = [9, 13]
    return replace(world, drainage=DrainagePlan(seam=None, parents=(parent,)))


def test_a_cell_turned_to_sea_is_level_water_and_its_rivers_end_in_it() -> None:
    world = _island_world()
    turned = turned_to_sea(world, [1])
    assert turned.classes[1] is CellClass.SEA
    assert turned.classes[0] is CellClass.LAND
    assert turned.mean_elevation.tolist() == [100, 0, 0]
    assert turned.drainage is not None
    assert world.drainage is not None
    before, after = world.drainage.parents[0], turned.drainage.parents[0]
    # The blocks the wasteland covered no longer drain; everything else is as it was.
    assert after[2:, 3].tolist() == [-1, -1]
    assert np.array_equal(np.delete(after, [11, 15]), np.delete(before, [11, 15]))
    assert before[2:, 3].tolist() == [9, 13]


def test_a_land_cell_turned_to_sea_leaves_the_land_numbered_before_the_water() -> None:
    # Four cells in a row: land 0 and 1, a wasteland 2 and the sea 3.
    labels = np.repeat(np.arange(4, dtype=np.int32), 2)[None, :].repeat(2, axis=0)
    kinds = (CellClass.LAND, CellClass.LAND, CellClass.WASTELAND, CellClass.SEA)
    world = derive_world(labels, kinds, np.where(labels < 3, 100, 0).astype(np.int32))
    world = replace(
        world,
        barrier=np.array([1, 2], dtype=np.int64),
        land_link=np.array([2], dtype=np.int64),
        planned=np.array([10, 20, 30, 0], dtype=np.int64),
    )
    turned = turned_to_sea(world, [0])
    assert turned.classes == (
        CellClass.LAND,
        CellClass.WASTELAND,
        CellClass.SEA,
        CellClass.SEA,
    )
    # The cells that stayed keep their order, the turned one leads the water.
    assert turned.labels[0].astype(np.int64).tolist() == [2, 2, 0, 0, 1, 1, 3, 3]  # pyright: ignore[reportAny]
    assert turned.barrier.tolist() == [0, 1]
    assert turned.land_link.tolist() == [1]
    assert turned.planned is not None
    assert turned.planned.tolist() == [20, 30, 0, 0]
    assert turned.mean_elevation.tolist() == [100, 100, 0, 0]
