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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, block_mean, box_blur, smoothstep, upsample, warped_noise
from rnw.noise import NOISE_SCALE
from rnw.parallel import band_rows, worker_count
from rnw.progress import checkpoint
from rnw.rng import derive_seed
from rnw.topology import euclidean_distance, label_components, nearest_label

if TYPE_CHECKING:
    from numpy.typing import NDArray

COAST_HEIGHT: Final[int] = 5700

# Hills are rough ground (epoch 64, ``epoch.ROUGH_HILLS``, ``cell_roughness``): the bend
# of the height over ``HILL_STEP`` pixels (``strip_bend``), which no slope has. A spread about the
# plane that fits a whole cell grows with the cell, so once the cells were sized by the land the
# largest became hills: hills were 1.32 times the median location and 327 permille of the coastal
# locations hills, where the bend gives 1.08 and 280 (vanilla 0.83 and 254 in the Old World) on
# world gady3byywf [V-EXEC 2026-11-13].
HILL_STEP: Final[int] = 8
ROUGHNESS_ROWS: Final[int] = 1024  # rows of a strip read for ``cell_roughness``

INLAND_LIMIT: Final[int] = 320
DISTANCE_STEP: Final[int] = 4
INLAND_SLOPE: Final[int] = 2
BROAD_HEIGHT: Final[int] = 1300
MOUNTAIN_PEAK: Final[int] = 38000
HILL_HEIGHT: Final[int] = 5500
# Epoch 64 (``epoch.ROUGH_HILLS``): hill country spreads about the middle of its noise this many
# tenths as far as the structural relief has it (``generate_relief``'s ``spread``), once the
# drainage is planned (``basins.shape_relief``). Read on the height the decals show, the land at
# 8000 to 9500 had a bend of 214 to 220 (vanilla 322 to 411) and 136 and 188 permille of the
# locations of worlds gady3byywf and seed 42 were hills (vanilla 217, the Americas 228); with the
# spread (and the river beds 200 below the sea at their mouths) the bend is 279 to 304 and hills
# are 179 and 216, the rivers unchanged [V-EXEC 2026-11-14].
HILL_GAIN: Final[int] = 36
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
    ("relief_belts", 900, 130, 390, 1000),
    ("relief_belts2", 600, 83, 260, 950),
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
# Painted hints (``rnw.landmask``): how much of the ground a player marked as mountains,
# highlands or lowlands, in permille, on a grid of ``HINT_STEP`` pixels, smoothed over
# ``HINT_BLUR`` of its cells. A class is felt from ``HINT_LOW`` of coverage and complete at
# ``HINT_HIGH``, so a thin stroke still makes a range. Painted mountains stand at least
# ``PAINT_FLOOR`` permille of a chain's height, whatever the massif noise says there.
HINT_STEP: Final[int] = 8
HINT_BLUR: Final[int] = 2
HINT_LOW: Final[int] = 80
HINT_HIGH: Final[int] = 600
# Painted mountains have flanks as a chain has: a second, wider smoothing of the mountains'
# coverage (``FLANK_BLUR`` cells) falls off over ``FLANK_LOW`` to ``FLANK_HIGH``, and the range
# is made of the flank and the crest zone in the shares the chains' envelope has.
FLANK_BLUR: Final[int] = 8
FLANK_LOW: Final[int] = 20
FLANK_HIGH: Final[int] = 300
FLANK_SHARE: Final[int] = 450
PAINT_FLOOR: Final[int] = 450
HIGHLAND_PLATEAU: Final[int] = 550  # permille of a plateau's rise that painted highlands reach
HINT_BYTES: Final[int] = 40  # working memory of the three hint fields per pixel of a strip
# Active margins (epoch 64, ``epoch.CORDILLERAS``): the coasts of a landmass that face one way,
# which turns slowly across the map, are where its plate meets another. A cordillera stands
# ``CORDILLERA_AXIS`` pixels inland of them, and the land falls away from them by up to
# ``TILT_HEIGHT`` over ``TILT_REACH`` pixels, so its rivers run across the continent to the far
# coast instead of radially to the nearest one. The fields live on a grid of ``MARGIN_STEP``
# pixels: the land's density smoothed over ``MARGIN_BLUR`` of its cells gives each coast its
# facing, and the distance to an active coast is measured within the landmass that has it.
MARGIN_STEP: Final[int] = 16
MARGIN_BLUR: Final[int] = 10
MARGIN_TURN: Final[int] = 6000  # pixels over which the facing of the active coasts turns
MARGIN_LOCAL: Final[int] = 1400  # period of the noise that breaks an active stretch up
MARGIN_NOISE: Final[int] = 400  # permille of a cosine the local noise moves a coast by
MARGIN_BIAS: Final[int] = 450  # cosine (permille) a coast must face its plate's way by
MARGIN_FILL: Final[int] = 4  # coarse cells of water that take their nearest land cell's value
CORDILLERA_AXIS: Final[tuple[int, int]] = (100, 260)
CORDILLERA_CORE: Final[int] = 45
CORDILLERA_FLANK: Final[int] = 130
CORDILLERA_FLOOR: Final[int] = 520  # permille of the peak a cordillera holds at its lowest pass
TILT_HEIGHT: Final[int] = 1800
TILT_REACH: Final[int] = 2400
# Behind a cordillera lies its foreland, a broad plain the rivers cross: the inner chains there
# keep ``PERMILLE - FORELAND_DAMP`` of their strength between the two pairs of distances.
FORELAND_DAMP: Final[int] = 800
FORELAND: Final[tuple[int, int, int, int]] = (260, 460, 1400, 2200)


@dataclass(frozen=True, slots=True, eq=False)
class ReliefHints:
    """What a drawing asks of the ground beyond its outline, as three coverage grids.

    Each grid has ``ceil(rows / HINT_STEP) + 1`` rows and ``ceil(columns / HINT_STEP) + 1``
    columns, sample ``(i, j)`` at pixel ``(i * HINT_STEP, j * HINT_STEP)``, as the distance grid
    of ``_inland_grid`` does. Values are permille of coverage.
    """

    mountains: NDArray[np.int32]
    highlands: NDArray[np.int32]
    lowlands: NDArray[np.int32]
    flanks: NDArray[np.int32]

    def grids(
        self,
    ) -> tuple[NDArray[np.int32], NDArray[np.int32], NDArray[np.int32], NDArray[np.int32]]:
        return self.mountains, self.highlands, self.lowlands, self.flanks

    def fits(self, shape: tuple[int, int]) -> bool:
        """Whether the grids are those of a raster of ``shape``."""
        grid = (-(-shape[0] // HINT_STEP) + 1, -(-shape[1] // HINT_STEP) + 1)
        return all(found.shape == grid for found in self.grids())


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


def _margin_grid(land: NDArray[np.bool_], seed: int, strip: int) -> NDArray[np.int64]:
    """Distance to the nearest active coast of the same landmass, in eighths of a pixel, on a
    grid ``MARGIN_STEP`` coarser (capped at ``TILT_REACH``; padded as ``_inland_grid`` is).

    A coast is active where it faces the way of its plate: the cosine between its facing (down
    the slope of the smoothed land density, from land to sea) and a direction that a per-seed
    vector and two slow noises give, moved by a local noise, exceeds ``MARGIN_BIAS``. Integer
    arithmetic and square roots of exact integers only.
    """
    step = MARGIN_STEP
    rows, columns = (int(size) for size in land.shape)
    coarse = np.empty((-(-rows // step), -(-columns // step)), dtype=bool)
    for first in range(0, rows, strip):
        mean = block_mean(land[first : first + strip].astype(np.int64) * PERMILLE, step)
        coarse[first // step : first // step + mean.shape[0]] = mean >= PERMILLE // 2
    shape = (int(coarse.shape[0]), int(coarse.shape[1]))
    density = np.pad(box_blur(coarse.astype(np.int64) * PERMILLE, MARGIN_BLUR), 1, mode="edge")
    gx = density[1:-1, 2:] - density[1:-1, :-2]
    gy = density[2:, 1:-1] - density[:-2, 1:-1]
    del density
    turn = MARGIN_TURN // step
    hashed = derive_seed(seed, "relief_margin_plate")
    base_u = (hashed & 0xFFFF) - 0x8000
    base_v = ((hashed >> 16) & 0xFFFF) - 0x8000
    u = warped_noise(derive_seed(seed, "relief_margin_u"), shape, step=4, period=turn,
                     octaves=1, warp_px=0) + base_u  # fmt: skip
    v = warped_noise(derive_seed(seed, "relief_margin_v"), shape, step=4, period=turn,
                     octaves=1, warp_px=0) + base_v  # fmt: skip
    dot = -(gx * u + gy * v)
    norm = np.floor(np.sqrt((gx * gx + gy * gy).astype(np.float64))).astype(np.int64) * np.floor(
        np.sqrt((u * u + v * v).astype(np.float64))
    ).astype(np.int64)
    del gx, gy, u, v
    cosine = dot * PERMILLE // np.maximum(norm, 1)
    del dot, norm
    local = warped_noise(
        derive_seed(seed, "relief_margin_local"),
        shape,
        step=2,
        period=MARGIN_LOCAL // step,
        octaves=2,
        warp_px=MARGIN_LOCAL // step // 3,
    )
    activity = cosine + local * MARGIN_NOISE // NOISE_SCALE - MARGIN_BIAS
    del cosine, local
    padded = np.pad(coarse, 1, mode="edge")
    shore = coarse & ~(padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:])
    active = shore & (activity > 0)
    del padded, shore, activity
    # Each landmass measures from its own active coasts only, however near another's lie.
    limit = TILT_REACH // step
    parts = label_components(coarse.astype(np.int32))
    distance = np.full(shape, TILT_REACH * 8, dtype=np.int64)
    for part in np.unique(parts[active]).tolist():
        mine = parts == part
        near = euclidean_distance(active & mine, limit) * step
        distance = np.where(mine, np.minimum(near, TILT_REACH * 8), distance)
    del parts
    # A cell of mostly water takes the value of the nearest land cell, so the land pixels at a
    # coast read their own landmass's distance, not one blended towards the cap over the sea.
    cells = np.arange(coarse.size, dtype=np.int32).reshape(shape)
    nearest = nearest_label(np.where(coarse, cells, -1).astype(np.int32), coarse, MARGIN_FILL)
    del cells
    filled = np.where(nearest >= 0, distance.ravel()[np.maximum(nearest, 0)], TILT_REACH * 8)
    return np.pad(np.minimum(filled, TILT_REACH * 8), ((0, 1), (0, 1)), mode="edge")


def _cordillera(
    seed: int, shape: tuple[int, int], row0: int, near: NDArray[np.int64]
) -> NDArray[np.int64]:
    """Envelope in [0, 1000] of the cordillera that runs along the active coasts, its axis
    ``CORDILLERA_AXIS`` pixels inland; ``near`` is the distance to them in eighths of a pixel."""
    wander = _field(seed, "relief_cordillera", shape, step=16, period=1200, octaves=2, row0=row0)
    low, high = CORDILLERA_AXIS
    axis = low + (np.clip(wander, -NOISE_SCALE, NOISE_SCALE) + NOISE_SCALE) * (high - low) // (
        2 * NOISE_SCALE
    )
    del wander
    distance = np.abs(near - axis * 8)
    width = _field(
        seed, "relief_cordillera_width", shape, step=16, period=900, octaves=2, row0=row0
    )
    scale = PERMILLE + width * PERMILLE // (2 * NOISE_SCALE)
    del width
    inner = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(CORDILLERA_CORE * 8 * scale // PERMILLE, 1),
        0,
        PERMILLE,
    )
    outer = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(CORDILLERA_FLANK * 8 * scale // PERMILLE, 1),
        0,
        PERMILLE,
    )
    return (smoothstep(outer, 0, PERMILLE) * 450 + smoothstep(inner, 0, PERMILLE) * 550) // PERMILLE


def _strength(  # noqa: PLR0913, PLR0917 - the chains, the painted classes and the active coasts.
    seed: int,
    shape: tuple[int, int],
    row0: int,
    painted: NDArray[np.int64] | None = None,
    calm: NDArray[np.int64] | None = None,
    near: NDArray[np.int64] | None = None,
) -> NDArray[np.int64]:
    """How far the ground is mountain, in [0, 1000]: the chains' envelope and massif height.

    ``painted`` (mountains a player drew, in permille of a full range) raises it to at least
    ``PAINT_FLOOR`` of the massif's height there, and ``calm`` (lowlands) takes the generated
    chains out, so a painted range stands wherever it is drawn and no chain crosses a plain.
    ``near`` (the distance to the active coasts, ``_margin_grid``) adds their cordillera.
    """
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
    belt_height = (
        None
        if near is None
        else CORDILLERA_FLOOR
        + (PERMILLE - CORDILLERA_FLOOR) * smoothstep(massif, MASSIF_LOW, MASSIF_HIGH) // PERMILLE
    )
    del massif
    presence = _field(seed, "relief_presence", shape, step=16, period=2400, octaves=2, row0=row0)
    link = MASSIF_FLOOR + (PERMILLE - MASSIF_FLOOR) * smoothstep(presence, -6000, 5000) // PERMILLE
    natural = envelope * height // PERMILLE * link // PERMILLE
    if near is not None and belt_height is not None:
        rise, flat, fade, end = (distance * 8 for distance in FORELAND)
        foreland = (
            smoothstep(near, rise, flat) * (PERMILLE - smoothstep(near, fade, end)) // PERMILLE
        )
        natural = natural * (PERMILLE - FORELAND_DAMP * foreland // PERMILLE) // PERMILLE
        belt = _cordillera(seed, shape, row0, near) * belt_height // PERMILLE
        natural = np.maximum(natural, belt)
    if calm is not None:
        natural = natural * (PERMILLE - calm) // PERMILLE
    if painted is None:
        return natural
    raised = painted * (PAINT_FLOOR + (PERMILLE - PAINT_FLOOR) * height // PERMILLE) // PERMILLE
    return np.maximum(natural, raised)


def _hint_fields(
    hints: ReliefHints | None, start: int, shape: tuple[int, int]
) -> tuple[NDArray[np.int64] | None, NDArray[np.int64] | None, NDArray[np.int64] | None]:
    """The painted mountains, highlands and lowlands over the rows of a window, each in permille
    of the class it asks for (None for a class nothing was painted as); ``start`` lies on the
    hints' grid, since it is a multiple of the strips' alignment."""
    if hints is None:
        return None, None, None
    first = start // HINT_STEP
    needed = (shape[0] - 1) // HINT_STEP + 2
    fields: list[NDArray[np.int64] | None] = []
    for grid in hints.grids():
        window = grid[first : first + needed].astype(np.int64)
        fields.append(upsample(window, HINT_STEP, shape) if window.any() else None)
    crest, highlands, lowlands, flank = fields
    mountains = None
    if crest is not None and flank is not None:
        inner = smoothstep(crest, HINT_LOW, HINT_HIGH)
        outer = smoothstep(flank, FLANK_LOW, FLANK_HIGH)
        mountains = (outer * FLANK_SHARE + inner * (PERMILLE - FLANK_SHARE)) // PERMILLE
    return (
        mountains,
        None if highlands is None else smoothstep(highlands, HINT_LOW, HINT_HIGH),
        None if lowlands is None else smoothstep(lowlands, HINT_LOW, HINT_HIGH),
    )


def _relief_strip(  # noqa: PLR0913, PLR0915 - a strip reads the land, both distance grids, the seed and rows.
    land: NDArray[np.bool_],
    grid: NDArray[np.int64],
    sea_grid: NDArray[np.int64],
    lake_grid: NDArray[np.int64] | None,
    *,
    seed: int,
    first: int,
    last: int,
    hints: ReliefHints | None = None,
    margin_grid: NDArray[np.int64] | None = None,
    spread_out: NDArray[np.int16] | None = None,
) -> NDArray[np.int32]:
    """Height of rows ``first`` to ``last``, computed in a window that reaches ``HALO`` rows
    past them; every field is a function of the pixel, so the window changes nothing.
    ``margin_grid`` (``_margin_grid``) raises the active coasts' cordillera and tilt; the rows of
    ``spread_out`` receive the hill spread (``generate_relief``).
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
    painted, airy, calm = _hint_fields(hints, start, shape)
    near = None
    if margin_grid is not None:
        coarse = start // MARGIN_STEP
        needed = (shape[0] - 1) // MARGIN_STEP + 2
        near = upsample(margin_grid[coarse : coarse + needed], MARGIN_STEP, shape)
    strength = _strength(seed, shape, start, painted, calm, near)
    mountain = strength * (
        RIDGE_FLOOR + _ridged(seed, shape, start) * (PERMILLE - RIDGE_FLOOR) // PERMILLE
    )
    mountain = mountain // PERMILLE * MOUNTAIN_PEAK // PERMILLE
    hilly = _field(seed, "relief_hilly", shape, step=8, period=900, octaves=3, row0=start)
    foothill = box_blur(strength, FOOTHILL_RADIUS)
    hilliness = np.minimum(PERMILLE, smoothstep(hilly, -3000, 11000) + foothill * 3 // 2)
    del hilly, foothill
    if airy is not None:
        hilliness = np.maximum(hilliness, airy)
    if calm is not None:
        hilliness = hilliness * (PERMILLE - calm) // PERMILLE
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
    # The hills spread about the middle of their noise (``hill_spread``) by HILL_GAIN - 1 times.
    spread = (
        hilliness * ((hills_noise - NOISE_SCALE // 2) * HILL_HEIGHT // NOISE_SCALE) // PERMILLE
        if spread_out is not None
        else None
    )
    del hills_noise, hilliness
    plateau_noise = _field(
        seed, "relief_plateau", shape, step=8, period=1000, octaves=3, row0=start
    )
    plateau = smoothstep(plateau_noise, 9800, 14700)
    if airy is not None:
        plateau = np.maximum(plateau, airy * HIGHLAND_PLATEAU // PERMILLE)
    if calm is not None:
        plateau = plateau * (PERMILLE - calm) // PERMILLE
    plateau = plateau * (PERMILLE - strength) // PERMILLE
    plateau = plateau * PLATEAU_HEIGHT // PERMILLE
    del plateau_noise, strength
    base = COAST_HEIGHT + np.minimum(sea, INLAND_LIMIT * 8) * INLAND_SLOPE // 8
    broad_ramp = np.minimum(sea, BROAD_RAMP * 8) * PERMILLE // (BROAD_RAMP * 8)
    if near is not None:
        # The land falls away from an active coast across the continent.
        reach = TILT_REACH * 8
        tilt = TILT_HEIGHT * (reach - np.minimum(near, reach)) // reach
        base = base + tilt * broad_ramp // PERMILLE
        del tilt, near
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
    if spread_out is not None and spread is not None:
        # At most HILL_HEIGHT / 2 * (HILL_GAIN - 10) / 10 either way, well inside int16.
        spread = spread[core] * low_ramp[core] // PERMILLE * (HILL_GAIN - 10) // 10
        spread_out[first:last] = np.where(window[core], spread, 0)
    return np.where(window[core], height[core], 0).astype(np.int32)


def generate_relief(  # noqa: PLR0913 - the land, seed, lakes, drawing, margins and spread.
    land: NDArray[np.bool_],
    *,
    seed: int,
    lakes: NDArray[np.bool_] | None = None,
    hints: ReliefHints | None = None,
    margins: bool = False,
    spread: NDArray[np.int16] | None = None,
) -> NDArray[np.int32]:
    """Height per pixel of ``land`` (0 on water), deterministic for a seed.

    ``lakes`` are the enclosed waters inside the land: the distance to the sea, which sets the
    inland rise, reaches over them, and hills rise from their shores over ``LAKE_RAMP`` pixels.
    ``hints`` are the mountains, highlands and lowlands a player painted (``ReliefHints``): a
    painted range is raised from the same chains and crests as a generated one, painted
    highlands are hills and plateau, and lowlands are left flat. Without hints the relief is
    exactly what it was. With ``margins`` (epoch 64, ``epoch.CORDILLERAS``) the active coasts of
    each landmass raise a cordillera a little inland of them and tilt the land away. ``spread``
    (epoch 64, ``epoch.ROUGH_HILLS``), a raster of the land's shape, is filled with how far the
    hills would spread about the middle of their noise at ``HILL_GAIN`` (0 off the land), which
    ``basins.shape_relief`` adds once the drainage is planned.

    The raster is cut into strips of ``STRIP_ROWS`` rows (a multiple of the coarsest noise
    step) that run on a few threads; the result is the same for any strip height and any
    number of threads, and the working memory is a few strips instead of a dozen rasters.
    """
    rows, columns = (int(size) for size in land.shape)
    if hints is not None and not hints.fits(land.shape):
        message = "The relief hints are not those of this raster"
        raise ValueError(message)
    if spread is not None and spread.shape != land.shape:
        message = "The hill spread is not a raster of the land's shape"
        raise ValueError(message)
    weight = STRIP_BYTES + (HINT_BYTES if hints is not None else 0)
    workers = worker_count(STRIP_WORKERS, bytes_each=weight * columns * STRIP_ROWS)
    height = band_rows(
        weight * columns,
        workers=workers,
        floor=STRIP_FLOOR,
        ceiling=STRIP_ROWS + 2 * HALO,
    )
    strip = max(STRIP_ALIGN, (height - 2 * HALO) // STRIP_ALIGN * STRIP_ALIGN)
    grid = _inland_grid(land, strip)
    sea_grid = grid if lakes is None else _inland_grid(land | lakes, strip)
    lake_grid = None if lakes is None else _inland_grid(~lakes, strip)
    margin_grid = (
        _margin_grid(land if lakes is None else land | lakes, seed, strip) if margins else None
    )
    out = np.empty((rows, columns), dtype=np.int32)

    def run(first: int) -> None:
        checkpoint()
        last = min(rows, first + strip)
        out[first:last] = _relief_strip(
            land,
            grid,
            sea_grid,
            lake_grid,
            seed=seed,
            first=first,
            last=last,
            hints=hints,
            margin_grid=margin_grid,
            spread_out=spread,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(run, range(0, rows, strip)):
            pass
    return out


def strip_bend(
    land: NDArray[np.bool_], height: NDArray[np.integer], start: int, stop: int, rows: int
) -> NDArray[np.int64]:
    """The bend of every pixel of rows ``start`` to ``stop`` of a map of ``rows`` rows: the mean
    of ``|h(p + d) + h(p - d) - 2 h(p)|`` over ``d`` = ``HILL_STEP`` pixels along the row and the
    column whose two ends are land, -1 where neither is read. ``land`` and ``height`` hold the
    rows from ``max(0, start - HILL_STEP)`` to ``min(rows, stop + HILL_STEP)``; integers.
    """
    step = HILL_STEP
    low = max(0, start - step)
    columns = int(land.shape[1])
    values = height.astype(np.int64)
    inner = slice(start - low, stop - low)
    bend = np.zeros((stop - start, columns), dtype=np.int64)
    ends = np.zeros((stop - start, columns), dtype=np.int64)
    if columns > 2 * step:
        middle = slice(step, columns - step)
        both = land[inner, : -2 * step] & land[inner, 2 * step :]
        found = values[inner, 2 * step :] + values[inner, : -2 * step]
        found = np.abs(found - 2 * values[inner, middle])
        bend[:, middle] += np.where(both, found, 0)
        ends[:, middle] += both
    # Rows ``step`` away from the strip's own; the first and last ``step`` of the map have none.
    first, last = max(start, step), min(stop, rows - step)
    if first < last:
        here = slice(first - low, last - low)
        above = slice(first - step - low, last - step - low)
        below = slice(first + step - low, last + step - low)
        both = land[above] & land[below]
        found = np.abs(values[above] + values[below] - 2 * values[here])
        bend[first - start : last - start] += np.where(both, found, 0)
        ends[first - start : last - start] += both
    return np.where(ends > 0, bend // np.maximum(ends, 1), -1)


def land_blur(
    land: NDArray[np.bool_], height: NDArray[np.integer], radius: int
) -> NDArray[np.int64]:
    """The mean height of the land in the box of ``radius`` pixels round every land pixel, 0 off
    the land (``radius`` 0: the height itself). The edges of the window are replicated, so a row
    within ``radius`` of an edge that is not the map's reads short; read a window ``radius`` rows
    wider (``blurred_window``). Integers."""
    if radius <= 0:
        return np.where(land, height, 0).astype(np.int64)
    share = box_blur(land.astype(np.int64) * PERMILLE, radius)
    total = box_blur(np.where(land, height, 0).astype(np.int64) * PERMILLE, radius)
    return np.where(land, total // np.maximum(share, 1), 0)


def blurred_window(
    land: NDArray[np.bool_], height: NDArray[np.integer], low: int, high: int, radius: int
) -> NDArray[np.int64]:
    """Rows ``low`` to ``high`` of ``height`` blurred over the land (``land_blur``), read with
    ``radius`` more rows on each side, so they are the rows of the whole map's blur."""
    rows = int(land.shape[0])
    first, last = max(0, low - radius), min(rows, high + radius)
    blurred = land_blur(land[first:last], height[first:last], radius)
    return blurred[low - first : high - first]


def cell_roughness(
    labels: NDArray[np.int32],
    elevation: NDArray[np.integer],
    count: int,
    land: NDArray[np.bool_] | None = None,
    *,
    blur: int = 0,
) -> NDArray[np.int64]:
    """How rough each of the first ``count`` cells (the land cells) is: the mean bend of its
    height, ``|h(p + d) + h(p - d) - 2 h(p)|`` over ``d`` = ``HILL_STEP`` pixels along the rows and
    the columns, averaged over the directions whose two ends are land, then over the cell.

    A slope, as every cell rising from a coast has, does not bend; nor does the reading grow with
    the cell, as a spread about the cell's plane does. ``land`` marks the land pixels when the
    land cells are not simply the first ``count`` labels (vanilla's map, ``eu5_biomes.size_model``);
    a label of -1 is none. With ``blur`` the height is first blurred over the land
    (``land_blur``), so a fine texture that one map has and another lacks does not count.
    Integer arithmetic, a strip at a time.
    """
    rows = int(labels.shape[0])
    totals = np.zeros(count, dtype=np.int64)
    pixels = np.zeros(count, dtype=np.int64)
    on_map = (labels >= 0) & (labels < count) if land is None and blur else land
    for start in range(0, rows, ROUGHNESS_ROWS):
        checkpoint()
        stop = min(rows, start + ROUGHNESS_ROWS)
        low, high = max(0, start - HILL_STEP), min(rows, stop + HILL_STEP)
        block = labels[low:high]
        on_land = (block >= 0) & (block < count) if land is None else land[low:high]
        values = (
            elevation[low:high]
            if not blur or on_map is None
            else blurred_window(on_map, elevation, low, high, blur)
        )
        bend = strip_bend(on_land, values, start, stop, rows)
        cell = block[start - low : stop - low]
        keep = on_land[start - low : stop - low] & (cell >= 0) & (cell < count) & (bend >= 0)
        totals += np.bincount(cell[keep], weights=bend[keep], minlength=count).astype(np.int64)
        pixels += np.bincount(cell[keep], minlength=count)
    return totals // np.maximum(pixels, 1)
