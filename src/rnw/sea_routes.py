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
from collections import Counter
from typing import TYPE_CHECKING, Final

from rnw.sea_policy import MAX_DETOUR
from rnw.seas import Topography
from rnw.topology import adjacency_lengths, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

# A neighbouring coast is at most six typical sea-cell widths away by water.
# Its available route may be at most twice the unrestricted water-only route.
LOCAL_SCALES: Final[int] = 6
MIN_CYCLIC_BLOCK: Final[int] = 3
Graph = dict[int, list[tuple[int, int]]]
STRIP_ROWS: Final[int] = 256


class LaneError(ValueError):
    """The generated water cannot be given complete lanes to the game's water."""


def cross_oceans(  # noqa: C901, PLR0912, PLR0913, PLR0915 - water diagram and routes.
    world: NewWorld,
    waters: Waters,
    deep: set[int],
    lanes: set[int],
    *,
    docks: Collection[int] = (),
    sources: Collection[int] | None = None,
) -> int:
    """Connect neighbouring landmasses across water when their existing voyage is circuitous.

    A multi-source water-distance diagram starts at shores grouped by their landmass and
    position. Its boundaries identify neighbouring stretches and their shortest crossing,
    even across an ocean much wider than a local coastal connection. Shore grouping scales
    with the water's area divided by its shoreline, so long coasts get multiple crossings.
    Islands participate naturally. Only crossings that improve navigation are opened.
    """
    sea = set(waters.sea())
    links = navigation_links(world, waters)
    shores: dict[int, set[int]] = {}
    for first, second in world.edges:
        if first in sea and waters.landmass[second] >= 0:
            shores.setdefault(first, set()).add(int(waters.landmass[second]))
        if second in sea and waters.landmass[first] >= 0:
            shores.setdefault(second, set()).add(int(waters.landmass[first]))
    retained = len(waters.landmass_cells)
    for cell in sea.intersection(docks):
        shores.setdefault(cell, set()).add(retained)
    if not shores:
        return 0
    area = sum(int(world.pixels[cell]) for cell in sea)
    width = max(waters.scale, area // (len(shores) * waters.scale))
    # One closest shore stretch owns each water cell. Ties are deterministic.
    best: dict[int, tuple[int, tuple[int, int, int]]] = {}
    parent: dict[int, int] = {}
    heap: list[tuple[int, tuple[int, int, int], int]] = []
    for cell, masses in sorted(shores.items()):
        row, column = (int(value) for value in world.centroids[cell])
        shore = (min(masses), row // width, column // width)
        best[cell] = (0, shore)
        heapq.heappush(heap, (0, shore, cell))
    while heap:
        distance, shore, cell = heapq.heappop(heap)
        if best[cell] != (distance, shore):
            continue
        for other, length in links[cell]:
            candidate = (distance + length, shore)
            if other not in best or candidate < best[other]:
                best[other] = candidate
                parent[other] = cell
                heapq.heappush(heap, (*candidate, other))
    crossings: dict[tuple[tuple[int, int, int], tuple[int, int, int]], tuple[int, int, int]] = {}
    for cell, neighbours in links.items():
        if cell not in best:
            continue
        distance, mass = best[cell]
        for other, length in neighbours:
            if other not in best or best[other][1] == mass:
                continue
            other_distance, other_mass = best[other]
            pair = (min(mass, other_mass), max(mass, other_mass))
            candidate = (distance + length + other_distance, min(cell, other), max(cell, other))
            if candidate < crossings.get(pair, (1 << 62, 1 << 62, 1 << 62)):
                crossings[pair] = candidate
    allowed = sea - (deep - lanes)
    reached_sources = _reachable(links, allowed, sources) if sources is not None else allowed.copy()
    before = len(lanes)
    for distance, first, second in sorted(crossings.values()):
        path = [first, second]
        for start in (first, second):
            cell = start
            while cell in parent:
                cell = parent[cell]
                path.append(cell)
        start, end = first, second
        while start in parent:
            start = parent[start]
        while end in parent:
            end = parent[end]
        if start not in reached_sources and end not in reached_sources:
            continue
        reached, _ = _distances(links, start, allowed, distance * MAX_DETOUR, target=end)
        if end not in reached:
            opened = deep.intersection(path)
            lanes.update(opened)
            allowed.update(opened)
            reached_sources = _reachable(links, allowed, reached_sources)
    return len(lanes) - before


def _reachable(
    links: Mapping[int, Sequence[tuple[int, int]]],
    allowed: Collection[int],
    sources: Collection[int],
) -> set[int]:
    """Water reachable from current sources, without crossing closed water."""
    seen = set(sources) & set(allowed)
    pending = list(seen)
    while pending:
        for other, _ in links[pending.pop()]:
            if other in allowed and other not in seen:
                seen.add(other)
                pending.append(other)
    return seen


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


def navigation_links(world: NewWorld, waters: Waters) -> Graph:
    """A deep route needs a shared opening at least half a typical band wide.

    Merely touching at a few pixels does not continue an ocean current. Natural
    shallow channels keep all their contacts; this width applies only at deep
    route interfaces. Measure borders in strips without counting band seams twice.
    """
    links = _links(world, waters.sea())
    deep = {cell for cell in links if waters.topography[cell] is Topography.DEEP_OCEAN}
    if not deep:
        return links
    lengths: Counter[tuple[int, int]] = Counter()
    for start in range(0, len(world.labels), STRIP_ROWS):
        rows = world.labels[start : start + STRIP_ROWS]
        pairs, sizes = adjacency_lengths(rows)
        lengths.update(dict(zip(unpack_pairs(pairs), sizes.tolist(), strict=True)))
        if start:
            seam = world.labels[start - 1 : start + 1]
            # Only vertical contacts across this strip seam belong to this pass.
            first, second = seam[0], seam[1]
            for a, b in zip(first.tolist(), second.tolist(), strict=True):
                if a != b:
                    lengths[min(a, b), max(a, b)] += 1
    sizes = sorted(int(world.pixels[cell]) for cell in links)
    scale = min(waters.scale, math.isqrt(sizes[len(sizes) // 2]))
    opening = max(1, scale // 2)
    return {
        cell: [
            (other, distance)
            for other, distance in neighbours
            if (cell not in deep and other not in deep)
            or lengths[min(cell, other), max(cell, other)] >= opening
        ]
        for cell, neighbours in links.items()
    }


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
    links = navigation_links(world, waters)
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
    *,
    links: Graph | None = None,
) -> int | None:
    """A cyclic ocean tip attached at one junction, if one remains in the final water graph."""
    cells = set(navigable)
    block = _leaf_block(
        _links(world, cells) if links is None else links, set(lanes), cells, set(terminals)
    )
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
    links = navigation_links(world, waters)
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
