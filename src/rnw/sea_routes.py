"""Bound local coastal detours and complete ocean courses before closing deep water.

An inherited current can connect the world while leaving nearby coasts a voyage
apart, or stop in the middle of an ocean. Keep its lanes and add only the deep cells
needed for local connections and continuations to existing navigable water.
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
MIN_CYCLIC_BLOCK: Final[int] = 3
Graph = dict[int, list[tuple[int, int]]]


class LaneError(ValueError):
    """The generated water cannot be given complete lanes to the game's water."""


def _distances(  # noqa: PLR0913 - bounded paths, an optional goal and terminal stops.
    links: Mapping[int, Sequence[tuple[int, int]]],
    start: int,
    allowed: Collection[int],
    limit: int,
    *,
    target: int | None = None,
    stop_at: Collection[int] = (),
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
        if cell in stop_at:
            continue
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


def _ends(
    links: Mapping[int, Sequence[tuple[int, int]]],
    lanes: Collection[int],
    allowed: Collection[int],
    terminals: Collection[int],
) -> list[int]:
    return [
        cell
        for cell in sorted(lanes)
        if cell not in terminals
        and not any(other in terminals for other, _ in links[cell])
        and sum(other in allowed for other, _ in links[cell]) <= 1
    ]


def _stem(
    links: Graph, start: int, allowed: set[int], terminals: set[int]
) -> tuple[set[int], int | None]:
    """Exclude the incoming branch, including its junction, from a continuation's targets."""
    branch = {start}
    cell = start
    incoming = None
    while True:
        following = [other for other, _ in links[cell] if other in allowed and other not in branch]
        if cell in terminals or len(following) != 1:
            return branch, incoming
        other = following[0]
        if incoming is None:
            incoming = other
        branch.add(other)
        cell = other


def _continuation(
    links: Graph, start: int, shut: set[int], targets: set[int], forward: set[int]
) -> list[int] | None:
    """Shortest closed-water route ahead; otherwise the shortest reachable turn to open water.

    Existing lanes are destinations only: a search cannot walk back along its own lane.
    A complete search proves whether geography permits a forward destination before choosing
    a turn. Both choices are geographic planning, before any closed zones are folded.
    """
    best, parent = _distances(links, start, shut | targets | {start}, 1 << 62, stop_at=targets)
    reached = targets & best.keys()
    ahead = reached & forward
    if not reached:
        return None
    end = min(ahead or reached, key=lambda cell: (best[cell], cell))
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return path


def _leaf_block(  # noqa: C901, PLR0912, PLR0915 - iterative block-cut traversal.
    links: Graph, lanes: set[int], allowed: set[int], terminals: set[int]
) -> tuple[set[int], int, int] | None:
    """Find a cyclic deep-water end attached to the rest of navigation at one junction.

    Degree-one tests miss a broad tip with a loop. The block-cut graph exposes such a tip
    without interpreting a valid route between two coasts as a dead end. A virtual vertex
    joins terminal water for this test only; no such edge is written to the map.
    """
    root = -1
    graph = {cell: [other for other, _ in links[cell] if other in allowed] for cell in allowed}
    contacts = sorted(terminals & allowed)
    graph[root] = contacts
    for cell in contacts:
        graph[cell].append(root)
    discovered: dict[int, int] = {}
    low: dict[int, int] = {}
    parent: dict[int, int] = {}
    blocks: list[set[int]] = []
    edge_stack: list[tuple[int, int]] = []
    clock = 0
    for start in [root, *sorted(allowed)]:
        if start in discovered:
            continue
        discovered[start] = low[start] = clock
        clock += 1
        stack = [start]
        positions = {start: 0}
        while stack:
            here = stack[-1]
            index = positions[here]
            if index < len(graph[here]):
                other = graph[here][index]
                positions[here] += 1
                if other not in discovered:
                    parent[other] = here
                    discovered[other] = low[other] = clock
                    clock += 1
                    edge_stack.append((here, other))
                    positions[other] = 0
                    stack.append(other)
                elif parent.get(here) != other and discovered[other] < discovered[here]:
                    low[here] = min(low[here], discovered[other])
                    edge_stack.append((here, other))
                continue
            _ = stack.pop()
            if here not in parent:
                continue
            previous = parent[here]
            low[previous] = min(low[previous], low[here])
            if low[here] >= discovered[previous]:
                block: set[int] = set()
                while edge_stack:
                    edge = edge_stack.pop()
                    block.update(edge)
                    if edge == (previous, here):
                        break
                blocks.append(block)
    membership: dict[int, int] = {}
    for block in blocks:
        for cell in block:
            membership[cell] = membership.get(cell, 0) + 1
    for block in sorted(blocks, key=min):
        junctions = {cell for cell in block if membership[cell] > 1}
        if len(junctions) != 1 or len(block) < MIN_CYCLIC_BLOCK or not block <= lanes:
            continue
        junction = next(iter(junctions))
        distances, _ = _distances(links, junction, block, 1 << 62)
        tip = max(block - {junction}, key=lambda cell: (distances[cell], -cell))
        return block, tip, junction
    return None


def cyclic_end(
    world: NewWorld,
    lanes: Collection[int],
    navigable: Collection[int],
    terminals: Collection[int],
) -> int | None:
    """A cyclic ocean tip attached at one junction, if one remains in the final water graph."""
    cells = set(navigable)
    block = _leaf_block(_links(world, cells), set(lanes), cells, set(terminals))
    return None if block is None else block[1]


def complete_routes(
    world: NewWorld, waters: Waters, deep: set[int], lanes: set[int], docks: Collection[int]
) -> int:
    """Continue open-ocean ends to another lane, a coast or retained navigable water.

    Global reachability allows a lane attached at just one end. Its incoming stem and junction
    cannot be its destination: that would make a little loop at the same dead end. Prefer
    destinations within 45 degrees of the stem's outward heading, measured with integer dot
    and cross products. If land blocks every such route, take the shortest reachable turn.
    Each iteration opens closed cells; it cannot create another end or close existing water.
    Return the number opened, or raise when no continuation exists.
    """
    sea = set(waters.sea())
    links = _links(world, sea)
    terminals = (sea - deep) | (set(docks) & sea)
    before = len(lanes)
    while True:
        shut = deep - lanes
        allowed = sea - shut
        ends = _ends(links, lanes, allowed, terminals)
        if ends:
            start = ends[0]
            branch, incoming = _stem(links, start, allowed, terminals)
        else:
            block = _leaf_block(links, lanes, allowed, terminals)
            if block is None:
                break
            branch, start, incoming = block
            stem, _ = _stem(links, incoming, allowed - (branch - {incoming}), terminals)
            branch.update(stem)
        targets = sea - shut - branch
        forward: set[int] = set()
        if incoming is not None:
            dr, dc = (int(v) for v in world.centroids[start] - world.centroids[incoming])
            for cell in sorted(targets):
                row, column = (int(v) for v in world.centroids[cell] - world.centroids[start])
                dot = dr * row + dc * column
                if dot > 0 and dot >= abs(dr * column - dc * row):
                    forward.add(cell)
        path = _continuation(links, start, shut, targets, forward)
        if path is None:
            message = f"Ocean lane {start} ends in closed water with no continuation"
            raise LaneError(message)
        lanes.update(deep.intersection(path))
    return len(lanes) - before
