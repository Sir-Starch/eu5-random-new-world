"""Small worlds drawn as blocks of characters, for the tests of ports, water and currents."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world

if TYPE_CHECKING:
    from collections.abc import Sequence

# A character of a layout draws a block of one kind. ``#``, ``.``, ``w`` and ``k`` are a cell of
# their own, land, sea, wasteland and lake; a capital letter A to J is one land cell shared by
# every block with that letter, and a digit one sea cell shared the same way.
SINGLE: Final[dict[str, CellClass]] = {
    "#": CellClass.LAND,
    ".": CellClass.SEA,
    "w": CellClass.WASTELAND,
    "k": CellClass.LAKE,
}


def _kind(char: str) -> CellClass:
    if char in SINGLE:
        return SINGLE[char]
    return CellClass.SEA if char.isdigit() else CellClass.LAND


def _numbers(layout: Sequence[str]) -> tuple[list[list[int]], list[CellClass]]:
    names: dict[str, int] = {}
    kinds: list[CellClass] = []
    grid: list[list[int]] = []
    for line in layout:
        row: list[int] = []
        for char in line:
            if char in SINGLE:
                kinds.append(SINGLE[char])
                row.append(len(kinds) - 1)
                continue
            if char not in names:
                names[char] = len(kinds)
                kinds.append(_kind(char))
            row.append(names[char])
        grid.append(row)
    return grid, kinds


def block_world(layout: Sequence[str], *, block: int = 30) -> NewWorld:
    """A world drawn by ``layout``, each character a ``block`` pixels square.

    Cells are numbered in the order of their first block, row by row.
    """
    grid, kinds = _numbers(layout)
    numbers = np.array(grid, dtype=np.int32)
    labels = np.kron(numbers, np.ones((block, block), dtype=np.int32))
    return derive_world(labels, tuple(kinds), np.zeros(labels.shape, dtype=np.int32))


def cell(layout: Sequence[str], row: int, column: int) -> int:
    """The number of the cell drawn at a place of ``layout``."""
    return _numbers(layout)[0][row][column]
