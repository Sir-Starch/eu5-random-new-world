"""Compact, connected parts of a cell contact graph for the location hierarchy.

Game-independent. One level of the hierarchy (regions of a subcontinent, areas of a
region, provinces of an area) is a balanced geodesic Voronoi partition of the parent's
cells. Every part grows from its sources by Dijkstra over cell contacts, so it is a
shortest-path tree and therefore connected. A landmass without a source of its own (an
island) joins the part of the nearest cell as a whole, so no part ever has two pieces on
one landmass. Every part starts with an additive handicap that grows while it is larger
than its target, so part sizes approach their targets, and movable sources follow their
part's centre (Lloyd relaxation). Integer arithmetic and fixed tie-breaks make every
result a pure function of the inputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from numpy.typing import NDArray

LLOYD_ROUNDS: Final[int] = 6
BALANCE_ROUNDS: Final[int] = 12
CHUNK: Final[int] = 512


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
) -> list[int]:
    """Handicaps that bring part sizes towards their goals with the sources held still.

    With fixed sources a part shrinks as its handicap grows, so this is a subgradient
    ascent; a part's step halves whenever its size error changes sign. Returns the
    handicaps with the smallest total size error seen.
    """
    handicap = list(handicap)
    best: tuple[int, list[int]] | None = None
    step: list[int] = []
    sign = [0] * len(sources)
    for _ in range(BALANCE_ROUNDS):
        sizes = [len(group) for group in _groups(graph, layout, sources, handicap, pinned)]
        goals = _goals(layout, sources, targets, sizes)
        error = sum(abs(size - goal) for size, goal in zip(sizes, goals, strict=True))
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
    error = sum(abs(size - goal) for size, goal in zip(sizes, goals, strict=True))
    return handicap if best is None or error < best[0] else best[1]


def balanced_parts(
    graph: ContactGraph,
    members: Sequence[int],
    sources: Sequence[Sequence[int]],
    targets: Sequence[int],
    *,
    movable: Sequence[bool],
) -> tuple[list[list[int]], list[list[int]]]:
    """Grow one part per source list over ``members``; return the parts and final sources.

    A capacity-constrained centroidal partition (Balzer et al. 2009): the handicaps are
    balanced with the sources held still, then every movable source moves to the cell
    nearest its part's centre on its own landmass, and again. A movable part has one
    pinned source; the sources of other parts (anchors) can be taken by a neighbour.
    ``targets`` are relative part sizes, compared within each landmass and the islands
    that join it.
    """
    current = [list(nodes) for nodes in sources]
    layout = _layout(graph, members, current)
    handicap = [0] * len(current)
    for _ in range(LLOYD_ROUNDS):
        handicap = _balance(graph, layout, current, targets, handicap=handicap, pinned=movable)
        groups = _groups(graph, layout, current, handicap, movable)
        for part, group in enumerate(groups):
            if movable[part]:
                home = layout.piece_of[current[part][0]]
                mainland = [node for node in group if layout.piece_of[node] == home]
                middle = np.array(centre_of(graph, mainland), dtype=np.int64)
                gap = ((graph.centres[mainland] - middle) ** 2).sum(axis=1)
                current[part] = [mainland[int(np.argmin(gap))]]
    handicap = _balance(graph, layout, current, targets, handicap=handicap, pinned=movable)
    return _groups(graph, layout, current, handicap, movable), current


def split(graph: ContactGraph, members: Sequence[int], count: int) -> list[list[int]]:
    """``count`` compact connected parts of about equal size."""
    sources = [[node] for node in spread_sources(graph, members, count)]
    parts, _ = balanced_parts(graph, members, sources, [1] * count, movable=[True] * count)
    return parts


def keyed_parts(
    graph: ContactGraph,
    members: Sequence[int],
    centres: Sequence[tuple[int, int]],
    weights: Sequence[int],
) -> list[list[int]]:
    """One part per key, the key's part nearest its centre and sized by its weight.

    Equal parts come first; keys then take the parts closest to them, and the parts
    are rebalanced to the key weights from where the equal parts left their sources.
    """
    count = len(weights)
    sources = [[node] for node in spread_sources(graph, members, count)]
    parts, moved = balanced_parts(graph, members, sources, [1] * count, movable=[True] * count)
    pairing = match([centre_of(graph, part) for part in parts], centres)
    keyed: list[list[int]] = [[] for _ in range(count)]
    for part, key in enumerate(pairing):
        keyed[key] = moved[part]
    parts, _ = balanced_parts(graph, members, keyed, weights, movable=[True] * count)
    return parts


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
