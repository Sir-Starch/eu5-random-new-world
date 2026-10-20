"""Pure-Python LZAV format-3 decoder: the specification the Rust decoder must equal.

Moved from ``rnw.lzav`` when the decoder became native ([ADR 0005](docs/adr/0005-native-core.md)).
"""

from __future__ import annotations

from typing import Final

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
