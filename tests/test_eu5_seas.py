"""The water of a generated world in the game's files: port rows, currents, and what is checked."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_seas import (
    Coast,
    SeaError,
    VanillaPort,
    Water,
    current_text,
    foreign_coast,
    read_currents,
    read_ports,
    verify_seas,
)
from rnw.model import CellClass
from rnw.ports import ForeignCoast
from rnw.seas import Topography, analyse
from tests.block_worlds import block_world

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map
    from rnw.newworld import NewWorld

PORTS = """LandProvince;SeaZone;x;y;
stockholm;stockholms_skargard;8532;6945;x
bermuda;bermuda_island;4734;5162;x
"""
TEMPLATES = (
    "north_eastern_atlantic20 = { topography = deep_ocean climate = arctic"
    " movement_assistance = { -94.62 20.70 }}\n"
    "coast_zone = { topography = coastal_ocean climate = arctic }\n"
    "atlantic_gulf_stream5 = { topography = deep_ocean climate = tropical"
    " movement_assistance = { 109.62 28.82 }}\n"
    "inland = { topography = inland_sea climate = arctic }\n"
)


def test_ports_are_read_by_land_location_with_the_coordinates_as_written() -> None:
    ports = read_ports(PORTS)
    assert ports == {
        "stockholm": VanillaPort("stockholms_skargard", "8532", "6945"),
        "bermuda": VanillaPort("bermuda_island", "4734", "5162"),
    }


def test_only_deep_ocean_zones_with_a_current_give_one() -> None:
    assert read_currents(TEMPLATES) == {
        "north_eastern_atlantic20": (-9462, 2070),
        "atlantic_gulf_stream5": (10962, 2882),
    }


def test_a_current_is_written_as_the_game_writes_it() -> None:
    assert current_text((-9107, 503)) == "movement_assistance = { -91.07 5.03 }"
    assert current_text((5, -7)) == "movement_assistance = { 0.05 -0.07 }"
    assert current_text((10962, 2882)) == "movement_assistance = { 109.62 28.82 }"


def _map(keys: list[str], classes: list[CellClass]) -> Eu5Map:
    return cast("Eu5Map", cast("object", SimpleNamespace(keys=tuple(keys), classes=tuple(classes))))


def test_vanilla_land_whose_sea_was_replaced_is_free_and_the_rest_is_held() -> None:
    world = block_world(["...", "..."], block=2)
    game_map = _map(
        ["bermuda", "stockholm", "kerguelen", "bermuda_island"],
        [CellClass.LAND, CellClass.LAND, CellClass.NON_OWNABLE, CellClass.SEA],
    )
    contacts = {(0, 0), (0, 1), (1, 2), (2, 3), (3, 4)}
    ports = read_ports(PORTS)
    coast = foreign_coast(game_map, world, contacts, ports, removed={"bermuda_island"})
    assert coast.free == {"bermuda": frozenset({0, 1})}
    assert coast.held == frozenset({2})


def _world_with_ports() -> tuple[NewWorld, Plan]:
    layout = ["AAAAAAA", "1111111", "2222222", "3333333", "4444444"]
    world = block_world(layout, block=2)
    kinds = world.classes
    cells = [
        PlannedCell(
            key=f"rnw_{'loc' if kind is CellClass.LAND else 'sea'}_{index:05d}",
            name="x",
            color=index + 1,
            kind=kind,
            province="p",
            area="a",
            region="r",
            subcontinent="s",
            continent="c",
        )
        for index, kind in enumerate(kinds)
    ]
    return world, Plan(cells=cells)


def _written(plan: Plan, water: Water, *, drop: str = "") -> tuple[str, str]:
    lines: list[str] = []
    for number, planned in enumerate(plan.cells):
        if planned.kind is CellClass.SEA:
            kind = water.waters.topography[number]
            current = f" {current_text(water.flows[number])}" if number in water.flows else ""
            lines.append(f"{planned.key} = {{ topography = {kind}{current} }}")
    templates = "\n".join(lines) + "\n"
    ports = "LandProvince;SeaZone;x;y;\n"
    land = next(c for c in plan.cells if c.kind is CellClass.LAND)
    sea = [c for c in plan.cells if c.kind is CellClass.SEA]
    ports += f"{land.key};{sea[0].key};1;1;x\n"
    return ports.replace(drop, "") if drop else ports, templates


def _water(world: NewWorld) -> Water:
    waters = analyse(world)
    flows = {
        number: (9200, 0)
        for number in waters.sea()
        if waters.topography[number] is Topography.DEEP_OCEAN
    }
    return Water(waters, flows)


def test_written_ports_and_templates_that_hold_what_was_planned_pass() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates = _written(plan, water)
    coast = Coast(world, ForeignCoast(), {}, 0)
    assert verify_seas((ports, templates), plan, world, coast, water)["currents"] == len(
        water.flows
    )


def test_a_land_cell_that_touches_the_sea_has_a_port_or_the_export_stops() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    _, templates = _written(plan, water)
    coast = Coast(world, ForeignCoast(), {}, 0)
    with pytest.raises(SeaError, match="has no port"):
        _ = verify_seas(("LandProvince;SeaZone;x;y;\n", templates), plan, world, coast, water)


def test_a_port_to_a_sea_the_land_does_not_touch_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    _, templates = _written(plan, water)
    land = next(c for c in plan.cells if c.kind is CellClass.LAND)
    far = [c for c in plan.cells if c.kind is CellClass.SEA][-1]
    ports = f"LandProvince;SeaZone;x;y;\n{land.key};{far.key};1;1;x\n"
    coast = Coast(world, ForeignCoast(), {}, 0)
    with pytest.raises(SeaError, match="does not touch"):
        _ = verify_seas((ports, templates), plan, world, coast, water)


def test_a_land_named_twice_in_the_ports_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates = _written(plan, water)
    coast = Coast(world, ForeignCoast(), {}, 0)
    row = ports.splitlines()[1]
    with pytest.raises(SeaError, match="twice"):
        _ = verify_seas((ports + row + "\n", templates), plan, world, coast, water)


def test_a_deep_zone_without_its_current_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates = _written(plan, water)
    first = next(iter(water.flows))
    broken = templates.replace(f" {current_text(water.flows[first])}", "", 1)
    coast = Coast(world, ForeignCoast(), {}, 0)
    with pytest.raises(SeaError, match="current"):
        _ = verify_seas((ports, broken), plan, world, coast, water)


def test_a_zone_written_as_another_topography_than_planned_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates = _written(plan, water)
    coast = Coast(world, ForeignCoast(), {}, 0)
    broken = templates.replace("coastal_ocean", "ocean", 1)
    with pytest.raises(SeaError, match="not written as"):
        _ = verify_seas((ports, broken), plan, world, coast, water)
