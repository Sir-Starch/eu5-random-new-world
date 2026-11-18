"""The original tagged-list cursor and parse order, before the Rust reader."""

from __future__ import annotations

import struct
from typing import cast

from rnw.splnet import (
    CLOSE,
    EQUALS,
    FORMAT_VERSION,
    I32,
    I64,
    KEY_COUNTS,
    KEY_ID,
    KEY_POINT_IDS,
    KEY_POINTS,
    KEY_SEGMENT_IDS,
    KEY_SEGMENTS,
    KEY_STRIPS,
    KEY_VERSION,
    OPEN,
    SEGMENT_SHIFT,
    U32,
    SplineError,
    SplineNetwork,
    _points,
    check,
)
from rnw.splnet import (
    _Reader as SourceReader,
)

# The point-table reader and semantic checks are unchanged; these are the migrated lists.
# pyright: reportPrivateUsage=false, reportAny=false


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
    anchors, anchor_xy, point_xy = _points(cast("SourceReader", cast("object", reader)), points)
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
