"""Deterministic raster topology: label adjacency and 4-connected components."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import _native

if TYPE_CHECKING:
    from numpy.typing import NDArray

PAIR_SHIFT = np.int64(32)


def _packed(a: NDArray[np.int32], b: NDArray[np.int32]) -> NDArray[np.int64]:
    differ = a != b
    low = np.minimum(a[differ], b[differ]).astype(np.int64)
    high = np.maximum(a[differ], b[differ]).astype(np.int64)
    return (low << PAIR_SHIFT) | high


def adjacency_pairs(
    labels: NDArray[np.int32], *, wrap_x: bool = False, diagonal: bool = False
) -> NDArray[np.int64]:
    """Return sorted unique touching label pairs packed as ``low << 32 | high``.

    Pairs are 4-neighbour contacts; ``diagonal`` adds corner contacts. ``wrap_x``
    joins the first and last columns like a horizontally wrapping world map.
    """
    parts = [_packed(labels[:, :-1], labels[:, 1:]), _packed(labels[:-1], labels[1:])]
    if diagonal:
        parts.append(_packed(labels[:-1, :-1], labels[1:, 1:]))
        parts.append(_packed(labels[:-1, 1:], labels[1:, :-1]))
    if wrap_x and labels.shape[1] > 1:
        parts.append(_packed(labels[:, -1], labels[:, 0]))
        if diagonal:
            parts.append(_packed(labels[:-1, -1], labels[1:, 0]))
            parts.append(_packed(labels[:-1, 0], labels[1:, -1]))
    return np.unique(np.concatenate(parts))


def adjacency_lengths(
    labels: NDArray[np.int32],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Sorted unique touching label pairs (packed like ``adjacency_pairs``) and their lengths.

    A length is the number of 4-neighbour pixel contacts between the two labels.
    """
    packed = np.concatenate(
        [_packed(labels[:, :-1], labels[:, 1:]), _packed(labels[:-1], labels[1:])]
    )
    pairs, lengths = np.unique(packed, return_counts=True)
    return pairs, lengths.astype(np.int64)


def unpack_pairs(pairs: NDArray[np.int64]) -> list[tuple[int, int]]:
    """Expand packed pairs into Python tuples in sorted order."""
    mask = np.int64((1 << 32) - 1)
    return list(zip((pairs >> PAIR_SHIFT).tolist(), (pairs & mask).tolist(), strict=True))


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
    sources: NDArray[np.bool_], limit: int, *, octagonal: bool = False
) -> NDArray[np.int32]:
    """Step distance to the nearest source pixel, capped at ``limit``.

    Steps are 4-neighbour; ``octagonal`` also allows diagonal steps on every second
    round, which approximates Euclidean distance better than the diamond metric.
    """
    return _native.distance_from(
        np.ascontiguousarray(sources, dtype=np.bool_), int(limit), octagonal
    )
