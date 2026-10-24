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
    _land_areas,  # pyright: ignore[reportPrivateUsage]
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
    centre_of,
    contact_graph,
    keyed_parts,
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


def test_keyed_parts_follow_key_positions_and_weights() -> None:
    graph = _grid(40, 10)
    members = _land(graph)
    east, west = (50, 350), (50, 50)
    parts = keyed_parts(graph, members, [east, west], [3, 1])
    assert centre_of(graph, parts[0])[1] > centre_of(graph, parts[1])[1]
    assert abs(len(parts[0]) - 3 * len(parts[1])) <= len(members) // 20
    assert all(len(pieces(graph, part)) == 1 for part in parts)


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
        parents={"r": ("r", "s", "america"), "ocean": ("o", "os", "ocean")},
        keys=KeySpace(set()),
    )
    assert anchored == {"ocean"}
    assert [area.name for area in areas] == ["coast"]
    assert sorted(cell for area in areas for part in area.provinces for cell in part) == list(
        range(8)
    )
    _check_pieces(graph, areas, depth=2, exempt=anchored)


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
