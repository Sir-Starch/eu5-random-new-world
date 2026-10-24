"""Straits: narrow channels between near landmasses, and the gaps that crossings are read from."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.straits import (
    CROSSING_PX,
    MIN_LAND_PX,
    NEAR_PX,
    STRAIT_PX,
    _closed_water,  # pyright: ignore[reportPrivateUsage]
    _safe,  # pyright: ignore[reportPrivateUsage]
    narrow_gaps,
    pinch,
)
from rnw.topology import label_components

SIZE = 240


def _blocks(gap: int, *, rows: int = 80) -> tuple[np.ndarray, np.ndarray]:
    """Two blocks of land (``rows`` tall, 80 wide) ``gap`` pixels apart, in an ocean."""
    land = np.zeros((SIZE, SIZE), dtype=bool)
    land[60 : 60 + rows, 30:110] = True
    land[60 : 60 + rows, 110 + gap : 190 + gap] = True
    return land, ~land


def _gaps(land: np.ndarray, ocean: np.ndarray, widest: int = SIZE) -> list[int]:
    comps = label_components(land.astype(np.int32))
    labels = np.where(land, comps, -1).astype(np.int32)
    wanted = np.bincount(comps.ravel()) >= MIN_LAND_PX
    return sorted(gap.length for gap in narrow_gaps(labels, ocean, wanted, widest).values())


def test_the_narrowest_run_of_water_between_two_labels_is_a_gap() -> None:
    labels = np.full((12, 20), -1, dtype=np.int32)
    labels[:, :5] = 1
    labels[:, 11:] = 2
    labels[0:3, 5:8] = 1  # a headland that narrows the gap in the first rows
    water = labels < 0
    gaps = narrow_gaps(labels, water, np.array([False, True, True]), 10)
    gap = gaps[(1, 2)]
    assert (gap.length, gap.axis, gap.line) == (3, 0, 0)
    assert (gap.start, gap.stop) == (7, 11)
    assert gap.through == -1


def test_a_gap_is_found_along_a_column_as_along_a_row() -> None:
    labels = np.full((20, 9), -1, dtype=np.int32)
    labels[:6] = 3
    labels[10:] = 4
    gap = narrow_gaps(labels, labels < 0, np.ones(5, dtype=bool), 10)[(3, 4)]
    assert (gap.length, gap.axis, gap.start, gap.stop) == (4, 1, 5, 10)


def test_labels_that_do_not_count_and_the_same_label_make_no_gap() -> None:
    labels = np.full((8, 20), -1, dtype=np.int32)
    labels[:, :4] = 1
    labels[:, 10:14] = 2
    labels[:, 17:] = 1
    water = labels < 0
    gaps = narrow_gaps(labels, water, np.array([False, True, False]), 10)
    assert gaps == {}
    both = narrow_gaps(labels, water, np.array([False, True, True]), 10)
    assert set(both) == {(1, 2)}
    assert both[(1, 2)].length == 3  # the narrower of the two gaps between them


def test_a_run_longer_than_the_most_asked_is_no_gap() -> None:
    land, ocean = _blocks(40)
    assert _gaps(land, ocean, 39) == []
    assert _gaps(land, ocean, 40) == [40]


def test_near_landmasses_are_brought_together_to_a_strait() -> None:
    land, ocean = _blocks(NEAR_PX - 6)
    narrowed, water, made = pinch(land, ocean, np.zeros_like(land))
    assert made == 1
    (width,) = _gaps(narrowed, water)
    assert STRAIT_PX <= width <= STRAIT_PX + 1 < CROSSING_PX
    assert narrowed.sum() > land.sum()
    assert not (narrowed & water).any()
    assert (narrowed | water).all()
    assert land[narrowed ^ land].sum() == 0  # land only grows


def test_the_landmasses_stay_two_and_the_sea_one() -> None:
    land, ocean = _blocks(NEAR_PX - 6)
    narrowed, water, _ = pinch(land, ocean, np.zeros_like(land))
    assert (
        label_components(narrowed.astype(np.int32)).max()
        == label_components(land.astype(np.int32)).max()
    )
    seas = label_components(water.astype(np.int32))
    assert len(np.unique(seas[water])) == 1


def test_the_growth_tapers_off_so_the_shores_far_from_the_strait_keep_their_shape() -> None:
    land, ocean = _blocks(NEAR_PX - 6, rows=160)
    narrowed, _, _ = pinch(land, ocean, np.zeros_like(land))
    added = narrowed & ~land
    rows = np.flatnonzero(added.any(axis=1))
    # The strait is at the first of the equally narrow rows; the growth does not reach the far end.
    assert rows.max() - rows.min() < 4 * NEAR_PX
    assert rows.max() < 60 + 160 // 2


def test_land_that_is_already_a_crossing_apart_or_too_far_apart_is_left() -> None:
    for gap in (CROSSING_PX, NEAR_PX + 1):
        land, ocean = _blocks(gap)
        narrowed, water, made = pinch(land, ocean, np.zeros_like(land))
        assert made == 0
        assert np.array_equal(narrowed, land)
        assert np.array_equal(water, ocean)


def test_small_land_is_no_landmass_for_a_strait() -> None:
    land = np.zeros((SIZE, SIZE), dtype=bool)
    land[60:140, 30:110] = True
    land[90:100, 130:140] = True  # an islet of 100 pixels
    assert land.sum() > MIN_LAND_PX
    narrowed, _, made = pinch(land, ~land, np.zeros_like(land))
    assert made == 0
    assert np.array_equal(narrowed, land)


def test_no_land_is_added_where_the_area_is_off_limits() -> None:
    land, ocean = _blocks(NEAR_PX - 6)
    off = np.zeros_like(land)
    off[:, 100:140] = True
    narrowed, _, made = pinch(land, ocean, off)
    assert not (narrowed & ~land & off).any()
    assert made in {0, 1}


def test_a_third_landmass_is_never_joined_to_the_growth() -> None:
    land, ocean = _blocks(NEAR_PX - 6)
    land[150:210, 100:140] = True  # a third landmass close below the strait
    ocean = ~land
    narrowed, water, _ = pinch(land, ocean, np.zeros_like(land))
    parts = label_components(narrowed.astype(np.int32))
    assert len(np.unique(parts[narrowed])) == len(
        np.unique(label_components(land.astype(np.int32))[land])
    )
    assert water.sum() > 0


def test_the_result_is_the_same_every_time() -> None:
    land, ocean = _blocks(NEAR_PX - 6)
    first = pinch(land, ocean, np.zeros_like(land))
    second = pinch(land, ocean, np.zeros_like(land))
    assert np.array_equal(first[0], second[0])
    assert first[2] == second[2]


def test_closed_water_is_water_that_does_not_reach_the_edge() -> None:
    water = np.ones((20, 20), dtype=bool)
    water[5:15, 5:15] = False
    water[8:12, 8:12] = True
    assert _closed_water(water) == 1
    water[5:15, 5:15] = True
    assert _closed_water(water) == 0


def test_a_pinch_that_joins_the_landmasses_or_closes_a_sea_is_unsafe() -> None:
    water = np.ones((20, 20), dtype=bool)
    first = np.zeros((20, 20), dtype=bool)
    second = np.zeros((20, 20), dtype=bool)
    first[5:10, 2:8] = True
    second[5:10, 9:15] = True
    assert _safe(first, second, water & ~(first | second), water)
    second[5:10, 8:15] = True
    assert not _safe(first, second, water & ~(first | second), water)
    first = np.zeros((20, 20), dtype=bool)
    first[2:8, 2:8] = True
    ring = np.zeros((20, 20), dtype=bool)
    ring[10:16, 10:16] = True
    ring[12:14, 12:14] = False
    pocket = ~ring
    pocket[12:14, 12:14] = True
    assert not _safe(first, ring, pocket & ~first, water)
