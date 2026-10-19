"""Continuous relief for generated land: mountain belts, plateaus and hills.

Mountains follow belts, the zero lines of a low-frequency noise, so they form long
chains instead of blobs; a second noise switches belt segments on and off. Ridged
octaves give peaks and valleys inside the belts, foothills surround them, and smooth
plateaus and hill country fill the rest. Heights use EU5 decal height units: vanilla
land starts at about 5700 and Old World location means are about 6800 for flatland,
10000 for hills, 14600 for plateaus and 16000 for mountains [V-EXEC C48]. The same
field drives cell topography, wastelands and the rendered height decals.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, block_mean, box_blur, smoothstep, upsample, warped_noise
from rnw.noise import NOISE_SCALE
from rnw.rng import derive_seed
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray

COAST_HEIGHT: Final[int] = 5700
INLAND_LIMIT: Final[int] = 320
DISTANCE_STEP: Final[int] = 4
INLAND_SLOPE: Final[int] = 6
BROAD_HEIGHT: Final[int] = 1300
BELT_WIDTH: Final[int] = 6000
MOUNTAIN_BASE: Final[int] = 5000
MOUNTAIN_PEAK: Final[int] = 26000
HILL_HEIGHT: Final[int] = 4200
PLATEAU_HEIGHT: Final[int] = 6500
FOOTHILL_RADIUS: Final[int] = 48
BROAD_RAMP: Final[int] = 120
RELIEF_RAMP: Final[int] = 40
WARP_PERMILLE: Final[int] = 400
# (period in pixels, weight) of the ridged octaves inside mountain belts.
RIDGES: Final[tuple[tuple[int, int], ...]] = ((192, 5), (96, 3), (48, 2))


def _field(  # noqa: PLR0913 - a field is defined by its stream, grid and octaves.
    seed: int,
    stream: str,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
) -> NDArray[np.int64]:
    return warped_noise(
        derive_seed(seed, stream),
        shape,
        step=step,
        period=period,
        octaves=octaves,
        warp_px=period * WARP_PERMILLE // PERMILLE,
    )


def _ridged(seed: int, shape: tuple[int, int]) -> NDArray[np.int64]:
    """Ridged multi-octave noise in [0, 32768]: sharp crests where the noise crosses zero."""
    total = np.zeros(shape, dtype=np.int64)
    for period, weight in RIDGES:
        noise = _field(seed, f"relief_ridge_{period}", shape, step=2, period=period, octaves=1)
        crest = NOISE_SCALE - np.minimum(np.abs(noise), NOISE_SCALE)
        total += weight * (crest * crest // NOISE_SCALE)
    return total // sum(weight for _, weight in RIDGES)


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
    belts = _field(seed, "relief_belts", shape, step=8, period=1400, octaves=2)
    belts += _field(seed, "relief_belt_edge", shape, step=4, period=220, octaves=3) // 4
    width = _field(seed, "relief_belt_width", shape, step=16, period=900, octaves=2)
    width = BELT_WIDTH * (PERMILLE + width * 2 * PERMILLE // (3 * NOISE_SCALE)) // PERMILLE
    presence = _field(seed, "relief_presence", shape, step=16, period=2400, octaves=2)
    belt = np.clip(width - np.abs(belts), 0, None) * PERMILLE // np.maximum(width, 1)
    belt = smoothstep(belt, 0, PERMILLE)
    del belts, width
    strength = belt * smoothstep(presence, -3000, 6000) // PERMILLE
    del belt, presence
    mountain = strength * (MOUNTAIN_BASE + _ridged(seed, shape) * MOUNTAIN_PEAK // NOISE_SCALE)
    mountain //= PERMILLE
    hilly = _field(seed, "relief_hilly", shape, step=8, period=900, octaves=3)
    foothill = box_blur(strength, FOOTHILL_RADIUS)
    hilliness = np.minimum(PERMILLE, smoothstep(hilly, -3000, 11000) + foothill * 3 // 2)
    del hilly, foothill
    hills_noise = _field(seed, "relief_hills", shape, step=4, period=128, octaves=4)
    hills = hilliness * ((hills_noise + NOISE_SCALE) * HILL_HEIGHT // (2 * NOISE_SCALE))
    hills //= PERMILLE
    del hills_noise, hilliness
    plateau_noise = _field(seed, "relief_plateau", shape, step=8, period=1000, octaves=3)
    plateau = smoothstep(plateau_noise, 9800, 14700) * (PERMILLE - strength) // PERMILLE
    plateau = plateau * PLATEAU_HEIGHT // PERMILLE
    del plateau_noise, strength
    base = COAST_HEIGHT + np.minimum(inland, INLAND_LIMIT * 8) * INLAND_SLOPE // 8
    broad_ramp = np.minimum(inland, BROAD_RAMP * 8) * PERMILLE // (BROAD_RAMP * 8)
    relief_ramp = np.minimum(inland, RELIEF_RAMP * 8) * PERMILLE // (RELIEF_RAMP * 8)
    height = (
        base
        + broad * BROAD_HEIGHT // NOISE_SCALE * broad_ramp // PERMILLE
        + (mountain + hills + plateau) * relief_ramp // PERMILLE
    )
    height = np.maximum(height, COAST_HEIGHT)
    return np.where(land, height, 0).astype(np.int32)
