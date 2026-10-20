"""Compact connected hierarchy parts on synthetic contact graphs."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.hierarchy import (
    ContactGraph,
    PartitionError,
    balanced_parts,
    centre_of,
    contact_graph,
    keyed_parts,
    match,
    pieces,
    split,
    split_landmasses,
)

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


def test_anchored_parts_grow_from_their_anchors() -> None:
    graph = _grid(20, 10)
    members = _land(graph)
    anchors = [cell for cell in members if cell % 20 == 0]
    parts, _ = balanced_parts(graph, members, [anchors, [109]], [1, 1], movable=[False, True])
    assert abs(len(parts[0]) - len(parts[1])) <= len(members) // 10
    assert all(set(piece) & set(anchors) for piece in pieces(graph, parts[0]))
    assert 109 in parts[1]


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
