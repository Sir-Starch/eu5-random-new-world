"""Straits: where two landmasses come close, a channel an army can cross, and the rows that say so.

Game-independent. The game links two land locations that a narrow sea zone separates, "close
enough to each other so armies can cross it without the need of a navy" (``adjacencies.csv``, type
``sea``), and blockades the crossing with the sea zone [SOURCE wiki; V-LOCAL C245]. What close is,
the game's own 184 rows say: the two points of a crossing lie 1 to 9 pixels apart (median 3), each
on its own location, and the sea zone between touches both. The generated land has no such gaps: its
landmasses are a sea cell or more apart (two pairs of locations in the reference world within 12
pixels). So there are two things to do:

* **Pinch.** Two landmasses that come within ``NEAR_PX`` of each other are brought together at
  their nearest points to a channel of ``STRAIT_PX``: each grows by the same distance towards the
  other, the growth tapering to nothing over twice the gap, as a headland that a sea has not yet
  cut through. Nothing is merged, no third landmass is touched, and no water is cut off,
  or the pinch is not made.
* **Crossings.** Every pair of land locations of different landmasses that a gap of at most
  ``CROSSING_PX`` pixels (the game's widest crossing) divides, through a sea cell, is a crossing:
  its two points are where the gap is narrowest.

Everything is integer arithmetic (the distances are exact, in eighths of a pixel) and a square
root of an exact integer, so the result is the same on every platform; nothing is random, and
ties go to the lower number.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.progress import checkpoint
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Landmasses closer than this (pixels of water between them) are pinched, to this width.
NEAR_PX: Final[int] = 36
STRAIT_PX: Final[int] = 5
# The widest crossing of the game's own map, in pixels [V-LOCAL C245].
CROSSING_PX: Final[int] = 9
# Land smaller than this is no landmass for a strait.
MIN_LAND_PX: Final[int] = 2000
EIGHTHS: Final[int] = 8
STRIP: Final[int] = 1024
# The growth tapers off between one and this many gaps from the middle of the strait.
TAPER_GAPS: Final[int] = 2


@dataclass(frozen=True, slots=True)
class Gap:
    """The narrowest stretch of water between two labels along a row or a column.

    ``axis`` is 0 for a row of the raster, 1 for a column; ``line`` the row or column; ``start``
    and ``stop`` the positions along it of the last pixel of the first label and of the first pixel
    of the second; ``length`` the pixels of water between them.
    """

    first: int
    second: int
    length: int
    axis: int
    line: int
    start: int
    stop: int
    through: int


def narrow_gaps(
    labels: NDArray[np.int32],
    water: NDArray[np.bool_],
    wanted: NDArray[np.bool_],
    max_gap: int,
    *,
    through: NDArray[np.int32] | None = None,
) -> dict[tuple[int, int], Gap]:
    """The narrowest gap, by pair of labels, of a run of at most ``max_gap`` pixels of water.

    A gap is a run of water along a row or a column with a different ``wanted`` label at each end.
    ``wanted`` says by label which labels count. ``through`` (the labels by default) is what
    names the water in the middle of the run.
    """
    found: dict[tuple[int, int], Gap] = {}
    middle = labels if through is None else through
    for axis in (0, 1):
        length = int(labels.shape[1 - axis])
        for first in range(0, int(labels.shape[axis]), STRIP):
            checkpoint()
            stop = min(int(labels.shape[axis]), first + STRIP)
            block = (
                (labels[first:stop], water[first:stop], middle[first:stop])
                if axis == 0
                else (
                    labels[:, first:stop].T,
                    water[:, first:stop].T,
                    middle[:, first:stop].T,
                )
            )
            _scan(block, wanted, max_gap, axis, first, length, found)
    return found


def _scan(  # noqa: PLR0913, PLR0917 - a scan reads its block, filter, axis and where it sits.
    block: tuple[NDArray[np.int32], NDArray[np.bool_], NDArray[np.int32]],
    wanted: NDArray[np.bool_],
    max_gap: int,
    axis: int,
    offset: int,
    length: int,
    found: dict[tuple[int, int], Gap],
) -> None:
    labels, water, middle = block
    pad = np.zeros((labels.shape[0], 1), dtype=np.int8)
    edges = np.diff(np.concatenate([pad, water.astype(np.int8), pad], axis=1), axis=1)
    rows, starts = np.nonzero(edges == 1)
    ends = np.nonzero(edges == -1)[1]
    runs = ends - starts
    keep = (runs <= max_gap) & (starts > 0) & (ends < length)
    rows, starts, ends, runs = rows[keep], starts[keep], ends[keep], runs[keep]
    left, right = labels[rows, starts - 1], labels[rows, ends]
    good = (left >= 0) & (right >= 0) & (left != right)
    good[good] = wanted[left[good]] & wanted[right[good]]
    for row, begin, end, run, one, two in zip(
        rows[good].tolist(),
        starts[good].tolist(),
        ends[good].tolist(),
        runs[good].tolist(),
        left[good].tolist(),
        right[good].tolist(),
        strict=True,
    ):
        pair = (min(one, two), max(one, two))
        known = found.get(pair)
        line = row + offset
        if known is None or (run, axis, line) < (known.length, known.axis, known.line):
            first, second = (one, two) if one < two else (two, one)
            at = int(middle[row, (begin + end) // 2])
            a, b = (begin - 1, end) if one < two else (end, begin - 1)
            found[pair] = Gap(first, second, run, axis, line, a, b, at)


def pinch(
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    off_limits: NDArray[np.bool_],
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], int]:
    """Land and ocean with the near landmasses brought together to straits; how many were made.

    ``off_limits`` are the pixels that may not become land (the edge of the domain).
    """
    comps = label_components(land.astype(np.int32))
    sizes = np.bincount(comps.ravel())
    labels = np.where(land, comps, -1).astype(np.int32)
    del comps
    wanted = sizes >= MIN_LAND_PX
    gaps = narrow_gaps(labels, ocean, wanted, NEAR_PX)
    land, ocean = land.copy(), ocean.copy()
    made = 0
    for gap in sorted(gaps.values(), key=lambda item: (item.length, item.first, item.second)):
        if gap.length <= CROSSING_PX:
            continue
        checkpoint()
        made += _carve(gap, labels, land, ocean, off_limits)
    return land, ocean, made


def _window(gap: Gap, shape: tuple[int, int]) -> tuple[slice, slice, tuple[int, int]]:
    reach = TAPER_GAPS * gap.length + gap.length // 2 + 4
    middle = (gap.start + gap.stop) // 2
    row, column = (gap.line, middle) if gap.axis == 0 else (middle, gap.line)
    rows = slice(max(0, row - reach), min(shape[0], row + reach + 1))
    columns = slice(max(0, column - reach), min(shape[1], column + reach + 1))
    return rows, columns, (row - rows.start, column - columns.start)


def _carve(
    gap: Gap,
    labels: NDArray[np.int32],
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    off_limits: NDArray[np.bool_],
) -> int:
    """Narrow the gap to a strait if it can be done safely; 1 when it was, else 0."""
    rows, columns, (row, column) = _window(gap, (int(labels.shape[0]), int(labels.shape[1])))
    mask = labels[rows, columns]
    here, there = mask == gap.first, mask == gap.second
    water = ocean[rows, columns]
    others = land[rows, columns] & ~here & ~there
    limit = EIGHTHS * (gap.length + 2 * STRAIT_PX)
    near_first, near_second = euclidean_distance(here, limit), euclidean_distance(there, limit)
    nearest = int((near_first + near_second)[water].min(initial=limit * 2))
    # The centres of the two shores are one pixel more apart than the water between them.
    spread = (nearest - EIGHTHS * (STRAIT_PX + 1)) // 2
    if spread <= EIGHTHS:
        return 0
    taper = _taper(mask.shape, (row, column), gap.length)
    grow = spread * taper // EIGHTHS_TAPER
    free = water & ~off_limits[rows, columns]
    clear = euclidean_distance(others, limit) > EIGHTHS * (STRAIT_PX + 1)
    grown_first = free & clear & (near_first <= grow)
    grown_second = free & clear & (near_second <= grow)
    if not _safe(
        here | grown_first, there | grown_second, water & ~(grown_first | grown_second), water
    ):
        return 0
    inside = labels[rows, columns]
    inside[grown_first] = gap.first
    inside[grown_second] = gap.second
    land[rows, columns] |= grown_first | grown_second
    ocean[rows, columns] &= ~(grown_first | grown_second)
    return 1


EIGHTHS_TAPER: Final[int] = 1 << 10


def _taper(shape: tuple[int, int], middle: tuple[int, int], gap: int) -> NDArray[np.int64]:
    """How much of the growth reaches each pixel, out of ``EIGHTHS_TAPER``: all of it within one
    gap of the middle of the strait, none farther than ``TAPER_GAPS`` gaps."""
    rows = np.arange(shape[0], dtype=np.int64)[:, np.newaxis] - middle[0]
    columns = np.arange(shape[1], dtype=np.int64)[np.newaxis, :] - middle[1]
    away = np.floor(np.sqrt((rows * rows + columns * columns).astype(np.float64))).astype(np.int64)
    inner, outer = gap, TAPER_GAPS * gap
    return np.clip((outer - away) * EIGHTHS_TAPER // max(1, outer - inner), 0, EIGHTHS_TAPER)


def _safe(
    first: NDArray[np.bool_],
    second: NDArray[np.bool_],
    water_after: NDArray[np.bool_],
    water_before: NDArray[np.bool_],
) -> bool:
    """The two landmasses still apart, and no water cut off from the rest of the window's."""
    touching = (
        (first[:, :-1] & second[:, 1:]).any()
        or (second[:, :-1] & first[:, 1:]).any()
        or (first[:-1] & second[1:]).any()
        or (second[:-1] & first[1:]).any()
    )
    if touching:
        return False
    return _closed_water(water_after) <= _closed_water(water_before)


def _closed_water(water: NDArray[np.bool_]) -> int:
    """How many pieces of water do not reach the edge of the window."""
    parts = label_components(water.astype(np.int32))
    edge = np.zeros(parts.shape, dtype=bool)
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    reaching = np.unique(parts[edge & water])
    pieces = np.unique(parts[water])
    return int(np.count_nonzero(~np.isin(pieces, reaching)))
