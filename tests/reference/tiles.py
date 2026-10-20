"""Pure NumPy tiling and Python LZAV packing: the specification of the Rust layer packer.

Moved from ``rnw.terrain_tiles`` when ``write_layer`` became native
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.terrain_tiles import BORDER, SIDE, TILE, level_shapes, tile_counts
from tests.reference.lzav import encode

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.terrain_tiles import LayerFormat


def _tiles(level: NDArray[np.int64], dtype: str) -> list[bytes]:
    rows, columns = level.shape
    down, across = tile_counts(rows, columns)
    padded = np.pad(
        level,
        ((BORDER, down * TILE - rows + BORDER), (BORDER, across * TILE - columns + BORDER)),
        mode="edge",
    ).astype(dtype)
    return [
        padded[r * TILE : r * TILE + SIDE, c * TILE : c * TILE + SIDE].tobytes()
        for r in range(down)
        for c in range(across)
    ]


def raw_tiles(north_up: NDArray[np.int64], layer: LayerFormat) -> list[bytes]:
    """Uncompressed tiles of every mip level, in file order."""
    level = north_up[::-1]
    out: list[bytes] = []
    for index, _ in enumerate(level_shapes(layer)):
        if index:
            level = level[1::2, 1::2]
        out.extend(_tiles(level, layer.dtype))
    return out


def write_layer(north_up: NDArray[np.int64], layer: LayerFormat) -> tuple[str, bytes]:
    """Build ``.info`` text and ``.bin`` bytes for an image."""
    chunks: list[bytes] = []
    spans: list[tuple[int, int]] = []
    offset = 0
    for tile in raw_tiles(north_up, layer):
        packed = encode(tile)
        spans.append((offset, len(packed)))
        chunks.append(packed)
        offset += len(packed)
    infos = " ".join(f"{{\n\t\toffset={o}\n\t\tsize={s}\n\t}}" for o, s in spans)
    info = (
        f"source_resolution={{ {layer.width} {layer.height} }}\nnum_channels=1\n"
        f"bytes_per_channel={layer.sample_bytes}\nempty_value={{ 0 0 0 0 }}\nlzav=yes\n"
        f"tile_infos={{ {infos} }}\n"
    )
    return info, b"".join(chunks)
