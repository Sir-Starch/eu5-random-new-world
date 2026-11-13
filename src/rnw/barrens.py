"""Natural impassable terrain: which locations are wasteland, and of what kind (epoch 64).

Until epoch 63 the wastelands were the highest cells of the relief, so every one was a mountain.
The game's own map has no such rule: of 22,700 land locations 1,800 are impassable, and by
area less than a quarter of them are mountains. The rest is a flat jungle or tundra heart,
a sea of dunes, a plateau of stone, a forested or jungle highland. This module decides which
cells are wasteland once the climate and the vegetation of every cell are known, from three
things the installed game provides (the construction is described in ``docs/terrain-biomes.md``):

* **How much of what, where.** The area that vanilla wastelands of each kind (mountain, hills,
  plateau, flat, dune) cover in each patch of one climate group and one vegetation, as a share
  of that patch's land (``calibrate``). The world's own patches are weighed with those rates and
  the world's wasteland budget is divided between the (climate, vegetation, kind) classes in
  that proportion, bounded by what each class can hold (``_allocate``).
* **How big a unit is.** Vanilla wastelands are mostly single locations with a heavy tail of
  huge ones. A class draws its units' sizes from the vanilla sizes, in generated cells, and
  grows each unit from a seed over cells of one climate and vegetation, so that touching cells
  of one unit carry identical attributes and merge into one location (``wastelands``).
* **Where it fits.** A cell can only be a kind that its own ground allows (a mountain wasteland
  stands on high ground, a flat one on low smooth ground), and inside that the seeds and the
  growth prefer what the kind is: dry, remote, flat ground for dunes, wet remote lowland for
  jungle, cold remote ground for tundra, the highest and roughest ground for mountains.

Nothing is repaired afterwards. A wasteland is only added where every passable cell that
remains still reaches the coast, and only on cells that touch no sea, because the ports,
the docks and the strait crossings of the coast stage were made for the cells beside the sea as
they were. A cell whose templates would match no biome of ``biomes.txt`` is no candidate.
"""

# pyright: reportAny=false
from __future__ import annotations

import bisect
import heapq
import itertools
from collections import defaultdict, deque
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Final, final

import numpy as np

from rnw.model import CellClass
from rnw.rng import derive_seed, hash_point

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from numpy.typing import NDArray

# Mean height (relief units) from which a wasteland is a mountain, and the spread (standard
# deviation of the relief) under which ground is smooth; the epoch 63 rule for the topography
# of a wasteland, kept for the cells the planner does not choose.
MOUNTAIN_FLOOR: Final[int] = 14_000
FLAT_SPREAD: Final[int] = 900
PLATEAU_FLOOR: Final[int] = 11_000
# Most particular kinds first: the dunes take the flattest dry cells before the flat ground does.
KINDS: Final[tuple[str, ...]] = ("dune", "plateau", "flat", "hills", "mountain")
TOPOGRAPHY: Final[dict[str, str]] = {
    "dune": "dune_wasteland",
    "plateau": "plateau_wasteland",
    "flat": "flatland_wasteland",
    "hills": "hills_wasteland",
    "mountain": "mountain_wasteland",
}
# The vanilla topography of a wasteland location, by kind. A mesa is a plateau of rock; the
# marshes, salt pans and atolls are too few for a kind of their own.
VANILLA_KINDS: Final[dict[str, str]] = {
    "dune_wasteland": "dune",
    "plateau_wasteland": "plateau",
    "mesa_wasteland": "plateau",
    "flatland_wasteland": "flat",
    "hills_wasteland": "hills",
    "mountain_wasteland": "mountain",
}
LAND_KINDS: Final[frozenset[CellClass]] = frozenset({CellClass.LAND, CellClass.WASTELAND})
COLD: Final[frozenset[str]] = frozenset({"arctic", "subpolar"})
PPM: Final[int] = 1_000_000
PERMILLE: Final[int] = 1000
# Smaller patches of the game's map give no rate (a few dozen locations: noise, not a share).
MIN_PATCH_PX: Final[int] = 150_000
# A class never takes more than this share of the cells that could carry it.
CAPACITY_PERMILLE: Final[int] = 800
ROUNDS: Final[int] = 4
SMOOTHING: Final[int] = 4
NOISE_WEIGHT: Final[int] = 3

Patch = tuple[str, str]
Triple = tuple[str, str, str]
Class = tuple[str, str, str]


class WastelandPlanError(ValueError):
    """The wastelands of a plan would break an invariant of the world."""


def legacy_topography(height: int, spread: int) -> str:
    """The topography of a wasteland that the epoch 63 rule gave: by height, then smoothness."""
    if height >= MOUNTAIN_FLOOR:
        return TOPOGRAPHY["mountain"]
    return TOPOGRAPHY["plateau"] if spread < FLAT_SPREAD else TOPOGRAPHY["hills"]


def ground_of(height: int, spread: int) -> str:
    """The kind of wasteland the relief of a cell allows."""
    if height >= MOUNTAIN_FLOOR:
        return "mountain"
    if spread >= FLAT_SPREAD:
        return "hills"
    return "plateau" if height >= PLATEAU_FLOOR else "flat"


@dataclass(frozen=True, slots=True, eq=False)
class Calibration:
    """What the game's wastelands are like, read from its files.

    ``rates`` is, for a patch (a climate group and a vegetation) and a kind, the part per
    million of the patch's land area that wastelands of the kind cover. ``sizes`` is the sorted
    size in pixels of every vanilla wasteland location of a kind.
    """

    rates: Mapping[Class, int]
    sizes: Mapping[str, tuple[int, ...]]


def calibrate(  # noqa: PLR0913 - the calibration reads every attribute of a vanilla location.
    *,
    classes: Sequence[CellClass],
    climate: Sequence[str],
    vegetation: Sequence[str],
    topography: Sequence[str],
    pixels: NDArray[np.int64],
    include: NDArray[np.bool_],
    groups: Mapping[str, str],
) -> Calibration:
    """Rates and sizes of the vanilla wastelands among the ``include`` locations."""
    area: dict[Patch, int] = defaultdict(int)
    covered: dict[Class, int] = defaultdict(int)
    sizes: dict[str, list[int]] = defaultdict(list)
    for index, kind in enumerate(classes):
        size = int(pixels[index])
        if (
            size <= 0
            or not include[index]
            or kind not in LAND_KINDS
            or not climate[index]
            or not vegetation[index]
            or topography[index] == "atoll"
        ):
            continue
        patch = (groups.get(climate[index], climate[index]), vegetation[index])
        area[patch] += size
        name = VANILLA_KINDS.get(topography[index])
        if kind is CellClass.WASTELAND and name is not None:
            covered[(*patch, name)] += size
            sizes[name].append(size)
    rates = {
        key: share * PPM // area[(key[0], key[1])]
        for key, share in covered.items()
        if area[(key[0], key[1])] >= MIN_PATCH_PX
    }
    return Calibration(rates, {name: tuple(sorted(found)) for name, found in sizes.items()})


@dataclass(frozen=True, slots=True, eq=False)
class Terrain:
    """The land cells of a generated world as the planner reads them.

    Arrays and tuples are indexed by cell. ``edges`` joins land cells that touch. ``coastal`` is
    a cell that touches the sea, ``polar`` one that touches a polar edge of the map.
    """

    kinds: tuple[CellClass, ...]
    climate: tuple[str, ...]
    vegetation: tuple[str, ...]
    height: NDArray[np.int64]
    spread: NDArray[np.int64]
    pixels: NDArray[np.int64]
    rain: NDArray[np.int64]
    coast: NDArray[np.int64]
    latitude: NDArray[np.int64]
    coastal: NDArray[np.bool_]
    polar: NDArray[np.bool_]
    edges: NDArray[np.int64]


@dataclass(frozen=True, slots=True, eq=False)
class WastelandSettings:
    """What the planner is asked: how many cells, and what the game can draw."""

    budget: int
    polar: NDArray[np.bool_]
    groups: Mapping[str, str]
    biome_ok: Callable[[str, str, str], bool]


@dataclass(frozen=True, slots=True)
class WastelandPlan:
    """The class of every cell after planning, the topography of every wasteland, statistics."""

    kinds: tuple[CellClass, ...]
    topography: dict[int, str]
    stats: dict[str, object]


def _allocate(
    weights: Mapping[Class, int],
    capacity: Mapping[Class, int],
    total: int,
    offset: Fraction,
) -> dict[Class, int]:
    """Divide ``total`` between classes by ``weights``, none above its ``capacity``.

    A class that its capacity bounds keeps the capacity and the rest is divided again between the
    others (exact fractions). The shares are then rounded by systematic sampling from
    ``offset``, so the sum is the total and no share is more than a unit from its fraction.
    """
    share: dict[Class, Fraction] = {}
    active = {key for key, weight in weights.items() if weight > 0 and capacity.get(key, 0) > 0}
    left = Fraction(total)
    while active:
        scale = left / sum(weights[key] for key in active)
        capped = {key for key in active if weights[key] * scale >= capacity[key]}
        if not capped:
            share.update({key: weights[key] * scale for key in active})
            break
        for key in capped:
            share[key] = Fraction(capacity[key])
            left -= capacity[key]
        active -= capped
    out: dict[Class, int] = {}
    cumulative = offset
    for key in sorted(share):
        before = cumulative
        cumulative += share[key]
        out[key] = int(cumulative // 1 - before // 1)
    return out


def _permille_ranks(values: NDArray[np.int64]) -> NDArray[np.int64]:
    """Rank of every value in permille of the count (ties by position)."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=np.int64)
    ranks[order] = np.arange(values.size, dtype=np.int64) * PERMILLE // max(1, values.size)
    return ranks


@final
class _Reach:
    """Which passable cells still reach a coast, asked before a cell becomes impassable."""

    def __init__(self, adjacency: list[list[int]], passable: bytearray, sinks: bytearray) -> None:
        self.adjacency = adjacency
        self.passable = passable
        self.sinks = sinks

    def block(self, cell: int) -> None:
        """Make ``cell`` impassable for good."""
        self.passable[cell] = 0

    def can_block(self, cell: int) -> bool:
        """Whether every passable neighbour of ``cell`` reaches a coast without it."""
        passable = self.passable
        passable[cell] = 0
        try:
            good: set[int] = set()
            return all(
                neighbour in good or self._escapes(neighbour, good)
                for neighbour in self.adjacency[cell]
                if passable[neighbour]
            )
        finally:
            passable[cell] = 1

    def _escapes(self, start: int, good: set[int]) -> bool:
        """Whether a breadth-first walk from ``start`` reaches a coast or a cell known to."""
        seen = {start}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            if self.sinks[cell] or cell in good:
                good.update(seen)
                return True
            for other in self.adjacency[cell]:
                if self.passable[other] and other not in seen:
                    seen.add(other)
                    queue.append(other)
        return False

    def unreached(self) -> list[int]:
        """The passable cells that reach no coast."""
        seen = bytearray(len(self.passable))
        queue = deque(cell for cell, flag in enumerate(self.sinks) if flag and self.passable[cell])
        for cell in queue:
            seen[cell] = 1
        while queue:
            cell = queue.popleft()
            for other in self.adjacency[cell]:
                if self.passable[other] and not seen[other]:
                    seen[other] = 1
                    queue.append(other)
        return [cell for cell, flag in enumerate(self.passable) if flag and not seen[cell]]


@final
class _Planner:
    """One run of the plan: the state of the cells, the scores and the units grown so far."""

    def __init__(
        self,
        terrain: Terrain,
        calibration: Calibration,
        settings: WastelandSettings,
        seed: int,
    ) -> None:
        self.terrain = terrain
        self.calibration = calibration
        self.settings = settings
        self.key = derive_seed(seed, "natural_wastelands")
        count = len(terrain.kinds)
        self.land = [kind in LAND_KINDS for kind in terrain.kinds]
        adjacency: list[list[int]] = [[] for _ in range(count)]
        pairs: list[tuple[int, int]] = terrain.edges.tolist()
        for first, second in pairs:
            adjacency[first].append(second)
            adjacency[second].append(first)
        self.adjacency = adjacency
        self.wasteland = bytearray(count)
        self.triple: dict[int, Triple] = {}
        for cell in range(count):
            if self.land[cell] and (
                bool(terrain.polar[cell])
                or (terrain.kinds[cell] is CellClass.WASTELAND and bool(terrain.coastal[cell]))
            ):
                self._mark(cell, self._legacy(cell))
        passable = bytearray(
            int(self.land[cell] and not self.wasteland[cell]) for cell in range(count)
        )
        sinks = bytearray(
            int(bool(passable[cell]) and bool(terrain.coastal[cell])) for cell in range(count)
        )
        self.reach = _Reach(self.adjacency, passable, sinks)
        self.free = [
            cell
            for cell in range(count)
            if self.land[cell] and not terrain.coastal[cell] and not terrain.polar[cell]
        ]
        self.scores: dict[str, NDArray[np.int64]] = {}
        self.pools: dict[Class, list[int]] = {}
        self.members: dict[Class, set[int]] = {}
        self.cursor: dict[Class, int] = {}
        self.weights: dict[Class, int] = {}
        self.dead: set[int] = set()
        self.units: list[tuple[str, int]] = []
        self.mean_cell = 1

    def _legacy(self, cell: int) -> Triple:
        terrain = self.terrain
        return (
            terrain.climate[cell],
            terrain.vegetation[cell],
            legacy_topography(int(terrain.height[cell]), int(terrain.spread[cell])),
        )

    def _mark(self, cell: int, triple: Triple) -> None:
        self.wasteland[cell] = 1
        self.triple[cell] = triple

    def run(self, budget: int) -> WastelandPlan:
        """Plan the wastelands for ``budget`` cells beside the ones that cannot change."""
        terrain = self.terrain
        frozen = sum(1 for cell in self.triple if not terrain.polar[cell])
        free = set(self.free)
        forced = [cell for cell in self.reach.unreached() if cell in free]
        for cell in forced:
            self._mark(cell, self._legacy(cell))
            self.reach.block(cell)
        candidates = [cell for cell in self.free if not self.wasteland[cell]]
        wanted = max(0, budget - frozen)
        placed = 0
        if candidates and wanted:
            self.mean_cell = max(1, int(terrain.pixels[candidates].mean()))
            self._score(candidates)
            self._pool(candidates)
            placed = self._divide(wanted)
        unreached = self.reach.unreached()
        if unreached:
            message = f"The wasteland plan leaves {len(unreached)} cells without a way to a coast"
            raise WastelandPlanError(message)
        return self._result(budget, frozen, len(forced), placed)

    # -- scores --------------------------------------------------------------------------

    def _score(self, candidates: list[int]) -> None:
        """How well each cell suits each kind, in permille (0 to 1000), over the candidates."""
        terrain = self.terrain
        cells = np.array(candidates, dtype=np.int64)
        height, spread = terrain.height[cells], terrain.spread[cells]
        smooth = PERMILLE - _permille_ranks(spread)
        dry = PERMILLE - _permille_ranks(terrain.rain[cells])
        wet = _permille_ranks(terrain.rain[cells])
        remote = _permille_ranks(terrain.coast[cells])
        cold = _permille_ranks(terrain.latitude[cells])
        vegetation = np.array([terrain.vegetation[cell] for cell in candidates])
        freezing = np.array(
            [
                self.settings.groups.get(terrain.climate[c], terrain.climate[c]) in COLD
                for c in candidates
            ]
        )
        prior = np.where(
            vegetation == "desert",
            (dry + remote) // 2,
            np.where(
                vegetation == "jungle",
                (wet + remote) // 2,
                np.where(freezing, (cold + remote) // 2, remote),
            ),
        )
        physical = {
            "dune": (2 * smooth + dry + remote) // 4,
            "plateau": _permille_ranks(height - 3 * spread),
            "flat": (2 * smooth + prior) // 3,
            "hills": _permille_ranks(spread),
            "mountain": _permille_ranks(height + 2 * spread),
        }
        count = len(terrain.kinds)
        for kind, values in physical.items():
            noise = self._regional(kind, cells, count)
            full = np.zeros(count, dtype=np.int64)
            full[cells] = (
                (PERMILLE - NOISE_WEIGHT * 100) * values + NOISE_WEIGHT * 100 * noise
            ) // PERMILLE
            self.scores[kind] = full

    def _regional(self, kind: str, cells: NDArray[np.int64], count: int) -> NDArray[np.int64]:
        """A smooth noise over the candidates: districts that favour a kind more than others."""
        key = derive_seed(self.key, "region", kind)
        field = np.zeros(count, dtype=np.int64)
        field[cells] = [hash_point(key, int(cell), 0) % PERMILLE for cell in cells.tolist()]
        edges = self.terrain.edges
        inside = np.zeros(count, dtype=bool)
        inside[cells] = True
        edges = edges[inside[edges[:, 0]] & inside[edges[:, 1]]] if edges.size else edges
        degree = np.bincount(edges.ravel(), minlength=count).astype(np.int64)
        for _ in range(SMOOTHING):
            total = field * 2
            np.add.at(total, edges[:, 0], field[edges[:, 1]])
            np.add.at(total, edges[:, 1], field[edges[:, 0]])
            field = total // (2 + degree)
        return _permille_ranks(field[cells])

    # -- classes -------------------------------------------------------------------------

    def _pool(self, candidates: list[int]) -> None:
        """The cells that each (climate, vegetation, kind) class may take, best first."""
        terrain = self.terrain
        groups = self.settings.groups
        area: dict[Patch, int] = defaultdict(int)
        for cell in range(len(terrain.kinds)):
            if self.land[cell]:
                area[(terrain.climate[cell], terrain.vegetation[cell])] += int(terrain.pixels[cell])
        found: dict[Class, list[int]] = defaultdict(list)
        for cell in candidates:
            climate, vegetation = terrain.climate[cell], terrain.vegetation[cell]
            ground = ground_of(int(terrain.height[cell]), int(terrain.spread[cell]))
            for kind in KINDS:
                if kind != ground and not (kind == "dune" and ground == "flat"):
                    continue
                rate = self.calibration.rates.get(
                    (groups.get(climate, climate), vegetation, kind), 0
                )
                if rate > 0 and self.settings.biome_ok(climate, vegetation, TOPOGRAPHY[kind]):
                    found[(climate, vegetation, kind)].append(cell)
                    self.weights[(climate, vegetation, kind)] = rate * area[(climate, vegetation)]
        for klass, cells in found.items():
            score = self.scores[klass[2]]
            cells.sort(key=lambda cell, score=score: (-int(score[cell]), cell))
            self.pools[klass] = cells
            self.members[klass] = set(cells)
            self.cursor[klass] = 0

    def _divide(self, wanted: int) -> int:
        """Place ``wanted`` cells: a first division by the weights, then rounds for the rest."""
        placed = 0
        for number in range(ROUNDS):
            short = wanted - placed
            if short <= 0:
                break
            capacity = {
                klass: self._room(klass) * CAPACITY_PERMILLE // PERMILLE
                if number == 0
                else self._room(klass)
                for klass in self.pools
            }
            offset = Fraction(hash_point(self.key, number, 1) % PPM, PPM)
            quotas = _allocate(self.weights, capacity, short, offset)
            now = sum(self._place(klass, quotas[klass]) for klass in self._order(quotas))
            if not now:
                break
            placed += now
        return placed

    def _order(self, quotas: Mapping[Class, int]) -> list[Class]:
        return sorted((klass for klass, quota in quotas.items() if quota > 0), key=_by_kind)

    def _room(self, klass: Class) -> int:
        """How many cells of the class are still free and may be taken."""
        return sum(
            1 for cell in self.pools[klass] if not self.wasteland[cell] and cell not in self.dead
        )

    # -- units ---------------------------------------------------------------------------

    def _draw_size(self, kind: str) -> int:
        """The size, in cells, of a unit of ``kind``.

        A generated cell is several times a vanilla location, so what carries over is where the
        area lies: a vanilla wasteland pixel is drawn at random and the size of its location,
        in cells, is the unit's (small locations hold little of the area and rarely come up).
        """
        sizes = self.calibration.sizes.get(kind, ())
        if not sizes:
            return 1
        total = sum(sizes)
        point = hash_point(self.key, 100 + KINDS.index(kind), len(self.units)) % total
        size = sizes[bisect.bisect_right(list(itertools.accumulate(sizes)), point)]
        return max(1, (size + self.mean_cell // 2) // self.mean_cell)

    def _place(self, klass: Class, quota: int) -> int:
        placed = 0
        while placed < quota:
            seed = self._next_seed(klass)
            if seed is None:
                break
            size = min(quota - placed, self._draw_size(klass[2]))
            grown = self._grow(klass, seed, size)
            self.units.append((klass[2], grown))
            placed += grown
        return placed

    def _next_seed(self, klass: Class) -> int | None:
        """The best cell of the class that can still be wasteland, or None."""
        pool = self.pools[klass]
        triple = (klass[0], klass[1], TOPOGRAPHY[klass[2]])
        while self.cursor[klass] < len(pool):
            cell = pool[self.cursor[klass]]
            self.cursor[klass] += 1
            if self._admissible(cell, triple, frozenset()):
                return cell
        return None

    def _admissible(self, cell: int, triple: Triple, unit: frozenset[int] | set[int]) -> bool:
        """Whether ``cell`` may join a unit: free, not touching another unit of the same
        attributes (the two would merge into one location of unbounded size), and not the last
        way of any passable cell to a coast."""
        if self.wasteland[cell] or cell in self.dead:
            return False
        for other in self.adjacency[cell]:
            if other not in unit and self.triple.get(other) == triple:
                return False
        if not self.reach.can_block(cell):
            self.dead.add(cell)
            return False
        return True

    def _grow(self, klass: Class, seed: int, size: int) -> int:
        """A unit from ``seed``: the best neighbours of its cells, up to ``size`` cells."""
        triple = (klass[0], klass[1], TOPOGRAPHY[klass[2]])
        score = self.scores[klass[2]]
        members = self.members[klass]
        unit: set[int] = {seed}
        self._take(seed, triple)
        frontier: list[tuple[int, int]] = []

        def push(cell: int) -> None:
            for other in self.adjacency[cell]:
                if other in members and other not in unit:
                    heapq.heappush(frontier, (-int(score[other]), other))

        push(seed)
        while len(unit) < size and frontier:
            _, cell = heapq.heappop(frontier)
            if cell in unit or not self._admissible(cell, triple, unit):
                continue
            self._take(cell, triple)
            unit.add(cell)
            push(cell)
        return len(unit)

    def _take(self, cell: int, triple: Triple) -> None:
        self._mark(cell, triple)
        self.reach.block(cell)

    # -- result --------------------------------------------------------------------------

    def _result(self, budget: int, frozen: int, forced: int, placed: int) -> WastelandPlan:
        terrain = self.terrain
        kinds = tuple(
            (CellClass.WASTELAND if self.wasteland[cell] else CellClass.LAND)
            if self.land[cell]
            else kind
            for cell, kind in enumerate(terrain.kinds)
        )
        topography = {cell: triple[2] for cell, triple in self.triple.items()}
        by_kind: dict[str, int] = defaultdict(int)
        for name, cells in self.units:
            by_kind[name] += cells
        sizes = sorted((cells for _, cells in self.units), reverse=True)
        stats: dict[str, object] = {
            "budget": budget,
            "frozen_coastal_or_polar": frozen,
            "unreachable_forced": forced,
            "planned": placed,
            "shortfall": max(0, budget - frozen - placed),
            "by_kind": dict(by_kind),
            "units": len(sizes),
            "largest_units": sizes[:8],
        }
        return WastelandPlan(kinds, topography, stats)


def _by_kind(klass: Class) -> tuple[int, str, str]:
    return KINDS.index(klass[2]), klass[0], klass[1]


def plan_wastelands(
    terrain: Terrain, calibration: Calibration, settings: WastelandSettings, *, seed: int
) -> WastelandPlan:
    """Decide which land cells are wasteland, and of what kind, for a world of ``terrain``.

    Wastelands that touch the sea or a polar edge stay as they are, and so do the cells that
    touch the sea; every other cell is planned afresh: ``settings.budget`` less the wastelands
    at a coast.
    """
    return _Planner(terrain, calibration, settings, seed).run(settings.budget)
