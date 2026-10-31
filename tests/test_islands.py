"""Island groups stay where generated land leaves them room and otherwise move to free ocean."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.islands import Footprint, PlacementError, carve, place
from rnw.topology import within

if TYPE_CHECKING:
    from numpy.typing import NDArray

MARGIN = 8


def _footprint(rows: slice, columns: slice) -> Footprint:
    grid = np.zeros((200, 400), dtype=bool)
    grid[rows, columns] = True
    found = np.nonzero(grid)
    return Footprint(found[0].astype(np.int32), found[1].astype(np.int32))


def _world() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    domain = np.ones((200, 400), dtype=bool)
    land = np.zeros_like(domain)
    land[:, 160:240] = True
    return domain, land, domain & ~land


def test_a_group_clear_of_land_stays() -> None:
    domain, land, ocean = _world()
    group = _footprint(slice(90, 96), slice(40, 52))
    assert place(domain, land, ocean, [group], margin=MARGIN) == ((0, 0),)


def test_a_group_under_land_moves_to_the_nearest_free_ocean_keeping_its_shape() -> None:
    domain, land, ocean = _world()
    group = _footprint(slice(90, 100), slice(170, 190))
    ((rows, columns),) = place(domain, land, ocean, [group], margin=MARGIN)
    moved = np.zeros_like(domain)
    moved[group.rows + rows, group.columns + columns] = True
    assert moved.sum() == group.size
    assert not (moved & (within(land, MARGIN) | ~ocean)).any()
    assert abs(rows) <= 8
    assert columns % 8 == 0
    again = place(domain, land, ocean, [group], margin=MARGIN)
    assert again == ((rows, columns),)


def test_groups_keep_a_margin_from_each_other() -> None:
    domain, land, ocean = _world()
    first = _footprint(slice(90, 100), slice(170, 190))
    second = _footprint(slice(92, 102), slice(200, 216))
    moves = place(domain, land, ocean, [first, second], margin=MARGIN)
    paints: list[NDArray[np.bool_]] = []
    for group, (rows, columns) in zip((first, second), moves, strict=True):
        mask = np.zeros_like(domain)
        mask[group.rows + rows, group.columns + columns] = True
        paints.append(mask)
    assert not (paints[0] & within(paints[1], MARGIN)).any()
    assert not (paints[0] & ~ocean).any()
    assert not (paints[1] & ~ocean).any()


def test_a_group_that_no_ocean_can_hold_is_an_explicit_error() -> None:
    domain, land, ocean = _world()
    land[:, :] = True
    land[:, :40] = False
    ocean = domain & ~land
    group = _footprint(slice(90, 100), slice(100, 130))
    with pytest.raises(PlacementError, match="No free ocean"):
        _ = place(domain, land, ocean, [group], margin=MARGIN)


def test_carving_removes_the_groups_at_their_places() -> None:
    domain, _land, _ocean = _world()
    group = _footprint(slice(90, 100), slice(170, 190))
    carved = carve(domain, [group], [(8, -80)])
    assert carved[98:108, 90:110].sum() == 0
    assert carved.sum() == domain.sum() - group.size
    assert domain.all()
