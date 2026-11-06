"""The events of the recorded past (history plan §22, N9): selection, causes (N-C6) and script."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from rnw.content import RESTORATION, ContentPlan, Fallen, Formation
from rnw.eu5_memories import (
    RecallError,
    check_installation,
    event_id,
    events,
    restorations,
    select,
    stats,
    texts,
)
from rnw.eu5_start import HistoricalOpinion
from rnw.game_texts import localize
from rnw.history_model import Action, Bond, Factor
from rnw.memory_texts import FAMILIES, HEIR, KIN, LOST_LAND, OLD_PACT, SHRINE, TEXTS
from rnw.pdx import parse

from .history_fixtures import divided_valley
from .test_history_plan import inputs_for

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.eu5_start import FinalStartPlan


def _start() -> FinalStartPlan:
    from rnw.eu5_history_plan import project_start  # noqa: PLC0415 - the heavy part, once

    return project_start(inputs_for(divided_valley()))


def _opinion(  # noqa: PLR0913, PLR0917 - one projected memory is these few fields
    first: str, second: str, factor: Factor, action: Action, cause: str, value: int, place: str = ""
) -> HistoricalOpinion:
    return HistoricalOpinion("k", first, second, factor, value, 1, cause, 1300, action, place)


def test_each_country_recalls_its_strongest_qualifying_memory_once() -> None:
    """Grievance with a place is lost land, a pact's trust an old pact, a migration kin; the
    strongest wins and a memory of no family (fear) is no event."""
    start = _start()
    assert start.history is not None
    cause = start.history.events[-1].key
    a, b, c = (country.tag for country in start.countries)
    place = next(iter(start.names))
    opinions = (
        _opinion(a, b, Factor.GRIEVANCE, Action.CONFLICT, cause, -40, place),
        _opinion(a, c, Factor.TRUST, Action.PACT, cause, 10),
        _opinion(b, c, Factor.TRUST, Action.PROTECTION, cause, 20),
        _opinion(c, a, Factor.AFFINITY, Action.MIGRATION, cause, 30, place),
        _opinion(c, b, Factor.FEAR, Action.CONFLICT, cause, -50, place),
    )
    found = select(replace(start, historical_opinions=opinions), ContentPlan((), (), ()), (), 7)
    by_bearer = {memory.bearer: memory for memory in found}
    assert by_bearer[a].family == LOST_LAND
    assert by_bearer[a].partner == b
    assert by_bearer[a].place == place
    assert by_bearer[b].family == OLD_PACT
    assert by_bearer[c].family == KIN
    assert len(found) == 3
    for memory in found:
        assert 1338 <= memory.start < memory.until
        assert memory.cause == cause


def test_a_shrine_is_the_place_of_its_recorded_agreement() -> None:
    """An access memory names no place of its own; the bond of its event does."""
    start = _start()
    assert start.history is not None
    a, b, _ = (country.tag for country in start.countries)
    place = next(iter(start.names))
    last = start.history.events[-1]
    actor = start.history.state.actors[0].key
    shrine = replace(
        last,
        key="h_access",
        effects=replace(last.effects, bonds=(Bond(Action.ACCESS, actor, actor, "x", place),)),
    )
    history = replace(start.history, events=(*start.history.events, shrine))
    opinion = _opinion(a, b, Factor.TRUST, Action.ACCESS, "h_access", 25)
    found = select(
        replace(start, history=history, historical_opinions=(opinion,)),
        ContentPlan((), (), ()),
        (),
        7,
    )
    assert [(memory.family, memory.place) for memory in found] == [(SHRINE, place)]


def test_every_heir_of_a_restoration_remembers_the_old_realm() -> None:
    """N-C6: each heir's event names the division that is its cause, at the restoration's seat."""
    start = _start()
    restored = Formation(RESTORATION, 0, ("d0", "d1"), ("d0",), ("JAM", "OVB"), "d0", "old")
    realm = Fallen("old", "d0", ("d0", "d1"), ("JAM", "OVB"), 1, 1227, "h1227_division")
    found = select(start, ContentPlan((), (restored,), ()), (realm,), 7)
    heirs = [memory for memory in found if memory.family == HEIR]
    assert [memory.bearer for memory in heirs] == ["JAM", "OVB"]
    assert all(memory.cause == "h1227_division" and memory.place == "d0" for memory in heirs)
    assert all(memory.realm == 0 for memory in heirs)
    assert [entry["cause"] for entry in stats(heirs)] == ["h1227_division"] * 2


def test_the_events_ask_their_conditions_and_give_vanilla_effects() -> None:
    """A lost land asks that the other still holds it and offers a core; an heir's event ends
    once the realm is restored; every event fires once in its own window."""
    start = _start()
    assert start.history is not None
    cause = start.history.events[-1].key
    a, b, _ = (country.tag for country in start.countries)
    place = next(iter(start.names))
    opinions = (_opinion(a, b, Factor.GRIEVANCE, Action.CONFLICT, cause, -40, place),)
    restored = Formation(RESTORATION, 0, ("d0", "d1"), ("d0",), ("JAM", "OVB"), "d0", "old")
    realm = Fallen("old", "d0", ("d0", "d1"), ("JAM", "OVB"), 1, 1227, cause)
    memories = select(
        replace(start, historical_opinions=opinions),
        ContentPlan((), (restored,), ()),
        (realm,),
        7,
    )
    tags = restorations([restored], ["RST"])
    script = events(memories, tags)
    root = parse(script)
    lost = root.block(event_id(1))
    assert lost is not None
    window = lost.block("dynamic_historical_event")
    assert window is not None
    bearer = window.first("tag")
    assert bearer is not None
    assert bearer.value == a
    assert f"location:{place} = {{ owner ?= c:{b} }}" in script
    assert f"location:{place} = {{ add_core = root }}" in script
    heir = root.block(event_id(2))
    assert heir is not None
    assert "NOT = { country_exists = c:RST }" in script
    assert "fire_only_once = yes" in script
    for language in ("english", "russian", "turkish"):
        written = localize(texts(memories), language)
        assert written
        assert all("{" not in text for text in written.values())


def test_every_family_has_its_texts() -> None:
    """Title, description and two options for each family."""
    for family in FAMILIES:
        for part in ("title", "desc", "a", "b"):
            assert f"rnw_memory.{family}.{part}" in TEXTS


def test_a_bias_or_value_the_game_lacks_stops_the_export(tmp_path: Path) -> None:
    """The vanilla opinions and values the events name are checked against the installation."""
    biases = tmp_path / "game/in_game/common/biases/00.txt"
    biases.parent.mkdir(parents=True)
    _ = biases.write_text(
        "opinion_good_relations = { }\nopinion_refused_claim = { }\n", encoding="utf-8"
    )
    values = tmp_path / "game/main_menu/common/script_values/00.txt"
    values.parent.mkdir(parents=True)
    text = "prestige_weak_bonus = 5\nprestige_weak_penalty = -5\nstability_weak_bonus = 2\n"
    _ = values.write_text(text, encoding="utf-8")
    check_installation(tmp_path)
    _ = values.write_text("prestige_weak_bonus = 5\n", encoding="utf-8")
    with pytest.raises(RecallError, match="prestige_weak_penalty"):
        check_installation(tmp_path)
