"""Integer fractal value noise defined on absolute world coordinates.

All arithmetic is fixed-point integer arithmetic, so the same key and coordinates give
identical values on every platform. A field computed for a sub-window equals the same
pixels of a larger field. The kernels are Rust (`native/`, ADR 0005); their NumPy
specification is `tests/reference/noise.py`.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from rnw import _native
from rnw.rng import MASK64

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

NOISE_SCALE: Final[int] = 1 << 15
# Fractional interpolation must resolve every pixel of the largest continent.
UNIT: Final[int] = 1 << 16


def value_noise(  # noqa: PLR0913 - a field needs key, origin, size and period.
    key: int, x0: int, y0: int, width: int, height: int, *, period: int
) -> NDArray[np.int64]:
    """Return smooth value noise in [-32768, 32767] for a window of the world."""
    _check_window(x0, y0, width, height, period)
    flat = _native.value_window(key & MASK64, x0, y0, width, height, period)
    return flat.reshape(height, width)


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
    _check_window(x0, y0, width, height, period)
    flat = _native.fractal_window(
        key & MASK64, x0, y0, width, height, period, octaves, persistence_permille
    )
    return flat.reshape(height, width)


def _check_window(x0: int, y0: int, width: int, height: int, period: int) -> None:
    if min(x0, y0) < 0 or min(width, height, period) <= 0:
        message = "Noise requires a non-negative origin and positive size and period"
        raise ValueError(message)
