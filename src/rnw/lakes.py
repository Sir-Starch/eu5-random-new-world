"""Lakes inside generated land, sized and spread like the installed game's own.

Game-independent. A thresholded noise field leaves only accidental ponds: the installed
EU5 1.4.6 map has 11.2 lakes of at least 80 pixels per million land pixels, 0.78 % of its
land, with a heavy tail (a quarter of them 127-214 pixels, the 90th percentile 1,100, the
largest 22,692) [V-LOCAL 2026-10-30], while generated continents held 0.05-0.2 % and none
above 4,000 pixels. Here lake sites are drawn on a coarse grid by land area, each with a
size from that tail (a geometric choice of size steps of one quarter octave, a little
under 0.88 of the lakes passing each step, which is the vanilla Pareto exponent), an
elongation and an orientation. A lake is an ellipse with a noisy outline, kept a rim of
land away from every shore so it stays a lake and not a bay.

Everything is integer arithmetic on named SplitMix64 streams and hashed noise, so equal
inputs give equal lakes on every platform.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
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
SITE_BOOST_PERMILLE: Final[int] = 1_400
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
MAX_ELONGATION_PERMILLE: Final[int] = 2400
# The outline radius varies by this share of itself; the rim keeps clear of the largest
# value of that and of the lake's long radius.
OUTLINE_PERMILLE: Final[int] = 300
RIM_PERMILLE: Final[int] = 1450
RIM_PX: Final[int] = 14
# Rim distances reach 1.45 times the longest radius (about 130 pixels for a 22,000-pixel lake).
INLAND_LIMIT: Final[int] = 64


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


def _size(stream: SplitMix64, smallest: int) -> int:
    """A lake area: a geometric number of quarter-octave steps above ``smallest``."""
    step = 0
    while step < MAX_STEPS and stream.below(PERMILLE) < STEP_CHANCE_PERMILLE:
        step += 1
    within = PERMILLE + stream.below(STEP_SIZE[1] - STEP_SIZE[0])
    return smallest * STEP_SIZE[step] // PERMILLE * within // PERMILLE


def lake_sites(
    land: NDArray[np.bool_], seed: int, *, smallest: int, largest: int
) -> list[tuple[int, int, int, int, int, int]]:
    """Accepted sites as (row, column, long radius, short radius, orientation, key).

    The candidates of a ``CELL_PX`` square depend on its position and on the land inside
    it only; one that would reach within its rim of the shore is dropped.
    """
    rows, columns = (int(size) for size in land.shape)
    inland = _inland_px(land)
    per_cell = RATE_PERMILLE * SITE_BOOST_PERMILLE // PERMILLE
    key = derive_seed(seed, "lakes")
    sites: list[tuple[int, int, int, int, int, int]] = []
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
                rim = lake[0] * RIM_PERMILLE // PERMILLE + RIM_PX
                if int(inland[row // GRID_PX, column // GRID_PX]) >= rim:
                    sites.append((row, column, *lake, mix64(key ^ stream.next_u64())))
    return sites


def _lake(stream: SplitMix64, smallest: int, largest: int) -> tuple[int, int, int] | None:
    """Long radius, short radius and orientation of an elliptical lake; None above ``largest``.

    Larger draws are dropped, not capped, so the biggest lakes do not pile up at the limit.
    """
    area = _size(stream, smallest)
    if area > largest:
        return None
    elongation = PERMILLE + stream.below(MAX_ELONGATION_PERMILLE - PERMILLE)
    long_axis = math.isqrt(area * elongation // PI_PERMILLE)
    short_axis = math.isqrt(area * PERMILLE * PERMILLE // (elongation * PI_PERMILLE))
    return max(2, long_axis), max(2, short_axis), stream.below(len(COS))


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
    """The land pixels that become lakes, for a land mask; nothing outside land changes."""
    carve = np.zeros(land.shape, dtype=bool)
    rows, columns = (int(size) for size in land.shape)
    for row, column, long_axis, short_axis, angle, key in lake_sites(
        land, seed, smallest=smallest, largest=largest
    ):
        checkpoint()
        reach = long_axis * (PERMILLE + OUTLINE_PERMILLE) // PERMILLE + 2
        top, bottom = max(0, row - reach), min(rows, row + reach + 1)
        left, right = max(0, column - reach), min(columns, column + reach + 1)
        window = (slice(top, bottom), slice(left, right))
        inside = blob(window, (row, column), (long_axis, short_axis), angle, key)
        carve[window] |= inside & land[window]
    return carve
