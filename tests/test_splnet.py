"""The spline network format: read, write, check and rebuild (synthetic networks)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import struct
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.splnet import (
    POINT_FLAG,
    NewStrip,
    SplineError,
    SplineNetwork,
    parse,
    polyline,
    rebuild,
    route,
    serialize,
    strip_ends,
    strip_id,
)

if TYPE_CHECKING:
    from collections.abc import Callable

EMPTY = SplineNetwork(
    anchors=np.zeros(0, dtype=np.int64),
    anchor_xy=np.zeros((0, 2), dtype=np.float32),
    point_xy=np.zeros((0, 2), dtype=np.float32),
    segments=(),
    strips={},
)
PLACES = {1: (10.5, 10.5), 2: (30.5, 10.5), 3: (30.5, 30.5), 4: (50.5, 30.5)}


def _road(low: int, high: int, *inner: tuple[float, float]) -> NewStrip:
    path = np.array([PLACES[low], *inner, PLACES[high]], dtype=np.float32)
    return NewStrip(low, high, path)


def _network() -> SplineNetwork:
    """Four locations with the roads 1-2, 2-3 and 3-4, bent in the middle."""
    roads = [
        _road(1, 2, (20.0, 12.0)),
        _road(2, 3, (31.0, 20.0), (30.0, 25.0)),
        _road(3, 4, (40.0, 31.0)),
    ]
    return rebuild(EMPTY, {}, PLACES, roads)


def test_a_network_is_written_and_read_back_exactly() -> None:
    """Writing, reading and writing again gives the same bytes and the same network."""
    network = _network()
    data = serialize(network)
    again = parse(data)
    assert serialize(again) == data
    assert again.anchors.tolist() == [1, 2, 3, 4]
    assert again.anchor_xy.tolist() == [list(PLACES[i]) for i in (1, 2, 3, 4)]
    assert again.point_xy.shape == (4, 2)
    assert again.first_point == 5
    assert again.strips == network.strips
    assert again.segments == network.segments


def test_the_numbering_follows_the_engine_layout() -> None:
    """Strips ``higher << 35 | lower << 6``, segments ``n << 8``, points after the anchors."""
    network = _network()
    assert sorted(network.strips) == [strip_id(1, 2), strip_id(2, 3), strip_id(3, 4)]
    assert strip_id(2, 1) == strip_id(1, 2) == (2 << 35) | (1 << 6)
    assert strip_ends(strip_id(7, 3)) == (3, 7)
    assert network.segments[0] == (1, POINT_FLAG + 5, 2)
    assert network.segments[1] == (2, POINT_FLAG + 6, POINT_FLAG + 7, 3)
    data = serialize(network)
    assert data[:10] == struct.pack("<HHHi", 0xEE, 1, 0x0C, 4)
    assert struct.pack("<HHq", 1, 0x29C, 1 << 8) in data[10:]


def test_a_strip_is_walked_from_its_lower_anchor_even_through_a_reversed_segment() -> None:
    """Segments join end to end; one stored backwards is walked backwards."""
    network = SplineNetwork(
        anchors=np.array([1, 2, 3], dtype=np.int64),
        anchor_xy=np.array([(0.5, 0.5), (10.5, 0.5), (20.5, 0.5)], dtype=np.float32),
        point_xy=np.array([(5.0, 1.0), (15.0, 1.0)], dtype=np.float32),
        segments=((1, POINT_FLAG + 4, 2), (3, POINT_FLAG + 5, 2)),
        strips={strip_id(1, 3): (0, 1)},
    )
    assert route(network, strip_id(1, 3)) == [1, POINT_FLAG + 4, 2, POINT_FLAG + 5, 3]
    assert polyline(network, strip_id(1, 3)).tolist() == [
        [0.5, 0.5],
        [5.0, 1.0],
        [10.5, 0.5],
        [15.0, 1.0],
        [20.5, 0.5],
    ]


def _with_segment(network: SplineNetwork, segment: tuple[int, ...]) -> SplineNetwork:
    return replace(network, segments=(segment, *network.segments[1:]))


BROKEN: dict[str, Callable[[SplineNetwork], SplineNetwork]] = {
    "unsorted_anchors": lambda n: replace(n, anchors=n.anchors[::-1]),
    "gap_in_points": lambda n: replace(
        _with_segment(n, (1, POINT_FLAG + 5, 2)), point_xy=n.point_xy[:2]
    ),
    "missing_point": lambda n: _with_segment(n, (1, 99, 2)),
    "short_segment": lambda n: _with_segment(n, (1,)),
    "strip_between_no_anchors": lambda n: replace(n, strips={strip_id(8, 9): (0,)}),
    "strip_does_not_join": lambda n: replace(n, strips={strip_id(1, 4): (0,)}),
    "missing_segment": lambda n: replace(n, strips={strip_id(1, 2): (9,)}),
}


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_a_network_that_breaks_a_rule_is_not_written(case: str) -> None:
    """Each rule of the format is checked, and a network that breaks one fails loudly."""
    with pytest.raises(SplineError):
        _ = serialize(BROKEN[case](_network()))


@pytest.mark.parametrize("case", ["version", "truncated", "trailing"])
def test_bytes_that_are_not_the_known_format_are_refused(case: str) -> None:
    """A format number, a cut file and bytes after the last list are refused."""
    data = serialize(_network())
    if case == "version":
        data = data[:6] + struct.pack("<i", 5) + data[10:]
    if case == "truncated":
        data = data[:-3]
    if case == "trailing":
        data += b"\x00"
    with pytest.raises(SplineError):
        _ = parse(data)


def test_rebuild_drops_what_is_gone_renumbers_the_rest_and_adds_new_roads() -> None:
    """Location 2 is gone, 3 and 4 move down, a new location 4 is joined to the old 4."""
    network = _network()
    mapping = {1: 1, 3: 2, 4: 3}
    added = {4: (60.5, 40.5)}
    road = NewStrip(3, 4, np.array([(50.5, 30.5), (55.0, 36.0), (60.5, 40.5)], dtype=np.float32))
    result = rebuild(network, mapping, added, [road])
    assert result.anchors.tolist() == [1, 2, 3, 4]
    assert result.anchor_xy[1].tolist() == list(PLACES[3])
    assert sorted(result.strips) == [strip_id(2, 3), strip_id(3, 4)]
    assert polyline(result, strip_id(2, 3)).tolist() == polyline(network, strip_id(3, 4)).tolist()
    assert polyline(result, strip_id(3, 4))[1].tolist() == [55.0, 36.0]
    assert result.first_point == 5
    assert len(result.segments) == 2
    assert parse(serialize(result)).strips == result.strips


def test_rebuild_keeps_shared_segments_shared() -> None:
    """Two strips that use one segment still do after the renumbering."""
    network = SplineNetwork(
        anchors=np.array([1, 2, 3], dtype=np.int64),
        anchor_xy=np.array([(0.5, 0.5), (10.5, 0.5), (20.5, 0.5)], dtype=np.float32),
        point_xy=np.array([(5.0, 1.0), (15.0, 1.0)], dtype=np.float32),
        segments=((1, POINT_FLAG + 4, 2), (2, POINT_FLAG + 5, 3)),
        strips={strip_id(1, 2): (0,), strip_id(1, 3): (0, 1)},
    )
    result = rebuild(network, {1: 1, 2: 2, 3: 3}, {}, [])
    assert result.strips == network.strips
    assert len(result.segments) == 2
    assert polyline(result, strip_id(1, 3)).tolist() == polyline(network, strip_id(1, 3)).tolist()


def test_rebuild_numbers_points_after_the_highest_anchor() -> None:
    """Moving the locations up moves the first point with them."""
    result = rebuild(_network(), {1: 1, 2: 2, 3: 3, 4: 10}, {}, [])
    assert result.anchors.tolist() == [1, 2, 3, 10]
    assert result.first_point == 11
    assert result.segments[0][1] == POINT_FLAG + 11
    assert strip_id(3, 10) in result.strips


@pytest.mark.parametrize(
    "case", ["order", "same_index", "repeat", "exists", "anchor_exists", "ends"]
)
def test_rebuild_refuses_what_it_cannot_keep_correct(case: str) -> None:
    """A changed order, a clash, a repeated strip and a strip off its anchors all fail."""
    network = _network()
    mapping = {1: 1, 2: 2, 3: 3, 4: 4}
    anchors: dict[int, tuple[float, float]] = {5: (70.5, 70.5)}
    road = NewStrip(4, 5, np.array([PLACES[4], (60.0, 50.0), (70.5, 70.5)], dtype=np.float32))
    added = [road]
    if case == "order":
        mapping = {1: 2, 2: 1, 3: 3, 4: 4}
    if case == "same_index":
        mapping = {1: 1, 2: 1, 3: 3, 4: 4}
    if case == "repeat":
        added = [road, road]
    if case == "exists":
        added = [_road(1, 2)]
    if case == "anchor_exists":
        anchors = {4: (1.5, 1.5)}
    if case == "ends":
        added = [NewStrip(4, 5, np.array([(0.5, 0.5), (70.5, 70.5)], dtype=np.float32))]
    with pytest.raises(SplineError):
        _ = rebuild(network, mapping, anchors, added)
