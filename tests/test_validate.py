"""Deliberately corrupted synthetic worlds must fail with typed errors."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.model import Cell, CellClass, Parents, World
from rnw.settings import build_settings
from rnw.synth import generate_world, synthetic_base
from rnw.validate import (
    AdjacencyChangedError,
    BrokenParentError,
    DisconnectedCellError,
    DuplicateColorError,
    DuplicateKeyError,
    IneligibleChangeError,
    InvalidKeyError,
    OrphanSeaError,
    ProtectedPixelChangedError,
    UnexpectedLabelError,
    ValidationError,
    VanishedCellError,
    check_boundary_move,
    validate_world,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

SETTINGS = build_settings("continents")
BASE = synthetic_base(SETTINGS.synthetic)
WORLD = generate_world(2, SETTINGS)
FIRST_GENERATED = sum(cell.protected for cell in WORLD.cells)


def _with(
    world: World,
    *,
    labels: NDArray[np.int32] | None = None,
    cells: tuple[Cell, ...] | None = None,
) -> World:
    return World(
        world.labels.copy() if labels is None else labels,
        world.cells if cells is None else cells,
        world.anchors,
        wrap_x=world.wrap_x,
    )


def _interior_pixel(world: World, kind: CellClass) -> tuple[int, int, int]:
    """A pixel whose 3x3 neighbourhood is one generated cell of ``kind``."""
    labels = world.labels
    table = world.class_table(kind)
    for row in range(1, world.height - 1):
        for column in range(1, world.width - 1):
            label = int(labels[row, column])
            block = labels[row - 1 : row + 2, column - 1 : column + 2]
            if label >= FIRST_GENERATED and table[label] and bool(np.all(block == label)):
                return row, column, label
    message = "fixture has no interior pixel"
    raise AssertionError(message)


def test_clean_world_passes() -> None:
    """The unmodified fixture is valid against its protected base."""
    validate_world(WORLD, base=BASE)


def test_orphan_sea_fails() -> None:
    """A sea cell enclosed by land cannot be reached from the ocean anchors."""
    row, column, _ = _interior_pixel(WORLD, CellClass.LAND)
    orphan = Cell("rnw_orphan", 0x123456, CellClass.SEA, WORLD.cells[-1].parents)
    labels = WORLD.labels.copy()
    labels[row, column] = len(WORLD.cells)
    with pytest.raises(OrphanSeaError):
        validate_world(_with(WORLD, labels=labels, cells=(*WORLD.cells, orphan)), base=BASE)


def test_duplicate_color_fails() -> None:
    """Two cells with the same colour are rejected."""
    cells = list(WORLD.cells)
    cells[-1] = replace(cells[-1], color=cells[-2].color)
    with pytest.raises(DuplicateColorError):
        validate_world(_with(WORLD, cells=tuple(cells)), base=BASE)


def test_reserved_color_fails() -> None:
    """A generated cell may not reuse a reserved (for example unused vanilla) colour."""
    with pytest.raises(DuplicateColorError):
        validate_world(WORLD, base=BASE, reserved_colors=frozenset({WORLD.cells[-1].color}))


def test_duplicate_and_invalid_keys_fail() -> None:
    """Keys must be unique script identifiers."""
    cells = list(WORLD.cells)
    cells[-1] = replace(cells[-1], key=cells[-2].key)
    with pytest.raises(DuplicateKeyError):
        validate_world(_with(WORLD, cells=tuple(cells)), base=BASE)
    cells[-1] = replace(cells[-1], key="bad key")
    with pytest.raises(InvalidKeyError):
        validate_world(_with(WORLD, cells=tuple(cells)), base=BASE)


def test_broken_parent_fails() -> None:
    """A province that appears under two areas is a broken hierarchy."""
    cells = list(WORLD.cells)
    index = FIRST_GENERATED
    sibling = next(
        position
        for position, cell in enumerate(cells)
        if position != index and cell.parents.province == cells[index].parents.province
    )
    parents = cells[sibling].parents
    cells[sibling] = replace(cells[sibling], parents=replace(parents, area="rnw_other_area"))
    with pytest.raises(BrokenParentError):
        validate_world(_with(WORLD, cells=tuple(cells)), base=BASE)
    cells[sibling] = replace(cells[sibling], parents=Parents("", "a", "r", "s", "c"))
    with pytest.raises(BrokenParentError):
        validate_world(_with(WORLD, cells=tuple(cells)), base=BASE)


def test_changed_protected_pixel_fails() -> None:
    """Moving one Old World sea pixel to a generated neighbour is detected."""
    labels = WORLD.labels.copy()
    column = SETTINGS.synthetic.width - SETTINGS.synthetic.old_world_columns
    row = 0
    labels[row, column] = labels[row, column - 1]
    with pytest.raises(ProtectedPixelChangedError):
        validate_world(_with(WORLD, labels=labels), base=BASE)


def test_vanished_disconnected_and_unknown_labels_fail() -> None:
    """Empty cells, split cells and undeclared raster values are rejected."""
    spare = Cell("rnw_empty", 0x654321, CellClass.LAND, WORLD.cells[-1].parents)
    with pytest.raises(VanishedCellError):
        validate_world(_with(WORLD, cells=(*WORLD.cells, spare)), base=BASE)
    row, column, label = _interior_pixel(WORLD, CellClass.LAND)
    labels = WORLD.labels.copy()
    labels[row, column] = (label + 7) % len(WORLD.cells)
    with pytest.raises(ValidationError):
        validate_world(_with(WORLD, labels=labels), base=BASE)
    labels = WORLD.labels.copy()
    labels[row, column] = len(WORLD.cells)
    with pytest.raises(UnexpectedLabelError):
        validate_world(_with(WORLD, labels=labels), base=BASE)


def test_split_generated_cell_fails() -> None:
    """A stray pixel of a cell inside another cell makes it disconnected."""
    row, column, label = _interior_pixel(WORLD, CellClass.LAND)
    other = next(
        index
        for index in range(FIRST_GENERATED, len(WORLD.cells))
        if index != label and WORLD.cells[index].cell_class is CellClass.LAND
    )
    labels = WORLD.labels.copy()
    labels[row, column] = other
    with pytest.raises(DisconnectedCellError):
        validate_world(_with(WORLD, labels=labels), base=BASE)


BOUNDARY_BEFORE = np.array(
    [
        [0, 0, 1, 1, 1],
        [0, 0, 1, 1, 1],
        [0, 0, 0, 0, 0],
        [2, 2, 2, 2, 2],
    ],
    dtype=np.int32,
)
KEYS = ("land", "sea", "other")
ALL = np.ones(3, dtype=bool)
NONE_FROZEN = np.zeros(BOUNDARY_BEFORE.shape, dtype=bool)


def test_boundary_move_accepts_contact_preserving_edit() -> None:
    """Moving one land pixel into the sea keeps every contact."""
    after = BOUNDARY_BEFORE.copy()
    after[0, 1] = 1
    result = check_boundary_move(
        BOUNDARY_BEFORE, after, keys=KEYS, editable=ALL, enclosed=ALL, frozen=NONE_FROZEN
    )
    assert result["changed_px"] == 1


def test_boundary_move_rejects_frozen_ineligible_and_new_contacts() -> None:
    """Frozen pixels, locked cells and new cell contacts are all detected."""
    after = BOUNDARY_BEFORE.copy()
    after[0, 1] = 1
    frozen = NONE_FROZEN.copy()
    frozen[0, 1] = True
    with pytest.raises(ProtectedPixelChangedError):
        _ = check_boundary_move(
            BOUNDARY_BEFORE, after, keys=KEYS, editable=ALL, enclosed=ALL, frozen=frozen
        )
    locked = np.array([True, False, True])
    with pytest.raises(IneligibleChangeError):
        _ = check_boundary_move(
            BOUNDARY_BEFORE, after, keys=KEYS, editable=locked, enclosed=ALL, frozen=NONE_FROZEN
        )
    touching = BOUNDARY_BEFORE.copy()
    touching[2, 4] = 1
    with pytest.raises(AdjacencyChangedError):
        _ = check_boundary_move(
            BOUNDARY_BEFORE, touching, keys=KEYS, editable=ALL, enclosed=ALL, frozen=NONE_FROZEN
        )
