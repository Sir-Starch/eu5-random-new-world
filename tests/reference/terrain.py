"""Pure NumPy decal land mask, distances and heights: the specification of the Rust kernel.

Moved from ``rnw.eu5_terrain`` when they became native (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_terrain import (
    CAP_REACH,
    CAP_SLOPE,
    COAST_SMOOTH,
    CREST_FULL,
    CREST_HEIGHT,
    CREST_PERIOD,
    DETAIL_BASE,
    DETAIL_PERIOD,
    DETAIL_PERMILLE,
    EIGHTHS,
    OUTSIDE,
    SHORE_HEIGHT,
    WATER_CODE,
    WATER_PROFILE,
)
from rnw.fields import PERMILLE, box_blur, upsample
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.relief import COAST_HEIGHT
from rnw.rng import derive_seed
from rnw.topology import distance_from, euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _upsample(values: NDArray[np.generic], factor: int) -> NDArray[np.int64]:
    return np.repeat(np.repeat(values.astype(np.int64), factor, axis=0), factor, axis=1)


def _noise(  # noqa: PLR0913 - a strip-computed field needs origin, size and octaves.
    key: int, x0: int, y0: int, width: int, height: int, *, period: int
) -> NDArray[np.int64]:
    out = np.empty((height, width), dtype=np.int64)
    for row in range(0, height, 1024):
        rows = min(1024, height - row)
        out[row : row + rows] = fractal_noise(
            key, x0, y0 + row, width, rows, period=period, octaves=3, persistence_permille=500
        )
    return out


def _profile(
    distance: NDArray[np.int64], table: tuple[tuple[int, int], ...], unit: int = 1
) -> NDArray[np.int64]:
    """Integer piecewise-linear interpolation of a (distance, height) table.

    ``distance`` is in ``1 / unit`` pixels.
    """
    out = np.full(distance.shape, table[-1][1], dtype=np.int64)
    out[distance <= table[0][0] * unit] = table[0][1]
    for (d0, h0), (d1, h1) in pairwise(table):
        inside = (distance > d0 * unit) & (distance <= d1 * unit)
        out[inside] = h0 + (distance[inside] - d0 * unit) * (h1 - h0) // ((d1 - d0) * unit)
    return out


def land_and_distances(
    codes: NDArray[np.int64], vanilla_water: NDArray[np.bool_]
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int64], NDArray[np.int64]]:
    """Smoothed land mask, canvas mask and coast distances at decal resolution.

    Inputs are at location resolution. Distances are in eighths of a decal pixel; the
    inland one is Euclidean (computed per location pixel and interpolated), so slopes
    built on it have no metric artefacts.
    """
    canvas_location = codes != OUTSIDE
    land_location = np.where(canvas_location, codes != WATER_CODE, ~vanilla_water)
    canvas = _upsample(canvas_location.astype(np.int8), 2).astype(bool)
    raw = _upsample(land_location.astype(np.int8), 2).astype(bool)
    smooth = box_blur(raw.astype(np.int64) * 1000, COAST_SMOOTH) >= 500
    land = np.where(canvas, smooth, raw)
    shape = (int(land.shape[0]), int(land.shape[1]))
    reach = euclidean_distance(~land_location, CAP_REACH) * 2
    inland = box_blur(upsample(np.pad(reach, ((0, 1), (0, 1)), mode="edge"), 2, shape), 2)
    offshore = distance_from(land, WATER_PROFILE[-1][0] + 1, octagonal=True).astype(np.int64)
    offshore = box_blur(offshore * EIGHTHS, 2)
    inland = np.where(land, np.maximum(inland, EIGHTHS), 0)
    offshore = np.where(land, 0, np.maximum(offshore, EIGHTHS))
    return land, canvas, inland, offshore


def heights(  # noqa: PLR0913 - one window's height needs relief, coast, origin and seed.
    relief: NDArray[np.int64],
    *,
    land: NDArray[np.bool_],
    inland: NDArray[np.int64],
    offshore: NDArray[np.int64],
    seed: int,
    origin: tuple[int, int],
) -> NDArray[np.int64]:
    """Generated heights for a window: relief plus detail under a coastal cap.

    ``relief`` is at location resolution; the result is at decal resolution. Near the
    shore the height is capped by a ramp that starts at the lowest vanilla land height,
    so beaches are low and ranges rise from them without a terrace. Water follows the
    vanilla shelf profile. Distances are in eighths of a pixel.
    """
    filled = np.pad(np.where(relief > 0, relief, COAST_HEIGHT), ((0, 1), (0, 1)), mode="edge")
    shape = (int(land.shape[0]), int(land.shape[1]))
    smooth = upsample(filled, 2, shape)
    x0, y0 = origin
    detail = _noise(derive_seed(seed, "terrain_detail"), x0, y0, shape[1], shape[0],
                    period=DETAIL_PERIOD)  # fmt: skip
    raised = np.maximum(0, smooth - COAST_HEIGHT)
    amplitude = DETAIL_BASE + raised * DETAIL_PERMILLE // PERMILLE
    crest = NOISE_SCALE - np.minimum(
        np.abs(_noise(derive_seed(seed, "terrain_crests"), x0, y0, shape[1], shape[0],
                      period=CREST_PERIOD)),
        NOISE_SCALE,
    )  # fmt: skip
    crests = (crest * crest // NOISE_SCALE) * np.minimum(raised, CREST_FULL) // CREST_FULL
    inner = smooth + detail * amplitude // NOISE_SCALE + crests * CREST_HEIGHT // NOISE_SCALE
    cap = SHORE_HEIGHT + (inland - EIGHTHS) * CAP_SLOPE // EIGHTHS
    land_height = np.maximum(np.minimum(inner, cap), SHORE_HEIGHT)
    water_height = _profile(offshore, WATER_PROFILE, EIGHTHS)
    return np.where(land, land_height, water_height)
