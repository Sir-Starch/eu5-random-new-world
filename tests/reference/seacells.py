"""Independent versions of the sea-cell kernels (``native/src/seacells.rs``): a heap-based walk
through the water and a pixel-by-pixel nearest site, both in plain Python."""

# pyright: reportAny=false
from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# A step to a side, a diagonal and a knight's move, and what each costs (thousandths of a pixel).
STEPS: tuple[tuple[int, int, int], ...] = (
    (0, 1, 1000),
    (0, -1, 1000),
    (1, 0, 1000),
    (-1, 0, 1000),
    (1, 1, 1414),
    (1, -1, 1414),
    (-1, 1, 1414),
    (-1, -1, 1414),
    (1, 2, 2236),
    (1, -2, 2236),
    (-1, 2, 2236),
    (-1, -2, 2236),
    (2, 1, 2236),
    (2, -1, 2236),
    (-2, 1, 2236),
    (-2, -1, 2236),
)
UNREACHED = 2**32 - 1


def geodesic(  # noqa: C901 - a walk, its rules for a step and its ties in one place.
    mask: NDArray[np.bool_],
    region: NDArray[np.int32],
    sites: NDArray[np.int64],
    start: NDArray[np.uint32],
) -> tuple[NDArray[np.int32], NDArray[np.uint32]]:
    """The distance through water of every pixel from the nearest site, and that site: of the
    sites at the least distance the lowest. A step stays in its region, never cuts a corner."""
    height, width = mask.shape
    label = np.full(mask.shape, -1, dtype=np.int32)
    cost = np.full(mask.shape, UNREACHED, dtype=np.uint32)

    def open_(row: int, column: int, own: int) -> bool:
        inside = 0 <= row < height and 0 <= column < width
        return inside and bool(mask[row, column]) and int(region[row, column]) == own

    def clear(row: int, column: int, dr: int, dc: int) -> bool:
        own = int(region[row, column])
        if not open_(row + dr, column + dc, own):
            return False
        if abs(dr) + abs(dc) == 1:
            return True
        if abs(dr) == 1 and abs(dc) == 1:
            return open_(row + dr, column, own) and open_(row, column + dc, own)
        if abs(dr) == 2:
            mid = dr // 2
            return open_(row + mid, column, own) and open_(row + mid, column + dc, own)
        mid = dc // 2
        return open_(row, column + mid, own) and open_(row + dr, column + mid, own)

    best: dict[tuple[int, int], tuple[int, int]] = {}
    queue: list[tuple[int, int, int, int]] = []
    for index, (row, column) in enumerate(sites.tolist()):
        if not mask[row, column]:
            continue
        key = (int(start[index]), index)
        if (row, column) not in best or key < best[(row, column)]:
            best[(row, column)] = key
            heapq.heappush(queue, (key[0], key[1], row, column))
    while queue:
        reach, owner, row, column = heapq.heappop(queue)
        if best[(row, column)] != (reach, owner):
            continue
        cost[row, column] = reach
        label[row, column] = owner
        for dr, dc, price in STEPS:
            if not clear(row, column, dr, dc):
                continue
            here = (row + dr, column + dc)
            key = (reach + price, owner)
            if here not in best or key < best[here]:
                best[here] = key
                heapq.heappush(queue, (key[0], key[1], here[0], here[1]))
    return label, cost


def _smooth_depth(depth: NDArray[np.int32], step: int, row: int, column: int) -> int:
    """The coarse distance, interpolated between the centres of the four coarse pixels round it."""
    rows, columns = depth.shape
    span = 2 * step

    def place(at: int, count: int) -> tuple[int, int]:
        origin = 2 * at + 1 - step
        first = min(max(origin // span, 0), max(count - 2, 0))
        return first, min(max(origin - first * span, 0), span)

    r0, a = place(row, rows)
    c0, b = place(column, columns)
    r1, c1 = min(r0 + 1, rows - 1), min(c0 + 1, columns - 1)

    def at(r: int, c: int) -> int:
        return int(depth[r, c])

    total = (
        (span - a) * (span - b) * at(r0, c0)
        + (span - a) * b * at(r0, c1)
        + a * (span - b) * at(r1, c0)
        + a * b * at(r1, c1)
    )
    return total // (span * span)


def refine(  # noqa: PLR0913, PLR0917 - the rasters, the sites and what a band is.
    mask: NDArray[np.bool_],
    coarse: NDArray[np.int32],
    step: int,
    reach: int,
    sites: NDArray[np.int64],
    depth: NDArray[np.int32],
    band_width: int,
    last_band: int,
    site_band: NDArray[np.int32],
    site_claim: NDArray[np.int64],
) -> NDArray[np.int32]:
    """Each water pixel takes, of the labels of the coarse pixels round it, the one whose site is
    nearest (the lowest on a tie) among those of its own band. A claim wins inside its disk,
    ordered by distance squared minus land radius squared where disks overlap."""
    out = np.full(mask.shape, -1, dtype=np.int32)
    coarse_rows, coarse_columns = coarse.shape
    for found_row, found_column in zip(*np.nonzero(mask), strict=True):
        row, column = int(found_row), int(found_column)
        cr, cc = row // step, column // step
        band = min(_smooth_depth(depth, step, row, column) // max(band_width, 1), last_band)
        owners = {
            int(coarse[r, c])
            for r in range(max(cr - reach, 0), min(cr + reach, coarse_rows - 1) + 1)
            for c in range(max(cc - reach, 0), min(cc + reach, coarse_columns - 1) + 1)
            if coarse[r, c] >= 0
        }
        keys = {
            owner: (
                (row - int(sites[owner, 0])) ** 2 + (column - int(sites[owner, 1])) ** 2,
                owner,
            )
            for owner in owners
        }
        claimed = [
            (squared - int(site_claim[owner, 1]), owner)
            for owner, (squared, _) in keys.items()
            if site_claim[owner, 0] > 0 and squared <= site_claim[owner, 0]
        ]
        own = [
            key for owner, key in keys.items() if site_band[owner] < 0 or site_band[owner] == band
        ]
        if claimed:
            out[row, column] = min(claimed)[1]
        elif own:
            out[row, column] = min(own)[1]
        elif keys:
            out[row, column] = min(keys.values())[1]
    return out
