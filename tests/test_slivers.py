"""Cells cut thin between other cells join a neighbour; a strait between land stays."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.synth import merge_slivers


def _two_cells_and_a_needle() -> np.ndarray:
    labels = np.zeros((60, 200), dtype=np.int32)
    labels[:, 100:] = 1
    labels[:, 98:102] = 2  # a needle four pixels wide between two cells
    return labels


def test_a_needle_between_two_cells_joins_the_neighbour_it_shares_most_with() -> None:
    labels = _two_cells_and_a_needle()
    merged = merge_slivers(labels, 10.0, 400)
    assert len(set(np.unique(merged).tolist())) == 2
    assert merged[30, 99] in (0, 1)
    assert merged[30, 10] == 0
    assert merged[30, 150] == 1


def test_a_cell_as_thick_as_the_limit_stays() -> None:
    labels = np.zeros((60, 200), dtype=np.int32)
    labels[:, 100:] = 1
    labels[:, 90:110] = 2
    assert set(np.unique(merge_slivers(labels, 10.0, 400)).tolist()) == {0, 1, 2}


def test_a_strait_between_land_stays() -> None:
    labels = np.full((60, 200), -1, dtype=np.int32)
    labels[:, :80] = 0
    labels[:, 120:] = 1
    labels[:, 80:84] = 2  # four pixels wide, but bordered by land on one side
    labels[28:32, 84:120] = 3  # a channel four pixels wide between land (-1)
    assert 3 in np.unique(merge_slivers(labels, 10.0, 400)).tolist()


def test_merging_slivers_is_deterministic_and_keeps_the_land() -> None:
    labels = _two_cells_and_a_needle()
    labels[:5] = -1
    first = merge_slivers(labels, 10.0, 400)
    assert np.array_equal(first, merge_slivers(labels, 10.0, 400))
    assert np.array_equal(first >= 0, labels >= 0)


def test_a_sliver_never_joins_a_neighbour_that_touches_the_outside_when_it_does_not() -> None:
    labels = _two_cells_and_a_needle()
    outer = np.zeros(labels.shape, dtype=bool)
    outer[:, 199] = True  # cell 1 touches the outside of the generated world
    merged = merge_slivers(labels, 10.0, 400, outer)
    assert merged[30, 99] == 0
    # A sliver that itself touches the outside may join either neighbour.
    outer[:, 99] = True
    assert merge_slivers(labels, 10.0, 400, outer)[30, 99] in (0, 1)
