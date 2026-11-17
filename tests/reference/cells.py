"""Unchanged NumPy/Python cell kernels before the performance port (epoch 64)."""

# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.progress import checkpoint

if TYPE_CHECKING:
    from numpy.typing import NDArray

CENTRE_STRIP = 256
PERMILLE = 1000
SEED_GAP = 758


def grow_regions(mask: NDArray[np.bool_], seeds: NDArray[np.int32]) -> NDArray[np.int32]:
    """Grow seed labels through ``mask`` one 4-neighbour step per round.

    A pixel adopts the label of an already labelled neighbour in N, W, E, S order, so
    every grown region stays 4-connected to its seed. Unreachable pixels remain -1.
    Only the previous round's frontier can border unlabelled pixels, so each round
    touches the frontier instead of the whole raster.
    """
    height, width = mask.shape
    allowed = mask.ravel()
    labels = np.where(allowed, seeds.ravel(), -1).astype(np.int32)
    frontier = np.flatnonzero(labels >= 0)
    while frontier.size:
        checkpoint()
        frontier = _claim(labels, allowed, frontier, width, height)
    return labels.reshape(height, width)


def grow_weighted(
    mask: NDArray[np.bool_], seeds: NDArray[np.int32], speed: NDArray[np.int64]
) -> NDArray[np.int32]:
    """``grow_regions`` with each label growing at its own ``speed`` (one per label, positive):
    in round ``t`` a label steps on when ``t * speed // fastest`` grows, so the fastest steps
    every round, and the border between two seeds lies where they meet at their speeds.
    """
    height, width = mask.shape
    allowed = mask.ravel()
    labels = np.where(allowed, seeds.ravel(), -1).astype(np.int32)
    frontier = np.flatnonzero(labels >= 0)
    fastest = int(speed.max()) if speed.size else 1
    round_number = 0
    while frontier.size:
        checkpoint()
        round_number += 1
        pace = speed[labels[frontier]]
        steps = round_number * pace // fastest > (round_number - 1) * pace // fastest
        claimed = _claim(labels, allowed, frontier[steps], width, height)
        frontier = np.concatenate([frontier[~steps], claimed])
    return labels.reshape(height, width)


def _claim(
    labels: NDArray[np.int32],
    allowed: NDArray[np.bool_],
    frontier: NDArray[np.int64],
    width: int,
    height: int,
) -> NDArray[np.int64]:
    """One growth round in N, W, E, S priority; returns the newly labelled pixels."""
    column = frontier % width
    claimed: list[NDArray[np.int64]] = []
    for sources, offset in (
        (frontier[frontier < (height - 1) * width], width),
        (frontier[column != width - 1], 1),
        (frontier[column != 0], -1),
        (frontier[frontier >= width], -width),
    ):
        targets = sources + offset
        free = allowed[targets] & (labels[targets] < 0)
        labels[targets[free]] = labels[sources[free]]
        claimed.append(targets[free])
    return np.sort(np.concatenate(claimed))


def grade_spacing(
    spacing: NDArray[np.int64], land: NDArray[np.bool_], step_permille: int
) -> NDArray[np.int64]:
    """The largest spacing at or below ``spacing`` that grows by at most ``step_permille`` from
    one block of ``land`` to the next (``step_permille`` times the square root of two to a
    diagonal one), as a mesh limits the growth of its elements: a small spacing narrows the
    large ones around it, a large one never widens the small. Blocks without land neither take
    nor pass a limit."""
    big = np.int64(1) << 40
    graded = np.where(land, spacing, big)
    straight, diagonal = step_permille, step_permille * 1414 // 1000
    while True:
        padded = np.pad(graded, 1, constant_values=big)
        limit = np.minimum.reduce(
            [
                padded[:-2, 1:-1] + straight,
                padded[2:, 1:-1] + straight,
                padded[1:-1, :-2] + straight,
                padded[1:-1, 2:] + straight,
                padded[:-2, :-2] + diagonal,
                padded[:-2, 2:] + diagonal,
                padded[2:, :-2] + diagonal,
                padded[2:, 2:] + diagonal,
            ]
        )
        lowered = np.minimum(graded, np.where(land, limit, big))
        if np.array_equal(lowered, graded):
            return np.where(land, graded, spacing)
        graded = lowered


def throw_seeds(  # noqa: PLR0913 - the candidates, their spacings, the extremes and the width.
    xs: NDArray[np.int64],
    ys: NDArray[np.int64],
    radius: NDArray[np.int64],
    *,
    smallest: int,
    widest: int,
    columns: int,
) -> NDArray[np.int64]:
    """The raster positions of the candidates kept in turn: a candidate is dropped when a kept
    one lies nearer than ``SEED_GAP`` of the mean of their spacings (all in pixels). Kept seeds
    are filed in buckets of the ``smallest`` spacing, and a candidate looks as far as the
    ``widest`` spacing could reach."""
    buckets: dict[tuple[int, int], list[int]] = {}
    kept_x: list[int] = []
    kept_y: list[int] = []
    kept_r: list[int] = []
    gap = SEED_GAP * SEED_GAP
    scale = 4 * PERMILLE * PERMILLE
    for x, y, r in zip(xs.tolist(), ys.tolist(), radius.tolist(), strict=True):
        reach = -(-SEED_GAP * (r + widest) // (2 * PERMILLE * smallest))
        bx, by = x // smallest, y // smallest
        clear = True
        for cy in range(by - reach, by + reach + 1):
            for cx in range(bx - reach, bx + reach + 1):
                for j in buckets.get((cx, cy), ()):
                    dx, dy, both = x - kept_x[j], y - kept_y[j], r + kept_r[j]
                    if scale * (dx * dx + dy * dy) < gap * both * both:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                break
        if clear:
            buckets.setdefault((bx, by), []).append(len(kept_x))
            kept_x.append(x)
            kept_y.append(y)
            kept_r.append(r)
    return np.array(kept_y, dtype=np.int64) * columns + np.array(kept_x, dtype=np.int64)


def merge_small(labels: NDArray[np.int32], minimum: int) -> NDArray[np.int32]:
    """Merge cells smaller than ``minimum`` into their longest-border neighbour."""
    count = int(labels.max()) + 1
    sizes = np.bincount(labels[labels >= 0], minlength=count).astype(np.int64)
    pairs: dict[int, dict[int, int]] = {}
    for a, b in (
        (labels[:, :-1], labels[:, 1:]),
        (labels[:-1], labels[1:]),
    ):
        touching = (a != b) & (a >= 0) & (b >= 0)
        packed = a[touching].astype(np.int64) * count + b[touching]
        values, shared = np.unique(packed, return_counts=True)
        for value, length in zip(values.tolist(), shared.tolist(), strict=True):
            first, second = divmod(value, count)
            pairs.setdefault(first, {})[second] = (
                pairs.setdefault(first, {}).get(second, 0) + length
            )
            pairs.setdefault(second, {})[first] = (
                pairs.setdefault(second, {}).get(first, 0) + length
            )
    target = list(range(count))

    def resolve(item: int) -> int:
        while target[item] != item:
            item = target[item]
        return item

    for cell in range(count):
        if sizes[cell] >= minimum or not pairs.get(cell):
            continue
        best = min(pairs[cell].items(), key=lambda item: (-item[1], item[0]))[0]
        root = resolve(best)
        if root != cell:
            target[cell] = root
            sizes[root] += sizes[cell]
    mapping = np.array([resolve(item) for item in range(count)], dtype=np.int32)
    return np.where(labels >= 0, mapping[np.maximum(labels, 0)], -1).astype(np.int32)


def centre_pixels(grown: NDArray[np.int32], flat: NDArray[np.int64]) -> NDArray[np.int64]:
    """The raster position of the centre of each cell of ``grown`` (numbered as the seeds at
    ``flat``): the pixel of its mean row and column (floored) when the cell holds it, else the
    cell's pixel nearest to it, the first in raster order of equals. A seed that grew no cell
    keeps its pixel."""
    count = int(flat.size)
    rows, columns = (int(size) for size in grown.shape)
    pixels = np.zeros(count, dtype=np.int64)
    row_sums = np.zeros(count, dtype=np.int64)
    column_sums = np.zeros(count, dtype=np.int64)
    for first in range(0, rows, CENTRE_STRIP):
        part = grown[first : first + CENTRE_STRIP]
        ys, xs = np.nonzero(part >= 0)
        labels = part[ys, xs]
        pixels += np.bincount(labels, minlength=count)
        # Sums of whole rows and columns stay below 2^53, so the float sums are exact.
        row_sums += np.bincount(labels, weights=ys + first, minlength=count).astype(np.int64)
        column_sums += np.bincount(labels, weights=xs, minlength=count).astype(np.int64)
    grew = pixels > 0
    held = np.maximum(pixels, 1)
    centre_rows, centre_columns = row_sums // held, column_sums // held
    centres = centre_rows * columns + centre_columns
    own = grew & (grown.ravel()[centres] == np.arange(count))
    out = np.where(own, centres, flat)
    missing = np.flatnonzero(grew & ~own)
    if missing.size == 0:
        return out
    best = np.full(count, np.iinfo(np.int64).max, dtype=np.int64)
    found = np.full(count, -1, dtype=np.int64)
    wanted = np.zeros(count, dtype=bool)
    wanted[missing] = True
    for first in range(0, rows, CENTRE_STRIP):
        part = grown[first : first + CENTRE_STRIP]
        ys, xs = np.nonzero((part >= 0) & wanted[np.maximum(part, 0)])
        if ys.size == 0:
            continue
        labels = part[ys, xs].astype(np.int64)
        ys = ys + first
        distance = (ys - centre_rows[labels]) ** 2 + (xs - centre_columns[labels]) ** 2
        # Nearest first, then raster order; strips run in raster order, so an earlier strip's
        # equal pixel is kept.
        sequence = np.lexsort((ys * columns + xs, distance, labels))
        labels, distance = labels[sequence], distance[sequence]
        position = (ys * columns + xs)[sequence]
        firsts = np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]])
        chosen, nearest = labels[firsts], distance[firsts]
        better = nearest < best[chosen]
        best[chosen[better]] = nearest[better]
        found[chosen[better]] = position[firsts][better]
    out[missing] = found[missing]
    return out


def location_sums(
    labels: NDArray[np.int32],
    table: NDArray[np.int64],
    shape: tuple[int, int],
    count: int,
    *,
    step: int = 64,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The pixels of each of ``count`` labels and the sums of ``table`` (one row per ``step``
    block in raster order, ``shape`` blocks) over them; a label of -1 is none."""
    pixels = np.zeros(count, dtype=np.int64)
    sums = np.zeros((count, table.shape[1]), dtype=np.int64)
    columns = np.arange(int(labels.shape[1]), dtype=np.int64) // step
    for first in range(0, int(labels.shape[0]), step * 8):
        checkpoint()
        window = labels[first : first + step * 8].ravel()
        rows = np.arange(first, first + step * 8, dtype=np.int64)[: labels.shape[0] - first]
        block = (rows[:, np.newaxis] // step * shape[1] + columns[np.newaxis, :]).ravel()
        here = window >= 0
        block, owner = block[here], window[here]
        pixels += np.bincount(owner, minlength=count)
        for column in range(table.shape[1]):
            # Exact: integer sums below 2^53 in a strip.
            found = np.bincount(owner, weights=table[block, column], minlength=count)
            sums[:, column] += found.astype(np.int64)
    return pixels, sums


def strip_bend(
    land: NDArray[np.bool_], height: NDArray[np.integer], start: int, stop: int, rows: int
) -> NDArray[np.int64]:
    step = 8
    low = max(0, start - step)
    columns = int(land.shape[1])
    values = height.astype(np.int64)
    inner = slice(start - low, stop - low)
    bend = np.zeros((stop - start, columns), dtype=np.int64)
    ends = np.zeros((stop - start, columns), dtype=np.int64)
    if columns > 2 * step:
        middle = slice(step, columns - step)
        both = land[inner, : -2 * step] & land[inner, 2 * step :]
        found = values[inner, 2 * step :] + values[inner, : -2 * step]
        found = np.abs(found - 2 * values[inner, middle])
        bend[:, middle] += np.where(both, found, 0)
        ends[:, middle] += both
    # Rows ``step`` away from the strip's own; the first and last ``step`` of the map have none.
    first, last = max(start, step), min(stop, rows - step)
    if first < last:
        here = slice(first - low, last - low)
        above = slice(first - step - low, last - step - low)
        below = slice(first + step - low, last + step - low)
        both = land[above] & land[below]
        found = np.abs(values[above] + values[below] - 2 * values[here])
        bend[first - start : last - start] += np.where(both, found, 0)
        ends[first - start : last - start] += both
    return np.where(ends > 0, bend // np.maximum(ends, 1), -1)
