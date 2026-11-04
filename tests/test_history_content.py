"""Existing stories use surviving history without inventing eligible bearers."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw.content import (
    EMPIRE_PERIPHERY,
    GREAT_ALLIANCE,
    HistoricalFacts,
    alliances,
    peripheries,
    plan_content,
)
from rnw.eu5_history_plan import project_start
from rnw.eu5_story import facts_of
from rnw.history_content import country_starts, facts
from rnw.history_model import HistoryError, TrajectoryKind

from .history_fixtures import divided_valley
from .test_content_stories import _line  # pyright: ignore[reportPrivateUsage]
from .test_history_plan import inputs_for, realized_network


def test_neighbouring_identity_alone_does_not_invent_a_cooperative_past() -> None:
    original = _line()
    history = HistoricalFacts({("S0", "S1"): ("exchange",)}, frozenset(), {}, original.links)
    current = replace(original, history=history)
    assert alliances(original, 99)
    pairs = alliances(current, 99)
    assert pairs
    assert all(
        {current.places[first].owner, current.places[second].owner} == {"S0", "S1"}
        for first, second in pairs.items()
    )
    hostile = replace(current, history=replace(history, hostile=frozenset({("S0", "S1")})))
    assert not alliances(hostile, 99)
    assert not alliances(replace(current, subjects=frozenset({("S0", "S1")})), 99)
    different = _line(faith=lambda tag: tag, culture=lambda i: str(i // 10))
    assert not alliances(replace(different, history=history), 99)


def test_selected_council_and_periphery_keep_their_real_causes() -> None:
    original = _line(3, owners=lambda i: f"S{i}", city=lambda _: False, subjects={("S0", "S2")})
    history = HistoricalFacts(
        {("S0", "S1"): ("exchange", "pact")},
        frozenset(),
        {("S0", "S2"): "submission"},
        original.links,
    )
    current = replace(original, history=history)
    selected = plan_content(current, 99)
    councils = [o for o in selected.opportunities if o.family == GREAT_ALLIANCE]
    periphery = [o for o in selected.opportunities if o.family == EMPIRE_PERIPHERY]
    assert len(councils) == len(periphery) == 1
    assert councils[0].history_causes == ("exchange", "pact")
    assert periphery[0].history_causes == ("submission",)
    assert current.places[periphery[0].other].owner == "S2"
    assert not any(a.family in {GREAT_ALLIANCE, EMPIRE_PERIPHERY} for a in selected.absences)
    assert (
        plan_content(
            replace(
                current,
                history=HistoricalFacts({}, frozenset(), history.dependencies, history.contacts),
            ),
            99,
        ).count()[GREAT_ALLIANCE]
        == 0
    )


def test_maritime_dependencies_use_verified_contacts_without_joining_river_territories() -> None:
    original = _line(subjects={("S0", "S1"), ("S0", "S2")})
    split = frozenset(pair for pair in original.links if pair[0] not in {"p009", "p019"})
    history = HistoricalFacts(
        {},
        frozenset(),
        {("S0", "S1"): "one", ("S0", "S2"): "two"},
        frozenset({("p005", "p015"), ("p015", "p025")}),
    )
    current = replace(original, links=split, history=history)
    assert peripheries(current) == {"p000": "p020"}
    assert current.links == split
    assert not peripheries(replace(current, history=replace(history, contacts=frozenset())))


@pytest.mark.parametrize("kind", [TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION])
def test_adapter_uses_current_landed_countries_and_actual_causes(kind: TrajectoryKind) -> None:
    start = project_start(
        inputs_for(realized_network(kind, overlap=kind is TrajectoryKind.HIGHLAND_CONFEDERATION))
    )
    current = facts(start)
    assert current is not None
    landed = {c.tag for c in start.countries if c.kind == "state" or c.landed}
    assert {tag for tag, _, _, _ in country_starts(start)} == landed
    assert all({first, second} <= landed for first, second in current.cooperation)
    assert set(current.dependencies) == set(start.vassals)
    assert start.history is not None
    events = {event.key for event in start.history.events}
    assert all(set(causes) <= events for causes in current.cooperation.values())
    assert set(current.dependencies.values()) <= events
    assert current.contacts == frozenset(
        (route.first, route.second) for route in start.history.geography.routes
    )
    if kind is TrajectoryKind.HIGHLAND_CONFEDERATION:
        confederates = {c.tag for c in start.countries if c.kind == "tribe" and c.landed}
        assert confederates <= landed
        assert confederates
        pop = replace(start.countries[0], tag="ZZZ", kind="tribe", landed=False)
        assert "ZZZ" not in {
            tag
            for tag, _, _, _ in country_starts(replace(start, countries=(*start.countries, pop)))
        }
        keys = tuple(sorted(start.population))
        eligible = facts_of(
            keys=keys,
            population=start.population,
            ranks=dict.fromkeys(keys, "city"),
            religion=dict.fromkeys(keys, start.countries[0].religion),
            river=dict.fromkeys(keys, 1),
            states=country_starts(start),
            holy=(),
            links=tuple(current.contacts),
            history=current,
        )
        selected = plan_content(eligible, 99)
        assert any(o.bearer in confederates for o in selected.opportunities)


def test_no_dead_bootstrap_tag_or_stale_dependency_enters_content() -> None:
    start = project_start(inputs_for(divided_valley()))
    current = facts(start)
    assert current is not None
    assert start.history is not None
    live = {a.key for a in start.history.state.actors if a.living}
    assert {c.history_actor for c in start.countries} <= live
    assert {tag for tag, _, _, _ in country_starts(start)} == set(start.history_tags.values())
    with pytest.raises(HistoryError, match="dependencies differ"):
        _ = facts(replace(start, vassals=((start.countries[0].tag, start.countries[1].tag),)))
    broken = replace(start.countries[0], history_actor="absent")
    with pytest.raises(HistoryError, match="historical actors"):
        _ = facts(replace(start, countries=(broken, *start.countries[1:])))
    assert facts(replace(start, history=None)) is None
