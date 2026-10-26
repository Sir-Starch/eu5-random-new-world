"""Course continuations stop at the first existing water, and respect blocked headings."""

from __future__ import annotations

from rnw.sea_routes import _continuation  # pyright: ignore[reportPrivateUsage]


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
