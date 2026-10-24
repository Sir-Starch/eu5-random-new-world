"""The shapes of generated water: capes and bays, straits, enclosed seas and the depth zones.

Game-independent. A generated sea is one blob of sea cells with nothing to tell a gulf from the
ocean, while the game's own seas are told apart by their shape: the Mediterranean is one sea of
250 zones, a strait is a handful of narrow ones, the zones along a coast are bays and capes, and
the topography of a sea zone follows how far from land and how enclosed it is [V-LOCAL 1.4.3,
C234]. This module reads the shape of the water from the generated cells with measures that do
not depend on how big a cell is (its unit is the width of a typical sea cell, the *scale*):

* **Narrow water** is water that no disk of one scale of radius fits through: what a closing of
  the land at that radius fills. A narrow stretch that joins two wider waters is a strait (one
  or two cells) or a channel (more), a narrow stretch that ends is an inlet.
* **Enclosed water** is the same at three scales: a gulf or an inland sea that the land closes at
  its mouth. A connected group of enclosed cells is one body of water.
* **A coastal cell** touches land. It is a cape where little land lies round its deepest point,
  a bay where much does, the water of an island where it touches only small islands, and a plain
  coast otherwise.
* **Depth** is how many cells a sea cell is from land; ``topography`` maps it to the game's own
  types.

Nothing here draws a random number: names come from ``seanames``, currents from ``currents``.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, box_blur
from rnw.model import CellClass
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from numpy.typing import NDArray

    from rnw.newworld import NewWorld

# A coarse raster of at most this step is enough: a scale is about a dozen of its pixels.
MAX_STEP: Final[int] = 8
MIN_STEP: Final[int] = 2
STEP_SCALES: Final[int] = 12
# Radii of the closings, in scales, and the share of a cell's pixels that makes it narrow or
# enclosed (half). 1 and 3 are the smallest radii whose result reads as straits and as gulfs on
# the reference worlds (C235).
NARROW_SCALES: Final[int] = 1
ENCLOSED_SCALES: Final[int] = 3
# How far round its deepest point a coastal cell looks for land, in scales, and the land share
# (permille of the square) below which it is a cape and above which a bay.
LOOK_SCALES: Final[int] = 2
CAPE_PERMILLE: Final[int] = 120
BAY_PERMILLE: Final[int] = 380
# A landmass of at most this many cells is an island: water that touches only islands is theirs.
ISLAND_CELLS: Final[int] = 6
# Groups of enclosed cells smaller than this are no body of water of their own.
MIN_BODY_CELLS: Final[int] = 2
# A passage of at most this many cells is a strait, a longer one a channel.
STRAIT_CELLS: Final[int] = 2
TWO_WATERS: Final[int] = 2
# Cells that reach each other within this many steps through wider water are one water.
MOUTH_HOPS: Final[int] = 4
# Sea cells at least this many cells from land are deep ocean; water that no land touches at all
# (a piece of ocean beside the generated land) is as far from it as can be.
DEEP_HOPS: Final[int] = 2
FAR_HOPS: Final[int] = 1 << 16


class Shape(IntEnum):
    """What a sea cell is at its place in the water."""

    OPEN = 0
    COAST = 1
    CAPE = 2
    BAY = 3
    ISLE = 4
    NARROW = 5


class PassageKind(StrEnum):
    """A narrow stretch of water: joins two wider waters, or ends."""

    STRAIT = "strait"
    CHANNEL = "channel"
    INLET = "inlet"


class Topography(StrEnum):
    """The game's types of water (``common/topography``) that a generated sea cell takes.

    ``analyse`` gives every cell of the open ocean ``DEEP_OCEAN``; which of them are lanes and which
    are shut, ``OCEAN_WASTELAND``, is for ``rnw.lanes`` to say.
    """

    COASTAL_OCEAN = "coastal_ocean"
    OCEAN = "ocean"
    DEEP_OCEAN = "deep_ocean"
    INLAND_SEA = "inland_sea"
    NARROWS = "narrows"
    OCEAN_WASTELAND = "ocean_wasteland"


@dataclass(frozen=True, slots=True)
class Passage:
    """A connected stretch of narrow water."""

    cells: tuple[int, ...]
    kind: PassageKind


@dataclass(frozen=True, slots=True, eq=False)
class Waters:
    """The shape of every sea cell of a world, indexed by cell number (-1 for land and lakes)."""

    scale: int
    hop: NDArray[np.int32]
    shape: NDArray[np.int8]
    enclosed: NDArray[np.bool_]
    body: NDArray[np.int32]
    bodies: tuple[tuple[int, ...], ...]
    passage: NDArray[np.int32]
    passages: tuple[Passage, ...]
    landmass: NDArray[np.int32]
    landmass_cells: tuple[int, ...]
    topography: tuple[Topography | None, ...]

    def sea(self) -> list[int]:
        """The sea cells in order."""
        return [int(cell) for cell in np.flatnonzero(self.hop >= 0)]


def _step(scale: int) -> int:
    return max(MIN_STEP, min(MAX_STEP, scale // STEP_SCALES))


def _closing(land: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Land with every gap narrower than two radii filled: dilated by the radius, then eroded."""
    pad = radius + 2
    padded = np.pad(land, pad)
    limit = 8 * pad
    near = euclidean_distance(padded, limit) <= 8 * radius
    far = euclidean_distance(~near, limit) > 8 * radius
    return far[pad:-pad, pad:-pad]


def _components(flags: NDArray[np.bool_], links: Sequence[Sequence[int]]) -> list[list[int]]:
    """Connected groups of flagged cells in order of their lowest cell, each sorted."""
    seen = np.zeros(len(flags), dtype=bool)
    groups: list[list[int]] = []
    for start in np.flatnonzero(flags).tolist():
        if seen[start]:
            continue
        seen[start] = True
        group, stack = [start], [start]
        while stack:
            for other in links[stack.pop()]:
                if flags[other] and not seen[other]:
                    seen[other] = True
                    group.append(other)
                    stack.append(other)
        groups.append(sorted(group))
    return groups


def _landmasses(world: NewWorld, land: NDArray[np.bool_]) -> tuple[NDArray[np.int32], list[int]]:
    """Number the connected groups of land, wasteland and lake cells; their sizes in cells."""
    links: list[list[int]] = [[] for _ in world.classes]
    for first, second in world.edges:
        if land[first] and land[second]:
            links[first].append(second)
            links[second].append(first)
    groups = _components(land, links)
    number = np.full(len(world.classes), -1, dtype=np.int32)
    for index, group in enumerate(groups):
        number[group] = index
    return number, [len(group) for group in groups]


def _hops(links: Sequence[Sequence[int]], start: Sequence[int], count: int) -> NDArray[np.int32]:
    """Cell steps through water from the cells in ``start`` (0 there), -1 where unreached."""
    hop = np.full(count, -1, dtype=np.int32)
    queue = deque(sorted(start))
    for cell in queue:
        hop[cell] = 0
    while queue:
        cell = queue.popleft()
        for other in links[cell]:
            if hop[other] < 0:
                hop[other] = hop[cell] + 1
                queue.append(other)
    return hop


def _shares(
    lab: NDArray[np.int32], mask: NDArray[np.bool_], water: NDArray[np.bool_], count: int
) -> NDArray[np.bool_]:
    """Cells of which at least half the water pixels of the coarse raster are in ``mask``."""
    inside = lab >= 0
    num = np.bincount(lab[mask & inside], minlength=count + 1)[:count]
    den = np.bincount(lab[water & inside], minlength=count + 1)[:count]
    return 2 * num >= np.maximum(den, 1)


def _poles(lab: NDArray[np.int32], depth: NDArray[np.int64], count: int) -> NDArray[np.int64]:
    """Per cell, the flat coarse index of its deepest pixel (the first on a tie), -1 if none."""
    flat = lab.ravel()
    order = np.lexsort((np.arange(flat.size), depth.ravel(), flat))
    ends = np.flatnonzero(np.diff(flat[order], append=-2) != 0)
    poles = np.full(count, -1, dtype=np.int64)
    for end in ends.tolist():
        cell = int(flat[order[end]])
        if cell >= 0:
            poles[cell] = order[end]
    return poles


def _neighbours(world: NewWorld) -> list[list[int]]:
    links: list[list[int]] = [[] for _ in world.classes]
    for first, second in world.edges:
        links[first].append(second)
        links[second].append(first)
    return [sorted(item) for item in links]


def _mouths(group: Sequence[int], narrow: NDArray[np.bool_], links: Sequence[Sequence[int]]) -> int:
    """How many separate waters the wider water beside a narrow stretch is.

    Wider cells beside the stretch are one water when they reach each other through wider cells
    within ``MOUTH_HOPS`` steps: the two ends of a strait do not, the sides of an inlet do.
    """
    inside = set(group)
    beside = sorted({o for cell in group for o in links[cell] if o not in inside and not narrow[o]})
    parent = {cell: cell for cell in beside}

    def find(cell: int) -> int:
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    for start in beside:
        reach = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            if reach[cell] == MOUTH_HOPS:
                continue
            for other in links[cell]:
                if other not in reach and not narrow[other] and other not in inside:
                    reach[other] = reach[cell] + 1
                    queue.append(other)
        for other in reach:
            if other in parent:
                parent[find(other)] = find(start)
    return len({find(cell) for cell in beside})


def _passages(
    narrow: NDArray[np.bool_], links: Sequence[Sequence[int]]
) -> tuple[NDArray[np.int32], tuple[Passage, ...]]:
    """The connected narrow stretches: a strait or channel joins two waters, an inlet ends."""
    number = np.full(len(narrow), -1, dtype=np.int32)
    passages: list[Passage] = []
    for index, group in enumerate(_components(narrow, links)):
        waters = _mouths(group, narrow, links)
        if waters >= TWO_WATERS:
            kind = PassageKind.STRAIT if len(group) <= STRAIT_CELLS else PassageKind.CHANNEL
        else:
            kind = PassageKind.INLET if waters else PassageKind.CHANNEL
        number[group] = index
        passages.append(Passage(tuple(group), kind))
    return number, tuple(passages)


def _pockets(
    open_sea: NDArray[np.bool_], exterior: NDArray[np.bool_], links: Sequence[Sequence[int]]
) -> NDArray[np.bool_]:
    """Water that is neither narrow nor enclosed by a closing but has no way to the outside.

    A hole of the sea inside an archipelago is wider than the closing's radius and is as much a
    sea of its own as the water round it.
    """
    pockets = np.zeros(len(open_sea), dtype=bool)
    for group in _components(open_sea, links):
        if not exterior[group].any():
            pockets[group] = True
    return pockets


def _exterior(lab: NDArray[np.int32], count: int) -> NDArray[np.bool_]:
    """Cells that touch the world outside the generated domain: the game's own water, or the
    edge of the domain's picture, beyond which the map goes on."""
    outside = np.pad(lab < 0, 1, constant_values=True)
    near = np.zeros_like(outside)
    near[1:] |= outside[:-1]
    near[:-1] |= outside[1:]
    near[:, 1:] |= outside[:, :-1]
    near[:, :-1] |= outside[:, 1:]
    touching = np.unique(lab[near[1:-1, 1:-1] & (lab >= 0)])
    flags = np.zeros(count, dtype=bool)
    flags[touching] = True
    return flags


def analyse(world: NewWorld, shore: Collection[int] = ()) -> Waters:
    """The shape of the water of ``world``.

    ``shore`` are sea cells that touch land the world does not hold: the game's own land at the
    edge of the canvas. They are as much on a coast as a cell that touches the world's land.
    """
    count = len(world.classes)
    sea = np.array([kind is CellClass.SEA for kind in world.classes], dtype=bool)
    solid = np.array(
        [kind in {CellClass.LAND, CellClass.WASTELAND, CellClass.LAKE} for kind in world.classes],
        dtype=bool,
    )
    neighbours = _neighbours(world)
    sea_links = [
        [other for other in neighbours[cell] if sea[other]] if sea[cell] else []
        for cell in range(count)
    ]
    scale = max(MIN_STEP * STEP_SCALES, math.isqrt(int(np.median(world.pixels[sea]))))
    step = _step(scale)
    lab = np.ascontiguousarray(world.labels[step // 2 :: step, step // 2 :: step])
    land_pixels = np.append(solid, False)[lab]
    water = ~land_pixels
    narrow_at = _closing(land_pixels, round(NARROW_SCALES * scale / step)) & water
    enclosed_at = _closing(land_pixels, round(ENCLOSED_SCALES * scale / step)) & water
    narrow = sea & _shares(lab, narrow_at, water, count)
    enclosed = sea & _shares(lab, enclosed_at, water, count) & ~narrow
    enclosed |= _pockets(sea & ~narrow & ~enclosed, _exterior(lab, count), sea_links)
    foreign = set(shore)
    coast = [
        cell
        for cell in range(count)
        if sea[cell] and (cell in foreign or any(not sea[o] for o in neighbours[cell]))
    ]
    hop = _hops(sea_links, coast, count)
    hop[sea & (hop < 0)] = FAR_HOPS
    landmass, landmass_cells = _landmasses(world, solid)
    passage, passages = _passages(narrow, sea_links)
    bodies = tuple(
        tuple(group)
        for group in sorted(
            _components(enclosed, sea_links), key=lambda group: (-len(group), group)
        )
        if len(group) >= MIN_BODY_CELLS
    )
    body = np.full(count, -1, dtype=np.int32)
    for index, group in enumerate(bodies):
        body[list(group)] = index
    shape = _shapes(
        world, lab, land_pixels, scale, step, coast, neighbours, landmass, landmass_cells
    )
    shape[narrow] = Shape.NARROW
    return Waters(
        scale=scale,
        hop=hop,
        shape=shape,
        enclosed=body >= 0,
        body=body,
        bodies=bodies,
        passage=passage,
        passages=passages,
        landmass=landmass,
        landmass_cells=tuple(landmass_cells),
        topography=_topography(hop, shape, body),
    )


def _shapes(  # noqa: PLR0913, PLR0917 - the shape of a coast reads the raster and the landmasses.
    world: NewWorld,
    lab: NDArray[np.int32],
    land_pixels: NDArray[np.bool_],
    scale: int,
    step: int,
    coast: Sequence[int],
    neighbours: Sequence[Sequence[int]],
    landmass: NDArray[np.int32],
    landmass_cells: Sequence[int],
) -> NDArray[np.int8]:
    """Cape, bay, island water or plain coast for every coastal cell; open elsewhere."""
    count = len(world.classes)
    shape = np.full(count, Shape.OPEN, dtype=np.int8)
    look = max(1, round(LOOK_SCALES * scale / step))
    land_share = box_blur(land_pixels.astype(np.int64) * PERMILLE, look).ravel()
    depth = euclidean_distance(land_pixels, 8 * 4096)
    poles = _poles(lab, depth, count)
    for cell in coast:
        masses = {int(landmass[other]) for other in neighbours[cell] if landmass[other] >= 0}
        if masses and all(landmass_cells[mass] <= ISLAND_CELLS for mass in masses):
            shape[cell] = Shape.ISLE
            continue
        share = int(land_share[poles[cell]]) if poles[cell] >= 0 else PERMILLE // 4
        if share <= CAPE_PERMILLE:
            shape[cell] = Shape.CAPE
        elif share >= BAY_PERMILLE:
            shape[cell] = Shape.BAY
        else:
            shape[cell] = Shape.COAST
    return shape


def _topography(
    hop: NDArray[np.int32], shape: NDArray[np.int8], body: NDArray[np.int32]
) -> tuple[Topography | None, ...]:
    """The game's type of each sea cell: narrows, inland sea, then by depth from land."""
    types: list[Topography | None] = []
    for cell in range(len(hop)):
        if hop[cell] < 0:
            types.append(None)
        elif shape[cell] == Shape.NARROW:
            types.append(Topography.NARROWS)
        elif body[cell] >= 0:
            types.append(Topography.INLAND_SEA)
        elif hop[cell] == 0:
            types.append(Topography.COASTAL_OCEAN)
        elif hop[cell] < DEEP_HOPS:
            types.append(Topography.OCEAN)
        else:
            types.append(Topography.DEEP_OCEAN)
    return tuple(types)
