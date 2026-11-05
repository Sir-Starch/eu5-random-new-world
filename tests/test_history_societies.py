"""H3: caused divergence, identity conservation and extraordinary outcomes."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from rnw.history_context import Context
from rnw.history_engine import advance, create, digest, simulate, validate_history
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Exchange,
    Founding,
    Geography,
    Hearth,
    History,
    HistoryError,
    Livelihood,
    Military,
    Movement,
    Outcome,
    Proposal,
    Reason,
    Route,
    Rules,
    Society,
    Tenure,
    TrajectoryKind,
)
from rnw.history_trajectories import realizations, report

from .history_fixtures import divided_valley, valley_policy


def _context(history: History) -> Context:
    return Context(history, lambda: None)


def _neighbours(*, pressure: bool = False, seed: int = 42, tradition: int = 0) -> History:
    profile = Society(
        tradition=tradition,
        livelihood=Livelihood.MOBILE,
        military=Military.OFFENSIVE if pressure else Military.BALANCED,
        integration=600,
    )
    places = tuple(
        District(
            key,
            "plain",
            Tenure.TRIBE if pressure and key != "a" else Tenure.LAND,
            (
                Cohort(
                    key,
                    f"faith_{key}",
                    10_000 if pressure and key == "a" else 1000,
                    5000 if pressure and key == "a" else 500,
                ),
            ),
            coastal=True,
            headroom=200 if key != "a" else 0,
        )
        for key in ("a", "b", "c")
    )
    # D26: "b" already holds the council institutions that "a" may adopt from it.
    # Under pressure, the tribe "b" holds ruler authority instead.
    societies = {
        place.key: replace(
            profile,
            authority=Authority.COUNCIL if place.tenure is Tenure.LAND else Authority.RULER,
        )
        if place.key == "b"
        else profile
        for place in places
    }
    return create(
        Geography(places, (Route("a", "b"), Route("a", "c"), Route("b", "c"))),
        tuple(
            Founding(
                place.key,
                place.tenure,
                (place.key,),
                place.key,
                societies[place.key].authority,
                society=societies[place.key],
            )
            for place in places
        ),
        seed=seed,
    )


def _prepared(*, pressure: bool = False, seed: int = 42, tradition: int = 0) -> History:
    history = _neighbours(pressure=pressure, seed=seed, tradition=tradition)
    history = advance(history, (Proposal(Action.CONTACT, "a", "b"),))
    kind = Action.PRESSURE if pressure else Action.EXCHANGE
    history = advance(history, (Proposal(kind, "a", "b", ("b",) if pressure else ()),))
    while history.state.year < 1057:
        history = advance(history, ())
    return advance(history, (Proposal(kind, "a", "b", ("b",) if pressure else ()),))


@pytest.mark.parametrize(
    ("axis", "value", "pressure"),
    [
        ("centralization", 400, False),
        ("authority", Authority.RULER, True),
        ("livelihood", Livelihood.MIXED, False),
        ("exchange", Exchange.COASTAL, False),
        ("religious_authority", 400, True),
        ("military", Military.DEFENSIVE, True),
        ("integration", 700, True),
        ("tradition", 100, False),
    ],
)
def test_every_dimension_changes_only_through_an_eligible_caused_reform(
    axis: str,
    value: object,
    *,
    pressure: bool,
) -> None:
    history = _prepared(pressure=pressure)
    original = next(actor for actor in history.state.actors if actor.key == "a")
    desired = replace(original.society, **{axis: value})
    result = advance(history, (Proposal(Action.REFORM, "a", reform=desired),))
    event = result.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    assert 400 <= dict(event.commitments)["a"] <= 1000
    assert len(event.effects.reforms) == 1
    actor = next(actor for actor in result.state.actors if actor.key == "a")
    untouched = next(actor for actor in result.state.actors if actor.key == "c")
    assert actor.society == desired
    assert actor.society != untouched.society
    assert actor.society_cause == event.key
    experiences = [
        each for each in history.events if each.kind in {Action.EXCHANGE, Action.PRESSURE}
    ]
    assert len(experiences) == 2
    assert {each.key for each in experiences} <= set(event.causes)
    assert result.state.settlements == history.state.settlements
    assert result.state.holdings == history.state.holdings
    assert actor.tenure is original.tenure
    validate_history(result)


def test_reform_needs_two_prior_rounds_and_cannot_chain_in_the_same_round() -> None:
    history = _neighbours()
    desired = Society(
        tradition=0, livelihood=Livelihood.MOBILE, integration=600, authority=Authority.COUNCIL
    )
    result = advance(history, (Proposal(Action.REFORM, "a", reform=desired),))
    assert result.events[-1].reason is Reason.REPEATED_PROBLEM
    assert not result.events[-1].commitments
    history = _prepared()
    original = next(actor for actor in history.state.actors if actor.key == "a").society
    proposals = (
        Proposal(Action.REFORM, "a", reform=replace(original, tradition=original.tradition + 100)),
        Proposal(Action.REFORM, "a", reform=replace(original, exchange=Exchange.COASTAL), rank=1),
    )
    result = advance(history, proposals)
    assert sum(each.outcome is Outcome.ACCEPTED for each in result.events[-2:]) == 1
    assert result.events[-1].reason is Reason.COMMITTED
    validate_history(result)


def test_old_cooperation_does_not_justify_an_unrelated_or_late_reform() -> None:
    history = _prepared()
    profile = history.state.actors[0].society
    result = advance(
        history, (Proposal(Action.REFORM, "a", reform=replace(profile, religious_authority=600)),)
    )
    assert result.events[-1].reason is Reason.REPEATED_PROBLEM
    while history.state.year < 1142:
        history = advance(history, ())
    result = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.COUNCIL)),),
    )
    assert result.events[-1].reason is Reason.REPEATED_PROBLEM


def test_tradition_can_resist_reform_but_still_spends_the_commitment() -> None:
    outcomes: set[Outcome] = set()
    for seed in range(6):
        history = _prepared(seed=seed, tradition=1000)
        profile = history.state.actors[0].society
        result = advance(
            history,
            (Proposal(Action.REFORM, "a", reform=replace(profile, exchange=Exchange.COASTAL)),),
        )
        event = result.events[-1]
        outcomes.add(event.outcome)
        assert event.commitments
        if event.outcome is Outcome.FAILED:
            assert event.reason is Reason.RESISTANCE
            assert result.state.actors == history.state.actors
        validate_history(result)
    assert outcomes == {Outcome.ACCEPTED, Outcome.FAILED}


def _move(source: str, destination: str, *, amount: int = 100) -> Proposal:
    return Proposal(
        Action.MIGRATION,
        source,
        destination,
        movement=Movement(
            source,
            destination,
            Cohort(source, f"faith_{source}", amount, amount // 2),
        ),
    )


def _totals(history: History) -> Counter[tuple[str, str, str]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for settlement in history.state.settlements:
        for cohort in settlement.cohorts:
            counts[cohort.culture, cohort.religion, "people"] += cohort.population
            counts[cohort.culture, cohort.religion, "peasants"] += cohort.peasants
    return counts


def test_migration_makes_a_minority_and_conserves_each_identity_and_peasant_budget() -> None:
    history = advance(_neighbours(), (Proposal(Action.CONTACT, "a", "b"),))
    result = advance(history, (_move("a", "b"),))
    assert result.events[-1].outcome is Outcome.ACCEPTED
    assert _totals(result) == _totals(history)
    settlements = {place.district: place for place in result.state.settlements}
    assert settlements["a"].cohorts == (Cohort("a", "faith_a", 900, 450),)
    assert settlements["b"].cohorts == (
        Cohort("a", "faith_a", 100, 50),
        Cohort("b", "faith_b", 1000, 500),
    )
    assert settlements["b"].cause == result.events[-1].key
    assert result.state.holdings == history.state.holdings
    validate_history(result)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("capacity", Reason.CAPACITY),
        ("pressure", Reason.PRESSURE),
        ("route", Reason.UNREACHABLE),
        ("identity", Reason.INELIGIBLE),
        ("peasants", Reason.INELIGIBLE),
        ("support", Reason.SUPPORT),
        ("host", Reason.HOSTILE),
    ],
)
def test_migration_refuses_missing_conditions_without_changing_population(
    change: str, reason: Reason
) -> None:
    original = _neighbours()
    geography, foundings = original.geography, original.foundings
    proposal = _move("a", "b")
    if change in {"capacity", "pressure"}:
        geography = replace(
            geography,
            districts=tuple(
                replace(place, headroom=0 if change == "capacity" else 1000)
                if place.key == ("b" if change == "capacity" else "a")
                else place
                for place in geography.districts
            ),
        )
    elif change == "route":
        geography = replace(geography, routes=(Route("a", "c"), Route("b", "c")))
    elif change == "identity":
        proposal = replace(
            proposal, movement=Movement("a", "b", Cohort("invented", "faith_a", 100, 50))
        )
    elif change == "peasants":
        proposal = replace(proposal, movement=Movement("a", "b", Cohort("a", "faith_a", 100, 99)))
    elif change == "support":
        geography = replace(geography, rules=Rules(minimum_peasants=480))
    elif change == "host":
        foundings = tuple(
            replace(founding, society=replace(founding.society or Society(), integration=400))
            if founding.key == "b"
            else founding
            for founding in foundings
        )
    history = create(geography, foundings, seed=42)
    # Establish knowledge over a real intermediary for the missing direct movement route.
    if change == "route":
        history = advance(history, (Proposal(Action.CONTACT, "a", "c"),))
        history = advance(history, (Proposal(Action.EXCHANGE, "a", "c"),))
    history = advance(history, (Proposal(Action.CONTACT, "a", "b"),))
    result = advance(history, (proposal,))
    assert result.events[-1].reason is reason
    assert result.events[-1].outcome is Outcome.REFUSED
    assert result.state.settlements == history.state.settlements
    validate_history(result)


def test_competing_moves_reserve_destination_capacity_once_independent_of_input_order() -> None:
    original = _neighbours()
    places = tuple(
        replace(place, headroom=100 if place.key == "b" else 0)
        for place in original.geography.districts
    )
    history = create(replace(original.geography, districts=places), original.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a", "b"), Proposal(Action.CONTACT, "c", "b"))
    )
    proposals = (_move("a", "b"), _move("c", "b"))
    result = advance(history, proposals)
    assert digest(result) == digest(advance(history, tuple(reversed(proposals))))
    assert sorted(event.outcome for event in result.events[-2:]) == [
        Outcome.ACCEPTED,
        Outcome.REFUSED,
    ]
    assert _totals(result) == _totals(history)
    assert _context(result).index.population("b") == 1100
    validate_history(result)


def test_conquest_keeps_all_cohorts_and_does_not_assimilate_a_migrant_minority() -> None:
    original = _neighbours()
    places = tuple(
        replace(place, cohorts=(Cohort("c", "faith_c", 20_000, 10_000),))
        if place.key == "c"
        else place
        for place in original.geography.districts
    )
    history = create(replace(original.geography, districts=places), original.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a", "b"), Proposal(Action.CONTACT, "c", "b"))
    )
    history = advance(history, (_move("a", "b"),))
    before = history.state.settlements
    result = advance(history, (Proposal(Action.CONFLICT, "c", "b", ("b",)),))
    assert result.events[-1].outcome is Outcome.ACCEPTED
    assert result.state.settlements == before
    assert _totals(result) == _totals(original) + Counter(
        {("c", "faith_c", "people"): 19_000, ("c", "faith_c", "peasants"): 9500}
    )
    validate_history(result)


def test_a_conquest_and_migration_cannot_spend_the_same_prior_population() -> None:
    original = _neighbours()
    geography = replace(
        original.geography,
        districts=tuple(
            replace(place, cohorts=(Cohort("c", "faith_c", 20_000, 10_000),))
            if place.key == "c"
            else place
            for place in original.geography.districts
        ),
    )
    history = create(geography, original.foundings, seed=42)
    history = advance(
        history, (Proposal(Action.CONTACT, "a", "b"), Proposal(Action.CONTACT, "c", "b"))
    )
    result = advance(history, (_move("a", "b"), Proposal(Action.CONFLICT, "c", "b", ("b",))))
    assert result.events[-2].outcome is Outcome.ACCEPTED
    assert result.events[-1].reason is Reason.COMMITTED
    assert result.state.settlements == history.state.settlements
    assert _totals(result) == _totals(history)
    validate_history(result)


def _trajectory_world(kind: TrajectoryKind, *, chance: int = 1000) -> History:
    if kind is TrajectoryKind.GREAT_EMPIRE:
        places = tuple(
            District(str(n), "plain", Tenure.LAND, (Cohort("c", "r", 1000, 500),))
            for n in range(12)
        )
        routes = tuple(Route(str(n), str(n + 1), cost=250) for n in range(11))
        founding = tuple(
            Founding(
                f"centre_{n}",
                Tenure.LAND,
                tuple(str(key) for key in range(n * 4, n * 4 + 4)),
                str(n * 4),
            )
            for n in range(3)
        )
    else:
        tenure = Tenure.TRIBE if kind is TrajectoryKind.HIGHLAND_CONFEDERATION else Tenure.LAND
        places = tuple(
            District(
                str(n),
                "plain",
                tenure,
                (
                    Cohort(
                        "c",
                        "r",
                        3000 if n == 0 and kind is TrajectoryKind.SACRED_CENTRE else 1000,
                        500,
                    ),
                ),
                coastal=kind is TrajectoryKind.SEA_LEAGUE,
                highland=tenure is Tenure.TRIBE,
                sacred=n == 0 and kind is TrajectoryKind.SACRED_CENTRE,
            )
            for n in range(3)
        )
        routes = tuple(
            Route("0", str(n + 1), sea_steps=2 if kind is TrajectoryKind.SEA_LEAGUE else 0)
            for n in range(2)
        )
        founding = tuple(
            Founding(place.key, tenure, (place.key,), place.key, technology=2) for place in places
        )
    geography = Geography(
        places,
        routes,
        hearths=(Hearth("hearth", places[0].key, tuple(place.key for place in places)),),
    )
    return create(geography, founding, seed=42, empire_permille=chance)


@pytest.mark.parametrize(
    "kind",
    [
        TrajectoryKind.GREAT_EMPIRE,
        TrajectoryKind.SEA_LEAGUE,
        TrajectoryKind.HIGHLAND_CONFEDERATION,
        TrajectoryKind.SACRED_CENTRE,
    ],
)
def test_trajectories_are_seeded_only_per_eligible_hearth_and_grant_no_outcomes(
    kind: TrajectoryKind,
) -> None:
    history = _trajectory_world(kind)
    assert len(history.state.trajectories) == 1
    assert history.state.trajectories[0].kind is kind
    assert not history.state.bonds
    assert all(event.kind in {Action.FOUNDATION, Action.TRAJECTORY} for event in history.events)
    assert report(_context(history))[kind]["seeded"] == 1
    assert report(_context(history))[kind]["realized"] == 0
    zero = _trajectory_world(kind, chance=0)
    assert not zero.state.trajectories
    assert zero.state.holdings == history.state.holdings
    assert zero.state.settlements == history.state.settlements
    validate_history(history)


def test_great_ambition_uses_existing_capacity_without_granting_territory_or_power() -> None:
    original = _trajectory_world(TrajectoryKind.GREAT_EMPIRE, chance=0)
    geography = replace(
        original.geography,
        districts=tuple(
            replace(p, cohorts=(Cohort("c", "r", 6000, 3000),)) if int(p.key) >= 8 else p
            for p in original.geography.districts
        ),
    )
    plain = create(geography, original.foundings, seed=42, empire_permille=0)
    ambitious = create(geography, original.foundings, seed=42, empire_permille=1000)
    (trajectory,) = ambitious.state.trajectories
    assert trajectory.members == ("centre_2",)
    assert ambitious.state.holdings == plain.state.holdings
    assert ambitious.state.settlements == plain.state.settlements
    assert not ambitious.state.bonds
    assert [a.technology for a in ambitious.state.actors] == [
        a.technology for a in plain.state.actors
    ]
    assert report(_context(ambitious))[TrajectoryKind.GREAT_EMPIRE]["realized"] == 0
    validate_history(ambitious)


def test_great_empire_ambition_needs_actual_supported_expansion() -> None:
    original = _trajectory_world(TrajectoryKind.GREAT_EMPIRE)
    anchor = original.state.trajectories[0].anchor
    owner = _context(original).index.owner[anchor]
    homeland = _context(original).index.members[owner]
    geography = replace(
        original.geography,
        districts=tuple(
            replace(place, cohorts=(Cohort("c", "r", 20_000, 10_000),))
            if place.key in homeland
            else place
            for place in original.geography.districts
        ),
    )
    foundings = tuple(
        replace(founding, society=Society(integration=900)) if founding.key == owner else founding
        for founding in original.foundings
    )
    history = create(geography, foundings, seed=42, empire_permille=1000)
    assert not realizations(_context(history))
    for _ in range(2):
        context = _context(history)
        target = min(context.near[owner])
        taken = tuple(sorted(context.index.members[target]))
        history = advance(history, (Proposal(Action.CONTACT, owner, target),))
        history = advance(history, (Proposal(Action.CONFLICT, owner, target, taken),))
        assert history.events[-1].outcome is Outcome.ACCEPTED
        for _ in range(5):
            history = advance(history, ())
    assert report(_context(history))[TrajectoryKind.GREAT_EMPIRE] == {"seeded": 1, "realized": 1}
    assert len(_context(history).index.members[owner]) == 12
    assert _totals(history) == _totals(create(geography, foundings, seed=42))
    validate_history(history)


def test_shared_sea_without_a_bounded_physical_route_seeds_no_league() -> None:
    original = _trajectory_world(TrajectoryKind.SEA_LEAGUE)
    geography = replace(
        original.geography,
        routes=tuple(replace(route, sea_steps=5) for route in original.geography.routes),
    )
    history = create(geography, original.foundings, seed=42, empire_permille=1000)
    assert not history.state.trajectories


@pytest.mark.parametrize("kind", [TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION])
def test_extraordinary_network_requires_demonstrated_threat_and_actual_agreements(
    kind: TrajectoryKind,
) -> None:
    original = _trajectory_world(kind)
    sea = kind is TrajectoryKind.SEA_LEAGUE
    places = list(original.geography.districts)
    routes = list(original.geography.routes)
    foundings = list(original.foundings)
    for key in ("0", "1", "2"):
        if sea:
            border = f"border_{key}"
            places.append(District(border, "plain", Tenure.LAND, (Cohort("c", "r", 100, 50),)))
            routes.extend((Route(key, border), Route(border, "threat")))
            foundings = [
                replace(founding, districts=(*founding.districts, border))
                if founding.key == key
                else founding
                for founding in foundings
            ]
        else:
            routes.append(Route(key, "threat"))
    places.append(District("threat", "plain", Tenure.LAND, (Cohort("other", "r", 20_000, 10_000),)))
    foundings.append(
        Founding(
            "threat",
            Tenure.LAND,
            ("threat",),
            "threat",
            Authority.RULER,
            2,
            society=Society(
                authority=Authority.RULER, military=Military.OFFENSIVE, integration=800
            ),
        )
    )
    history = create(
        replace(original.geography, districts=tuple(places), routes=tuple(routes)),
        foundings,
        seed=42,
        empire_permille=1000,
    )
    holdings = history.state.holdings
    assert not realizations(_context(history))
    for key in ("0", "1", "2"):
        history = advance(history, (Proposal(Action.CONTACT, "threat", key),))
        history = advance(
            history,
            (
                Proposal(
                    Action.CONFLICT if sea else Action.PRESSURE,
                    "threat",
                    key,
                    (f"border_{key}" if sea else key,),
                ),
            ),
        )
        assert history.events[-1].outcome is Outcome.ACCEPTED
    assert not realizations(_context(history))
    if not sea:
        assert history.state.holdings == holdings
        assert all(
            actor.tenure is Tenure.TRIBE for actor in history.state.actors if actor.key != "threat"
        )
    history = advance(
        history, (Proposal(Action.CONTACT, "0", "1"), Proposal(Action.CONTACT, "0", "2"))
    )
    if sea:
        history = advance(
            history, (Proposal(Action.EXCHANGE, "0", "1"), Proposal(Action.EXCHANGE, "0", "2"))
        )
        assert not realizations(_context(history))
    history = advance(
        history,
        (
            Proposal(Action.PACT, "0", "1", threat="threat"),
            Proposal(Action.PACT, "0", "2", threat="threat"),
        ),
    )
    found = realizations(_context(history))
    assert len(found) == 1
    assert found[0].kind is kind
    assert set(found[0].members) == {"0", "1", "2"}
    assert sum(bond.kind is Action.PACT for bond in history.state.bonds) == 2
    assert report(_context(history))[kind] == {"seeded": 1, "realized": 1}
    assert _totals(history) == _totals(create(history.geography, history.foundings, seed=42))
    validate_history(history)


def test_sacred_trajectory_is_realized_only_after_actual_access_bargains() -> None:
    history = _trajectory_world(TrajectoryKind.SACRED_CENTRE)
    history = advance(
        history, (Proposal(Action.CONTACT, "1", "0"), Proposal(Action.CONTACT, "2", "0"))
    )
    assert not realizations(_context(history))
    history = advance(
        history,
        (Proposal(Action.ACCESS, "1", "0", ("0",)), Proposal(Action.ACCESS, "2", "0", ("0",))),
    )
    found = realizations(_context(history))
    assert len(found) == 1
    assert found[0].kind is TrajectoryKind.SACRED_CENTRE
    assert {bond.cause for bond in history.state.bonds} <= set(found[0].causes)
    validate_history(history)


def test_fractured_realm_requires_a_real_recorded_union_and_separation() -> None:
    history = divided_valley()
    assert not any(
        item.kind is TrajectoryKind.FRACTURED_REALM for item in history.state.trajectories
    )
    # A small synthetic recognition floor tests lineage, rather than the calibrated empire size.
    geography = replace(
        history.geography,
        rules=replace(history.geography.rules, empire_locations=6),
        districts=tuple(
            replace(place, cohorts=(Cohort("valley_people", "river_faith", 3000, 1500),))
            if place.key == "d0"
            else place
            for place in history.geography.districts
        ),
    )
    assert not realizations(_context(create(geography, history.foundings, seed=42)))
    result = create(geography, history.foundings, seed=42)
    while result.state.year < 1232:
        result = advance(result, valley_policy(_context(result)))
    found = realizations(_context(result))
    assert len(found) == 1
    assert found[0].kind is TrajectoryKind.FRACTURED_REALM
    assert (
        next(event.key for event in result.events if event.kind is Action.SEPARATION)
        in found[0].causes
    )
    assert not realizations(
        _context(history)
    )  # The downstream successor has since become dominant.
    validate_history(result)


@pytest.mark.parametrize("tamper", ["profile", "cohort", "trajectory"])
def test_replay_rejects_unexplained_profiles_population_and_ambitions(tamper: str) -> None:
    history = _trajectory_world(TrajectoryKind.GREAT_EMPIRE)
    state = history.state
    if tamper == "profile":
        actor = state.actors[0]
        state = replace(
            state, actors=(replace(actor, society=replace(actor.society, integration=999)),)
        )
    elif tamper == "cohort":
        place = state.settlements[0]
        state = replace(
            state,
            settlements=(
                replace(place, cohorts=(Cohort("invented", "r", 1000, 500),)),
                *state.settlements[1:],
            ),
        )
    else:
        state = replace(state, trajectories=())
    with pytest.raises(HistoryError):
        validate_history(replace(history, state=state))


@pytest.mark.parametrize("seed", [3, 42, 77])
def test_autonomous_societies_preserve_population_and_all_input_permutations(seed: int) -> None:
    history = _neighbours(pressure=True, seed=seed)
    original = history.geography
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
    result = simulate(history, turbulence=1000)
    assert digest(result) == digest(simulate(permuted, turbulence=1000))
    assert _totals(result) == _totals(history)
    assert any(
        event.kind is Action.MIGRATION and event.outcome is Outcome.ACCEPTED
        for event in result.events
    )
    validate_history(result)


def test_trajectory_streams_and_profiles_are_independent_of_hearth_and_cohort_order() -> None:
    original = _trajectory_world(TrajectoryKind.SEA_LEAGUE)
    geography = replace(
        original.geography,
        hearths=(
            *original.geography.hearths,
            Hearth("second", "2", tuple(reversed(original.geography.hearths[0].domain))),
        ),
    )
    geography = replace(
        geography,
        districts=tuple(
            replace(
                place,
                cohorts=(
                    Cohort("c", "r", 900, 450),
                    Cohort("c", "r", 100, 50),
                ),
            )
            for place in geography.districts
        ),
    )
    history = create(geography, original.foundings, seed=42, empire_permille=1000)
    permuted = create(
        replace(
            geography,
            hearths=tuple(reversed(geography.hearths)),
            districts=tuple(
                replace(place, cohorts=tuple(reversed(place.cohorts)))
                for place in reversed(geography.districts)
            ),
            routes=tuple(reversed(geography.routes)),
        ),
        tuple(reversed(original.foundings)),
        seed=42,
        empire_permille=1000,
    )
    assert len(history.state.trajectories) == 2
    assert digest(history) == digest(permuted)
    validate_history(history)


def test_council_rule_needs_collective_bargains_not_routine_exchange() -> None:
    history = _prepared()
    profile = history.state.actors[0].society
    result = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.COUNCIL)),),
    )
    assert result.events[-1].reason is Reason.REPEATED_PROBLEM


def test_a_new_authority_is_adopted_from_a_neighbour_that_holds_it() -> None:
    history = _prepared(pressure=True)
    profile = history.state.actors[0].society
    accepted = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.RULER)),),
    )
    event = accepted.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    neighbour = next(actor for actor in history.state.actors if actor.key == "b")
    assert neighbour.society_cause in event.causes
    refused = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.SACRED)),),
    )
    assert refused.events[-1].reason is Reason.REPEATED_PROBLEM
