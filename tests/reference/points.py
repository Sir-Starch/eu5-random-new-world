"""Pure NumPy interior point per cell: the specification of the Rust kernel.

Moved from ``rnw.newworld._interior_points`` when it became native
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.topology import distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray


def best_points(
    labels: NDArray[np.int32], score: NDArray[np.int64], tie: NDArray[np.int64], count: int
) -> NDArray[np.int64]:
    """Per label, the first pixel (raster order) with the highest score, ties by ``tie``."""
    width = labels.shape[1]
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    order = inside[np.lexsort((inside, -tie.ravel()[inside], -score.ravel()[inside], flat[inside]))]
    owners = flat[order]
    first = np.flatnonzero(np.concatenate([[True], owners[1:] != owners[:-1]]))
    points = np.zeros((count, 2), dtype=np.int64)
    points[owners[first]] = np.stack([order[first] // width, order[first] % width], axis=1)
    return points


def interior_points(
    labels: NDArray[np.int32],
    land: NDArray[np.bool_],
    interior_limit: int,
    shore_limit: int,
) -> NDArray[np.int64]:
    """Per cell, the first pixel with the best interior score (water: boundary distance)."""
    count = land.size
    padded = np.pad(labels, 1, constant_values=-1)
    center = padded[1:-1, 1:-1]
    boundary = (
        (padded[:-2, 1:-1] != center)
        | (padded[2:, 1:-1] != center)
        | (padded[1:-1, :-2] != center)
        | (padded[1:-1, 2:] != center)
    )
    is_land = np.concatenate([land, [False]])[labels]
    distance = distance_from(boundary, interior_limit).astype(np.int64)
    border = distance_from(boundary, interior_limit, octagonal=True).astype(np.int64)
    shore = distance_from(~is_land, shore_limit, octagonal=True).astype(np.int64)
    score = np.where(is_land, np.minimum(2 * border, shore), distance)
    tie = np.where(is_land, border, 0)
    return best_points(labels, score, tie, count)
