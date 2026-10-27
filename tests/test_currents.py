"""Currents for generated deep water: continued from the game's, bent round land."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from rnw.currents import CurrentError, flow
from rnw.seas import Topography, analyse
from tests.block_worlds import block_world, cell

OPEN_SEA = ["." * 20 for _ in range(10)]
WITH_AN_ISLAND = [
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
    ".........######.....",
    ".........######.....",
    "....................",
    "....................",
    "....................",
]


def _deep(layout: list[str]) -> tuple[list[int], dict[int, list[tuple[int, int]]]]:
    waters = analyse(block_world(layout))
    deep = [n for n in waters.sea() if waters.topography[n] is Topography.DEEP_OCEAN]
    samples = {cell(layout, row, 0): [(9000, 0)] for row in range(len(layout))}
    return deep, samples


def test_a_sample_beside_deep_water_is_continued_into_it_at_the_game_s_strength() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    deep, samples = _deep(OPEN_SEA)
    flows = flow(world, waters, samples, deep)
    assert set(flows) == set(deep)
    assert deep
    for x, y in flows.values():
        assert abs(math.hypot(x, y) - 9000) < 2
        assert x > 8900
        assert abs(y) < 800


def test_the_strength_is_the_mean_of_the_currents_that_are_continued() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    samples = {
        cell(OPEN_SEA, row, 0): [(8000, 0) if row % 2 else (0, 10000)]
        for row in range(len(OPEN_SEA))
    }
    deep, _ = _deep(OPEN_SEA)
    flows = flow(world, waters, samples, deep)
    assert flows
    assert all(abs(math.hypot(*vector) - 9000) <= 2 for vector in flows.values())


def test_a_current_flowing_into_land_is_bent_along_it() -> None:
    """Flowing north-east towards an island to the east: the nearer the island, the more north."""
    world = block_world(WITH_AN_ISLAND)
    waters = analyse(world)
    deep, _ = _deep(WITH_AN_ISLAND)
    samples = {cell(WITH_AN_ISLAND, row, 0): [(6000, 6000)] for row in range(len(WITH_AN_ISLAND))}
    flows = flow(world, waters, samples, deep)
    near = flows[cell(WITH_AN_ISLAND, 5, 6)]
    far = flows[cell(WITH_AN_ISLAND, 0, 2)]
    assert abs(far[1] - far[0]) < 700
    assert near[1] > near[0] + 1500
    assert abs(math.hypot(*near) - math.hypot(*far)) < 5


def test_deep_water_with_no_current_of_the_game_beside_it_is_refused() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    deep, _ = _deep(OPEN_SEA)
    with pytest.raises(CurrentError, match="No current"):
        _ = flow(world, waters, {}, deep)


def test_a_world_without_deep_water_needs_no_currents() -> None:
    world = block_world(["..#", ".#.", "#.."])
    assert flow(world, analyse(world), {}, []) == {}


def test_currents_are_the_same_every_time() -> None:
    world = block_world(WITH_AN_ISLAND)
    waters = analyse(world)
    deep, samples = _deep(WITH_AN_ISLAND)
    assert flow(world, waters, samples, deep) == flow(world, waters, samples, deep)


def test_only_the_cells_given_as_lanes_carry_a_current() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    deep, samples = _deep(OPEN_SEA)
    lanes = deep[::3]
    flows = flow(world, waters, samples, lanes)
    assert set(flows) == set(lanes)
    assert lanes


@pytest.mark.parametrize("east", [8000, -8000])
def test_a_narrow_lane_follows_its_course_in_both_directions(east: int) -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    lane = [cell(OPEN_SEA, 5, column) for column in range(2, 18)]
    samples = {lane[0]: [(east, 5000)]}
    currents = flow(world, waters, samples, lane)
    for number in lane[1:-1]:
        x, y = currents[number]
        assert x * east > 0
        assert y == 0


def test_an_ambiguous_perpendicular_current_does_not_choose_a_corridor_direction() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    lane = [cell(OPEN_SEA, 5, column) for column in range(2, 18)]
    currents = flow(world, waters, {lane[0]: [(0, 9000)]}, lane)
    assert currents[lane[7]] == (0, 9000)


def test_a_source_across_closed_water_does_not_feed_a_current() -> None:
    layout = ["." * 9 for _ in range(5)]
    world = block_world(layout)
    waters = analyse(world)
    topography = list(waters.topography)
    for row in range(len(layout)):
        topography[cell(layout, row, 4)] = Topography.OCEAN_WASTELAND
    waters = replace(waters, topography=tuple(topography))
    with pytest.raises(CurrentError, match="through navigable water"):
        _ = flow(world, waters, {cell(layout, 2, 0): [(9000, 0)]}, [cell(layout, 2, 8)])


def test_opposing_sources_do_not_invent_an_eastward_current() -> None:
    world = block_world(OPEN_SEA)
    waters = analyse(world)
    lane = cell(OPEN_SEA, 5, 5)
    with pytest.raises(CurrentError, match="no direction"):
        _ = flow(world, waters, {lane: [(9000, 0), (-9000, 0)]}, [lane])
