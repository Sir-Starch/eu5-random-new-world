"""The lanes of the open ocean, and the impassable water between them.

Game-independent. The game's open ocean is mostly closed to ships: 46 great zones of
``ocean_wasteland`` (impassable, 56 per cent of all the sea) lie between narrow lanes of deep
ocean, one or two cells wide, that follow the ocean currents and join the coastal water of
the lands, so a ship has the route a current gives it and nothing else [V-LOCAL 1.4.3, V-GAME
owner's maps of 1.4.4, C241]. A generated ocean that is deep everywhere would be sailable
everywhere and carry a current in every zone. This module chooses which deep cells are lanes
and which water is shut.

* **Courses.** Deep cells mostly covered by a replaced game current become lanes. The world
  generator builds sea cells against the current bands so their edges follow the bands rather
  than a random overlap. Where land cuts a course, it can end at the coast.
* **Anchors.** A deep cell that touches a lane of the game's own continues it.
* **Linked.** Every stretch of passable water (coastal and ocean cells round the lands, inland
  seas, narrows, lanes) must reach the game's own water, so ships can come from the Old World to
  every coast. A stretch that does not is joined to the water that does by the cheapest
  string of deep cells (one cell wide, the nearer to land the cheaper: lanes lie close to
  coasts), which becomes a lane.
* **Local routes.** Nearby coasts and retained-water contacts get bounded detours
  through ``sea_routes``, independently of global reachability.
* **Crossings.** A water-distance diagram of shore stretches identifies useful crossings
  between distant coasts and retained water. A crossing opens only when it improves the
  existing network's detour.
* **Ends.** Open-ocean ends continue to another lane, coastal water or a retained-water
  contact. Reachability from one end alone is not a complete ocean route.
* **Zones.** Each connected stretch of closed deep water becomes one location.
  A patch without an interior in the cell graph is navigable, not an isolated ocean.
  A size target must not manufacture neighbouring oceans with unrelated names.

Nothing here draws a random number; ties go to the lower cell.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.sea_routes import LaneError, complete_routes, cross_oceans, shorten_routes
from rnw.seas import Topography

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# Vector of a current, in hundredths of the game's unit: east, then north.
Vector = tuple[int, int]
# The share of a cell, in permille, that a course must cover for the cell to be a lane.
COURSE_PERMILLE: Final[int] = 500
# A string of deep cells that joins water to water costs one a cell, and more the farther it
# runs from land than this many cells (a lane keeps to the coasts).
NEAR_HOPS: Final[int] = 3
FAR_COST: Final[int] = 3
__all__ = ["COURSE_PERMILLE", "Course", "LaneError", "Lanes", "plan_lanes"]


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
    local_pairs: int = 0
    shortcuts: int = 0
    completed: int = 0


def plan_lanes(  # noqa: PLR0913 - currents, retained contacts, and designed geometry.
    world: NewWorld,
    waters: Waters,
    courses: Mapping[int, Course],
    anchors: Collection[int],
    docks: Collection[int],
    *,
    preferred: Collection[int] = (),
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
    sources = set(anchors) | {
        cell for cell, course in courses.items() if course.permille >= COURSE_PERMILLE
    }
    # A designed crossing is only a current when its navigable component has a
    # real source. This decision precedes both final zoning and current vectors.
    proposed = deep.intersection(preferred)
    provisional = set(links) - (deep - lanes - proposed)
    for stretch in _stretches(links, provisional):
        if sources.intersection(stretch):
            lanes.update(proposed.intersection(stretch))
    if not any(cell in docks for cell in links):
        message = "No cell of the generated water touches the game's water"
        raise LaneError(message)
    before = len(lanes)
    sealed = _join(links, waters, deep, lanes, docks)
    linked = len(lanes) - before
    local_pairs, shortcuts = shorten_routes(world, waters, deep, lanes, docks)
    completed = complete_routes(world, waters, deep, lanes, docks)
    shortcuts += cross_oceans(world, waters, deep, lanes, docks=docks, sources=sources)
    # A closed patch needs an interior: a cell with closed water on at least two
    # sides. Isolated cells and single-edge slivers are part of the surrounding
    # navigable water, not separate ocean basins. This is done before folding.
    navigable = set(links) - (deep - lanes)
    reached = {
        cell
        for stretch in _stretches(links, navigable)
        if sources.intersection(stretch)
        for cell in stretch
    }
    for zone in _stretches(links, deep - lanes):
        inside = set(zone)
        has_interior = any(sum(other in inside for other in links[cell]) >= 2 for cell in zone)  # noqa: PLR2004 - two sides form an interior.
        if not has_interior and any(other in reached for cell in zone for other in links[cell]):
            lanes.update(zone)
            reached.update(zone)
    shut = sorted(deep - lanes)
    return Lanes(
        frozenset(lanes),
        tuple(tuple(s) for s in _stretches(links, shut)),
        linked,
        sealed,
        local_pairs,
        shortcuts,
        completed,
    )


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
