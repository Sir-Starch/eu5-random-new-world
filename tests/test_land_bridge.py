"""The geometry of a land bridge: a cheap winding route, smoothed, with a body of varying width."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.land_bridge import (
    NoRouteError,
    Winding,
    lattice,
    paint,
    route,
    smooth,
    swell,
    trace,
    wind,
)
from rnw.noise import NOISE_SCALE


def _plain(height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    return np.full((height, width), 1000, dtype=np.int32), np.ones((height, width), dtype=bool)


def test_a_route_goes_round_a_wall_and_reaches_the_goal() -> None:
    cost, free = _plain(30, 40)
    free[5:25, 20] = False
    goal = np.zeros_like(free)
    goal[15, 39] = True
    blocks = route(cost, free, (15, 0), goal)
    assert blocks[0] == (15, 0)
    assert blocks[-1] == (15, 39)
    assert all(free[block] for block in blocks)
    assert any(row < 5 or row >= 25 for row, column in blocks if column == 20)


def test_a_route_over_open_ground_is_not_a_corner() -> None:
    """Sixteen moves leave no preferred direction: a diagonal goal is reached on a diagonal."""
    cost, free = _plain(40, 40)
    goal = np.zeros_like(free)
    goal[39, 39] = True
    blocks = route(cost, free, (0, 0), goal)
    assert len(blocks) <= 41
    assert len({row - column for row, column in blocks}) <= 3


def test_a_route_follows_cheap_ground_and_is_repeatable() -> None:
    cost, free = _plain(30, 60)
    cost[:, :] = 3000
    cost[20:23, :] = 1000
    goal = np.zeros_like(free)
    goal[:, 59] = True
    first = route(cost, free, (5, 0), goal)
    assert first == route(cost, free, (5, 0), goal)
    assert sum(1 for row, _ in first if 20 <= row < 23) > len(first) // 2


def test_a_long_straight_route_is_made_to_wind_and_a_short_one_is_left() -> None:
    cost, free = _plain(80, 400)
    goal = np.zeros_like(free)
    goal[40, 399] = True
    straight = route(cost, free, (40, 0), goal)
    assert {row for row, _ in straight} == {40}
    winding = Winding(spacing=30, low=4, high=8, key=7)
    bent = wind(straight, cost, free, goal, winding)
    assert bent[0] == (40, 0)
    assert bent[-1] == (40, 399)
    assert all(free[block] for block in bent)
    rows = [row for row, _ in bent]
    assert min(rows) <= 40 - 3
    assert max(rows) >= 40 + 3
    assert bent == wind(straight, cost, free, goal, winding)
    assert wind(straight[:25], cost, free, goal, winding) == straight[:25]


def test_a_route_that_cannot_wind_is_left_as_it_was() -> None:
    cost, free = _plain(3, 200)
    goal = np.zeros_like(free)
    goal[1, 199] = True
    straight = route(cost, free, (1, 0), goal)
    assert all(free[block] for block in wind(straight, cost, free, goal, Winding(20, 6, 9, 1)))


def test_a_route_that_cannot_reach_says_so() -> None:
    cost, free = _plain(10, 10)
    free[:, 5] = False
    goal = np.zeros_like(free)
    goal[5, 9] = True
    with pytest.raises(NoRouteError):
        _ = route(cost, free, (5, 0), goal)
    with pytest.raises(NoRouteError):
        _ = route(cost, free, (5, 0), np.zeros_like(free))


def test_smoothing_keeps_the_ends_and_leaves_no_corner() -> None:
    corner = [(0, 0), (0, 40), (40, 40)]
    line = smooth(corner)
    assert line[0] == corner[0]
    assert line[-1] == corner[-1]
    assert line == smooth(corner)
    middle = [point for point in line if abs(point[0] - 20) + abs(point[1] - 20) < 25]
    assert (0, 40) not in line
    assert min(abs(point[0]) + abs(point[1] - 40) for point in middle) > 2


def test_a_traced_axis_has_every_pixel_once_in_order() -> None:
    axis = trace([(0, 0), (3, 12), (3, 20)])
    assert axis[0].tolist() == [0, 0, 0]
    assert axis[-1].tolist() == [3, 20, 20]
    assert axis[:, 2].tolist() == list(range(len(axis)))
    assert np.max(np.abs(np.diff(axis[:, :2], axis=0))) <= 1


def test_lattice_noise_is_smooth_bounded_and_repeatable() -> None:
    noise = lattice(7, 400, 50)
    assert noise.shape == (401,)
    assert noise.min() >= 0
    assert noise.max() <= NOISE_SCALE
    assert np.array_equal(noise, lattice(7, 400, 50))
    assert not np.array_equal(noise, lattice(8, 400, 50))
    assert np.max(np.abs(np.diff(noise))) < NOISE_SCALE // 10


def test_the_ends_flare_and_the_middle_does_not() -> None:
    flare = swell(1000, 200)
    assert flare[0] == flare[-1] == NOISE_SCALE
    assert flare[500] == 0
    assert np.all(np.diff(flare[:201]) <= 0)


def test_a_painted_ridge_swells_with_its_radius_and_covers_its_axis() -> None:
    axis = trace([(40, 5), (40, 195)])
    length = int(axis[-1, 2])
    radius = np.where(np.arange(length + 1) < 100, 8, 20).astype(np.int64)
    edge = np.zeros((80, 200), dtype=np.int32)
    ridge = paint(axis, radius, edge, roughness_permille=0, every=2)
    assert ridge[axis[:, 0], axis[:, 1]].all()
    assert int(ridge[:, 50].sum()) in range(15, 19)
    assert int(ridge[:, 150].sum()) in range(39, 43)
    assert np.array_equal(ridge, paint(axis, radius, edge, roughness_permille=0, every=2))
    rough = paint(axis, radius, edge + NOISE_SCALE // 2, roughness_permille=600, every=2)
    assert rough.sum() > ridge.sum()
