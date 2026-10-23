"""The eligibility of the harvest, route, alliance and empire stories (synthetic worlds)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.content import (
    EMPIRE_PERIPHERY,
    GREAT_ALLIANCE,
    HARVEST,
    MAX_CHAINS,
    ROUTE_MARKET,
    ROUTE_MAX_STEPS,
    ROUTE_MIN_STEPS,
    Facts,
    Place,
    State,
    alliances,
    harvest_centres,
    peripheries,
    plan_content,
    routes,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

SEED = 99


def _line(  # noqa: PLR0913 - a synthetic world is these few knobs
    count: int = 30,
    *,
    owners: Callable[[int], str] = lambda i: f"S{i // 10}",
    relief: Callable[[int], str] = lambda _: "flatland",
    faith: Callable[[str], str] = lambda _: "faith",
    culture: Callable[[int], str] = lambda _: "c0",
    city: Callable[[int], bool] = lambda i: i % 5 == 0,
    subjects: Collection[tuple[str, str]] = (),
) -> Facts:
    """Places along a line (each linked to the next), owned in blocks of ten by default."""
    places: dict[str, Place] = {}
    for index in range(count):
        owner = owners(index)
        places[f"p{index:03d}"] = Place(
            f"p{index:03d}",
            100 + (index % 4) * 10,
            0,
            "city" if city(index) else "",
            faith(owner),
            owner,
            relief(index),
            culture(index),
        )
    tags = sorted({place.owner for place in places.values()})
    firsts = {tag: next(key for key, p in places.items() if p.owner == tag) for tag in tags}
    states = {tag: State(tag, firsts[tag], faith(tag)) for tag in tags}
    links = frozenset((f"p{i:03d}", f"p{i + 1:03d}") for i in range(count - 1))
    return Facts(places, states, frozenset(), links, {}, frozenset(subjects))


def test_a_harvest_centre_is_a_centre_on_high_ground_or_among_the_most_populous() -> None:
    """The land cannot easily feed a city in the hills, nor a very large one."""
    flat = {place.key for place in harvest_centres(_line())}
    assert flat
    assert all(_line().places[key].population >= 130 for key in flat)
    facts = _line(relief=lambda i: "hills" if i < 10 else "flatland")
    hilly = {place.key for place in harvest_centres(facts)}
    assert flat < hilly
    assert any(
        facts.places[key].relief == "hills" and facts.places[key].population < 130 for key in hilly
    )
    assert all(facts.places[key].owner in facts.states for key in hilly)


def test_a_route_joins_two_centres_of_one_state_over_its_own_places() -> None:
    """The ends are centres of the same state, between the least and the most steps apart."""
    facts = _line(owners=lambda i: "S0" if i < 20 else "S1")
    joined = routes(facts, SEED)
    assert joined
    for start, end in joined.items():
        assert facts.places[start].owner == facts.places[end].owner
        steps = abs(int(start[1:]) - int(end[1:]))
        assert ROUTE_MIN_STEPS <= steps <= ROUTE_MAX_STEPS


def test_a_route_does_not_run_through_another_state_or_beyond_its_reach() -> None:
    """Centres cut apart by a foreign place, or too far, are not joined."""
    # S0 holds p000 and p004 with S1's p001-p003 between; S2 holds p010 and p030, too far apart
    owner = {0: "S0", 4: "S0", 10: "S2", 30: "S2"}
    facts = _line(
        count=31,
        owners=lambda i: owner.get(i, "S1"),
        city=lambda i: i in owner,
    )
    assert routes(facts, SEED).get("p000") is None
    assert routes(facts, SEED).get("p030") is None
    adjacent = _line(count=2, owners=lambda _: "S0", city=lambda _: True)
    assert not routes(adjacent, SEED)


def test_an_alliance_pairs_neighbours_that_share_a_faith_or_a_people() -> None:
    """Neighbours of one faith, or one culture, might sit in a council; others do not."""
    facts = _line(
        faith=lambda tag: "red" if tag in {"S0", "S1"} else "blue",
        culture=lambda i: f"c{i // 10}",
    )
    paired = alliances(facts, SEED)
    owner = {key: place.owner for key, place in facts.places.items()}
    assert paired
    for mine, theirs in paired.items():
        assert owner[mine] != owner[theirs]
        assert facts.states[owner[mine]].religion == facts.states[owner[theirs]].religion
    # S1 and S2 differ in faith and in nothing else shared, so no pair joins them
    distinct = _line(
        faith=lambda tag: tag,
        culture=lambda i: f"culture{i // 10}",
    )
    assert not alliances(distinct, SEED)
    people = _line(faith=lambda tag: tag, culture=lambda i: "one" if i < 20 else "two")
    assert any(
        {owner[mine], owner[theirs]} == {"S0", "S1"}
        for mine, theirs in alliances(people, SEED).items()
    )


def test_a_state_and_its_subject_form_no_council_and_each_pair_has_one() -> None:
    """A council needs two independent states, and two that would choose each other make one."""
    facts = _line(subjects={("S0", "S1")})
    owner = {key: place.owner for key, place in facts.places.items()}
    for mine, theirs in alliances(facts, SEED).items():
        assert {owner[mine], owner[theirs]} != {"S0", "S1"}
    mutual = alliances(_line(), SEED)
    for mine, theirs in mutual.items():
        assert mutual.get(theirs) != mine


def test_the_periphery_is_the_capital_of_the_most_distant_subject() -> None:
    """A state with subjects gets its farthest subject's capital; one without gets none."""
    facts = _line(subjects={("S0", "S1"), ("S0", "S2")})
    far = peripheries(facts)
    assert far == {"p000": "p020"}
    assert not peripheries(_line())


def test_the_new_stories_share_the_limits_of_the_older_ones() -> None:
    """At most two chains a state, one start a year, one bearer a family, anchors may repeat."""
    facts = _line(count=60, owners=lambda i: f"S{i // 6}", subjects={("S0", "S9")})
    for seed in range(20):
        plan = plan_content(facts, seed)
        for tag in {o.bearer for o in plan.opportunities}:
            mine = [o for o in plan.opportunities if o.bearer == tag]
            assert len(mine) <= MAX_CHAINS
            assert len({o.start.year for o in mine}) == len(mine)
        for family in (HARVEST, ROUTE_MARKET, GREAT_ALLIANCE, EMPIRE_PERIPHERY):
            bearers = [o.bearer for o in plan.opportunities if o.family == family]
            assert len(bearers) == len(set(bearers))
        for opportunity in plan.opportunities:
            if opportunity.family in {ROUTE_MARKET, GREAT_ALLIANCE, EMPIRE_PERIPHERY}:
                assert opportunity.other
                assert opportunity.other != opportunity.centre
            else:
                assert not opportunity.other


def test_a_world_without_what_a_family_needs_records_why() -> None:
    """No neighbours of one faith, no subjects, no centre in reach: reasons, not errors."""
    facts = _line(count=2, owners=lambda _: "S0", faith=lambda _: "x", city=lambda _: True)
    plan = plan_content(facts, SEED)
    reasons = {absence.family: absence.reason for absence in plan.absences}
    assert "state holds subjects" in reasons[EMPIRE_PERIPHERY]
    assert GREAT_ALLIANCE in reasons
    assert ROUTE_MARKET in reasons
