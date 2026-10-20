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

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, block_mean, box_blur, smoothstep, upsample, warped_noise
from rnw.noise import NOISE_SCALE
from rnw.parallel import band_rows, worker_count
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
# Strips start on the noise lattice (the coarsest field samples every 16 pixels) and the
# foothill blur reaches FOOTHILL_RADIUS rows past a strip, a multiple of that step too.
STRIP_ALIGN: Final[int] = 16
STRIP_ROWS: Final[int] = 256
STRIP_FLOOR: Final[int] = 2 * FOOTHILL_RADIUS + STRIP_ALIGN
STRIP_WORKERS: Final[int] = 8
# Working memory of a strip window per pixel: a dozen arrays of eight-byte integers.
STRIP_BYTES: Final[int] = 140


def _field(  # noqa: PLR0913 - a field is defined by its stream, grid and octaves.
    seed: int,
    stream: str,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
    row0: int,
) -> NDArray[np.int64]:
    return warped_noise(
        derive_seed(seed, stream),
        shape,
        step=step,
        period=period,
        octaves=octaves,
        warp_px=period * WARP_PERMILLE // PERMILLE,
        row0=row0,
    )


def _ridged(seed: int, shape: tuple[int, int], row0: int) -> NDArray[np.int64]:
    """Ridged multi-octave noise in [0, 32768]: sharp crests where the noise crosses zero."""
    total = np.zeros(shape, dtype=np.int64)
    for period, weight in RIDGES:
        noise = _field(
            seed, f"relief_ridge_{period}", shape, step=2, period=period, octaves=1, row0=row0
        )
        crest = NOISE_SCALE - np.minimum(np.abs(noise), NOISE_SCALE)
        total += weight * (crest * crest // NOISE_SCALE)
    return total // sum(weight for _, weight in RIDGES)


def _inland_grid(land: NDArray[np.bool_], strip: int) -> NDArray[np.int64]:
    """Smooth Euclidean distance to the sea in eighths of a pixel on a coarse grid.

    A breadth-first step metric leaves streaks that steep slopes would turn into
    visible terraces, so the distance is exact on a grid ``DISTANCE_STEP`` coarser and
    interpolated back (``_inland``). Distances are capped at ``INLAND_LIMIT``. The grid is
    padded by one sample on the far sides, as the interpolation reads it.
    """
    step = DISTANCE_STEP
    rows, columns = (int(size) for size in land.shape)
    coarse = np.empty((-(-rows // step), -(-columns // step)), dtype=bool)
    for first in range(0, rows, strip):
        mean = block_mean(land[first : first + strip].astype(np.int64) * PERMILLE, step)
        coarse[first // step : first // step + mean.shape[0]] = mean >= PERMILLE // 2
    eighths = euclidean_distance(~coarse, INLAND_LIMIT // step)
    return np.pad(eighths * step, ((0, 1), (0, 1)), mode="edge")


def _relief_strip(
    land: NDArray[np.bool_],
    grid: NDArray[np.int64],
    seed: int,
    first: int,
    last: int,
) -> NDArray[np.int32]:
    """Height of rows ``first`` to ``last``, computed in a window that reaches the foothill
    blur past them; every field is a function of the pixel, so the window changes nothing.
    """
    rows, columns = (int(size) for size in land.shape)
    start, stop = max(0, first - FOOTHILL_RADIUS), min(rows, last + FOOTHILL_RADIUS)
    shape = (stop - start, columns)
    window = land[start:stop]
    lattice = start // DISTANCE_STEP
    inland = np.where(
        window,
        upsample(
            grid[lattice : lattice + (shape[0] - 1) // DISTANCE_STEP + 2],
            DISTANCE_STEP,
            shape,
        ),
        0,
    )
    broad = _field(seed, "relief_broad", shape, step=16, period=1600, octaves=3, row0=start)
    belts = _field(seed, "relief_belts", shape, step=8, period=1400, octaves=2, row0=start)
    belts += _field(seed, "relief_belt_edge", shape, step=4, period=220, octaves=3, row0=start) // 4
    width = _field(seed, "relief_belt_width", shape, step=16, period=900, octaves=2, row0=start)
    width = BELT_WIDTH * (PERMILLE + width * 2 * PERMILLE // (3 * NOISE_SCALE)) // PERMILLE
    presence = _field(seed, "relief_presence", shape, step=16, period=2400, octaves=2, row0=start)
    belt = np.clip(width - np.abs(belts), 0, None) * PERMILLE // np.maximum(width, 1)
    belt = smoothstep(belt, 0, PERMILLE)
    del belts, width
    strength = belt * smoothstep(presence, -3000, 6000) // PERMILLE
    del belt, presence
    mountain = strength * (
        MOUNTAIN_BASE + _ridged(seed, shape, start) * MOUNTAIN_PEAK // NOISE_SCALE
    )
    mountain //= PERMILLE
    hilly = _field(seed, "relief_hilly", shape, step=8, period=900, octaves=3, row0=start)
    foothill = box_blur(strength, FOOTHILL_RADIUS)
    hilliness = np.minimum(PERMILLE, smoothstep(hilly, -3000, 11000) + foothill * 3 // 2)
    del hilly, foothill
    hills_noise = _field(seed, "relief_hills", shape, step=4, period=128, octaves=4, row0=start)
    hills = hilliness * ((hills_noise + NOISE_SCALE) * HILL_HEIGHT // (2 * NOISE_SCALE))
    hills //= PERMILLE
    del hills_noise, hilliness
    plateau_noise = _field(
        seed, "relief_plateau", shape, step=8, period=1000, octaves=3, row0=start
    )
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
    core = slice(first - start, last - start)
    return np.where(window[core], height[core], 0).astype(np.int32)


def generate_relief(land: NDArray[np.bool_], *, seed: int) -> NDArray[np.int32]:
    """Height per pixel of ``land`` (0 on water), deterministic for a seed.

    The raster is cut into strips of ``STRIP_ROWS`` rows (a multiple of the coarsest noise
    step) that run on a few threads; the result is the same for any strip height and any
    number of threads, and the working memory is a few strips instead of a dozen rasters.
    """
    rows, columns = (int(size) for size in land.shape)
    workers = worker_count(STRIP_WORKERS, bytes_each=STRIP_BYTES * columns * STRIP_ROWS)
    height = band_rows(
        STRIP_BYTES * columns,
        workers=workers,
        floor=STRIP_FLOOR,
        ceiling=STRIP_ROWS + 2 * FOOTHILL_RADIUS,
    )
    strip = max(STRIP_ALIGN, (height - 2 * FOOTHILL_RADIUS) // STRIP_ALIGN * STRIP_ALIGN)
    grid = _inland_grid(land, strip)
    out = np.empty((rows, columns), dtype=np.int32)

    def run(first: int) -> None:
        last = min(rows, first + strip)
        out[first:last] = _relief_strip(land, grid, seed, first, last)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(run, range(0, rows, strip)):
            pass
    return out
