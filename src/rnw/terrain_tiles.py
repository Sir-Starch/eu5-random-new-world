"""EU5 1.4.1 terrain decal layers: tiled, mip-mapped, LZAV-compressed images.

Observed layout [V-EXEC]: a layer image is stored south-up; it is cut into 128x128
tiles with a 2-pixel border copied from neighbours (edge pixels repeated at the image
boundary), giving 132x132 tiles in row-major order. Mip level k+1 takes every odd
pixel of level k. All levels are stored one after another down to a single tile. Each
tile is an independent LZAV stream; ``.info`` lists byte offsets and sizes in ``.bin``.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.lzav import decode, encode

if TYPE_CHECKING:
    from numpy.typing import NDArray

TILE: Final[int] = 128
BORDER: Final[int] = 2
SIDE: Final[int] = TILE + 2 * BORDER
TILE_INFO: Final[re.Pattern[str]] = re.compile(r"offset=(\d+)\s+size=(\d+)")
HEADER: Final[re.Pattern[str]] = re.compile(
    r"source_resolution=\{ (\d+) (\d+) \}\nnum_channels=(\d+)\nbytes_per_channel=(\d+)\n"
)


class TileFormatError(ValueError):
    """A layer does not follow the observed tile layout."""


@dataclass(frozen=True, slots=True)
class LayerFormat:
    """Image size and sample type of one decal layer."""

    width: int
    height: int
    dtype: str

    @property
    def sample_bytes(self) -> int:
        """Bytes per sample."""
        return np.dtype(self.dtype).itemsize


def parse_info(text: str) -> tuple[LayerFormat, list[tuple[int, int]]]:
    """Read size, sample type and tile spans from ``.info`` text."""
    match = HEADER.match(text.removeprefix("﻿"))
    if match is None:
        message = "unexpected .info header"
        raise TileFormatError(message)
    width, height, channels, sample = (int(group) for group in match.groups())
    if channels != 1 or sample not in {1, 2}:
        message = f"unsupported layer: {channels} channels x {sample} bytes"
        raise TileFormatError(message)
    dtype = "<u2" if sample == 2 else "u1"  # noqa: PLR2004 - 16-bit samples
    spans = [(int(offset), int(size)) for offset, size in TILE_INFO.findall(text)]
    return LayerFormat(width, height, dtype), spans


def level_shapes(layer: LayerFormat) -> list[tuple[int, int]]:
    """(rows, columns) of every mip level, largest first, down to one tile."""
    shapes = [(layer.height, layer.width)]
    while shapes[-1][0] > TILE or shapes[-1][1] > TILE:
        rows, columns = shapes[-1]
        shapes.append((max(1, rows // 2), max(1, columns // 2)))
    return shapes


def tile_counts(rows: int, columns: int) -> tuple[int, int]:
    """Tiles down and across for one level."""
    return -(-rows // TILE), -(-columns // TILE)


def read_level0(layer: LayerFormat, spans: list[tuple[int, int]], data: bytes) -> NDArray[np.int64]:
    """Decode mip level 0 and return it north-up."""
    down, across = tile_counts(layer.height, layer.width)
    image = np.zeros((down * TILE, across * TILE), dtype=np.int64)
    raw_size = SIDE * SIDE * layer.sample_bytes
    for index in range(down * across):
        offset, size = spans[index]
        tile = np.frombuffer(decode(data[offset : offset + size], raw_size), layer.dtype)
        row, column = divmod(index, across)
        image[row * TILE : (row + 1) * TILE, column * TILE : (column + 1) * TILE] = tile.reshape(
            SIDE, SIDE
        )[BORDER : BORDER + TILE, BORDER : BORDER + TILE]
    return image[: layer.height, : layer.width][::-1]


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
