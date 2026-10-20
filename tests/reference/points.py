"""Pure NumPy best pixel per label: the specification of the Rust kernel.

Moved from ``rnw.newworld._interior_points`` when it became native
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

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
