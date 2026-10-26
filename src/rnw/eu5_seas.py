"""The water of a generated world in the game's terms: its ports, its coast against vanilla land,
and the currents it continues.

The game's own map meets the generated world along the canvas edge and round the islets that stay
inside it (Bermuda, Saint Helena). Three things follow from that [V-GAME 1.4.4, C232]:

* a vanilla land location whose port row names a sea zone that the canvas replaced loses the row
  and the engine says ``coastal but has no port setup``; it is given a row to a generated sea
  cell it touches (its own coordinates kept) and takes part in the choice of ports like land of
  the generated world (``rnw.ports``);
* the generated sea cells that touch vanilla land with a port of its own can only be served by
  generated land, which ``settle_seas`` sees to;
* the game's lanes of deep water (its currents) that touch the generated water are continued
  into it, and the courses of the lanes that the canvas replaced are where the generated lanes
  run (``rnw.lanes``, ``rnw.currents``); the rest of the open ocean is closed to ships, as it
  is in the game (``ocean_wasteland``).

Reading and writing here are the game's: ``ports.csv`` rows and ``movement_assistance`` of the
location templates. Everything that is geography is in ``rnw.ports``, ``rnw.seas`` and
``rnw.currents``.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.currents import HUNDREDTHS, Vector, flow
from rnw.eu5_map import class_lists
from rnw.eu5_newworld import outside_contacts
from rnw.eu5_oceans import emitted_cells
from rnw.lanes import COURSE_PERMILLE, Course, plan_lanes
from rnw.model import CellClass
from rnw.ports import ForeignCoast, relabel, settle_seas
from rnw.seas import Topography, Waters, analyse
from rnw.straits import CROSSING_PX, narrow_gaps

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan
    from rnw.newworld import NewWorld

CURRENT: Final[re.Pattern[str]] = re.compile(
    r"movement_assistance\s*=\s*\{\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\}"
)
TOPOGRAPHY: Final[re.Pattern[str]] = re.compile(r"topography\s*=\s*([A-Za-z_]+)")
# The game gives the closed ocean no stack of units and no battle: its 47 zones of
# ``ocean_wasteland`` and its wastelands have no locator of these two kinds, every other location
# has [V-LOCAL C250].
NO_UNITS: Final[tuple[str, ...]] = (
    "generated_map_object_locators_unit_stack.txt",
    "generated_map_object_locators_combat.txt",
)
VFX_LOCATORS: Final[str] = "generated_locators_vfx.txt"
LOCATOR_ID: Final[re.Pattern[str]] = re.compile(r"\bid=(\w+)")
PORT_COLUMNS: Final[int] = 4
ADJACENCY_COLUMNS: Final[int] = 8
STRIP_ROWS: Final[int] = 1024
LAND_LIKE: Final[frozenset[CellClass]] = frozenset(
    {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
)
PERMILLE: Final[int] = 1000
# No current of the game is stronger than this (vanilla 1.4.3: 54 to 125).
MAX_STRENGTH: Final[float] = 200.0


@dataclass(frozen=True, slots=True)
class VanillaPort:
    """One row of the game's ``ports.csv``: the sea zone and the coordinates, as written."""

    sea: str
    x: str
    y: str


def read_ports(text: str) -> dict[str, VanillaPort]:
    """The rows of ``ports.csv`` by land location."""
    ports: dict[str, VanillaPort] = {}
    for line in text.splitlines()[1:]:
        fields = [field.strip() for field in line.split(";")]
        if len(fields) >= PORT_COLUMNS and fields[0]:
            ports[fields[0]] = VanillaPort(fields[1], fields[2], fields[3])
    return ports


def foreign_coast(
    game_map: Eu5Map,
    world: NewWorld,
    contacts: Collection[tuple[int, int]],
    ports: Mapping[str, VanillaPort],
    removed: Collection[str],
) -> ForeignCoast:
    """The vanilla land that touches generated sea cells, sorted by what becomes of its port."""
    free: dict[str, set[int]] = {}
    held: set[int] = set()
    for label, cell in sorted(contacts):
        if (
            world.classes[cell] is not CellClass.SEA
            or game_map.classes[label] is not CellClass.LAND
        ):
            continue
        key = game_map.keys[label]
        port = ports.get(key)
        if port is not None and port.sea in removed:
            free.setdefault(key, set()).add(cell)
        else:
            held.add(cell)
    return ForeignCoast({key: frozenset(cells) for key, cells in free.items()}, frozenset(held))


VANILLA_TEMPLATE: Final[re.Pattern[str]] = re.compile(
    r"^(\w+)\s*=\s*\{([^\n]*)\}\s*$", re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class VanillaWater:
    """What a game location template says of a zone of water: its topography, its current."""

    topography: str
    current: Vector | None


def read_waters(templates: str) -> dict[str, VanillaWater]:
    """The topography and the current (hundredths) of every template of ``location_templates``."""
    waters: dict[str, VanillaWater] = {}
    for entry in VANILLA_TEMPLATE.finditer(templates):
        topography = TOPOGRAPHY.search(entry.group(2))
        found = CURRENT.search(entry.group(2))
        if topography is not None:
            waters[entry.group(1)] = VanillaWater(
                topography.group(1),
                None
                if found is None
                else (
                    round(float(found.group(1)) * HUNDREDTHS),
                    round(float(found.group(2)) * HUNDREDTHS),
                ),
            )
    return waters


@dataclass(frozen=True, slots=True)
class Coast:
    """A world whose coastal sea zones can all have ports, and what meets the game's map.

    ``samples`` are the currents of the game's lanes that touch a generated cell, ``courses`` where
    the currents of the lanes that the canvas replaced ran over the generated cells, ``docks``
    the generated cells that touch water of the game's that ships can enter, ``shore`` those that
    touch land of the game's (an islet inside the canvas, the land at its edge).
    """

    world: NewWorld
    foreign: ForeignCoast
    samples: dict[int, list[Vector]]
    courses: dict[int, Course]
    docks: frozenset[int]
    shore: frozenset[int]
    merged: int

    def renumbered(self, world: NewWorld, cell_of: Sequence[int], keep: Collection[int]) -> Coast:
        """This coast in ``world``, whose cells are the old ones folded as ``cell_of`` says.

        ``keep`` are the old cells whose courses and currents stay: those that were not folded.
        """
        return Coast(
            world,
            self.foreign.renumbered(cell_of),
            {cell_of[cell]: vectors for cell, vectors in self.samples.items() if cell in keep},
            {cell_of[cell]: course for cell, course in self.courses.items() if cell in keep},
            frozenset(cell_of[cell] for cell in self.docks if cell in keep),
            frozenset(cell_of[cell] for cell in self.shore if cell in keep),
            self.merged,
        )


def settle_coast(  # noqa: PLR0913 - the coast reads the map, canvas, world, ports and templates.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    *,
    ports: Mapping[str, VanillaPort],
    vanilla: Mapping[str, VanillaWater],
    removed: Collection[str],
) -> Coast:
    """Settle the sea cells of ``world`` against ports; collect the game's lanes beside it."""
    contacts = outside_contacts(game_map, canvas, world, len(game_map.keys))
    settled = settle_seas(world, foreign_coast(game_map, world, contacts, ports, removed))
    samples: dict[int, list[Vector]] = {}
    docks: set[int] = set()
    shore: set[int] = set()
    for label, cell in sorted(contacts):
        if game_map.classes[label] in LAND_LIKE and world.classes[cell] is CellClass.SEA:
            shore.add(settled.cell_of[cell])
        water = vanilla.get(game_map.keys[label])
        if (
            game_map.classes[label] is not CellClass.SEA
            or water is None
            or water.topography == Topography.OCEAN_WASTELAND
        ):
            continue
        docks.add(settled.cell_of[cell])
        if water.topography == Topography.DEEP_OCEAN and water.current is not None:
            samples.setdefault(settled.cell_of[cell], []).append(water.current)
    return Coast(
        settled.world,
        settled.foreign,
        samples,
        courses_over(game_map, canvas, settled.world, vanilla),
        frozenset(docks),
        frozenset(shore),
        settled.merged,
    )


def courses_over(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, vanilla: Mapping[str, VanillaWater]
) -> dict[int, Course]:
    """Where the currents of the game's deep zones that the canvas replaced ran over ``world``.

    For every generated cell, the share of its pixels (permille) that lay in such a zone, and the
    mean of their currents over those pixels.
    """
    count = len(game_map.keys)
    lane = np.zeros(count + 1, dtype=bool)
    east = np.zeros(count + 1, dtype=np.int64)
    north = np.zeros(count + 1, dtype=np.int64)
    for label, key in enumerate(game_map.keys):
        water = vanilla.get(key)
        if (
            canvas.removed[label]
            and water is not None
            and water.topography == Topography.DEEP_OCEAN
            and water.current is not None
        ):
            lane[label] = True
            east[label], north[label] = water.current
    cells = len(world.classes)
    area = np.zeros(cells, dtype=np.int64)
    east_sum = np.zeros(cells, dtype=np.float64)
    north_sum = np.zeros(cells, dtype=np.float64)
    height, crop = world.labels.shape
    columns = (np.arange(crop, dtype=np.int64) + canvas.col0) % canvas.shape[1]
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS))
        old = canvas.rolled(game_map.labels, rows)[:, columns]
        generated = world.labels[rows]
        on = lane[old] & (generated >= 0)
        found, were = generated[on], old[on]
        area += np.bincount(found, minlength=cells)
        east_sum += np.bincount(found, weights=east[were], minlength=cells)
        north_sum += np.bincount(found, weights=north[were], minlength=cells)
    courses: dict[int, Course] = {}
    for cell in np.flatnonzero(area).tolist():
        if world.classes[cell] is CellClass.SEA:
            courses[cell] = Course(
                int(PERMILLE * area[cell] // max(1, int(world.pixels[cell]))),
                (
                    round(float(east_sum[cell]) / int(area[cell])),
                    round(float(north_sum[cell]) / int(area[cell])),
                ),
            )
    return courses


@dataclass(frozen=True, slots=True)
class Water:
    """The water of the final world: its coast, its shapes, its lanes and their currents.

    ``zones`` are the cells of impassable water (each was folded from the cells of its zone),
    ``flows`` the current of each lane cell, ``linked`` how many deep cells were made lanes to
    join water to the game's, ``sealed`` how many stretches of water no lane could join,
    ``crossings`` the pairs of lands that a strait divides narrowly enough to cross.
    ``completed`` counts deep cells opened to finish ocean-lane ends.
    """

    coast: Coast
    waters: Waters
    lanes: frozenset[int]
    zones: frozenset[int]
    flows: dict[int, Vector]
    linked: int
    sealed: int
    crossings: tuple[Crossing, ...] = ()
    local_pairs: int = 0
    shortcuts: int = 0
    completed: int = 0


def shape_water(coast: Coast) -> Water:
    """Choose the lanes, fold the shut deep water into zones, and give the lanes their currents."""
    waters = analyse(coast.world, coast.shore)
    chosen = plan_lanes(coast.world, waters, coast.courses, coast.samples, coast.docks)
    fold = {cell: zone[0] for zone in chosen.zones for cell in zone[1:]}
    if fold:
        world, cell_of = relabel(coast.world, fold)
        final = coast.renumbered(world, cell_of, set(range(len(coast.world.classes))) - set(fold))
        waters = analyse(world, final.shore)
    else:
        world, cell_of, final = coast.world, tuple(range(len(coast.world.classes))), coast
    lanes = frozenset(cell_of[cell] for cell in chosen.lanes)
    zones = frozenset(cell_of[zone[0]] for zone in chosen.zones)
    topography = tuple(
        Topography.OCEAN_WASTELAND if cell in zones else kind
        for cell, kind in enumerate(waters.topography)
    )
    waters = replace(waters, topography=topography)
    sources: dict[int, list[Vector]] = {
        cell: list(vectors) for cell, vectors in final.samples.items()
    }
    for cell, course in final.courses.items():
        if cell in lanes and course.permille >= COURSE_PERMILLE:
            sources.setdefault(cell, []).append(course.vector)
    flows = flow(world, waters, sources, sorted(lanes))
    strait_rows = tuple(crossings(world, waters.landmass.tolist()))
    return Water(
        final,
        waters,
        lanes,
        zones,
        flows,
        chosen.linked,
        chosen.sealed,
        strait_rows,
        chosen.local_pairs,
        chosen.shortcuts,
        chosen.completed,
    )


def _decimal(hundredths: int) -> str:
    whole, part = divmod(abs(hundredths), HUNDREDTHS)
    return f"{'-' if hundredths < 0 else ''}{whole}.{part:02d}"


def current_text(vector: Vector) -> str:
    """A current as the game writes it: two decimals, east then north."""
    return f"movement_assistance = {{ {_decimal(vector[0])} {_decimal(vector[1])} }}"


class SeaError(ValueError):
    """The written ports, topography or currents do not hold what the water needs."""


def verify_seas(
    texts: tuple[str, str, str], plan: Plan, world: NewWorld, coast: Coast, water: Water
) -> dict[str, object]:
    """Read ``ports.csv``, the templates and ``default.map`` (``texts``) as written; check them.

    Every land location has one port row at most, to a sea zone it touches; every land cell and
    every vanilla land of the coast that touches the sea has a row; every sea zone that touches
    a land location is named by a row; every generated sea cell has the topography and, when it
    is a lane, the current that was planned; the impassable zones are in the lists of the sea
    zones and of the impassable locations, and no other generated water is; the water ships can
    enter reaches the game's.
    """
    ports_text, templates_text, map_text = texts
    ports = _verify_ports(ports_text, plan, world, coast)
    return {
        "ports_checked": ports,
        **_verify_templates(templates_text, plan, water),
        **_verify_lists(map_text, plan, water),
        **_verify_reach(world, coast, water),
    }


def _touching(world: NewWorld) -> dict[int, set[int]]:
    touching: dict[int, set[int]] = {cell: set() for cell in range(len(world.classes))}
    for first, second in world.edges:
        touching[first].add(second)
        touching[second].add(first)
    return touching


def _verify_ports(ports_text: str, plan: Plan, world: NewWorld, coast: Coast) -> int:
    index = {cell.key: number for number, cell in enumerate(plan.cells)}
    kinds = [cell.kind for cell in plan.cells]
    lines = [line for line in ports_text.splitlines()[1:] if line.strip()]
    rows = read_ports(ports_text)
    if len(rows) != len(lines):
        message = "ports.csv names a land location twice"
        raise SeaError(message)
    touching = _touching(world)
    served: set[int] = set()
    for key, port in rows.items():
        sea = index.get(port.sea)
        if sea is None:
            continue
        land = index.get(key)
        near = touching[land] if land is not None else coast.foreign.free.get(key, frozenset())
        if land is not None and (
            kinds[land] is not CellClass.LAND or kinds[sea] is not CellClass.SEA
        ):
            message = f"Port {key} to {port.sea} is not from land to sea"
            raise SeaError(message)
        if sea not in near:
            message = f"Port {key} names {port.sea}, which it does not touch"
            raise SeaError(message)
        served.add(sea)
    for key in sorted(coast.foreign.free):
        if key not in rows or rows[key].sea not in index:
            message = f"Vanilla land {key} lost its port to a replaced sea zone and has none"
            raise SeaError(message)
    for number, cell in enumerate(plan.cells):
        near = [kinds[other] for other in touching[number]]
        if cell.kind is CellClass.LAND and CellClass.SEA in near and cell.key not in rows:
            message = f"Coastal land {cell.key} has no port"
            raise SeaError(message)
        if cell.kind is CellClass.SEA and CellClass.LAND in near and number not in served:
            message = f"Coastal sea zone {cell.key} has no port connected to it"
            raise SeaError(message)
    return len(rows)


def _verify_templates(templates_text: str, plan: Plan, water: Water) -> dict[str, object]:
    index = {cell.key: number for number, cell in enumerate(plan.cells)}
    found: Counter[str] = Counter()
    currents = 0
    for entry in VANILLA_TEMPLATE.finditer(templates_text):
        number = index.get(entry.group(1))
        if number is None or plan.cells[number].kind is not CellClass.SEA:
            continue
        body = entry.group(2)
        topography = TOPOGRAPHY.search(body)
        planned = water.waters.topography[number]
        if topography is None or planned is None or topography.group(1) != planned:
            message = f"Sea zone {entry.group(1)} is not written as {planned}"
            raise SeaError(message)
        current = CURRENT.search(body)
        if (current is not None) != (number in water.flows):
            message = f"Sea zone {entry.group(1)} ({planned}) and its current do not agree"
            raise SeaError(message)
        if current is not None:
            strength = math.hypot(float(current.group(1)), float(current.group(2)))
            if not 1.0 <= strength <= MAX_STRENGTH:
                message = f"Sea zone {entry.group(1)} has a current of strength {strength}"
                raise SeaError(message)
            currents += 1
        found[str(planned)] += 1
    # Several internal closed cells may be one connected final ocean location.
    identities = {cell.key: number for number, cell in enumerate(plan.cells)}
    expected = Counter(
        str(water.waters.topography[number])
        for number in identities.values()
        if water.waters.topography[number] is not None
    )
    if found != expected:
        message = f"Sea templates written {dict(found)}, planned {dict(expected)}"
        raise SeaError(message)
    return {"topography": dict(sorted(found.items())), "currents": currents}


def _verify_lists(map_text: str, plan: Plan, water: Water) -> dict[str, object]:
    lists = class_lists(map_text)
    seas = set(lists["sea_zones"])
    shut = set(lists["impassable_mountains"])
    for number, cell in enumerate(plan.cells):
        if cell.kind is not CellClass.SEA:
            continue
        if cell.key not in seas:
            message = f"Sea zone {cell.key} is not in the list of sea zones"
            raise SeaError(message)
        if (cell.key in shut) != (number in water.zones):
            message = f"Sea zone {cell.key} is wrongly in or out of the impassable locations"
            raise SeaError(message)
    for number in water.lanes:
        if water.waters.topography[number] is not Topography.DEEP_OCEAN:
            message = f"Lane {plan.cells[number].key} is not deep ocean"
            raise SeaError(message)
    deep = [
        number
        for number, kind in enumerate(water.waters.topography)
        if kind is Topography.DEEP_OCEAN and number not in water.lanes
    ]
    if deep:
        message = f"{len(deep)} deep ocean cells are no lane and carry no current"
        raise SeaError(message)
    return {"impassable_checked": len(water.zones), "lanes_checked": len(water.lanes)}


def _verify_reach(world: NewWorld, coast: Coast, water: Water) -> dict[str, object]:
    """Ships can sail from the game's water to every coastal sea zone, but a sealed sea's."""
    sea = [number for number, kind in enumerate(world.classes) if kind is CellClass.SEA]
    shut = water.zones
    reached = set(coast.docks) - shut
    touching = _touching(world)
    queue = sorted(reached)
    while queue:
        cell = queue.pop()
        for other in touching[cell]:
            if other not in reached and other not in shut and world.classes[other] is CellClass.SEA:
                reached.add(other)
                queue.append(other)
    cut_off = [cell for cell in sea if cell not in shut and cell not in reached]
    if water.sealed == 0 and cut_off:
        message = f"{len(cut_off)} sea cells cannot be reached by sea from the game's water"
        raise SeaError(message)
    navigable = set(sea) - shut
    terminals = (navigable - water.lanes) | set(coast.docks)
    for cell in sorted(water.lanes - terminals):
        neighbours = touching[cell] & navigable
        if not neighbours & terminals and len(neighbours) <= 1:
            message = f"Ocean lane {cell} ends in closed water"
            raise SeaError(message)
    return {"sea_cells_reached": len(reached), "sea_cells_cut_off": len(cut_off)}


@dataclass(frozen=True, slots=True)
class Crossing:
    """Two land cells of different landmasses that a strait of ``CROSSING_PX`` pixels divides.

    ``start`` and ``stop`` are (row, column) in the world's picture: a pixel of ``first`` and a
    pixel of ``second`` where the strait is narrowest; ``through`` is the sea cell between them.
    """

    first: int
    second: int
    through: int
    start: tuple[int, int]
    stop: tuple[int, int]


def crossings(world: NewWorld, landmass: Sequence[int]) -> list[Crossing]:
    """The crossings of ``world``, by the numbers of their cells.

    The game's own are 184 pairs of locations 1 to 9 pixels apart, each point on its own location,
    with the sea zone between them touching both (C245): here every pair of land cells of different
    landmasses (``landmass`` numbers the land cells) that a run of at most ``CROSSING_PX`` pixels of
    sea cell divides along a row or a column, at the narrowest run.
    """
    land = np.array([kind is CellClass.LAND for kind in world.classes], dtype=bool)
    sea = np.array([kind is CellClass.SEA for kind in world.classes] + [False], dtype=bool)
    water = sea[world.labels]
    found: list[Crossing] = []
    touching = _touching(world)
    gaps = narrow_gaps(world.labels, water, land, CROSSING_PX)
    for gap in sorted(gaps.values(), key=lambda item: (item.first, item.second)):
        if landmass[gap.first] == landmass[gap.second] or not sea[gap.through]:
            continue
        # A short raster gap may cross two different sea zones. The game requires
        # the named through-zone to touch both ends of a single crossing.
        if gap.through not in touching[gap.first] or gap.through not in touching[gap.second]:
            continue
        start, stop = (
            ((gap.line, gap.start), (gap.line, gap.stop))
            if gap.axis == 0
            else ((gap.start, gap.line), (gap.stop, gap.line))
        )
        found.append(Crossing(gap.first, gap.second, gap.through, start, stop))
    return found


def verify_crossings(
    text: str, plan: Plan, world: NewWorld, canvas: Canvas, expected: Sequence[Crossing]
) -> dict[str, object]:
    """Read ``adjacencies.csv`` as written; every generated crossing is as the world has it.

    A row names two land cells of different landmasses and a sea cell, with a point on each of
    the two land cells, at most ``CROSSING_PX`` pixels apart, and the sea cell touches both; the
    rows are exactly the crossings of the world; no pair is twice.
    """
    index = {cell.key: number for number, cell in enumerate(plan.cells)}
    touching = _touching(world)
    height = int(world.labels.shape[0])
    width = int(canvas.shape[1])
    wanted = {(item.first, item.second, item.through) for item in expected}
    seen: set[tuple[int, int, int]] = set()
    for line in text.splitlines()[1:]:
        fields = [field.strip() for field in line.split(";")]
        if len(fields) < ADJACENCY_COLUMNS or fields[0] not in index:
            continue
        first, second, through = (index.get(name, -1) for name in (fields[0], fields[1], fields[3]))
        if fields[2] != "sea" or min(first, second, through) < 0:
            message = (
                f"Crossing {fields[0]} to {fields[1]} is not a sea crossing of generated cells"
            )
            raise SeaError(message)
        if (first, second, through) in seen:
            message = f"Crossing {fields[0]} to {fields[1]} is written twice"
            raise SeaError(message)
        seen.add((first, second, through))
        if through not in touching[first] or through not in touching[second]:
            message = f"Crossing {fields[0]} to {fields[1]} through {fields[3]} does not touch both"
            raise SeaError(message)
        x1, y1, x2, y2 = (int(value) for value in fields[4:8])
        points: list[int] = []
        for x, y in ((x1, y1), (x2, y2)):
            column = (x - canvas.col0 + canvas.roll) % width
            row = height - 1 - y
            inside = 0 <= row < height and 0 <= column < world.labels.shape[1]
            points.append(int(world.labels[row, column]) if inside else -1)
        if points != [first, second]:
            message = f"Crossing {fields[0]} to {fields[1]} has a point off its location"
            raise SeaError(message)
        if abs(x1 - x2) + abs(y1 - y2) > CROSSING_PX + 1:
            message = f"Crossing {fields[0]} to {fields[1]} is wider than {CROSSING_PX} pixels"
            raise SeaError(message)
    if seen != wanted:
        message = (
            f"The generated crossings of adjacencies.csv are not the world's: "
            f"{len(seen)} written, {len(wanted)} expected, {len(seen ^ wanted)} apart"
        )
        raise SeaError(message)
    return {"crossings_checked": len(seen)}


def verify_locators(
    files: Mapping[str, str],
    plan: Plan,
    water: Water,
    *,
    all_locations: frozenset[str] | None = None,
) -> dict[str, object]:
    """Read the locators of units and battles (``files`` by their names) as written.

    Every generated land, sea and lake location has one of each and a closed zone has none, as
    the game's own map has it; the engine logs ``map object locator is incomplete`` otherwise
    (the first closed zones had them, C250).
    """
    expected = {
        cell.key
        for number, cell in enumerate(plan.cells)
        if cell.kind in {CellClass.LAND, CellClass.SEA, CellClass.LAKE}
        and number not in water.zones
    }
    ours = {cell.key for cell in plan.cells}
    for name in NO_UNITS:
        if name not in files:
            continue
        found = {key for key in LOCATOR_ID.findall(files[name]) if key in ours}
        if found != expected:
            message = (
                f"{name} has {len(found - expected)} locators too many and "
                f"{len(expected - found)} too few"
            )
            raise SeaError(message)
    if VFX_LOCATORS in files:
        expected_vfx = (
            set(all_locations)
            if all_locations is not None
            else {cell.key for cell in emitted_cells(plan)}
        )
        found_vfx = set(LOCATOR_ID.findall(files[VFX_LOCATORS]))
        if all_locations is None:
            found_vfx &= expected_vfx
        if found_vfx != expected_vfx:
            message = (
                f"{VFX_LOCATORS} has {len(found_vfx - expected_vfx)} locators too many and "
                f"{len(expected_vfx - found_vfx)} too few"
            )
            raise SeaError(message)
    for name, text in files.items():
        identifiers = LOCATOR_ID.findall(text)
        if len(identifiers) != len(set(identifiers)):
            message = f"{name} repeats a location locator"
            raise SeaError(message)
    return {"locators_checked": len(expected)}
