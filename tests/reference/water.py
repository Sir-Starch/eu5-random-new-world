"""Whole-image water texture rebuild: the specification of the banded ``rnw.eu5_water``.

Moved from ``rnw.eu5_water`` when the rebuild went row strip by row strip
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.dds import rewrite
from rnw.eu5_water import (
    BAND_ROWS,
    BLEND,
    GRID,
    _background,  # pyright: ignore[reportPrivateUsage]
    _background_grid,  # pyright: ignore[reportPrivateUsage]
    _decode,  # pyright: ignore[reportPrivateUsage]
    _downsample,  # pyright: ignore[reportPrivateUsage]
)
from rnw.fields import box_blur
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.topology import distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _open_water_cells(
    image: NDArray[np.int64], distance: NDArray[np.int64], reach: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Colour sums and counts of the pixels ``reach`` or more from land, cell by cell."""
    rows, columns = distance.shape
    cells = (-(-rows // GRID), -(-columns // GRID))
    sums = np.zeros((*cells, 4), dtype=np.int64)
    counts = np.zeros(cells, dtype=np.int64)
    for row in range(cells[0]):
        for column in range(cells[1]):
            window = (
                slice(row * GRID, (row + 1) * GRID),
                slice(column * GRID, (column + 1) * GRID),
            )
            far = distance[window] >= reach
            counts[row, column] = np.count_nonzero(far)
            sums[row, column] = image[window][far].sum(axis=0)
    return sums, counts


def _profile_table(
    image: NDArray[np.int64],
    distance: NDArray[np.int64],
    grid: NDArray[np.int64],
    reach: int,
) -> NDArray[np.int64]:
    """Mean RGBA offset from the open-water background per (latitude band, distance to land)."""
    bands = image.shape[0] // BAND_ROWS
    band = np.minimum(np.arange(image.shape[0], dtype=np.int64) // BAND_ROWS, bands - 1)[:, None]
    key = (band * (reach + 1) + np.minimum(distance, reach)).ravel()
    size = bands * (reach + 1)
    counts = np.maximum(1, np.bincount(key, minlength=size))
    offset = image - _background(grid, 0, image.shape[0], image.shape[1])
    table = np.zeros((size, 4), dtype=np.int64)
    for channel in range(4):
        sums = np.bincount(key, weights=offset[..., channel].ravel(), minlength=size)
        table[:, channel] = sums.astype(np.int64) // counts
    return table.reshape(bands, reach + 1, 4)


def _synthesize(
    table: NDArray[np.int64], distance: NDArray[np.int64], reach: int
) -> NDArray[np.int64]:
    """Colour by latitude (linearly blended between bands) and distance to land."""
    rows = distance.shape[0]
    bands = table.shape[0]
    position = (np.arange(rows, dtype=np.int64) * 1000 - BAND_ROWS * 500) // BAND_ROWS
    lower = np.minimum(np.maximum(position // 1000, 0), bands - 1)
    upper = np.minimum(lower + 1, bands - 1)
    weight = np.minimum(np.maximum(position - lower * 1000, 0), 1000)[:, None, None]
    d = np.minimum(distance, reach)
    first = table[lower[:, None], d]
    second = table[upper[:, None], d]
    return (first * (1000 - weight) + second * weight) // 1000


def rebuild(  # noqa: PLR0913 - one texture needs masks at its own scale and the seed.
    data: bytes,
    *,
    factor: int,
    reach: int,
    masks: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]],
    seed: int,
    stream: str,
) -> tuple[bytes, int]:
    vanilla_water, new_water, canvas = masks
    image = _decode(data).astype(np.int64)
    old_water = _downsample(vanilla_water, factor, any_true=False)
    fresh_water = _downsample(new_water, factor, any_true=False)
    touched = _downsample(canvas, factor, any_true=True)
    old_distance = distance_from(~old_water, reach + 1, octagonal=True, wrap_x=True).astype(
        np.int64
    )
    new_distance = distance_from(~fresh_water, reach + 1, octagonal=True, wrap_x=True).astype(
        np.int64
    )
    grid = _background_grid(*_open_water_cells(image, old_distance, reach))
    table = _profile_table(image, old_distance, grid, reach)
    affected = distance_from(old_distance != new_distance, 3, octagonal=True, wrap_x=True) <= 2
    touched |= old_water & fresh_water & affected
    synthetic = _synthesize(table, new_distance, reach) + _background(
        grid, 0, image.shape[0], image.shape[1]
    )
    for channel in range(4):
        padded = np.pad(synthetic[..., channel], ((0, 0), (2, 2)), mode="wrap")
        synthetic[..., channel] = box_blur(padded, 2)[:, 2:-2]
    rows, columns = touched.shape
    noise = fractal_noise(
        derive_seed(seed, stream),
        0,
        0,
        columns,
        rows,
        period=96,
        octaves=3,
        persistence_permille=500,
    )
    other = fractal_noise(
        derive_seed(seed, stream),
        columns,
        0,
        columns,
        rows,
        period=96,
        octaves=3,
        persistence_permille=500,
    )
    position = np.arange(columns, dtype=np.int64) * 1000 // columns
    weight = position * position * (3000 - 2 * position) // 1_000_000
    noise = (other * (1000 - weight) + noise * weight) // 1000
    synthetic[..., :3] += (noise * 6 // NOISE_SCALE)[..., None]
    calm = np.minimum(old_distance, new_distance)
    keep = np.clip(calm - (reach - BLEND), 0, BLEND)[..., None]
    blended = (image * keep + synthetic * (BLEND - keep)) // BLEND
    result = np.where(touched[..., None], blended, image).clip(0, 255).astype(np.uint8)
    changed = touched & np.any(result != image, axis=2)
    return rewrite(data, result, changed), int(np.count_nonzero(changed))
