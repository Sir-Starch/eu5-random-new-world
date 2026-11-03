"""Native societies of a generated New World: population, cultures, religions, polities.

Game-independent. The input is a graph of land locations with a tribal carrying
capacity, a farming potential and a travel cost per location, plus sea links between
coasts that share a sea zone. Civilisation hearths start where smoothed farming
potential is highest; complexity falls off with travel cost from a hearth and is
damped on poor land. Complexity multiplies population density and the peasant share,
and turns land into states; elsewhere cultures form tribes or stay unorganised.
Religion zones grow by weighted travel cost over the whole graph and culture zones
grow inside them, so every zone is connected. All arithmetic is integer.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rng import SplitMix64, derive_seed

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from numpy.typing import NDArray

    from rnw.settings import NativeSettings

PERMILLE: Final[int] = 1000
STEP_COST: Final[int] = 1000
# Vanilla American locations owned by states hold a median 10 (mean 34) times the
# population a tribal density fit predicts [V-EXEC C67]; full complexity gives 12 times.
COMPLEX_GAIN: Final[int] = 11_000
# Default peasant share at full complexity: peasants are a median 39% (quartiles 34-44%) of
# pops in vanilla state locations. State-land planning keeps this baseline so the mix control
# changes pop types without moving land or changing the population distribution.
PEASANT_PEAK: Final[int] = 600
# Poor land damps complexity: gate = GATE_BASE + (1000 - GATE_BASE) * potential.
GATE_BASE: Final[int] = 400
HEARTH_FLOOR: Final[int] = 500
HEARTH_JITTER: Final[int] = 300
HEARTH_STRENGTH: Final[tuple[int, int]] = (700, 1000)
NOISE_RANGE: Final[tuple[int, int]] = (600, 1500)
ZONE_WEIGHT: Final[tuple[int, int]] = (700, 1300)
# Seeds of a zone of N locations keep about 1.1 * sqrt(N / pi) steps apart.
SPACING_PERMILLE: Final[int] = 620
MIN_POPULATION: Final[int] = 20
# Vanilla 1337 Americas: 9 cities and 16 towns for 223 landed countries [V-EXEC C67].
CITY_PERMILLE: Final[int] = 40
TOWN_PERMILLE: Final[int] = 110
CITY: Final[str] = "city"
TOWN: Final[str] = "town"
STATE: Final[str] = "state"
TRIBE: Final[str] = "tribe"
# A great empire takes connected inhabited land around its capital, this many permille of
# all land locations, but at least EMPIRE_FLOOR [INFERRED design]. Vanilla 1337's largest
# native state, the Aztec empire, holds 23 of 4,434 land locations (5 permille) [V-EXEC C117].
EMPIRE_SHARE: Final[tuple[int, int]] = (8, 16)
EMPIRE_FLOOR: Final[int] = 12
BOOTSTRAP_MIN: Final[int] = 400


@dataclass(frozen=True, slots=True, eq=False)
class LandGraph:
    """Land locations 0..n-1 with per-location inputs and contacts."""

    capacity: NDArray[np.int64]
    potential: NDArray[np.int64]
    cost: NDArray[np.int64]
    edges: NDArray[np.int64]
    links: NDArray[np.int64]
    link_cost: int = 4 * STEP_COST
    coastal: NDArray[np.bool_] | None = None


@dataclass(frozen=True, slots=True)
class Polity:
    """A state (owns its members) or a tribe (holds their pops); capital is a member.

    A ``landed`` tribe owns its members like a state, as the confederates of vanilla's
    Haudenosaunee do (R7d).
    """

    kind: str
    members: tuple[int, ...]
    capital: int
    culture: int
    great: bool = False
    landed: bool = False


@dataclass(frozen=True, slots=True)
class StateFloor:
    """Least agrarian population and share supporting a landed country, from vanilla.

    Population is in milli-pops, share in permille. The game-independent default only
    requires a nonzero farming population; the adapter supplies the installed baseline.
    """

    peasants: int = 1
    share: int = 1

    def supports(self, population: int, peasants: int) -> bool:
        return peasants >= self.peasants and peasants * PERMILLE >= population * self.share


MINIMUM_STATE_SUPPORT: Final[StateFloor] = StateFloor()


@dataclass(frozen=True, slots=True, eq=False)
class Societies:
    """Per-location population (milli-pops), zones and the polities."""

    complexity: NDArray[np.int64]
    population: NDArray[np.int64]
    peasants: NDArray[np.int64]
    religion: NDArray[np.int64]
    culture: NDArray[np.int64]
    hearths: tuple[int, ...]
    polities: tuple[Polity, ...]
    ranks: dict[int, str]
    markets: tuple[int, ...]


class _Graph:
    """Compressed adjacency with the cost of each move."""

    __slots__: tuple[str, ...] = ("costs", "starts", "targets")

    def __init__(self, graph: LandGraph) -> None:
        count = len(graph.capacity)
        pairs = [graph.edges, graph.edges[:, ::-1], graph.links, graph.links[:, ::-1]]
        sources = np.concatenate([pair[:, 0] for pair in pairs])
        targets = np.concatenate([pair[:, 1] for pair in pairs])
        extra = np.concatenate(
            [
                np.zeros(2 * len(graph.edges), dtype=np.int64),
                np.full(2 * len(graph.links), graph.link_cost, dtype=np.int64),
            ]
        )
        order = np.lexsort((targets, sources))
        self.targets: list[int] = targets[order].tolist()
        self.costs: list[int] = (graph.cost[targets] + extra)[order].tolist()
        self.starts: list[int] = np.searchsorted(sources[order], np.arange(count + 1)).tolist()

    def grow(  # noqa: PLR0913 - travel, identity and habitat costs share one connected frontier.
        self,
        seeds: list[int],
        *,
        weights: list[int] | None = None,
        allowed: NDArray[np.bool_] | None = None,
        limit: int | None = None,
        identity: _Identity | None = None,
        territory: _Territory | None = None,
    ) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Weighted multi-source travel cost: (raw cost, owning seed index) per node.

        A node joins the seed reaching it first by cost * 1000 / weight; regions are
        connected through their own members. Unreached nodes get -1.
        """
        count = len(self.starts) - 1
        owner = np.full(count, -1, dtype=np.int64)
        cost = np.full(count, -1, dtype=np.int64)
        heap: list[tuple[int, int, int, int]] = []
        for index, node in enumerate(seeds):
            heapq.heappush(heap, (0, index, node, 0))
        owners: list[int] = owner.tolist()
        costs: list[int] = cost.tolist()
        permitted = None if allowed is None else allowed.tolist()
        while heap:
            _, index, node, raw = heapq.heappop(heap)
            if owners[node] >= 0:
                continue
            owners[node] = index
            costs[node] = raw
            weight = PERMILLE if weights is None else weights[index]
            for slot in range(self.starts[node], self.starts[node + 1]):
                target = self.targets[slot]
                if owners[target] >= 0 or (permitted is not None and not permitted[target]):
                    continue
                penalty = 1 if identity is None else identity.penalty(seeds[index], target)
                habitat = PERMILLE if territory is None else territory.penalty(seeds[index], target)
                total = raw + self.costs[slot] * penalty * habitat // PERMILLE
                if limit is not None and total > limit:
                    continue
                heapq.heappush(heap, (total * PERMILLE // weight, index, target, total))
        return np.array(costs, dtype=np.int64), np.array(owners, dtype=np.int64)


@dataclass(frozen=True, slots=True)
class _Territory:
    """Founding-centre affinities: generalist, farming corridor, habitat or coast.

    Preferences add at most twice the normal move cost. Every move stays positive,
    so frontiers remain connected and barriers are traversable. There is no direction
    or coordinate assumption: coastal distance follows the graph, including wrap.
    Only polities use these costs; population and identity zones keep their own model.
    """

    styles: list[int]
    potential: list[int]
    terrain: list[int]
    inland: list[int]
    strength: int = PERMILLE

    @classmethod
    def of(cls, graph: LandGraph, moves: _Graph, seed: int) -> _Territory:
        coast = [] if graph.coastal is None else np.flatnonzero(graph.coastal).tolist()
        distance, _ = moves.grow(coast)
        inland = np.where(distance < 0, 4 * STEP_COST, distance).tolist()
        rng = SplitMix64(derive_seed(seed, "territory-affinities"))
        # Coastal growth is an option only for centres within two travel steps of
        # the sea. Inland and coastless societies still have three viable styles.
        styles = [rng.below(4 if near <= 2 * STEP_COST else 3) for near in inland]
        return cls(styles, graph.potential.tolist(), graph.cost.tolist(), inland)

    def penalty(self, capital: int, target: int) -> int:
        """A bounded permille move multiplier relative to the founding centre."""
        match self.styles[capital]:
            case 1:
                # Fertile valleys and river-fed plains can extend beyond the centre.
                extra = 3 * (PERMILLE - self.potential[target])
            case 2:
                # Similar terrain permits upland belts as well as lowland basins.
                extra = 2 * abs(self.terrain[capital] - self.terrain[target])
            case 3:
                extra = self.inland[target] * PERMILLE // (2 * STEP_COST)
            case _:
                extra = 0
        return PERMILLE + min(2 * PERMILLE, extra) * self.strength // PERMILLE


@dataclass(frozen=True, slots=True)
class _Identity:
    """Soft growth costs relative to a capital; identities and populations stay fixed."""

    culture: list[int]
    religion: list[int]
    cultural_cost: int = 3
    religious_cost: int = 2

    def penalty(self, capital: int, target: int) -> int:
        """Charge throughout foreign territory, including travel back through it."""
        return (
            1
            + self.cultural_cost * (self.culture[capital] != self.culture[target])
            + self.religious_cost * (self.religion[capital] != self.religion[target])
        )

    def capitals(self, graph: _Graph, population: NDArray[np.int64]) -> NDArray[np.int64]:
        """Population scores favouring capitals surrounded by their own identity.

        The self and immediate travel neighbours give a bounded local measure. A
        coherent centre scores up to twice as much as a boundary of equal population.
        Sea links count as neighbours, as they do for territorial growth.
        """
        scores = population.copy()
        for node in range(len(population)):
            neighbours = [node, *graph.targets[graph.starts[node] : graph.starts[node + 1]]]
            total = sum(int(population[n]) for n in neighbours)
            core = sum(
                int(population[n])
                for n in neighbours
                if self.culture[n] == self.culture[node] and self.religion[n] == self.religion[node]
            )
            scores[node] = int(population[node]) * (PERMILLE + PERMILLE * core // max(1, total))
        return scores


def _food(graph: _Graph, potential: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """Farming potential summed within ``radius`` travel cost of promising locations.

    Only locations at or above the median potential are scored; a lone fertile islet
    therefore scores far below a broad fertile region.
    """
    food = np.zeros(len(potential), dtype=np.int64)
    if not len(potential):
        return food
    floor = int(np.sort(potential)[len(potential) // 2])
    for node in np.flatnonzero(potential >= max(1, floor)).tolist():
        cost, _ = graph.grow([node], limit=radius)
        food[node] = int(potential[cost >= 0].sum())
    return food


def _uniform(rng: SplitMix64, bounds: tuple[int, int]) -> int:
    return bounds[0] + rng.below(bounds[1] - bounds[0] + 1)


def _spacing(locations: int) -> int:
    """Seed spacing in travel cost for zones of about ``locations`` locations."""
    root = math.isqrt(max(1, locations) * PERMILLE * PERMILLE)
    return max(STEP_COST, SPACING_PERMILLE * root * STEP_COST // (PERMILLE * PERMILLE))


def _spaced_seeds(
    graph: _Graph,
    order: list[int],
    *,
    wanted: int,
    spacing: int,
    allowed: NDArray[np.bool_] | None = None,
) -> list[int]:
    """Take candidates in order, skipping any within ``spacing`` of a taken seed."""
    blocked = np.zeros(len(graph.starts) - 1, dtype=bool)
    seeds: list[int] = []
    for node in order:
        if len(seeds) >= wanted:
            break
        if blocked[node]:
            continue
        seeds.append(node)
        reach, _ = graph.grow([node], allowed=allowed, limit=spacing - 1)
        blocked |= reach >= 0
    return seeds


def _shuffled(nodes: list[int], rng: SplitMix64) -> list[int]:
    out = list(nodes)
    for index in range(len(out) - 1, 0, -1):
        other = rng.below(index + 1)
        out[index], out[other] = out[other], out[index]
    return out


def _zones(  # noqa: PLR0913 - identity zones and tribal territories share the partitioner.
    graph: _Graph,
    members: NDArray[np.bool_],
    *,
    locations: int,
    rng: SplitMix64,
    bias: NDArray[np.int64] | None = None,
    territory: _Territory | None = None,
) -> tuple[NDArray[np.int64], int]:
    """Split ``members`` into connected zones of about ``locations``; -1 elsewhere."""
    nodes = np.flatnonzero(members).tolist()
    zone = np.full(len(members), -1, dtype=np.int64)
    if not nodes:
        return zone, 0
    wanted = max(1, (len(nodes) + locations // 2) // locations)
    seeds = _spaced_seeds(
        graph, _shuffled(nodes, rng), wanted=wanted, spacing=_spacing(locations), allowed=members
    )
    weights: list[int] = []
    while True:
        weights += [
            _uniform(rng, ZONE_WEIGHT) + (0 if bias is None else int(bias[node]))
            for node in seeds[len(weights) :]
        ]
        _, owner = graph.grow(seeds, weights=weights, allowed=members, territory=territory)
        missing = [node for node in nodes if owner[node] < 0]
        if not missing:
            break
        seeds.append(missing[0])
    zone[members] = owner[members]
    return zone, len(seeds)


def _hearths(
    graph: _Graph, food: NDArray[np.int64], *, wanted: int, reach: int, rng: SplitMix64
) -> list[int]:
    """Best farming regions, 1.5 reaches apart and above HEARTH_FLOOR of the best score."""
    if wanted <= 0 or not len(food) or int(food.max()) <= 0:
        return []
    jitter = np.array([PERMILLE + rng.below(HEARTH_JITTER) for _ in range(len(food))])
    keys = food * jitter
    floor = int(food.max()) * HEARTH_FLOOR // PERMILLE
    order = [int(node) for node in np.argsort(-keys, kind="stable") if food[node] >= floor]
    return _spaced_seeds(graph, order, wanted=wanted, spacing=3 * reach // 2)


def _complexity(
    graph: _Graph, hearths: list[int], potential: NDArray[np.int64], *, reach: int, rng: SplitMix64
) -> NDArray[np.int64]:
    count = len(potential)
    best = np.zeros(count, dtype=np.int64)
    for number, hearth in enumerate(hearths):
        strength = PERMILLE if number == 0 else _uniform(rng, HEARTH_STRENGTH)
        cost, _ = graph.grow([hearth], limit=reach)
        reached = cost >= 0
        level = np.zeros(count, dtype=np.int64)
        level[reached] = strength * (reach - cost[reached]) // reach
        best = np.maximum(best, level)
    gate = GATE_BASE + (PERMILLE - GATE_BASE) * potential // PERMILLE
    return best * gate // PERMILLE


def _population(
    capacity: NDArray[np.int64], complexity: NDArray[np.int64], target: int, rng: SplitMix64
) -> NDArray[np.int64]:
    noise = np.array([_uniform(rng, NOISE_RANGE) for _ in range(len(capacity))], dtype=np.int64)
    gain = PERMILLE + COMPLEX_GAIN * complexity // PERMILLE
    raw = capacity * gain // PERMILLE * noise // PERMILLE
    total = int(raw.sum())
    if total <= 0:
        return np.zeros(len(capacity), dtype=np.int64)
    out = raw * target // total
    return np.where(out >= MIN_POPULATION, out, 0)


def _state_land(  # noqa: PLR0913 - the core, the share and how the outliers are placed
    complexity: NDArray[np.int64],
    inhabited: NDArray[np.bool_],
    share: int,
    *,
    spread: int = 0,
    moves: _Graph | None = None,
    potential: NDArray[np.int64] | None = None,
    reach: int = 0,
    pocket: int = 1,
    rng: SplitMix64 | None = None,
    floor: StateFloor = MINIMUM_STATE_SUPPORT,
) -> tuple[NDArray[np.bool_], NDArray[np.int64]]:
    """State land: ``share`` permille of the inhabited land, mostly the most complex.

    ``spread`` permille of it goes to pockets away from the core, as the small groups of
    states apart from the great centres in vanilla 1337 America (C117): a pocket starts at
    an inhabited location at least ``reach`` from all other state land, drawn by its
    potential, and takes the nearest one to three times ``pocket`` locations.
    """
    complexity = complexity.copy()
    minimum = (floor.share * PERMILLE + PEASANT_PEAK - 1) // PEASANT_PEAK
    candidates = np.flatnonzero(inhabited & (complexity >= minimum))
    wanted = int(np.count_nonzero(inhabited)) * share // PERMILLE
    outlying = wanted * spread // PERMILLE if moves is not None and rng is not None else 0
    order = candidates[np.argsort(-complexity[candidates], kind="stable")][: wanted - outlying]
    land = np.zeros(len(complexity), dtype=bool)
    land[order] = True
    if outlying == 0 or moves is None or rng is None or potential is None:
        return land, complexity
    placed = 0
    while placed < outlying:
        taken = np.flatnonzero(land).tolist()
        cost, _ = moves.grow(taken, limit=reach) if taken else (np.full(len(land), -1), None)
        # A remote state needs a local farming centre, rather than ownership imposed
        # on wholly tribal land outside every hearth. Poor islands remain tribal.
        farmable = inhabited & ~land & (potential >= minimum)
        pool = np.flatnonzero(farmable & (cost < 0))
        if pool.size == 0:
            break
        weights = np.maximum(1, potential[pool])
        pick = rng.below(int(weights.sum()))
        start = int(pool[int(np.searchsorted(np.cumsum(weights), pick, side="right"))])
        size = min(outlying - placed, pocket * (1 + rng.below(3)))
        near, _ = moves.grow([start], allowed=farmable, limit=reach)
        local = int(potential[start]) * np.maximum(0, reach - near) // max(1, reach)
        reached = np.flatnonzero((near >= 0) & (local >= minimum))
        members = reached[np.argsort(near[reached], kind="stable")][: max(1, size)]
        land[members] = True
        complexity[members] = np.maximum(complexity[members], local[members])
        placed += int(members.size)
    return land, complexity


def _states(  # noqa: PLR0913 - capitals need population, eligibility and target size.
    graph: _Graph,
    land: NDArray[np.bool_],
    population: NDArray[np.int64],
    *,
    locations: int,
    rng: SplitMix64,
    eligible: NDArray[np.bool_],
    identity: _Identity,
    territory: _Territory | None = None,
) -> list[tuple[int, list[int]]]:
    """Capitals and members of states covering ``land``; big capitals grow farther."""
    nodes = np.flatnonzero(land).tolist()
    if not nodes or not np.any(land & eligible):
        return []
    jitter = np.array([PERMILLE + rng.below(HEARTH_JITTER) for _ in range(len(population))])
    order = [
        int(node)
        for node in np.argsort(-(identity.capitals(graph, population) * jitter), kind="stable")
        if land[node] and eligible[node]
    ]
    wanted = max(1, (len(nodes) + locations // 2) // locations)
    capitals = _spaced_seeds(graph, order, wanted=wanted, spacing=2 * STEP_COST, allowed=land)
    peak = max(1, int(population[capitals].max()))
    while True:
        weights = [
            PERMILLE // 2 + 3 * PERMILLE * int(population[c]) // (2 * peak) for c in capitals
        ]
        _, owner = graph.grow(
            capitals, weights=weights, allowed=land, identity=identity, territory=territory
        )
        missing = [node for node in order if owner[node] < 0]
        if not missing:
            break
        capitals.append(missing[0])
    return [
        (capital, [node for node in nodes if owner[node] == index])
        for index, capital in enumerate(capitals)
    ]


def _empires(  # noqa: PLR0913 - the hearths, the people and the chance decide
    graph: _Graph,
    hearths: list[int],
    population: NDArray[np.int64],
    inhabited: NDArray[np.bool_],
    *,
    chance: int,
    seed: int,
    eligible: NDArray[np.bool_],
    identity: _Identity,
    peasants: NDArray[np.int64],
    floor: StateFloor,
    territory: _Territory,
) -> list[tuple[int, list[int]]]:
    """Capitals and members of the great empires: each hearth raises one with ``chance`` permille.

    The empire's capital balances population and local identity coherence near its hearth.
    Growth mildly favours its culture and faith by travel cost, so it is connected; it never takes
    land another empire holds. A stream of its own draws the chance and the size for every
    hearth whether or not an empire rises, so a higher chance raises empires at the same
    hearths and more, and ``chance`` 0 changes nothing else.
    """
    rng = SplitMix64(derive_seed(seed, "empires"))
    taken = np.zeros(len(inhabited), dtype=bool)
    empires: list[tuple[int, list[int]]] = []
    scores = identity.capitals(graph, population)
    for hearth in hearths:
        draw, share = rng.below(PERMILLE), _uniform(rng, EMPIRE_SHARE)
        if draw >= chance or taken[hearth]:
            continue
        free = inhabited & ~taken
        near, _ = graph.grow([hearth], allowed=free, limit=2 * STEP_COST)
        candidates = np.flatnonzero((near >= 0) & inhabited & eligible)
        if not candidates.size:
            continue
        capital = int(candidates[int(np.argmax(scores[candidates]))])
        reach, _ = graph.grow([capital], allowed=free, identity=identity, territory=territory)
        reached = np.flatnonzero(reach >= 0)
        size = max(EMPIRE_FLOOR, len(inhabited) * share // PERMILLE)
        members = reached[np.argsort(reach[reached], kind="stable")][:size]
        if not floor.supports(int(population[members].sum()), int(peasants[members].sum())):
            continue
        taken[members] = True
        empires.append((capital, sorted(members.tolist())))
    return empires


def _tribes(  # noqa: PLR0913, PLR0917 - tribes read zones, population and the settings.
    graph: _Graph,
    culture: NDArray[np.int64],
    land: NDArray[np.bool_],
    population: NDArray[np.int64],
    settings: NativeSettings,
    rng: SplitMix64,
    territory: _Territory,
) -> list[Polity]:
    polities: list[Polity] = []
    # Typical tribes hold only six locations. Gentler preferences leave room for
    # neighbours instead of squeezing them into tiny remnants during competition.
    territory = replace(territory, strength=PERMILLE // 2)
    for zone in range(int(culture.max()) + 1 if len(culture) else 0):
        members = land & (culture == zone)
        if not np.any(members) or rng.below(PERMILLE) >= settings.organized_permille:
            continue
        parts, count = _zones(
            graph, members, locations=settings.tribe_locations, rng=rng, territory=territory
        )
        for part in range(count):
            nodes = np.flatnonzero(parts == part)
            if not nodes.size:
                continue
            capital = int(nodes[int(np.argmax(population[nodes]))])
            polities.append(Polity(TRIBE, tuple(nodes.tolist()), capital, zone))
    return polities


def _ranks(
    polities: list[Polity], population: NDArray[np.int64], hearths: list[int], graph: _Graph,
    reach: int,
) -> tuple[dict[int, str], tuple[int, ...]]:  # fmt: skip
    states = [polity for polity in polities if polity.kind == STATE]
    if not states:
        return {}, ()
    states.sort(key=lambda p: (-int(population[list(p.members)].sum()), p.capital))
    cities = max(1, (len(states) * CITY_PERMILLE + PERMILLE // 2) // PERMILLE)
    towns = (len(states) * TOWN_PERMILLE + PERMILLE // 2) // PERMILLE
    ranks = {state.capital: CITY for state in states[:cities]}
    ranks.update({state.capital: TOWN for state in states[cities : cities + towns]})
    markets = [state.capital for state in states[:cities]]
    for hearth in hearths:
        cost, _ = graph.grow([hearth], limit=reach)
        local = [state for state in states if cost[state.capital] >= 0]
        if local and local[0].capital not in markets:
            markets.append(local[0].capital)
    return ranks, tuple(markets)


def regional_markets(graph: LandGraph, societies: Societies) -> Societies:
    """Plan a trading town in every disconnected group of landed countries.

    Land contacts and shared coastal waters connect a group, through its own land only.
    Existing centres serve their group; an unserved group uses its most populous country's
    capital. Vanilla American market centres are towns or cities, never tribal wilderness.
    This is a settlement plan, not an estimate of the engine's market access or profits.
    """
    states = [p for p in societies.polities if p.kind == STATE or p.landed]
    states.sort(key=lambda p: (-int(societies.population[list(p.members)].sum()), p.capital))
    land = np.zeros(len(graph.capacity), dtype=bool)
    for state in states:
        land[list(state.members)] = True
    moves = _Graph(graph)
    ranks = dict(societies.ranks)
    markets = list(societies.markets)
    _, covered = moves.grow(markets, allowed=land)
    for state in states:
        if covered[state.capital] < 0:
            markets.append(state.capital)
            _, local = moves.grow([state.capital], allowed=land)
            covered[local >= 0] = 0
    for market in markets:
        _ = ranks.setdefault(market, TOWN)
    return replace(societies, ranks=ranks, markets=tuple(markets))


def settlement_centres(graph: LandGraph, societies: Societies, *, reach: int) -> Societies:
    """Recompute calibrated centres from the surviving countries and current population."""
    ranks, markets = _ranks(
        list(societies.polities),
        societies.population,
        list(societies.hearths),
        _Graph(graph),
        reach,
    )
    return regional_markets(graph, replace(societies, ranks=ranks, markets=markets))


def land_routes(
    graph: LandGraph, allowed: Collection[int], source: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Cheapest travel cost from ``source`` over land contacts inside ``allowed``.

    Returns the cost of every location and the location before it on its route; both are
    -1 for the unreached, and the source has cost 0 and no location before it. A move costs
    the travel cost of the location entered, as everywhere in the model, and the sea links
    are never used. Of two routes of equal cost the one whose last step starts at the lower
    index wins.
    """
    count = len(graph.capacity)
    permitted = np.zeros(count, dtype=bool)
    permitted[list(allowed)] = True
    if not permitted[source]:
        message = "The source of a route must be an allowed location"
        raise ValueError(message)
    edges = graph.edges[permitted[graph.edges[:, 0]] & permitted[graph.edges[:, 1]]]
    neighbours: dict[int, list[int]] = {}
    for first, second in edges.tolist():
        neighbours.setdefault(first, []).append(second)
        neighbours.setdefault(second, []).append(first)
    entering: list[int] = graph.cost.tolist()
    cost = [-1] * count
    before = [-1] * count
    best: dict[int, int] = {source: 0}
    heap: list[tuple[int, int]] = [(0, source)]
    while heap:
        total, node = heapq.heappop(heap)
        if cost[node] >= 0:
            continue
        cost[node] = total
        for other in neighbours.get(node, ()):
            if cost[other] >= 0:
                continue
            reach = total + entering[other]
            known = best.get(other)
            if known is None or reach < known:
                best[other], before[other] = reach, node
                heapq.heappush(heap, (reach, other))
            elif reach == known and node < before[other]:
                before[other] = node
    return np.array(cost, dtype=np.int64), np.array(before, dtype=np.int64)


def hearth_domains(graph: LandGraph, hearths: Sequence[int]) -> NDArray[np.int64]:
    """The hearth each location is nearest to by travel cost, sea links included; -1 without one.

    The domain of a hearth is what its extraordinary society, if one rises, is drawn from (R7d).
    """
    if not hearths:
        return np.full(len(graph.capacity), -1, dtype=np.int64)
    _, owner = _Graph(graph).grow(list(hearths))
    return owner


def travel_from(graph: LandGraph, source: int) -> NDArray[np.int64]:
    """Travel cost from ``source`` to each location over land contacts and sea links; -1 if none."""
    cost, _ = _Graph(graph).grow([source])
    return cost


def trunk_roads(
    graph: LandGraph, allowed: Collection[int], capital: int, targets: Collection[int]
) -> tuple[tuple[int, int], ...]:
    """Road pairs of the shortest land routes from ``capital`` to ``targets``.

    The routes run through ``allowed`` only (``land_routes``); a target that no route reaches
    stays unlinked. The result is the union of the routes as unordered pairs, each once,
    lower index first, sorted.
    """
    cost, before = land_routes(graph, allowed, capital)
    pairs: set[tuple[int, int]] = set()
    for target in targets:
        node = target
        if cost[node] < 0:
            continue
        while node != capital:
            step = int(before[node])
            pairs.add((min(node, step), max(node, step)))
            node = step
    return tuple(sorted(pairs))


def generate_societies(
    graph: LandGraph,
    settings: NativeSettings,
    *,
    seed: int,
    target: int,
    state_floor: StateFloor = MINIMUM_STATE_SUPPORT,
) -> Societies:
    """Native societies for one land graph; ``target`` is the total in milli-pops."""
    return _generate_societies(
        graph,
        settings,
        seed=seed,
        target=target,
        state_floor=state_floor,
        state_locations=settings.state_locations,
        empire_chance=settings.empire_permille,
    )


def bootstrap_societies(  # noqa: PLR0913 - calibrated inputs plus the history partition factor.
    graph: LandGraph,
    settings: NativeSettings,
    *,
    seed: int,
    target: int,
    state_floor: StateFloor,
    size_permille: int = PERMILLE,
) -> Societies:
    """1037's ordinary polities, without any extraordinary outcome assigned in advance.

    The provisional factor is 1 until H7 calibration. Scaling the partition size does
    not scale the state-land budget, its pocket size, population or identity zones.
    Trajectory chance belongs to history, never this geographical bootstrap.
    """
    if not BOOTSTRAP_MIN <= size_permille <= PERMILLE:
        message = "History bootstrap size must be between 400 and 1000 permille"
        raise ValueError(message)
    return _generate_societies(
        graph,
        settings,
        seed=seed,
        target=target,
        state_floor=state_floor,
        state_locations=max(1, settings.state_locations * size_permille // PERMILLE),
        empire_chance=0,
    )


def _generate_societies(  # noqa: PLR0913 - shared calibration, with independent partition/chance.
    graph: LandGraph,
    settings: NativeSettings,
    *,
    seed: int,
    target: int,
    state_floor: StateFloor,
    state_locations: int,
    empire_chance: int,
) -> Societies:
    count = len(graph.capacity)
    moves = _Graph(graph)
    rng = SplitMix64(derive_seed(seed, "natives"))
    reach = settings.hearth_reach_steps * STEP_COST
    expected = count * settings.hearths_per_10k
    wanted = expected // 10_000 + (1 if rng.below(10_000) < expected % 10_000 else 0)
    food = _food(moves, graph.potential, reach // 2)
    hearths = _hearths(moves, food, wanted=wanted, reach=reach, rng=rng)
    complexity = _complexity(moves, hearths, graph.potential, reach=reach, rng=rng)
    state_land, complexity = _state_land(
        complexity,
        graph.capacity > 0,
        settings.state_share_permille,
        spread=settings.state_spread_permille,
        moves=moves,
        potential=graph.potential,
        reach=reach,
        pocket=settings.state_locations,
        rng=SplitMix64(derive_seed(seed, "state-land")),
        floor=state_floor,
    )
    population = _population(
        graph.capacity, complexity, target * settings.population_permille // PERMILLE, rng
    )
    share = settings.peasant_peak_permille * complexity // PERMILLE
    peasants = population * share // PERMILLE
    everyone = np.ones(count, dtype=bool)
    religion, _ = _zones(moves, everyone, locations=settings.religion_locations, rng=rng)
    culture = np.full(count, -1, dtype=np.int64)
    zones = 0
    for zone in range(int(religion.max()) + 1 if count else 0):
        members = religion == zone
        inner, made = _zones(
            moves, members, locations=settings.culture_locations, rng=rng, bias=2 * complexity
        )
        culture[members] = inner[members] + zones
        zones += made
    inhabited = population > 0
    territory = _Territory.of(graph, moves, seed)
    agrarian = peasants * PERMILLE >= population * state_floor.share
    eligible = (peasants >= state_floor.peasants) & agrarian
    empires = _empires(
        moves,
        hearths,
        population,
        inhabited,
        chance=empire_chance,
        seed=seed,
        eligible=eligible,
        peasants=peasants,
        floor=state_floor,
        identity=_Identity(culture.tolist(), religion.tolist(), cultural_cost=1, religious_cost=1),
        territory=territory,
    )
    empire_land = np.zeros(count, dtype=bool)
    for _, members in empires:
        empire_land[members] = True
    polities = [
        Polity(STATE, tuple(members), capital, int(culture[capital]), great=True)
        for capital, members in empires
    ]
    polities += [
        Polity(STATE, tuple(members), capital, int(culture[capital]))
        for capital, members in _states(
            moves,
            state_land & inhabited & agrarian & ~empire_land,
            population,
            locations=state_locations,
            rng=rng,
            eligible=eligible,
            identity=_Identity(culture.tolist(), religion.tolist()),
            territory=territory,
        )
    ]
    # State-land share is a placement budget: a component without a supported capital
    # is available to tribes, rather than becoming an economically empty country.
    state_land = empire_land.copy()
    for polity in polities:
        state_land[list(polity.members)] = True
    polities += _tribes(
        moves, culture, inhabited & ~state_land & ~empire_land, population, settings, rng, territory
    )
    ranks, markets = _ranks(polities, population, hearths, moves, reach)
    societies = Societies(
        complexity=complexity,
        population=population,
        peasants=peasants,
        religion=religion,
        culture=culture,
        hearths=tuple(hearths),
        polities=tuple(polities),
        ranks=ranks,
        markets=markets,
    )
    return regional_markets(graph, societies)
