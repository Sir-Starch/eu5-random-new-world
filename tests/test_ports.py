"""Ports of a generated coast: one per land, one at least for every coastal sea zone."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import pytest

from rnw.model import CellClass
from rnw.ports import ForeignCoast, PortError, plan_ports, served, settle_seas
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
