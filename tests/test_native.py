"""The Rust kernels equal their pure-Python references bit for bit (ADR 0005)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import lzav
from tests.reference import lzav as reference_lzav


def _streams() -> list[bytes]:
    generator = np.random.default_rng(7)
    noise = bytes(generator.integers(0, 256, 3000, dtype=np.uint8))
    runs = bytes(generator.integers(0, 3, 5000, dtype=np.uint8)) + bytes(40_000) + b"\x07" * 77
    shorts = [b"a", b"abcdefgh", bytes(range(20))]
    return [noise, runs, *shorts]


@pytest.mark.parametrize("raw", _streams())
def test_lzav_decoder_equals_the_reference(raw: bytes) -> None:
    """Literal-only and run-length streams decode to the original in both decoders."""
    for stream in (lzav.encode(raw), lzav.encode_literals(raw)):
        size = (
            max(len(raw), lzav.LITERALS_AT_END) if stream == lzav.encode_literals(raw) else len(raw)
        )
        assert lzav.decode(stream, size) == reference_lzav.decode(stream, size)


def test_lzav_decoder_refuses_what_the_reference_refuses() -> None:
    """Wrong formats, wrong sizes and references before the data fail in both."""
    raw = bytes(300)
    stream = lzav.encode(raw)
    for data, size in ((b"\x25\x00", 0), (stream, len(raw) + 1), (stream[:-5], len(raw))):
        with pytest.raises(ValueError):  # noqa: PT011 - both raise a ValueError subclass
            _ = lzav.decode(data, size)
        with pytest.raises((ValueError, IndexError)):
            _ = reference_lzav.decode(data, size)
    assert lzav.LzavError.__mro__[1] is ValueError
