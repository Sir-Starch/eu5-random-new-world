"""Deterministic raster topology: label adjacency and 4-connected components."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

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


def unpack_pairs(pairs: NDArray[np.int64]) -> list[tuple[int, int]]:
    """Expand packed pairs into Python tuples in sorted order."""
    mask = np.int64((1 << 32) - 1)
    return list(zip((pairs >> PAIR_SHIFT).tolist(), (pairs & mask).tolist(), strict=True))


def _find(parent: list[int], item: int) -> int:
    while parent[item] != item:
        parent[item] = parent[parent[item]]
        item = parent[item]
    return item


def label_components(labels: NDArray[np.int32], *, wrap_x: bool = False) -> NDArray[np.int64]:
    """Number 4-connected equal-label components in raster order of first pixel.

    Horizontal runs are joined with a union-find whose root is always the smallest
    run index, so the numbering is independent of hash order and platform.
    """
    height, width = labels.shape
    if labels.size == 0:
        return np.zeros(labels.shape, dtype=np.int64)
    starts = np.ones(labels.shape, dtype=bool)
    starts[:, 1:] = labels[:, 1:] != labels[:, :-1]
    run_of = np.cumsum(starts.ravel(), dtype=np.int64).reshape(height, width) - 1
    run_count = int(run_of[-1, -1]) + 1
    same = labels[1:] == labels[:-1]
    first = [run_of[:-1][same]]
    second = [run_of[1:][same]]
    if wrap_x and width > 1:
        seam = labels[:, -1] == labels[:, 0]
        first.append(run_of[:, -1][seam])
        second.append(run_of[:, 0][seam])
    joined = np.unique(np.concatenate(first) * run_count + np.concatenate(second))
    parent = list(range(run_count))
    for upper, lower in zip(
        (joined // run_count).tolist(), (joined % run_count).tolist(), strict=True
    ):
        root_a = _find(parent, upper)
        root_b = _find(parent, lower)
        if root_a != root_b:
            parent[max(root_a, root_b)] = min(root_a, root_b)
    roots = np.array([_find(parent, item) for item in range(run_count)], dtype=np.int64)
    _, component_of_run = np.unique(roots, return_inverse=True)
    return component_of_run.astype(np.int64)[run_of]


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
