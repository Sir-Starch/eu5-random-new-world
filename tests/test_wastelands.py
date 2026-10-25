"""Impassable location units respect connectivity and biome boundaries."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.hierarchy import contact_graph, pieces, split
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.wastelands import location_units


def test_only_connected_compatible_wastelands_are_one_unit() -> None:
    labels = np.array([[0, 1, 2, 3], [4, 1, 2, 5]], dtype=np.int32)
    kinds = (CellClass.WASTELAND,) * 4 + (CellClass.LAND, CellClass.WASTELAND)
    world = derive_world(labels, kinds, np.full(labels.shape, 18000, dtype=np.int32))
    attrs = [("cold", "forest", "mountains", "")] * 6
    attrs[2] = ("cold", "sparse", "mountains", "")
    got = location_units(world, attrs)
    assert got.owner == (0, 0, 2, 3, 4, 3)
    assert got.members[0] == (0, 1)
    assert got.members[3] == (3, 5)
    assert got.centres[0].tolist() == [0, 0]  # weighted by pixels, not cell count
    assert (0, 2) in got.edges
    assert (2, 3) in got.edges
    assert (0, 0) not in got.edges
    assert (
        got.owner == location_units(replace(world, edges=tuple(reversed(world.edges))), attrs).owner
    )
    assert np.array_equal(world.labels, labels)
    assert np.all(world.elevation == 18000)


def test_diagonal_wastes_and_water_never_merge() -> None:
    labels = np.array([[0, 1], [2, 3]], dtype=np.int32)
    world = derive_world(
        labels,
        (CellClass.WASTELAND, CellClass.SEA, CellClass.LAKE, CellClass.WASTELAND),
        np.zeros(labels.shape, dtype=np.int32),
    )
    assert location_units(world, [("same",)] * 4).owner == (0, 1, 2, 3)
    with pytest.raises(ValueError, match="signature"):
        _ = location_units(world, [])


def test_administrative_partition_cannot_cut_a_large_wasteland() -> None:
    labels = np.arange(60, dtype=np.int32).reshape(6, 10)
    kinds = tuple(CellClass.WASTELAND if 2 <= i % 10 <= 6 else CellClass.LAND for i in range(60))
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    units = location_units(world, [("one biome",)] * 60)
    keep = [cell == owner for cell, owner in enumerate(units.owner)]
    graph = contact_graph(units.centres, units.edges, keep)
    parts = split(graph, [i for i, flag in enumerate(keep) if flag], 5)
    expanded = [[i for unit in part for i in units.members[unit]] for part in parts]
    owners = {cell: part for part, cells in enumerate(expanded) for cell in cells}
    assert len({owners[i] for i, kind in enumerate(kinds) if kind is CellClass.WASTELAND}) == 1
    original = contact_graph(world.centroids, world.edges, [True] * 60)
    assert all(len(pieces(original, part)) == 1 for part in expanded)
