"""Course continuations stop at the first existing water, and respect blocked headings."""

# pyright: reportAny=false

from __future__ import annotations

from collections import deque

from rnw.sea_routes import (
    _continuation,  # pyright: ignore[reportPrivateUsage]
    _leaf_block,  # pyright: ignore[reportPrivateUsage]
    _links,  # pyright: ignore[reportPrivateUsage]
    complete_routes,
    cross_oceans,
)
from rnw.seas import Topography, analyse
from tests.block_worlds import block_world, cell


def test_a_forward_destination_cannot_be_reached_by_walking_through_another_terminal() -> None:
    # Forward water 3 is reachable only through the side coast 2. The new route
    # must end at 2, not pretend its continuation still runs through closed water.
    links = {0: [(1, 1)], 1: [(0, 1), (2, 1)], 2: [(1, 1), (3, 1)], 3: [(2, 1)]}
    assert _continuation(links, 0, {1}, {2, 3}, {3}) == [2, 1, 0]


def test_a_lane_turns_towards_reachable_water_when_land_blocks_the_forward_route() -> None:
    links = {0: [(1, 1)], 1: [(0, 1), (2, 1)], 2: [(1, 1)], 3: []}
    assert _continuation(links, 0, {1}, {2, 3}, {3}) == [2, 1, 0]


def test_no_reachable_water_is_reported_instead_of_an_invented_route() -> None:
    assert _continuation({0: [(1, 1)], 1: [(0, 1)], 2: []}, 0, {1}, {2}, {2}) is None


def test_a_wide_loop_at_a_course_end_is_continued_to_the_other_coast() -> None:
    layout = ["#" + "." * 19 + "#" for _ in range(15)]
    world = block_world(layout)
    waters = analyse(world)
    sea = set(waters.sea())
    deep = {n for n in sea if waters.topography[n] is Topography.DEEP_OCEAN}
    lanes = {cell(layout, 6, column) for column in range(3, 7)}
    lanes |= {cell(layout, row, column) for row in (6, 7) for column in (6, 7)}
    before = set(lanes)
    docks: set[int] = set()
    opened = complete_routes(world, waters, deep, lanes, docks)
    assert opened > 0
    assert len(lanes - before) == opened
    terminals = sea - deep
    assert _leaf_block(_links(world, sea), lanes, sea - (deep - lanes), terminals) is None
    assert any(cell(layout, row, 17) in lanes for row in range(15))


def test_a_loop_with_two_terminal_connections_is_not_a_dead_end() -> None:
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1), (3, 5)]
    links: dict[int, list[tuple[int, int]]] = {n: [] for n in range(6)}
    for first, second in edges:
        links[first].append((second, 1))
        links[second].append((first, 1))
    assert _leaf_block(links, {1, 2, 3, 4}, set(links), {0, 5}) is None


def test_cross_ocean_shortcut_joins_distant_continents() -> None:
    # Both coastlines already have navigable water around the bottom of the map, but
    # a crossing near their closest points is much shorter than the perimeter.
    layout = ["#" + "." * 25 + "#" for _ in range(50)]
    world = block_world(layout)
    waters = analyse(world)
    sea = set(waters.sea())
    deep = {n for n in sea if waters.topography[n] is Topography.DEEP_OCEAN}
    lanes = {cell(layout, 49, column) for column in range(2, 25)} & deep
    before = set(lanes)
    assert cross_oceans(world, waters, deep, lanes) > 0
    assert lanes - before <= deep
    # The added crossing is geographically distinct from the perimeter route.
    previous_row = int(world.centroids[next(iter(before))][0])
    assert max(int(world.centroids[n][0]) for n in lanes - before) < previous_row
    allowed = sea - (deep - lanes)
    links = _links(world, allowed)
    for row in (0, 12, 25, 37):
        start, end = cell(layout, row, 1), cell(layout, row, 25)
        distances = {start: 0}
        pending = deque([start])
        while pending:
            here = pending.popleft()
            for other, _ in links[here]:
                if other not in distances:
                    distances[other] = distances[here] + 1
                    pending.append(other)
        assert distances[end] <= 2 * 24


def test_a_crossing_without_a_reachable_current_source_is_not_invented() -> None:
    layout = ["#" + "." * 25 + "#" for _ in range(20)]
    world = block_world(layout)
    waters = analyse(world)
    deep = {n for n in waters.sea() if waters.topography[n] is Topography.DEEP_OCEAN}
    lanes: set[int] = set()
    assert cross_oceans(world, waters, deep, lanes, sources=set()) == 0
    assert not lanes
