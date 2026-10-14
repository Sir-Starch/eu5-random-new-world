"""Game-independent world model: identified raster cells, classes and parents.

A world is a label raster whose values index ``cells``. Cells carry a semantic key, a
unique colour, a land/water class and a five-level parent chain. Protected cells come
from a fixed base (for EU5, the Old World) and must not change; unprotected cells may
be newly generated, which keeps the model ready for new IDs (T3) even though the first
EU5 exporter only moves pixels between existing IDs (T2).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray


class CellClass(StrEnum):
    """Land/water role of a cell, mirroring the observed EU5 class lists."""

    LAND = "land"
    SEA = "sea"
    LAKE = "lake"
    WASTELAND = "wasteland"
    NON_OWNABLE = "non_ownable"


WATER_CLASSES: Final[frozenset[CellClass]] = frozenset({CellClass.SEA, CellClass.LAKE})
PARENT_LEVELS: Final[tuple[str, ...]] = (
    "province",
    "area",
    "region",
    "subcontinent",
    "continent",
)


@dataclass(frozen=True, slots=True)
class Parents:
    """The five parent names of a location, from smallest to largest."""

    province: str
    area: str
    region: str
    subcontinent: str
    continent: str

    def chain(self) -> tuple[str, str, str, str, str]:
        """Return parents ordered from province to continent."""
        return (self.province, self.area, self.region, self.subcontinent, self.continent)


@dataclass(frozen=True, slots=True)
class Cell:
    """One semantic location or water body."""

    key: str
    color: int
    cell_class: CellClass
    parents: Parents
    protected: bool = False

    @property
    def is_water(self) -> bool:
        """Whether ships rather than armies occupy the cell."""
        return self.cell_class in WATER_CLASSES


@dataclass(frozen=True, slots=True, eq=False)
class World:
    """Integer-coordinate world: a label raster plus its cells and ocean anchors."""

    labels: NDArray[np.int32]
    cells: tuple[Cell, ...]
    anchors: frozenset[int]
    wrap_x: bool = False

    @property
    def height(self) -> int:
        """Raster rows."""
        return int(self.labels.shape[0])

    @property
    def width(self) -> int:
        """Raster columns."""
        return int(self.labels.shape[1])

    def water_table(self) -> NDArray[np.bool_]:
        """Per-cell water flags, indexable by the label raster."""
        return np.array([cell.is_water for cell in self.cells], dtype=bool)

    def class_table(self, kind: CellClass) -> NDArray[np.bool_]:
        """Per-cell flags for one class."""
        return np.array([cell.cell_class is kind for cell in self.cells], dtype=bool)

    def protected_table(self) -> NDArray[np.bool_]:
        """Per-cell protection flags."""
        return np.array([cell.protected for cell in self.cells], dtype=bool)

    def edges(self) -> list[tuple[int, int]]:
        """Undirected 4-neighbour cell graph, sorted."""
        return unpack_pairs(adjacency_pairs(self.labels, wrap_x=self.wrap_x))
