"""Pure NumPy distance fields and label spreading: the specification of the Rust kernels.

Moved from ``rnw.topology`` when they became native (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def nearest_label(
    labels: NDArray[np.int32], sources: NDArray[np.bool_], limit: int
) -> NDArray[np.int32]:
    """Spread the labels of ``sources`` pixels outwards by up to ``limit`` 4-steps.

    Pixels farther than ``limit`` keep -1. A pixel reached by several labels in the same
    step takes the label of the lowest-index neighbour that reached it, so the result
    does not depend on platform or hash order.
    """
    height, width = labels.shape
    out = np.where(sources, labels, -1).astype(np.int32).ravel()
    frontier = np.flatnonzero(sources.ravel())
    for _ in range(limit):
        if not frontier.size:
            break
        column = frontier % width
        origins = [
            frontier[frontier >= width],
            frontier[frontier < (height - 1) * width],
            frontier[column != 0],
            frontier[column != width - 1],
        ]
        targets = [origins[0] - width, origins[1] + width, origins[2] - 1, origins[3] + 1]
        source = np.concatenate(origins)
        reached = np.concatenate(targets)
        fresh = out[reached] < 0
        source, reached = source[fresh], reached[fresh]
        order = np.lexsort((source, reached))
        source, reached = source[order], reached[order]
        first = np.concatenate([[True], reached[1:] != reached[:-1]]) if reached.size else reached
        out[reached[first]] = out[source[first]]
        frontier = reached[first]
    return out.reshape(height, width)


def euclidean_distance(sources: NDArray[np.bool_], limit: int) -> NDArray[np.int64]:
    """Exact Euclidean distance to the nearest source, in eighths of a pixel.

    Separable: a vertical pass finds the nearest source row per column, then a
    horizontal minimum over offsets up to ``limit``. Distances beyond ``limit`` are
    capped there. The square root of an exact integer is correctly rounded in IEEE
    arithmetic, so results are identical on every platform.
    """
    height, width = sources.shape
    far = limit + 1
    vertical = np.full((height, width), far, dtype=np.int64)
    last = np.full(width, -far, dtype=np.int64)
    for row in range(height):
        last = np.where(sources[row], row, last)
        vertical[row] = np.minimum(row - last, far)
    last = np.full(width, height + far, dtype=np.int64)
    for row in range(height - 1, -1, -1):
        last = np.where(sources[row], row, last)
        vertical[row] = np.minimum(vertical[row], np.minimum(last - row, far))
    square = vertical * vertical
    best = square.copy()
    for offset in range(1, limit + 1):
        extra = offset * offset
        _ = np.minimum(best[:, offset:], square[:, :-offset] + extra, out=best[:, offset:])
        _ = np.minimum(best[:, :-offset], square[:, offset:] + extra, out=best[:, :-offset])
    best = np.minimum(best, far * far)
    return np.floor(np.sqrt(best.astype(np.float64)) * 8).astype(np.int64)


def distance_from(
    sources: NDArray[np.bool_], limit: int, *, octagonal: bool = False
) -> NDArray[np.int32]:
    """Step distance to the nearest source pixel, capped at ``limit``.

    Steps are 4-neighbour; ``octagonal`` also allows diagonal steps on every second
    round, which approximates Euclidean distance better than the diamond metric.
    """
    height, width = sources.shape
    distance = np.full(sources.size, limit, dtype=np.int32)
    frontier = np.flatnonzero(sources.ravel())
    distance[frontier] = 0
    for step in range(1, limit):
        if not frontier.size:
            break
        column = frontier % width
        parts = [
            frontier[frontier >= width] - width,
            frontier[frontier < (height - 1) * width] + width,
            frontier[column != 0] - 1,
            frontier[column != width - 1] + 1,
        ]
        if octagonal and step % 2 == 0:
            up = frontier >= width
            down = frontier < (height - 1) * width
            left = column != 0
            right = column != width - 1
            parts += [
                frontier[up & left] - width - 1,
                frontier[up & right] - width + 1,
                frontier[down & left] + width - 1,
                frontier[down & right] + width + 1,
            ]
        reached = np.concatenate(parts)
        reached = np.unique(reached[distance[reached] > step])
        distance[reached] = step
        frontier = reached
    return distance.reshape(height, width)
