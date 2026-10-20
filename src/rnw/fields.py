"""Integer raster helpers shared by relief, climate and terrain synthesis.

Every function is integer arithmetic on NumPy arrays, so results are identical on all
platforms. Large rasters are processed in row strips to bound memory.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import MASK64, mix64

if TYPE_CHECKING:
    from numpy.typing import NDArray

PERMILLE: Final[int] = 1000
STRIP_ROWS: Final[int] = 1024


def smoothstep(values: NDArray[np.int64], low: int, high: int) -> NDArray[np.int64]:
    """Smoothstep from ``low`` to ``high`` in permille (0 below, 1000 above)."""
    t = np.clip((values - low) * PERMILLE // max(1, high - low), 0, PERMILLE)
    return t * t * (3 * PERMILLE - 2 * t) // (PERMILLE * PERMILLE)


SUBPIXEL: Final[int] = 16


def _flat(values: NDArray[np.int64]) -> NDArray[np.int64]:
    return np.ascontiguousarray(values, dtype=np.int64).reshape(-1)


def value_noise_at(
    key: int, xs: NDArray[np.int64], ys: NDArray[np.int64], period: int
) -> NDArray[np.int64]:
    """Value noise in [-32768, 32767] at arbitrary integer coordinates of any shape."""
    flat = _native.value_noise_at(key & MASK64, _flat(xs), _flat(ys), period)
    return flat.reshape(xs.shape)


def fractal_at(  # noqa: PLR0913 - octave controls are part of the field definition.
    key: int,
    xs: NDArray[np.int64],
    ys: NDArray[np.int64],
    *,
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[np.int64]:
    """Rotated-lattice fractal noise at sub-pixel coordinates (units of 1/16 pixel)."""
    flat = _native.fractal_at(
        key & MASK64, _flat(xs), _flat(ys), period, octaves, persistence_permille
    )
    return flat.reshape(xs.shape)


def warped_noise(  # noqa: PLR0913 - a field is defined by its stream, grid, warp and octaves.
    key: int,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
    warp_px: int,
) -> NDArray[np.int64]:
    """Domain-warped rotated fractal noise, sampled every ``step`` pixels and upsampled.

    Coordinates are displaced by two low-frequency noises of amplitude ``warp_px``
    before lookup, which bends straight features into natural curves.
    """
    rows = shape[0] // step + 2
    columns = shape[1] // step + 2
    ys = (np.arange(rows, dtype=np.int64) * step * SUBPIXEL)[:, np.newaxis]
    xs = (np.arange(columns, dtype=np.int64) * step * SUBPIXEL)[np.newaxis, :]
    ys, xs = np.broadcast_arrays(ys, xs)
    if warp_px:
        warp_period = max(2, period * 2)
        dx = fractal_at(mix64(key ^ 0x57A1), xs, ys, period=warp_period, octaves=2,
                        persistence_permille=500)  # fmt: skip
        dy = fractal_at(mix64(key ^ 0x57A2), xs, ys, period=warp_period, octaves=2,
                        persistence_permille=500)  # fmt: skip
        xs = xs + dx * warp_px * SUBPIXEL // NOISE_SCALE
        ys = ys + dy * warp_px * SUBPIXEL // NOISE_SCALE
    coarse = fractal_at(key, xs, ys, period=period, octaves=octaves, persistence_permille=500)
    return upsample(coarse, step, shape)


def coarse_noise(  # noqa: PLR0913 - a field is defined by its stream, grid and octaves.
    key: int,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[np.int64]:
    """Fractal noise sampled every ``step`` pixels (one extra sample per axis).

    Sample ``(i, j)`` stands for pixel ``(i * step, j * step)``; ``period`` is in pixels.
    """
    rows = shape[0] // step + 2
    columns = shape[1] // step + 2
    return fractal_noise(
        key,
        0,
        0,
        columns,
        rows,
        period=max(2, period // step),
        octaves=octaves,
        persistence_permille=persistence_permille,
    )


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


def resample_nearest(values: NDArray[np.int64], shape: tuple[int, int]) -> NDArray[np.int64]:
    """Nearest-neighbour resampling of a coarse grid to ``shape``."""
    rows = np.arange(shape[0], dtype=np.int64) * values.shape[0] // shape[0]
    columns = np.arange(shape[1], dtype=np.int64) * values.shape[1] // shape[1]
    return values[rows[:, np.newaxis], columns[np.newaxis, :]]
