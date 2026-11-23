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
    """Sixteen by sixteen pixels: a sea cell (0) and a land cell (1) beside a wasteland cell (2)
    that reaches the bottom edge, with a plan that drains the land into the sea."""
    labels = np.zeros((16, 16), dtype=np.int32)
    labels[:, 4:12] = 1
    labels[8:, 12:] = 2
    elevation = np.where(labels > 0, 100, 0).astype(np.int32)
    world = derive_world(labels, (CellClass.SEA, CellClass.LAND, CellClass.WASTELAND), elevation)
    # Coarse blocks are four pixels square: land drains west into the sea in column 0, and the
    # wasteland's blocks (rows 2 and 3 of column 3) drain through the land beside them.
    parent = np.full((4, 4), -1, dtype=np.int32)
    for row in range(4):
        parent[row, 1:3] = [row * 4, row * 4 + 1]
    parent[2:, 3] = [9, 13]
    return replace(world, drainage=DrainagePlan(seam=None, parents=(parent,)))


def test_a_cell_turned_to_sea_is_level_water_and_its_rivers_end_in_it() -> None:
    world = _island_world()
    turned = turned_to_sea(world, [2])
    assert turned.classes[2] is CellClass.SEA
    assert turned.classes[1] is CellClass.LAND
    assert turned.mean_elevation.tolist() == [0, 100, 0]
    assert turned.drainage is not None
    assert world.drainage is not None
    before, after = world.drainage.parents[0], turned.drainage.parents[0]
    # The blocks the wasteland covered no longer drain; everything else is as it was.
    assert after[2:, 3].tolist() == [-1, -1]
    assert np.array_equal(np.delete(after, [11, 15]), np.delete(before, [11, 15]))
    assert before[2:, 3].tolist() == [9, 13]
