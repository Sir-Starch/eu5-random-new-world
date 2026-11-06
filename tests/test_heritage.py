"""The vanilla American chains adapted to generated facts (history plan §22, N9): their bearers."""

from __future__ import annotations

from rnw.content import (
    ALLIANCE_GROUP,
    CONFEDERATION_COUNCIL,
    DECLINING_CENTRE,
    SENIOR_PARTNER,
    Facts,
    Fallen,
    HistoricalFacts,
    Place,
    State,
    councils,
    declining_centres,
    plan_content,
    seniors,
)
from rnw.stories_heritage import LEADS, council, founding, nation


def _facts(
    *,
    fallen: tuple[Fallen, ...] = (),
    confederations: tuple[tuple[str, ...], ...] = (),
    alliances: frozenset[tuple[str, str]] | None = None,
) -> Facts:
    """Five states; S(n) holds n + 1 places, its capital the first of them."""
    places: dict[str, Place] = {}
    states: dict[str, State] = {}
    number = 0
    for state in range(5):
        tag = f"S{state}"
        keys = [f"p{number + offset:02d}" for offset in range(state + 1)]
        number += state + 1
        for key in keys:
            places[key] = Place(key, 100, 0, "town", "f", tag)
        states[tag] = State(tag, keys[0], "f")
    history = HistoricalFacts(
        {}, frozenset(), {}, frozenset(), fallen, confederations, alliances or frozenset()
    )
    return Facts(places, states, frozenset(), frozenset(), history=history)


def test_the_seat_of_a_fallen_realm_held_by_a_state_is_a_declining_centre() -> None:
    """Its cause is the division that ended the realm."""
    realm = Fallen("old", "p03", ("p03", "p04"), ("S1", "S2"), 1, 1200, "h1200_division")
    facts = _facts(fallen=(realm,))
    assert declining_centres(facts) == {"p03": "h1200_division"}
    plan = plan_content(facts, 7)
    [story] = [o for o in plan.opportunities if o.family == DECLINING_CENTRE]
    assert story.centre == "p03"
    assert story.bearer == "S2"
    assert story.history_causes == ("h1200_division",)
    gone = Fallen("lost", "nowhere", (), (), 1, 1200, "x")
    assert declining_centres(_facts(fallen=(gone,))) == {}


def test_the_largest_member_of_a_confederation_holds_its_council() -> None:
    """The game leads a confederation by size; the story asks for the lead in play."""
    facts = _facts(confederations=(("S1", "S3", "S2"),))
    assert [place.owner for place in councils(facts)] == ["S3"]
    plan = plan_content(facts, 7)
    assert [o.bearer for o in plan.opportunities if o.family == CONFEDERATION_COUNCIL] == ["S3"]
    assert LEADS in council().gate


def test_the_strongest_of_an_alliance_of_three_is_the_senior_partner() -> None:
    """Its strongest ally is the junior partner; two allies are no triple alliance."""
    three = frozenset({("S1", "S2"), ("S2", "S4")})
    facts = _facts(alliances=three)
    found = seniors(facts)
    capital = {tag: state.capital for tag, state in facts.states.items()}
    assert found == {capital["S4"]: capital["S2"]}
    plan = plan_content(facts, 7)
    [story] = [o for o in plan.opportunities if o.family == SENIOR_PARTNER]
    assert story.other == capital["S2"]
    assert ALLIANCE_GROUP == 3
    assert seniors(_facts(alliances=frozenset({("S1", "S2")}))) == {}


def test_a_nation_begins_its_founding_at_its_capital() -> None:
    """The formation stores the capital, opens the assembly and schedules the cleanup."""
    lines = founding(nation())
    assert lines[0] == "capital = { save_scope_as = home_place }"
    assert "name = rnw_nation_centre value = scope:home_place" in lines[1]
    assert "id = rnw_nation.1" in lines[2]
    assert "id = rnw_nation.9" in lines[3]
