"""Compact, connected parts of a cell contact graph for the location hierarchy.

Game-independent. One level of the hierarchy (regions of a subcontinent, areas of a
region, provinces of an area) is a balanced geodesic Voronoi partition of the parent's
cells. Every part grows from its sources by Dijkstra over cell contacts, so it is a
shortest-path tree and therefore connected. A landmass without a source of its own (an
island) joins the part of the nearest cell as a whole, so no part ever has two pieces on
one landmass. Every part starts with an additive handicap that grows while it is larger
than its target, so part sizes approach their targets, and movable sources follow their
part's centre (Lloyd relaxation). The top level can instead be cut from north to south
(``neck_parts``): each boundary is the shortest cut, by maximum flow, within a window of
latitudes around the part's share, tried at several latitudes for the size nearest the share,
so it runs through a landmass's waist and joins small landmasses whole; a part may hold two
pieces of one landmass when each can hold a region. Integer arithmetic and fixed tie-breaks
make every result a pure function of the inputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

import numpy as np

from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from numpy.typing import NDArray

LLOYD_ROUNDS: Final[int] = 6
BALANCE_ROUNDS: Final[int] = 12
CHUNK: Final[int] = 512
NECK_WINDOW: Final[int] = 200
NECK_CONTACT: Final[int] = 1000
NECK_PULL: Final[int] = 150
NECK_REACH: Final[int] = 150
NECK_STEP: Final[int] = 10
NECK_CELLS_PER_CONTACT: Final[int] = 4


class PartitionError(ValueError):
    """A level cannot be split as asked; this is a caller bug."""


@dataclass(frozen=True, slots=True, eq=False)
class ContactGraph:
    """Cell centres (row, column) and contacts; a link is (neighbour, centre distance)."""

    centres: NDArray[np.int64]
    links: tuple[tuple[tuple[int, int], ...], ...]


def contact_graph(
    centres: NDArray[np.int64], edges: Iterable[tuple[int, int]], keep: Sequence[bool]
) -> ContactGraph:
    """Contacts between kept cells, each as long as the distance of their centres."""
    rows = [(int(row), int(column)) for row, column in centres.tolist()]
    links: list[list[tuple[int, int]]] = [[] for _ in rows]
    for first, second in edges:
        if keep[first] and keep[second]:
            (row_a, column_a), (row_b, column_b) = rows[first], rows[second]
            length = max(1, math.isqrt((row_a - row_b) ** 2 + (column_a - column_b) ** 2))
            links[first].append((second, length))
            links[second].append((first, length))
    return ContactGraph(centres, tuple(tuple(sorted(item)) for item in links))


def pieces(graph: ContactGraph, members: Iterable[int]) -> list[list[int]]:
    """Connected pieces of ``members``, each sorted, in order of their lowest cell."""
    inside = set(members)
    seen: set[int] = set()
    found: list[list[int]] = []
    for start in sorted(inside):
        if start in seen:
            continue
        seen.add(start)
        piece, stack = [start], [start]
        while stack:
            for neighbour, _ in graph.links[stack.pop()]:
                if neighbour in inside and neighbour not in seen:
                    seen.add(neighbour)
                    piece.append(neighbour)
                    stack.append(neighbour)
        found.append(sorted(piece))
    return found


def centre_of(graph: ContactGraph, members: Sequence[int]) -> tuple[int, int]:
    """Mean cell centre of ``members`` (floored)."""
    total = graph.centres[list(members)].sum(axis=0) // len(members)
    return int(total[0]), int(total[1])


def match(points: Sequence[tuple[int, int]], targets: Sequence[tuple[int, int]]) -> list[int]:
    """Pair each point with a distinct target, closest pairs first; -1 once targets run out."""
    pairing = [-1] * len(points)
    if not points or not targets:
        return pairing
    first = np.array(points, dtype=np.int64)
    second = np.array(targets, dtype=np.int64)
    delta = first[:, np.newaxis, :] - second[np.newaxis, :, :]
    distance = (delta * delta).sum(axis=2).ravel()
    rows, columns = np.divmod(np.arange(distance.size, dtype=np.int64), len(targets))
    taken: set[int] = set()
    for flat in np.lexsort((columns, rows, distance)).tolist():
        point, target = divmod(int(flat), len(targets))
        if pairing[point] < 0 and target not in taken:
            pairing[point] = target
            taken.add(target)
    return pairing


def _farthest(centres: NDArray[np.int64], piece: list[int], count: int) -> list[int]:
    """The cell nearest the piece's centre, then each cell farthest from those chosen."""
    points = centres[piece]
    middle = points.sum(axis=0) // len(piece)
    chosen = [int(np.argmin(((points - middle) ** 2).sum(axis=1)))]
    gap = ((points - points[chosen[0]]) ** 2).sum(axis=1)
    gap[chosen[0]] = -1
    while len(chosen) < count:
        pick = int(np.argmax(gap))
        chosen.append(pick)
        gap = np.minimum(gap, ((points - points[pick]) ** 2).sum(axis=1))
        gap[chosen] = -1
    return [piece[index] for index in chosen]


def spread_sources(graph: ContactGraph, members: Sequence[int], count: int) -> list[int]:
    """``count`` well-spread cells; landmasses get them in proportion to their size.

    Pieces share the count by largest remainder, so a piece far below an average part
    gets none and later joins its nearest part.
    """
    if not 1 <= count <= len(members):
        message = f"Cannot split {len(members)} cells into {count} parts"
        raise PartitionError(message)
    found = pieces(graph, members)
    total = len(members)
    shares = [len(piece) * count // total for piece in found]
    order = sorted(range(len(found)), key=lambda item: (-(len(found[item]) * count % total), item))
    for item in order[: count - sum(shares)]:
        shares[item] += 1
    sources: list[int] = []
    for piece, share in zip(found, shares, strict=True):
        if share:
            sources.extend(_farthest(graph.centres, piece, share))
    return sources


def _nearest_cell(
    centres: NDArray[np.int64], piece: list[int], candidates: NDArray[np.int64]
) -> int:
    """The candidate closest to any cell of ``piece`` (lowest indices on ties)."""
    best: tuple[int, int] | None = None
    targets = centres[candidates]
    for start in range(0, len(piece), CHUNK):
        points = centres[piece[start : start + CHUNK]]
        delta = points[:, np.newaxis, :] - targets[np.newaxis, :, :]
        distance = (delta * delta).sum(axis=2)
        flat = int(np.argmin(distance))
        value = int(distance.ravel()[flat])
        if best is None or value < best[0]:
            best = (value, int(candidates[flat % len(candidates)]))
    if best is None:
        message = "An empty piece has no nearest cell"
        raise PartitionError(message)
    return best[1]


def _grow(
    graph: ContactGraph,
    inside: set[int],
    sources: list[list[int]],
    handicap: list[int],
    pinned: Sequence[bool],
) -> dict[int, int]:
    """Multi-source Dijkstra from every source at its part's handicap.

    Pinned sources always keep their part, so a pinned part never vanishes; other
    sources can be taken by a part that reaches them first.
    """
    owner = {node: part for part, nodes in enumerate(sources) if pinned[part] for node in nodes}
    heap: list[tuple[int, int, int]] = []
    for part, nodes in enumerate(sources):
        for node in nodes:
            if not pinned[part]:
                heap.append((handicap[part], part, node))
                continue
            for neighbour, length in graph.links[node]:
                if neighbour in inside and neighbour not in owner:
                    heap.append((handicap[part] + length, part, neighbour))
    heapq.heapify(heap)
    while heap:
        distance, part, node = heapq.heappop(heap)
        if node in owner:
            continue
        owner[node] = part
        for neighbour, length in graph.links[node]:
            if neighbour in inside and neighbour not in owner:
                heapq.heappush(heap, (distance + length, part, neighbour))
    return owner


@dataclass(frozen=True, slots=True)
class _Layout:
    """Pieces of the members: which hold sources, and where the others attach."""

    inside: set[int]
    piece_of: dict[int, int]
    islands: list[tuple[list[int], int]]
    spacing: int


def _layout(graph: ContactGraph, members: Sequence[int], sources: list[list[int]]) -> _Layout:
    found = pieces(graph, members)
    piece_of = {node: number for number, piece in enumerate(found) for node in piece}
    seeded = {piece_of[node] for nodes in sources for node in nodes}
    rooted = np.array([node for number in sorted(seeded) for node in found[number]], dtype=np.int64)
    islands = [
        (piece, _nearest_cell(graph.centres, piece, rooted))
        for number, piece in enumerate(found)
        if number not in seeded
    ]
    inside = set(members)
    lengths = sorted(
        length for node in inside for neighbour, length in graph.links[node] if neighbour in inside
    )
    return _Layout(inside, piece_of, islands, lengths[len(lengths) // 2] if lengths else 1)


def _groups(
    graph: ContactGraph,
    layout: _Layout,
    sources: list[list[int]],
    handicap: list[int],
    pinned: Sequence[bool],
) -> list[list[int]]:
    """Cells of every part, islands included, each list sorted."""
    owner = _grow(graph, layout.inside, sources, handicap, pinned)
    for piece, anchor in layout.islands:
        for node in piece:
            owner[node] = owner[anchor]
    groups: list[list[int]] = [[] for _ in sources]
    for node in sorted(owner):
        groups[owner[node]].append(node)
    return groups


def _goals(
    layout: _Layout, sources: list[list[int]], targets: Sequence[int], sizes: list[int]
) -> list[int]:
    """Targets scaled to the cells each landmass (with its islands) actually holds."""
    cluster = [layout.piece_of[nodes[0]] for nodes in sources]
    held: dict[int, int] = {}
    wanted: dict[int, int] = {}
    for part, number in enumerate(cluster):
        held[number] = held.get(number, 0) + sizes[part]
        wanted[number] = wanted.get(number, 0) + targets[part]
    return [
        max(1, held[number] * targets[part] // max(1, wanted[number]))
        for part, number in enumerate(cluster)
    ]


def _balance(  # noqa: PLR0913 - balancing reads the layout, sources, targets and state.
    graph: ContactGraph,
    layout: _Layout,
    sources: list[list[int]],
    targets: Sequence[int],
    *,
    handicap: list[int],
    pinned: Sequence[bool],
    minimum: Sequence[int] = (),
) -> list[int]:
    """Handicaps that bring part sizes towards their goals with the sources held still.

    With fixed sources a part shrinks as its handicap grows, so this is a subgradient
    ascent; a part's step halves whenever its size error changes sign. Returns the
    handicaps with the smallest child-capacity deficit, then total size error seen.
    """
    handicap = list(handicap)
    best: tuple[tuple[int, int], list[int]] | None = None
    step: list[int] = []
    sign = [0] * len(sources)
    for _ in range(BALANCE_ROUNDS):
        checkpoint()
        sizes = [len(group) for group in _groups(graph, layout, sources, handicap, pinned)]
        goals = _goals(layout, sources, targets, sizes)
        error = _partition_error(sizes, goals, minimum)
        if best is None or error < best[0]:
            best = (error, handicap)
        if not step:
            step = [layout.spacing * math.isqrt(goal) // 2 for goal in goals]
        for part, goal in enumerate(goals):
            excess = sizes[part] - goal
            now = (excess > 0) - (excess < 0)
            if now and now == -sign[part]:
                step[part] = max(1, step[part] // 2)
            sign[part] = now or sign[part]
            handicap[part] += step[part] * max(-goal, min(goal, excess)) // goal
        lowest = min(handicap)
        handicap = [value - lowest for value in handicap]
    sizes = [len(group) for group in _groups(graph, layout, sources, handicap, pinned)]
    goals = _goals(layout, sources, targets, sizes)
    error = _partition_error(sizes, goals, minimum)
    return handicap if best is None or error < best[0] else best[1]


def _partition_error(
    sizes: Sequence[int], goals: Sequence[int], minimum: Sequence[int]
) -> tuple[int, int]:
    """Reserve room for child keys before optimizing size, without assigning identities."""
    deficit = (
        sum(max(0, need - size) for size, need in zip(sorted(sizes), sorted(minimum), strict=True))
        if minimum
        else 0
    )
    return deficit, sum(abs(size - goal) for size, goal in zip(sizes, goals, strict=True))


def balanced_parts(  # noqa: PLR0913 - the sources, their targets and how each may move or be taken.
    graph: ContactGraph,
    members: Sequence[int],
    sources: Sequence[Sequence[int]],
    targets: Sequence[int],
    *,
    movable: Sequence[bool],
    pinned: Sequence[bool] | None = None,
    minimum: Sequence[int] = (),
) -> tuple[list[list[int]], list[list[int]]]:
    """Grow one part per source list over ``members``; return the parts and final sources.

    A capacity-constrained centroidal partition (Balzer et al. 2009): the handicaps are
    balanced with the sources held still, then every movable source moves to the cell
    nearest its part's centre on its own landmass, and again. The sources of a pinned part
    (by default a movable one, which has a single source) always keep their part; the sources
    of other parts (anchors) can be taken by a neighbour. ``targets`` are relative part sizes,
    compared within each landmass and the islands that join it. ``minimum`` is a
    multiset of required child-key counts, before part identities are known. The
    constrained search selects its latest feasible Lloyd iterate; an infeasible
    search fails before any keys or physical profiles are assigned.
    """
    current = [list(nodes) for nodes in sources]
    if minimum and (
        len(minimum) != len(current) or min(minimum) < 1 or sum(minimum) > len(members)
    ):
        message = "The partition cannot hold its child-key minima"
        raise PartitionError(message)
    layout = _layout(graph, members, current)
    handicap = [0] * len(current)
    held = movable if pinned is None else pinned
    candidates: list[tuple[list[list[int]], list[list[int]]]] = []
    for _ in range(LLOYD_ROUNDS):
        checkpoint()
        handicap = _balance(
            graph, layout, current, targets, handicap=handicap, pinned=held, minimum=minimum
        )
        groups = _groups(graph, layout, current, handicap, held)
        if minimum:
            candidates.append((groups, [list(nodes) for nodes in current]))
        for part, group in enumerate(groups):
            if movable[part]:
                home = layout.piece_of[current[part][0]]
                mainland = [node for node in group if layout.piece_of[node] == home]
                middle = np.array(centre_of(graph, mainland), dtype=np.int64)
                gap = ((graph.centres[mainland] - middle) ** 2).sum(axis=1)
                current[part] = [mainland[int(np.argmin(gap))]]
    handicap = _balance(
        graph, layout, current, targets, handicap=handicap, pinned=held, minimum=minimum
    )
    groups = _groups(graph, layout, current, handicap, held)
    if minimum:
        candidates.append((groups, current))
        # Lloyd movement is a bounded search over layouts, not a hard constraint.
        # Choose its latest feasible iterate before any identities are assigned.
        _, (groups, current) = min(
            enumerate(candidates),
            key=lambda item: (
                _partition_error([len(group) for group in item[1][0]], targets, minimum)[0],
                -item[0],
            ),
        )
    if _partition_error([len(group) for group in groups], targets, minimum)[0]:
        message = "No constructed partition meets its child-key minima"
        raise PartitionError(message)
    return groups, current


def split(
    graph: ContactGraph, members: Sequence[int], count: int, *, minimum: Sequence[int] = ()
) -> list[list[int]]:
    """``count`` compact connected parts, reserving the supplied child-key capacities."""
    sources = [[node] for node in spread_sources(graph, members, count)]
    parts, _ = balanced_parts(
        graph, members, sources, [1] * count, movable=[True] * count, minimum=minimum
    )
    return parts


@final
class _Flow:
    """A maximum flow (Dinic) on integer capacities; arcs are stored in pairs (``arc ^ 1``)."""

    def __init__(self, size: int) -> None:
        self.size = size
        self.head: list[int] = []
        self.capacity: list[int] = []
        self.arcs: list[list[int]] = [[] for _ in range(size)]

    def add(self, first: int, second: int, forward: int, backward: int = 0) -> None:
        self.arcs[first].append(len(self.head))
        self.head.append(second)
        self.capacity.append(forward)
        self.arcs[second].append(len(self.head))
        self.head.append(first)
        self.capacity.append(backward)

    def _levels(self, source: int) -> list[int]:
        level = [-1] * self.size
        level[source] = 0
        queue = [source]
        for node in queue:
            for arc in self.arcs[node]:
                if self.capacity[arc] > 0 and level[self.head[arc]] < 0:
                    level[self.head[arc]] = level[node] + 1
                    queue.append(self.head[arc])
        return level

    def _augment(self, source: int, sink: int, level: list[int], seen: list[int]) -> int:
        """Push one blocking-flow path from ``source``; 0 when the level graph is exhausted."""
        path: list[int] = []
        node = source
        while True:
            if node == sink:
                pushed = min(self.capacity[arc] for arc in path)
                for arc in path:
                    self.capacity[arc] -= pushed
                    self.capacity[arc ^ 1] += pushed
                return pushed
            arcs = self.arcs[node]
            while seen[node] < len(arcs):
                arc = arcs[seen[node]]
                following = self.head[arc]
                if self.capacity[arc] > 0 and level[following] == level[node] + 1:
                    path.append(arc)
                    node = following
                    break
                seen[node] += 1
            else:
                if not path:
                    return 0
                level[node] = -1
                node = self.head[path.pop() ^ 1]
                seen[node] += 1

    def source_side(self, source: int, sink: int) -> list[bool]:
        """Saturate the flow, then the nodes the source still reaches: the smallest minimum cut."""
        while True:
            level = self._levels(source)
            if level[sink] < 0:
                return [reached >= 0 for reached in level]
            seen = [0] * self.size
            while self._augment(source, sink, level, seen):
                pass


def _north_side(graph: ContactGraph, members: Sequence[int], count: int) -> list[int]:
    """About ``count`` of the northernmost members: the shortest cut near that latitude.

    Members are ranked by row, then column and index. The ``count`` northernmost are the
    banded answer; the cut may instead follow any line inside a window of ``NECK_WINDOW``
    permille of the members on either side of it, where it costs ``NECK_CONTACT`` per contact
    it severs and each member pays up to ``NECK_PULL`` for lying on the far side of the
    banded line, growing with its distance from it. A landmass whose narrowest waist lies in
    the window is cut there; one that lies inside it is joined whole to the side its
    latitude favours. Members beyond the window keep their side. The minimum cut is exact
    (maximum flow), and the smallest one is taken, so the result is a pure function of the
    inputs.
    """
    ranked = sorted(members, key=lambda node: (*graph.centres[node].tolist(), node))
    size = len(ranked)
    half = max(1, size * NECK_WINDOW // 1000)
    first = max(1, count - half)
    last = min(size - 1, count + half)
    inside = {node: number for number, node in enumerate(ranked[first:last])}
    above, below = set(ranked[:first]), set(ranked[last:])
    source, sink = len(inside), len(inside) + 1
    flow = _Flow(len(inside) + 2)
    width = max(1, half)
    for node, number in inside.items():
        rank = first + number
        pulled = NECK_PULL * (count - rank) // width
        toward_source, toward_sink = max(0, pulled), max(0, -pulled)
        for neighbour, _ in graph.links[node]:
            if neighbour in inside:
                if neighbour > node:
                    flow.add(number, inside[neighbour], NECK_CONTACT, NECK_CONTACT)
            elif neighbour in above:
                toward_source += NECK_CONTACT
            elif neighbour in below:
                toward_sink += NECK_CONTACT
        if toward_source:
            flow.add(source, number, toward_source)
        if toward_sink:
            flow.add(number, sink, toward_sink)
    reached = flow.source_side(source, sink)
    return ranked[:first] + [node for node, number in inside.items() if reached[number]]


def _split_pieces(
    graph: ContactGraph, landmasses: Sequence[Sequence[int]], cells: Sequence[int], least: int
) -> tuple[list[int], list[int]]:
    """``cells`` as (kept, small): small are pieces under ``least`` beside a larger one there."""
    held = set(cells)
    kept: list[int] = []
    small: list[int] = []
    for landmass in landmasses:
        found = pieces(graph, [node for node in landmass if node in held])
        for number, piece in enumerate(sorted(found, key=lambda cells: (-len(cells), cells[0]))):
            (kept if number == 0 or len(piece) >= least else small).extend(piece)
    return sorted(kept), sorted(small)


def _closest_north(
    graph: ContactGraph, members: Sequence[int], target: int, least: Sequence[int]
) -> list[int]:
    """The north side, from cuts near several latitudes, whose size comes closest to ``target``.

    A cut at the waist takes whole peninsulas and islands, so the size of a side moves in steps
    as the latitude moves, and the cut at the banded line alone can stop far from the share.
    Lines are tried from ``NECK_REACH`` permille of the members above ``target`` to as many
    below it, first every five ``NECK_STEP`` permille, then every step around the best. A side
    is what its cut holds with the settling of ``_settle_pieces`` done: its pieces under
    ``least[0]`` cells that share a landmass with a larger one go to the other side, and the
    other side's under ``least[1]`` come to it. A cut scores its distance in cells from
    ``target`` plus ``NECK_CELLS_PER_CONTACT`` cells for each contact it severs; ties go to the
    line nearest the banded one. The scan is fixed, so the result is a pure function of the
    inputs.
    """
    size = len(members)
    step = max(1, size * NECK_STEP // 1000)
    reach = size * NECK_REACH // 1000
    inside = set(members)
    landmasses = pieces(graph, members)
    seen: dict[int, tuple[tuple[int, int, int], list[int]]] = {}

    def score(asked: int) -> tuple[int, int, int]:
        asked = min(max(1, asked), size - 1)
        if asked not in seen:
            north, _ = _split_pieces(
                graph, landmasses, _north_side(graph, members, asked), least[0]
            )
            held = set(north)
            rest = [node for node in members if node not in held]
            _, strays = _split_pieces(graph, landmasses, rest, least[1])
            north = sorted([*north, *strays])
            held = set(north)
            severed = sum(
                1
                for node in north
                for neighbour, _ in graph.links[node]
                if neighbour in inside and neighbour not in held
            )
            miss = abs(len(north) - target) + NECK_CELLS_PER_CONTACT * severed
            seen[asked] = ((miss, abs(asked - target), asked), north)
        return seen[asked][0]

    coarse = range(target - reach, target + reach + 1, 5 * step)
    best = min(score(asked) for asked in [target, *coarse])
    for asked in range(best[2] - 4 * step, best[2] + 4 * step + 1, step):
        _ = score(asked)
    return seen[min(score(asked) for asked in sorted(seen))[2]][1]


def _settle_pieces(
    graph: ContactGraph,
    members: Sequence[int],
    owner: dict[int, int],
    lowest: Sequence[int],
) -> list[list[int]]:
    """Parts whose pieces on a landmass are each at least ``lowest`` of the part, or its largest.

    On every landmass a part keeps its largest piece and any piece of ``lowest[part]`` cells or
    more: a piece that large can hold a region of its own. Every smaller piece joins the part it
    has most contacts with (lowest index on ties), which can make a piece of that part larger, so
    the pass repeats until nothing moves. A part is never emptied: its largest piece stays.
    """
    landmasses = pieces(graph, members)
    moved = True
    while moved:
        moved = False
        for part, least in enumerate(lowest):
            for landmass in landmasses:
                found = pieces(graph, [node for node in landmass if owner[node] == part])
                for piece in sorted(found, key=lambda cells: (-len(cells), cells[0]))[1:]:
                    if len(piece) >= least:
                        continue
                    inside = set(piece)
                    counts: dict[int, int] = {}
                    for node in piece:
                        for neighbour, _ in graph.links[node]:
                            if neighbour in owner and neighbour not in inside:
                                counts[owner[neighbour]] = counts.get(owner[neighbour], 0) + 1
                    target = min(counts, key=lambda other: (-counts[other], other))
                    owner.update(dict.fromkeys(piece, target))
                    moved = True
    parts: list[list[int]] = [[] for _ in lowest]
    for node in sorted(owner):
        parts[owner[node]].append(node)
    if not all(parts):
        message = "A part lost all its cells"
        raise PartitionError(message)
    return parts


def neck_parts(
    graph: ContactGraph,
    members: Sequence[int],
    weights: Sequence[int],
    lowest: Sequence[int] = (),
) -> list[list[int]]:
    """Parts from the first row to the last, each about its ``weights`` share of members.

    Parts are cut off one at a time from the north: each takes the shortest cut, in contacts,
    near the latitude that gives it its share of the cells left, tried at several latitudes
    for the size nearest its share (``_closest_north``). A boundary therefore runs through a
    landmass's waist instead of along a row, and a small landmass is not sliced.

    A part may hold several pieces of one landmass, for instance two peninsulas that hang south
    from a body that belongs to the north, as a subcontinent does on the game's own map. Only a
    piece smaller than ``lowest[part]`` cells (1 by default, so none) beside a larger one on
    its landmass joins the part it touches most (``_settle_pieces``): it is too small to hold
    a region of its own.
    """
    if not weights or min(weights) < 1 or len(members) < len(weights):
        message = f"Cannot cut {len(members)} cells by the weights {list(weights)}"
        raise PartitionError(message)
    owner: dict[int, int] = {}
    left = sorted(members)
    least = list(lowest) or [1] * len(weights)
    for part, weight in enumerate(weights[:-1]):
        count = weight * len(left) // sum(weights[part:])
        count = min(max(1, count), len(left) - (len(weights) - part - 1))
        north = _closest_north(graph, left, count, least[part : part + 2])
        owner.update(dict.fromkeys(north, part))
        taken = set(north)
        left = [node for node in left if node not in taken]
    owner.update(dict.fromkeys(left, len(weights) - 1))
    return _settle_pieces(graph, members, owner, least)


def piece_counts(found: Sequence[Sequence[int]], size: int, *, at_least: int) -> list[int]:
    """Parts per piece: one per ``size`` cells, at least one each and ``at_least`` in all.

    Extra parts go to the piece with the most cells per part, while it has room.
    """
    counts = [max(1, (len(piece) + size // 2) // size) for piece in found]
    while sum(counts) < at_least:
        room = [number for number, piece in enumerate(found) if counts[number] < len(piece)]
        if not room:
            break
        widest = max(
            room, key=lambda number: (len(found[number]) * size // counts[number], -number)
        )
        counts[widest] += 1
    return counts


def absorb_small_pieces(
    graph: ContactGraph, parts: Sequence[Sequence[int]], *, first: int, minimum: int
) -> list[list[int]]:
    """Move small side pieces of the first ``first`` parts to the part they touch most.

    Each of those parts keeps its largest piece; another piece below ``minimum`` cells
    joins the part it has most contacts with (lowest index on ties), as an island too
    small for a part of its own joins its nearest part.
    """
    owner = {cell: number for number, part in enumerate(parts) for cell in part}
    for number in range(first):
        mine = [cell for cell in sorted(owner) if owner[cell] == number]
        found = sorted(pieces(graph, mine), key=lambda piece: (-len(piece), piece[0]))
        for piece in found[1:]:
            if len(piece) >= minimum:
                continue
            inside = set(piece)
            counts: dict[int, int] = {}
            for cell in piece:
                for neighbour, _ in graph.links[cell]:
                    if neighbour not in inside and neighbour in owner:
                        counts[owner[neighbour]] = counts.get(owner[neighbour], 0) + 1
            if counts:
                target = min(counts, key=lambda part: (-counts[part], part))
                for cell in piece:
                    owner[cell] = target
    moved: list[list[int]] = [[] for _ in parts]
    for cell in sorted(owner):
        moved[owner[cell]].append(cell)
    return moved


def split_landmasses(
    graph: ContactGraph, groups: Iterable[Sequence[int]], *, exempt: set[int] | None = None
) -> list[int]:
    """Indices of groups with two pieces on one landmass (or water body) of ``graph``."""
    groups = list(groups)
    everything = [node for group in groups for node in group]
    mass = {
        node: number for number, piece in enumerate(pieces(graph, everything)) for node in piece
    }
    broken: list[int] = []
    for number, group in enumerate(groups):
        if exempt and number in exempt:
            continue
        masses = [mass[piece[0]] for piece in pieces(graph, group)]
        if len(masses) != len(set(masses)):
            broken.append(number)
    return broken
