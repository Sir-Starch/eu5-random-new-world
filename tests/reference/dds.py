"""The whole-image DXT5 rewrite: the specification of the chunked ``rnw.dds.rewrite``.

Moved from ``rnw.dds`` when the rewrite became chunked and byte-valued (ADR 0005).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.dds import BLOCK, BLOCK_BYTES, encode_blocks, layout

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _blocks_of(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    rows, columns = image.shape[:2]
    padded = np.pad(
        image,
        ((0, -rows % BLOCK), (0, -columns % BLOCK), (0, 0)),
        mode="edge",
    )
    down, across = padded.shape[0] // BLOCK, padded.shape[1] // BLOCK
    return padded.reshape(down, BLOCK, across, BLOCK, 4).transpose(0, 2, 1, 3, 4)


def _halve(image: NDArray[np.int64]) -> NDArray[np.int64]:
    rows, columns = image.shape[:2]
    if rows == 1 and columns == 1:
        return image
    padded = np.pad(image, ((0, rows % 2), (0, columns % 2), (0, 0)), mode="edge")
    return (
        padded.reshape(padded.shape[0] // 2, 2, padded.shape[1] // 2, 2, -1).sum(axis=(1, 3)) // 4
    )


def rewrite(data: bytes, image: NDArray[np.uint8], changed: NDArray[np.bool_]) -> bytes:
    """Re-encode the blocks of every mip level that overlap ``changed`` pixels.

    ``image`` is the full new level-0 RGBA image; lower levels are box-filtered from it.
    Blocks not overlapping ``changed`` keep their original bytes.
    """
    shape = layout(data)
    out = bytearray(data)
    level_image = image.astype(np.int64)
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
        blocks = _blocks_of(level_image[:rows, :columns].clip(0, 255).astype(np.uint8))
        indices = np.flatnonzero(touched.ravel())
        encoded = np.frombuffer(
            encode_blocks(blocks.reshape(-1, BLOCK, BLOCK, 4)[indices]), np.uint8
        )
        target = np.frombuffer(out, np.uint8, count=down * across * BLOCK_BYTES, offset=offset)
        view = target.reshape(-1, BLOCK_BYTES).copy()
        view[indices] = encoded.reshape(-1, BLOCK_BYTES)
        out[offset : offset + view.size] = view.tobytes()
    return bytes(out)
