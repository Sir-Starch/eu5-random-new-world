"""The water of a generated world in the game's files: port rows, currents, and what is checked."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, final

import numpy as np
import pytest

from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import (
    _locator_instances,  # pyright: ignore[reportPrivateUsage]
)
from rnw.eu5_seas import (
    NO_UNITS,
    Coast,
    SeaError,
    VanillaPort,
    VanillaWater,
    Water,
    courses_over,
    crossings,
    current_text,
    foreign_coast,
    read_ports,
    read_waters,
    verify_crossings,
    verify_locators,
    verify_seas,
)
from rnw.model import CellClass
from rnw.ports import ForeignCoast
from rnw.seas import Topography, analyse
from tests.block_worlds import block_world, cell

if TYPE_CHECKING:
    from rnw.currents import Vector
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_seas import Crossing
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


def test_the_topography_and_the_current_of_every_template_are_read() -> None:
    assert read_waters(TEMPLATES) == {
        "north_eastern_atlantic20": VanillaWater("deep_ocean", (-9462, 2070)),
        "coast_zone": VanillaWater("coastal_ocean", None),
        "atlantic_gulf_stream5": VanillaWater("deep_ocean", (10962, 2882)),
        "inland": VanillaWater("inland_sea", None),
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


def _written(plan: Plan, water: Water, *, drop: str = "") -> tuple[str, str, str]:
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
    return ports.replace(drop, "") if drop else ports, templates, _map_text(plan, water)


def _map_text(plan: Plan, water: Water) -> str:
    seas = " ".join(c.key for c in plan.cells if c.kind is CellClass.SEA)
    shut = " ".join(plan.cells[number].key for number in sorted(water.zones))
    return f"sea_zones = {{ {seas} }}\nimpassable_mountains = {{ {shut} }}\n"


def _water(world: NewWorld, *, shut: tuple[int, ...] = (), docks: tuple[int, ...] = ()) -> Water:
    """Every deep cell a lane, but the ``shut`` ones, which are impassable zones."""
    waters = analyse(world)
    deep = [n for n in waters.sea() if waters.topography[n] is Topography.DEEP_OCEAN]
    lanes = frozenset(deep) - set(shut)
    topography = tuple(
        Topography.OCEAN_WASTELAND if n in shut else kind
        for n, kind in enumerate(waters.topography)
    )
    flows: dict[int, Vector] = dict.fromkeys(sorted(lanes), (9200, 0))
    coast = Coast(
        world, ForeignCoast(), {}, {}, frozenset(docks or (max(waters.sea()),)), frozenset(), 0
    )
    return Water(coast, replace(waters, topography=topography), lanes, frozenset(shut), flows, 0, 0)


def test_written_ports_and_templates_that_hold_what_was_planned_pass() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    texts = _written(plan, water)
    assert verify_seas(texts, plan, world, water.coast, water)["currents"] == len(water.flows)


def test_a_land_cell_that_touches_the_sea_has_a_port_or_the_export_stops() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    _, templates, lists = _written(plan, water)
    with pytest.raises(SeaError, match="has no port"):
        _ = verify_seas(
            ("LandProvince;SeaZone;x;y;\n", templates, lists), plan, world, water.coast, water
        )


def test_a_port_to_a_sea_the_land_does_not_touch_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    _, templates, lists = _written(plan, water)
    land = next(c for c in plan.cells if c.kind is CellClass.LAND)
    far = [c for c in plan.cells if c.kind is CellClass.SEA][-1]
    ports = f"LandProvince;SeaZone;x;y;\n{land.key};{far.key};1;1;x\n"
    with pytest.raises(SeaError, match="does not touch"):
        _ = verify_seas((ports, templates, lists), plan, world, water.coast, water)


def test_a_land_named_twice_in_the_ports_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates, lists = _written(plan, water)
    row = ports.splitlines()[1]
    with pytest.raises(SeaError, match="twice"):
        _ = verify_seas((ports + row + "\n", templates, lists), plan, world, water.coast, water)


def test_a_lane_without_its_current_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates, lists = _written(plan, water)
    first = next(iter(water.flows))
    broken = templates.replace(f" {current_text(water.flows[first])}", "", 1)
    with pytest.raises(SeaError, match="current"):
        _ = verify_seas((ports, broken, lists), plan, world, water.coast, water)


def test_a_zone_written_as_another_topography_than_planned_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    ports, templates, lists = _written(plan, water)
    broken = templates.replace("coastal_ocean", "ocean", 1)
    with pytest.raises(SeaError, match="not written as"):
        _ = verify_seas((ports, broken, lists), plan, world, water.coast, water)


def test_an_impassable_zone_has_no_current_and_is_in_both_lists() -> None:
    world, plan = _world_with_ports()
    shut = _water(world).waters.sea()[-1]
    water = _water(world, shut=(shut,), docks=(shut - 1,))
    texts = _written(plan, water)
    assert f"topography = {Topography.OCEAN_WASTELAND}" in texts[1]
    assert verify_seas(texts, plan, world, water.coast, water)["impassable_checked"] == 1
    ports, templates, _ = texts
    open_list = _map_text(plan, replace(water, zones=frozenset()))
    with pytest.raises(SeaError, match="impassable"):
        _ = verify_seas((ports, templates, open_list), plan, world, water.coast, water)


def test_a_zone_of_ours_missing_from_the_impassable_list_stops_the_export() -> None:
    world, plan = _world_with_ports()
    shut = _water(world).waters.sea()[-1]
    water = _water(world, shut=(shut,), docks=(shut - 1,))
    ports, templates, _ = _written(plan, water)
    lists = f"sea_zones = {{ {' '.join(c.key for c in plan.cells if c.kind is CellClass.SEA)} }}\n"
    with pytest.raises(SeaError, match="impassable"):
        _ = verify_seas((ports, templates, lists), plan, world, water.coast, water)


def test_deep_water_that_is_neither_a_lane_nor_shut_stops_the_export() -> None:
    world, plan = _world_with_ports()
    water = _water(world)
    dropped = replace(water, lanes=frozenset(sorted(water.lanes)[1:]))
    with pytest.raises(SeaError, match="no lane"):
        _ = verify_seas(_written(plan, water), plan, world, water.coast, dropped)


def test_a_sea_that_ships_cannot_reach_stops_the_export() -> None:
    world, plan = _world_with_ports()
    shut = _water(world).waters.sea()[-2]
    water = _water(world, shut=(shut,), docks=(shut + 1,))
    with pytest.raises(SeaError, match="cannot be reached"):
        _ = verify_seas(_written(plan, water), plan, world, water.coast, water)


@final
class _Canvas:
    """A canvas that is the map itself: nothing rolled, the crop at its left edge."""

    def __init__(self, removed: np.ndarray) -> None:
        self.removed = removed
        self.col0 = 0
        self.shape = (4, 4)

    def rolled(self, labels: np.ndarray, rows: slice) -> np.ndarray:
        return labels[rows]


def test_a_course_is_where_a_replaced_deep_zone_ran_over_a_generated_cell() -> None:
    world = block_world(["11", "22"], block=2)
    keys = ("gulf_stream", "kept_stream", "rock")
    labels = np.array(
        [[0, 0, 0, 1], [0, 0, 0, 1], [2, 2, 1, 1], [2, 2, 1, 1]],
        dtype=np.int32,
    )
    game_map = SimpleNamespace(keys=keys, labels=labels)
    canvas = _Canvas(np.array([True, False, False]))
    vanilla = {
        "gulf_stream": VanillaWater("deep_ocean", (9000, 1000)),
        "kept_stream": VanillaWater("deep_ocean", (-9000, 0)),
        "rock": VanillaWater("ocean", None),
    }
    courses = courses_over(
        cast("Eu5Map", cast("object", game_map)),
        cast("Canvas", cast("object", canvas)),
        world,
        vanilla,
    )
    assert courses[0].permille == 750
    assert courses[0].vector == (9000, 1000)
    assert 1 not in courses


STRAIT = ["AAA1BBB", "AAA1BBB", "AAA1BBB", "2222222"]


def _plan_of(world: NewWorld) -> Plan:
    return Plan(
        cells=[
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
            for index, kind in enumerate(world.classes)
        ]
    )


def _strait(layout: list[str] = STRAIT, block: int = 4) -> tuple[NewWorld, Plan, list[Crossing]]:
    world = block_world(layout, block=block)
    waters = analyse(world)
    return world, _plan_of(world), crossings(world, waters.landmass.tolist())


def _row(plan: Plan, item: Crossing, height: int, *, swap: bool = False) -> str:
    (r1, c1), (r2, c2) = item.start, item.stop
    first, second = plan.cells[item.first].key, plan.cells[item.second].key
    if swap:
        c1, c2 = c2, c1
    through = plan.cells[item.through].key
    return f"{first};{second};sea;{through};{c1};{height - 1 - r1};{c2};{height - 1 - r2};xxx"


def test_two_lands_a_narrow_sea_cell_divides_are_a_crossing_through_it() -> None:
    world, plan, found = _strait()
    left, right, between = (cell(STRAIT, 0, column) for column in (0, 4, 3))
    assert [(c.first, c.second, c.through) for c in found] == [(left, right, between)]
    assert found[0].start == (0, 11)
    assert found[0].stop == (0, 16)
    assert world.classes[between] is CellClass.SEA
    assert plan.cells[between].key.startswith("rnw_sea")


def test_lands_of_one_landmass_or_a_sea_wider_than_the_games_crossings_make_none() -> None:
    joined = ["AAA1BBB", "AAA1BBB", "AAACBBB", "2222222"]
    assert _strait(joined)[2] == []
    assert _strait(STRAIT, block=10)[2] == []


def test_the_rows_that_say_what_the_world_has_pass_and_any_other_stops_the_export() -> None:
    world, plan, found = _strait()
    height = world.labels.shape[0]
    canvas = cast("Canvas", cast("object", SimpleNamespace(col0=0, roll=0, shape=(height, 28))))
    text = "From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n"
    rows = _row(plan, found[0], height)
    assert verify_crossings(text + rows + "\n", plan, world, canvas, found) == {
        "crossings_checked": 1
    }
    with pytest.raises(SeaError, match="not the world's"):
        _ = verify_crossings(text, plan, world, canvas, found)
    with pytest.raises(SeaError, match="twice"):
        _ = verify_crossings(text + rows + "\n" + rows + "\n", plan, world, canvas, found)
    with pytest.raises(SeaError, match="point off"):
        _ = verify_crossings(
            text + _row(plan, found[0], height, swap=True) + "\n", plan, world, canvas, found
        )
    stranger = rows.replace(";sea;", ";land;")
    with pytest.raises(SeaError, match="not a sea crossing"):
        _ = verify_crossings(text + stranger + "\n", plan, world, canvas, found)
    other = rows.replace(plan.cells[found[0].through].key, plan.cells[cell(STRAIT, 3, 0)].key)
    with pytest.raises(SeaError, match="not the world's"):
        _ = verify_crossings(text + other + "\n", plan, world, canvas, found)


def test_a_crossing_through_a_sea_that_does_not_touch_both_lands_stops_the_export() -> None:
    layout = [*STRAIT, "3333333"]
    world, plan, found = _strait(layout)
    height = world.labels.shape[0]
    canvas = cast("Canvas", cast("object", SimpleNamespace(col0=0, roll=0, shape=(height, 28))))
    text = "From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n"
    far = plan.cells[cell(layout, 4, 0)].key
    row = _row(plan, found[0], height).replace(plan.cells[found[0].through].key, far)
    with pytest.raises(SeaError, match="does not touch both"):
        _ = verify_crossings(text + row + "\n", plan, world, canvas, found)


def _locator_keys(instances: dict[str, list[str]], name: str) -> set[str]:
    return {
        line.split("=")[1] for line in "".join(instances[name]).split() if line.startswith("id=")
    }


def _closed_world() -> tuple[NewWorld, Plan, Water, Canvas]:
    world, plan = _world_with_ports()
    water = _water(world, shut=(_water(world).waters.sea()[-1],), docks=())
    canvas = cast("Canvas", cast("object", SimpleNamespace(col0=0, roll=0, shape=(10, 14))))
    return world, plan, water, canvas


def test_the_closed_ocean_has_no_stack_of_units_and_no_battle_as_in_the_game() -> None:
    world, plan, water, canvas = _closed_world()
    shut = plan.cells[next(iter(water.zones))].key
    instances = _locator_instances(plan, world, canvas, {}, water.zones)
    for name in NO_UNITS:
        keys = _locator_keys(instances, name)
        assert shut not in keys
        assert len(keys) == len(plan.cells) - 1
    # The game's vfx locators cover every location, the closed ocean too.
    assert shut in _locator_keys(instances, "generated_locators_vfx.txt")


def test_written_locators_that_hold_what_was_planned_pass_and_any_other_stops_the_export() -> None:
    world, plan, water, canvas = _closed_world()
    instances = _locator_instances(plan, world, canvas, {}, water.zones)
    files = {name: "".join(instances[name]) for name in NO_UNITS}
    assert verify_locators(files, plan, water) == {"locators_checked": len(plan.cells) - 1}
    shut = plan.cells[next(iter(water.zones))].key
    extra = {name: text + f"id={shut}\n" for name, text in files.items()}
    with pytest.raises(SeaError, match="1 locators too many and 0 too few"):
        _ = verify_locators(extra, plan, water)
    short = {name: text.replace(f"id={plan.cells[0].key}\n", "") for name, text in files.items()}
    with pytest.raises(SeaError, match="0 locators too many and 1 too few"):
        _ = verify_locators(short, plan, water)
