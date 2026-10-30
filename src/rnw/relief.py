"""Continuous relief for generated land: mountain chains, hills and plateaus.

A mountain chain follows the zero line of a low-frequency noise. Dividing the noise by its
slope gives the distance to that line, so a chain keeps its width where the noise is flat (a
bare threshold swells into blobs there) and forks where two lines cross. A massif noise sets
how high each stretch rises, so ranges climb to peaks and fall to passes instead of holding
one height, and a second, narrower family of chains adds lower ranges between them. Ridged
octaves from 128 to 8 pixels, each weighed by the crest below it, give sharp peaks over
smooth valleys the way erosion does; foothills surround the chains and hill country and smooth
plateaus fill the rest. Heights use EU5 decal height units: vanilla land starts at about
5700 and Old World location means are about 6800 for flatland, 10000 for hills, 14600 for
plateaus and 16000 for mountains [V-EXEC C48]. The same field drives cell topography,
wastelands and the rendered height decals, and the installed mountain stamps (``eu5_mountains``)
follow its chains.
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
from rnw.progress import checkpoint
from rnw.rng import derive_seed
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray

COAST_HEIGHT: Final[int] = 5700
INLAND_LIMIT: Final[int] = 320
DISTANCE_STEP: Final[int] = 4
INLAND_SLOPE: Final[int] = 4
BROAD_HEIGHT: Final[int] = 1300
MOUNTAIN_PEAK: Final[int] = 28000
HILL_HEIGHT: Final[int] = 6800
PLATEAU_HEIGHT: Final[int] = 6500
FOOTHILL_RADIUS: Final[int] = 48
BROAD_RAMP: Final[int] = 120
RELIEF_RAMP: Final[int] = 40
LAKE_RAMP: Final[int] = 16  # pixels over which hills and plateaus rise from a lake's shore
WARP_PERMILLE: Final[int] = 400
# (stream, period of the axis noise, half-widths in pixels of the crest zone and of the whole
# chain, strength in permille) of each family of chains. A chain's own width wanders between
# half and three halves of these.
CHAINS: Final[tuple[tuple[str, int, int, int, int], ...]] = (
    ("relief_belts", 1100, 100, 300, 1000),
    ("relief_belts2", 700, 64, 200, 950),
)
AXIS_WANDER: Final[int] = 20  # a chain's axis is displaced by a finer noise a twentieth as strong
AXIS_WARP: Final[int] = 200
SLOPE_REACH: Final[int] = 8  # pixels each side of the central difference that measures the slope
SLOPE_BLUR: Final[int] = 10
SLOPE_FLOOR: Final[int] = 64  # sixteenths of a noise unit per pixel; caps a chain's swelling
# A noise that crosses zero more gently than this is no range: its zero lines are closed rings
# round a faint extreme, and a chain fades out between the two slopes.
SLOPE_FADE: Final[tuple[int, int]] = (100, 320)
# Massif heights, in permille of the peak, from the lowest stretch to the highest; the noise
# that sets them is smoothstepped between the two bounds.
MASSIF_FLOOR: Final[int] = 380
MASSIF_LOW: Final[int] = -9000
MASSIF_HIGH: Final[int] = 15000
RIDGE_FLOOR: Final[int] = 250  # permille of a chain's height that holds without any ridge
RIDGE_GAIN: Final[int] = 2000  # permille of the next octave a full crest lets through
RIDGE_WARP: Final[int] = 700
# (period in pixels, weight in permille) of the ridged octaves inside mountain chains.
RIDGES: Final[tuple[tuple[int, int], ...]] = (
    (128, 1000),
    (64, 800),
    (32, 600),
    (16, 450),
    (8, 300),
)
# Strips start on the noise lattice (the coarsest field samples every 16 pixels). A strip's
# window reaches HALO rows past it: the foothill blur (FOOTHILL_RADIUS) over a strength that
# itself reads the slope (SLOPE_REACH and SLOPE_BLUR rows away), rounded up to the lattice.
STRIP_ALIGN: Final[int] = 16
STRIP_ROWS: Final[int] = 256
HALO: Final[int] = 80
STRIP_FLOOR: Final[int] = 2 * HALO + STRIP_ALIGN
STRIP_WORKERS: Final[int] = 8
# Working memory of a strip window per pixel: about thirty arrays of eight-byte integers.
STRIP_BYTES: Final[int] = 240


def _field(  # noqa: PLR0913 - a field is defined by its stream, grid, octaves and warp.
    seed: int,
    stream: str,
    shape: tuple[int, int],
    *,
    step: int,
    period: int,
    octaves: int,
    row0: int,
    warp: int = WARP_PERMILLE,
) -> NDArray[np.int64]:
    return warped_noise(
        derive_seed(seed, stream),
        shape,
        step=step,
        period=period,
        octaves=octaves,
        warp_px=period * warp // PERMILLE,
        row0=row0,
    )


def _ridged(seed: int, shape: tuple[int, int], row0: int) -> NDArray[np.int64]:
    """Ridged multifractal in [0, 1000]: sharp crests where a noise crosses zero.

    Each octave's crest (one at the zero line, squared) lets a share of the next octave through,
    so fine ridges grow on high crests and the low ground between stays smooth.
    """
    total = np.zeros(shape, dtype=np.int64)
    weight = np.full(shape, PERMILLE, dtype=np.int64)
    for period, share in RIDGES:
        noise = _field(
            seed,
            f"relief_ridge_{period}",
            shape,
            step=2,
            period=period,
            octaves=1,
            row0=row0,
            warp=RIDGE_WARP,
        )
        crest = NOISE_SCALE - np.minimum(np.abs(noise), NOISE_SCALE)
        del noise
        crest = crest * crest // NOISE_SCALE
        total += crest * weight // PERMILLE * share // PERMILLE
        weight = np.minimum(PERMILLE, crest * RIDGE_GAIN // NOISE_SCALE)
        del crest
    shares = sum(share for _, share in RIDGES)
    return np.minimum(PERMILLE, total * PERMILLE * PERMILLE // (shares * NOISE_SCALE))


def _chain(  # noqa: PLR0913 - a chain is defined by its stream, window, period and widths.
    seed: int,
    stream: str,
    shape: tuple[int, int],
    row0: int,
    *,
    period: int,
    core: int,
    flank: int,
) -> NDArray[np.int64]:
    """Envelope in [0, 1000] of the chains along the zero line of one noise.

    Full across the crest zone, falling through the flanks; the distance is measured to the
    line itself (noise over slope), not by a threshold of the noise.
    """
    axis = _field(seed, stream, shape, step=8, period=period, octaves=2, row0=row0, warp=AXIS_WARP)
    wander = _field(seed, f"{stream}_edge", shape, step=4, period=260, octaves=3, row0=row0)
    reach = SLOPE_REACH
    padded = np.pad(axis, reach, mode="edge")
    dx = (
        (padded[reach:-reach, 2 * reach :] - padded[reach:-reach, : -2 * reach]) * 16 // (2 * reach)
    )
    dy = (
        (padded[2 * reach :, reach:-reach] - padded[: -2 * reach, reach:-reach]) * 16 // (2 * reach)
    )
    del padded
    slope = box_blur(np.sqrt(dx * dx + dy * dy).astype(np.int64), SLOPE_BLUR)
    del dx, dy
    distance = np.abs(axis + wander // AXIS_WANDER) * 256 // np.maximum(slope, SLOPE_FLOOR)
    decisive = smoothstep(slope, *SLOPE_FADE)
    del axis, wander, slope
    width = _field(seed, f"{stream}_width", shape, step=16, period=900, octaves=2, row0=row0)
    scale = PERMILLE + width * PERMILLE // (2 * NOISE_SCALE)
    del width
    inner = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(core * 16 * scale // PERMILLE, 1), 0, PERMILLE
    )
    outer = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(flank * 16 * scale // PERMILLE, 1), 0, PERMILLE
    )
    envelope = (
        smoothstep(outer, 0, PERMILLE) * 450 + smoothstep(inner, 0, PERMILLE) * 550
    ) // PERMILLE
    return envelope * decisive // PERMILLE


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


def _strength(seed: int, shape: tuple[int, int], row0: int) -> NDArray[np.int64]:
    """How far the ground is mountain, in [0, 1000]: the chains' envelope and massif height."""
    envelope = np.zeros(shape, dtype=np.int64)
    for stream, period, core, flank, share in CHAINS:
        chain = _chain(seed, stream, shape, row0, period=period, core=core, flank=flank)
        _ = np.maximum(envelope, chain * share // PERMILLE, out=envelope)
        del chain
    massif = _field(
        seed, "relief_massif", shape, step=16, period=520, octaves=3, row0=row0, warp=500
    )
    height = (
        MASSIF_FLOOR
        + (PERMILLE - MASSIF_FLOOR) * smoothstep(massif, MASSIF_LOW, MASSIF_HIGH) // PERMILLE
    )
    del massif
    presence = _field(seed, "relief_presence", shape, step=16, period=2400, octaves=2, row0=row0)
    link = MASSIF_FLOOR + (PERMILLE - MASSIF_FLOOR) * smoothstep(presence, -6000, 5000) // PERMILLE
    return envelope * height // PERMILLE * link // PERMILLE


def _relief_strip(  # noqa: PLR0913 - a strip reads the land, both distance grids, the seed and rows.
    land: NDArray[np.bool_],
    grid: NDArray[np.int64],
    sea_grid: NDArray[np.int64],
    lake_grid: NDArray[np.int64] | None,
    *,
    seed: int,
    first: int,
    last: int,
) -> NDArray[np.int32]:
    """Height of rows ``first`` to ``last``, computed in a window that reaches ``HALO`` rows
    past them; every field is a function of the pixel, so the window changes nothing.
    """
    rows, columns = (int(size) for size in land.shape)
    start, stop = max(0, first - HALO), min(rows, last + HALO)
    shape = (stop - start, columns)
    window = land[start:stop]
    lattice = start // DISTANCE_STEP
    rows_needed = (shape[0] - 1) // DISTANCE_STEP + 2
    # Mountains fade out at any shore. The base rise and the broad tilt follow the distance to
    # the sea alone, or each lake would stand in a cone, and hills and plateaus rise from a lake
    # over a short ramp, not a bowl of flat ground.
    inland = upsample(grid[lattice : lattice + rows_needed], DISTANCE_STEP, shape)
    sea = upsample(sea_grid[lattice : lattice + rows_needed], DISTANCE_STEP, shape)
    lake = (
        None
        if lake_grid is None
        else upsample(lake_grid[lattice : lattice + rows_needed], DISTANCE_STEP, shape)
    )
    broad = _field(seed, "relief_broad", shape, step=16, period=1600, octaves=3, row0=start)
    strength = _strength(seed, shape, start)
    mountain = strength * (
        RIDGE_FLOOR + _ridged(seed, shape, start) * (PERMILLE - RIDGE_FLOOR) // PERMILLE
    )
    mountain = mountain // PERMILLE * MOUNTAIN_PEAK // PERMILLE
    hilly = _field(seed, "relief_hilly", shape, step=8, period=900, octaves=3, row0=start)
    foothill = box_blur(strength, FOOTHILL_RADIUS)
    hilliness = np.minimum(PERMILLE, smoothstep(hilly, -3000, 11000) + foothill * 3 // 2)
    del hilly, foothill
    broad_hills = _field(
        seed, "relief_hills", shape, step=4, period=72, octaves=3, row0=start, warp=600
    )
    fine_hills = _field(
        seed, "relief_hills2", shape, step=2, period=20, octaves=2, row0=start, warp=500
    )
    hills_noise = (broad_hills + NOISE_SCALE) // 2 * 700 // PERMILLE + (
        fine_hills + NOISE_SCALE
    ) // 2 * 300 // PERMILLE
    del broad_hills, fine_hills
    hills = hilliness * (hills_noise * HILL_HEIGHT // NOISE_SCALE) // PERMILLE
    del hills_noise, hilliness
    plateau_noise = _field(
        seed, "relief_plateau", shape, step=8, period=1000, octaves=3, row0=start
    )
    plateau = smoothstep(plateau_noise, 9800, 14700) * (PERMILLE - strength) // PERMILLE
    plateau = plateau * PLATEAU_HEIGHT // PERMILLE
    del plateau_noise, strength
    base = COAST_HEIGHT + np.minimum(sea, INLAND_LIMIT * 8) * INLAND_SLOPE // 8
    broad_ramp = np.minimum(sea, BROAD_RAMP * 8) * PERMILLE // (BROAD_RAMP * 8)
    relief_ramp = np.minimum(inland, RELIEF_RAMP * 8) * PERMILLE // (RELIEF_RAMP * 8)
    low_ramp = relief_ramp
    if lake is not None:
        sea_ramp = np.minimum(sea, RELIEF_RAMP * 8) * PERMILLE // (RELIEF_RAMP * 8)
        low_ramp = np.minimum(
            sea_ramp, np.minimum(lake, LAKE_RAMP * 8) * PERMILLE // (LAKE_RAMP * 8)
        )
    height = (
        base
        + broad * BROAD_HEIGHT // NOISE_SCALE * broad_ramp // PERMILLE
        + mountain * relief_ramp // PERMILLE
        + (hills + plateau) * low_ramp // PERMILLE
    )
    height = np.maximum(height, COAST_HEIGHT)
    core = slice(first - start, last - start)
    return np.where(window[core], height[core], 0).astype(np.int32)


def generate_relief(
    land: NDArray[np.bool_], *, seed: int, lakes: NDArray[np.bool_] | None = None
) -> NDArray[np.int32]:
    """Height per pixel of ``land`` (0 on water), deterministic for a seed.

    ``lakes`` are the enclosed waters inside the land: the distance to the sea, which sets the
    inland rise, reaches over them, and hills rise from their shores over ``LAKE_RAMP`` pixels.

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
        ceiling=STRIP_ROWS + 2 * HALO,
    )
    strip = max(STRIP_ALIGN, (height - 2 * HALO) // STRIP_ALIGN * STRIP_ALIGN)
    grid = _inland_grid(land, strip)
    sea_grid = grid if lakes is None else _inland_grid(land | lakes, strip)
    lake_grid = None if lakes is None else _inland_grid(~lakes, strip)
    out = np.empty((rows, columns), dtype=np.int32)

    def run(first: int) -> None:
        checkpoint()
        last = min(rows, first + strip)
        out[first:last] = _relief_strip(
            land, grid, sea_grid, lake_grid, seed=seed, first=first, last=last
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(run, range(0, rows, strip)):
            pass
    return out
