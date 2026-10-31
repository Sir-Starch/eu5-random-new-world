"""Procedural north-south barrier with a guaranteed bent land core and coastal relief.

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
# The land share the Wall itself is sized for. A smaller share thins the side land only:
# the barrier takes its land first and the continents beside it share what is left.
BASE_LAND_PERMILLE = 250


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


def core(
    height: int, seed: int, centre: int, half: int, settings: NewWorldSettings
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Per-row centre column and half-width of the land that the barrier must always keep.

    The centre drifts and the width swells and narrows along the whole length, so a
    forced core is a bent, broad ridge of land rather than a ruler-straight strip. Both
    stay inside the envelope with room for the coastal jitter that `coast` adds; the width
    never falls below three tenths of the envelope's half-width, so the rows overlap.
    """
    ys = np.arange(height, dtype=np.int64)
    period = max(8, settings.feature_px)
    drift = value_noise_at(derive_seed(seed, "wall_core_drift"), ys * 0, ys, period)
    swell = value_noise_at(derive_seed(seed, "wall_core_swell"), ys * 0, ys, max(8, period // 2))
    middle = centre + drift * (3 * half) // (10 * NOISE_SCALE)
    reach = 3 * half // 10 + (swell + NOISE_SCALE) * half // (10 * NOISE_SCALE)
    return middle, reach


def spine(domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> NDArray[np.int64]:
    """The column of the guaranteed land core in every row."""
    centre, half = geometry(domain, settings)
    return core(domain.shape[0], seed, centre, half, settings)[0]


def coast(domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> NDArray[np.bool_]:
    """Threshold one continuous density field inside a straight continental envelope.

    Land share shifts sea level, feature size and octaves set the scale of bays and
    islands, and coastal irregularity controls their strength. A low-density saddle
    can become a strait when continuity is not required; no passages are placed.
    """
    centre, half = geometry(domain, settings)
    height, _ = domain.shape
    middle, reach = core(height, seed, centre, half, settings)
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
        across = np.abs(xs - centre)
        # Coastal noise fades over the envelope's outer quarter, so a coast eases toward its
        # edge instead of being cut off along a straight vertical line there.
        fade = np.clip((half - across) * 4 * PERMILLE // half, 0, PERMILLE)
        density = (
            1600
            - across * 3000 // half
            + (max(settings.land_permille, BASE_LAND_PERMILLE) - BASE_LAND_PERMILLE) * 3
            + (noise * 3 + profile * 3)
            * settings.wall_coast_permille
            * fade
            // (NOISE_SCALE * PERMILLE)
        )
        # The core's edge is ragged like any coast, within an eighth of the envelope.
        edge = np.clip(noise * half // (8 * NOISE_SCALE), -(half // 8), half // 8)
        kept = np.abs(xs - middle[ys]) <= reach[ys] + edge
        polar = (ys < settings.coast_margin_px) | (ys >= height - settings.coast_margin_px)
        solid = (density > 0) | (kept & (polar | (settings.wall_allow_gaps == 0)))
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
    half = geometry(domain, settings)[1]
    middle = spine(domain, seed, settings)
    xs = np.arange(domain.shape[1], dtype=np.int64)[None, :]
    for first in range(0, len(domain), STRIP_ROWS):
        checkpoint()
        rows = slice(first, min(len(domain), first + STRIP_ROWS))
        ys = np.arange(rows.start, rows.stop, dtype=np.int64)[:, None]
        noise = value_noise_at(derive_seed(seed, "wall_spine"), ys * 0, ys, max(8, half))
        ridge = middle[rows][:, None] + noise * half // (8 * NOISE_SCALE)
        strength = np.maximum(0, half // 2 - np.abs(xs - ridge))
        lift = strength * 18000 * settings.wall_ridge_permille // (max(1, half // 2) * PERMILLE)
        elevation[rows] += np.where(land[rows], lift, 0).astype(np.int32)
