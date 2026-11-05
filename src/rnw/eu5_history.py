"""1037 bootstrap at the boundary between calibrated EU5 population and history.

H4's construction adapter. This module is not wired into the world writer until
the complete final-plan projection is ready. It reads typed data, never EU5 output.
"""

# NumPy scalar/list conversion is typed as Any in its stubs.
# pyright: reportAny=false

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_start import PopCohort
from rnw.history_checks import require, unique
from rnw.history_engine import create
from rnw.history_model import (
    PERMILLE,
    Authority,
    Cohort,
    District,
    Founding,
    Geography,
    Hearth,
    History,
    HistoryError,
    Route,
    Rules,
    Tenure,
)
from rnw.rng import SplitMix64, derive_seed
from rnw.societies import EMPIRE_FLOOR, STATE, TRIBE, LandGraph, Societies, hearth_domains

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping, Sequence

    from rnw.eu5_natives import VanillaNatives

Population = tuple[tuple[str, tuple[PopCohort, ...]], ...]

# D26 design weights of founding authority in a regional tradition, before each
# region's own variation (0.5-1.5x per authority), its coasts and its sacred places.
TRADITION: Final[dict[Authority, int]] = {
    Authority.COUNCIL: 100,
    Authority.RULER: 450,
    Authority.SACRED: 100,
    Authority.CUSTOMARY: 300,
}
COASTAL_COUNCIL: Final[int] = 200
SACRED_TRADITION: Final[int] = 100
DOMINANT_TRADITION: Final[int] = 3


def _checkpoint() -> None:
    """Optional generator cancellation callback."""


def installed_rules(vanilla: VanillaNatives) -> Rules:
    """Reuse installed engine prerequisites, without seeding any actual outcome."""
    calibration = vanilla.archetypes
    if calibration is None:
        message = "Missing history archetype calibration"
        raise HistoryError(message)
    require(vanilla.empire is not None, "Missing history empire calibration")
    return Rules(
        minimum_peasants=vanilla.state_floor.peasants,
        minimum_share=vanilla.state_floor.share,
        minimum_overlord_technology=vanilla.overlord_level,
        empire_locations=EMPIRE_FLOOR,
        league_technology=calibration.republic_level,
        confederation_density=calibration.confederate_density,
    )


def canonical_population(pops: Mapping[str, Sequence[PopCohort]]) -> Population:
    """Merge equal typed cohorts, rejecting invalid input rather than losing it."""
    result: list[tuple[str, tuple[PopCohort, ...]]] = []
    for key, rows in sorted(pops.items()):
        require(bool(key), "Empty population location")
        merged: Counter[tuple[str, str, str]] = Counter()
        for pop in rows:
            require(
                bool(pop.kind and pop.culture and pop.religion) and pop.amount > 0,
                "Invalid typed population cohort",
            )
            merged[pop.kind, pop.culture, pop.religion] += pop.amount
        if merged:
            result.append(
                (
                    key,
                    tuple(
                        PopCohort(kind, amount, culture, religion)
                        for (kind, culture, religion), amount in sorted(merged.items())
                    ),
                )
            )
    return tuple(result)


def identity_cohorts(pops: Sequence[PopCohort]) -> tuple[Cohort, ...]:
    """History's identity and farming budgets, including every diaspora and elite."""
    people: Counter[tuple[str, str]] = Counter()
    farmers: Counter[tuple[str, str]] = Counter()
    for pop in pops:
        people[pop.culture, pop.religion] += pop.amount
        if pop.kind == "peasants":
            farmers[pop.culture, pop.religion] += pop.amount
    return tuple(
        Cohort(culture, religion, amount, farmers[culture, religion])
        for (culture, religion), amount in sorted(people.items())
    )


@dataclass(frozen=True, slots=True, eq=False)
class BootstrapInputs:
    """Already constructed identities and physical opportunity; no resource roll.

    ``pops`` is AFTER diaspora. Technology is keyed by polity seat and must cover
    every state/tribe explicitly. Rules are the installed agrarian, technology and
    extraordinary predicates, supplied by the existing calibration adapter.
    """

    graph: LandGraph
    societies: Societies
    keys: tuple[str, ...]
    regions: Mapping[str, str]
    pops: Mapping[str, Sequence[PopCohort]]
    technology: Mapping[str, int]
    routes: tuple[Route, ...]
    rules: Rules
    highland: Collection[str] = ()
    sacred: Collection[str] = ()


@dataclass(frozen=True, slots=True)
class HistoryBootstrap:
    """Immutable population roots retained for exact typed-cohort projection."""

    history: History
    pops: Population
    calibrated_population: int
    diaspora_population: int


def _conditions(inputs: BootstrapInputs, pops: Population) -> None:
    keys, societies, graph = inputs.keys, inputs.societies, inputs.graph
    unique(keys, "bootstrap location")
    require(
        all(
            p.members
            and all(0 <= node < len(keys) for node in p.members)
            and p.capital in p.members
            for p in societies.polities
        )
        and all(0 <= centre < len(keys) for centre in societies.hearths)
        and len(set(societies.hearths)) == len(societies.hearths),
        "Invalid bootstrap polity/hearth",
    )
    require(
        all(
            len(values) == len(keys)
            for values in (
                graph.capacity,
                graph.potential,
                graph.cost,
                societies.population,
                societies.peasants,
                societies.complexity,
                societies.culture,
                societies.religion,
            )
        ),
        "History bootstrap dimensions differ",
    )
    require(
        graph.coastal is None or len(graph.coastal) == len(keys),
        "History bootstrap coastal dimensions differ",
    )
    require(
        set(inputs.regions) == set(keys)
        and set(inputs.pops) <= set(keys)
        and set(inputs.highland) <= set(keys)
        and set(inputs.sacred) <= set(keys),
        "History bootstrap geography/identities differ",
    )
    require(
        all(0 <= int(value) <= PERMILLE for value in graph.potential)
        and all(int(value) > 0 for value in graph.cost),
        "Invalid history terrain opportunity",
    )
    by_place = dict(pops)
    for node, key in enumerate(keys):
        population = int(societies.population[node])
        peasants = int(societies.peasants[node])
        actual = identity_cohorts(by_place.get(key, ()))
        require(
            0 <= peasants <= population
            and sum(pop.population for pop in actual) >= population
            and sum(pop.peasants for pop in actual) >= peasants
            and bool(actual) == (population > 0),
            f"Typed bootstrap population is incomplete at {key}",
        )
    require(
        set(inputs.technology) == {keys[polity.capital] for polity in societies.polities}
        and all(value >= 0 for value in inputs.technology.values()),
        "Incomplete bootstrap technology",
    )
    require(
        all(not p.great and not p.landed and p.kind in {STATE, TRIBE} for p in societies.polities),
        "An extraordinary outcome was assigned before history",
    )
    require(
        all(route.sea_steps <= inputs.rules.max_sea_steps for route in inputs.routes),
        "Bootstrap passage exceeds the history route bound",
    )
    positions = {key: node for node, key in enumerate(keys)}
    require(
        all(route.first in positions and route.second in positions for route in inputs.routes),
        "Bootstrap route names an unknown location",
    )
    for sea, edges in ((False, graph.edges), (True, graph.links)):
        planned = {
            tuple(sorted((positions[route.first], positions[route.second])))
            for route in inputs.routes
            if bool(route.sea_steps) is sea
        }
        require(
            planned == {tuple(sorted((int(a), int(b)))) for a, b in edges},
            "Bootstrap graph differs from physical history routes",
        )


def traditions(districts: Sequence[District], seed: int) -> dict[str, tuple[int, ...]]:
    """Each region's weighting of founding authority, in ``Authority`` order (D26).

    Neighbours of a region tend to share institutions while regions differ; coasts
    favour councils and actual sacred places sacred authority. Neither a donor
    identity nor a template grants an institution.
    """
    places: dict[str, list[District]] = defaultdict(list)
    for place in districts:
        places[place.region].append(place)
    found: dict[str, tuple[int, ...]] = {}
    for region, members in sorted(places.items()):
        coastal = sum(place.coastal for place in members) * PERMILLE // len(members)
        weights: list[int] = []
        for authority in Authority:
            variation = derive_seed(seed, "history", "tradition", region, authority.value) % 1001
            weight = TRADITION[authority] * (500 + variation) // PERMILLE
            if authority is Authority.COUNCIL:
                weight += COASTAL_COUNCIL * coastal // PERMILLE
            if authority is Authority.SACRED and any(place.sacred for place in members):
                weight += SACRED_TRADITION
            weights.append(max(1, weight))
        # Each region has one dominant tradition, so regions differ visibly.
        point = derive_seed(seed, "history", "tradition", region, "dominant") % sum(weights)
        for number, weight in enumerate(weights):
            if point < weight:
                weights[number] = weight * DOMINANT_TRADITION
                break
            point -= weight
        found[region] = tuple(weights)
    return found


def _foundings(
    inputs: BootstrapInputs,
    districts: Sequence[District],
    *,
    seed: int,
    checkpoint: Callable[[], None],
) -> tuple[Founding, ...]:
    keys = inputs.keys
    held: set[str] = set()
    found: list[Founding] = []
    regional = traditions(districts, seed)
    for polity in inputs.societies.polities:
        checkpoint()
        require(
            bool(polity.members)
            and all(0 <= member < len(keys) for member in polity.members)
            and polity.capital in polity.members,
            "Invalid bootstrap polity",
        )
        members = tuple(sorted(keys[node] for node in polity.members))
        require(not held.intersection(members), "Bootstrap polities overlap")
        held.update(members)
        seat = keys[polity.capital]
        key = f"polity:{seat}"
        tenure = Tenure.LAND if polity.kind == STATE else Tenure.TRIBE
        # Founding authority has its own stream, weighted by the region's tradition:
        # neither a donor identity nor its template gives an institutional advantage.
        weights = regional[inputs.regions[seat]]
        point = SplitMix64(derive_seed(seed, "history", "authority", key)).below(sum(weights))
        authority = Authority.CUSTOMARY
        for candidate, weight in zip(Authority, weights, strict=True):
            if point < weight:
                authority = candidate
                break
            point -= weight
        found.append(
            Founding(
                key,
                tenure,
                members,
                seat,
                authority,
                inputs.technology[seat],
            )
        )
    places = {place.key: place for place in districts}
    unorganized = {place.key for place in districts if place.population and place.key not in held}
    near: dict[str, set[str]] = defaultdict(set)
    for route in inputs.routes:
        if route.sea_steps <= inputs.rules.max_sea_steps:
            near[route.first].add(route.second)
            near[route.second].add(route.first)
    # Communities cover the remaining inhabited envelope, with no exported tags.
    # Connect only neighbours with the same dominant identity; minorities remain.
    identity = {
        key: max(place.cohorts, key=lambda pop: (pop.population, pop.culture, pop.religion))
        for key, place in places.items()
        if place.cohorts
    }
    while unorganized:
        checkpoint()
        start = min(unorganized)
        members, pending = {start}, [start]
        unorganized.remove(start)
        origin = identity[start]
        while pending:
            for other in sorted(near[pending.pop()] & unorganized):
                target = identity[other]
                if (origin.culture, origin.religion) == (target.culture, target.religion):
                    unorganized.remove(other)
                    members.add(other)
                    pending.append(other)
        seat = min(members, key=lambda key: (-places[key].population, key))
        found.append(
            Founding(
                f"community:{min(members)}",
                Tenure.COMMUNITY,
                tuple(sorted(members)),
                seat,
                technology=0,
            )
        )
    return tuple(sorted(found, key=lambda founding: founding.key))


def bootstrap_history(
    inputs: BootstrapInputs,
    *,
    seed: int,
    empire_permille: int,
    turbulence: int = 500,
    checkpoint: Callable[[], None] = _checkpoint,
) -> HistoryBootstrap:
    """Construct causal roots for every inhabitant, with no 1337 outcome preassigned.

    Provisional food headroom is population * farming potential / 4000 (0-25%).
    It is independent of RGOs and of donor identity, never reduces the starting
    budget, and is not a demographic population estimate or an H7 calibration.
    """
    pops = canonical_population(inputs.pops)
    _conditions(inputs, pops)
    keys, graph, societies = inputs.keys, inputs.graph, inputs.societies
    typed = dict(pops)
    tenure: dict[str, Tenure] = {}
    for polity in societies.polities:
        require(
            all(0 <= member < len(keys) for member in polity.members),
            "Invalid bootstrap polity location",
        )
        for member in polity.members:
            require(keys[member] not in tenure, "Bootstrap polities overlap")
            tenure[keys[member]] = Tenure.LAND if polity.kind == STATE else Tenure.TRIBE
    districts: list[District] = []
    for node, key in enumerate(keys):
        checkpoint()
        cohorts = identity_cohorts(typed.get(key, ()))
        population = sum(pop.population for pop in cohorts)
        districts.append(
            District(
                key,
                inputs.regions[key],
                tenure.get(key, Tenure.COMMUNITY),
                cohorts,
                coastal=bool(graph.coastal[node]) if graph.coastal is not None else False,
                defence=max(PERMILLE, int(graph.cost[node])),
                sacred=key in inputs.sacred,
                headroom=population * int(graph.potential[node]) // (4 * PERMILLE),
                highland=key in inputs.highland,
                complexity=int(societies.complexity[node]),
            )
        )
    domains = hearth_domains(graph, societies.hearths)
    hearths = tuple(
        Hearth(
            f"hearth:{keys[centre]}",
            keys[centre],
            tuple(keys[node] for node, owner in enumerate(domains) if owner == number),
        )
        for number, centre in enumerate(societies.hearths)
    )
    history = create(
        Geography(tuple(districts), inputs.routes, inputs.rules, hearths),
        _foundings(inputs, districts, seed=seed, checkpoint=checkpoint),
        seed=seed,
        empire_permille=empire_permille,
        turbulence=turbulence,
        checkpoint=checkpoint,
    )
    calibrated = int(societies.population.sum())
    return HistoryBootstrap(
        history,
        pops,
        calibrated,
        sum(pop.amount for _, rows in pops for pop in rows) - calibrated,
    )
