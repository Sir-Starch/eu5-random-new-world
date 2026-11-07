"""Physical reuse must retain fresh state facts and complete independent replay equality."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw import history_context, history_engine
from rnw.history_checks import Index, validate_snapshot
from rnw.history_model import END, Cohort, HistoryError

from .history_fixtures import valley
from .reference.history_burden import per_place_burden
from .reference.history_contacts import unoptimized_contacts
from .reference.history_index import UncachedIndex
from .test_history_candidates import histories


def test_physical_reuse_never_reuses_population_or_ownership_from_a_prior_snapshot() -> None:
    history = valley()
    before = Index(history.geography, history.state, lambda: None)
    place = history.state.settlements[0]
    old_population, old_peasants = (
        before.population(place.district),
        before.peasants(place.district),
    )
    updated = replace(place, cohorts=(Cohort("new culture", "new faith", 213, 107),))
    holding = next(h for h in history.state.holdings if h.district == place.district)
    other = next(a.key for a in history.state.actors if a.living and a.key != holding.actor)
    state = replace(
        history.state,
        settlements=(updated, *history.state.settlements[1:]),
        holdings=tuple(
            replace(h, actor=other) if h is holding else h for h in history.state.holdings
        ),
    )
    after = Index(history.geography, state, lambda: None, physical=before)
    reference = UncachedIndex(history.geography, state, lambda: None)
    assert (after.population(place.district), after.peasants(place.district)) == (213, 107)
    assert (before.population(place.district), before.peasants(place.district)) == (
        old_population,
        old_peasants,
    )
    assert after.owner == reference.owner
    assert after.owner[place.district] == other
    assert before.owner[place.district] == holding.actor
    assert after.members == reference.members
    assert after.adjacency == reference.adjacency
    assert after.capacities == reference.capacities
    assert after.settlements == reference.settlements
    assert all(after.population(key) == reference.population(key) for key in after.settlements)


def test_reusing_an_index_for_different_physical_inputs_fails_explicitly() -> None:
    history = valley()
    before = Index(history.geography, history.state, lambda: None)
    different = replace(history.geography, routes=())
    with pytest.raises(HistoryError, match="Different indexed geography"):
        _ = Index(different, history.state, lambda: None, physical=before)


@pytest.mark.parametrize("turbulence", [0, 200, 500, 800, 1000])
def test_uncached_reference_retains_every_round_event_effect_and_replayed_fact(
    turbulence: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    for initial in histories():
        result = history_engine.simulate(initial, turbulence=turbulence)
        history_engine.validate_history(result)
        with monkeypatch.context() as patch:
            patch.setattr(history_context, "Index", UncachedIndex)
            patch.setattr(history_engine, "Index", UncachedIndex)
            patch.setattr(history_context.Context, "_contacts", unoptimized_contacts)
            reference = history_engine.simulate(initial, turbulence=turbulence)
            history_engine.validate_history(reference)
        assert reference == result


def test_all_contact_types_and_single_intermediary_costs_equal_the_original_calculation() -> None:
    for initial in histories():
        for history in (initial, history_engine.simulate(initial)):
            fast = history_context.Context(history, lambda: None)
            reference = history_context.Context(history, lambda: None)
            unoptimized_contacts(reference)
            assert fast.near == reference.near
            assert fast.land_near == reference.land_near
            assert fast.sea_near == reference.sea_near
            assert fast.reach == reference.reach


def test_one_search_gives_each_place_its_frontier_distance() -> None:
    """``travel`` equals ``distance`` to every held and passed place, unreached included."""
    for initial in histories():
        history = history_engine.simulate(initial)
        context = history_context.Context(history, lambda: None)
        for actor in history.state.actors:
            if not actor.living:
                continue
            held = context.index.members[actor.key]
            beside = sorted(
                {other for key in held for other in context.index.adjacency[key]} - held
            )
            for through in ((), tuple(beside[:2])):
                travel = context.travel(actor.key, through)
                for key in sorted(held | set(through)):
                    assert travel.get(key, 1 << 60) == context.distance(actor.key, key, through)


@pytest.mark.parametrize("turbulence", [200, 500, 800])
def test_burden_from_one_search_equals_one_search_per_place(
    turbulence: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    for initial in histories():
        result = history_engine.simulate(initial, turbulence=turbulence)
        with monkeypatch.context() as patch:
            patch.setattr(history_context, "_burden", per_place_burden)
            reference = history_engine.simulate(initial, turbulence=turbulence)
        assert reference == result


def test_a_later_round_extends_the_event_tables_of_the_earlier_one() -> None:
    for initial in histories():
        history, previous = initial, None
        while history.state.year < END:
            fresh = history_context.Context(history, lambda: None)
            extended = history_context.Context(history, lambda: None, previous=previous)
            assert extended.event_years == fresh.event_years
            assert extended.event_kinds == fresh.event_kinds
            assert extended.events == fresh.events
            assert {key: events for key, events in extended.experiences.items() if events} == {
                key: events for key, events in fresh.experiences.items() if events
            }
            history = history_engine.advance(history, history_engine.propose(extended))
            previous = extended


def test_a_settlement_found_valid_is_checked_again_once_it_is_replaced() -> None:
    history = valley()
    first = Index(history.geography, history.state, lambda: None)
    validate_snapshot(first, history.state)
    place = history.state.settlements[0]
    emptied = replace(place, cause="")
    state = replace(history.state, settlements=(emptied, *history.state.settlements[1:]))
    with pytest.raises(HistoryError, match="Unexplained/empty settlement"):
        validate_snapshot(Index(history.geography, state, lambda: None, physical=first), state)
    # The unchanged snapshot is still accepted on the shared index.
    again = Index(history.geography, history.state, lambda: None, physical=first)
    validate_snapshot(again, history.state)
