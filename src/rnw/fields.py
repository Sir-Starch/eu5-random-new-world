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
from rnw.noise import NOISE_SCALE
from rnw.rng import MASK64, mix64

if TYPE_CHECKING:
    from numpy.typing import NDArray

PERMILLE: Final[int] = 1000


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
    row0: int = 0,
) -> NDArray[np.int64]:
    """Domain-warped rotated fractal noise, sampled every ``step`` pixels and upsampled.

    Coordinates are displaced by two low-frequency noises of amplitude ``warp_px``
    before lookup, which bends straight features into natural curves. ``row0`` is the row
    of the whole raster where the window ``shape`` starts; it must lie on the sample
    lattice (a multiple of ``step``), so a window holds the rows of the whole raster.
    """
    if row0 % step:
        message = f"row0 {row0} is not a multiple of the step {step}"
        raise ValueError(message)
    rows = shape[0] // step + 2
    columns = shape[1] // step + 2
    ys = ((np.arange(rows, dtype=np.int64) + row0 // step) * step * SUBPIXEL)[:, np.newaxis]
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


def upsample(coarse: NDArray[np.int64], step: int, shape: tuple[int, int]) -> NDArray[np.int64]:
    """Bilinear interpolation of a grid whose sample ``(i, j)`` sits at ``(i*step, j*step)``."""
    return _native.upsample(np.ascontiguousarray(coarse, dtype=np.int64), step, *shape)


def block_mean(values: NDArray[np.int64], step: int) -> NDArray[np.int64]:
    """Mean of each ``step`` x ``step`` block (partial blocks at the edges included)."""
    return _native.block_mean(np.ascontiguousarray(values, dtype=np.int64), step)


def box_blur(values: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """Separable integer box blur with edge replication."""
    return _native.box_blur(np.ascontiguousarray(values, dtype=np.int64), radius)
