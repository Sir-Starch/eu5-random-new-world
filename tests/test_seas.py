"""The shapes of generated water on small worlds drawn as blocks of 30 pixels (the scale)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.seas import PassageKind, Shape, Topography, analyse
from tests.block_worlds import block_world, cell

OPEN_SEA_WITH_AN_ISLAND = [
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......#........",
    "................",
    "................",
    "................",
    "................",
    "................",
]
WALL_WITH_A_GAP = [
    "..............",
    "..............",
    "#######.######",
    "#######.######",
    "..............",
    "..............",
]
LAGOON = [
    "................",
    "................",
    "..############..",
    "..#..........#..",
    "..#..........#..",
    "..#..........#..",
    "..#..........#..",
    "..####....####..",
    "................",
    "................",
    "................",
    "................",
]


def test_depth_counts_the_cells_from_land_and_names_the_game_s_topography() -> None:
    world = block_world(OPEN_SEA_WITH_AN_ISLAND)
    waters = analyse(world)
    island = cell(OPEN_SEA_WITH_AN_ISLAND, 5, 7)
    assert waters.hop[island] == -1
    ring = [
        cell(OPEN_SEA_WITH_AN_ISLAND, row, column)
        for row, column in ((4, 7), (6, 7), (5, 6), (5, 8))
    ]
    assert [int(waters.hop[number]) for number in ring] == [0, 0, 0, 0]
    assert all(waters.topography[number] is Topography.COASTAL_OCEAN for number in ring)
    corner = cell(OPEN_SEA_WITH_AN_ISLAND, 4, 6)
    assert waters.hop[corner] == 1
    assert waters.topography[corner] is Topography.OCEAN
    far = cell(OPEN_SEA_WITH_AN_ISLAND, 0, 0)
    assert waters.hop[far] >= 2
    assert waters.topography[far] is Topography.DEEP_OCEAN
    assert waters.topography[island] is None


def test_a_cell_beside_land_the_world_does_not_hold_is_on_a_coast_too() -> None:
    """The game's own islet inside the canvas: its water is coastal, and deep ocean is not."""
    layout = ["#" + "." * 14 for _ in range(9)]
    world = block_world(layout)
    islet = cell(layout, 4, 10)
    waters = analyse(world, shore=[islet])
    assert waters.hop[islet] == 0
    assert waters.topography[islet] is Topography.COASTAL_OCEAN
    assert waters.topography[cell(layout, 4, 11)] is Topography.OCEAN
    assert analyse(world).topography[islet] is Topography.DEEP_OCEAN


def test_the_water_of_a_small_island_is_the_island_s() -> None:
    waters = analyse(block_world(OPEN_SEA_WITH_AN_ISLAND))
    ring = [
        cell(OPEN_SEA_WITH_AN_ISLAND, row, column)
        for row, column in ((4, 7), (6, 7), (5, 6), (5, 8))
    ]
    assert [Shape(waters.shape[number]) for number in ring] == [Shape.ISLE] * 4
    assert Shape(waters.shape[cell(OPEN_SEA_WITH_AN_ISLAND, 0, 0)]) is Shape.OPEN
    assert waters.bodies == ()
    assert waters.passages == ()


def test_a_gap_in_a_wall_is_a_strait_between_two_waters() -> None:
    waters = analyse(block_world(WALL_WITH_A_GAP))
    gap = {cell(WALL_WITH_A_GAP, 2, 7), cell(WALL_WITH_A_GAP, 3, 7)}
    assert len(waters.passages) == 1
    assert set(waters.passages[0].cells) == gap
    assert waters.passages[0].kind is PassageKind.STRAIT
    assert all(waters.topography[number] is Topography.NARROWS for number in gap)
    assert all(Shape(waters.shape[number]) is Shape.NARROW for number in gap)


def test_a_lagoon_with_a_narrow_mouth_is_a_body_of_inland_sea() -> None:
    waters = analyse(block_world(LAGOON))
    inside = {cell(LAGOON, row, column) for row in range(3, 7) for column in range(3, 13)}
    assert len(waters.bodies) == 1
    assert inside <= set(waters.bodies[0])
    assert all(waters.topography[number] is Topography.INLAND_SEA for number in waters.bodies[0])
    outside = cell(LAGOON, 11, 0)
    assert waters.topography[outside] is Topography.DEEP_OCEAN
    assert waters.body[outside] == -1


def test_a_hole_in_an_archipelago_is_a_sea_of_its_own() -> None:
    """Open water with no way to the outside is enclosed however wide it is."""
    layout = [
        "##############",
        "##..........##",
        "##..........##",
        "##..........##",
        "##..........##",
        "##..........##",
        "##############",
    ]
    waters = analyse(block_world(layout))
    inside = {cell(layout, row, column) for row in range(1, 6) for column in range(2, 12)}
    assert len(waters.bodies) == 1
    assert set(waters.bodies[0]) == inside


def test_a_cape_a_bay_and_a_plain_coast_are_told_apart_by_the_land_round_them() -> None:
    """The water at the tip of a spit has little land round it, in the angle between spit and
    shore much, along a straight shore a share between."""
    layout = [
        "....................",
        "....................",
        "....................",
        "....................",
        "........#...........",
        "........#...........",
        "........#...........",
        "####################",
        "####################",
        "####################",
    ]
    waters = analyse(block_world(layout))

    def shape(row: int, column: int) -> Shape:
        return Shape(waters.shape[cell(layout, row, column)])

    assert shape(3, 8) is Shape.CAPE
    assert shape(5, 7) is Shape.BAY
    assert shape(5, 9) is Shape.BAY
    assert shape(6, 0) is Shape.COAST
    assert shape(0, 0) is Shape.OPEN


def test_the_shape_of_water_is_the_same_every_time() -> None:
    first = analyse(block_world(LAGOON))
    second = analyse(block_world(LAGOON))
    assert np.array_equal(first.hop, second.hop)
    assert np.array_equal(first.shape, second.shape)
    assert first.bodies == second.bodies
    assert first.topography == second.topography
