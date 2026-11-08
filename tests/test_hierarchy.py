"""Compact connected hierarchy parts on synthetic contact graphs."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_newworld import (
    IdentityError,
    _Area,  # pyright: ignore[reportPrivateUsage]
    _check_pieces,  # pyright: ignore[reportPrivateUsage]
    _check_shores,  # pyright: ignore[reportPrivateUsage]
    _independent_coasts,  # pyright: ignore[reportPrivateUsage]
    _inland_areas,  # pyright: ignore[reportPrivateUsage]
    _land_areas,  # pyright: ignore[reportPrivateUsage]
    _protect_ocean_boundary,  # pyright: ignore[reportPrivateUsage]
    _reserve,  # pyright: ignore[reportPrivateUsage]
    _sea_areas,  # pyright: ignore[reportPrivateUsage]
    _SeaArea,  # pyright: ignore[reportPrivateUsage]
    _Tally,  # pyright: ignore[reportPrivateUsage]
)
from rnw.eu5_regionkeys import KeyMatcher, Trait, profile
from rnw.hierarchy import (
    ContactGraph,
    PartitionError,
    absorb_small_pieces,
    balanced_parts,
    banded_parts,
    centre_of,
    contact_graph,
    match,
    piece_counts,
    pieces,
    split,
    split_landmasses,
)
from rnw.loc_keys import KeySpace

SPACING = 10


def _grid(width: int, height: int, *, gap_column: int | None = None) -> ContactGraph:
    """Square cells; a ``gap_column`` of water splits the grid into two landmasses."""
    centres = np.array(
        [(row * SPACING, column * SPACING) for row in range(height) for column in range(width)],
        dtype=np.int64,
    )
    edges: list[tuple[int, int]] = []
    for row in range(height):
        for column in range(width):
            cell = row * width + column
            if column + 1 < width:
                edges.append((cell, cell + 1))
            if row + 1 < height:
                edges.append((cell, cell + width))
    keep = [gap_column is None or index % width != gap_column for index in range(width * height)]
    return contact_graph(centres, edges, keep)


def _land(graph: ContactGraph) -> list[int]:
    return [cell for cell, links in enumerate(graph.links) if links]


def test_split_gives_connected_parts_of_about_equal_size() -> None:
    graph = _grid(24, 18)
    members = _land(graph)
    parts = split(graph, members, 12)
    assert sorted(cell for part in parts for cell in part) == members
    assert all(len(pieces(graph, part)) == 1 for part in parts)
    sizes = [len(part) for part in parts]
    assert max(sizes) - min(sizes) <= len(members) // 12 // 3
    assert parts == split(graph, members, 12)


def _irregular_grid() -> ContactGraph:
    """Synthetic contact geometry whose unconstrained Lloyd search shrinks one part to two."""
    points = (
        (7, 8),
        (51, 1),
        (78, 199),
        (55, 117),
        (130, 68),
        (88, 69),
        (134, 113),
        (118, 135),
        (2, 199),
        (41, 3),
        (118, 81),
        (98, 161),
        (115, 159),
        (164, 14),
        (106, 119),
        (13, 106),
        (0, 26),
        (141, 90),
        (48, 67),
        (59, 114),
        (63, 85),
        (159, 46),
        (10, 136),
        (43, 146),
        (176, 31),
        (33, 178),
        (55, 86),
        (166, 193),
        (165, 85),
        (34, 3),
        (58, 136),
        (102, 5),
    )
    grid = _grid(8, 4)
    edges = [
        (first, second)
        for first, links in enumerate(grid.links)
        for second, _ in links
        if first < second
    ]
    return contact_graph(np.array(points, dtype=np.int64), edges, [True] * len(points))


def test_child_capacity_is_reserved_during_partition_search_before_matching() -> None:
    graph = _irregular_grid()
    members = list(range(32))
    needs = (3, 4, 5, 6)
    assert min(map(len, split(graph, members, 4))) == 2
    parts = split(graph, members, 4, minimum=needs)
    assert all(size >= need for size, need in zip(sorted(map(len, parts)), needs, strict=True))
    assert sorted(cell for part in parts for cell in part) == members
    assert split_landmasses(graph, parts) == []
    assert parts == split(graph, list(reversed(members)), 4, minimum=tuple(reversed(needs)))


def test_irregular_regions_keep_every_child_key_without_repairing_matched_boundaries() -> None:
    graph = _irregular_grid()
    tally = _Tally(0)
    trait = Trait("tropical", "hills", 100, coastal=False)
    templates: dict[str, list[Trait]] = {}
    for region, count in enumerate((3, 4, 5, 6)):
        for child in range(count):
            region_key, area = f"region_{region}", f"area_{region}_{child}"
            tally.add(("america", "sub", region_key, area), region * 40, child * 20, 100)
            for name in (region_key, area):
                templates.setdefault(name, []).append(trait)
    physical = KeyMatcher(
        {key: profile(rows) for key, rows in templates.items()}, dict.fromkeys(range(32), trait)
    )
    areas = _land_areas(graph, list(range(32)), tally, 6, KeySpace(set()), physical=physical)
    assert {area.name for area in areas if not area.new} == {
        key for name in tally.children["sub"] for key in tally.children[name]
    }
    _check_pieces(graph, areas, depth=4, exempt=set())
    assert sorted(cell for area in areas for part in area.provinces for cell in part) == list(
        range(32)
    )


@pytest.mark.parametrize("needs", [(1, 1), (0, 1, 1, 1), (10, 10, 10, 10)])
def test_impossible_child_capacity_fails_explicitly(needs: tuple[int, ...]) -> None:
    with pytest.raises(PartitionError, match="child-key minima"):
        _ = split(_irregular_grid(), list(range(32)), 4, minimum=needs)


def test_islands_without_a_source_join_the_nearest_part_whole() -> None:
    graph = _grid(30, 10, gap_column=27)
    members = _land(graph)
    mainland, island = pieces(graph, members)
    assert len(island) < len(mainland) // 6
    parts = split(graph, members, 6)
    holder = [part for part in parts if island[0] in part]
    assert len(holder) == 1
    assert set(island) <= set(holder[0])
    assert split_landmasses(graph, parts) == []


def test_bands_follow_rows_and_weights() -> None:
    graph = _grid(10, 40)
    members = _land(graph)
    north, south = banded_parts(graph, members, [3, 1])
    assert (len(north), len(south)) == (300, 100)
    assert max(int(graph.centres[cell][0]) for cell in north) < min(
        int(graph.centres[cell][0]) for cell in south
    )
    assert all(len(pieces(graph, part)) == 1 for part in (north, south))
    assert banded_parts(graph, list(reversed(members)), [3, 1]) == [north, south]


def test_a_band_crossing_a_landmass_twice_keeps_one_piece_there() -> None:
    """A U open to the north: the northern band holds both arms, so it keeps the larger one
    and the other arm joins the southern band, which it touches."""
    width, height = 10, 10
    graph = _grid(width, height)
    hollow = {row * width + column for row in range(6) for column in range(3, 7)}
    keep = [cell not in hollow for cell in range(width * height)]
    edges = [(first, second) for first, links in enumerate(graph.links) for second, _ in links]
    graph = contact_graph(graph.centres, edges, keep)
    members = _land(graph)
    north, south = banded_parts(graph, members, [1, 1])
    assert split_landmasses(graph, [north, south]) == []
    assert len(pieces(graph, north)) == 1
    assert sorted(north + south) == members
    with pytest.raises(PartitionError, match="Cannot band"):
        _ = banded_parts(graph, members, [1, 0])


def test_region_keys_keep_their_vanilla_layout_against_physical_pull() -> None:
    """Four regions lie in the vanilla quadrants; the generated land's climate is the mirror
    image of vanilla's. Place decides: each key keeps its quadrant (C502)."""
    graph = _grid(40, 40)
    tally = _Tally(0)
    corners = {
        "north_west": (0, 0),
        "north_east": (0, 1),
        "south_west": (1, 0),
        "south_east": (1, 1),
    }
    climate = {
        "north_west": "arctic",
        "north_east": "temperate",
        "south_west": "arid",
        "south_east": "tropical",
    }
    templates: dict[str, list[Trait]] = {}
    for region, (row, column) in corners.items():
        for child in range(4):
            area = f"{region}_{child}"
            tally.add(("america", "sub", region, area), row * 200 + child * 10, column * 200, 100)
            for name in (region, area):
                templates.setdefault(name, []).append(
                    Trait(climate[region], "hills", 100, coastal=False)
                )
    mirror = {(0, 0): "tropical", (0, 1): "arid", (1, 0): "temperate", (1, 1): "arctic"}
    traits = {
        cell: Trait(mirror[cell // 40 // 20, cell % 40 // 20], "hills", 100, coastal=False)
        for cell in range(1600)
    }
    physical = KeyMatcher({key: profile(rows) for key, rows in templates.items()}, traits)
    areas = _land_areas(graph, list(range(1600)), tally, 6, KeySpace(set()), physical=physical)
    _check_pieces(graph, areas, depth=4, exempt=set())
    for region, (row, column) in corners.items():
        cells = [
            cell
            for area in areas
            if area.parents[0] == region
            for part in area.provinces
            for cell in part
        ]
        middle = centre_of(graph, cells)
        assert (middle[0] >= 200, middle[1] >= 200) == (row == 1, column == 1), region


def test_physical_keys_keep_original_parents_and_connected_parts() -> None:
    """Two subcontinents, each with two regions and four areas; no parent can change."""
    graph = _grid(40, 10)
    tally = _Tally(0)
    traits = {
        cell: Trait("arctic" if cell % 40 < 20 else "tropical", "hills", 100, coastal=False)
        for cell in range(400)
    }
    templates: dict[str, list[Trait]] = {}
    parents: dict[str, tuple[str, str, str]] = {}
    for cell in range(400):
        sub = f"sub{cell % 40 // 20}"
        region = f"region{cell % 40 // 10}"
        area = f"area{cell % 40 // 5}"
        tally.add(("america", sub, region, area), cell // 40 * 10, cell % 40 * 10, 100)
        parents[area] = (region, sub, "america")
        for name in (region, area):
            templates.setdefault(name, []).append(traits[399 - cell])
    physical = KeyMatcher({key: profile(rows) for key, rows in templates.items()}, traits)
    areas = _land_areas(graph, list(range(400)), tally, 6, KeySpace(set()), physical=physical)
    assert {area.name for area in areas if not area.new} == set(parents)
    assert all(area.new or area.parents == parents[area.name] for area in areas)
    assert sorted(cell for area in areas for part in area.provinces for cell in part) == list(
        range(400)
    )
    _check_pieces(graph, areas, depth=4, exempt=set())
    assert len(physical.assignments) == 12


def test_a_small_vanilla_region_still_keeps_all_four_area_keys() -> None:
    """The reference's old three-cell Chaco partition must not drop its fourth area."""
    graph = _grid(40, 10)
    tally = _Tally(0)
    trait = Trait("tropical", "hills", 100, coastal=False)
    templates: dict[str, list[Trait]] = {}
    for cell in range(400):
        region = "small" if cell < 4 else "large"
        area = f"{region}_{cell if cell < 4 else (cell - 4) // 99}"
        tally.add(("america", "sub", region, area), cell // 40 * 10, cell % 40 * 10, 100)
        for name in (region, area):
            templates.setdefault(name, []).append(trait)
    physical = KeyMatcher(
        {key: profile(rows) for key, rows in templates.items()}, dict.fromkeys(range(400), trait)
    )
    areas = _land_areas(graph, list(range(400)), tally, 6, KeySpace(set()), physical=physical)
    assert {area.name for area in areas if not area.new} == tally.children[
        "small"
    ] | tally.children["large"]
    assert len([area for area in areas if area.parents[0] == "small"]) >= 4
    _check_pieces(graph, areas, depth=4, exempt=set())


def test_anchored_parts_grow_from_their_anchors() -> None:
    graph = _grid(20, 10)
    members = _land(graph)
    anchors = [cell for cell in members if cell % 20 == 0]
    parts, _ = balanced_parts(graph, members, [anchors, [109]], [1, 1], movable=[False, True])
    assert abs(len(parts[0]) - len(parts[1])) <= len(members) // 10
    assert all(set(piece) & set(anchors) for piece in pieces(graph, parts[0]))
    assert 109 in parts[1]


def test_pinned_sources_keep_their_part_whatever_its_target() -> None:
    """A part that would shrink to nothing keeps the cells it is pinned to."""
    graph = _grid(20, 10)
    members = _land(graph)
    sources = [[0, 1, 20], [199]]
    parts, _ = balanced_parts(
        graph, members, sources, [1, 1000], movable=[False, False], pinned=[True, True]
    )
    assert {0, 1, 20} <= set(parts[0])
    assert 199 in parts[1]
    assert all(len(pieces(graph, part)) == 1 for part in parts)


def test_match_pairs_closest_first_and_runs_out() -> None:
    assert match([(0, 0), (0, 10), (0, 11)], [(0, 12), (0, 1)]) == [1, -1, 0]
    assert match([], [(0, 0)]) == []


def test_split_landmasses_flags_two_pieces_on_one_landmass() -> None:
    graph = _grid(5, 1)
    assert split_landmasses(graph, [[0, 4], [1, 2, 3]]) == [0]
    assert split_landmasses(graph, [[0, 4], [1, 2, 3]], exempt={0}) == []


def test_impossible_split_fails_loudly() -> None:
    graph = _grid(3, 1)
    with pytest.raises(PartitionError):
        _ = split(graph, _land(graph), 4)


def test_small_side_pieces_join_the_part_they_touch_most() -> None:
    graph = _grid(10, 1)
    parts = [[0, 1, 2, 3, 7], [4, 5, 6], [8, 9]]
    moved = absorb_small_pieces(graph, parts, first=1, minimum=2)
    assert moved == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]
    assert absorb_small_pieces(graph, parts, first=1, minimum=1) == [list(p) for p in parts]


def test_piece_counts_reach_the_key_count_on_the_widest_piece() -> None:
    assert piece_counts([[0] * 100, [0] * 10], 50, at_least=1) == [2, 1]
    assert piece_counts([[0] * 100, [0] * 10], 50, at_least=5) == [4, 1]
    assert piece_counts([[0] * 2, [0]], 50, at_least=9) == [2, 1]


def test_a_region_with_too_little_shore_takes_the_nearest_free_water() -> None:
    graph = _grid(10, 1)
    shores = {"a": [0], "b": [9]}
    reserved = _reserve(graph, shores, {"a": 3, "b": 1}, taken={5})
    assert reserved == {"a": [0, 1, 2], "b": [9]}
    assert shores == {"a": [0], "b": [9]}


def test_reserved_water_stops_at_water_that_belongs_to_others() -> None:
    graph = _grid(10, 1)
    held = _reserve(graph, {"a": [0], "b": [9]}, {"a": 4, "b": 4}, taken={2})
    assert held == {"a": [0, 1], "b": [6, 7, 8, 9]}
    assert _reserve(graph, {"a": [0]}, {"a": 1}, taken=set()) == {"a": [0]}


def test_ocean_with_only_a_vanilla_remainder_needs_no_empty_generated_area() -> None:
    """Seed 210: the coastal region takes all water even at the ocean's two anchors."""
    graph = _grid(4, 2)
    seas = [
        _SeaArea("coast", "r", coastal=True, replaced=100, centre=(0, 0), remaining=frozenset()),
        _SeaArea(
            "ocean", "o", coastal=False, replaced=1, centre=(50, 50), remaining=frozenset({99})
        ),
    ]
    areas, anchored = _sea_areas(
        graph,
        list(range(8)),
        seas,
        {(99, 6), (99, 7)},
        coasts={"r": [0, 1, 2, 3]},
        parents={
            "r": ("r", "s", "america"),
            "ocean": ("o", "os", "atlantic_ocean_continent"),
        },
        keys=KeySpace(set()),
    )
    assert anchored == {"ocean"}
    assert [area.name for area in areas] == ["coast"]
    assert sorted(cell for area in areas for part in area.provinces for cell in part) == list(
        range(8)
    )
    _check_pieces(graph, areas, depth=2, exempt=anchored)


def test_inland_seas_get_separate_connected_areas_of_their_dominant_shore() -> None:
    graph = _grid(8, 2, gap_column=4)
    basins = ((0, 1, 2, 3, 8, 9, 10, 11), (5, 6, 7, 13, 14, 15))
    areas = _inland_areas(
        graph,
        basins,
        {"north": [0, 1, 2, 5], "south": [3, 6, 7]},
        {"north": ("north", "n", "america"), "south": ("south", "s", "america")},
        KeySpace(set()),
    )
    assert [area.parents[0] for area in areas] == ["north", "south"]
    assert all(area.new and area.name.startswith("rnw_sea_area_") for area in areas)
    assert [sorted(cell for province in area.provinces for cell in province) for area in areas] == [
        list(basin) for basin in basins
    ]
    _check_pieces(graph, areas, depth=2, exempt=set())
    _check_shores(graph, areas, {"north": [0, 1, 2, 5], "south": [3, 6, 7]})


def test_passable_old_world_sea_gets_connected_ocean_hierarchy() -> None:
    graph = _grid(8, 2)
    sources = [[4]]
    protected = _protect_ocean_boundary(graph, sources, {0, 8}, {7, 15})
    assert protected == {0}
    assert {4, 7, 15} <= set(sources[0])
    assert len(pieces(graph, sources[0])) == 1
    crossing = [[4]]
    assert _protect_ocean_boundary(graph, crossing, {5, 6, 7}, {7}) == {0}
    assert 7 in crossing[0]


def test_coastal_seas_cannot_take_the_old_world_boundary() -> None:
    graph = _grid(8, 2)
    seas = [
        _SeaArea("coast", "r", coastal=True, replaced=100, centre=(0, 0), remaining=frozenset()),
        _SeaArea("ocean", "o", coastal=False, replaced=1, centre=(0, 40), remaining=frozenset()),
        _SeaArea(
            "greenland",
            "western_europe",
            coastal=False,
            replaced=0,
            centre=(0, 70),
            remaining=frozenset({99}),
        ),
    ]
    areas, _ = _sea_areas(
        graph,
        list(range(16)),
        seas,
        {(99, 7)},
        coasts={"r": [0, 8]},
        parents={
            "r": ("r", "north_america", "america"),
            "ocean": ("o", "o", "atlantic_ocean_continent"),
            "greenland": ("western_europe", "western_europe", "europe"),
        },
        keys=KeySpace(set()),
        boundary={7, 15},
    )
    assigned = {cell: area.parents[2] for area in areas for part in area.provinces for cell in part}
    assert assigned[7] == assigned[15] == "atlantic_ocean_continent"
    assert "greenland" not in {area.name for area in areas}


def test_boundary_only_region_has_no_independent_coast() -> None:
    coasts = _independent_coasts({"boundary_only": [7, 15], "independent": [2, 7]}, {7, 15})
    assert coasts == {"independent": [2]}


def test_boundary_only_shore_stays_in_the_protected_ocean_hierarchy() -> None:
    graph = _grid(8, 2)
    seas = [
        _SeaArea("coast", "r", coastal=True, replaced=100, centre=(0, 0), remaining=frozenset()),
        _SeaArea("ocean", "o", coastal=False, replaced=1, centre=(0, 40), remaining=frozenset()),
        _SeaArea(
            "greenland",
            "western_europe",
            coastal=False,
            replaced=0,
            centre=(0, 70),
            remaining=frozenset({99}),
        ),
    ]
    areas, _ = _sea_areas(
        graph,
        list(range(16)),
        seas,
        {(99, 7), (99, 15)},
        coasts={},
        parents={
            "r": ("r", "north_america", "america"),
            "ocean": ("o", "o", "atlantic_ocean_continent"),
            "greenland": ("western_europe", "western_europe", "europe"),
        },
        keys=KeySpace(set()),
        boundary={7, 15},
    )
    assigned = {cell: area.parents[2] for area in areas for part in area.provinces for cell in part}
    assert assigned[7] == assigned[15] == "atlantic_ocean_continent"
    assert sorted(assigned) == list(range(16))
    assert "greenland" not in {area.name for area in areas}


@pytest.mark.parametrize("provinces", [[], [[]], [[0], []]])
def test_empty_generated_area_or_province_fails_with_identity_error(
    provinces: list[list[int]],
) -> None:
    with pytest.raises(IdentityError, match="area empty has an empty province or no provinces"):
        _check_pieces(
            _grid(2, 1),
            [_Area("empty", ("r", "s", "c"), provinces, new=False)],
            depth=2,
            exempt=set(),
        )
