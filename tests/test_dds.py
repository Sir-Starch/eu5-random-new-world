"""The chunked DXT5 rewrite equals the whole-image one for any chunk size."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import struct

import numpy as np
import pytest

from rnw import dds
from tests.reference import dds as reference_dds


def _file(rows: int, columns: int, seed: int) -> bytes:
    """A DXT5 file of random blocks with a full mip chain."""
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<II", header, 12, rows, columns)
    levels = 1
    while max(rows >> levels, columns >> levels) > 0 and levels < 12:
        levels += 1
    struct.pack_into("<I", header, 28, levels)
    header[84:88] = b"DXT5"
    size = sum(
        -(-max(1, rows >> level) // 4) * -(-max(1, columns >> level) // 4) * 16
        for level in range(levels)
    )
    body = np.random.default_rng(seed).integers(0, 256, size, dtype=np.uint8).tobytes()
    return bytes(header) + body


@pytest.mark.parametrize(("rows", "columns"), [(64, 48), (37, 53), (8, 130)])
@pytest.mark.parametrize("chunk", [1, 7, 4096])
def test_chunked_rewrite_equals_the_whole_image_rewrite(
    monkeypatch: pytest.MonkeyPatch, rows: int, columns: int, chunk: int
) -> None:
    """Pixels of the changed blocks are re-encoded the same way at every mip level."""
    generator = np.random.default_rng(rows * columns)
    data = _file(rows, columns, rows)
    image = generator.integers(0, 256, (rows, columns, 4), dtype=np.uint8)
    image[: rows // 2] = image[0, 0]  # flat blocks take the single-colour path
    changed = generator.random((rows, columns)) < 0.05
    monkeypatch.setattr(dds, "CHUNK_BLOCKS", chunk)
    result = dds.rewrite(data, image, changed)
    assert result == reference_dds.rewrite(data, image, changed)
    assert result != data
    assert len(result) == len(data)
    untouched = dds.rewrite(data, image, np.zeros((rows, columns), dtype=bool))
    assert untouched == data
