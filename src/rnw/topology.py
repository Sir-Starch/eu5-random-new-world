"""Deterministic raster topology: label adjacency and 4-connected components."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native

if TYPE_CHECKING:
    from numpy.typing import NDArray

PAIR_SHIFT = np.int64(32)
LOW_BITS = np.int64((1 << 32) - 1)
WITHIN_STEP: Final[int] = 4
WITHIN_EIGHTHS: Final[int] = 8


def adjacency_pairs(
    labels: NDArray[np.int32], *, wrap_x: bool = False, diagonal: bool = False
) -> NDArray[np.int64]:
    """Return sorted unique touching label pairs packed as ``low << 32 | high``.

    Pairs are 4-neighbour contacts; ``diagonal`` adds corner contacts. ``wrap_x``
    joins the first and last columns like a horizontally wrapping world map. The kernel is
    Rust (ADR 0005), its NumPy specification is ``tests/reference/topology.py``.
    """
    return _native.adjacency_pairs(np.ascontiguousarray(labels, dtype=np.int32), wrap_x, diagonal)


def adjacency_lengths(
    labels: NDArray[np.int32],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Sorted unique touching label pairs (packed like ``adjacency_pairs``) and their lengths.

    A length is the number of 4-neighbour pixel contacts between the two labels.
    """
    return _native.adjacency_lengths(np.ascontiguousarray(labels, dtype=np.int32))


def unpack_pairs(pairs: NDArray[np.int64]) -> list[tuple[int, int]]:
    """Expand packed pairs into Python tuples in sorted order."""
    return list(zip((pairs >> PAIR_SHIFT).tolist(), (pairs & LOW_BITS).tolist(), strict=True))


def label_components(labels: NDArray[np.int32], *, wrap_x: bool = False) -> NDArray[np.int32]:
    """Number 4-connected equal-label components in raster order of first pixel.

    Horizontal runs are joined with a union-find whose root is always the smallest run
    index, so the numbering is independent of hash order and platform.
    """
    if labels.size == 0:
        return np.zeros(labels.shape, dtype=np.int32)
    return _native.label_components(np.ascontiguousarray(labels, dtype=np.int32), wrap_x)


def component_counts(
    labels: NDArray[np.int32], *, wrap_x: bool = False, label_count: int | None = None
) -> NDArray[np.int64]:
    """Count 4-connected components per label index."""
    components = label_components(labels, wrap_x=wrap_x)
    total = int(components.max()) + 1 if components.size else 0
    owner = np.zeros(total, dtype=np.int64)
    owner[components.ravel()] = labels.ravel()
    size = label_count if label_count is not None else int(labels.max()) + 1
    return np.bincount(owner, minlength=size).astype(np.int64)


def nearest_label(
    labels: NDArray[np.int32], sources: NDArray[np.bool_], limit: int
) -> NDArray[np.int32]:
    """Spread the labels of ``sources`` pixels outwards by up to ``limit`` 4-steps.

    Pixels farther than ``limit`` keep -1. A pixel reached by several labels in the same
    step takes the label of the lowest-index neighbour that reached it, so the result
    does not depend on platform or hash order.
    """
    return _native.nearest_label(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(sources, dtype=np.bool_),
        int(limit),
    )


def euclidean_distance(sources: NDArray[np.bool_], limit: int) -> NDArray[np.int64]:
    """Exact Euclidean distance to the nearest source, in eighths of a pixel.

    Distances beyond ``limit`` are capped there. The square root of an exact integer is
    correctly rounded in IEEE arithmetic, so results are identical on every platform.
    """
    return _native.euclidean_distance(np.ascontiguousarray(sources, dtype=np.bool_), int(limit))


def distance_from(
    sources: NDArray[np.bool_], limit: int, *, octagonal: bool = False, wrap_x: bool = False
) -> NDArray[np.int32]:
    """Step distance to the nearest source pixel, capped at ``limit``.

    Steps are 4-neighbour; ``octagonal`` also allows diagonal steps on every second
    round, which approximates Euclidean distance better than the diamond metric.
    With ``wrap_x`` the left and right columns touch; the poles stay separate.
    """
    return _native.distance_from(
        np.ascontiguousarray(sources, dtype=np.bool_), int(limit), octagonal, wrap_x
    )


def within(sources: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Pixels at most ``radius`` pixels (Euclidean) from a source pixel.

    Computed on blocks of ``WITHIN_STEP`` pixels, so a source counts for its whole block (up to
    three pixels of extra reach) and the contour is exact to a block. Sources are pooled with
    ``any``, so no island of a pixel or two is lost. The distances are those of the blocks round
    the sources' bounding box, a block beyond the reach on each side: every block farther out is
    beyond the radius, so the result is the same as over the whole raster.
    """
    height, width = sources.shape
    out = np.zeros((height, width), dtype=bool)
    rows = np.flatnonzero(sources.any(axis=1))
    if rows.size == 0:
        return out
    columns = np.flatnonzero(sources[int(rows[0]) : int(rows[-1]) + 1].any(axis=0))
    limit = radius // WITHIN_STEP
    reach = limit + 1
    blocks = (-(-height // WITHIN_STEP), -(-width // WITHIN_STEP))
    top = max(0, int(rows[0]) // WITHIN_STEP - reach) * WITHIN_STEP
    left = max(0, int(columns[0]) // WITHIN_STEP - reach) * WITHIN_STEP
    bottom = min(height, (min(blocks[0], int(rows[-1]) // WITHIN_STEP + 1 + reach)) * WITHIN_STEP)
    right = min(width, (min(blocks[1], int(columns[-1]) // WITHIN_STEP + 1 + reach)) * WITHIN_STEP)
    window = sources[top:bottom, left:right]
    down, across = -(-window.shape[0] // WITHIN_STEP), -(-window.shape[1] // WITHIN_STEP)
    padded = np.zeros((down * WITHIN_STEP, across * WITHIN_STEP), dtype=bool)
    padded[: window.shape[0], : window.shape[1]] = window
    pooled = padded.reshape(down, WITHIN_STEP, across, WITHIN_STEP).any(axis=3).any(axis=1)
    del padded
    near = euclidean_distance(pooled, limit + 1) <= WITHIN_EIGHTHS * limit
    grown = np.repeat(np.repeat(near, WITHIN_STEP, axis=0), WITHIN_STEP, axis=1)
    out[top:bottom, left:right] = grown[: bottom - top, : right - left]
    return out
