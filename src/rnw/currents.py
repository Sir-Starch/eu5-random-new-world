"""Ocean currents for the deep water of a generated world: the game's gyres, carried inland.

Game-independent. Every deep-ocean zone of the game's own map holds a current, ``movement_assistance
= { east north }``, a vector of about 92 units that the Sea Currents map mode draws as an arrow
and ships feel as a speed bonus or a headwind: 749 of the 750 deep-ocean zones of 1.4.3 have one,
no other sea zone has [V-LOCAL 1.4.3, C234]. The vectors follow the real gyres: the north
equatorial currents run west at about 90, the equatorial counter-currents east, the Gulf Stream
east-north-east (the second number grows northwards) [V-LOCAL, C236]. The generated New World
replaces a great part of the Atlantic and the Pacific, so without currents of its own there
would be a hole in every gyre.

``flow`` continues the game's currents into the generated deep water. Each generated deep zone
takes a blend of the four nearest sources through navigable water, weighted by inverse square
distance, bent away from land and smoothed. On unambiguous two-sided stretches its direction
follows the lane. A lane without a reachable source or a cancelled direction is an error.
Integer geometry and IEEE arithmetic are taken in a fixed order.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import math
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.seas import Topography

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# A current: hundredths of the game's unit, east then north.
Vector = tuple[int, int]
HUNDREDTHS: Final[int] = 100
# Each deep zone is fed by this many of the nearest sources of current.
SOURCES: Final[int] = 4
# Land turns a current aside within this many scales of it; the smoothing rounds.
BEND_SCALES: Final[int] = 6
SMOOTHING_ROUNDS: Final[int] = 2
# A current shorter than this (after bending and smoothing) has no direction left.
MIN_NORM: Final[float] = 1e-9
CORRIDOR_NEIGHBOURS: Final[int] = 2
MIN_ALONG_SHARE: Final[float] = 0.25


class CurrentError(ValueError):
    """The generated deep water has no current of the game's to continue."""


def _length(world: NewWorld, first: int, second: int) -> int:
    row = int(world.centroids[first, 0] - world.centroids[second, 0])
    column = int(world.centroids[first, 1] - world.centroids[second, 1])
    return max(1, math.isqrt(row * row + column * column))


def _sea_links(world: NewWorld, sea: set[int]) -> dict[int, list[tuple[int, int]]]:
    links: dict[int, list[tuple[int, int]]] = {cell: [] for cell in sorted(sea)}
    for first, second in world.edges:
        if first in sea and second in sea:
            length = _length(world, first, second)
            links[first].append((second, length))
            links[second].append((first, length))
    return {cell: sorted(others) for cell, others in links.items()}


def _nearest_sources(
    links: Mapping[int, Sequence[tuple[int, int]]], sources: Sequence[int]
) -> dict[int, list[tuple[int, int]]]:
    """For every cell, the ``SOURCES`` nearest sources through the water: (source, distance)."""
    found: dict[int, list[tuple[int, int]]] = {cell: [] for cell in links}
    queue: list[tuple[int, int, int]] = [(0, source, source) for source in sources]
    heapq.heapify(queue)
    while queue:
        distance, cell, source = heapq.heappop(queue)
        reached = found[cell]
        if len(reached) >= SOURCES or any(other == source for other, _ in reached):
            continue
        reached.append((source, distance))
        for other, length in links[cell]:
            heapq.heappush(queue, (distance + length, other, source))
    return found


def flow(
    world: NewWorld,
    waters: Waters,
    samples: Mapping[int, Sequence[Vector]],
    lanes: Sequence[int],
) -> dict[int, Vector]:
    """The current of every lane cell, which are the deep-ocean cells that carry one.

    ``samples`` maps a generated sea cell to the currents the game gives it: those of its zones
    that touch it, and of the lanes that ran over it. Raises ``CurrentError`` when there are
    none to continue.
    """
    sea = {
        cell for cell in waters.sea() if waters.topography[cell] is not Topography.OCEAN_WASTELAND
    }
    deep = sorted(set(lanes) & sea)
    sources = {
        cell: (
            sum(x for x, _ in vectors) / len(vectors),
            sum(y for _, y in vectors) / len(vectors),
        )
        for cell, vectors in sorted(samples.items())
        if vectors and cell in sea
    }
    if deep and not sources:
        message = "No current of the game touches the generated deep water, so none continues"
        raise CurrentError(message)
    if not deep:
        return {}
    strength = math.fsum(math.sqrt(x * x + y * y) for x, y in sources.values()) / len(sources)
    links = _sea_links(world, sea)
    nearest = _nearest_sources(links, sorted(sources))
    blended: dict[int, tuple[float, float]] = {}
    for cell in deep:
        reached = nearest[cell]
        if not reached:
            message = f"No current reaches ocean lane {cell} through navigable water"
            raise CurrentError(message)
        blended[cell] = _blend(reached, sources)
    blended = _bend(world, waters, deep, blended)
    for _ in range(SMOOTHING_ROUNDS):
        blended = _smooth(blended, links)
    blended = _follow_corridors(world, blended, links)
    return {cell: _scaled(blended[cell], strength) for cell in deep}


def _blend(
    reached: Sequence[tuple[int, int]], sources: Mapping[int, tuple[float, float]]
) -> tuple[float, float]:
    """The sources' currents weighted by the inverse square of their distance."""
    total = 0.0
    x = y = 0.0
    for source, distance in reached:
        weight = 1.0 / ((distance + 1) * (distance + 1))
        total += weight
        x += weight * sources[source][0]
        y += weight * sources[source][1]
    return x / total, y / total


def _bend(
    world: NewWorld,
    waters: Waters,
    deep: Sequence[int],
    current: Mapping[int, tuple[float, float]],
) -> dict[int, tuple[float, float]]:
    """Remove the part of a current that flows into land nearby, more the nearer the land is."""
    land_cells = np.array(
        [index for index in range(len(world.classes)) if waters.hop[index] < 0], dtype=np.int64
    )
    if not land_cells.size:
        return dict(current)
    land = world.centroids[land_cells]
    reach = BEND_SCALES * waters.scale
    bent: dict[int, tuple[float, float]] = {}
    for cell in deep:
        x, y = current[cell]
        offsets = land - world.centroids[cell]
        squares = (offsets * offsets).sum(axis=1)
        nearest = int(np.argmin(squares))
        distance_squared = int(squares[nearest])
        if distance_squared < reach * reach:
            distance = math.sqrt(distance_squared)
            # Rows grow southwards: the northward unit is minus the row.
            east, north = float(offsets[nearest, 1]), -float(offsets[nearest, 0])
            norm = math.sqrt(east * east + north * north)
            if norm > 0:
                east, north = east / norm, north / norm
                into = x * east + y * north
                if into > 0:
                    share = into * (reach - distance) / reach
                    x, y = x - share * east, y - share * north
        bent[cell] = (x, y)
    return bent


def _smooth(
    current: Mapping[int, tuple[float, float]], links: Mapping[int, Sequence[tuple[int, int]]]
) -> dict[int, tuple[float, float]]:
    """Each current averaged with those of its deep neighbours (itself counted twice)."""
    smoothed: dict[int, tuple[float, float]] = {}
    for cell, (x, y) in current.items():
        count = 2
        total_x, total_y = 2 * x, 2 * y
        for other, _ in links[cell]:
            if other in current:
                total_x += current[other][0]
                total_y += current[other][1]
                count += 1
        smoothed[cell] = (total_x / count, total_y / count)
    return smoothed


def _follow_corridors(
    world: NewWorld,
    current: Mapping[int, tuple[float, float]],
    links: Mapping[int, Sequence[tuple[int, int]]],
) -> dict[int, tuple[float, float]]:
    """Align unbranched corridors with their actual geometry, retaining the flow's sense.

    Only two-sided, approximately straight stretches have an unambiguous axis. Junctions,
    ends and sharp bends retain the interpolated flow: choosing an arm there by cell number
    would invent a current direction. A perpendicular current is equally ambiguous.
    """
    result = dict(current)
    for cell, (x, y) in current.items():
        neighbours = [other for other, _ in links[cell] if other in current]
        if len(neighbours) != CORRIDOR_NEIGHBOURS:
            continue
        first, second = neighbours
        r1, c1 = (int(v) for v in world.centroids[first] - world.centroids[cell])
        r2, c2 = (int(v) for v in world.centroids[second] - world.centroids[cell])
        # Both arms must point into opposite half-planes and form at least a 90-degree angle.
        if r1 * r2 + c1 * c2 >= 0:
            continue
        east = float(c2 - c1)
        north = float(r1 - r2)
        length = math.hypot(east, north)
        norm = math.hypot(x, y)
        if length < MIN_NORM or norm < MIN_NORM:
            continue
        east, north = east / length, north / length
        along = x * east + y * north
        # A near-perpendicular inherited current does not decide which way this corridor flows.
        if abs(along) < norm * MIN_ALONG_SHARE:
            continue
        sign = 1 if along > 0 else -1
        result[cell] = (sign * norm * east, sign * norm * north)
    return result


def _scaled(vector: tuple[float, float], strength: float) -> Vector:
    """The direction of ``vector`` at the game's strength, in hundredths."""
    x, y = vector
    norm = math.sqrt(x * x + y * y)
    if norm < MIN_NORM:
        message = "Contradictory current sources have no direction"
        raise CurrentError(message)
    factor = strength / norm
    return round(x * factor), round(y * factor)
