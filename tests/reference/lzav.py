"""Pure-Python LZAV format-3 decoder: the specification the Rust decoder must equal.

Moved from ``rnw.lzav`` when the decoder became native ([ADR 0005](docs/adr/0005-native-core.md)).
"""

from __future__ import annotations

from typing import Final, cast

import numpy as np

FORMAT: Final[int] = 3
MIN_REFERENCE: Final[int] = 5
LITERALS_AT_END: Final[int] = 9
OFFSET_MASKS: Final[tuple[int, ...]] = (0, 0x3FF, 0x7FFF, 0x1FFFFF)
CARRY_SHIFTS: Final[tuple[int, ...]] = (0, 0, 3, 5)
SHORT_LENGTH: Final[int] = 16
VARINT_LIMIT: Final[int] = 28


class LzavError(ValueError):
    """Malformed or unsupported LZAV data."""


def _varint(data: bytes | bytearray, index: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80 or shift >= VARINT_LIMIT - 7:
            return value, index
        shift += 7


def decode(data: bytes | bytearray, size: int) -> bytes:
    """Decode a format-3 stream that expands to exactly ``size`` bytes."""
    if len(data) < 2 or data[0] >> 4 != FORMAT:
        message = "not an LZAV format-3 stream"
        raise LzavError(message)
    extra = (data[0] & 15) - 1
    out = bytearray()
    index = 1
    carry = 0
    shift = 0
    while index < len(data):
        header = data[index]
        kind = (header >> 4) & 3
        index += 1
        if kind == 0:
            count = header & 15
            if count == 0:
                count, index = _varint(data, index)
                count += SHORT_LENGTH
            carry |= (header >> 6) << shift
            shift += 2
            out += data[index : index + count]
            index += count
            continue
        word = int.from_bytes(bytes(data[index : index + 4]).ljust(4, b"\0"), "little")
        distance = ((((word << 2) | (header >> 6)) & OFFSET_MASKS[kind]) << shift) | carry
        new_shift = CARRY_SHIFTS[kind]
        carry = (data[index + kind - 1] << new_shift) >> 8
        shift = new_shift
        index += kind
        count = header & 15
        if count:
            length = extra + count
        else:
            length, index = _varint(data, index)
            length += extra + SHORT_LENGTH
        start = len(out) - distance
        if distance <= 0 or start < 0:
            message = "reference outside decoded data"
            raise LzavError(message)
        for step in range(length):
            out.append(out[start + step])
    if len(out) != size:
        message = f"decoded {len(out)} bytes, expected {size}"
        raise LzavError(message)
    return bytes(out)


RUN_DISTANCE: Final[int] = 8
MIN_RUN: Final[int] = 32
SHORT_REFERENCE: Final[int] = 15


def _length_bytes(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    out.append(value)
    return bytes(out)


def _literal_block(chunk: bytes) -> bytes:
    if len(chunk) < SHORT_LENGTH:
        return bytes([len(chunk)]) + chunk
    return b"\x00" + _length_bytes(len(chunk) - SHORT_LENGTH) + chunk


def _runs(raw: bytes) -> list[tuple[int, int]]:
    """Spans [start, end) where every byte repeats the byte 8 positions earlier."""
    if len(raw) <= RUN_DISTANCE:
        return []
    data = np.frombuffer(raw, dtype=np.uint8)
    same = np.concatenate([[False], data[RUN_DISTANCE:] == data[:-RUN_DISTANCE], [False]])
    edges = np.flatnonzero(np.diff(same.astype(np.int8)))
    spans: list[tuple[int, int]] = []
    starts = cast("list[int]", edges[0::2].tolist())
    ends = cast("list[int]", edges[1::2].tolist())
    for start, end in zip(starts, ends, strict=True):
        if end - start >= MIN_RUN:
            spans.append((start + RUN_DISTANCE, end + RUN_DISTANCE))
    return spans


def encode(raw: bytes) -> bytes:
    """Encode with offset-8 reference blocks for repeated runs, literals elsewhere.

    Literal blocks carry no offset bits, so after one the decoder's carry shift is 2
    and the 10-bit offset field holds ``8 >> 2``; directly after a reference it is 8.
    The final ``LITERALS_AT_END`` bytes are always literals.
    """
    limit = len(raw) - LITERALS_AT_END
    out = bytearray([FORMAT << 4 | MIN_REFERENCE])
    position = 0
    for run_start, run_end in _runs(raw):
        start = max(run_start, position)
        end = min(run_end, limit)
        if end - start < MIN_REFERENCE + 1:
            continue
        shift = 0
        if start > position:
            out += _literal_block(raw[position:start])
            shift = 2
        field = RUN_DISTANCE >> shift
        length = end - start
        extra = MIN_REFERENCE - 1
        if length - extra <= SHORT_REFERENCE:
            out += bytes([(field & 3) << 6 | 0x10 | (length - extra), field >> 2])
        else:
            out += bytes([(field & 3) << 6 | 0x10, field >> 2])
            out += _length_bytes(length - extra - SHORT_LENGTH)
        position = end
    tail = raw[position:]
    out += (
        b"\x00" + _length_bytes(len(tail) - SHORT_LENGTH) + tail
        if len(tail) >= SHORT_LENGTH
        else bytes([len(tail)]) + tail
    )
    return bytes(out)
