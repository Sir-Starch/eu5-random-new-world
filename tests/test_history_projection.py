"""H4 bootstrap and typed population at the actual society/history boundary."""

# NumPy stubs type conversions as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_history import (
    BootstrapInputs,
    HistoryBootstrap,
    bootstrap_history,
    canonical_population,
    identity_cohorts,
)
from rnw.eu5_natives import _pop_cohorts  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_start import PopCohort
from rnw.history_engine import create, digest, simulate, validate_history
from rnw.history_model import (
    Action,
    Cohort,
    HistoryError,
    Movement,
    Outcome,
    Proposal,
    Route,
    Rules,
    Society,
    Tenure,
)
from rnw.history_population import project_population
from rnw.history_routes import PhysicalMap, physical_routes, routed_graph
from rnw.model import CellClass
from rnw.settings import NATIVES
from rnw.societies import LandGraph, Polity, Societies, StateFloor, bootstrap_societies

from .history_fixtures import valley, valley_policy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.history_context import Context


def boundary() -> BootstrapInputs:
    keys = ("a0", "a1", "b0", "b1", "t0", "t1", "c0", "c1", "empty")
    edges = ((0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8))
    graph = LandGraph(
        np.full(9, 5000, dtype=np.int64),
        np.array([100, *([1000] * 8)], dtype=np.int64),
        np.full(9, 1000, dtype=np.int64),
        np.array(edges, dtype=np.int64),
        np.empty((0, 2), dtype=np.int64),
        coastal=np.zeros(9, dtype=np.bool_),
    )
    society = Societies(
        np.full(9, 750, dtype=np.int64),
        np.array([*([2000] * 8), 0], dtype=np.int64),
        np.array([*([1000] * 8), 0], dtype=np.int64),
        np.zeros(9, dtype=np.int64),
        np.zeros(9, dtype=np.int64),
        (0,),
        (
            Polity("state", (0, 1), 0, 0),
            Polity("state", (2, 3), 2, 0),
            Polity("tribe", (4, 5), 4, 0),
        ),
        {0: "town"},
        (0,),
    )
    pops: dict[str, tuple[PopCohort, ...]] = {
        key: (
            PopCohort("peasants", 1000, "people", "faith"),
            PopCohort("tribesmen", 700, "people", "faith"),
            PopCohort("clergy", 200, "people", "faith"),
            PopCohort("nobles", 100, "people", "faith"),
        )
        for key in keys[:-1]
    }
    # The actual native writer adds peasant diasporas in state land and tribesmen
    # elsewhere; both additions, including farmers, enter history's initial budget.
    pops["a0"] = (*pops["a0"], PopCohort("peasants", 50, "diaspora", "other_faith"))
    pops["c0"] = (*pops["c0"], PopCohort("tribesmen", 50, "other_people", "faith"))
    return BootstrapInputs(
        graph,
        society,
        keys,
        dict.fromkeys(keys, "region"),
        pops,
        {"a0": 2, "b0": 1, "t0": 0},
        tuple(Route(keys[a], keys[b]) for a, b in edges),
        Rules(minimum_peasants=338, minimum_share=122),
        highland=("t0", "t1"),
        sacred=("b1",),
    )


def prepared() -> HistoryBootstrap:
    result = bootstrap_history(boundary(), seed=42, empire_permille=0)
    roots = tuple(
        replace(founding, society=Society(authority=founding.authority, integration=700))
        for founding in result.history.foundings
    )
    return replace(
        result, history=create(result.history.geography, roots, seed=42, empire_permille=0)
    )


def migration_policy(context: Context) -> tuple[Proposal, ...]:
    if context.state.year == 1037:
        return (Proposal(Action.CONTACT, "polity:a0", "polity:b0"),)
    if context.state.year == 1042:
        pop = Cohort("diaspora", "other_faith", 5, 5)
    elif context.state.year == 1047:
        pop = Cohort("people", "faith", 200, 100)
    else:
        return ()
    return (
        Proposal(
            Action.MIGRATION,
            "polity:a0",
            "polity:b0",
            movement=Movement("a0", "b0", pop),
        ),
    )


def budget(pops: Mapping[str, Sequence[PopCohort]]) -> Counter[tuple[str, str, str]]:
    result: Counter[tuple[str, str, str]] = Counter()
    for rows in pops.values():
        for pop in rows:
            result[pop.kind, pop.culture, pop.religion] += pop.amount
    return result


def test_bootstrap_covers_the_fixed_envelope_after_all_diasporas() -> None:
    root = bootstrap_history(boundary(), seed=42, empire_permille=0)
    history = root.history
    assert root.calibrated_population == 16_000
    assert root.diaspora_population == 100
    assert sum(place.population for place in history.geography.districts) == 16_100
    assert sum(place.peasants for place in history.geography.districts) == 8050
    assert {f.tenure for f in history.foundings} == {Tenure.LAND, Tenure.TRIBE, Tenure.COMMUNITY}
    assert next(f for f in history.foundings if f.tenure is Tenure.COMMUNITY).districts == (
        "c0",
        "c1",
    )
    assert {h.district for h in history.state.holdings} == set(boundary().keys) - {"empty"}
    assert all(event.kind is Action.FOUNDATION for event in history.events)
    assert not history.state.bonds
    assert not history.state.knowledge
    assert all(
        actor.technology == 0 for actor in history.state.actors if actor.tenure is Tenure.COMMUNITY
    )
    assert project_population(root, history) == dict(root.pops)
    validate_history(history)


def test_headroom_is_food_opportunity_not_donor_identity() -> None:
    inputs = boundary()
    first = bootstrap_history(inputs, seed=42, empire_permille=0)
    places = {p.key: p for p in first.history.geography.districts}
    assert places["a0"].headroom == 51
    assert places["b0"].headroom == 500
    assert places["empty"].headroom == 0
    assert places["b1"].sacred
    assert places["t0"].highland
    changed = replace(
        inputs,
        pops={
            key: tuple(
                replace(pop, culture="another_culture", religion="another_faith") for pop in rows
            )
            for key, rows in inputs.pops.items()
        },
    )
    second = bootstrap_history(changed, seed=42, empire_permille=0)
    assert [(p.key, p.headroom, p.defence) for p in first.history.geography.districts] == [
        (p.key, p.headroom, p.defence) for p in second.history.geography.districts
    ]
    assert [(a.key, a.authority) for a in first.history.state.actors] == [
        (a.key, a.authority) for a in second.history.state.actors
    ]


def test_bootstrap_input_order_does_not_choose_a_different_history() -> None:
    inputs = boundary()
    expected = bootstrap_history(inputs, seed=42, empire_permille=1000)
    shuffled = replace(
        inputs,
        pops={key: tuple(reversed(rows)) for key, rows in reversed(tuple(inputs.pops.items()))},
        societies=replace(inputs.societies, polities=tuple(reversed(inputs.societies.polities))),
        routes=tuple(replace(r, first=r.second, second=r.first) for r in reversed(inputs.routes)),
    )
    actual = bootstrap_history(shuffled, seed=42, empire_permille=1000)
    assert actual.pops == expected.pops
    assert digest(actual.history) == digest(expected.history)


def bad_polity(inputs: BootstrapInputs, defect: str) -> BootstrapInputs:
    first, *rest = inputs.societies.polities
    if defect == "polity":
        first = replace(first, capital=9999)
    elif defect == "overlap":
        first = replace(first, members=(*first.members, 2))
    elif defect == "empire":
        first = replace(first, great=True)
    else:
        first = replace(first, landed=True)
    return replace(inputs, societies=replace(inputs.societies, polities=(first, *rest)))


@pytest.mark.parametrize(
    "defect",
    [
        "population",
        "farmers",
        "technology",
        "polity",
        "overlap",
        "empire",
        "landed",
        "region",
        "unknown_empty_population",
        "coast",
        "route",
        "passage",
        "hearth",
        "food",
    ],
)
def test_invalid_bootstrap_is_rejected_explicitly(defect: str) -> None:
    inputs = boundary()
    if defect == "population":
        inputs = replace(
            inputs, pops={key: rows for key, rows in inputs.pops.items() if key != "a0"}
        )
    elif defect == "farmers":
        inputs = replace(
            inputs,
            pops={
                key: tuple(
                    replace(pop, kind="tribesmen") if pop.kind == "peasants" else pop
                    for pop in rows
                )
                for key, rows in inputs.pops.items()
            },
        )
    elif defect == "technology":
        inputs = replace(inputs, technology={})
    elif defect in {"polity", "overlap", "empire", "landed"}:
        inputs = bad_polity(inputs, defect)
    elif defect == "region":
        inputs = replace(inputs, regions={})
    elif defect == "unknown_empty_population":
        inputs = replace(inputs, pops={**inputs.pops, "unknown": ()})
    elif defect == "coast":
        inputs = replace(inputs, graph=replace(inputs.graph, coastal=np.zeros(1, dtype=np.bool_)))
    elif defect == "route":
        inputs = replace(inputs, routes=inputs.routes[:-1])
    elif defect == "passage":
        inputs = replace(inputs, routes=(*inputs.routes, Route("a0", "c1", 10_000, 5)))
    elif defect == "hearth":
        inputs = replace(inputs, societies=replace(inputs.societies, hearths=(9999,)))
    elif defect == "food":
        inputs.graph.potential[0] = 1001
    with pytest.raises(HistoryError):
        _ = bootstrap_history(inputs, seed=42, empire_permille=0)


@pytest.mark.parametrize(
    "pop",
    [
        PopCohort("peasants", -1, "people", "faith"),
        PopCohort("", 1, "people", "faith"),
        PopCohort("peasants", 1, "", "faith"),
        PopCohort("peasants", 0, "people", "faith"),
    ],
)
def test_invalid_typed_population_is_not_dropped(pop: PopCohort) -> None:
    with pytest.raises(HistoryError, match="Invalid typed population"):
        _ = canonical_population({"place": (pop,)})


def test_population_projection_preserves_elites_farmers_and_both_diasporas() -> None:
    root = prepared()
    history = simulate(root.history, policy=migration_policy)
    validate_history(history)
    moves = [event for event in history.events if event.kind is Action.MIGRATION]
    assert len(moves) == 2
    assert all(e.outcome is Outcome.ACCEPTED for e in moves)
    final = project_population(root, history)
    assert budget(final) == budget(dict(root.pops))
    assert PopCohort("peasants", 5, "diaspora", "other_faith") in final["b0"]
    assert PopCohort("clergy", 220, "people", "faith") in final["b0"]
    assert PopCohort("nobles", 110, "people", "faith") in final["b0"]
    assert PopCohort("tribesmen", 770, "people", "faith") in final["b0"]
    assert final["c0"] == dict(root.pops)["c0"]
    assert {key: identity_cohorts(rows) for key, rows in final.items()} == {
        place.district: place.cohorts for place in history.state.settlements
    }


def test_largest_remainder_rounding_preserves_every_nonfarmer_type() -> None:
    inputs = boundary()
    pops = dict(inputs.pops)
    pops["a0"] = (
        PopCohort("peasants", 1000, "people", "faith"),
        PopCohort("tribesmen", 334, "people", "faith"),
        PopCohort("clergy", 333, "people", "faith"),
        PopCohort("nobles", 333, "people", "faith"),
    )
    root = bootstrap_history(replace(inputs, pops=pops), seed=42, empire_permille=0)

    def policy(context: Context) -> tuple[Proposal, ...]:
        if context.state.year == 1042:
            return (
                Proposal(
                    Action.MIGRATION,
                    "polity:a0",
                    "polity:b0",
                    movement=Movement(
                        "a0",
                        "b0",
                        Cohort("people", "faith", 151, 75),
                    ),
                ),
            )
        return migration_policy(context) if context.state.year == 1037 else ()

    history = simulate(root.history, policy=policy)
    assert next(e for e in history.events if e.kind is Action.MIGRATION).outcome is Outcome.ACCEPTED
    final = project_population(root, history)
    assert PopCohort("tribesmen", 726, "people", "faith") in final["b0"]
    assert PopCohort("clergy", 225, "people", "faith") in final["b0"]
    assert PopCohort("nobles", 125, "people", "faith") in final["b0"]
    assert budget(final) == budget(dict(root.pops))


def test_population_projection_rejects_another_bootstrap_and_tampered_final() -> None:
    root = prepared()
    history = simulate(root.history, policy=migration_policy)
    with pytest.raises(HistoryError, match="different bootstrap"):
        _ = project_population(root, replace(history, seed=77))
    settlement, *rest = history.state.settlements
    changed = replace(settlement, cohorts=(replace(settlement.cohorts[0], population=99),))
    with pytest.raises(HistoryError, match="final history"):
        _ = project_population(
            root, replace(history, state=replace(history.state, settlements=(changed, *rest)))
        )


def test_union_division_and_conquest_never_retype_the_inhabitants() -> None:
    initial = valley()
    pops = {
        place.key: (
            PopCohort("peasants", place.peasants, "valley_people", "river_faith"),
            PopCohort("clergy", 25, "valley_people", "river_faith"),
            PopCohort(
                "tribesmen", place.population - place.peasants - 25, "valley_people", "river_faith"
            ),
        )
        for place in initial.geography.districts
    }
    root = HistoryBootstrap(initial, canonical_population(pops), 13_000, 0)
    history = simulate(initial, policy=valley_policy)
    assert any(event.effects.retired for event in history.events)
    assert any(
        event.kind is Action.CONFLICT and event.effects.transfers for event in history.events
    )
    assert project_population(root, history) == dict(root.pops)


@pytest.mark.parametrize("defect", ["duplicate", "conservation", "cause", "nonmigration"])
def test_population_projection_checks_the_effects_it_consumes(defect: str) -> None:
    root = prepared()
    history = simulate(root.history, policy=migration_policy)
    events = list(history.events)
    number = next(i for i, event in enumerate(events) if event.kind is Action.MIGRATION)
    event = events[number]
    first, second = event.effects.settlements
    if defect == "duplicate":
        changed = (first, first)
    elif defect == "conservation":
        pop, *rest = first.cohorts
        changed = (
            replace(first, cohorts=(replace(pop, population=pop.population + 1), *rest)),
            second,
        )
    elif defect == "cause":
        changed = (replace(first, cause="invented"), second)
    else:
        changed = (first, second)
        event = replace(event, kind=Action.REFORM)
    events[number] = replace(event, effects=replace(event.effects, settlements=changed))
    with pytest.raises(HistoryError):
        _ = project_population(root, replace(history, events=tuple(events)))


@pytest.mark.parametrize("defect", ["missing", "duplicate", "notland", "edge", "cost", "bound"])
def test_invalid_physical_maps_are_rejected(defect: str) -> None:
    physical = PhysicalMap(
        ("a", "b"), (0, 1), (1000, 1000), (CellClass.LAND, CellClass.LAND), ((0, 1),)
    )
    if defect == "missing":
        physical = replace(physical, keys=("a",), cells=(0,), costs=(1000,))
    elif defect == "duplicate":
        physical = replace(physical, cells=(0, 0))
    elif defect == "notland":
        physical = replace(physical, classes=(CellClass.LAND, CellClass.SEA))
    elif defect == "edge":
        physical = replace(physical, edges=((0, 99),))
    elif defect == "cost":
        physical = replace(physical, costs=(0, 1000))
    with pytest.raises(HistoryError):
        _ = physical_routes(physical, max_sea_steps=-1 if defect == "bound" else 4)


def test_physical_passages_count_water_cells_and_respect_wrap_edges() -> None:
    # 0--sea--sea--1--2 is two wet cells; 2--four seas--3 needs four.
    # 0--lake--4 cannot make maritime contact. 4--5 is an explicit seam edge.
    classes = (CellClass.LAND,) * 6 + (CellClass.SEA,) * 6 + (CellClass.LAKE,)
    edges = (
        (0, 6),
        (6, 7),
        (7, 1),
        (1, 2),
        (2, 8),
        (8, 9),
        (9, 10),
        (10, 11),
        (11, 3),
        (0, 12),
        (12, 4),
        (4, 5),
    )
    physical = PhysicalMap(tuple("abcdef"), tuple(range(6)), (1000,) * 6, classes, edges)
    routes = physical_routes(physical)
    by_pair = {(r.first, r.second): r for r in routes}
    assert by_pair["a", "b"].sea_steps == 2
    assert by_pair["c", "d"].sea_steps == 4
    assert by_pair["b", "c"].sea_steps == 0
    assert by_pair["e", "f"].sea_steps == 0
    assert ("a", "e") not in by_pair
    assert ("a", "c") not in by_pair  # Cannot cross land as if it were water.
    assert (
        physical_routes(replace(physical, edges=tuple((b, a) for a, b in reversed(edges))))
        == routes
    )
    assert ("c", "d") not in {
        (r.first, r.second) for r in physical_routes(physical, max_sea_steps=3)
    }
    assert all(r.sea_steps == 0 for r in physical_routes(physical, max_sea_steps=0))


def test_routes_choose_shortest_passage_and_prefer_direct_land() -> None:
    physical = PhysicalMap(
        ("a", "b"),
        (0, 1),
        (1000, 2000),
        (CellClass.LAND, CellClass.LAND, CellClass.SEA, CellClass.SEA),
        ((0, 2), (2, 3), (3, 1), (2, 1)),
    )
    (route,) = physical_routes(physical)
    assert (route.sea_steps, route.cost) == (1, 4500)
    (route,) = physical_routes(replace(physical, edges=(*physical.edges, (0, 1))))
    assert (route.sea_steps, route.cost) == (0, 1500)


def test_bootstrap_discards_unverified_shared_water_links_before_construction() -> None:
    inputs = boundary()
    graph = replace(inputs.graph, links=np.array([[0, 8]], dtype=np.int64))
    routed = routed_graph(graph, inputs.keys, inputs.routes)
    assert len(routed.links) == 0
    assert len(graph.links) == 1  # Existing inputs are not mutated.
    with pytest.raises(HistoryError, match="land routes differ"):
        _ = routed_graph(graph, inputs.keys, inputs.routes[:-1])


def test_coastal_passages_are_available_to_bootstrap_and_history() -> None:
    inputs = boundary()
    physical = PhysicalMap(
        inputs.keys,
        tuple(range(9)),
        tuple(inputs.graph.cost.tolist()),
        (CellClass.LAND,) * 9 + (CellClass.SEA,),
        (*tuple((int(a), int(b)) for a, b in inputs.graph.edges), (0, 9), (9, 7)),
    )
    routes = physical_routes(physical)
    coast = (
        inputs.graph.coastal.copy()
        if inputs.graph.coastal is not None
        else np.zeros(9, dtype=np.bool_)
    )
    coast[[0, 7]] = True
    graph = routed_graph(replace(inputs.graph, coastal=coast), inputs.keys, routes)
    assert graph.links.tolist() == [[0, 7]]
    root = bootstrap_history(
        replace(inputs, graph=graph, routes=routes), seed=42, empire_permille=0
    )
    assert Route("a0", "c1", 4000, 1) in root.history.geography.routes


def test_route_and_bootstrap_cancellation_propagates() -> None:
    def cancelled() -> None:
        message = "cancelled"
        raise InterruptedError(message)

    with pytest.raises(InterruptedError):
        _ = physical_routes(
            PhysicalMap(
                ("a", "b"), (0, 1), (1000, 1000), (CellClass.LAND, CellClass.LAND), ((0, 1),)
            ),
            checkpoint=cancelled,
        )
    with pytest.raises(InterruptedError):
        _ = bootstrap_history(boundary(), seed=42, empire_permille=0, checkpoint=cancelled)
    root = prepared()
    with pytest.raises(InterruptedError):
        _ = project_population(root, root.history, checkpoint=cancelled)


def test_constructed_societies_run_through_history_and_typed_projection() -> None:
    count, side = 256, 16
    keys = tuple(f"place_{node:03}" for node in range(count))
    edges = tuple(
        (node, node + step)
        for node in range(count)
        for step in (1, side)
        if (step == 1 and node % side < side - 1) or (step == side and node + step < count)
    )
    physical = PhysicalMap(
        keys, tuple(range(count)), (1000,) * count, (CellClass.LAND,) * count, edges
    )
    routes = physical_routes(physical)
    graph = LandGraph(
        np.full(count, 5000, dtype=np.int64),
        np.full(count, 900, dtype=np.int64),
        np.full(count, 1000, dtype=np.int64),
        np.array(edges, dtype=np.int64),
        np.empty((0, 2), dtype=np.int64),
        coastal=np.zeros(count, dtype=np.bool_),
    )
    graph = routed_graph(graph, keys, routes)
    settings = replace(
        NATIVES,
        hearths_per_10k=80,
        state_share_permille=300,
        empire_permille=1000,
        culture_locations=8,
        religion_locations=40,
    )
    societies = bootstrap_societies(
        graph, settings, seed=42, target=1_000_000, state_floor=StateFloor(338, 122)
    )
    cultures = [f"people_{zone}" for zone in range(int(societies.culture.max()) + 1)]
    religions = [f"faith_{zone}" for zone in range(int(societies.religion.max()) + 1)]
    pops = _pop_cohorts(societies, list(keys), religions, cultures)
    first = min(pops)
    pops[first].append(PopCohort("tribesmen", 50, "diaspora", "other_faith"))
    inputs = BootstrapInputs(
        graph,
        societies,
        keys,
        dict.fromkeys(keys, "region"),
        pops,
        {keys[p.capital]: 2 if p.kind == "state" else 0 for p in societies.polities},
        routes,
        Rules(minimum_peasants=338, minimum_share=122),
    )
    root = bootstrap_history(inputs, seed=42, empire_permille=1000)
    history = simulate(root.history)
    validate_history(history)
    final = project_population(root, history)
    assert history.state.year == 1337
    assert root.diaspora_population == 50
    assert budget(final) == budget(pops)
    places = {place.key: place.tenure for place in history.geography.districts}
    actors = {actor.key: actor for actor in history.state.actors}
    assert all(places[h.district] == actors[h.actor].tenure for h in history.state.holdings)
