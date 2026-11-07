"""Keep or move island groups on a generated domain (T3, game-independent).

The generation domain covers the island groups of the installed game, so a continent may be
generated over them. A group is a set of pixels (its islands and the small sea zones that touch
them) that stays or moves as one rigid piece. It stays where the generated land lies a coast
margin away from it on open ocean; otherwise it moves to the free ocean nearest to its old
place, by a deterministic search over translations. Moving is a pure translation, so the shape
of the group and the distances between its islands survive.

A group prefers to keep its latitude: a step north or south counts twice a step sideways.
Failing to find a place for a group is an explicit error.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.topology import within

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

BLOCK: Final[int] = 8
LATITUDE_WEIGHT: Final[int] = 4


class PlacementError(ValueError):
    """No free ocean can hold an island group."""


@dataclass(frozen=True, slots=True, eq=False)
class Footprint:
    """The pixels of one island group, in the coordinates of the domain."""

    rows: NDArray[np.int32]
    columns: NDArray[np.int32]

    @property
    def size(self) -> int:
        """Number of pixels."""
        return int(self.rows.size)


def _pooled(mask: NDArray[np.bool_], *, outside: bool = False) -> NDArray[np.bool_]:
    """``mask`` on blocks of ``BLOCK`` pixels, a block set if any of its pixels is.

    Pixels that the last blocks reach past the mask count as ``outside``.
    """
    rows, columns = -(-mask.shape[0] // BLOCK), -(-mask.shape[1] // BLOCK)
    padded = np.full((rows * BLOCK, columns * BLOCK), outside, dtype=bool)
    padded[: mask.shape[0], : mask.shape[1]] = mask
    return padded.reshape(rows, BLOCK, columns, BLOCK).any(axis=(1, 3))


def _pool_into(blocked: NDArray[np.bool_], mask: NDArray[np.bool_]) -> None:
    """``blocked |= _pooled(mask, outside=True)``, over the blocks that hold a pixel of ``mask``.

    The blocks that the last ones reach past the mask are set already: ``blocked`` began as a
    pooled mask with ``outside`` set, and it only grows.
    """
    rows = np.flatnonzero(mask.any(axis=1))
    if rows.size == 0:
        return
    columns = np.flatnonzero(mask[int(rows[0]) : int(rows[-1]) + 1].any(axis=0))
    top, bottom = int(rows[0]) // BLOCK, int(rows[-1]) // BLOCK + 1
    left, right = int(columns[0]) // BLOCK, int(columns[-1]) // BLOCK + 1
    window = mask[top * BLOCK : bottom * BLOCK, left * BLOCK : right * BLOCK]
    blocked[top:bottom, left:right] |= _pooled(window, outside=True)


def _paint(
    shape: tuple[int, int], footprint: Footprint, rows: int = 0, columns: int = 0
) -> NDArray[np.bool_]:
    mask = np.zeros(shape, dtype=bool)
    mask[footprint.rows + rows, footprint.columns + columns] = True
    return mask


def _overlaps(blocked: NDArray[np.bool_], shape: NDArray[np.bool_]) -> NDArray[np.float64]:
    """For each origin, the number of ``blocked`` blocks that ``shape`` covers there."""
    height, width = blocked.shape[0] + shape.shape[0], blocked.shape[1] + shape.shape[1]
    size = (1 << (height - 1).bit_length(), 1 << (width - 1).bit_length())
    spectrum = np.fft.rfft2(blocked.astype(np.float64), size) * np.conj(
        np.fft.rfft2(shape.astype(np.float64), size)
    )
    covered = np.fft.irfft2(spectrum, size)
    return covered[: blocked.shape[0] - shape.shape[0] + 1, : blocked.shape[1] - shape.shape[1] + 1]


def _nearest(blocked: NDArray[np.bool_], footprint: Footprint) -> tuple[int, int] | None:
    """The translation of ``footprint`` to the nearest place free of ``blocked``, in pixels."""
    top = int(footprint.rows.min()) // BLOCK * BLOCK
    left = int(footprint.columns.min()) // BLOCK * BLOCK
    shape = _pooled(
        _paint(
            (int(footprint.rows.max()) - top + 1, int(footprint.columns.max()) - left + 1),
            Footprint(footprint.rows - top, footprint.columns - left),
        )
    )
    if shape.shape[0] > blocked.shape[0] or shape.shape[1] > blocked.shape[1]:
        return None
    free = _overlaps(blocked, shape) < 0.5  # noqa: PLR2004 - counts of blocks are integers
    rows, columns = np.nonzero(free)
    if rows.size == 0:
        return None
    shift_rows, shift_columns = rows * BLOCK - top, columns * BLOCK - left
    cost = LATITUDE_WEIGHT * shift_rows.astype(np.int64) ** 2 + shift_columns.astype(np.int64) ** 2
    best = int(np.argmin(cost))
    return int(shift_rows[best]), int(shift_columns[best])


def place(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    groups: Sequence[Footprint],
    *,
    margin: int,
) -> tuple[tuple[int, int], ...]:
    """The (rows, columns) translation of every group; (0, 0) for a group that stays.

    A group may stand only on ocean at least ``margin`` pixels from land and from what
    lies outside the domain, and ``margin`` from the other groups.
    """
    if not groups:
        return ()
    edge = ~domain
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    forbidden = within(land, margin) | ~ocean | within(edge, margin)
    shape = domain.shape
    moves: list[tuple[int, int] | None] = [None] * len(groups)
    taken = np.zeros(shape, dtype=bool)
    for index, group in enumerate(groups):
        if not forbidden[group.rows, group.columns].any():
            moves[index] = (0, 0)
            taken[group.rows, group.columns] = True
    blocked = _pooled(forbidden | within(taken, margin), outside=True)
    order = sorted(
        (index for index, move in enumerate(moves) if move is None),
        key=lambda index: (-groups[index].size, index),
    )
    for index in order:
        found = _nearest(blocked, groups[index])
        if found is None:
            message = (
                f"No free ocean holds the island group of {groups[index].size} pixels; "
                "lower the land share or try another seed"
            )
            raise PlacementError(message)
        moves[index] = found
        placed = _paint(shape, groups[index], *found)
        _pool_into(blocked, within(placed, margin))
    return tuple(move for move in moves if move is not None)


def carve(
    domain: NDArray[np.bool_], groups: Sequence[Footprint], moves: Sequence[tuple[int, int]]
) -> NDArray[np.bool_]:
    """``domain`` without the pixels of the groups at their places."""
    carved = domain.copy()
    for group, (rows, columns) in zip(groups, moves, strict=True):
        carved[group.rows + rows, group.columns + columns] = False
    return carved
