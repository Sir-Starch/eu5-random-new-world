"""Integer fractal value noise defined on absolute world coordinates.

All arithmetic is fixed-point integer arithmetic, so the same key and coordinates give
identical values on every platform. A field computed for a sub-window equals the same
pixels of a larger field.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rng import GAMMA, MASK64, hash_grid, mix64

if TYPE_CHECKING:
    from numpy.typing import NDArray

NOISE_SCALE: Final[int] = 1 << 15
UNIT: Final[int] = 256
PERMILLE: Final[int] = 1000


def _smooth(t: NDArray[np.int64]) -> NDArray[np.int64]:
    """Smoothstep in units of 1/256: 3t^2 - 2t^3."""
    return (t * t * (3 * UNIT - 2 * t)) // (UNIT * UNIT)


def value_noise(  # noqa: PLR0913 - a field needs key, origin, size and period.
    key: int, x0: int, y0: int, width: int, height: int, *, period: int
) -> NDArray[np.int64]:
    """Return smooth value noise in [-32768, 32767] for a window of the world."""
    if min(x0, y0) < 0 or min(width, height, period) <= 0:
        message = "Noise requires a non-negative origin and positive size and period"
        raise ValueError(message)
    xs = np.arange(x0, x0 + width, dtype=np.int64)
    ys = np.arange(y0, y0 + height, dtype=np.int64)
    ix = xs // period
    iy = ys // period
    sx = _smooth((xs - ix * period) * UNIT // period)
    sy = _smooth((ys - iy * period) * UNIT // period)
    lattice_x = np.arange(int(ix[0]), int(ix[-1]) + 2, dtype=np.int64)
    lattice_y = np.arange(int(iy[0]), int(iy[-1]) + 2, dtype=np.int64)
    raw = hash_grid(key, lattice_x[np.newaxis, :], lattice_y[:, np.newaxis])
    lattice = (raw >> np.uint64(48)).astype(np.int64) - NOISE_SCALE
    gx = (ix - ix[0])[np.newaxis, :]
    gy = (iy - iy[0])[:, np.newaxis]
    v00 = lattice[gy, gx]
    v10 = lattice[gy, gx + 1]
    v01 = lattice[gy + 1, gx]
    v11 = lattice[gy + 1, gx + 1]
    top = v00 * UNIT + (v10 - v00) * sx[np.newaxis, :]
    bottom = v01 * UNIT + (v11 - v01) * sx[np.newaxis, :]
    return (top * UNIT + (bottom - top) * sy[:, np.newaxis]) // (UNIT * UNIT)


def fractal_noise(  # noqa: PLR0913 - octave controls are part of the field definition.
    key: int,
    x0: int,
    y0: int,
    width: int,
    height: int,
    *,
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[np.int64]:
    """Sum value-noise octaves with halving periods, normalized to [-32768, 32767]."""
    total = np.zeros((height, width), dtype=np.int64)
    amplitude = PERMILLE
    weight = 0
    for octave in range(octaves):
        octave_key = mix64((key + octave * GAMMA) & MASK64)
        octave_period = max(2, period >> octave)
        total += amplitude * value_noise(octave_key, x0, y0, width, height, period=octave_period)
        weight += amplitude
        amplitude = max(1, amplitude * persistence_permille // PERMILLE)
    return total // max(1, weight)
