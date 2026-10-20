"""Minimal DXT5 (BC3) DDS support: block encoder and partial mip-chain rewriting.

The encoder uses bounding-box endpoints per 4x4 block (alpha: 8-value mode, colour:
4-colour BC1 mode) and nearest-palette indices. It is meant for smooth textures such as
water colour; untouched blocks keep their original bytes.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

HEADER_SIZE: Final[int] = 128
BLOCK: Final[int] = 4
BLOCK_BYTES: Final[int] = 16
DXT5: Final[bytes] = b"DXT5"
CHUNK_BLOCKS: Final[int] = 1 << 15


class DdsError(ValueError):
    """Unsupported DDS layout."""


@dataclass(frozen=True, slots=True)
class DdsLayout:
    """Size, mip count and byte offset of every level of a DXT5 file."""

    width: int
    height: int
    levels: tuple[tuple[int, int, int], ...]

    def blocks(self, level: int) -> tuple[int, int]:
        """Blocks down and across at a mip level."""
        _, rows, columns = self.levels[level]
        return -(-rows // BLOCK), -(-columns // BLOCK)


def layout(data: bytes) -> DdsLayout:
    """Parse a plain DXT5 DDS header (no DX10 extension)."""
    if data[:4] != b"DDS " or data[84:88] != DXT5:
        message = "only DXT5 DDS files are supported"
        raise DdsError(message)
    height, width = struct.unpack_from("<II", data, 12)
    mips = max(1, struct.unpack_from("<I", data, 28)[0])
    offset = HEADER_SIZE
    levels: list[tuple[int, int, int]] = []
    for level in range(mips):
        rows, columns = max(1, height >> level), max(1, width >> level)
        levels.append((offset, rows, columns))
        offset += -(-rows // BLOCK) * -(-columns // BLOCK) * BLOCK_BYTES
    if offset > len(data):
        message = "DDS file is shorter than its mip chain"
        raise DdsError(message)
    return DdsLayout(width, height, tuple(levels))


def _to565(rgb: NDArray[np.int64]) -> NDArray[np.int64]:
    return ((rgb[..., 0] >> 3) << 11) | ((rgb[..., 1] >> 2) << 5) | (rgb[..., 2] >> 3)


def _from565(value: NDArray[np.int64]) -> NDArray[np.int64]:
    red = (value >> 11) & 31
    green = (value >> 5) & 63
    blue = value & 31
    return np.stack(
        [(red << 3) | (red >> 2), (green << 2) | (green >> 4), (blue << 3) | (blue >> 2)], axis=-1
    )


def encode_blocks(blocks: NDArray[np.uint8]) -> bytes:
    """Encode ``(n, 4, 4, 4)`` RGBA blocks as DXT5 bytes."""
    pixels = blocks.reshape(-1, 16, 4).astype(np.int64)
    count = pixels.shape[0]
    alpha = pixels[:, :, 3]
    a0 = alpha.max(axis=1)
    a1 = alpha.min(axis=1)
    weights = np.array(
        [[7, 0], [0, 7], [6, 1], [5, 2], [4, 3], [3, 4], [2, 5], [1, 6]], dtype=np.int64
    )
    palette_a = (weights[:, 0][None, :] * a0[:, None] + weights[:, 1][None, :] * a1[:, None]) // 7
    a_index = np.argmin(np.abs(alpha[:, :, None] - palette_a[:, None, :]), axis=2)
    a_index[a0 == a1] = 0
    a_bits = np.zeros(count, dtype=np.uint64)
    for pixel in range(16):
        a_bits |= a_index[:, pixel].astype(np.uint64) << np.uint64(3 * pixel)
    rgb = pixels[:, :, :3]
    c0 = _to565(rgb.max(axis=1))
    c1 = _to565(rgb.min(axis=1))
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    e0 = _from565(c0)
    e1 = _from565(c1)
    palette = np.stack([e0, e1, (2 * e0 + e1) // 3, (e0 + 2 * e1) // 3], axis=1)
    distance = ((rgb[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(axis=3)
    c_index = np.argmin(distance, axis=2)
    c_index[c0 == c1] = 0
    c_bits = np.zeros(count, dtype=np.uint64)
    for pixel in range(16):
        c_bits |= c_index[:, pixel].astype(np.uint64) << np.uint64(2 * pixel)
    out = np.zeros((count, BLOCK_BYTES), dtype=np.uint8)
    out[:, 0] = a0
    out[:, 1] = a1
    for byte in range(6):
        out[:, 2 + byte] = (a_bits >> np.uint64(8 * byte)) & np.uint64(0xFF)
    out[:, 8] = c0 & 0xFF
    out[:, 9] = c0 >> 8
    out[:, 10] = c1 & 0xFF
    out[:, 11] = c1 >> 8
    for byte in range(4):
        out[:, 12 + byte] = (c_bits >> np.uint64(8 * byte)) & np.uint64(0xFF)
    return out.tobytes()


def _blocks_of(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """A ``(down, across, 4, 4, 4)`` view of the image cut into 4 x 4 blocks (edges repeated)."""
    rows, columns = image.shape[:2]
    padded = np.pad(
        image,
        ((0, -rows % BLOCK), (0, -columns % BLOCK), (0, 0)),
        mode="edge",
    )
    down, across = padded.shape[0] // BLOCK, padded.shape[1] // BLOCK
    return padded.reshape(down, BLOCK, across, BLOCK, 4).transpose(0, 2, 1, 3, 4)


def _halve(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """The next mip level: the mean of every 2 x 2 block, rounded down (edges repeated)."""
    rows, columns = image.shape[:2]
    if rows == 1 and columns == 1:
        return image
    padded = np.pad(image, ((0, rows % 2), (0, columns % 2), (0, 0)), mode="edge")
    total = padded.reshape(padded.shape[0] // 2, 2, padded.shape[1] // 2, 2, -1).sum(
        axis=(1, 3), dtype=np.uint16
    )
    return (total // 4).astype(np.uint8)


def rewrite(data: bytes, image: NDArray[np.uint8], changed: NDArray[np.bool_]) -> bytes:
    """Re-encode the blocks of every mip level that overlap ``changed`` pixels.

    ``image`` is the full new level-0 RGBA image; lower levels are box-filtered from it.
    Blocks not overlapping ``changed`` keep their original bytes. The blocks are encoded
    ``CHUNK_BLOCKS`` at a time, which bounds the working memory and not the result.
    """
    shape = layout(data)
    out = bytearray(data)
    level_image = image
    level_mask = changed
    for level, (offset, rows, columns) in enumerate(shape.levels):
        if level:
            level_image = _halve(level_image)
            mask_rows, mask_columns = level_mask.shape
            padded = np.pad(level_mask, ((0, mask_rows % 2), (0, mask_columns % 2)))
            level_mask = padded.reshape(padded.shape[0] // 2, 2, padded.shape[1] // 2, 2).any(
                axis=(1, 3)
            )
        down, across = shape.blocks(level)
        mask = np.pad(
            level_mask[:rows, :columns], ((0, down * BLOCK - rows), (0, across * BLOCK - columns))
        )
        touched = cast(
            "NDArray[np.bool_]", mask.reshape(down, BLOCK, across, BLOCK).any(axis=(1, 3))
        )
        if not np.any(touched):
            continue
        blocks = _blocks_of(level_image[:rows, :columns])
        indices = np.flatnonzero(touched.ravel())
        target = np.frombuffer(out, np.uint8, count=down * across * BLOCK_BYTES, offset=offset)
        view = target.reshape(-1, BLOCK_BYTES).copy()
        for start in range(0, indices.size, CHUNK_BLOCKS):
            chosen = indices[start : start + CHUNK_BLOCKS]
            encoded = np.frombuffer(
                encode_blocks(blocks[chosen // across, chosen % across]), np.uint8
            )
            view[chosen] = encoded.reshape(-1, BLOCK_BYTES)
        out[offset : offset + view.size] = view.tobytes()
    return bytes(out)
