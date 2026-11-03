"""H2: causal outcomes, invalid inputs, replay and deterministic arbitration."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from rnw.history_engine import advance, create, digest, simulate, validate_history
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Factor,
    Founding,
    Geography,
    History,
    HistoryError,
    Outcome,
    Proposal,
    Reason,
    Route,
    Rules,
    Tenure,
)
from rnw.progress import Cancelled

from .history_fixtures import divided_valley, valley, valley_policy


def _line(*, count: int = 3, seed: int = 42) -> History:
    districts = tuple(
        District(
            str(n),
            "plain",
            Tenure.LAND,
            (Cohort("culture", "faith", 1000 * (n + 1), 500 * (n + 1)),),
        )
        for n in range(count)
    )
    geography = Geography(districts, tuple(Route(str(n), str(n + 1)) for n in range(count - 1)))
    return create(
        geography,
        tuple(Founding(f"a{n}", Tenure.LAND, (str(n),), str(n)) for n in range(count)),
        seed=seed,
    )


def test_divided_valley_reproduces_the_accepted_causal_story() -> None:
    history = divided_valley()
    assert history.state.year == 1337
    assert len(history.rounds) == 60
    assert len(history.events) == 21
    assert all(event.outcome is Outcome.ACCEPTED for event in history.events)
    unions = [event for event in history.events if event.kind is Action.UNION]
    assert [event.year for event in unions] == [1087, 1112]
    divided = next(event for event in history.events if event.kind is Action.SEPARATION)
    assert divided.year == 1227
    assert unions[-1].key in divided.causes
    living = {actor.seat: actor for actor in history.state.actors if actor.living}
    assert set(living) == {"u0", "m0", "d0"}
    assert {actor.parents for actor in living.values()} == {(divided.actors[0],)}
    assert {actor.authority for actor in living.values()} == {
        Authority.RULER,
        Authority.CUSTOMARY,
        Authority.SACRED,
    }
    assert (
        next(holding.actor for holding in history.state.holdings if holding.district == "u1")
        == living["d0"].key
    )
    grievance = next(
        memory
        for memory in history.state.memories
        if (
            memory.first == living["u0"].key
            and memory.second == living["d0"].key
            and memory.factor is Factor.GRIEVANCE
        )
    )
    assert grievance.year == 1282
    assert grievance.at(1281) == 0
    assert grievance.at(1337) == 165
    assert grievance.at(1600) == 0
    assert not any(
        memory.first == living["d0"].key
        and memory.second == living["u0"].key
        and memory.factor is Factor.GRIEVANCE
        for memory in history.state.memories
    )
    access = next(bond for bond in history.state.bonds if bond.kind is Action.ACCESS)
    assert (access.first, access.second, access.place) == (living["m0"].key, living["d0"].key, "d1")
    assert next(event.year for event in history.events if event.key == access.cause) == 1317
    assert history.geography.districts == valley().geography.districts
    validate_history(history)
    assert digest(history) == "087c98c431878ebcb82146211056fb9ec3978fe9c418cd7d21be40ca6f56219c"


def test_every_round_uses_the_prior_snapshot_and_is_atomic() -> None:
    history = _line()
    original = history
    result = advance(
        history,
        (
            Proposal(Action.CONTACT, "a0", "a1"),
            Proposal(Action.EXCHANGE, "a0", "a1", rank=1),
        ),
    )
    exchange = next(event for event in result.events if event.kind is Action.EXCHANGE)
    assert exchange.outcome is Outcome.REFUSED
    assert exchange.reason is Reason.UNKNOWN
    assert history == original
    assert not result.state.bonds
    result = advance(result, (Proposal(Action.EXCHANGE, "a0", "a1"),))
    assert result.state.bonds[0].kind is Action.EXCHANGE
    validate_history(result)


def test_union_requires_recorded_cooperation() -> None:
    history = _line()
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    history = advance(history, (Proposal(Action.UNION, "a0", "a1"),))
    assert history.events[-1].outcome is Outcome.REFUSED
    assert history.events[-1].reason is Reason.BARGAIN
    assert sum(actor.living for actor in history.state.actors) == 3


def test_shared_sea_labels_are_not_access_and_sea_steps_are_bounded() -> None:
    history = _line(count=2)
    districts = tuple(replace(place, coastal=True) for place in history.geography.districts)
    geography = replace(
        history.geography, districts=districts, routes=(Route("0", "1", sea_steps=5),)
    )
    history = create(geography, history.foundings, seed=42)
    result = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    assert result.events[-1].reason is Reason.UNREACHABLE
    assert not result.state.knowledge
    geography = replace(geography, routes=(Route("0", "1", sea_steps=4),))
    history = advance(
        create(geography, history.foundings, seed=42), (Proposal(Action.CONTACT, "a0", "a1"),)
    )
    assert len(history.state.knowledge) == 2
    with pytest.raises(HistoryError, match="coasts"):
        _ = create(
            replace(geography, districts=_line(count=2).geography.districts),
            history.foundings,
            seed=42,
        )


def test_exchange_reaches_a_partner_only_over_an_existing_physical_corridor() -> None:
    history = _line()
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    history = advance(history, (Proposal(Action.EXCHANGE, "a0", "a1"),))
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a2"),))
    assert history.events[-1].outcome is Outcome.ACCEPTED
    validate_history(history)


def test_conflicting_annexations_reserve_the_victim_once() -> None:
    history = _line()
    districts = tuple(
        replace(
            place, cohorts=(Cohort("culture", "faith", 10_000 if place.key != "1" else 100, 50),)
        )
        for place in history.geography.districts
    )
    history = create(replace(history.geography, districts=districts), history.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a0", "a1"), Proposal(Action.CONTACT, "a2", "a1"))
    )
    proposals = (
        Proposal(Action.CONFLICT, "a0", "a1", ("1",)),
        Proposal(Action.CONFLICT, "a2", "a1", ("1",)),
    )
    first = advance(history, proposals)
    second = advance(history, tuple(reversed(proposals)))
    assert digest(first) == digest(second)
    events = first.events[-2:]
    assert sum(event.outcome is Outcome.ACCEPTED for event in events) == 1
    assert sum(event.reason is Reason.COMMITTED for event in events) == 1
    assert not next(actor for actor in first.state.actors if actor.key == "a1").living
    validate_history(first)


def test_failed_attack_records_a_different_memory_without_transfer() -> None:
    history = _line(count=2)
    places = tuple(
        replace(place, defence=100_000 if place.key == "0" else 1000)
        for place in history.geography.districts
    )
    history = create(replace(history.geography, districts=places), history.foundings, seed=42)
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    before = history.state.holdings
    history = advance(history, (Proposal(Action.CONFLICT, "a1", "a0", ("0",)),))
    assert history.events[-1].outcome is Outcome.FAILED
    assert history.events[-1].reason is Reason.REPELLED
    assert history.state.holdings == before
    assert any(
        memory.first == "a1" and memory.second == "a0" and memory.factor is Factor.FEAR
        for memory in history.state.memories
    )
    validate_history(history)


def test_dependency_needs_knowledge_imbalance_and_a_capable_lord() -> None:
    history = _line(count=2)
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    history = advance(history, (Proposal(Action.DEPENDENCY, "a0", "a1"),))
    assert history.state.bonds[0].kind is Action.DEPENDENCY
    assert history.state.bonds[0].first == "a0"
    history = advance(history, (Proposal(Action.DEPENDENCY, "a1", "a0"),))
    assert history.events[-1].outcome is Outcome.REFUSED
    validate_history(history)


def test_overlord_can_fight_with_reachable_subject_support() -> None:
    history = _line()
    places = tuple(
        replace(place, cohorts=(Cohort("c", "r", 4000 if place.key == "1" else 1000, 500),))
        for place in history.geography.districts
    )
    history = create(replace(history.geography, districts=places), history.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a0", "a1"), Proposal(Action.CONTACT, "a1", "a2"))
    )
    history = advance(history, (Proposal(Action.DEPENDENCY, "a0", "a1"),))
    history = advance(history, (Proposal(Action.CONFLICT, "a1", "a2", ("2",)),))
    battle = history.events[-1]
    assert battle.outcome is Outcome.ACCEPTED
    assert dict(battle.commitments)["a0"] == 300
    assert (
        next(bond.cause for bond in history.state.bonds if bond.kind is Action.DEPENDENCY)
        in battle.causes
    )
    validate_history(history)


@pytest.mark.parametrize("tamper", ["cause", "holding", "bond", "memory", "outcome", "founding"])
def test_replay_rejects_unexplained_or_contradictory_facts(tamper: str) -> None:
    history = divided_valley()
    state = history.state
    if tamper == "cause":
        event = replace(history.events[-1], causes=(history.events[-1].key,))
        history = replace(history, events=(*history.events[:-1], event))
    elif tamper == "holding":
        state = replace(
            state, holdings=(replace(state.holdings[0], cause="invented"), *state.holdings[1:])
        )
    elif tamper == "bond":
        state = replace(state, bonds=(replace(state.bonds[0], second=state.bonds[0].first),))
    elif tamper == "memory":
        state = replace(
            state, memories=(replace(state.memories[0], weight=999), *state.memories[1:])
        )
    elif tamper == "outcome":
        event = replace(history.events[-1], outcome=Outcome.REFUSED)
        history = replace(history, events=(*history.events[:-1], event))
    else:
        history = replace(
            history,
            foundings=tuple(replace(founding, technology=9) for founding in history.foundings),
        )
    history = replace(history, state=state)
    with pytest.raises(HistoryError):
        validate_history(history)


@pytest.mark.parametrize("seed", [3, 7, 42, 77, 1000])
@pytest.mark.parametrize("turbulence", [0, 500, 1000])
def test_autonomous_history_is_deterministic_and_respects_commitments(
    seed: int, turbulence: int
) -> None:
    history = _line(count=12, seed=seed)
    original = history.geography
    result = simulate(history, turbulence=turbulence)
    permuted = create(
        replace(
            original,
            districts=tuple(reversed(original.districts)),
            routes=tuple(
                replace(route, first=route.second, second=route.first)
                for route in reversed(original.routes)
            ),
        ),
        tuple(reversed(history.foundings)),
        seed=seed,
    )
    assert digest(result) == digest(simulate(permuted, turbulence=turbulence))
    assert result.geography == original
    for year in range(1037, 1337, 5):
        commitments: Counter[str] = Counter()
        for event in result.events:
            if event.year == year:
                commitments.update(dict(event.commitments))
        assert all(amount <= 1000 for amount in commitments.values())
    validate_history(result)


def test_quiet_empty_and_tribal_worlds_do_not_force_countries_or_diplomacy() -> None:
    empty = simulate(create(Geography((), ()), (), seed=0))
    assert empty.state.year == 1337
    assert not empty.events
    assert not empty.state.actors
    validate_history(empty)
    place = District("island", "alone", Tenure.TRIBE, (Cohort("culture", "faith", 1000, 0),))
    history = create(
        Geography((place,), ()),
        (Founding("tribe", Tenure.TRIBE, (place.key,), place.key),),
        seed=42,
    )
    result = simulate(history, turbulence=1000)
    assert len(result.events) == 1
    assert result.state.holdings == history.state.holdings
    assert result.state.actors[0].tenure is Tenure.TRIBE
    validate_history(result)


def test_cancellation_inside_a_round_leaves_the_prior_history_untouched() -> None:
    history = _line(count=150)
    before = digest(history)
    checks = 0

    def cancel() -> None:
        nonlocal checks
        checks += 1
        if checks == 4:
            raise Cancelled

    with pytest.raises(Cancelled):
        _ = simulate(history, checkpoint=cancel)
    assert digest(history) == before


def test_malformed_bootstraps_and_actions_fail_explicitly() -> None:
    history = _line()
    with pytest.raises(HistoryError, match="three"):
        _ = advance(history, tuple(Proposal(Action.CONTACT, "a0", "a1", rank=n) for n in range(4)))
    with pytest.raises(HistoryError, match="absent/extinct"):
        _ = advance(history, (Proposal(Action.CONTACT, "vanilla", "a1"),))
    with pytest.raises(HistoryError, match="reserved"):
        _ = create(
            history.geography,
            (*history.foundings, replace(history.foundings[0], key="extra")),
            seed=42,
        )
    geography = replace(history.geography, rules=Rules(minimum_peasants=999_999))
    with pytest.raises(HistoryError, match="Unsupported"):
        _ = create(geography, history.foundings, seed=42)


def test_permuting_scripted_proposals_preserves_the_valley_record() -> None:
    result = simulate(valley(), policy=lambda context: tuple(reversed(valley_policy(context))))
    assert digest(result) == digest(divided_valley())


def test_joint_unions_inherit_both_ends_of_memory_and_knowledge() -> None:
    history = _line(count=4)
    for year in range(1037, 1087, 5):
        proposals = ()
        if year == 1037:
            proposals = tuple(Proposal(Action.CONTACT, f"a{n}", f"a{n + 1}") for n in range(3))
        elif year in (1042, 1057, 1072):
            proposals = tuple(Proposal(Action.EXCHANGE, f"a{n}", f"a{n + 1}") for n in range(3))
        history = advance(history, proposals)
    history = advance(
        history, (Proposal(Action.UNION, "a0", "a1"), Proposal(Action.UNION, "a2", "a3"))
    )
    living = {actor.key for actor in history.state.actors if actor.living}
    assert len(living) == 2
    assert {(known.first, known.second) for known in history.state.knowledge} == {
        (first, second) for first in living for second in living if first != second
    }
    assert any(
        memory.first in living and memory.second in living for memory in history.state.memories
    )
    validate_history(history)


def test_two_offers_of_submission_choose_one_overlord() -> None:
    history = _line()
    places = tuple(
        replace(place, cohorts=(Cohort("c", "r", 100 if place.key == "1" else 10_000, 50),))
        for place in history.geography.districts
    )
    history = create(replace(history.geography, districts=places), history.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a1", "a0"), Proposal(Action.CONTACT, "a1", "a2"))
    )
    history = advance(
        history, (Proposal(Action.DEPENDENCY, "a1", "a0"), Proposal(Action.DEPENDENCY, "a1", "a2"))
    )
    assert len(history.state.bonds) == 1
    assert sum(event.reason is Reason.COMMITTED for event in history.events[-2:]) == 1
    validate_history(history)


def test_an_indirect_exchange_does_not_invent_a_further_physical_route() -> None:
    history = _line(count=4)
    for proposal in (
        Proposal(Action.CONTACT, "a0", "a1"),
        Proposal(Action.EXCHANGE, "a0", "a1"),
        Proposal(Action.CONTACT, "a0", "a2"),
        Proposal(Action.EXCHANGE, "a0", "a2"),
        Proposal(Action.CONTACT, "a0", "a3"),
    ):
        history = advance(history, (proposal,))
    assert history.events[-1].reason is Reason.UNREACHABLE
    validate_history(history)


def test_shared_defender_cannot_fully_commit_to_several_conflicts() -> None:
    attackers = ("one", "two", "three", "four")
    targets = ("w", "x", "y", "z")
    keys = ("hub", *attackers, *targets, "threat")
    places = tuple(
        District(
            key,
            "plain",
            Tenure.LAND,
            (
                Cohort(
                    "c", "r", 300 if key in targets else (1000 if key == "threat" else 2000), 150
                ),
            ),
            defence=100_000 if key == "threat" else 1000,
        )
        for key in keys
    )
    routes = tuple(Route(first, second) for n, first in enumerate(keys) for second in keys[n + 1 :])
    history = create(
        Geography(places, routes),
        tuple(Founding(key, Tenure.LAND, (key,), key) for key in keys),
        seed=42,
    )
    # Five towns really encounter and are repelled by the same approach before any pact.
    for key in ("hub", *attackers):
        history = advance(history, (Proposal(Action.CONTACT, key, "threat"),))
        history = advance(history, (Proposal(Action.CONFLICT, key, "threat", ("threat",)),))
        assert history.events[-1].outcome is Outcome.FAILED
    for key in attackers:
        history = advance(history, (Proposal(Action.CONTACT, "hub", key),))
        history = advance(history, (Proposal(Action.PACT, "hub", key, threat="threat"),))
        assert history.events[-1].outcome is Outcome.ACCEPTED
    for actor, target in zip(attackers, targets, strict=True):
        history = advance(history, (Proposal(Action.CONTACT, actor, target),))
    history = advance(
        history,
        tuple(
            Proposal(Action.CONFLICT, actor, target, (target,))
            for actor, target in zip(attackers, targets, strict=True)
        ),
    )
    battles = history.events[-4:]
    assert all(event.outcome is Outcome.ACCEPTED for event in battles)
    allocations = sorted(dict(event.commitments).get("hub", 0) for event in battles)
    assert allocations == [100, 300, 300, 300]
    validate_history(history)
