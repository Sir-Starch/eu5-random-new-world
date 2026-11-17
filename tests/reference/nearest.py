"""Original partition-based nearest neighbours, including its boundary ties."""

# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def nearest(train: NDArray[np.int64], block: NDArray[np.int64], k: int) -> NDArray[np.int64]:
    """The ``k`` nearest training rows of each row of ``block``, nearest first (ties by index,
    but which of the rows as far as the ``k``-th it keeps is the partition's).

    The squared distance is |a|^2 + |b|^2 - 2 a.b, exact in integers (standardized features are
    a few times 10^4, so every term stays far below 2^63) and the same as the sum of squared
    differences, at a third of the time.
    """
    distance = (train * train).sum(axis=1)[np.newaxis, :] - 2 * (block @ train.T)
    distance += (block * block).sum(axis=1)[:, np.newaxis]
    nearest = np.argpartition(distance, k - 1, axis=1)[:, :k]
    near_distance = np.take_along_axis(distance, nearest, axis=1)
    order = np.lexsort((nearest, near_distance), axis=-1)
    return np.take_along_axis(nearest, order, axis=1)
