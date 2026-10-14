"""Offline invariants for generated worlds, with one typed error per failure class."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

import numpy as np

from rnw.model import PARENT_LEVELS, CellClass, World
from rnw.topology import adjacency_pairs, component_counts, label_components, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

IDENTIFIER: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
COLOR_LIMIT: Final[int] = 1 << 24
PERMILLE: Final[int] = 1000
NO_COLORS: Final[frozenset[int]] = frozenset()


class ValidationError(Exception):
    """A world violates an invariant required before export."""


@dataclass(frozen=True, slots=True)
class DuplicateKeyError(ValidationError):
    """Two cells share a key."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Duplicate cell key: {self.key}"


@dataclass(frozen=True, slots=True)
class InvalidKeyError(ValidationError):
    """A cell key is not a plain script identifier."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Invalid cell key: {self.key!r}"


@dataclass(frozen=True, slots=True)
class DuplicateColorError(ValidationError):
    """Two cells, or a cell and a reserved declaration, share a colour."""

    color: int

    @override
    def __str__(self) -> str:
        return f"Duplicate or reserved colour: {self.color:06X}"


@dataclass(frozen=True, slots=True)
class UnexpectedLabelError(ValidationError):
    """The raster contains a value that is not a declared cell."""

    count: int

    @override
    def __str__(self) -> str:
        return f"Raster has {self.count} pixels without a declared cell"


@dataclass(frozen=True, slots=True)
class VanishedCellError(ValidationError):
    """A declared cell owns no pixel."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Cell has no pixels: {self.key}"


@dataclass(frozen=True, slots=True)
class DisconnectedCellError(ValidationError):
    """A cell is split into more 4-connected parts than allowed."""

    key: str
    components: int

    @override
    def __str__(self) -> str:
        return f"Cell {self.key} has {self.components} disconnected parts"


@dataclass(frozen=True, slots=True)
class BrokenParentError(ValidationError):
    """A parent name is invalid or has two different parents."""

    name: str

    @override
    def __str__(self) -> str:
        return f"Broken parent hierarchy at: {self.name}"


@dataclass(frozen=True, slots=True)
class OrphanSeaError(ValidationError):
    """A sea cell cannot be reached by sea from an ocean anchor."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Sea cell is not connected to the ocean anchors: {self.key}"


@dataclass(frozen=True, slots=True)
class ProtectedPixelChangedError(ValidationError):
    """A pixel owned by a protected cell differs from the base world."""

    count: int

    @override
    def __str__(self) -> str:
        return f"{self.count} protected pixels changed"


@dataclass(frozen=True, slots=True)
class ProtectedCellChangedError(ValidationError):
    """A protected cell's identity or attributes changed."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Protected cell changed: {self.key}"


def check_identity(world: World, reserved_colors: frozenset[int] = NO_COLORS) -> None:
    """Keys and colours are unique; generated cells avoid reserved colours."""
    keys: set[str] = set()
    colors: set[int] = set()
    for cell in world.cells:
        if IDENTIFIER.fullmatch(cell.key) is None:
            raise InvalidKeyError(cell.key)
        if cell.key in keys:
            raise DuplicateKeyError(cell.key)
        keys.add(cell.key)
        reserved = not cell.protected and cell.color in reserved_colors
        if cell.color in colors or reserved or not 0 <= cell.color < COLOR_LIMIT:
            raise DuplicateColorError(cell.color)
        colors.add(cell.color)


def check_hierarchy(world: World) -> None:
    """Every parent name is an identifier and has exactly one parent of its own."""
    upward: dict[tuple[int, str], str] = {}
    for cell in world.cells:
        chain = cell.parents.chain()
        for level, name in enumerate(chain):
            if IDENTIFIER.fullmatch(name) is None:
                where = f"{cell.key}.{PARENT_LEVELS[level]}"
                raise BrokenParentError(where)
            if level + 1 < len(chain):
                previous = upward.setdefault((level, name), chain[level + 1])
                if previous != chain[level + 1]:
                    raise BrokenParentError(name)


def check_raster(world: World, base: World | None = None) -> NDArray[np.int64]:
    """Labels are declared; cells are nonempty and no more fragmented than allowed.

    Generated cells must be one 4-connected part. A protected cell may not have more
    parts than in ``base``. Returns per-cell pixel counts.
    """
    labels = world.labels
    invalid = int(np.count_nonzero((labels < 0) | (labels >= len(world.cells))))
    if invalid:
        raise UnexpectedLabelError(invalid)
    counts = np.bincount(labels.ravel(), minlength=len(world.cells)).astype(np.int64)
    for index in np.flatnonzero(counts == 0).tolist():
        raise VanishedCellError(world.cells[index].key)
    parts = component_counts(labels, wrap_x=world.wrap_x, label_count=len(world.cells))
    allowed = np.ones(len(world.cells), dtype=np.int64)
    if base is not None:
        base_parts = component_counts(base.labels, wrap_x=base.wrap_x, label_count=len(base.cells))
        allowed[: len(base.cells)] = np.maximum(allowed[: len(base.cells)], base_parts)
    for index in np.flatnonzero(parts > allowed).tolist():
        raise DisconnectedCellError(world.cells[index].key, int(parts[index]))
    return counts


def check_sea_reachability(world: World) -> None:
    """Every sea cell is reachable from an ocean anchor through sea-sea contacts."""
    sea = world.class_table(CellClass.SEA)
    neighbours: dict[int, list[int]] = {}
    for first, second in world.edges():
        if sea[first] and sea[second]:
            neighbours.setdefault(first, []).append(second)
            neighbours.setdefault(second, []).append(first)
    seen = {anchor for anchor in world.anchors if sea[anchor]}
    queue = deque(sorted(seen))
    while queue:
        for neighbour in neighbours.get(queue.popleft(), []):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    for index in np.flatnonzero(sea).tolist():
        if index not in seen:
            raise OrphanSeaError(world.cells[index].key)


def check_protected(world: World, base: World) -> None:
    """Protected cells keep their identity and exact pixel sets."""
    if world.labels.shape != base.labels.shape or len(world.cells) < len(base.cells):
        raise ProtectedPixelChangedError(int(world.labels.size))
    for index, cell in enumerate(base.cells):
        if cell.protected and world.cells[index] != cell:
            raise ProtectedCellChangedError(cell.key)
    protected = base.protected_table()
    was = protected[base.labels]
    now = np.zeros(world.labels.shape, dtype=bool)
    in_base = world.labels < len(base.cells)
    now[in_base] = protected[world.labels[in_base]]
    changed = (was | now) & (world.labels != base.labels)
    if np.any(changed):
        raise ProtectedPixelChangedError(int(np.count_nonzero(changed)))


def validate_world(
    world: World, *, base: World | None = None, reserved_colors: frozenset[int] = NO_COLORS
) -> None:
    """Run all generic invariants in a fixed order; raise the first failure."""
    check_identity(world, reserved_colors)
    check_hierarchy(world)
    _ = check_raster(world, base)
    check_sea_reachability(world)
    if base is not None:
        check_protected(world, base)


def topology_metrics(world: World, island_px: int) -> dict[str, int]:
    """Integer land/sea metrics for comparing seeds and presets."""
    water = world.water_table()[world.labels]
    land = ~water
    masses = label_components(land.astype(np.int32), wrap_x=world.wrap_x)
    sizes = np.bincount(masses[land]) if np.any(land) else np.zeros(0, dtype=np.int64)
    sizes = sizes[sizes > 0]
    land_px = int(np.count_nonzero(land))
    coast = int(np.count_nonzero(land[:, 1:] != land[:, :-1])) + int(
        np.count_nonzero(land[1:] != land[:-1])
    )
    largest = int(sizes.max()) if sizes.size else 0
    by_class = {kind: int(np.count_nonzero(world.class_table(kind))) for kind in CellClass}
    return {
        "pixels": int(world.labels.size),
        "land_px": land_px,
        "land_permille": land_px * PERMILLE // int(world.labels.size),
        "landmasses": int(sizes.size),
        "islands": int(np.count_nonzero(sizes < island_px)),
        "largest_landmass_permille": largest * PERMILLE // max(1, land_px),
        "coast_edges": coast,
        "cells": len(world.cells),
        "land_cells": by_class[CellClass.LAND],
        "sea_cells": by_class[CellClass.SEA],
        "lake_cells": by_class[CellClass.LAKE],
        "cell_edges": len(unpack_pairs(adjacency_pairs(world.labels, wrap_x=world.wrap_x))),
    }


@dataclass(frozen=True, slots=True)
class IneligibleChangeError(ValidationError):
    """A changed pixel involves a cell that was not allowed to change."""

    count: int

    @override
    def __str__(self) -> str:
        return f"{self.count} changed pixels involve ineligible cells"


@dataclass(frozen=True, slots=True)
class AdjacencyChangedError(ValidationError):
    """Cells gained or lost a contact."""

    added: int
    removed: int

    @override
    def __str__(self) -> str:
        return f"Cell adjacency changed: {self.added} added, {self.removed} removed"


def check_boundary_move(  # noqa: PLR0913 - each table is a separate invariant input.
    before: NDArray[np.int32],
    after: NDArray[np.int32],
    *,
    keys: tuple[str, ...],
    editable: NDArray[np.bool_],
    enclosed: NDArray[np.bool_],
    frozen: NDArray[np.bool_],
) -> dict[str, int]:
    """Verify an ID-preserving boundary edit of one raster window.

    ``editable`` marks labels allowed to change; ``enclosed`` marks labels whose every
    pixel and neighbour lies inside the window, so their topology is fully visible.
    Frozen pixels must be identical, changed cells must stay nonempty and no more
    fragmented, and the 4- and 8-neighbour contact sets must be identical.
    """
    changed = before != after
    if np.any(changed & frozen):
        raise ProtectedPixelChangedError(int(np.count_nonzero(changed & frozen)))
    involved = np.concatenate([before[changed], after[changed]])
    bad = ~(editable[involved] & enclosed[involved])
    if np.any(bad):
        raise IneligibleChangeError(int(np.count_nonzero(bad)))
    touched = np.unique(involved)
    size = editable.size
    new_counts = np.bincount(after.ravel(), minlength=size)
    for label in touched[new_counts[touched] == 0].tolist():
        raise VanishedCellError(keys[int(label)])
    if touched.size:
        old_parts = component_counts(before, label_count=size)
        new_parts = component_counts(after, label_count=size)
        for label in touched[new_parts[touched] > old_parts[touched]].tolist():
            raise DisconnectedCellError(keys[int(label)], int(new_parts[label]))
    for diagonal in (False, True):
        old_pairs = adjacency_pairs(before, diagonal=diagonal)
        new_pairs = adjacency_pairs(after, diagonal=diagonal)
        if not np.array_equal(old_pairs, new_pairs):
            added = np.setdiff1d(new_pairs, old_pairs).size
            removed = np.setdiff1d(old_pairs, new_pairs).size
            raise AdjacencyChangedError(int(added), int(removed))
    return {
        "changed_px": int(np.count_nonzero(changed)),
        "touched_cells": int(touched.size),
        "cell_contacts_4": int(adjacency_pairs(before).size),
        "cell_contacts_8": int(adjacency_pairs(before, diagonal=True).size),
    }
