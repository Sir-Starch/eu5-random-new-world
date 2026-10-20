"""LZAV stream format 3: the native decoder and a small encoder.

Implemented from the format description and decoder in LZAV 5.18 by Aleksey Vaneev
(MIT, https://github.com/avaneev/lzav, commit 539f189193e1e81cddcccf554c8fe17dc107e876).
No LZAV code is copied. A stream is a prefix byte ``format << 4 | mref`` followed by
literal blocks (type 0) and reference blocks (types 1-3); it always ends with a literal
block. The encoder emits one final literal block, which is the form LZAV's own
compressor uses for very short inputs.
"""

from __future__ import annotations

from typing import Final

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


def encode(raw: bytes) -> bytes:
    """Encode with offset-8 reference blocks for repeated runs, literals elsewhere.

    Literal blocks carry no offset bits, so after one the decoder's carry shift is 2
    and the 10-bit offset field holds ``8 >> 2``; directly after a reference it is 8.
    The final ``LITERALS_AT_END`` bytes are always literals.
    """
    return _native.lzav_encode(bytes(raw))


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
