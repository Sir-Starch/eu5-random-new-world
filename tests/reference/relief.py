"""Whole-raster relief: the specification of the strip-by-strip ``rnw.relief.generate_relief``.

Moved from ``rnw.relief`` when the relief went strip by strip (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.fields import PERMILLE, block_mean, box_blur, smoothstep, upsample, warped_noise
from rnw.noise import NOISE_SCALE
from rnw.relief import (
    AXIS_WANDER,
    AXIS_WARP,
    BROAD_HEIGHT,
    BROAD_RAMP,
    CHAINS,
    COAST_HEIGHT,
    DISTANCE_STEP,
    FOOTHILL_RADIUS,
    HILL_HEIGHT,
    INLAND_LIMIT,
    INLAND_SLOPE,
    MASSIF_FLOOR,
    MASSIF_HIGH,
    MASSIF_LOW,
    MOUNTAIN_PEAK,
    PLATEAU_HEIGHT,
    RELIEF_RAMP,
    RIDGE_FLOOR,
    RIDGE_GAIN,
    RIDGE_WARP,
    RIDGES,
    SLOPE_BLUR,
    SLOPE_FADE,
    SLOPE_FLOOR,
    SLOPE_REACH,
    WARP_PERMILLE,
)
from rnw.rng import derive_seed
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _field(  # noqa: PLR0913 - a field is defined by its stream, grid, octaves and warp.
    seed: int,
    stream: str,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
    warp: int = WARP_PERMILLE,
) -> NDArray[np.int64]:
    return warped_noise(
        derive_seed(seed, stream),
        shape,
        step=step,
        period=period,
        octaves=octaves,
        warp_px=period * warp // PERMILLE,
    )


def _ridged(seed: int, shape: tuple[int, int]) -> NDArray[np.int64]:
    """Ridged multifractal in [0, 1000]: each octave's crest weighs the next one."""
    total = np.zeros(shape, dtype=np.int64)
    weight = np.full(shape, PERMILLE, dtype=np.int64)
    for period, share in RIDGES:
        noise = _field(
            seed, f"relief_ridge_{period}", shape, step=2, period=period, octaves=1, warp=RIDGE_WARP
        )
        crest = NOISE_SCALE - np.minimum(np.abs(noise), NOISE_SCALE)
        crest = crest * crest // NOISE_SCALE
        total += crest * weight // PERMILLE * share // PERMILLE
        weight = np.minimum(PERMILLE, crest * RIDGE_GAIN // NOISE_SCALE)
    shares = sum(share for _, share in RIDGES)
    return np.minimum(PERMILLE, total * PERMILLE * PERMILLE // (shares * NOISE_SCALE))


def _chain(  # noqa: PLR0913 - a chain is defined by its stream, grid, period and widths.
    seed: int, stream: str, shape: tuple[int, int], *, period: int, core: int, flank: int
) -> NDArray[np.int64]:
    """Envelope in [0, 1000] of the chains along the zero line of one noise."""
    axis = _field(seed, stream, shape, step=8, period=period, octaves=2, warp=AXIS_WARP)
    wander = _field(seed, f"{stream}_edge", shape, step=4, period=260, octaves=3)
    padded = np.pad(axis, SLOPE_REACH, mode="edge")
    reach = SLOPE_REACH
    dx = (
        (padded[reach:-reach, 2 * reach :] - padded[reach:-reach, : -2 * reach]) * 16 // (2 * reach)
    )
    dy = (
        (padded[2 * reach :, reach:-reach] - padded[: -2 * reach, reach:-reach]) * 16 // (2 * reach)
    )
    slope = box_blur(np.sqrt(dx * dx + dy * dy).astype(np.int64), SLOPE_BLUR)
    distance = np.abs(axis + wander // AXIS_WANDER) * 256 // np.maximum(slope, SLOPE_FLOOR)
    decisive = smoothstep(slope, *SLOPE_FADE)
    width = _field(seed, f"{stream}_width", shape, step=16, period=900, octaves=2)
    scale = PERMILLE + width * PERMILLE // (2 * NOISE_SCALE)
    crest_zone = np.maximum(core * 16 * scale // PERMILLE, 1)
    whole = np.maximum(flank * 16 * scale // PERMILLE, 1)
    inner = np.clip(PERMILLE - distance * PERMILLE // crest_zone, 0, PERMILLE)
    outer = np.clip(PERMILLE - distance * PERMILLE // whole, 0, PERMILLE)
    envelope = (
        smoothstep(outer, 0, PERMILLE) * 450 + smoothstep(inner, 0, PERMILLE) * 550
    ) // PERMILLE
    return envelope * decisive // PERMILLE


def _inland(land: NDArray[np.bool_]) -> NDArray[np.int64]:
    """Smooth Euclidean distance to the sea in eighths of a pixel, from a coarse grid.

    A breadth-first step metric leaves streaks that steep slopes would turn into
    visible terraces, so the distance is exact on a grid ``DISTANCE_STEP`` coarser and
    interpolated back. Distances are capped at ``INLAND_LIMIT``.
    """
    shape = (int(land.shape[0]), int(land.shape[1]))
    step = DISTANCE_STEP
    coarse = block_mean(land.astype(np.int64) * PERMILLE, step) >= PERMILLE // 2
    eighths = euclidean_distance(~coarse, INLAND_LIMIT // step)
    padded = np.pad(eighths * step, ((0, 1), (0, 1)), mode="edge")
    return np.where(land, upsample(padded, step, shape), 0)


def generate_relief(land: NDArray[np.bool_], *, seed: int) -> NDArray[np.int32]:
    """Height per pixel of ``land`` (0 on water), deterministic for a seed."""
    shape = (int(land.shape[0]), int(land.shape[1]))
    inland = _inland(land)
    broad = _field(seed, "relief_broad", shape, step=16, period=1600, octaves=3)
    envelope = np.zeros(shape, dtype=np.int64)
    for stream, period, core, flank, share in CHAINS:
        chain = _chain(seed, stream, shape, period=period, core=core, flank=flank)
        envelope = np.maximum(envelope, chain * share // PERMILLE)
    massif = _field(seed, "relief_massif", shape, step=16, period=520, octaves=3, warp=500)
    height = (
        MASSIF_FLOOR
        + (PERMILLE - MASSIF_FLOOR) * smoothstep(massif, MASSIF_LOW, MASSIF_HIGH) // PERMILLE
    )
    presence = _field(seed, "relief_presence", shape, step=16, period=2400, octaves=2)
    link = MASSIF_FLOOR + (PERMILLE - MASSIF_FLOOR) * smoothstep(presence, -6000, 5000) // PERMILLE
    strength = envelope * height // PERMILLE * link // PERMILLE
    mountain = strength * (
        RIDGE_FLOOR + _ridged(seed, shape) * (PERMILLE - RIDGE_FLOOR) // PERMILLE
    )
    mountain = mountain // PERMILLE * MOUNTAIN_PEAK // PERMILLE
    hilly = _field(seed, "relief_hilly", shape, step=8, period=900, octaves=3)
    foothill = box_blur(strength, FOOTHILL_RADIUS)
    hilliness = np.minimum(PERMILLE, smoothstep(hilly, -3000, 11000) + foothill * 3 // 2)
    broad_hills = _field(seed, "relief_hills", shape, step=4, period=72, octaves=3, warp=600)
    fine_hills = _field(seed, "relief_hills2", shape, step=2, period=20, octaves=2, warp=500)
    hills_noise = (broad_hills + NOISE_SCALE) // 2 * 700 // PERMILLE + (
        fine_hills + NOISE_SCALE
    ) // 2 * 300 // PERMILLE
    hills = hilliness * (hills_noise * HILL_HEIGHT // NOISE_SCALE) // PERMILLE
    plateau_noise = _field(seed, "relief_plateau", shape, step=8, period=1000, octaves=3)
    plateau = smoothstep(plateau_noise, 9800, 14700) * (PERMILLE - strength) // PERMILLE
    plateau = plateau * PLATEAU_HEIGHT // PERMILLE
    base = COAST_HEIGHT + np.minimum(inland, INLAND_LIMIT * 8) * INLAND_SLOPE // 8
    broad_ramp = np.minimum(inland, BROAD_RAMP * 8) * PERMILLE // (BROAD_RAMP * 8)
    relief_ramp = np.minimum(inland, RELIEF_RAMP * 8) * PERMILLE // (RELIEF_RAMP * 8)
    result = (
        base
        + broad * BROAD_HEIGHT // NOISE_SCALE * broad_ramp // PERMILLE
        + (mountain + hills + plateau) * relief_ramp // PERMILLE
    )
    result = np.maximum(result, COAST_HEIGHT)
    return np.where(land, result, 0).astype(np.int32)
