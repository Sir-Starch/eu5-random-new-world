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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rng import SplitMix64, derive_seed

if TYPE_CHECKING:
    from collections.abc import Collection

    from numpy.typing import NDArray

    from rnw.settings import NativeSettings

PERMILLE: Final[int] = 1000
STEP_COST: Final[int] = 1000
# Vanilla American locations owned by states hold a median 10 (mean 34) times the
# population a tribal density fit predicts [V-EXEC C67]; full complexity gives 12 times.
COMPLEX_GAIN: Final[int] = 11_000
# Peasants are a median 39% (quartiles 34-44%) of pops in vanilla state locations.
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
# A great empire takes the nearest inhabited land around its capital, this many permille of
# all land locations, but at least EMPIRE_FLOOR [INFERRED design]. Vanilla 1337's largest
# native state, the Aztec empire, holds 23 of 4,434 land locations (5 permille) [V-EXEC C117].
EMPIRE_SHARE: Final[tuple[int, int]] = (8, 16)
EMPIRE_FLOOR: Final[int] = 12


@dataclass(frozen=True, slots=True, eq=False)
class LandGraph:
    """Land locations 0..n-1 with per-location inputs and contacts."""

    capacity: NDArray[np.int64]
    potential: NDArray[np.int64]
    cost: NDArray[np.int64]
    edges: NDArray[np.int64]
    links: NDArray[np.int64]
    link_cost: int = 4 * STEP_COST


@dataclass(frozen=True, slots=True)
class Polity:
    """A state (owns its members) or a tribe (holds their pops); capital is a member."""

    kind: str
    members: tuple[int, ...]
    capital: int
    culture: int
    great: bool = False


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

    def grow(
        self,
        seeds: list[int],
        *,
        weights: list[int] | None = None,
        allowed: NDArray[np.bool_] | None = None,
        limit: int | None = None,
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
                total = raw + self.costs[slot]
                if limit is not None and total > limit:
                    continue
                heapq.heappush(heap, (total * PERMILLE // weight, index, target, total))
        return np.array(costs, dtype=np.int64), np.array(owners, dtype=np.int64)


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


def _zones(
    graph: _Graph,
    members: NDArray[np.bool_],
    *,
    locations: int,
    rng: SplitMix64,
    bias: NDArray[np.int64] | None = None,
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
        _, owner = graph.grow(seeds, weights=weights, allowed=members)
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
) -> NDArray[np.bool_]:
    """State land: ``share`` permille of the inhabited land, mostly the most complex.

    ``spread`` permille of it goes to pockets away from the core, as the small groups of
    states apart from the great centres in vanilla 1337 America (C117): a pocket starts at
    an inhabited location at least ``reach`` from all other state land, drawn by its
    potential, and takes the nearest one to three times ``pocket`` locations.
    """
    candidates = np.flatnonzero(inhabited & (complexity > 0))
    wanted = int(np.count_nonzero(inhabited)) * share // PERMILLE
    outlying = wanted * spread // PERMILLE if moves is not None and rng is not None else 0
    order = candidates[np.argsort(-complexity[candidates], kind="stable")][: wanted - outlying]
    land = np.zeros(len(complexity), dtype=bool)
    land[order] = True
    if outlying == 0 or moves is None or rng is None or potential is None:
        return land
    placed = 0
    while placed < outlying:
        taken = np.flatnonzero(land).tolist()
        cost, _ = moves.grow(taken, limit=reach) if taken else (np.full(len(land), -1), None)
        pool = np.flatnonzero(inhabited & ~land & (cost < 0))
        if pool.size == 0:
            break
        weights = np.maximum(1, potential[pool])
        pick = rng.below(int(weights.sum()))
        start = int(pool[int(np.searchsorted(np.cumsum(weights), pick, side="right"))])
        size = min(outlying - placed, pocket * (1 + rng.below(3)))
        near, _ = moves.grow([start], allowed=inhabited & ~land, limit=reach)
        reached = np.flatnonzero(near >= 0)
        members = reached[np.argsort(near[reached], kind="stable")][: max(1, size)]
        land[members] = True
        placed += int(members.size)
    return land


def _states(
    graph: _Graph,
    land: NDArray[np.bool_],
    population: NDArray[np.int64],
    *,
    locations: int,
    rng: SplitMix64,
) -> list[tuple[int, list[int]]]:
    """Capitals and members of states covering ``land``; big capitals grow farther."""
    nodes = np.flatnonzero(land).tolist()
    if not nodes:
        return []
    jitter = np.array([PERMILLE + rng.below(HEARTH_JITTER) for _ in range(len(population))])
    order = [int(node) for node in np.argsort(-(population * jitter), kind="stable") if land[node]]
    wanted = max(1, (len(nodes) + locations // 2) // locations)
    capitals = _spaced_seeds(graph, order, wanted=wanted, spacing=2 * STEP_COST, allowed=land)
    peak = max(1, int(population[capitals].max()))
    while True:
        weights = [
            PERMILLE // 2 + 3 * PERMILLE * int(population[c]) // (2 * peak) for c in capitals
        ]
        _, owner = graph.grow(capitals, weights=weights, allowed=land)
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
) -> list[tuple[int, list[int]]]:
    """Capitals and members of the great empires: each hearth raises one with ``chance`` permille.

    The empire's capital is the most populous inhabited location near its hearth, and it
    takes the nearest inhabited locations by travel cost, so it is connected; it never takes
    land another empire holds. A stream of its own draws the chance and the size for every
    hearth whether or not an empire rises, so a higher chance raises empires at the same
    hearths and more, and ``chance`` 0 changes nothing else.
    """
    rng = SplitMix64(derive_seed(seed, "empires"))
    taken = np.zeros(len(inhabited), dtype=bool)
    empires: list[tuple[int, list[int]]] = []
    for hearth in hearths:
        draw, share = rng.below(PERMILLE), _uniform(rng, EMPIRE_SHARE)
        if draw >= chance or taken[hearth]:
            continue
        free = inhabited & ~taken
        near, _ = graph.grow([hearth], allowed=free, limit=2 * STEP_COST)
        candidates = np.flatnonzero((near >= 0) & inhabited)
        if not candidates.size:
            continue
        capital = int(candidates[int(np.argmax(population[candidates]))])
        reach, _ = graph.grow([capital], allowed=free)
        reached = np.flatnonzero(reach >= 0)
        size = max(EMPIRE_FLOOR, len(inhabited) * share // PERMILLE)
        members = reached[np.argsort(reach[reached], kind="stable")][:size]
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
) -> list[Polity]:
    polities: list[Polity] = []
    for zone in range(int(culture.max()) + 1 if len(culture) else 0):
        members = land & (culture == zone)
        if not np.any(members) or rng.below(PERMILLE) >= settings.organized_permille:
            continue
        parts, count = _zones(graph, members, locations=settings.tribe_locations, rng=rng)
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
    graph: LandGraph, settings: NativeSettings, *, seed: int, target: int
) -> Societies:
    """Native societies for one land graph; ``target`` is the total in milli-pops."""
    count = len(graph.capacity)
    moves = _Graph(graph)
    rng = SplitMix64(derive_seed(seed, "natives"))
    reach = settings.hearth_reach_steps * STEP_COST
    expected = count * settings.hearths_per_10k
    wanted = expected // 10_000 + (1 if rng.below(10_000) < expected % 10_000 else 0)
    food = _food(moves, graph.potential, reach // 2)
    hearths = _hearths(moves, food, wanted=wanted, reach=reach, rng=rng)
    complexity = _complexity(moves, hearths, graph.potential, reach=reach, rng=rng)
    population = _population(
        graph.capacity, complexity, target * settings.population_permille // PERMILLE, rng
    )
    share = PEASANT_PEAK * complexity // PERMILLE
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
    state_land = _state_land(
        complexity,
        inhabited,
        settings.state_share_permille,
        spread=settings.state_spread_permille,
        moves=moves,
        potential=graph.potential,
        reach=reach,
        pocket=settings.state_locations,
        rng=rng,
    )
    empires = _empires(
        moves, hearths, population, inhabited, chance=settings.empire_permille, seed=seed
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
            state_land & ~empire_land,
            population,
            locations=settings.state_locations,
            rng=rng,
        )
    ]
    polities += _tribes(
        moves, culture, inhabited & ~state_land & ~empire_land, population, settings, rng
    )
    ranks, markets = _ranks(polities, population, hearths, moves, reach)
    return Societies(
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
