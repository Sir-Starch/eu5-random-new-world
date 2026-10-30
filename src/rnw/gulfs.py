"""Inland seas, gulfs and lagoons: water a thresholded coast noise does not make.

Game-independent. Thresholded fractal noise gives bays that widen towards the sea. Real coasts
also hold seas that lie inland and reach the ocean by a strait (the Black, Baltic and Azov
seas, Hudson Bay), and gulfs closed by a spit that leaves one narrow entrance (the Gulf of
Gdansk behind the Hel peninsula, the Sea of Azov behind the Arabat spit). Here a basin with a
noisy outline is cut into the land, with a rim of land around it, and a strait is cut from it
to the nearest ocean. The strait is the corridor of pixels whose distances to the basin and to
the ocean add up to little more than the distance between them: narrowest in the middle and
flaring at both ends, as the Bosporus does. A thin rim (down to ``rim_px``) between the basin
and the open sea is a spit; a thick one is an isthmus the strait cuts through.

Sizes follow a scale length (the feature size of a continent, bounded by the caller), so the
proportions are the same on every scale. Everything is
integer arithmetic on named SplitMix64 streams and hashed noise, so equal inputs give equal
seas on every platform. The strait is cut through land only and always reaches ocean water; a
sea that would not is not made.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from math import isqrt
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import SUBPIXEL, fractal_at
from rnw.lakes import STEP_SIZE, blob
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import SplitMix64, derive_seed, mix64
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

PERMILLE: Final[int] = 1000
EIGHTHS: Final[int] = 8
# Candidates per square of ``CELL_PERMILLE`` of the scale length, by land area, in millionths
# of a candidate per (scale length)^2 of land; each tries ``TRIES`` positions.
CELL_PERMILLE: Final[int] = 500
SEAS_PER_SQUARE: Final[int] = 420_000
TRIES: Final[int] = 4
# Basin area in (scale length)^2 permille: 1.2 % to 16 % (30,000 to 410,000 pixels at 1,600).
AREA_MIN_PERMILLE: Final[int] = 12
AREA_STEPS: Final[int] = 15
MAX_ELONGATION_PERMILLE: Final[int] = 2600
# The outline is as ragged as an ocean coast: many octaves that fade slowly.
OUTLINE_PERMILLE: Final[int] = 380
OUTLINE_OCTAVES: Final[int] = 6
OUTLINE_PERSISTENCE_PERMILLE: Final[int] = 620
# Rim of land between a basin and any water but its strait, and the longest strait, as shares
# of the scale length; the half-width of the strait at its middle ranges between two shares.
RIM_PERMILLE: Final[int] = 10
STRAIT_LENGTH_PERMILLE: Final[int] = 200
HALF_WIDTH_MIN_PERMILLE: Final[int] = 3
HALF_WIDTH_MAX_PERMILLE: Final[int] = 11
# How much the corridor widens towards each end, per distance from that end.
FUNNEL_PERMILLE: Final[int] = 350
# Own water must cover at least this share of the drawn outline, or the site is refused.
FILL_PERCENT: Final[int] = 92
ELLIPSE_REACH_PERMILLE: Final[int] = 1500
MIN_RIM_PX: Final[int] = 4


def carve_inland_seas(
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    seed: int,
    *,
    scale_px: int,
) -> NDArray[np.bool_]:
    """The land pixels that become inland seas and their straits; nothing else changes.

    ``ocean`` is the water that reaches the open sea. Seas are cut one after another, each
    seeing the water the earlier ones left, so two never share a strait by accident.
    """
    land, ocean = land.copy(), ocean.copy()
    carve = np.zeros(land.shape, dtype=bool)
    rows, columns = (int(size) for size in land.shape)
    cell = max(32, scale_px * CELL_PERMILLE // PERMILLE)
    key = derive_seed(seed, "inland_seas")
    for top in range(0, rows, cell):
        checkpoint()
        for left in range(0, columns, cell):
            area = int(np.count_nonzero(land[top : top + cell, left : left + cell]))
            if not area:
                continue
            stream = SplitMix64(mix64(key ^ (top << 32) ^ left))
            wanted, rest = divmod(area * SEAS_PER_SQUARE // (scale_px * scale_px), 1_000_000)
            wanted += stream.below(1_000_000) < rest
            made = 0
            for _ in range(wanted * TRIES):
                if made >= wanted:
                    break
                site = (
                    min(rows - 1, top + stream.below(cell)),
                    min(columns - 1, left + stream.below(cell)),
                )
                if not land[site]:
                    continue
                made += _cut(land, ocean, carve, site, stream, scale_px)
    return carve


def _cut(  # noqa: PLR0913, PLR0917 - the rasters, a site, its stream and the scale.
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    carve: NDArray[np.bool_],
    site: tuple[int, int],
    stream: SplitMix64,
    scale_px: int,
) -> int:
    """Cut one sea at ``site`` if it fits; 1 when it was cut, else 0. Draws the same either way."""
    step = stream.below(AREA_STEPS + 1)
    area = scale_px * scale_px * AREA_MIN_PERMILLE * STEP_SIZE[step] // (PERMILLE * PERMILLE)
    elongation = PERMILLE + stream.below(MAX_ELONGATION_PERMILLE - PERMILLE)
    drawn_half_width = max(
        2,
        scale_px
        * (
            HALF_WIDTH_MIN_PERMILLE
            + stream.below(HALF_WIDTH_MAX_PERMILLE - HALF_WIDTH_MIN_PERMILLE)
        )
        // PERMILLE,
    )
    angle = stream.below(16)
    shape_key = mix64(stream.next_u64())
    wiggle_key = mix64(stream.next_u64())
    long_axis = max(3, isqrt(area * elongation // 3142))
    short_axis = max(3, isqrt(area * PERMILLE * PERMILLE // (elongation * 3142)))
    # A strait is a narrow mouth of its sea, never a share of its width.
    half_width = max(2, min(drawn_half_width, short_axis // 4))
    rim = max(MIN_RIM_PX, scale_px * RIM_PERMILLE // PERMILLE)
    reach_strait = max(rim + 4, scale_px * STRAIT_LENGTH_PERMILLE // PERMILLE)
    rows, columns = (int(size) for size in land.shape)
    reach = long_axis * ELLIPSE_REACH_PERMILLE // PERMILLE + reach_strait + rim + 8
    window = (
        slice(max(0, site[0] - reach), min(rows, site[0] + reach + 1)),
        slice(max(0, site[1] - reach), min(columns, site[1] + reach + 1)),
    )
    land_w, ocean_w = land[window], ocean[window]
    shape = blob(
        window,
        site,
        (long_axis, short_axis),
        angle,
        shape_key,
        outline_permille=OUTLINE_PERMILLE,
        octaves=OUTLINE_OCTAVES,
        persistence_permille=OUTLINE_PERSISTENCE_PERMILLE,
    )
    basin = shape & land_w
    if basin.any():
        # A ragged outline can leave lobes that touch only at a corner; the sea is its largest part.
        parts = label_components(basin.astype(np.int32))
        sizes = np.bincount(parts[basin])
        basin = parts == int(np.argmax(sizes))
    if not basin.any() or (
        int(np.count_nonzero(basin)) * 100 < int(np.count_nonzero(shape)) * FILL_PERCENT
    ):
        return 0
    limit = reach_strait + rim + 8
    nearest_water = euclidean_distance(~land_w, rim + 1)
    if bool(np.any(basin & (nearest_water < EIGHTHS * rim))):
        return 0
    from_basin = euclidean_distance(basin, limit)
    from_ocean = euclidean_distance(ocean_w, limit)
    total = from_basin + from_ocean
    shortest = int(total[land_w].min())
    if shortest > EIGHTHS * reach_strait:
        return 0
    length = max(1, shortest // EIGHTHS)
    ys, xs = np.mgrid[window].astype(np.int64)
    wiggle = fractal_at(
        wiggle_key,
        xs * SUBPIXEL,
        ys * SUBPIXEL,
        period=max(8, length // 2),
        octaves=2,
        persistence_permille=500,
    )
    slack = 2 * EIGHTHS * half_width * half_width // length + (
        np.minimum(from_basin, from_ocean) * FUNNEL_PERMILLE // PERMILLE
    )
    slack = np.maximum(slack // 3, slack * (PERMILLE + 500 * wiggle // NOISE_SCALE) // PERMILLE)
    cut = basin | (land_w & (total <= shortest + slack))
    left = land_w & ~cut
    water = label_components((~left).astype(np.int32))
    reached = np.unique(water[ocean_w])
    if not bool(np.isin(water[basin], reached).all()):
        return 0
    # Corridor pixels the strait does not reach would be ponds on the shore; they stay land.
    cut &= np.isin(water, np.unique(water[basin]))
    land[window] &= ~cut
    ocean[window] |= cut
    carve[window] |= cut
    return 1
