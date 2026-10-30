"""Lakes inside generated land, sized and spread like the installed game's own.

Game-independent. A thresholded noise field leaves only accidental ponds: the installed
EU5 1.4.6 map has 11.2 lakes of at least 80 pixels per million land pixels, 0.78 % of its
land, with a heavy tail (a quarter of them 127-214 pixels, the 90th percentile 1,100, the
largest 22,692) [V-LOCAL 2026-10-30], while generated continents held 0.05-0.2 % and none
above 4,000 pixels. Here lake sites are drawn on a coarse grid by land area, each with a
size from that tail (a geometric choice of size steps of one quarter octave, a little
under 0.88 of the lakes passing each step, which is the vanilla Pareto exponent), an
elongation and an orientation. The area is exact; the shape is not an ellipse with a rough
edge, which reads as a crater. A lake is the part of a warped ellipse where a fractal noise
lifts a bowl-shaped envelope above a level chosen to leave exactly that area, so it has
lobes, bays, headlands, sinuous arms and sometimes islands, more or less as the noise
(``complexity``) outweighs the bowl; some are narrow fingers. It keeps a rim of land away
from every shore so it stays a lake and not a bay.

Everything is integer arithmetic on named SplitMix64 streams and hashed noise, so equal
inputs give equal lakes on every platform.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, SUBPIXEL, block_mean, fractal_at
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import SplitMix64, derive_seed, mix64
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Sites are drawn per square of the land; distance to the shore is read on a coarser grid.
CELL_PX: Final[int] = 256
GRID_PX: Final[int] = 4
STRIP_ROWS: Final[int] = 1024
# Lakes per million land pixels (in permille) that reach the smallest lake size; the
# vanilla 11.2 for 80 pixels, with some drawn sites lost to the rim rule below.
RATE_PERMILLE: Final[int] = 11_200
SITE_BOOST_PERMILLE: Final[int] = 1_100
# Share of lakes passing each quarter-octave size step (2 ** (-0.875 / 4)).
STEP_CHANCE_PERMILLE: Final[int] = 859
MAX_STEPS: Final[int] = 43
# round(1000 * 2 ** (step / 4)).
STEP_SIZE: Final[tuple[int, ...]] = (
    1000, 1189, 1414, 1682, 2000, 2378, 2828, 3364, 4000, 4757, 5657, 6727, 8000, 9514, 11314,
    13454, 16000, 19027, 22627, 26909, 32000, 38055, 45255, 53817, 64000, 76109, 90510, 107635,
    128000, 152219, 181019, 215269, 256000, 304437, 362039, 430539, 512000, 608874, 724077,
    861078, 1024000, 1217748, 1448155, 1722156,
)  # fmt: skip
# (cos, sin) * 1024 of sixteen orientations over half a turn.
COS: Final[tuple[int, ...]] = (
    1024, 1004, 946, 851, 724, 569, 392, 200, 0, -200, -392, -569, -724, -851, -946, -1004,
)  # fmt: skip
SIN: Final[tuple[int, ...]] = (
    0, 200, 392, 569, 724, 851, 946, 1004, 1024, 1004, 946, 851, 724, 569, 392, 200,
)  # fmt: skip
ANGLE_SCALE: Final[int] = 1024
PI_PERMILLE: Final[int] = 3142
# The outline radius of a ``blob`` varies by this share of itself.
OUTLINE_PERMILLE: Final[int] = 300
RIM_PX: Final[int] = 14
INLAND_LIMIT: Final[int] = 64
# A lake never reaches beyond this share of its ellipse's squared radius, whatever the noise.
BOUND_PERMILLE: Final[int] = 2800
# Fractal octaves of a lake's outline and their persistence: a shore as ragged as a coast.
SHAPE_OCTAVES: Final[int] = 6
SHAPE_PERSISTENCE_PERMILLE: Final[int] = 580
# Fractal noise stays within about a third of its range, so it is scaled up before it is
# weighed against the bowl; its lobes are this share of the short radius across.
NOISE_GAIN: Final[int] = 4
LOBE_PERMILLE: Final[int] = 600
FINGER_PERMILLE: Final[int] = 120
COMPLEX_PERMILLE: Final[int] = 400


def _inland_px(land: NDArray[np.bool_]) -> NDArray[np.int32]:
    """Distance from each ``GRID_PX`` block of land to the nearest water block, in pixels."""
    rows, columns = (int(size) for size in land.shape)
    coarse = np.empty((-(-rows // GRID_PX), -(-columns // GRID_PX)), dtype=bool)
    for first in range(0, rows, STRIP_ROWS):
        checkpoint()
        mean = block_mean(land[first : first + STRIP_ROWS].astype(np.int64) * PERMILLE, GRID_PX)
        coarse[first // GRID_PX : first // GRID_PX + mean.shape[0]] = mean >= PERMILLE // 2
    eighths = euclidean_distance(~coarse, INLAND_LIMIT)
    return (eighths * GRID_PX // 8).astype(np.int32)


@dataclass(frozen=True, slots=True)
class Lake:
    """One lake to draw: where, how large, and the shape of its bowl and its noise.

    ``complexity`` is the weight of the noise against the bowl, in permille of the bowl's
    depth at its middle, and ``warp`` the bend of the whole in permille of the short radius.
    """

    row: int
    column: int
    area: int
    long_axis: int
    short_axis: int
    angle: int
    complexity: int
    warp: int
    key: int


def _size(stream: SplitMix64, smallest: int) -> int:
    """A lake area: a geometric number of quarter-octave steps above ``smallest``."""
    step = 0
    while step < MAX_STEPS and stream.below(PERMILLE) < STEP_CHANCE_PERMILLE:
        step += 1
    within = PERMILLE + stream.below(STEP_SIZE[1] - STEP_SIZE[0])
    return smallest * STEP_SIZE[step] // PERMILLE * within // PERMILLE


def _lake(
    stream: SplitMix64, smallest: int, largest: int
) -> tuple[int, int, int, int, int, int] | None:
    """Area, radii, orientation, complexity and warp of a lake; None above ``largest``.

    Larger draws are dropped, not capped, so the biggest lakes do not pile up at the limit.
    About an eighth are fingers (long, sinuous and fairly smooth), two fifths of the rest
    tangled and the others between.
    """
    area = _size(stream, smallest)
    kind = stream.below(PERMILLE)
    if kind < FINGER_PERMILLE:
        elongation = 3000 + stream.below(3000)
        complexity, warp = 350 + stream.below(300), 600 + stream.below(300)
    elif kind < COMPLEX_PERMILLE:
        elongation = PERMILLE + stream.below(1200)
        complexity, warp = 900 + stream.below(700), 450 + stream.below(300)
    else:
        elongation = PERMILLE + stream.below(1400)
        complexity, warp = 500 + stream.below(500), 300 + stream.below(300)
    angle = stream.below(len(COS))
    if area > largest:
        return None
    long_axis = math.isqrt(area * elongation // PI_PERMILLE)
    short_axis = math.isqrt(area * PERMILLE * PERMILLE // (elongation * PI_PERMILLE))
    return area, max(2, long_axis), max(2, short_axis), angle, complexity, warp


def lake_sites(
    land: NDArray[np.bool_],
    seed: int,
    *,
    smallest: int,
    largest: int,
    inland: NDArray[np.int32] | None = None,
) -> list[Lake]:
    """The lakes to try, in order; one that would reach the shore is dropped by ``carve_lakes``.

    The candidates of a ``CELL_PX`` square depend on its position and on the land inside it
    only. A candidate whose middle is nearer the shore than its rim and half its width is
    dropped here, as it cannot fit.
    """
    rows, columns = (int(size) for size in land.shape)
    if inland is None:
        inland = _inland_px(land)
    per_cell = RATE_PERMILLE * SITE_BOOST_PERMILLE // PERMILLE
    key = derive_seed(seed, "lakes")
    sites: list[Lake] = []
    for top in range(0, rows, CELL_PX):
        checkpoint()
        for left in range(0, columns, CELL_PX):
            block = inland[
                top // GRID_PX : (top + CELL_PX) // GRID_PX,
                left // GRID_PX : (left + CELL_PX) // GRID_PX,
            ]
            area = int(np.count_nonzero(block > 0)) * GRID_PX * GRID_PX
            if not area:
                continue
            stream = SplitMix64(mix64(key ^ (top << 32) ^ left))
            # Expected lakes in this square, in millionths of a lake per land pixel.
            expected = area * per_cell // PERMILLE
            count, rest = divmod(expected, 1_000_000)
            count += stream.below(1_000_000) < rest
            for _ in range(count):
                row = top + stream.below(CELL_PX)
                column = left + stream.below(CELL_PX)
                lake = _lake(stream, smallest, largest)
                if lake is None or row >= rows or column >= columns:
                    continue
                area_px, long_axis, short_axis, angle, complexity, warp = lake
                if int(inland[row // GRID_PX, column // GRID_PX]) >= RIM_PX + short_axis // 2:
                    sites.append(
                        Lake(
                            row,
                            column,
                            area_px,
                            long_axis,
                            short_axis,
                            angle,
                            complexity,
                            warp,
                            mix64(key ^ stream.next_u64()),
                        )
                    )
    return sites


def lake_window(lake: Lake, shape: tuple[int, int]) -> tuple[slice, slice]:
    """The pixels a lake can reach: the bound on its ellipse and the bend, clipped to ``shape``."""
    bend = lake.short_axis * lake.warp // PERMILLE
    reach = math.isqrt(BOUND_PERMILLE * lake.long_axis * lake.long_axis // PERMILLE) + 2 * bend + 2
    return (
        slice(max(0, lake.row - reach), min(shape[0], lake.row + reach + 1)),
        slice(max(0, lake.column - reach), min(shape[1], lake.column + reach + 1)),
    )


def lake_shape(lake: Lake, window: tuple[slice, slice]) -> NDArray[np.bool_]:
    """The pixels of ``lake`` inside ``window``: exactly its area when the window holds it.

    Coordinates are bent by two smooth noises; in the bent coordinates a bowl (one at the
    ellipse's middle, zero on its rim, below zero outside) plus ``complexity`` times a
    fractal noise forms a field, and the lake is the ``area`` pixels where that field is
    highest, within the bound that keeps it near its ellipse.
    """
    ys, xs = np.mgrid[window].astype(np.int64)
    period = max(8, lake.short_axis * LOBE_PERMILLE // PERMILLE)
    bend = lake.short_axis * lake.warp // PERMILLE
    bent_x = xs + (
        fractal_at(
            mix64(lake.key ^ 0x57A1),
            xs * SUBPIXEL,
            ys * SUBPIXEL,
            period=2 * period,
            octaves=2,
            persistence_permille=500,
        )
        * bend
        // NOISE_SCALE
    )
    bent_y = ys + (
        fractal_at(
            mix64(lake.key ^ 0x57A2),
            xs * SUBPIXEL,
            ys * SUBPIXEL,
            period=2 * period,
            octaves=2,
            persistence_permille=500,
        )
        * bend
        // NOISE_SCALE
    )
    dy, dx = bent_y - lake.row, bent_x - lake.column
    along = (dx * COS[lake.angle] + dy * SIN[lake.angle]) // ANGLE_SCALE
    across = (dy * COS[lake.angle] - dx * SIN[lake.angle]) // ANGLE_SCALE
    long_sq, short_sq = lake.long_axis * lake.long_axis, lake.short_axis * lake.short_axis
    squared = along * along * short_sq + across * across * long_sq
    bowl = PERMILLE - PERMILLE * squared // (long_sq * short_sq)
    noise = fractal_at(
        lake.key,
        bent_x * SUBPIXEL,
        bent_y * SUBPIXEL,
        period=period,
        octaves=SHAPE_OCTAVES,
        persistence_permille=SHAPE_PERSISTENCE_PERMILLE,
    )
    field = bowl + NOISE_GAIN * lake.complexity * noise // NOISE_SCALE
    near = squared * PERMILLE <= BOUND_PERMILLE * long_sq * short_sq
    count = int(np.count_nonzero(near))
    take = min(lake.area, count)
    if take <= 0:
        return np.zeros(near.shape, dtype=bool)
    values = field[near]
    level = int(np.partition(values, count - take)[count - take])
    return near & (field >= level)


def blob(  # noqa: PLR0913 - a blob is a window, a centre, two radii, an angle and its noise.
    window: tuple[slice, slice],
    centre: tuple[int, int],
    axes: tuple[int, int],
    angle: int,
    key: int,
    *,
    outline_permille: int = OUTLINE_PERMILLE,
    octaves: int = 3,
    persistence_permille: int = 500,
) -> NDArray[np.bool_]:
    """An ellipse with a noisy outline, on the pixels ``window`` of a raster.

    ``axes`` are the long and short radius, ``angle`` indexes ``COS``/``SIN`` and the outline
    radius varies by up to ``outline_permille`` of itself, with a period of the short radius
    and finer octaves down to a short radius over ``2 ** (octaves - 1)``.
    """
    ys, xs = np.mgrid[window].astype(np.int64)
    long_axis, short_axis = axes
    dy, dx = ys - centre[0], xs - centre[1]
    along = (dx * COS[angle] + dy * SIN[angle]) // ANGLE_SCALE
    across = (dy * COS[angle] - dx * SIN[angle]) // ANGLE_SCALE
    noise = fractal_at(
        key,
        xs * SUBPIXEL,
        ys * SUBPIXEL,
        period=max(8, short_axis),
        octaves=octaves,
        persistence_permille=persistence_permille,
    )
    scale = PERMILLE + outline_permille * noise // NOISE_SCALE
    return (along * along * short_axis * short_axis + across * across * long_axis * long_axis) * (
        PERMILLE * PERMILLE
    ) < (long_axis * short_axis * scale) ** 2


def carve_lakes(
    land: NDArray[np.bool_], seed: int, *, smallest: int, largest: int
) -> NDArray[np.bool_]:
    """The land pixels that become lakes, for a land mask; nothing outside land changes.

    A lake whose shape would come within ``RIM_PX`` of water, or whose area the land cannot
    hold, is not drawn.
    """
    carve = np.zeros(land.shape, dtype=bool)
    inland = _inland_px(land)
    shape = (int(land.shape[0]), int(land.shape[1]))
    for lake in lake_sites(land, seed, smallest=smallest, largest=largest, inland=inland):
        checkpoint()
        window = lake_window(lake, shape)
        inside = lake_shape(lake, window)
        ys, xs = np.nonzero(inside)
        near = inland[(ys + window[0].start) // GRID_PX, (xs + window[1].start) // GRID_PX]
        if ys.size and int(near.min()) >= RIM_PX:
            carve[window] |= inside & land[window]
    return carve
