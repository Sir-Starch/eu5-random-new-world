"""Physical reuse must retain fresh state facts and complete independent replay equality."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw import history_context, history_engine
from rnw.history_checks import Index
from rnw.history_model import Cohort, HistoryError

from .history_fixtures import valley
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
