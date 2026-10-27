"""Lanes of the open ocean and the impassable water between them."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import pytest

from rnw import lanes as lane_module
from rnw.lanes import (
    COURSE_PERMILLE,
    Course,
    LaneError,
    _sliver_is_route,  # pyright: ignore[reportPrivateUsage]
    plan_lanes,
)
from rnw.seas import Topography, analyse
from tests.block_worlds import block_world, cell

if TYPE_CHECKING:
    from collections.abc import Collection

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# A coast on the left, twelve rows of open sea beside it.
COAST = ["#" + "." * 19 for _ in range(12)]
CURRENT = (9000, 0)


def _setup() -> tuple[NewWorld, Waters, set[int]]:
    world = block_world(COAST)
    waters = analyse(world)
    docks = {cell(COAST, row, 19) for row in range(len(COAST))}
    return world, waters, docks


def _course(row: int, first: int, last: int, permille: int = 800) -> dict[int, Course]:
    return {cell(COAST, row, column): Course(permille, CURRENT) for column in range(first, last)}


def test_the_deep_cells_a_course_ran_over_are_lanes_and_the_rest_is_shut() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    deep = {n for n in waters.sea() if waters.topography[n] is Topography.DEEP_OCEAN}
    docks = {cell(COAST, row, 19) for row in range(len(COAST))}
    lanes = plan_lanes(world, waters, _course(5, 3, 18), set(), docks)
    ran = {cell(COAST, 5, column) for column in range(3, 18)}
    assert ran <= lanes.lanes
    assert lanes.lanes <= deep
    shut = {cell for zone in lanes.zones for cell in zone}
    assert shut == deep - lanes.lanes
    assert lanes.sealed == 0


def test_a_course_that_covered_too_little_of_a_cell_makes_no_lane() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    docks = {cell(COAST, row, 19) for row in range(len(COAST))}
    thin = _course(5, 3, 18, permille=COURSE_PERMILLE - 1)
    lanes = plan_lanes(world, waters, thin, set(), docks)
    assert not any(cell(COAST, 5, column) in lanes.lanes for column in range(3, 18))


def test_a_deep_cell_that_touches_a_lane_of_the_game_continues_it() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    anchor = cell(COAST, 6, 19)
    lanes = plan_lanes(world, waters, {}, {anchor}, {anchor})
    assert anchor in lanes.lanes


def test_water_that_cannot_reach_the_games_is_joined_to_it_by_deep_cells() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    # The coastal water reaches nothing of the game's: only a far corner touches it.
    corner = cell(COAST, 0, 19)
    lanes = plan_lanes(world, waters, {}, set(), {corner})
    assert lanes.linked > 0
    assert corner in lanes.lanes
    assert lanes.sealed == 0
    joined = lanes.lanes
    assert all(waters.topography[n] is Topography.DEEP_OCEAN for n in joined)


def test_the_cheapest_string_keeps_close_to_the_coast() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    docks = {cell(COAST, 0, 19)}
    # Deep water starts two cells from the coast: the string meets the coastal water there.
    lanes = plan_lanes(world, waters, {}, set(), docks)
    assert lanes.linked == len(lanes.lanes)
    assert min(int(waters.hop[n]) for n in lanes.lanes) == 2


def test_no_cell_that_touches_the_games_water_stops_the_export() -> None:
    world = block_world(COAST)
    waters = analyse(world)
    with pytest.raises(LaneError, match="touches the game's water"):
        _ = plan_lanes(world, waters, {}, set(), set())


def test_connected_closed_water_is_one_zone_without_an_arbitrary_size_partition() -> None:
    layout = ["#" + "." * 39 for _ in range(30)]
    world = block_world(layout)
    waters = analyse(world)
    docks = {cell(layout, row, 39) for row in range(30)}
    lanes = plan_lanes(world, waters, {}, set(), docks)
    # Cross-ocean lanes may divide the closed water, but no artificial size cap does.
    assert max(map(len, lanes.zones)) > 48 * 5
    seen: set[int] = set()
    for zone in lanes.zones:
        assert not seen & set(zone)
        seen.update(zone)
    edges = {frozenset(edge) for edge in world.edges}
    for zone in lanes.zones:
        inside = set(zone)
        reached, stack = {zone[0]}, [zone[0]]
        while stack:
            here = stack.pop()
            for other in inside - reached:
                if frozenset((here, other)) in edges:
                    reached.add(other)
                    stack.append(other)
        assert reached == inside


def test_lanes_and_zones_are_the_same_for_the_same_world() -> None:
    world, waters, docks = _setup()
    first = plan_lanes(world, waters, _course(5, 3, 18), set(), docks)
    second = plan_lanes(world, waters, _course(5, 3, 18), set(), docks)
    assert first == second


def test_closed_zones_have_an_interior_in_the_sea_graph() -> None:
    world, waters, docks = _setup()
    planned = plan_lanes(world, waters, _course(5, 3, 18), set(), docks)
    neighbours: dict[int, set[int]] = {cell: set() for cell in waters.sea()}
    for first, second in world.edges:
        if first in neighbours and second in neighbours:
            neighbours[first].add(second)
            neighbours[second].add(first)
    for zone in planned.zones:
        inside = set(zone)
        assert any(len(neighbours[cell] & inside) >= 2 for cell in zone)


def test_designed_crossing_only_opens_where_a_current_can_reach_it() -> None:
    world, waters, docks = _setup()
    route = {cell(COAST, 5, column) for column in range(3, 18)}
    without_source = plan_lanes(world, waters, {}, set(), docks, preferred=route)
    assert not route <= without_source.lanes
    with_source = plan_lanes(world, waters, {}, {cell(COAST, 5, 19)}, docks, preferred=route)
    assert route <= with_source.lanes


def test_a_closed_sea_that_no_deep_water_joins_is_counted_not_joined() -> None:
    layout = [
        "####################",
        "#..................#",
        "#.################.#",
        "#.#00000000000000#.#",
        "#.################.#",
        "#..................#",
        "####################",
    ]
    world = block_world(layout)
    waters = analyse(world)
    corner = cell(layout, 1, 1)
    lanes = plan_lanes(world, waters, {}, set(), {corner})
    assert lanes.sealed >= 1


def test_globally_connected_lanes_also_join_nearby_opposite_coasts() -> None:
    layout = ["#.......#" for _ in range(25)]
    world = block_world(layout)
    waters = analyse(world)
    lanes = plan_lanes(world, waters, {}, set(), {cell(layout, 0, 4)})
    assert lanes.sealed == 0
    assert lanes.shortcuts > 0
    shut = {n for zone in lanes.zones for n in zone}
    links: dict[int, list[int]] = {n: [] for n in waters.sea()}
    for a, b in world.edges:
        if a in links and b in links:
            links[a].append(b)
            links[b].append(a)
    # Independent breadth-first traversal: uniform blocks have equal edge lengths.
    for row in range(25):
        start, end = cell(layout, row, 1), cell(layout, row, 7)
        distance, queue = {start: 0}, deque([start])
        while queue:
            here = queue.popleft()
            for other in links[here]:
                if other not in shut and other not in distance:
                    distance[other] = 1 + distance[here]
                    queue.append(other)
        assert distance[end] <= 2 * 6


def test_every_retained_passable_water_contact_continues_into_open_water() -> None:
    world, waters, docks = _setup()
    lanes = plan_lanes(world, waters, {}, set(), docks)
    assert docks <= lanes.lanes
    assert lanes.shortcuts > 0


def _ocean_ends(world: NewWorld, waters: Waters, lanes: set[int], docks: set[int]) -> set[int]:
    """Independent degree check, including the coastal band as legitimate destinations."""
    sea = set(waters.sea())
    deep = {n for n in sea if waters.topography[n] is Topography.DEEP_OCEAN}
    allowed = sea - (deep - lanes)
    terminals = (sea - deep) | docks
    neighbours: dict[int, set[int]] = {n: set() for n in allowed}
    for first, second in world.edges:
        if first in allowed and second in allowed:
            neighbours[first].add(second)
            neighbours[second].add(first)
    return {
        n for n in lanes - terminals if not neighbours[n] & terminals and len(neighbours[n]) <= 1
    }


@pytest.mark.parametrize("gap", [False, True])
def test_inherited_courses_cross_the_ocean_even_when_both_coasts_already_reach_the_game(
    *, gap: bool
) -> None:
    # Both shores have their own retained-water contact. Global connectivity therefore
    # accepts the two halves of this crossing, even with a closed cell between them.
    layout = ["#" + "." * 19 + "#" for _ in range(15)]
    world = block_world(layout)
    waters = analyse(world)
    docks = {cell(layout, 0, column) for column in (1, 19)}
    row = 7
    course = {
        cell(layout, row, column): Course(800, CURRENT)
        for column in range(3, 18 if gap else 10)
        if column != 10
    }
    planned = plan_lanes(world, waters, course, set(), docks)
    assert not _ocean_ends(world, waters, set(planned.lanes), docks)
    # A gap is joined; an inherited lane ending where an old coast used to be
    # continues ahead to the new shore instead of looping back into its own stem.
    assert {cell(layout, row, column) for column in range(3, 18)} <= planned.lanes
    assert all(waters.topography[n] is Topography.DEEP_OCEAN for n in planned.lanes)
    assert planned.completed > 0


def test_crossings_cannot_leave_a_new_dead_end(monkeypatch: pytest.MonkeyPatch) -> None:
    world, waters, docks = _setup()
    injected: list[int] = []

    def crossing(  # noqa: PLR0913 - matches the planner's crossing callback
        world: NewWorld,
        waters: Waters,
        deep: set[int],
        lanes: set[int],
        *,
        docks: Collection[int],
        sources: Collection[int],
    ) -> int:
        del sources
        links: dict[int, set[int]] = {n: set() for n in waters.sea()}
        for first, second in world.edges:
            if first in links and second in links:
                links[first].add(second)
                links[second].add(first)
        allowed = set(links) - (deep - lanes)
        terminals = (set(links) - deep) | set(docks)
        choices = [
            n
            for n in sorted(deep - lanes)
            if len(links[n] & allowed) == 1 and links[n] & lanes and not links[n] & terminals
        ]
        assert choices
        injected.append(choices[0])
        lanes.add(choices[0])
        return 1

    monkeypatch.setattr(lane_module, "cross_oceans", crossing)
    planned = plan_lanes(world, waters, _course(5, 3, 18), set(), docks)
    assert injected[0] in planned.lanes
    assert not _ocean_ends(world, waters, set(planned.lanes), docks)


def test_a_sliver_opens_only_when_it_does_not_end_in_closed_water() -> None:
    links = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}
    assert not _sliver_is_route([1], links, {0}, set())
    assert _sliver_is_route([1], links, {0}, {0})
    assert _sliver_is_route([1], links, {0, 2}, set())
    assert not _sliver_is_route([1, 2], links, {0}, set())
    assert _sliver_is_route([1, 2], links, {0, 3}, set())


def test_a_lane_that_already_ends_at_coastal_water_needs_no_continuation() -> None:
    world, waters, docks = _setup()
    planned = plan_lanes(world, waters, _course(5, 3, 20), set(), docks)
    assert planned.completed == 0
