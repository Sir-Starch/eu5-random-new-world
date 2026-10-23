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
else), so the world the rest of the generator sees has a port for every coastal zone.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from rnw.model import CellClass
from rnw.newworld import STRIP_ROWS, derive_world
from rnw.progress import checkpoint
from rnw.topology import adjacency_lengths, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from rnw.newworld import NewWorld


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
    pairs, counts = adjacency_lengths(world.labels)
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


def settle_seas(world: NewWorld, foreign: ForeignCoast | None = None) -> Settled:
    """``world`` with every coastal sea zone able to have a port of its own.

    A sea cell that no assignment can serve becomes one cell with a sea neighbour: preferably a
    cell that is served (nothing else changes), then another unserved one (the two share the
    shortage), then any; the longest shared border first. The world itself when nothing is
    unserved. Raises ``PortError`` for a cell that stays unserved, which means vanilla land with
    a port of its own touches generated water that has no land of its own.
    """
    foreign = foreign or ForeignCoast()
    lengths = pair_lengths(world)
    links, needed = coast_links(world, foreign, lengths)
    sea_links: dict[int, dict[int, int]] = {}
    for (first, second), length in lengths.items():
        if world.classes[first] is CellClass.SEA and world.classes[second] is CellClass.SEA:
            sea_links.setdefault(first, {})[second] = length
            sea_links.setdefault(second, {})[first] = length
    merged: dict[int, int] = {}
    while True:
        checkpoint()
        unserved = plan_ports(links, needed).unserved
        if not unserved:
            break
        sea = unserved[0]
        target = _merge_target(sea, sea_links, needed, set(unserved), links)
        _merge(sea, target, sea_links, links, needed)
        merged[sea] = target
    if not merged:
        return Settled(world, foreign, tuple(range(len(world.classes))), 0)
    settled, cell_of = _relabel(world, merged)
    return Settled(settled, foreign.renumbered(cell_of), cell_of, len(merged))


def _merge_target(
    sea: int,
    sea_links: Mapping[int, Mapping[int, int]],
    needed: Collection[int],
    unserved: Collection[int],
    links: Mapping[int, Mapping[int, int]],
) -> int:
    """The sea neighbour to fold ``sea`` into: a served one, an unserved one, any; longest first."""
    if not any(sea in seas for seas in links.values()):
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


def _relabel(world: NewWorld, merged: Mapping[int, int]) -> tuple[NewWorld, tuple[int, ...]]:
    """The world with each merged cell relabelled to what it was folded into, cells renumbered."""
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
    return derive_world(labels, kinds, world.elevation), cell_of
