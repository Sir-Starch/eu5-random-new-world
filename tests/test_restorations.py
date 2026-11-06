"""The restorations of fallen realms (history plan §22, N7): heights, heirs, files and reasons."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw import wording
from rnw.content import (
    RESTORATION,
    RESTORATION_PLACES,
    Facts,
    Fallen,
    HistoricalFacts,
    Place,
    State,
    plan_content,
    restorations,
)
from rnw.eu5_formation import (
    RESTORATION_FILE,
    Identity,
    block,
    files,
    key_of,
    restoration_event,
    texts,
)
from rnw.eu5_history_plan import project_start
from rnw.formations import BY_FAMILY, HEIRS_TOOLTIP, RESTORATION_EVENT
from rnw.game_texts import localize
from rnw.history_content import facts, heights
from rnw.history_model import HistoryError, Transfer
from rnw.pdx import parse

from .history_fixtures import divided_valley
from .test_history_plan import inputs_for

UNION = "h1112_union_55f8ecd58d27ad80_0"


def test_a_realm_is_measured_at_its_height_from_the_recorded_transfers() -> None:
    """The union of the divided valley held all six districts between its union and division."""
    history = divided_valley()
    height = heights(history)
    assert height[UNION] == frozenset({"d0", "d1", "m0", "m1", "u0", "u1"})
    assert len(height["middle"]) == 2


def test_transfers_that_do_not_lead_to_the_holdings_of_1337_are_refused() -> None:
    """A replay that misses a recorded holding is a broken history, not a smaller realm."""
    history = divided_valley()
    events = list(history.events)
    at = max(n for n, event in enumerate(events) if event.effects.transfers)
    last = events[at]
    for transfers in ((), (Transfer("u1", "nobody", "someone"),)):
        changed = replace(last, effects=replace(last.effects, transfers=transfers))
        with pytest.raises(HistoryError, match="holdings of 1337"):
            _ = heights(replace(history, events=(*events[:at], changed, *events[at + 1 :])))


def test_the_divided_union_has_its_three_successors_as_heirs() -> None:
    """Every living country descended from the divided union is its heir, by the map's tags."""
    start = project_start(inputs_for(divided_valley()))
    current = facts(start)
    assert current is not None
    [realm] = current.fallen
    assert realm.key == UNION
    assert realm.places == ("d0", "d1", "m0", "m1", "u0", "u1")
    assert set(realm.heirs) == {country.tag for country in start.countries}
    assert realm.year == 1227
    assert start.history is not None
    assert realm.cause in {event.key for event in start.history.events}


def _facts(fallen: tuple[Fallen, ...], count: int = 12) -> Facts:
    places = {
        f"p{n:02d}": Place(f"p{n:02d}", 100 + n, 0, "city" if n % 4 == 0 else "", "f", f"S{n // 4}")
        for n in range(count)
    }
    states = {f"S{n}": State(f"S{n}", f"p{n * 4:02d}", "f") for n in range(count // 4)}
    history = HistoricalFacts({}, frozenset(), {}, frozenset(), fallen)
    return Facts(places, states, frozenset(), frozenset(), history=history)


def _fallen(key: str, places: range, heirs: tuple[str, ...], rank: int = 1) -> Fallen:
    return Fallen(
        key, f"p{places[0]:02d}", tuple(f"p{n:02d}" for n in places), heirs, rank, 1200, "e"
    )


def test_a_fallen_realm_with_two_heirs_is_restored_over_its_old_land() -> None:
    """The heirs are the claimants and the old seat stays the seat."""
    found, passed = restorations(_facts((_fallen("old", range(8), ("S0", "S1")),)))
    assert not passed
    [restored] = found
    assert restored.family == RESTORATION
    assert restored.states == ("S0", "S1")
    assert restored.places == tuple(f"p{n:02d}" for n in range(8))
    assert restored.seat == "p00"
    assert restored.basis == "old"


def test_every_fallen_realm_without_a_restoration_has_its_reason() -> None:
    """N-C5: one heir, an outgrown heir, too little land and an overlap are each recorded."""
    fallen = (
        _fallen("big", range(12), ("S0", "S1", "S2")),
        _fallen("inside", range(4, 12), ("S1", "S2")),
        _fallen("alone", range(8), ("S0",)),
        _fallen("crowned", range(8), ("S0", "S1"), rank=3),
        _fallen("small", range(RESTORATION_PLACES - 1), ("S0", "S1")),
    )
    found, passed = restorations(_facts(fallen))
    assert [formation.basis for formation in found] == ["big"]
    reasons = dict(passed)
    assert set(reasons) == {"inside", "alone", "crowned", "small"}
    assert "larger restoration" in reasons["inside"]
    assert "heirs" in reasons["alone"]
    assert "kingdom" in reasons["crowned"]
    assert "inhabited" in reasons["small"]
    plan = plan_content(_facts(fallen), 7)
    assert dict(plan.passed) == reasons


def _restored() -> tuple[Identity, str]:
    formation = restorations(_facts((_fallen("old", range(8), ("S0", "S1")),)))[0][0]
    identity = Identity(
        "RST",
        wording.Phrase(wording.FORMATION + "restoration", "Tlacoyan"),
        wording.adjective("Tlacoyan"),
        (1, 2, 3),
        ("red", "blue"),
    )
    return identity, block(formation, identity)


def test_only_the_heirs_may_restore_it_and_the_others_are_asked() -> None:
    """The potential names the heirs by any tag they had; the formation summons the others."""
    formation = restorations(_facts((_fallen("old", range(8), ("S0", "S1")),)))[0][0]
    identity, text = _restored()
    entry = parse(text).block(key_of(formation))
    assert entry is not None
    potential = entry.block("potential", "OR")
    assert potential is not None
    assert [item.value for item in potential.find("has_or_had_tag")] == ["S0", "S1"]
    assert f"custom_tooltip = {HEIRS_TOOLTIP}" in text
    effect = entry.block("form_effect")
    assert effect is not None
    hidden = [item.value for item in effect.find("hidden_effect")]
    summons = next(
        (
            found
            for found in (
                item.block("every_country") for item in hidden if not isinstance(item, str)
            )
            if found is not None
        ),
        None,
    )
    assert summons is not None
    fired = summons.block("trigger_event_non_silently")
    assert fired is not None
    event = fired.first("id")
    assert event is not None
    assert event.value == restoration_event(formation) == f"{RESTORATION_EVENT}.1"
    assert "NOT = { this = root }" in text
    assert BY_FAMILY[RESTORATION].level == 3
    assert "add_core = root" in text
    assert identity.tag in files([formation], [identity])[RESTORATION_FILE]


def test_an_heir_recognizes_the_restoration_or_becomes_its_rival() -> None:
    """The event names the restored country by its tag; each answer has its price."""
    formation = restorations(_facts((_fallen("old", range(8), ("S0", "S1")),)))[0][0]
    identity, _ = _restored()
    script = files([formation], [identity])[RESTORATION_FILE]
    event = parse(script).block(restoration_event(formation))
    assert event is not None
    trigger = event.block("trigger")
    assert trigger is not None
    exists = trigger.first("country_exists")
    assert exists is not None
    assert exists.value == "c:RST"
    options = [entry.value for entry in event.find("option")]
    assert len(options) == 2
    recognize, contest = options
    assert not isinstance(recognize, str)
    assert not isinstance(contest, str)
    assert recognize.first("add_rival") is None
    rival = contest.first("add_rival")
    assert rival is not None
    assert rival.value == "scope:restorer"
    written = localize(texts([formation], [identity]), "russian")
    assert written["RST"] == "Возрождённое Тлакоянское царство"
    assert "[restorer.GetNameWithNoTooltip]" in written[f"{RESTORATION_EVENT}.desc"]
    assert written[HEIRS_TOOLTIP]
