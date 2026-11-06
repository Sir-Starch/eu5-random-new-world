"""A name for the new state (history plan §22, N9): the founder's choice between two names."""

from __future__ import annotations

from rnw import wording
from rnw.content import (
    NEW_WORLD_EMPIRE,
    POSTCOLONIAL_FEDERATION,
    REGIONAL_REALM,
    RIVER_UNION,
    Formation,
)
from rnw.eu5_formation import Identity, block
from rnw.eu5_naming import EVENT_FILE, events, fires, namings, other_key, texts
from rnw.game_texts import localize
from rnw.pdx import parse
from rnw.wording import Phrase

NAMES = {"seat": "Kaira", "throne": "Tolan"}
REGIONS = {"east_region": "Laltsu"}


def _union() -> Formation:
    return Formation(RIVER_UNION, 0, ("seat",), ("seat",), ("ABC",), "seat", home="east_region")


def _realm() -> Formation:
    return Formation(
        REGIONAL_REALM,
        0,
        ("throne",),
        ("throne",),
        ("ABC",),
        "throne",
        region="east_region",
        throne="throne",
        home="east_region",
    )


def test_a_seat_named_formation_offers_its_region_and_a_realm_its_throne() -> None:
    """The second name is the one the world has that the first is not; the nation and the
    empire are named otherwise."""
    union = (_union(), "UNI", Phrase(wording.FORMATION + "union", "Kaira"))
    realm = (_realm(), "REA", Phrase(wording.FORMATION + "realm", "Laltsu"))
    nation = Formation(POSTCOLONIAL_FEDERATION, 0, ("seat",), (), (), "seat", home="east_region")
    empire = Formation(NEW_WORLD_EMPIRE, 0, ("seat",), (), (), "seat", continent="america")
    choices = namings(
        [
            union,
            realm,
            (nation, "NAT", Phrase(wording.FORMATION + "federation", "Laltsu")),
            (empire, "EMP", wording.reference("america")),
        ],
        NAMES,
        REGIONS,
    )
    assert set(choices) == {"UNI", "REA"}
    assert choices["UNI"].other == Phrase(wording.FORMATION + "union", "Laltsu")
    assert choices["REA"].other == Phrase(wording.FORMATION + "realm", "Tolan")
    same = (_union(), "SAM", Phrase(wording.FORMATION + "union", "Laltsu"))
    assert namings([same], NAMES, REGIONS) == {}


def test_the_founder_is_asked_and_the_second_name_is_written_in_every_language() -> None:
    """The formation fires the event; its second option renames the country."""
    formation = _union()
    name = Phrase(wording.FORMATION + "union", "Kaira")
    choices = namings([(formation, "UNI", name)], NAMES, REGIONS)
    naming = choices["UNI"]
    identity_text = block(
        formation,
        Identity("UNI", name, wording.adjective("Kaira"), (1, 2, 3), ("red", "blue")),
        fires(naming),
    )
    assert "trigger_event_non_silently = { id = rnw_naming.1 }" in identity_text
    script = events([naming])
    event = parse(script).block("rnw_naming.1")
    assert event is not None
    options = [entry.value for entry in event.find("option")]
    assert len(options) == 2
    second = options[1]
    assert not isinstance(second, str)
    renamed = second.first("change_country_name")
    assert renamed is not None
    assert renamed.value == other_key("UNI")
    assert EVENT_FILE.endswith("rnw_naming.txt")
    written = localize(texts([naming]), "russian")
    assert written[other_key("UNI")] == "Лалцуский союз"
    assert "Кайрский союз" in written["rnw_naming.1.a"]
    assert "Лалцуский союз" in written["rnw_naming.1.b"]
