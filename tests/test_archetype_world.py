"""The extraordinary societies of R7d applied to a small made-up world."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import cast

import numpy as np
import pytest

from rnw.archetypes import (
    FRACTURED_REALM,
    HIGHLAND_CONFEDERATION,
    SACRED_CENTRE,
    SEA_LEAGUE,
    Rules,
    plan_archetypes,
)
from rnw.eu5_archetypes import ArchetypeCalibration
from rnw.eu5_natives import (
    Country,
    NativesError,
    VanillaNatives,
    _archetypes,  # pyright: ignore[reportPrivateUsage]
    _Cells,  # pyright: ignore[reportPrivateUsage]
    _neighbours,  # pyright: ignore[reportPrivateUsage]
    _Varied,  # pyright: ignore[reportPrivateUsage]
    archetype_structure,
    country_records,
    discover_areas,
    state_economy,
)
from rnw.pdx import parse
from rnw.societies import (
    CITY,
    STATE,
    STEP_COST,
    TOWN,
    TRIBE,
    LandGraph,
    Polity,
    Societies,
    StateFloor,
)

CALIBRATION = ArchetypeCalibration(
    republic_include="republic_t",
    republic_government=(("type", "republic"), ("heir_selection", "oligarchic_elective")),
    republic_level=2,
    theocracy=(("type", "theocracy"), ("heir_selection", "theocratic_elective")),
    confederation_date="1337.1.1",
    cohesion=(("gold", 100), ("stability", 33), ("tribal_cohesion", 90)),
    confederate_density=0,
    sliders={
        SEA_LEAGUE: (("land_vs_naval", 60),),
        SACRED_CENTRE: (("spiritualist_vs_humanist", -90),),
    },
    alliances=22,
    rivals=45,
    confederations=1,
)


def _vanilla(calibration: ArchetypeCalibration | None = CALIBRATION) -> VanillaNatives:
    return VanillaNatives(
        density={},
        population_per_location=0,
        cultures={},
        religions={},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
        archetypes=calibration,
    )


# Polities: 0-2 a league's states (one location each, a sea between them), 3-5 highland tribes in
# a chain, 6-8 a sacred centre (the state 6 touches 7 and 8), 9-12 a fractured realm of states of
# three locations each, the state 9 touching the rest.
LOCATIONS = [(n,) for n in range(9)] + [tuple(range(9 + 3 * k, 12 + 3 * k)) for k in range(4)]
NODES = 21
POPULATION = [600, 500, 400, 100, 90, 80, 1000, 900, 800, 350, 340, 330, 320]
EDGES = [
    (3, 4),
    (4, 5),
    (6, 7),
    (6, 8),
    *((9 + 3 * k + i, 9 + 3 * k + i + 1) for k in range(4) for i in range(2)),
    (9, 12),
    (9, 15),
    (9, 18),
]
LINKS = [(0, 1), (0, 2), (1, 2)]
HEARTHS = (0, 3, 6, 9)


def _owner(node: int) -> int:
    return next(number for number, nodes in enumerate(LOCATIONS) if node in nodes)


def _societies(**changes: object) -> Societies:
    population = np.zeros(NODES, dtype=np.int64)
    religion = np.zeros(NODES, dtype=np.int64)
    zones = [0] * 3 + [1] * 3 + [2] * 3 + [3] * 12
    for node in range(NODES):
        number = _owner(node)
        population[node] = POPULATION[number] // len(LOCATIONS[number])
        religion[node] = zones[node]
    polities = tuple(
        Polity(TRIBE if 3 <= number <= 5 else STATE, nodes, nodes[0], number)
        for number, nodes in enumerate(LOCATIONS)
    )
    fields: dict[str, object] = {
        "complexity": np.full(NODES, 800, dtype=np.int64),
        "population": population,
        "peasants": population // 3,
        "religion": religion,
        "culture": np.arange(NODES, dtype=np.int64),
        "hearths": HEARTHS,
        "polities": polities,
        "ranks": {6: CITY},
        "markets": (6,),
    }
    fields.update(changes)
    return Societies(**fields)  # pyright: ignore[reportArgumentType]


def _graph() -> LandGraph:
    return LandGraph(
        capacity=np.full(NODES, 1000, dtype=np.int64),
        potential=np.full(NODES, 500, dtype=np.int64),
        cost=np.full(NODES, STEP_COST, dtype=np.int64),
        edges=np.array(EDGES, dtype=np.int64),
        links=np.array(LINKS, dtype=np.int64),
    )


def _cells() -> _Cells:
    return _Cells(
        cells=list(range(NODES)),
        climate=["tropical"] * NODES,
        vegetation=["forest"] * NODES,
        topography=["flatland"] * 3 + ["hills"] * 3 + ["flatland"] * (NODES - 6),
        latitude=[0] * NODES,
        coastal=[node < 3 for node in range(NODES)],
        seas=[[100] if node < 3 else [] for node in range(NODES)],
    )


def _countries() -> tuple[Country, ...]:
    return tuple(
        Country(
            tag=f"T{number:02d}",
            name=f"Place {number}",
            kind=TRIBE if 3 <= number <= 5 else STATE,
            members=tuple(f"loc{node}" for node in nodes),
            capital=f"loc{nodes[0]}",
            culture="c",
            religion="r",
            include="tribe_t" if 3 <= number <= 5 else "monarchy_t",
            areas=(f"area{nodes[0]}",),
            color=(1, 2, 3),
            color2=(3, 2, 1),
            government=(("type", "tribe"),) if 3 <= number <= 5 else (("type", "monarchy"),),
            level=None if 3 <= number <= 5 else 2,
        )
        for number, nodes in enumerate(LOCATIONS)
    )


def _apply(
    chance: int = 1000, *, calibration: ArchetypeCalibration | None = CALIBRATION, seed: int = 3
) -> tuple[_Varied, Societies]:
    societies = _societies()
    graph = _graph()
    return (
        _archetypes(
            societies,
            graph,
            _cells(),
            _vanilla(calibration),
            _countries(),
            near=_neighbours(societies, graph.edges),
            bound=set(),
            chance=chance,
            seed=seed,
        ),
        societies,
    )


def test_each_domain_gets_the_one_kind_it_allows() -> None:
    varied, _ = _apply()
    report = varied.report
    groups = cast("list[dict[str, object]]", report["groups"])
    assert sorted(str(group["kind"]) for group in groups) == sorted(
        [SEA_LEAGUE, HIGHLAND_CONFEDERATION, SACRED_CENTRE, FRACTURED_REALM]
    )
    assert report["options"] == {
        SEA_LEAGUE: 1,
        HIGHLAND_CONFEDERATION: 1,
        FRACTURED_REALM: 1,
        SACRED_CENTRE: 1,
    }
    assert {group["domain"] for group in groups} == {0, 1, 2, 3}
    for group in groups:
        assert group["causes"]
        assert group["weaknesses"]


def test_a_league_takes_the_republic_ranks_for_its_ports_and_a_ring_of_alliances() -> None:
    varied, before = _apply()
    countries = {country.tag: country for country in varied.countries}
    league = [c for c in varied.countries if c.archetype == SEA_LEAGUE]
    assert len(league) == 3
    for country in league:
        assert country.include == "republic_t"
        assert dict(country.government) == {
            "type": "republic",
            "heir_selection": "oligarchic_elective",
            "land_vs_naval": "60",
        }
    assert len(varied.alliances) == 3
    assert {tag for pair in varied.alliances for tag in pair} == {c.tag for c in league}
    assert varied.societies.ranks == {0: CITY, 1: TOWN, 2: TOWN, 3: TOWN, 6: CITY, 9: TOWN}
    assert varied.societies.markets == (6, 0, 9, 3)
    assert before.ranks == {6: CITY}
    assert countries[league[0].tag].landed is False


def test_a_confederation_owns_its_land_and_writes_the_confederates_currency() -> None:
    varied, _ = _apply()
    tribes = [c for c in varied.countries if c.archetype == HIGHLAND_CONFEDERATION]
    assert len(tribes) == 3
    assert all(c.landed and c.currency == CALIBRATION.cohesion for c in tribes)
    assert all(c.kind == TRIBE for c in tribes)
    assert [tuple(tag for tag in group) for group in varied.confederations] == [
        tuple(c.tag for c in tribes)
    ]
    assert [polity.landed for polity in varied.societies.polities[3:6]] == [True] * 3
    text = "countries = {\n\tcountries = {\n" + country_records(tuple(tribes)) + "\t}\n}\n"
    record = parse(text).block("countries", "countries", tribes[0].tag)
    assert record is not None
    assert record.first("type") is None
    assert record.block("own_control_core") is not None
    currency = record.block("currency_data")
    assert currency is not None
    assert [(entry.key, entry.value) for entry in currency.entries] == [
        ("gold", "100"),
        ("stability", "33"),
        ("tribal_cohesion", "90"),
    ]


def test_a_sacred_centre_is_a_theocracy_and_the_rival_of_its_competitors() -> None:
    varied, _ = _apply()
    centre = [c for c in varied.countries if c.archetype == SACRED_CENTRE]
    assert len(centre) == 3
    hub, *others = centre
    assert hub.include == ""
    record = parse(country_records((hub,))).block(hub.tag)
    assert record is not None
    assert record.first("include") is None
    level = record.first("starting_technology_level")
    assert level is not None
    assert level.value == str(hub.level)
    assert dict(hub.government) == {
        "type": "theocracy",
        "heir_selection": "theocratic_elective",
        "spiritualist_vs_humanist": "-90",
    }
    assert all(dict(c.government) == {"type": "monarchy"} for c in others)
    held = {(a, b) for a, b in varied.rivals if hub.tag in (a, b)}
    assert held == {(hub.tag, c.tag) for c in others} | {(c.tag, hub.tag) for c in others}


def test_a_fractured_realm_is_a_set_of_returned_rivalries_between_touching_centres() -> None:
    varied, _ = _apply()
    realm = {c.tag for c in varied.countries if c.archetype == FRACTURED_REALM}
    assert len(realm) == 4
    inside = {pair for pair in varied.rivals if set(pair) <= realm}
    assert len(inside) == 6
    assert all((b, a) in inside for a, b in inside)


def test_holders_of_a_relation_are_told_to_discover_their_partners_capitals() -> None:
    varied, _ = _apply()
    countries = varied.countries
    capitals = {c.tag: c.capital for c in countries}
    known: dict[str, set[str]] = {}
    for holder, partner in varied.pairs:
        known.setdefault(holder, set()).add(capitals[partner])
    assert known
    tribes = [c.tag for c in countries if c.archetype == HIGHLAND_CONFEDERATION]
    assert all(
        known[tag] == {capitals[other] for other in tribes if other != tag} for tag in tribes
    )
    aware = discover_areas(countries, {tag: frozenset(places) for tag, places in known.items()})
    assert all(not known.get(c.tag, set()) - set(c.areas) for c in aware)


def test_a_chance_of_nothing_changes_nothing() -> None:
    varied, societies = _apply(0)
    assert varied.countries == _countries()
    assert varied.societies.ranks == societies.ranks
    assert varied.societies.polities == societies.polities
    assert (varied.alliances, varied.rivals, varied.confederations, varied.pairs) == ((),) * 4
    assert varied.report["groups"] == []


def test_a_group_without_a_calibration_is_refused_and_no_group_needs_none() -> None:
    with pytest.raises(NativesError, match="No archetype calibration"):
        _ = _apply(calibration=None)
    varied, _ = _apply(0, calibration=None)
    assert varied.report == {}


def test_a_bound_polity_joins_no_group() -> None:
    societies = _societies()
    graph = _graph()
    near = _neighbours(societies, graph.edges)
    countries = _countries()
    free = archetype_structure(societies, graph, _cells(), countries, near=near, bound=set())
    bound = archetype_structure(societies, graph, _cells(), countries, near=near, bound={0})
    assert free.free[0]
    assert not bound.free[0]
    rules = Rules(level=2, density=0)
    league = [g for g in plan_archetypes(free, rules, chance=1000, seed=3) if g.kind == SEA_LEAGUE]
    assert len(league) == 1
    assert [
        g for g in plan_archetypes(bound, rules, chance=1000, seed=3) if g.kind == SEA_LEAGUE
    ] == []


def test_the_structure_reads_the_domains_ports_and_cradles() -> None:
    societies = _societies()
    graph = _graph()
    structure = archetype_structure(
        societies,
        graph,
        _cells(),
        _countries(),
        near=_neighbours(societies, graph.edges),
        bound=set(),
    )
    assert structure.domains == len(HEARTHS) + 1
    assert [structure.domain[n] for n in (0, 3, 6, 9)] == [0, 1, 2, 3]
    assert structure.ports[0] == {100: 0}
    assert structure.ports[3] == {}
    assert structure.highland[3] == 1000
    assert structure.highland[0] == 0
    assert structure.locations[9] == 3
    assert {0, 3, 6, 9} == set(structure.cradle) & {0, 3, 6, 9}
    assert structure.level[3] == -1
    assert structure.level[0] == 2


def test_unsupported_tribes_cannot_gain_land_through_a_confederation() -> None:
    societies = _societies()
    graph = _graph()
    societies.peasants[3:6] = 0
    varied = _archetypes(
        societies,
        graph,
        _cells(),
        _vanilla(CALIBRATION),
        _countries(),
        near=_neighbours(societies, graph.edges),
        bound=set(),
        chance=1000,
        seed=3,
    )
    assert not varied.confederations
    assert not any(p.landed for p in varied.societies.polities)
    assert any(c.archetype == SEA_LEAGUE for c in varied.countries)


def test_economic_validation_includes_landed_tribes_and_reports_isolation() -> None:
    societies = _societies()
    graph = _graph()
    near = _neighbours(societies, graph.edges)
    floor = StateFloor(peasants=100, share=100)
    report = state_economy(societies, near, floor)
    assert report["without_peasants"] == 0
    assert report["landed_countries"] == 10
    assert report["isolated_countries"] == 3
    polities = list(societies.polities)
    polities[3] = replace(polities[3], landed=True)
    societies = replace(societies, polities=tuple(polities))
    societies.peasants[3] = 0
    with pytest.raises(NativesError, match="lacks farming support"):
        _ = state_economy(societies, near, floor)
