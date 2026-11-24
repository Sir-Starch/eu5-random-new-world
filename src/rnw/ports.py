"""Ports of a generated coast: one for every land location, at least one for every coastal sea zone.

Game-independent. EU5 gives a land location one port, a row of ``ports.csv`` that names one sea
zone it touches (the game's own file has no location twice [V-LOCAL 1.4.3, C233]). Its map
checker logs ``Coastal Seazone ... has no ports connected to it`` for a sea zone that touches a
land location and is named by no port row, and ``Location ... is coastal but has no port setup``
for a land location without a row [V-GAME 1.4.4, C232]. Choosing for every land cell the sea it
touches longest, as the first exports did, leaves a sea zone without a port whenever each of
its land neighbours prefers another: 48 of the 1,900 zones of the reference world.

Whether every coastal sea zone can be given a port of its own is Hall's condition on a bipartite
graph: land cells on one side, the sea cells they touch on the other. ``plan_ports`` finds a
matching that serves every sea zone it can and gives every other land cell the sea it touches
longest. ``settle_seas`` makes the condition true by construction: a sea cell that cannot be
served is made one cell with a neighbouring sea cell (never a land cell turned into something
else), so the world the rest of the generator sees has a port for every coastal zone. With
``dissolve`` (epoch 64, ``epoch.COMPACT_SEAS``) a cell that two or more served neighbours can take
between them is not folded into one of them but divided among them along the middle of the
cell, so that no cell doubles in size for it.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np

from rnw import _native
from rnw.model import CellClass
from rnw.newworld import STRIP_ROWS, derive_world
from rnw.progress import checkpoint
from rnw.topology import adjacency_lengths, label_components, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.newworld import NewWorld

# A cell is divided among the served cells that border it only if there are this many of them.
MIN_TAKERS = 2


class PortError(ValueError):
    """A coastal sea zone cannot be given a port, whatever is merged."""


@dataclass(frozen=True, slots=True)
class PortPlan:
    """The sea each land location's port names, and the coastal seas left without one."""

    port: dict[int, int]
    unserved: tuple[int, ...]


def plan_ports(links: Mapping[int, Mapping[int, int]], needed: Iterable[int]) -> PortPlan:
    """A port for every land with a sea to touch, and for as many ``needed`` seas as possible.

    ``links[land][sea]`` is how long the two touch. A sea is served by a land of its own, found
    by augmenting paths (a land that serves one sea gives it up when that sea can be served by
    another), so the seas served are as many as any assignment can serve; the lands that are
    not needed for one name the sea they touch longest (the lowest number on a tie). A land
    prefers the sea it touches longest, so where nothing competes the choice is the old one.
    """
    favourite = {
        land: min(seas, key=lambda sea: (-seas[sea], sea)) for land, seas in links.items() if seas
    }
    lands_of: dict[int, list[int]] = {}
    for land in favourite:
        for sea in links[land]:
            lands_of.setdefault(sea, []).append(land)
    for sea, lands in lands_of.items():
        lands.sort(key=lambda land, sea=sea: (favourite[land] != sea, -links[land][sea], land))
    matching = _Matching(lands_of)
    unserved = [
        start
        for start in sorted(set(needed), key=lambda sea: (len(lands_of.get(sea, ())), sea))
        if not matching.augment(start)
    ]
    port = {land: matching.holder.get(land, favourite[land]) for land in favourite}
    return PortPlan(port, tuple(sorted(unserved)))


class _Matching:
    """A land for each sea served so far, grown one sea at a time along augmenting paths."""

    __slots__: tuple[str, ...] = ("holder", "lands_of")

    def __init__(self, lands_of: Mapping[int, list[int]]) -> None:
        self.lands_of: Mapping[int, list[int]] = lands_of
        self.holder: dict[int, int] = {}

    def augment(self, start: int) -> bool:
        """Give ``start`` a land of its own, moving other seas to other lands if it must."""
        via: dict[int, tuple[int, int]] = {}
        seen_lands: set[int] = set()
        seen_seas = {start}
        queue = deque([start])
        while queue:
            sea = queue.popleft()
            for land in self.lands_of.get(sea, ()):
                if land in seen_lands:
                    continue
                seen_lands.add(land)
                owner = self.holder.get(land)
                if owner is None:
                    self._shift(start, sea, land, via)
                    return True
                if owner not in seen_seas:
                    seen_seas.add(owner)
                    via[owner] = (sea, land)
                    queue.append(owner)
        return False

    def _shift(self, start: int, sea: int, land: int, via: Mapping[int, tuple[int, int]]) -> None:
        """Walk the path back from its free land: each sea takes the land of the next."""
        while True:
            self.holder[land] = sea
            if sea == start:
                return
            sea, land = via[sea]


@dataclass(frozen=True, slots=True)
class ForeignCoast:
    """Land of the game's own map that touches generated water.

    ``free`` maps a vanilla land location whose port row names a sea zone the canvas replaced
    (so the export writes the row again) to the generated sea cells it touches; ``held`` are the
    generated sea cells that touch vanilla land whose port row stays with a sea zone of its own,
    so only generated land can serve them.
    """

    free: Mapping[str, frozenset[int]] = field(default_factory=dict[str, frozenset[int]])
    held: frozenset[int] = frozenset()

    def renumbered(self, cell_of: Sequence[int]) -> ForeignCoast:
        """The same coast in a world whose cells were renumbered (``Settled.cell_of``)."""
        return ForeignCoast(
            {key: frozenset(cell_of[cell] for cell in cells) for key, cells in self.free.items()},
            frozenset(cell_of[cell] for cell in self.held),
        )


def coast_links(
    world: NewWorld, foreign: ForeignCoast, lengths: Mapping[tuple[int, int], int]
) -> tuple[dict[int, dict[int, int]], set[int]]:
    """Land-to-sea links of a world and the sea cells that need a port.

    Land cells are numbered as in the world; the vanilla land locations of ``foreign.free`` are
    numbered -1, -2, ... in key order. Wasteland and lakes are no land for a port: the engine
    leaves a sea zone beside only those without a port [V-GAME 1.4.4, C232].
    """
    kinds = world.classes
    links: dict[int, dict[int, int]] = {}
    for (first, second), length in lengths.items():
        for land, sea in ((first, second), (second, first)):
            if kinds[land] is CellClass.LAND and kinds[sea] is CellClass.SEA:
                links.setdefault(land, {})[sea] = length
    needed = {sea for seas in links.values() for sea in seas} | set(foreign.held)
    for number, key in enumerate(sorted(foreign.free), start=1):
        seas = foreign.free[key]
        links[-number] = dict.fromkeys(sorted(seas), 1)
        needed.update(seas)
    return links, needed


def pair_lengths(world: NewWorld) -> dict[tuple[int, int], int]:
    """How many pixels of border every two touching cells share."""
    pairs, counts = adjacency_lengths(world.labels, wrap_x=world.wrap_x)
    return {
        (first, second): length
        for (first, second), length in zip(unpack_pairs(pairs), counts.tolist(), strict=True)
        if first >= 0 and second >= 0
    }


def served(world: NewWorld, foreign: ForeignCoast) -> PortPlan:
    """The ports of a world as ``plan_ports`` plans them, for tests and the export's check."""
    links, needed = coast_links(world, foreign, pair_lengths(world))
    return plan_ports(links, needed)


@dataclass(frozen=True, slots=True)
class Settled:
    """A world whose coastal sea zones can all have a port, with what changed."""

    world: NewWorld
    foreign: ForeignCoast
    cell_of: tuple[int, ...]
    merged: int


def settle_seas(
    world: NewWorld,
    foreign: ForeignCoast | None = None,
    *,
    shared_coast: bool = False,
    minimum_sea: int = 0,
    dissolve: bool = False,
) -> Settled:
    """``world`` with every coastal sea zone able to have a port of its own.

    A sea cell that no assignment can serve becomes one cell with a sea neighbour: preferably a
    cell that is served (nothing else changes), then another unserved one (the two share the
    shortage), then any; the longest shared border first. The world itself when nothing is
    unserved. On a shared coast, a zone that only touches retained land may reach a port by
    folding along adjoining water. An unserved zone with no such route raises ``PortError``.
    When joining regional grids, small pieces at their common edges are first folded
    over their broadest marine contact, so each starts with a full-size sea neighbour.
    With ``dissolve`` (and no ``minimum_sea``), an unserved cell that no foreign land touches and
    that two or more served cells border is divided among them first (``_absorb``).
    """
    foreign = foreign or ForeignCoast()
    lengths = pair_lengths(world)
    links, needed = coast_links(world, foreign, lengths)
    sea_links = _sea_links(world, lengths)
    merged: dict[int, int] = {}
    if dissolve and not minimum_sea:
        labels, divided = _dissolve(world, foreign, lengths)
        if divided:
            world = replace(world, labels=labels)
            merged.update(divided)
            links, needed = coast_links(world, foreign, lengths)
            sea_links = _sea_links(world, lengths)
    if minimum_sea:
        sizes = world.pixels.tolist()
        small = sorted(
            (sea for sea in sea_links if sizes[sea] < minimum_sea), key=sizes.__getitem__
        )
        for sea in small:
            neighbours = sea_links[sea]
            if sizes[sea] >= minimum_sea or not neighbours:
                continue
            target = min(neighbours, key=lambda other: (-neighbours[other], -sizes[other], other))
            _merge(sea, target, sea_links, links, needed)
            merged[sea] = target
            sizes[target] += sizes[sea]
    while True:
        checkpoint()
        unserved = plan_ports(links, needed).unserved
        if not unserved:
            break
        sea = unserved[0]
        target = _merge_target(
            sea, sea_links, needed, set(unserved), links, shared_coast=shared_coast
        )
        _merge(sea, target, sea_links, links, needed)
        merged[sea] = target
    if not merged:
        return Settled(world, foreign, tuple(range(len(world.classes))), 0)
    settled, cell_of = relabel(world, merged)
    return Settled(settled, foreign.renumbered(cell_of), cell_of, len(merged))


def _sea_links(
    world: NewWorld, lengths: Mapping[tuple[int, int], int]
) -> dict[int, dict[int, int]]:
    """How long every two touching sea cells share a border, for each of them."""
    sea_links: dict[int, dict[int, int]] = {}
    for (first, second), length in lengths.items():
        if world.classes[first] is CellClass.SEA and world.classes[second] is CellClass.SEA:
            sea_links.setdefault(first, {})[second] = length
            sea_links.setdefault(second, {})[first] = length
    return sea_links


def _dissolve(
    world: NewWorld, foreign: ForeignCoast, lengths: dict[tuple[int, int], int]
) -> tuple[NDArray[np.int32], dict[int, int]]:
    """The labels of ``world`` with every unserved cell that its served neighbours can take given
    to them, and for each such cell the neighbour that took most of it.

    A cell is taken when no land of the game's own map touches it (the foreign coast names it by
    its number) and at least two served cells border it. ``lengths`` (the borders of the cells) is
    kept in step with the labels; what is served is worked out again after each cell, since it
    depends on the cells that are left.
    """
    abroad = set(foreign.held).union(*foreign.free.values())
    labels = world.labels
    copied = False
    taken: dict[int, int] = {}
    while True:
        checkpoint()
        links, needed = coast_links(world, foreign, lengths)
        sea_links = _sea_links(world, lengths)
        unserved = plan_ports(links, needed).unserved
        gone = set(unserved)
        for sea in unserved:
            takers = sorted(
                other
                for other in sea_links.get(sea, {})
                if other in needed and other not in gone and other not in abroad
            )
            if sea in abroad or len(takers) < MIN_TAKERS:
                continue
            if not copied:
                labels, copied = labels.copy(), True
            main = _absorb(labels, sea, takers, lengths, wrap_x=world.wrap_x)
            if main is not None:
                taken[sea] = main
                break
        else:
            return labels, taken


def _absorb(
    labels: NDArray[np.int32],
    sea: int,
    takers: Sequence[int],
    lengths: dict[tuple[int, int], int],
    *,
    wrap_x: bool,
) -> int | None:
    """Give the pixels of cell ``sea`` to ``takers`` in ``labels``, each to the taker whose border
    with the cell is nearer by a way through the cell, and update the ``lengths`` of the borders.

    Returns the taker that got most, or None, with nothing changed, where the cell reaches the
    edge of a wrapping raster or a pixel of it is cut off from every taker.
    """
    rows, columns = np.nonzero(labels == sea)
    top, bottom = max(0, int(rows.min()) - 1), min(labels.shape[0], int(rows.max()) + 2)
    left, right = max(0, int(columns.min()) - 1), min(labels.shape[1], int(columns.max()) + 2)
    if wrap_x and (left == 0 or right == labels.shape[1]):
        return None
    window = labels[top:bottom, left:right]
    inside = window == sea
    sites: list[tuple[int, int]] = []
    owner: list[int] = []
    for taker in takers:
        theirs = window == taker
        near = np.zeros_like(inside)
        near[1:] |= theirs[:-1]
        near[:-1] |= theirs[1:]
        near[:, 1:] |= theirs[:, :-1]
        near[:, :-1] |= theirs[:, 1:]
        for row, column in zip(*np.nonzero(inside & near), strict=True):
            sites.append((int(row), int(column)))
            owner.append(taker)
    if not sites:
        return None
    found, _ = _native.sea_geodesic(
        np.ascontiguousarray(inside),
        np.zeros(inside.shape, dtype=np.int32),
        np.asarray(sites, dtype=np.int64),
        np.zeros(len(sites), dtype=np.uint32),
    )
    if (found[inside] < 0).any():
        return None
    trial = window.copy()
    trial[inside] = np.asarray(owner, dtype=np.int32)[found[inside]]
    if not _joined(trial, window, takers):
        return None
    before = _pair_counts(window)
    after = _pair_counts(trial)
    given = trial[inside]
    window[inside] = given
    for pair in before.keys() | after.keys():
        total = lengths.get(pair, 0) + after.get(pair, 0) - before.get(pair, 0)
        if total:
            lengths[pair] = total
        else:
            _ = lengths.pop(pair, None)
    shares = np.bincount(given, minlength=int(given.max()) + 1)
    return int(np.argmax(shares))


def _joined(trial: NDArray[np.int32], window: NDArray[np.int32], takers: Sequence[int]) -> bool:
    """Whether every taker of ``trial`` is still one piece of what it was in ``window``.

    A pixel given to a taker can touch it by a corner only, where three cells meet; such a piece
    (one no old pixel of the taker is joined to) is given to the taker it touches along most
    sides. False, with ``trial`` left as it is, where a piece touches no taker along a side.
    """
    for _ in range(len(takers) + 1):
        parts = label_components(trial)
        changed = False
        for taker in takers:
            mine = trial == taker
            old = np.unique(parts[window == taker])
            lost = mine & ~np.isin(parts, old)
            if not lost.any():
                continue
            votes: dict[int, int] = {}
            for here, there in (
                ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
                ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
                ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
                ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
            ):
                touching = lost[here] & ~mine[there]
                for other in np.unique(trial[there][touching]).tolist():
                    if other in takers:
                        votes[other] = votes.get(other, 0) + int(
                            (trial[there][touching] == other).sum()
                        )
            if not votes:
                return False
            trial[lost] = max(votes, key=lambda other: (votes[other], -other))
            changed = True
        if not changed:
            return True
    return False


def _pair_counts(labels: NDArray[np.int32]) -> dict[tuple[int, int], int]:
    """How many pixel contacts every two labels of ``labels`` share (not counting the outside)."""
    pairs, counts = adjacency_lengths(labels)
    return {
        pair: length
        for pair, length in zip(unpack_pairs(pairs), counts.tolist(), strict=True)
        if pair[0] >= 0 and pair[1] >= 0
    }


def _merge_target(  # noqa: PLR0913 - the merge uses every side of the coast graph.
    sea: int,
    sea_links: Mapping[int, Mapping[int, int]],
    needed: Collection[int],
    unserved: Collection[int],
    links: Mapping[int, Mapping[int, int]],
    *,
    shared_coast: bool,
) -> int:
    """The sea neighbour to fold ``sea`` into: a served one, an unserved one, any; longest first."""
    if not any(sea in seas for seas in links.values()):
        if shared_coast:
            port_seas = {cell for seas in links.values() for cell in seas}
            first = _water_step_to_port(sea, sea_links, port_seas)
            if first is not None:
                return first
        message = (
            f"Sea cell {sea} touches vanilla land with a port of its own and no land of its own"
        )
        raise PortError(message)
    neighbours = sea_links.get(sea, {})
    if not neighbours:
        message = f"Sea cell {sea} needs a port and touches no other water to share one with"
        raise PortError(message)

    def rank(other: int) -> tuple[int, int, int]:
        group = 0 if other in needed and other not in unserved else 1 if other in unserved else 2
        return group, -neighbours[other], other

    return min(neighbours, key=rank)


def _water_step_to_port(
    sea: int, sea_links: Mapping[int, Mapping[int, int]], port_seas: Collection[int]
) -> int | None:
    """Find the first step on the shortest water path, preferring a wider first border."""
    neighbours = sea_links.get(sea, {})
    first_steps = sorted(neighbours, key=lambda other: (-neighbours[other], other))
    seen = {sea, *first_steps}
    queue = deque((other, other) for other in first_steps)
    while queue:
        cell, first = queue.popleft()
        if cell in port_seas:
            return first
        for other in sea_links[cell]:
            if other not in seen:
                seen.add(other)
                queue.append((other, first))
    return None


def _merge(
    sea: int,
    target: int,
    sea_links: dict[int, dict[int, int]],
    links: dict[int, dict[int, int]],
    needed: set[int],
) -> None:
    """Fold ``sea`` into ``target`` in the link tables."""
    for other, length in sea_links.pop(sea, {}).items():
        _ = sea_links[other].pop(sea, None)
        if other != target:
            sea_links[other][target] = sea_links[other].get(target, 0) + length
            sea_links[target][other] = sea_links[target].get(other, 0) + length
    for seas in links.values():
        if sea in seas:
            seas[target] = seas.get(target, 0) + seas.pop(sea)
    if sea in needed:
        needed.discard(sea)
        needed.add(target)


def relabel(world: NewWorld, merged: Mapping[int, int]) -> tuple[NewWorld, tuple[int, ...]]:
    """The world with each merged cell relabelled to what it was folded into, cells renumbered.

    ``merged`` maps a cell to the one it becomes part of; a chain of such steps is followed to
    its end. The second value gives the new number of every old cell.
    """
    count = len(world.classes)
    final = list(range(count))
    for sea in sorted(merged):
        final[sea] = merged[sea]
    for sea in range(count):
        while final[final[sea]] != final[sea]:
            final[sea] = final[final[sea]]
    kept = [cell for cell in range(count) if final[cell] == cell]
    number = {cell: index for index, cell in enumerate(kept)}
    cell_of = tuple(number[final[cell]] for cell in range(count))
    table = np.array([*cell_of, -1], dtype=np.int32)
    labels = np.empty_like(world.labels)
    for start in range(0, world.labels.shape[0], STRIP_ROWS):
        checkpoint()
        stop = start + STRIP_ROWS
        labels[start:stop] = table[world.labels[start:stop]]
    kinds = tuple(world.classes[cell] for cell in kept)
    moved: list[int] = [cell_of[int(cell)] for cell in world.barrier]
    barrier = np.unique(np.array(moved, dtype=np.int64))
    return (
        replace(
            derive_world(labels, kinds, world.elevation, wrap_x=world.wrap_x),
            barrier=barrier,
            drainage=world.drainage,
            planned=None if world.planned is None else world.planned[kept],
        ),
        cell_of,
    )
