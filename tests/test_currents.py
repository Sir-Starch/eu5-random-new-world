"""Currents for generated deep water: clear directed courses that continue the game's, or none."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math

import pytest

from rnw.currents import (
    BRIDGE,
    MIN_BRANCH,
    MIN_COURSE,
    MIN_OPEN,
    CurrentError,
    Flow,
    check_courses,
    flow,
)
from tests.block_worlds import block_world, cell

OPEN_SEA = ["." * 20 for _ in range(10)]


def _row(row: int, first: int, last: int) -> list[int]:
    """The cells of a straight lane along ``row`` from column ``first`` to ``last``."""
    return [cell(OPEN_SEA, row, column) for column in range(first, last + 1)]


def _east(vector: tuple[int, int]) -> bool:
    return vector[0] > 0 and abs(vector[1]) <= abs(vector[0]) // 5


def test_a_lane_that_continues_a_current_of_the_game_flows_along_itself_at_its_strength() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {lane[0]: [(9000, 0)]})
    assert set(result.flows) == set(lane)
    assert not result.dropped
    for x, y in result.flows.values():
        assert abs(math.hypot(x, y) - 9000) < 2
        assert x > 8900
        assert abs(y) < 300


def test_the_same_lane_flows_the_other_way_when_the_game_s_current_leaves_it() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {lane[0]: [(-9000, 0)]})
    assert set(result.flows) == set(lane)
    assert all(vector[0] < -8900 for vector in result.flows.values())


def test_the_strength_is_the_mean_of_the_game_s_currents() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    docks = {lane[0]: [(8000, 0)], cell(OPEN_SEA, 0, 0): [(10000, 0)]}
    result = flow(world, lane, docks)
    assert result.flows
    assert all(abs(math.hypot(*vector) - 9000) <= 2 for vector in result.flows.values())


def test_a_lane_that_no_current_of_the_game_touches_has_no_current() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {})
    assert result == Flow({}, frozenset(lane))
    assert flow(world, [], {lane[0]: [(9000, 0)]}) == Flow({}, frozenset())


def test_a_current_that_crosses_a_lane_sideways_gives_it_no_direction() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {lane[0]: [(0, 9000)]})
    assert not result.flows
    assert result.dropped == frozenset(lane)


def test_a_stub_is_ordinary_sea_even_where_a_current_touches_it() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 2 + MIN_COURSE - 2)
    result = flow(world, lane, {lane[0]: [(9000, 0)]})
    assert not result.flows
    assert result.dropped == frozenset(lane)


def test_a_short_piece_that_joins_two_currents_of_the_game_is_a_course() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 2 + BRIDGE)
    result = flow(world, lane, {lane[0]: [(9000, 0)], lane[-1]: [(9000, 0)]})
    assert set(result.flows) == set(lane)
    assert all(_east(vector) for vector in result.flows.values())


def test_one_current_of_the_game_at_each_end_the_course_follows_one_and_drops_the_other() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {lane[0]: [(9000, 0)], lane[-1]: [(-9000, 0)]})
    check_courses(world, result.flows)
    assert result.flows
    assert len({vector[0] > 0 for vector in result.flows.values()}) == 1
    assert lane[0] in result.flows or lane[-1] in result.flows
    assert lane[0] in result.dropped or lane[-1] in result.dropped


def test_well_supported_currents_that_meet_head_on_are_two_courses_and_an_ordinary_cell() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    sources = {lane[0]: [(9000, 0)] * 3, lane[-1]: [(-9000, 0)] * 3}
    result = flow(world, lane, sources)
    check_courses(world, result.flows)
    (middle,) = result.dropped
    index = lane.index(middle)
    assert all(_east(result.flows[c]) for c in lane[:index])
    assert all(result.flows[c][0] < 0 for c in lane[index + 1 :])


def test_a_current_of_the_game_that_opposes_a_cell_does_not_split_a_well_supported_course() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    sources = {lane[0]: [(9000, 0)] * 3, lane[10]: [(-9000, 0)]}
    result = flow(world, lane, sources)
    check_courses(world, result.flows)
    assert result.flows
    assert all(vector[0] > 0 for vector in result.flows.values())
    assert lane[10] in result.dropped


def test_a_short_side_branch_is_dropped_and_the_course_stays() -> None:
    layout = [*OPEN_SEA]
    world = block_world(layout)
    lane = _row(5, 2, 17)
    branch = [cell(layout, row, 9) for row in range(5 - (MIN_BRANCH - 1), 5)]
    result = flow(world, [*lane, *branch], {lane[0]: [(9000, 0)]})
    assert set(branch) <= result.dropped
    assert set(lane) - result.dropped
    assert all(_east(result.flows[c]) for c in result.flows)


def test_a_long_side_branch_carries_the_current_away_from_the_course() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    branch = [cell(OPEN_SEA, row, 9) for row in range(5 - MIN_BRANCH, 5)]
    result = flow(world, [*lane, *branch], {lane[0]: [(9000, 0)]})
    assert set(branch) <= set(result.flows)
    assert all(result.flows[c][1] > 0 for c in branch)


def test_a_lane_two_cells_wide_becomes_one_clear_course() -> None:
    world = block_world(OPEN_SEA)
    lane = [*_row(4, 2, 17), *_row(5, 2, 17)]
    result = flow(world, lane, {_row(5, 2, 2)[0]: [(9000, 0)]})
    assert len(result.flows) >= 16
    check_courses(world, result.flows)
    assert all(vector[0] > 0 for vector in result.flows.values())
    assert sum(_east(vector) for vector in result.flows.values()) >= 12


def test_a_bent_lane_is_followed_round_the_bend() -> None:
    world = block_world(OPEN_SEA)
    along = _row(2, 2, 12)
    down = [cell(OPEN_SEA, row, 12) for row in range(3, 9)]
    result = flow(world, [*along, *down], {along[0]: [(9000, 0)]})
    assert set(result.flows) == {*along, *down}
    assert _east(result.flows[along[3]])
    assert result.flows[down[3]][1] < -6000
    assert abs(result.flows[down[3]][0]) < 3000


def test_the_courses_are_the_same_every_time() -> None:
    world = block_world(OPEN_SEA)
    lane = [*_row(4, 2, 17), *_row(5, 2, 17)]
    sources = {lane[0]: [(9000, 1000)], lane[-1]: [(-9000, 0)]}
    assert flow(world, lane, sources) == flow(world, lane, sources)


def test_two_neighbours_driven_into_each_other_are_refused() -> None:
    world = block_world(OPEN_SEA)
    first, second = cell(OPEN_SEA, 5, 5), cell(OPEN_SEA, 5, 6)
    with pytest.raises(CurrentError, match="head-on"):
        check_courses(world, {first: (9000, 0), second: (-9000, 0)})
    check_courses(world, {first: (9000, 0), second: (9000, 0)})
    check_courses(world, {first: (-9000, 0), second: (9000, 0)})


def _over(
    cells: list[int], vector: tuple[int, int], permille: int = 1000
) -> dict[int, tuple[tuple[int, int], int]]:
    return dict.fromkeys(cells, (vector, permille))


def test_an_old_course_directs_the_course_that_a_dock_anchors() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {lane[0]: [(0, 9000)]}, _over(lane, (-9000, 0)))
    assert set(result.flows) == set(lane)  # open water: the old lane's direction is the field
    assert all(vector[0] < 0 for vector in result.flows.values())
    result = flow(world, lane, {lane[-1]: [(-9000, 0)]}, _over(lane, (-9000, 0)))
    assert set(result.flows) == set(lane)
    assert all(vector[0] < 0 for vector in result.flows.values())


def test_a_crossing_of_open_water_follows_the_direction_of_the_gyres() -> None:
    """No zone of the game touches the lane: the old lane that ran over it gives its direction."""
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    for east in (9000, -9000):
        result = flow(world, lane, {cell(OPEN_SEA, 0, 0): [(east, 0)]}, _over(lane, (east, 0)))
        assert set(result.flows) == set(lane)
        assert all(vector[0] * east > 0 for vector in result.flows.values())
        check_courses(world, result.flows)


def test_a_crossing_that_lies_across_the_gyres_has_no_current() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {cell(OPEN_SEA, 0, 0): [(0, 9000)]}, _over(lane, (0, 9000)))
    assert not result.flows
    assert result.dropped == frozenset(lane)


def test_a_short_crossing_of_open_water_is_not_a_current() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 2 + MIN_OPEN - 2)
    result = flow(world, lane, {cell(OPEN_SEA, 0, 0): [(9000, 0)]}, _over(lane, (9000, 0)))
    assert not result.flows
    lane = _row(5, 2, 2 + MIN_OPEN - 1)
    result = flow(world, lane, {cell(OPEN_SEA, 0, 0): [(9000, 0)]}, _over(lane, (9000, 0)))
    assert set(result.flows) == set(lane)


def test_open_water_far_from_every_source_takes_the_zonal_current_of_its_latitude() -> None:
    layout = ["." * 60 for _ in range(10)]
    world = block_world(layout)
    lane = [cell(layout, 5, column) for column in range(40, 56)]
    near = [cell(layout, 5, column) for column in range(3)]
    sources = {c: [(9000, 0)] for c in near}
    result = flow(world, lane, sources)
    assert set(result.flows) == set(lane)
    assert all(vector[0] > 0 for vector in result.flows.values())
    other = [cell(layout, 9, column) for column in range(3)]
    assert not flow(world, lane, {c: [(9000, 0)] for c in other}).flows


def test_a_lane_that_an_old_course_barely_touched_gives_no_direction() -> None:
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    result = flow(world, lane, {cell(OPEN_SEA, 0, 0): [(9000, 0)]}, _over(lane, (9000, 0), 100))
    assert not result.flows


def test_a_crossing_runs_through_the_shallow_strips_between_its_deep_ones() -> None:
    """The line is prepared along its whole length; only the deep cells can carry the arrow."""
    world = block_world(OPEN_SEA)
    full = _row(5, 2, 10)
    shallow = {full[3], full[4], full[5]}
    lane = [c for c in full if c not in shallow]
    docks = {cell(OPEN_SEA, 0, 0): [(9000, 0)]}
    courses = _over(full, (9000, 0))
    assert not flow(world, lane, docks, courses).flows  # two pieces of three cells
    result = flow(world, lane, docks, courses, connectors=shallow)
    assert set(result.flows) == set(lane)
    assert not shallow & set(result.flows)
    assert all(_east(vector) for vector in result.flows.values())


def test_a_wide_stretch_of_lane_carries_no_arrows() -> None:
    layout = ["." * 14 for _ in range(14)]
    world = block_world(layout)
    sea = [cell(layout, row, column) for row in range(14) for column in range(14)]
    docks = {cell(layout, 7, 0): [(9000, 0)]}
    assert not flow(world, sea, docks, _over(sea, (9000, 0))).flows


def test_the_straight_end_of_a_course_beyond_a_small_twig_keeps_its_current() -> None:
    """A twig at a junction near the end must not eat the end of the course as a short branch."""
    world = block_world(OPEN_SEA)
    lane = _row(5, 2, 17)
    twig = [cell(OPEN_SEA, 4, 15)]
    result = flow(world, [*lane, *twig], {lane[0]: [(9000, 0)]})
    assert set(lane[-3:]) <= set(result.flows)
    assert not set(twig) & set(result.flows)
