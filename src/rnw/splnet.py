"""The spline network of EU5's map: ``in_game/gfx/map/spline_network/spline_network.splnet``.

NOT GAME VALIDATED. The game draws and routes its roads along strips between road anchors and logs
``Could not find spline network strip of type 0 between anchors a and b`` for every road between
two locations that have none, over and over [V-GAME owner C161]. Vanilla bakes the strips of every
land-land contact (50,580 of 50,580 on 1.4.3) and of all 1,646 road pairs of the 1337 setup, for the
vanilla locations only [V-LOCAL C162].

The file is the engine's tagged binary (little endian; ``key = value`` is a u16 key, a u16 ``1``
and the value, a block opens with ``3`` and closes with ``4``, values carry a u16 type: ``0x0c``
i32, ``0x0d`` f32, ``0x14`` u32, ``0x29c`` i64). It holds, in this order:

* ``0xee`` = 4, ``0x45a`` = { points, segments, strips } as i32 counts;
* ``0x5f4``: points, each ``{ 0x0b = u32 id, 0x4c = { f32 x, f32 y } }``. An **anchor** has the
  index of its location in the order of ``definitions.txt`` counted from 1, the other points the id
  ``0x10000000 + index`` with the indexes running on from the highest anchor, one after the other.
  The position is in map pixels, x from the left and y from the bottom (the locator's ``z``);
* ``0x5f5``: segments, each ``{ 0x0b = i64 id, 0x5f7 = { u32 point ids... } }`` with the id
  ``n << 8`` for the n-th segment, a polyline from point to point;
* ``0x5f6``: strips, each ``{ 0x0b = i64 id, 0x5f5 = { i64 segment ids... } }`` with the id
  ``higher location << 35 | lower location << 6``: the road between two touching locations, as the
  segments that join the lower location's anchor to the higher one's (a segment may be walked
  backwards, and vanilla shares segments between strips).

Every list is sorted by id. ``parse`` checks all of this and ``serialize`` writes it: the engine's
own reader is not available, so what is not checked here would be a guess. Vanilla's file is read
and written back byte for byte (``tests/test_local_install.py``).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from numpy.typing import NDArray

POINT_FLAG: Final[int] = 0x10000000
MIN_POINTS: Final[int] = 2
# Vanilla's segments have 6.8 points on average and 6 at the median, 88 at most [V-EXEC C162].
SEGMENT_POINTS: Final[int] = 6
SEGMENT_SHIFT: Final[int] = 8
STRIP_HIGH_SHIFT: Final[int] = 35
STRIP_LOW_SHIFT: Final[int] = 6
STRIP_LOW_MASK: Final[int] = (1 << STRIP_HIGH_SHIFT) - 1
FORMAT_VERSION: Final[int] = 4
KEY_VERSION: Final[int] = 0xEE
KEY_COUNTS: Final[int] = 0x45A
KEY_POINTS: Final[int] = 0x5F4
KEY_SEGMENTS: Final[int] = 0x5F5
KEY_STRIPS: Final[int] = 0x5F6
KEY_ID: Final[int] = 0x0B
KEY_POSITION: Final[int] = 0x4C
KEY_POINT_IDS: Final[int] = 0x5F7
KEY_SEGMENT_IDS: Final[int] = 0x5F5
EQUALS: Final[int] = 1
OPEN: Final[int] = 3
CLOSE: Final[int] = 4
I32: Final[int] = 0x0C
F32: Final[int] = 0x0D
U32: Final[int] = 0x14
I64: Final[int] = 0x29C
# A point item is fixed, { id = u32 position = { f32 f32 } } in 34 bytes, its u16 tokens constant.
POINT_ITEM: Final[np.dtype[np.void]] = np.dtype(
    [
        ("open", "<u2"),
        ("key", "<u2"),
        ("eq", "<u2"),
        ("type", "<u2"),
        ("id", "<u4"),
        ("pos_key", "<u2"),
        ("pos_eq", "<u2"),
        ("pos_open", "<u2"),
        ("x_type", "<u2"),
        ("x", "<f4"),
        ("y_type", "<u2"),
        ("y", "<f4"),
        ("pos_close", "<u2"),
        ("close", "<u2"),
    ]
)
POINT_TOKENS: Final[dict[str, int]] = {
    "open": OPEN,
    "key": KEY_ID,
    "eq": EQUALS,
    "type": U32,
    "pos_key": KEY_POSITION,
    "pos_eq": EQUALS,
    "pos_open": OPEN,
    "x_type": F32,
    "y_type": F32,
    "pos_close": CLOSE,
    "close": CLOSE,
}


class SplineError(ValueError):
    """A spline network that is not the one this module knows, or that cannot be built."""


@dataclass(frozen=True, slots=True, eq=False)
class SplineNetwork:
    """Anchors, the points between them, segments and strips of one map.

    ``anchors`` are location indexes in ascending order with their positions; ``point_xy`` are the
    other points in id order (point ``j`` is ``POINT_FLAG + first_point + j``); a segment is the ids
    of its points and a strip lists the indexes of its segments.
    """

    anchors: NDArray[np.int64]
    anchor_xy: NDArray[np.float32]
    point_xy: NDArray[np.float32]
    segments: tuple[tuple[int, ...], ...]
    strips: dict[int, tuple[int, ...]]

    @property
    def first_point(self) -> int:
        """Index of the first point that is no anchor: one past the highest anchor."""
        return int(self.anchors[-1]) + 1 if self.anchors.size else 1


def strip_id(first: int, second: int) -> int:
    """Id of the strip between two locations, given by their indexes in either order."""
    low, high = sorted((first, second))
    return (high << STRIP_HIGH_SHIFT) | (low << STRIP_LOW_SHIFT)


def strip_ends(strip: int) -> tuple[int, int]:
    """The (lower, higher) location indexes of a strip id."""
    return (strip & STRIP_LOW_MASK) >> STRIP_LOW_SHIFT, strip >> STRIP_HIGH_SHIFT


class _Reader:
    """A cursor over the bytes of a spline network."""

    __slots__: tuple[str, ...] = ("data", "offset")

    def __init__(self, data: bytes) -> None:
        self.data: bytes = data
        self.offset: int = 0

    def number(self, fmt: str) -> int:
        try:
            (value,) = struct.unpack_from(fmt, self.data, self.offset)
        except struct.error as error:
            message = f"Spline network: truncated at byte {self.offset}"
            raise SplineError(message) from error
        self.offset += struct.calcsize(fmt)
        return int(value)

    def peek(self) -> int:
        try:
            return int(struct.unpack_from("<H", self.data, self.offset)[0])
        except struct.error as error:
            message = f"Spline network: truncated at byte {self.offset}"
            raise SplineError(message) from error

    def expect(self, *tokens: int) -> None:
        for token in tokens:
            found = self.number("<H")
            if found != token:
                where = self.offset - 2
                message = f"Spline network: expected {token:#x}, found {found:#x} at byte {where}"
                raise SplineError(message)

    def start(self, key: int) -> None:
        self.expect(key, EQUALS, OPEN)


def parse(data: bytes) -> SplineNetwork:
    """Read a spline network and check every rule of the format."""
    reader = _Reader(data)
    reader.expect(KEY_VERSION, EQUALS, I32)
    version = reader.number("<i")
    if version != FORMAT_VERSION:
        message = f"Spline network: format {version}, not {FORMAT_VERSION}"
        raise SplineError(message)
    reader.start(KEY_COUNTS)
    counts: list[int] = []
    for _ in range(3):
        reader.expect(I32)
        counts.append(reader.number("<i"))
    reader.expect(CLOSE)
    points, segments, strips = counts
    reader.start(KEY_POINTS)
    anchors, anchor_xy, point_xy = _points(reader, points)
    reader.expect(CLOSE)
    reader.start(KEY_SEGMENTS)
    segment_list = [_segment(reader, number) for number in range(segments)]
    reader.expect(CLOSE)
    reader.start(KEY_STRIPS)
    strip_map = _strips(reader, strips, segments)
    reader.expect(CLOSE)
    if reader.offset != len(data):
        message = f"Spline network: {len(data) - reader.offset} bytes follow the last list"
        raise SplineError(message)
    network = SplineNetwork(anchors, anchor_xy, point_xy, tuple(segment_list), strip_map)
    check(network)
    return network


def _points(
    reader: _Reader, count: int
) -> tuple[NDArray[np.int64], NDArray[np.float32], NDArray[np.float32]]:
    end = reader.offset + count * POINT_ITEM.itemsize
    if end > len(reader.data):
        message = "Spline network: truncated in the points"
        raise SplineError(message)
    block = np.frombuffer(reader.data, dtype=POINT_ITEM, count=count, offset=reader.offset)
    reader.offset = end
    for name, token in POINT_TOKENS.items():
        if np.any(block[name] != token):
            message = "Spline network: a point is not { id = u32 position = { f32 f32 } }"
            raise SplineError(message)
    ids = block["id"].astype(np.int64)
    if np.any(np.diff(ids) <= 0):
        message = "Spline network: the points are not sorted by unique id"
        raise SplineError(message)
    xy = np.stack([block["x"], block["y"]], axis=1).astype(np.float32)
    anchored = ids < POINT_FLAG
    return ids[anchored], xy[anchored], xy[~anchored]


def _segment(reader: _Reader, number: int) -> tuple[int, ...]:
    reader.expect(OPEN, KEY_ID, EQUALS, I64)
    ident = reader.number("<q")
    if ident != number << SEGMENT_SHIFT:
        message = f"Spline network: segment {number} has the id {ident}"
        raise SplineError(message)
    reader.start(KEY_POINT_IDS)
    members: list[int] = []
    while reader.peek() == U32:
        reader.expect(U32)
        members.append(reader.number("<I"))
    reader.expect(CLOSE, CLOSE)
    return tuple(members)


def _strips(reader: _Reader, count: int, segments: int) -> dict[int, tuple[int, ...]]:
    found: dict[int, tuple[int, ...]] = {}
    previous = -1
    for _ in range(count):
        reader.expect(OPEN, KEY_ID, EQUALS, I64)
        ident = reader.number("<q")
        if ident <= previous:
            message = "Spline network: the strips are not sorted by unique id"
            raise SplineError(message)
        previous = ident
        reader.start(KEY_SEGMENT_IDS)
        refs: list[int] = []
        while reader.peek() == I64:
            reader.expect(I64)
            ref = reader.number("<q")
            if ref % (1 << SEGMENT_SHIFT) or not 0 <= ref >> SEGMENT_SHIFT < segments:
                message = f"Spline network: a strip names the segment {ref}, which does not exist"
                raise SplineError(message)
            refs.append(ref >> SEGMENT_SHIFT)
        reader.expect(CLOSE, CLOSE)
        found[ident] = tuple(refs)
    return found


def check(network: SplineNetwork) -> None:
    """Fail unless the numbering holds, references resolve and every strip joins its anchors."""
    anchors = network.anchors
    if anchors.size and (
        anchors[0] < 1 or np.any(np.diff(anchors) <= 0) or anchors[-1] >= POINT_FLAG
    ):
        message = "Spline network: the anchors are not unique indexes in ascending order"
        raise SplineError(message)
    if len(network.anchor_xy) != len(anchors):
        message = "Spline network: an anchor lacks its position"
        raise SplineError(message)
    known = {int(a) for a in anchors.tolist()}
    last = network.first_point + len(network.point_xy)
    for number, members in enumerate(network.segments):
        if len(members) < MIN_POINTS:
            message = f"Spline network: segment {number} has {len(members)} points"
            raise SplineError(message)
        for member in members:
            index = member - POINT_FLAG
            exists = member in known if member < POINT_FLAG else network.first_point <= index < last
            if not exists:
                message = f"Spline network: segment {number} names a point {member} that is absent"
                raise SplineError(message)
    for ident, refs in network.strips.items():
        low, high = strip_ends(ident)
        if not low < high or low not in known or high not in known or not refs:
            message = f"Spline network: strip {ident} does not join two anchors"
            raise SplineError(message)
        if any(not 0 <= ref < len(network.segments) for ref in refs):
            message = f"Spline network: strip {ident} names a segment that does not exist"
            raise SplineError(message)
        _ = route(network, ident)


def route(network: SplineNetwork, ident: int) -> list[int]:
    """The point ids of a strip from its lower anchor to its higher one.

    Segments are joined end to end by their end points and a segment may be walked backwards.
    """
    low, high = strip_ends(ident)
    here = low
    path = [low]
    for ref in network.strips[ident]:
        members = network.segments[ref]
        if members[0] == here:
            path += members[1:]
            here = members[-1]
        elif members[-1] == here:
            path += members[-2::-1]
            here = members[0]
        else:
            message = f"Spline network: strip {ident} does not join up at segment {ref}"
            raise SplineError(message)
    if here != high:
        message = f"Spline network: strip {ident} ends at {here}, not at its anchor {high}"
        raise SplineError(message)
    return path


def position(network: SplineNetwork, point: int) -> tuple[float, float]:
    """The (x, y) of a point id."""
    if point < POINT_FLAG:
        row = int(np.searchsorted(network.anchors, point))
        return float(network.anchor_xy[row, 0]), float(network.anchor_xy[row, 1])
    row = point - POINT_FLAG - network.first_point
    return float(network.point_xy[row, 0]), float(network.point_xy[row, 1])


def polyline(network: SplineNetwork, ident: int) -> NDArray[np.float32]:
    """The positions of a strip from its lower anchor to its higher one."""
    return np.array([position(network, point) for point in route(network, ident)], dtype=np.float32)


def serialize(network: SplineNetwork) -> bytes:
    """Write a spline network in the engine's format; ``parse`` reads back what this writes."""
    check(network)
    count = len(network.anchors) + len(network.point_xy)
    ids = np.concatenate(
        [
            network.anchors,
            POINT_FLAG + network.first_point + np.arange(len(network.point_xy), dtype=np.int64),
        ]
    )
    block = np.zeros(count, dtype=POINT_ITEM)
    for name, token in POINT_TOKENS.items():
        block[name] = token
    block["id"] = ids
    xy = np.concatenate([network.anchor_xy, network.point_xy])
    block["x"], block["y"] = xy[:, 0], xy[:, 1]
    out = [
        struct.pack("<HHHi", KEY_VERSION, EQUALS, I32, FORMAT_VERSION),
        struct.pack("<HHH", KEY_COUNTS, EQUALS, OPEN),
        *(
            struct.pack("<Hi", I32, size)
            for size in (count, len(network.segments), len(network.strips))
        ),
        struct.pack("<HHHH", CLOSE, KEY_POINTS, EQUALS, OPEN),
        block.tobytes(),
        struct.pack("<HHHH", CLOSE, KEY_SEGMENTS, EQUALS, OPEN),
    ]
    for number, members in enumerate(network.segments):
        out.append(
            struct.pack(
                "<HHHHqHHH",
                OPEN,
                KEY_ID,
                EQUALS,
                I64,
                number << SEGMENT_SHIFT,
                KEY_POINT_IDS,
                EQUALS,
                OPEN,
            )
        )
        out.append(b"".join(struct.pack("<HI", U32, member) for member in members))
        out.append(struct.pack("<HH", CLOSE, CLOSE))
    out.append(struct.pack("<HHHH", CLOSE, KEY_STRIPS, EQUALS, OPEN))
    for ident in sorted(network.strips):
        out.append(
            struct.pack(
                "<HHHHqHHH", OPEN, KEY_ID, EQUALS, I64, ident, KEY_SEGMENT_IDS, EQUALS, OPEN
            )
        )
        out.append(
            b"".join(struct.pack("<Hq", I64, ref << SEGMENT_SHIFT) for ref in network.strips[ident])
        )
        out.append(struct.pack("<HH", CLOSE, CLOSE))
    out.append(struct.pack("<H", CLOSE))
    return b"".join(out)


@dataclass(frozen=True, slots=True, eq=False)
class NewStrip:
    """A road to add: its locations (new indexes, ``low`` below ``high``) and its polyline.

    The polyline runs from the anchor of ``low`` to the anchor of ``high`` as an array of
    positions; its end points are those anchors.
    """

    low: int
    high: int
    path: NDArray[np.float32]


def rebuild(
    vanilla: SplineNetwork,
    mapping: Mapping[int, int],
    anchors: Mapping[int, tuple[float, float]],
    added: Sequence[NewStrip],
) -> SplineNetwork:
    """The spline network of a map whose locations changed.

    ``mapping`` gives the new index of every old location that is still there. The anchors,
    strips, segments and points of the others leave, and what is left keeps its order and is only
    renumbered to close the gaps (a strip keeps its segments, shared ones included), so that a map
    that lost nothing gets the same bytes back. ``anchors`` are the positions of the anchors of
    new locations and ``added`` the new roads; a road may join a new location to an old one and
    becomes a chain of short segments after the old ones, its points one run after the old ones.
    The order of the kept locations must not change: a strip runs from its lower anchor to its
    higher one.

    Vanilla's segments and points are not in the order of the strips or of each other: its points
    are numbered in runs along roads, its segments in an order of their own. Neither is touched
    here, because the engine's reader may rely on them [INFERRED].
    """
    if len(set(mapping.values())) != len(mapping):
        message = "Spline network: two locations got the same index"
        raise SplineError(message)
    positions = _anchor_positions(vanilla, mapping, anchors)
    kept = _kept_strips(vanilla, mapping)
    fresh = _fresh_strips(added, kept, positions)
    first = max(positions, default=0) + 1
    old_segments = sorted({ref for old in kept.values() for ref in vanilla.strips[old]})
    old_points = sorted(
        {point for ref in old_segments for point in vanilla.segments[ref] if point >= POINT_FLAG}
    )
    renumbered = {point: POINT_FLAG + first + number for number, point in enumerate(old_points)}
    point_xy = [_flagged(vanilla, point) for point in old_points]
    segments = [
        tuple(
            renumbered[point] if point >= POINT_FLAG else mapping[point]
            for point in vanilla.segments[ref]
        )
        for ref in old_segments
    ]
    numbers = {ref: number for number, ref in enumerate(old_segments)}
    strips: dict[int, tuple[int, ...]] = {}
    for ident in sorted(kept.keys() | fresh.keys()):
        if ident in kept:
            strips[ident] = tuple(numbers[ref] for ref in vanilla.strips[kept[ident]])
            continue
        chain = _chain(fresh[ident], first, point_xy)
        strips[ident] = tuple(range(len(segments), len(segments) + len(chain)))
        segments += chain
    order = sorted(positions)
    network = SplineNetwork(
        anchors=np.array(order, dtype=np.int64),
        anchor_xy=np.array([positions[i] for i in order], dtype=np.float32).reshape(-1, 2),
        point_xy=np.array(point_xy, dtype=np.float32).reshape(-1, 2),
        segments=tuple(segments),
        strips=strips,
    )
    check(network)
    return network


def _anchor_positions(
    vanilla: SplineNetwork, mapping: Mapping[int, int], anchors: Mapping[int, tuple[float, float]]
) -> dict[int, tuple[float, float]]:
    positions = {
        mapping[int(old)]: (float(x), float(y))
        for old, (x, y) in zip(vanilla.anchors.tolist(), vanilla.anchor_xy.tolist(), strict=True)
        if old in mapping
    }
    if positions.keys() & anchors.keys():
        message = "Spline network: an anchor to add already exists"
        raise SplineError(message)
    return positions | {int(index): (float(x), float(y)) for index, (x, y) in anchors.items()}


def _kept_strips(vanilla: SplineNetwork, mapping: Mapping[int, int]) -> dict[int, int]:
    """New id -> old id of the strips whose two locations are still there."""
    kept: dict[int, int] = {}
    for old in vanilla.strips:
        low, high = strip_ends(old)
        if low in mapping and high in mapping:
            if not mapping[low] < mapping[high]:
                message = "Spline network: the locations changed their order"
                raise SplineError(message)
            kept[strip_id(mapping[low], mapping[high])] = old
    return kept


def _fresh_strips(
    added: Sequence[NewStrip], kept: Mapping[int, int], positions: Mapping[int, tuple[float, float]]
) -> dict[int, NewStrip]:
    fresh = {strip_id(strip.low, strip.high): strip for strip in added}
    if len(fresh) != len(added) or fresh.keys() & kept.keys():
        message = "Spline network: a strip to add is repeated or exists"
        raise SplineError(message)
    for ident, strip in fresh.items():
        if not strip.low < strip.high or len(strip.path) < MIN_POINTS:
            message = (
                f"Spline network: strip {ident} does not run from a lower to a higher location"
            )
            raise SplineError(message)
        ends = ((strip.low, strip.path[0]), (strip.high, strip.path[-1]))
        if any(
            index not in positions or (float(end[0]), float(end[1])) != positions[index]
            for index, end in ends
        ):
            message = f"Spline network: strip {ident} does not run between its two anchors"
            raise SplineError(message)
    return fresh


def _chain(
    strip: NewStrip, first: int, point_xy: list[tuple[float, float]]
) -> list[tuple[int, ...]]:
    """The segments of a new strip, ``SEGMENT_POINTS`` points each, each joined to the next.

    Inner points join ``point_xy`` in the order of the path, as one run, like the points of a road
    in vanilla.
    """
    inner = strip.path[1:-1].tolist()
    ids: list[int] = [strip.low]
    for x, y in inner:
        ids.append(POINT_FLAG + first + len(point_xy))
        point_xy.append((float(x), float(y)))
    ids.append(strip.high)
    step = SEGMENT_POINTS - 1
    return [tuple(ids[start : start + SEGMENT_POINTS]) for start in range(0, len(ids) - 1, step)]


def _flagged(network: SplineNetwork, point: int) -> tuple[float, float]:
    x, y = network.point_xy[point - POINT_FLAG - network.first_point].tolist()
    return float(x), float(y)
