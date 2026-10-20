"""Pure NumPy raster resampling and blurring: the specification of the Rust kernels.

Moved from ``rnw.fields`` when they became native (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

STRIP_ROWS: Final[int] = 1024


def upsample(coarse: NDArray[np.int64], step: int, shape: tuple[int, int]) -> NDArray[np.int64]:
    """Bilinear interpolation of a grid whose sample ``(i, j)`` sits at ``(i*step, j*step)``."""
    height, width = shape
    columns = np.arange(width, dtype=np.int64)
    j = columns // step
    fx = columns % step
    out = np.empty(shape, dtype=np.int64)
    for start in range(0, height, STRIP_ROWS):
        rows = np.arange(start, min(height, start + STRIP_ROWS), dtype=np.int64)
        i = (rows // step)[:, np.newaxis]
        fy = (rows % step)[:, np.newaxis]
        top = coarse[i, j] * (step - fx) + coarse[i, j + 1] * fx
        bottom = coarse[i + 1, j] * (step - fx) + coarse[i + 1, j + 1] * fx
        out[start : start + rows.size] = (top * (step - fy) + bottom * fy) // (step * step)
    return out


def block_mean(values: NDArray[np.int64], step: int) -> NDArray[np.int64]:
    """Mean of each ``step`` x ``step`` block (partial blocks at the edges included)."""
    height, width = values.shape
    rows = -(-height // step)
    columns = -(-width // step)
    padded = np.pad(values, ((0, rows * step - height), (0, columns * step - width)), mode="edge")
    return padded.reshape(rows, step, columns, step).sum(axis=(1, 3)) // (step * step)


def box_blur(values: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """Separable integer box blur with edge replication."""
    out = values
    for axis in (0, 1):
        padded = np.pad(
            out, [(radius + 1, radius) if a == axis else (0, 0) for a in (0, 1)], mode="edge"
        )
        summed = np.cumsum(padded, axis=axis, dtype=np.int64)
        size = 2 * radius + 1
        if axis == 0:
            out = (summed[size:] - summed[:-size]) // size
        else:
            out = (summed[:, size:] - summed[:, :-size]) // size
    return out
