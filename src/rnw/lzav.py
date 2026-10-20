"""LZAV stream format 3: the native decoder and a small encoder.

Implemented from the format description and decoder in LZAV 5.18 by Aleksey Vaneev
(MIT, https://github.com/avaneev/lzav, commit 539f189193e1e81cddcccf554c8fe17dc107e876).
No LZAV code is copied. A stream is a prefix byte ``format << 4 | mref`` followed by
literal blocks (type 0) and reference blocks (types 1-3); it always ends with a literal
block. The encoder emits one final literal block, which is the form LZAV's own
compressor uses for very short inputs.
"""

from __future__ import annotations

from typing import Final, cast

import numpy as np

from rnw import _native

FORMAT: Final[int] = 3
MIN_REFERENCE: Final[int] = 5
LITERALS_AT_END: Final[int] = 9
SHORT_LENGTH: Final[int] = 16


# The decoder is native (ADR 0005); its pure-Python specification is tests/reference/lzav.py.
LzavError = _native.LzavError


def decode(data: bytes | bytearray, size: int) -> bytes:
    """Decode a format-3 stream that expands to exactly ``size`` bytes."""
    return _native.lzav_decode(bytes(data), size)


RUN_DISTANCE: Final[int] = 8
MIN_RUN: Final[int] = 32
SHORT_REFERENCE: Final[int] = 15


def _length_bytes(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:  # noqa: PLR2004 - seven bits per varint byte
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


def encode_literals(raw: bytes) -> bytes:
    """Encode ``raw`` as a valid format-3 stream with one final literal block."""
    payload = raw if len(raw) >= LITERALS_AT_END else raw.ljust(LITERALS_AT_END, b"\0")
    parts = bytearray([FORMAT << 4 | MIN_REFERENCE])
    if len(payload) < SHORT_LENGTH:
        parts.append(len(payload))
    else:
        parts.append(0)
        remaining = len(payload) - SHORT_LENGTH
        while remaining > 0x7F:  # noqa: PLR2004 - seven bits per varint byte
            parts.append(0x80 | (remaining & 0x7F))
            remaining >>= 7
        parts.append(remaining)
    return bytes(parts) + payload
