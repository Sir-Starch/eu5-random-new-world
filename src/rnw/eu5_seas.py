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
* the currents of the game's deep zones that touch the generated water are the ones the
  generated deep water continues (``rnw.currents``).

Reading and writing here are the game's: ``ports.csv`` rows and ``movement_assistance`` of the
location templates. Everything that is geography is in ``rnw.ports``, ``rnw.seas`` and
``rnw.currents``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.currents import HUNDREDTHS, Vector, flow
from rnw.eu5_newworld import outside_contacts
from rnw.model import CellClass
from rnw.ports import ForeignCoast, settle_seas
from rnw.seas import Topography, Waters, analyse

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan
    from rnw.newworld import NewWorld

CURRENT: Final[re.Pattern[str]] = re.compile(
    r"movement_assistance\s*=\s*\{\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\}"
)
TOPOGRAPHY: Final[re.Pattern[str]] = re.compile(r"topography\s*=\s*([A-Za-z_]+)")
PORT_COLUMNS: Final[int] = 4
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


def read_currents(templates: str) -> dict[str, Vector]:
    """The current of every deep-ocean zone of ``location_templates.txt``, in hundredths."""
    currents: dict[str, Vector] = {}
    for entry in VANILLA_TEMPLATE.finditer(templates):
        topography = TOPOGRAPHY.search(entry.group(2))
        found = CURRENT.search(entry.group(2))
        if topography is not None and topography.group(1) == Topography.DEEP_OCEAN and found:
            currents[entry.group(1)] = (
                round(float(found.group(1)) * HUNDREDTHS),
                round(float(found.group(2)) * HUNDREDTHS),
            )
    return currents


@dataclass(frozen=True, slots=True)
class Coast:
    """A world whose coastal sea zones can all have ports, and what meets the game's map."""

    world: NewWorld
    foreign: ForeignCoast
    samples: dict[int, list[Vector]]
    merged: int


def settle_coast(  # noqa: PLR0913 - the coast reads the map, canvas, world, ports and templates.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    *,
    ports: Mapping[str, VanillaPort],
    currents: Mapping[str, Vector],
    removed: Collection[str],
) -> Coast:
    """Settle the sea cells of ``world`` against ports; collect the game's currents beside it."""
    contacts = outside_contacts(game_map, canvas, world, len(game_map.keys))
    settled = settle_seas(world, foreign_coast(game_map, world, contacts, ports, removed))
    samples: dict[int, list[Vector]] = {}
    for label, cell in sorted(contacts):
        vector = currents.get(game_map.keys[label])
        if game_map.classes[label] is CellClass.SEA and vector is not None:
            samples.setdefault(settled.cell_of[cell], []).append(vector)
    return Coast(settled.world, settled.foreign, samples, settled.merged)


@dataclass(frozen=True, slots=True)
class Water:
    """The shape of the water of the settled world and the currents of its deep zones."""

    waters: Waters
    flows: dict[int, Vector]


def shape_water(coast: Coast) -> Water:
    """Read the shapes of the water and continue the game's currents into the deep zones."""
    waters = analyse(coast.world)
    return Water(waters, flow(coast.world, waters, coast.samples))


def _decimal(hundredths: int) -> str:
    whole, part = divmod(abs(hundredths), HUNDREDTHS)
    return f"{'-' if hundredths < 0 else ''}{whole}.{part:02d}"


def current_text(vector: Vector) -> str:
    """A current as the game writes it: two decimals, east then north."""
    return f"movement_assistance = {{ {_decimal(vector[0])} {_decimal(vector[1])} }}"


class SeaError(ValueError):
    """The written ports, topography or currents do not hold what the water needs."""


def verify_seas(
    texts: tuple[str, str], plan: Plan, world: NewWorld, coast: Coast, water: Water
) -> dict[str, object]:
    """Read ``ports.csv`` and the templates (``texts``) as written; check what the engine checks.

    Every land location has one port row at most, to a sea zone it touches; every land cell and
    every vanilla land of the coast that touches the sea has a row; every sea zone that touches
    a land location is named by a row; every generated sea cell has the topography and, when
    deep, the current that was planned.
    """
    ports_text, templates_text = texts
    ports = _verify_ports(ports_text, plan, world, coast)
    return {"ports_checked": ports, **_verify_templates(templates_text, plan, water)}


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
        if (current is not None) != (planned is Topography.DEEP_OCEAN):
            message = f"Sea zone {entry.group(1)} ({planned}) and its current do not agree"
            raise SeaError(message)
        if current is not None:
            strength = math.hypot(float(current.group(1)), float(current.group(2)))
            if not 1.0 <= strength <= MAX_STRENGTH:
                message = f"Sea zone {entry.group(1)} has a current of strength {strength}"
                raise SeaError(message)
            currents += 1
        found[str(planned)] += 1
    expected = Counter(str(kind) for kind in water.waters.topography if kind is not None)
    if found != expected:
        message = f"Sea templates written {dict(found)}, planned {dict(expected)}"
        raise SeaError(message)
    return {"topography": dict(sorted(found.items())), "currents": currents}
