"""Ports of a generated coast: one per land, one at least for every coastal sea zone."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world
from rnw.ports import ForeignCoast, PortError, plan_ports, relabel, served, settle_seas
from tests.block_worlds import block_world, cell


def test_a_land_serves_the_sea_it_touches_longest_when_nothing_competes() -> None:
    links = {0: {10: 5, 11: 3}, 1: {11: 4}}
    plan = plan_ports(links, needed={10, 11})
    assert plan.port == {0: 10, 1: 11}
    assert plan.unserved == ()


def test_a_sea_takes_a_land_that_another_sea_can_do_without() -> None:
    """Land 0 would serve sea 11 (its longest border) but land 1 can serve only that sea."""
    links = {0: {10: 3, 11: 5}, 1: {11: 2}}
    plan = plan_ports(links, needed={10, 11})
    assert plan.port == {0: 10, 1: 11}
    assert plan.unserved == ()


def test_serving_a_sea_can_move_a_chain_of_other_seas() -> None:
    """Seas 10 to 12 and lands 0 to 2 form a chain; the only full assignment shifts all three."""
    links = {0: {10: 9, 11: 1}, 1: {11: 9, 12: 1}, 2: {12: 9}}
    plan = plan_ports(links, needed={10, 11, 12})
    assert plan.port == {0: 10, 1: 11, 2: 12}
    assert plan.unserved == ()


def test_a_sea_with_no_land_of_its_own_is_unserved_and_a_land_still_has_a_port() -> None:
    links = {0: {10: 5, 11: 3}}
    plan = plan_ports(links, needed={10, 11})
    assert plan.unserved == (11,)
    assert plan.port == {0: 10}


def test_the_plan_does_not_depend_on_the_order_of_its_inputs() -> None:
    links = {2: {12: 4, 10: 4}, 0: {10: 4, 11: 4}, 1: {11: 4, 12: 4}}
    first = plan_ports(links, needed=[10, 11, 12])
    second = plan_ports(dict(reversed(links.items())), needed=[12, 11, 10])
    assert first == second


def test_land_with_two_coastal_neighbours_leaves_one_sea_zone_a_port_of_its_own() -> None:
    """One land touches three sea cells in a row: they become one zone, which the land serves."""
    world = block_world(["AAA", "..."], block=2)
    assert len(served(world, ForeignCoast()).unserved) == 2
    settled = settle_seas(world)
    assert settled.merged == 2
    assert settled.world.classes == (CellClass.LAND, CellClass.SEA)
    assert settled.cell_of == (0, 1, 1, 1)
    assert not served(settled.world, ForeignCoast()).unserved
    assert settled.world.pixels.tolist() == [world.pixels[0], world.pixels[1:].sum()]


def test_a_settled_world_is_the_world_itself() -> None:
    world = block_world(["#.#"], block=2)
    settled = settle_seas(world)
    assert settled.world is world
    assert settled.merged == 0
    assert settled.cell_of == (0, 1, 2)


def test_small_open_water_fragment_folds_into_its_broadest_sea_neighbour() -> None:
    labels = np.zeros((6, 9), dtype=np.int32)
    labels[:, 6:] = 1
    labels[3, 5] = 2
    world = derive_world(labels, (CellClass.SEA,) * 3, np.zeros_like(labels))
    settled = settle_seas(world, minimum_sea=5)
    assert settled.merged == 1
    assert settled.cell_of == (0, 1, 0)
    assert settled.world.pixels.tolist() == [36, 18]


def test_water_beside_only_wasteland_or_a_lake_needs_no_port() -> None:
    """The engine names a sea zone without a port only beside land (C232)."""
    world = block_world(["w.k", "###"], block=2)
    sea = cell(["w.k", "###"], 0, 1)
    assert sea not in served(world, ForeignCoast()).unserved
    assert settle_seas(world).world is world


def test_the_cells_round_a_vanilla_islet_share_its_one_port() -> None:
    """Four sea cells touch land of the game that can serve one of them: they become one."""
    world = block_world(["..", ".."], block=2)
    islet = ForeignCoast(free={"bermuda": frozenset({0, 1, 2, 3})})
    assert len(served(world, islet).unserved) == 3
    settled = settle_seas(world, islet)
    assert settled.world.classes == (CellClass.SEA,)
    assert settled.foreign.free == {"bermuda": frozenset({0})}
    assert not served(settled.world, settled.foreign).unserved


def test_water_beside_vanilla_land_with_a_port_of_its_own_cannot_be_settled() -> None:
    world = block_world(["..", ".."], block=2)
    with pytest.raises(PortError, match="vanilla land"):
        _ = settle_seas(world, ForeignCoast(held=frozenset({0})))


def test_shared_coast_can_follow_contiguous_water_to_a_port() -> None:
    world = block_world(["...A"], block=2)
    settled = settle_seas(world, ForeignCoast(held=frozenset({0})), shared_coast=True)
    assert settled.cell_of == (0, 0, 0, 1)
    assert served(settled.world, settled.foreign).port == {1: 0}


def test_shared_coast_cannot_cross_wasteland_to_find_a_port() -> None:
    world = block_world([".w.A"], block=2)
    with pytest.raises(PortError, match="vanilla land"):
        _ = settle_seas(world, ForeignCoast(held=frozenset({0})), shared_coast=True)


def test_the_second_sea_zone_of_a_land_joins_the_first_not_the_open_sea() -> None:
    """A land touches two sea cells, one open sea lies beyond: the two share the land's port."""
    layout = ["A.1", "A.1"]
    world = block_world(layout, block=2)
    settled = settle_seas(world)
    assert settled.merged == 1
    assert settled.cell_of == (0, 1, 2, 1)
    assert settled.world.classes == (CellClass.LAND, CellClass.SEA, CellClass.SEA)
    assert not served(settled.world, ForeignCoast()).unserved
    open_sea = cell(layout, 0, 2)
    assert settled.cell_of[open_sea] == 2


def test_settling_changes_no_pixel_of_land_and_none_outside_the_merged_cells() -> None:
    world = block_world(["AAA", "...", "444"], block=2)
    settled = settle_seas(world)
    land = world.labels == 0
    assert (settled.world.labels[land] == 0).all()
    assert (settled.world.labels >= 0).all()
    assert settled.world.labels.shape == world.labels.shape
    assert int(settled.world.pixels.sum()) == int(world.pixels.sum())


def test_folding_sea_cells_renumbers_the_barrier_with_the_land() -> None:
    labels = np.arange(4, dtype=np.int32).reshape(1, 4)
    kinds = (CellClass.SEA, CellClass.SEA, CellClass.LAND, CellClass.LAND)
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    world = replace(world, barrier=np.array([2, 3], dtype=np.int64))
    folded, cell_of = relabel(world, {0: 1})
    assert cell_of == (0, 0, 1, 2)
    assert folded.barrier.tolist() == [1, 2]
    assert [folded.classes[cell] for cell in folded.barrier.tolist()] == [CellClass.LAND] * 2


def test_folding_sea_cells_keeps_the_area_planned_for_each_cell() -> None:
    labels = np.arange(4, dtype=np.int32).reshape(1, 4)
    kinds = (CellClass.SEA, CellClass.SEA, CellClass.LAND, CellClass.LAND)
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    world = replace(world, planned=np.array([0, 0, 70, 90], dtype=np.int64))
    folded, _ = relabel(world, {0: 1})
    assert folded.planned is not None
    assert folded.planned.tolist() == [0, 70, 90]


def test_dissolving_gives_an_unserved_cell_to_the_two_served_cells_beside_it() -> None:
    """One land touches the cell in the middle and the cells at its sides, another one the right
    side: the middle cell is unserved, and its pixels go half and half to its neighbours."""
    world = block_world(["AAB", "123"], block=6)
    assert served(world, ForeignCoast()).unserved == (3,)
    merged = settle_seas(world)
    assert merged.world.pixels.tolist() == [72, 36, 72, 36]  # folded whole into one side
    dissolved = settle_seas(world, dissolve=True)
    assert dissolved.merged == 1
    assert dissolved.world.pixels.tolist() == [72, 36, 54, 54]
    assert dissolved.cell_of == (0, 1, 2, 2, 3)
    assert not served(dissolved.world, ForeignCoast()).unserved
    land = world.labels < 2
    assert np.array_equal(dissolved.world.labels[land], world.labels[land])


def test_the_halves_of_a_dissolved_cell_are_each_one_piece_beside_their_taker() -> None:
    world = block_world(["AAB", "123"], block=6)
    dissolved = settle_seas(world, dissolve=True).world
    left, right = int(dissolved.labels[11, 0]), int(dissolved.labels[11, 17])
    assert left != right
    assert (dissolved.labels[6:, :9] == left).all()
    assert (dissolved.labels[6:, 9:] == right).all()


def test_a_cell_with_one_served_neighbour_is_still_folded_into_it() -> None:
    world = block_world(["ABB", "123"], block=6)
    assert settle_seas(world, dissolve=True).world.pixels.tolist() == (
        settle_seas(world).world.pixels.tolist()
    )


def test_a_cell_that_foreign_land_touches_is_not_dissolved() -> None:
    world = block_world(["AAB", "123"], block=6)
    foreign = ForeignCoast(held=frozenset({3}))
    folded = settle_seas(world, foreign, dissolve=True)
    assert folded.world.pixels.tolist() == settle_seas(world, foreign).world.pixels.tolist()


def test_dissolving_does_not_change_a_settled_world() -> None:
    world = block_world(["#.#"], block=6)
    assert settle_seas(world, dissolve=True).world is world


def test_a_dissolved_world_is_the_same_whichever_way_it_is_asked() -> None:
    world = block_world(["AAB", "123"], block=6)
    first = settle_seas(world, dissolve=True)
    second = settle_seas(world, dissolve=True)
    assert first.cell_of == second.cell_of
    assert np.array_equal(first.world.labels, second.world.labels)


def _grid_with_a_small_piece() -> NewWorld:
    """Land A over twelve columns and B over six; below them a piece of two columns (``t``), then
    the seas ``1``, ``2`` and ``3`` six columns wide each. A touches ``t``, ``1`` and ``2``, B
    only ``3``."""
    labels = np.zeros((6, 20), dtype=np.int32)
    labels[:3, 14:] = 1
    labels[3:, :2] = 2
    labels[3:, 2:8] = 3
    labels[3:, 8:14] = 4
    labels[3:, 14:] = 5
    kinds = (CellClass.LAND, CellClass.LAND) + (CellClass.SEA,) * 4
    return derive_world(labels, kinds, np.zeros_like(labels))


def test_a_small_piece_is_folded_first_and_the_cell_that_cannot_be_served_is_divided() -> None:
    world = _grid_with_a_small_piece()
    settled = settle_seas(world, minimum_sea=10, dissolve=True)
    assert settled.world.classes == (CellClass.LAND, CellClass.LAND, CellClass.SEA, CellClass.SEA)
    assert not served(settled.world, ForeignCoast()).unserved
    labels = settled.world.labels
    # the piece went with the sea beside it, the cell in the middle was shared by both sides
    assert (labels[3:, :11] == labels[3, 0]).all()
    assert (labels[3:, 11:] == labels[3, 19]).all()
    assert settled.cell_of[2] == settled.cell_of[3] == int(labels[3, 0])
    assert settled.cell_of[4] in {int(labels[3, 0]), int(labels[3, 19])}
    assert settled.merged == 2


def test_with_small_pieces_and_no_dissolving_the_cell_is_folded_whole_as_before() -> None:
    world = _grid_with_a_small_piece()
    settled = settle_seas(world, minimum_sea=10)
    # the piece and the unserved middle cell both went whole to the left
    assert settled.world.pixels.tolist() == [42, 18, 42, 18]
    assert settled.cell_of == (0, 1, 2, 2, 2, 3)
    assert not served(settled.world, ForeignCoast()).unserved
