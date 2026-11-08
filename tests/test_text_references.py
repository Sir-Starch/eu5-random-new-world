"""The world asks the game only for texts it writes (no key on the screen)."""

from __future__ import annotations

import pytest

from rnw.loc_keys import key_hashes
from rnw.text_references import TextReferenceError, asked_keys, verify

LOC = "main_menu/localization/{language}/rnw_test_l_{language}.yml"
DECISION = "in_game/common/decisions/rnw_history.txt"
EVENTS = "in_game/events/rnw_memory.txt"
FORMABLES = "in_game/common/formable_countries/rnw_formations.txt"
GEOGRAPHY = "in_game/common/scripted_geography/rnw_formations.txt"


def _yaml(language: str, entries: dict[str, str]) -> bytes:
    lines = [f"l_{language}:", *(f' {key}: "{text}"' for key, text in entries.items())]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def _world(texts: dict[str, str], scripts: dict[str, str]) -> dict[str, bytes]:
    outputs = {
        LOC.format(language=language): _yaml(language, texts) for language in ("english", "german")
    }
    outputs.update((path, text.encode("utf-8-sig")) for path, text in scripts.items())
    return outputs


def test_a_decision_needs_its_title_and_description() -> None:
    """Vanilla names a decision ``<key>.title`` and describes it ``<key>.desc``."""
    script = {DECISION: "rnw_our_history = {\n\tallow = { always = yes }\n}\n"}
    with pytest.raises(TextReferenceError, match=r"rnw_our_history\.title"):
        _ = verify(_world({"rnw_our_history": "Our History"}, script), set())
    texts = {"rnw_our_history.title": "Our History", "rnw_our_history.desc": "Read it."}
    assert verify(_world(texts, script), set())["script_text_keys"] == 2


def test_an_event_of_the_events_list_needs_its_entry_and_a_hidden_one_nothing() -> None:
    script = {
        EVENTS: (
            "namespace = rnw_memory\n"
            "rnw_memory.1 = {\n\ttitle = rnw_memory.a.title\n\tdesc = rnw_memory.a.desc\n"
            "\tdynamic_historical_event = { tag = ABC from = 1340.1.1 to = 1380.1.1 }\n"
            "\toption = { name = rnw_memory.a.a }\n}\n"
            "rnw_memory.2 = {\n\ttitle = nothing\n\thidden = yes\n}\n"
        )
    }
    texts = {"rnw_memory.a.title": "T", "rnw_memory.a.desc": "D", "rnw_memory.a.a": "A"}
    with pytest.raises(TextReferenceError, match=r"rnw_memory\.1\.entry"):
        _ = verify(_world(texts, script), set())
    asked = asked_keys(_world(texts, script))[EVENTS]
    assert "nothing" not in asked
    texts["rnw_memory.1.entry"] = "T"
    assert verify(_world(texts, script), set())["script_text_keys"] == 4


def test_a_reference_resolves_to_the_world_or_to_vanilla() -> None:
    texts = {"EZZ": "$rnw_formation_two_shores_name$", "ABC": "$america$ and $EZZ|U$"}
    with pytest.raises(TextReferenceError, match=r"rnw_formation_two_shores_name"):
        _ = verify(_world(texts, {}), key_hashes(("america",)))
    texts["rnw_formation_two_shores_name"] = "Empire of the Two Shores"
    assert verify(_world(texts, {}), key_hashes(("america",)))["text_references"] == 6


def test_a_formable_names_its_country_and_every_geography_of_its_file() -> None:
    """The game asked for every geography of the formables' file, used or not."""
    scripts = {
        FORMABLES: (
            "rnw_realm_1_f = {\n\tname = ABC\n\tadjective = ABC_ADJ\n"
            "\tform_effect = { scripted_geography:rnw_realm_1_f_geography = { } }\n}\n"
        ),
        GEOGRAPHY: (
            "rnw_realm_1_f_geography = { region = { r } }\n"
            "rnw_realm_1_f_geography_atlantic_ocean_continent = { location = { a } }\n"
        ),
        "in_game/common/scripted_geography/rnw_treaty_longitudes.txt": "rnw_bit_0 = { }\n",
    }
    texts = {"rnw_realm_1_f": "$ABC$", "ABC": "Realm", "ABC_ADJ": "Realmish"}
    texts["rnw_realm_1_f_geography"] = "$ABC$"
    with pytest.raises(TextReferenceError, match=r"atlantic_ocean_continent"):
        _ = verify(_world(texts, scripts), set())
    texts["rnw_realm_1_f_geography_atlantic_ocean_continent"] = "Atlantic Coast"
    assert verify(_world(texts, scripts), set())["script_text_keys"] == 6


def test_every_language_is_checked() -> None:
    outputs = _world({"rnw_our_history.title": "T", "rnw_our_history.desc": "D"}, {})
    outputs[DECISION] = b"rnw_our_history = { }\n"
    outputs[LOC.format(language="german")] = _yaml("german", {"rnw_our_history.title": "T"})
    with pytest.raises(TextReferenceError, match=r"german: rnw_our_history\.desc"):
        _ = verify(outputs, set())
