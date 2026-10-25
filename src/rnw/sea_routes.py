"""Bound local coastal detours before deciding which deep water stays closed.

An inherited current can connect the world while leaving nearby coasts a voyage
apart. Keep its lanes and add only the deep cells needed for local connections.
Distances are integer centroid lengths through water, never through land. This
is an offline geographic criterion, not the engine's travel-time calculation.
"""

# NumPy stubs type array indexing and tolist() as Any.
# pyright: reportAny=false
from __future__ import annotations

import heapq
import math
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# A neighbouring coast is at most six typical sea-cell widths away by water.
# Its available route may be at most twice the unrestricted water-only route.
LOCAL_SCALES: Final[int] = 6
MAX_DETOUR: Final[int] = 2
Graph = dict[int, list[tuple[int, int]]]


def _distances(
    links: Mapping[int, Sequence[tuple[int, int]]],
    start: int,
    allowed: Collection[int],
    limit: int,
    *,
    target: int | None = None,
) -> tuple[dict[int, int], dict[int, int]]:
    if start not in allowed:
        return {}, {}
    best = {start: 0}
    parent: dict[int, int] = {}
    queue = [(0, start)]
    while queue:
        distance, cell = heapq.heappop(queue)
        if distance != best[cell]:
            continue
        if cell == target:
            break
        for other, length in links[cell]:
            step = distance + length
            if other in allowed and step <= limit and step < best.get(other, step + 1):
                best[other] = step
                parent[other] = cell
                heapq.heappush(queue, (step, other))
    return best, parent


def _links(world: NewWorld, sea: Collection[int]) -> Graph:
    links: Graph = {cell: [] for cell in sorted(sea)}
    for first, second in world.edges:
        if first in links and second in links:
            row, column = (int(v) for v in world.centroids[first] - world.centroids[second])
            length = max(1, math.isqrt(row * row + column * column))
            links[first].append((second, length))
            links[second].append((first, length))
    return {cell: sorted(others) for cell, others in links.items()}


def shorten_routes(
    world: NewWorld,
    waters: Waters,
    deep: set[int],
    lanes: set[int],
    docks: Collection[int],
) -> tuple[int, int]:
    """Add lanes for nearby coasts and Old World contacts; return pair/cell counts.

    Pairs are processed shortest first, then by cell number. Opening water can
    only improve earlier routes. Only a shortest path's closed deep cells open;
    enclosed seas, land, existing lanes and water outside this world stay intact.
    """
    sea = set(waters.sea())
    links = _links(world, sea)
    ends = {cell for cell in sea if waters.hop[cell] == 0 or cell in docks}
    limit = LOCAL_SCALES * waters.scale
    paths: dict[int, dict[int, int]] = {}
    pairs: list[tuple[int, int, int]] = []
    for start in sorted(ends):
        distances, parents = _distances(links, start, sea, limit)
        paths[start] = parents
        pairs.extend(
            (distance, start, end)
            for end, distance in distances.items()
            if end in ends and end > start
        )
    before = len(lanes)
    lanes.update(deep.intersection(docks))
    allowed = sea - (deep - lanes)
    for distance, start, end in sorted(pairs):
        reached, _ = _distances(links, start, allowed, distance * MAX_DETOUR, target=end)
        if end in reached:
            continue
        cell = end
        while cell != start:
            if cell in deep:
                lanes.add(cell)
                allowed.add(cell)
            cell = paths[start][cell]
        if start in deep:
            lanes.add(start)
            allowed.add(start)
    return len(pairs), len(lanes) - before
