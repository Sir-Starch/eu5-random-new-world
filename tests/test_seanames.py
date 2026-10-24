"""Names for generated water: one sea, one name; places for straits, coasts and islands."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from rnw import wording
from rnw.model import CellClass
from rnw.seanames import (
    SEA_CELLS,
    Kind,
    Placement,
    SeaNames,
    _sector,  # pyright: ignore[reportPrivateUsage]
    name_waters,
    reference,
)
from rnw.seas import Topography, Waters, analyse
from rnw.wording import english, render
from tests.block_worlds import block_world, cell

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rnw.newworld import NewWorld

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
WALL_WITH_A_GAP = [
    "..............",
    "..............",
    "#######.######",
    "#######.######",
    "..............",
    "..............",
]
ISLAND = [
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


def _named(
    layout: Sequence[str],
    *,
    seed: int = 1,
    area: Callable[[int, int], str] = lambda _row, _column: "an_area",
    ocean: Callable[[str], bool] = lambda _area: False,
) -> tuple[NewWorld, Waters, SeaNames, dict[int, tuple[int, int]]]:
    world = block_world(layout)
    waters = analyse(world)
    where: dict[int, tuple[int, int]] = {}
    placed: list[Placement | None] = [None] * len(world.classes)
    for row, line in enumerate(layout):
        for column, _ in enumerate(line):
            number = cell(layout, row, column)
            if world.classes[number] is CellClass.SEA:
                where[number] = (row, column)
                name = area(row, column)
                placed[number] = Placement(f"province_{row // 3}_{name}", name, ocean(name))
    return world, waters, name_waters(world, waters, placed, seed=seed), where


def test_every_cell_of_a_sea_has_its_name_and_the_cells_of_one_sea_share_it() -> None:
    world, waters, names, _ = _named(LAGOON)
    inside = [cell(LAGOON, row, column) for row in range(3, 7) for column in range(4, 12)]
    assert len(waters.bodies[0]) >= SEA_CELLS
    heart = {names.cells[number] for number in inside if waters.hop[number] > 0}
    assert len(heart) == 1
    assert english(next(iter(heart))).endswith(" Sea")
    assert all(names.cells[number] for number in waters.sea())
    assert set(names.cells) == set(waters.sea())
    assert world.classes[cell(LAGOON, 2, 2)] is CellClass.LAND


def test_the_cells_of_a_strait_are_one_strait() -> None:
    _, waters, names, _ = _named(WALL_WITH_A_GAP)
    gap = [cell(WALL_WITH_A_GAP, 2, 7), cell(WALL_WITH_A_GAP, 3, 7)]
    assert {names.cells[number] for number in gap} == {names.cells[gap[0]]}
    assert english(names.cells[gap[0]]).endswith(" Strait")
    assert waters.passages[0].cells == tuple(gap)


def test_the_water_round_an_island_is_called_after_it() -> None:
    _, _, names, _ = _named(ISLAND)
    ring = [cell(ISLAND, row, column) for row, column in ((4, 7), (6, 7), (5, 6), (5, 8))]
    assert len({names.cells[number] for number in ring}) == 1
    assert english(names.cells[ring[0]]).endswith(" Island")


def test_open_water_takes_the_name_of_its_area_and_an_ocean_area_keeps_the_games() -> None:
    far = cell(ISLAND, 0, 0)
    _, _, names, _ = _named(ISLAND, area=lambda _row, _column: "far_sea")
    assert names.cells[far] == names.areas["far_sea"]
    _, _, ocean, _ = _named(
        ISLAND, area=lambda _row, _column: "pacific_area", ocean=lambda _a: True
    )
    assert ocean.cells[far] == reference("pacific_area")
    assert {english(ocean.cells[far]), render(ocean.cells[far], "korean")} == {"$pacific_area$"}
    assert "pacific_area" not in ocean.areas


def test_an_area_that_is_mostly_a_sea_is_named_for_it_and_for_its_side_of_it() -> None:
    def halves(row: int, column: int) -> str:
        if not (2 <= row <= 7 and 2 <= column <= 13):
            return "outer_area"
        return "west_area" if column < 8 else "east_area"

    _, waters, names, _ = _named(LAGOON, area=halves)
    sea_name = english(names.cells[cell(LAGOON, 5, 5)])
    assert sea_name.endswith(" Sea")
    assert len(waters.bodies) == 1
    west, east = (english(names.areas[area]) for area in ("west_area", "east_area"))
    assert west.endswith(sea_name)
    assert east.endswith(sea_name)
    assert west != east
    assert "Western" in west or "Central" in west
    # Every language tells the halves apart by its own compass words.
    for language in ("russian", "german", "japanese"):
        parts = {render(names.areas[area], language) for area in ("west_area", "east_area")}
        assert len(parts) == 2, language


def test_a_province_takes_the_name_most_of_its_cells_share() -> None:
    _, _, names, where = _named(ISLAND)
    for province, text in names.provinces.items():
        members = [
            number for number in names.cells if f"province_{where[number][0] // 3}" in province
        ]
        counts = [names.cells[number] for number in members]
        assert text in {*counts, names.areas["an_area"]}


def test_names_depend_on_the_seed_and_on_nothing_else() -> None:
    first = _named(LAGOON, seed=1)[2]
    again = _named(LAGOON, seed=1)[2]
    other = _named(LAGOON, seed=2)[2]
    assert first == again
    assert first.cells != other.cells


def test_every_language_has_a_pattern_for_every_kind_with_the_name_in_it() -> None:
    assert {kind.value for kind in Kind} == set(wording.WATERS)
    for language, grammar in wording.LANGUAGES.items():
        for kind in Kind:
            assert "{n}" in grammar.terms[kind.value].pattern, (language, kind)


def test_the_compass_sector_of_an_offset_is_one_of_eight_by_integers() -> None:
    """East, north east, north, ... counter-clockwise; rows grow southwards."""
    offsets = [(0, 10), (-10, 10), (-10, 0), (-10, -10), (0, -10), (10, -10), (10, 0), (10, 10)]
    assert [_sector(row, column) for row, column in offsets] == list(range(8))
    assert _sector(-4, 10) == 0
    assert _sector(-5, 10) == 1
    assert _sector(0, 0) == 0


def test_a_zone_of_impassable_ocean_is_an_ocean_of_its_own_unless_its_area_is_the_games() -> None:
    far = cell(ISLAND, 0, 0)
    world = block_world(ISLAND)
    waters = analyse(world)
    shut = replace(
        waters,
        topography=tuple(
            Topography.OCEAN_WASTELAND if number == far else kind
            for number, kind in enumerate(waters.topography)
        ),
    )
    placed = [
        Placement("province", "an_area", ocean=False)
        if world.classes[number] is CellClass.SEA
        else None
        for number in range(len(world.classes))
    ]
    names = name_waters(world, shut, placed, seed=1)
    assert english(names.cells[far]).endswith(" Ocean")
    assert names.cells[far] != names.areas["an_area"]
    ocean = [
        Placement("province", "pacific_area", ocean=True) if placement else None
        for placement in placed
    ]
    assert name_waters(world, shut, ocean, seed=1).cells[far] == reference("pacific_area")
