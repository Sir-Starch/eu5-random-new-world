"""Procedural north-south barrier with an optional protected straight core and coastal relief.

No EU4 map data is used. The full-height corridor is derived from the installed EU5
canvas; protected Old World pixels are never annexed to make the barrier fit.
"""

# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.fields import SUBPIXEL, fractal_at, value_noise_at
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

PERMILLE = 1000
STRIP_ROWS = 256


def geometry(domain: NDArray[np.bool_], settings: NewWorldSettings) -> tuple[int, int]:
    """Centre and maximum half-width inside a full-height, protected-free corridor."""
    ends = np.flatnonzero(np.diff(np.pad(domain.all(axis=0), 1).astype(np.int8)))
    runs = [(int(a), int(b)) for a, b in zip(ends[::2], ends[1::2], strict=True)]
    half = max(4, domain.shape[1] * settings.wall_width_permille // (2 * PERMILLE))
    padding = half + settings.coast_margin_px
    fits = [(a + padding, b - padding - 1) for a, b in runs if b - a > 2 * padding]
    if not fits:
        message = (
            "The Wall needs a continuous north-south canvas corridor wide enough for its width"
        )
        raise ValueError(message)
    left, right = max(fits, key=lambda run: run[1] - run[0])
    return left + (right - left) * settings.wall_position_permille // PERMILLE, half


def coast(domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> NDArray[np.bool_]:
    """Threshold one continuous density field inside a straight continental envelope.

    Land share shifts sea level, feature size and octaves set the scale of bays and
    islands, and coastal irregularity controls their strength. A low-density saddle
    can become a strait when continuity is not required; no passages are placed.
    """
    centre, half = geometry(domain, settings)
    height, _ = domain.shape
    left, right = centre - half, centre + half + 1
    xs = np.arange(left, right, dtype=np.int64)[None, :]
    result = np.zeros(domain.shape, dtype=bool)
    key = derive_seed(seed, "wall_density")
    for first in range(0, height, STRIP_ROWS):
        checkpoint()
        ys = np.arange(first, min(height, first + STRIP_ROWS), dtype=np.int64)[:, None]
        xx, yy = np.broadcast_arrays(xs * SUBPIXEL, ys * SUBPIXEL)
        noise = fractal_at(
            key,
            xx,
            yy,
            period=max(8, settings.feature_px // 3),
            octaves=settings.octaves,
            persistence_permille=settings.persistence_permille,
        )
        # A broad longitudinal field shares the same seed and controls. Its saddles
        # can cross the full envelope; finer octaves form coastal islets and bays.
        profile = fractal_at(
            key,
            yy * 0,
            yy,
            period=max(8, settings.feature_px),
            octaves=settings.octaves,
            persistence_permille=settings.persistence_permille,
        )
        density = (
            1600
            - np.abs(xs - centre) * 3000 // half
            + (settings.land_permille - 250) * 3
            + (noise * 3 + profile * 3) * settings.wall_coast_permille // NOISE_SCALE
        )
        core = np.abs(xs - centre) <= max(1, half // 4)
        polar = (ys < settings.coast_margin_px) | (ys >= height - settings.coast_margin_px)
        solid = (density > 0) | (core & (polar | (settings.wall_allow_gaps == 0)))
        result[first : first + len(ys), left:right] = solid
    return result


def add_relief(
    elevation: NDArray[np.int32],
    land: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
) -> None:
    """Raise a meandering longitudinal spine while leaving habitable coastal shelves."""
    centre, half = geometry(domain, settings)
    xs = np.arange(domain.shape[1], dtype=np.int64)[None, :]
    for first in range(0, len(domain), STRIP_ROWS):
        checkpoint()
        rows = slice(first, min(len(domain), first + STRIP_ROWS))
        ys = np.arange(rows.start, rows.stop, dtype=np.int64)[:, None]
        noise = value_noise_at(derive_seed(seed, "wall_spine"), ys * 0, ys, max(8, half))
        spine = centre + noise * half // (6 * NOISE_SCALE)
        strength = np.maximum(0, half // 2 - np.abs(xs - spine))
        lift = strength * 18000 * settings.wall_ridge_permille // (max(1, half // 2) * PERMILLE)
        elevation[rows] += np.where(land[rows], lift, 0).astype(np.int32)
