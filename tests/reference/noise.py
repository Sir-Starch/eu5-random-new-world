"""Pure NumPy value and fractal noise: the specification the Rust kernels must equal.

Moved from ``rnw.noise`` and ``rnw.fields`` when the kernels became native
(docs/adr/0005-native-core.md). All arithmetic is fixed-point integer arithmetic.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.noise import NOISE_SCALE, UNIT
from rnw.rng import GAMMA, MASK64, hash_grid, mix64

if TYPE_CHECKING:
    from numpy.typing import NDArray

PERMILLE: Final[int] = 1000


def _smooth(t: NDArray[np.int64]) -> NDArray[np.int64]:
    """Fixed-point smoothstep: 3t^2 - 2t^3."""
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


SUBPIXEL: Final[int] = 16
ANGLE_SCALE: Final[int] = 1024
# (cos, sin) * 1024 of the lattice rotation per octave: multiples of the golden angle,
# so no two octaves share grid axes and features do not line up with the raster.
ROTATIONS: Final[tuple[tuple[int, int], ...]] = (
    (-755, 692), (90, -1020), (623, 813), (-1008, -178), (864, -550), (-266, 989),
)  # fmt: skip


def _smooth_unit(t: NDArray[np.int64]) -> NDArray[np.int64]:
    return t * t * (3 * UNIT - 2 * t) // (UNIT * UNIT)


def value_noise_at(
    key: int, xs: NDArray[np.int64], ys: NDArray[np.int64], period: int
) -> NDArray[np.int64]:
    """Value noise in [-32768, 32767] at arbitrary integer coordinates of any shape."""
    ix = np.floor_divide(xs, period)
    iy = np.floor_divide(ys, period)
    sx = _smooth_unit((xs - ix * period) * UNIT // period)
    sy = _smooth_unit((ys - iy * period) * UNIT // period)
    corners = [
        (hash_grid(key, ix + dx, iy + dy) >> np.uint64(48)).astype(np.int64) - NOISE_SCALE
        for dy in (0, 1)
        for dx in (0, 1)
    ]
    top = corners[0] * UNIT + (corners[1] - corners[0]) * sx
    bottom = corners[2] * UNIT + (corners[3] - corners[2]) * sx
    return (top * UNIT + (bottom - top) * sy) // (UNIT * UNIT)


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
    total = np.zeros(xs.shape, dtype=np.int64)
    amplitude = PERMILLE
    weight = 0
    for octave in range(octaves):
        cos, sin = ROTATIONS[octave % len(ROTATIONS)]
        rx = (xs * cos - ys * sin) // ANGLE_SCALE
        ry = (xs * sin + ys * cos) // ANGLE_SCALE
        octave_key = mix64((key + octave * GAMMA) & MASK64)
        octave_period = max(2, (period >> octave)) * SUBPIXEL
        total += amplitude * value_noise_at(octave_key, rx, ry, octave_period)
        weight += amplitude
        amplitude = max(1, amplitude * persistence_permille // PERMILLE)
    return total // max(1, weight)
