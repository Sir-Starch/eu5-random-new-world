"""The lanes of the open ocean, and the impassable water between them.

Game-independent. The game's open ocean is mostly closed to ships: 46 great zones of
``ocean_wasteland`` (impassable, 56 per cent of all the sea) lie between narrow lanes of deep
ocean, one or two cells wide, that follow the ocean currents and join the coastal water of
the lands, so a ship has the route a current gives it and nothing else [V-LOCAL 1.4.3, V-GAME
owner's maps of 1.4.4, C241]. A generated ocean that is deep everywhere would be sailable
everywhere and carry a current in every zone. This module chooses which deep cells are lanes
and which water is shut.

* **Courses.** The canvas replaced a great part of the game's own lanes (390 of its 750 deep
  zones), and each of them ran in some direction: the course of the current. A generated deep
  cell on which a course ran by at least ``COURSE_PERMILLE`` of its area is a lane, carrying
  that current (``currents``). Where the generated land cuts a course, the lane ends at the
  coast, as the current would.
* **Anchors.** A deep cell that touches a lane of the game's own continues it.
* **Linked.** Every stretch of passable water (coastal and ocean cells round the lands, inland
  seas, narrows, lanes) must reach the game's own water, so ships can come from the Old World to
  every coast. A stretch that does not is joined to the water that does by the cheapest
  string of deep cells (one cell wide, the nearer to land the cheaper: lanes lie close to
  coasts), which becomes a lane.
* **Zones.** The deep cells that are no lane are impassable. Each connected stretch of them is
  cut into zones of about ``ZONE_CELLS`` cells (the game's median zone is 32 cells, its mean 78),
  each of which becomes one location when the export folds its cells together.

Nothing here draws a random number; ties go to the lower cell.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.hierarchy import contact_graph, pieces, split
from rnw.seas import Topography

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# Vector of a current, in hundredths of the game's unit: east, then north.
Vector = tuple[int, int]
# The share of a cell, in permille, that a course must cover for the cell to be a lane.
COURSE_PERMILLE: Final[int] = 500
# About this many cells to a zone of impassable water.
ZONE_CELLS: Final[int] = 48
# A string of deep cells that joins water to water costs one a cell, and more the farther it
# runs from land than this many cells (a lane keeps to the coasts).
NEAR_HOPS: Final[int] = 3
FAR_COST: Final[int] = 3


class LaneError(ValueError):
    """The generated water cannot be given lanes the game's own water can be reached by."""


@dataclass(frozen=True, slots=True)
class Course:
    """Where a game current ran over a generated cell: its share of the cell, its vector."""

    permille: int
    vector: Vector


@dataclass(frozen=True, slots=True)
class Lanes:
    """Which deep cells are lanes, and the zones that the rest of the deep water is cut into."""

    lanes: frozenset[int]
    zones: tuple[tuple[int, ...], ...]
    linked: int
    sealed: int


def plan_lanes(
    world: NewWorld,
    waters: Waters,
    courses: Mapping[int, Course],
    anchors: Collection[int],
    docks: Collection[int],
) -> Lanes:
    """Choose the lanes of ``world`` and cut the deep water between them into zones.

    ``courses`` are the generated cells over which the game's currents ran, ``anchors`` the cells
    that touch a lane of the game's, ``docks`` the cells that touch any of the game's passable
    water. Raises ``LaneError`` when no cell of the generated water touches the game's water.
    """
    links = _links(world, waters)
    deep = {
        cell
        for cell in range(len(world.classes))
        if waters.topography[cell] is Topography.DEEP_OCEAN
    }
    lanes = {
        cell
        for cell in deep
        if cell in anchors or (cell in courses and courses[cell].permille >= COURSE_PERMILLE)
    }
    if not any(cell in docks for cell in links):
        message = "No cell of the generated water touches the game's water"
        raise LaneError(message)
    before = len(lanes)
    sealed = _join(links, waters, deep, lanes, docks)
    shut = sorted(deep - lanes)
    return Lanes(frozenset(lanes), _zones(world, shut), len(lanes) - before, sealed)


def _links(world: NewWorld, waters: Waters) -> dict[int, list[int]]:
    """The sea cells and the sea cells each touches, sorted."""
    links: dict[int, list[int]] = {cell: [] for cell in waters.sea()}
    for first, second in world.edges:
        if first in links and second in links:
            links[first].append(second)
            links[second].append(first)
    return {cell: sorted(others) for cell, others in links.items()}


def _stretches(links: Mapping[int, Sequence[int]], cells: Collection[int]) -> list[list[int]]:
    """Connected stretches of ``cells``, each sorted, in order of their lowest cell."""
    inside = set(cells)
    seen: set[int] = set()
    found: list[list[int]] = []
    for start in sorted(inside):
        if start in seen:
            continue
        seen.add(start)
        stretch, stack = [start], [start]
        while stack:
            for other in links[stack.pop()]:
                if other in inside and other not in seen:
                    seen.add(other)
                    stretch.append(other)
                    stack.append(other)
        found.append(sorted(stretch))
    return found


def _join(
    links: Mapping[int, Sequence[int]],
    waters: Waters,
    deep: set[int],
    lanes: set[int],
    docks: Collection[int],
) -> int:
    """Add cells to ``lanes`` until every stretch of passable water that can reach the game's does.

    Returns how many stretches could not: closed seas, with no deep water to link them by.
    """
    while True:
        shut = deep - lanes
        stretches = _stretches(links, [cell for cell in links if cell not in shut])
        reached = [any(cell in docks for cell in stretch) for stretch in stretches]
        waiting = {
            cell: number
            for number, stretch in enumerate(stretches)
            if not reached[number]
            for cell in stretch
        }
        if not waiting:
            return 0
        sources = [
            cell for number, stretch in enumerate(stretches) if reached[number] for cell in stretch
        ]
        starts = sorted({other for cell in sources for other in links[cell] if other in shut})
        starts = sorted({*starts, *(cell for cell in shut if cell in docks)})
        path = _route(links, waters, shut, starts, waiting)
        if path is None:
            return len(set(waiting.values()))
        lanes.update(path)


def _route(
    links: Mapping[int, Sequence[int]],
    waters: Waters,
    shut: Collection[int],
    starts: Sequence[int],
    waiting: Mapping[int, int],
) -> list[int] | None:
    """The cheapest string of shut cells from the ``starts`` to a stretch in ``waiting``.

    A start is a shut cell beside passable water that reaches the game's, or one that touches the
    game's own water itself.
    """
    shut_cells = set(shut)
    best: dict[int, int] = {}
    parent: dict[int, int] = {}
    heap: list[tuple[int, int]] = []
    for cell in starts:
        best[cell] = _cost(waters, cell)
        parent[cell] = -1
        heapq.heappush(heap, (best[cell], cell))
    while heap:
        cost, cell = heapq.heappop(heap)
        if cost > best[cell]:
            continue
        if any(other in waiting for other in links[cell]):
            path = [cell]
            while parent[path[-1]] >= 0:
                path.append(parent[path[-1]])
            return sorted(path)
        for other in links[cell]:
            if other in shut_cells:
                step = cost + _cost(waters, other)
                if step < best.get(other, step + 1):
                    best[other] = step
                    parent[other] = cell
                    heapq.heappush(heap, (step, other))
    return None


def _cost(waters: Waters, cell: int) -> int:
    return 1 + FAR_COST * max(0, int(waters.hop[cell]) - NEAR_HOPS)


def _zones(world: NewWorld, shut: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    """The shut cells cut into connected zones of about ``ZONE_CELLS`` cells."""
    keep = [False] * len(world.classes)
    for cell in shut:
        keep[cell] = True
    graph = contact_graph(world.centroids, world.edges, keep)
    zones: list[tuple[int, ...]] = []
    for stretch in pieces(graph, shut):
        count = max(1, round(len(stretch) / ZONE_CELLS))
        parts = split(graph, stretch, count) if count > 1 else [stretch]
        zones.extend(tuple(sorted(part)) for part in parts)
    return tuple(sorted(zones))
