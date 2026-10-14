"""Coast movement keeps cell topology and stays within its displacement bound."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.coast import RING_OK, move_coast
from rnw.model import CellClass
from rnw.noise import fractal_noise
from rnw.settings import build_settings
from rnw.synth import generate_world
from rnw.validate import check_boundary_move

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.coast import CoastResult
    from rnw.settings import CoastSettings

SETTINGS = build_settings("archipelago")
WORLD = generate_world(6, SETTINGS)
PROTECTED = WORLD.protected_table()
LAND_OK = WORLD.class_table(CellClass.LAND) & ~PROTECTED
SEA_OK = WORLD.class_table(CellClass.SEA) & ~PROTECTED
FROZEN = PROTECTED[WORLD.labels]
KEYS = tuple(cell.key for cell in WORLD.cells)


def _move(field: NDArray[np.int64], settings: CoastSettings) -> CoastResult:
    return move_coast(
        WORLD.labels, land_ok=LAND_OK, sea_ok=SEA_OK, frozen=FROZEN, field=field, settings=settings
    )


def _field() -> NDArray[np.int64]:
    return fractal_noise(
        77, 0, 0, WORLD.width, WORLD.height, period=16, octaves=3, persistence_permille=600
    )


def test_ring_table_accepts_only_single_edge_arcs() -> None:
    """Removing the centre must keep the A neighbours 4-connected around the ring."""
    north, north_east, east, south = 1, 2, 4, 16
    assert RING_OK[north | north_east | east]
    assert not RING_OK[north | east]
    assert not RING_OK[north | south]
    assert not RING_OK[0]
    assert not RING_OK[north_east]


def test_moved_coast_preserves_topology_and_protected_pixels() -> None:
    """The independent validator accepts the result; both directions occur."""
    result = _move(_field(), SETTINGS.coast)
    stats = check_boundary_move(
        WORLD.labels,
        result.labels,
        keys=KEYS,
        editable=LAND_OK | SEA_OK,
        enclosed=np.ones(len(KEYS), dtype=bool),
        frozen=FROZEN,
    )
    assert stats["changed_px"] == int(np.count_nonzero(result.to_land | result.to_sea))
    assert np.any(result.to_land)
    assert np.any(result.to_sea)
    assert not np.any(result.to_land & result.to_sea)


def test_displacement_is_bounded_by_pass_count() -> None:
    """A pixel moved in pass k is within k 4-steps of the original boundary."""
    passes = 4
    result = _move(_field(), replace(SETTINGS.coast, passes=passes))
    labels = WORLD.labels
    reach = np.zeros(labels.shape, dtype=bool)
    reach[:, 1:] |= labels[:, 1:] != labels[:, :-1]
    reach[:, :-1] |= labels[:, 1:] != labels[:, :-1]
    reach[1:] |= labels[1:] != labels[:-1]
    reach[:-1] |= labels[1:] != labels[:-1]
    for _ in range(passes - 1):
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        reach = grown
    changed = result.labels != labels
    assert np.any(changed)
    assert not np.any(changed & ~reach)


def test_field_sign_controls_direction_and_zero_passes_do_nothing() -> None:
    """Positive fields only grow land, negative only grow sea."""
    ones = np.full(WORLD.labels.shape, 30_000, dtype=np.int64)
    grow = _move(ones, SETTINGS.coast)
    assert np.any(grow.to_land)
    assert not np.any(grow.to_sea)
    erode = _move(-ones, SETTINGS.coast)
    assert np.any(erode.to_sea)
    assert not np.any(erode.to_land)
    still = _move(ones, replace(SETTINGS.coast, passes=0))
    assert np.array_equal(still.labels, WORLD.labels)


def test_size_floor_and_cap_hold_for_every_cell() -> None:
    """No cell shrinks below or grows above its configured share."""
    coast = SETTINGS.coast
    result = _move(-np.full(WORLD.labels.shape, 30_000, dtype=np.int64), coast)
    before = np.bincount(WORLD.labels.ravel(), minlength=len(KEYS))
    after = np.bincount(result.labels.ravel(), minlength=len(KEYS))
    assert np.all(after * 1000 >= before * coast.min_keep_permille)
    assert np.all(after * 1000 <= before * coast.max_growth_permille)
