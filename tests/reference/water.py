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
from rnw.eu5_water import BAND_ROWS, BLEND, _decode, _downsample  # pyright: ignore[reportPrivateUsage]
from rnw.fields import box_blur
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.topology import distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _profile_table(
    image: NDArray[np.int64], distance: NDArray[np.int64], reach: int
) -> NDArray[np.int64]:
    """Mean RGBA per (latitude band, distance to land) from vanilla pixels."""
    bands = image.shape[0] // BAND_ROWS
    band = np.minimum(np.arange(image.shape[0], dtype=np.int64) // BAND_ROWS, bands - 1)[:, None]
    key = (band * (reach + 1) + np.minimum(distance, reach)).ravel()
    size = bands * (reach + 1)
    counts = np.maximum(1, np.bincount(key, minlength=size))
    table = np.zeros((size, 4), dtype=np.int64)
    for channel in range(4):
        sums = np.bincount(key, weights=image[..., channel].ravel(), minlength=size)
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
    old_distance = distance_from(~old_water, reach + 1, octagonal=True).astype(np.int64)
    new_distance = distance_from(~fresh_water, reach + 1, octagonal=True).astype(np.int64)
    table = _profile_table(image, old_distance, reach)
    synthetic = _synthesize(table, new_distance, reach)
    for channel in range(4):
        synthetic[..., channel] = box_blur(synthetic[..., channel], 2)
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
    synthetic[..., :3] += (noise * 6 // NOISE_SCALE)[..., None]
    calm = np.minimum(old_distance, new_distance)
    keep = np.clip(calm - (reach - BLEND), 0, BLEND)[..., None]
    blended = (image * keep + synthetic * (BLEND - keep)) // BLEND
    result = np.where(touched[..., None], blended, image).clip(0, 255).astype(np.uint8)
    changed = touched & np.any(result != image, axis=2)
    return rewrite(data, result, changed), int(np.count_nonzero(changed))
