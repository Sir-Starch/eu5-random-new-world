"""Neutralizing and rebinding the scripts that carry the content decisions (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.content_check import check_decisions
from rnw.content_decisions import TABLE, Decision, Verdict
from rnw.content_inventory import Consumer
from rnw.eu5_content import (
    ContentError,
    Place,
    Scripts,
    carry_out,
    guard_targets,
    guard_text,
    matches,
    places,
    rebind_discovery,
    rebind_game_start,
    selector_of,
)
from rnw.eu5_remap import script_files
from rnw.geography import Location
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

EVENTS = """namespace = ev

ev.1 = { # has a trigger
\ttype = country_event
\ttrigger = {
\t\tcurrent_year > 1500
\t}
\toption = { name = ev.1.a }
}
ev.2 = { # has none
\ttype = country_event
\toption = { name = ev.2.a }
}
ev.3 = { type = country_event trigger = { tag = ABC } }
ev.4 = { type = country_event }
ev.2 = { type = country_event }
"""


def test_discovery_uses_current_coastal_areas_and_preserves_other_triggers() -> None:
    text = (
        "before = { always = yes }\n"
        "discovered_any_in_americas_trigger = { OR = { "
        "has_discovered_area = area:removed_coast } }\n"
        "after = { always = no }\n"
    )
    rewritten = rebind_discovery(text, ["new_coast", "existing_coast", "new_coast"])
    assert rewritten.startswith("before = { always = yes }\n")
    assert rewritten.endswith("after = { always = no }\n")
    assert "removed_coast" not in rewritten
    gate = parse(rewritten).block("discovered_any_in_americas_trigger")
    assert gate is not None
    areas = gate.block("OR")
    assert areas is not None
    assert [entry.value for entry in areas.entries] == ["area:existing_coast", "area:new_coast"]


def test_discovery_rebinding_requires_its_installed_anchor_and_nonempty_water() -> None:
    with pytest.raises(ContentError, match="expected OR"):
        _ = rebind_discovery("unrelated = { always = yes }", ["coast"])
    with pytest.raises(ContentError, match="shape changed"):
        _ = rebind_discovery(
            "discovered_any_in_americas_trigger = { OR = { always = yes } }", ["coast"]
        )
    with pytest.raises(ContentError, match="expected OR"):
        _ = rebind_discovery("discovered_any_in_americas_trigger = { OR = {} }", [])


def test_a_gate_is_closed_in_the_block_vanilla_gives_it() -> None:
    """An existing trigger gets ``always = no``; a missing one is written; others stay."""
    text, count = guard_text(EVENTS, {"ev.1", "ev.2", "ev.3"}, "trigger")
    assert count == 4  # ev.2 is defined twice
    assert "trigger = {\n\t\talways = no\n\t\tcurrent_year > 1500\n\t}" in text
    assert "\toption = { name = ev.2.a }\n\ttrigger = { always = no }\n}" in text
    assert "ev.3 = { type = country_event trigger = {\n\t\talways = no tag = ABC } }" in text
    assert "ev.4 = { type = country_event }\n" in text  # untouched
    assert text.count("always = no") == 4
    assert parse(text).entries  # still reads


def test_a_one_line_object_without_the_gate_gets_one_inline() -> None:
    """The closing brace shares the line, so the gate is written before it, not on a new line."""
    text, count = guard_text("x = { a = b }\n", {"x"}, "potential")
    assert count == 1
    assert text == "x = { a = b potential = { always = no } }\n"


def test_a_gate_that_is_not_a_block_is_refused() -> None:
    """A scalar where a block is expected means the file is not what the table was made for."""
    with pytest.raises(ContentError, match="trigger is not a block"):
        _ = guard_text("x = { trigger = yes }\n", {"x"}, "trigger")


def _consumer(category: str, ident: str, *files: str) -> tuple[str, Consumer]:
    consumer = Consumer(category, ident, files, {})
    return consumer.key, consumer


def test_only_neutralized_identities_and_the_canal_are_guarded() -> None:
    """Rows that keep, rebind, retire or are inert get no gate; an ungated category is skipped."""
    rows = dict(
        [
            _consumer("events", "a.1", "f.txt"),
            _consumer("events", "a.2", "f.txt"),
            _consumer("events", "a.3", "f.txt"),
            _consumer("common/decisions", "canal", "d.txt"),
            _consumer("gfx/map", "panama_canal", "g.txt"),
            _consumer("common/advances", "gone", "a.txt"),
        ]
    )
    verdicts: dict[str, Verdict | None] = {
        "events:a.1": Verdict(Decision.NEUTRALIZE, "identity"),
        "events:a.2": Verdict(Decision.KEEP, "generic"),
        "events:a.3": Verdict(Decision.REPLACE, "retired", "N3"),
        "common/decisions:canal": Verdict(Decision.NEUTRALIZE, "canal"),
        "gfx/map:panama_canal": Verdict(Decision.NEUTRALIZE, "canal"),
        "common/advances:gone": Verdict(Decision.REPLACE, "identity", "N4"),
    }
    found = {(t.category, t.ident, t.gate) for t in guard_targets(rows, verdicts)}
    assert found == {
        ("events", "a.1", "trigger"),
        ("common/decisions", "canal", "potential"),
        ("common/advances", "gone", "potential"),
    }
    stray = dict([_consumer("common/estates", "x", "e.txt")])
    with pytest.raises(ContentError, match="neither gated nor ungated"):
        _ = guard_targets(stray, {"common/estates:x": Verdict(Decision.NEUTRALIZE, "identity")})


def _pop(size: str, culture: str, religion: str) -> str:
    row = f"\tdefine_pop = {{\ttype = peasants\tsize = {size}\tculture = {culture}\t"
    return row + f"religion = {religion} }}"


POPS = {
    "l_a": [_pop("5.000", "nahua", "nahuatl")],
    "l_b": [
        _pop("9.000", "nahua", "nahuatl"),
        _pop("1.000", "other", "folk"),
    ],
    "l_c": [_pop("2.000", "nahuatl_kin", "folk")],
    "l_d": [_pop("0.500", "other", "folk")],
}
TRAITS: dict[str, tuple[str, frozenset[str]]] = {
    "nahua": ("nahuatl_language", frozenset({"mexica_group"})),
    "nahuatl_kin": ("nahuatl_language", frozenset()),
    "other": ("other_language", frozenset()),
}


def test_places_hold_the_culture_and_religion_that_have_most_of_them() -> None:
    """A diaspora line does not change what a location is."""
    found = {place.key: place for place in places(POPS)}
    assert found["l_b"] == Place("l_b", "nahua", "nahuatl", 10_000)
    assert found["l_c"].culture == "nahuatl_kin"


def test_a_selector_reads_culture_language_group_and_religion_from_a_potential() -> None:
    """The cultures a formable asks for are those it names, by key, language or group."""
    selector = selector_of(
        """potential = { OR = { culture = culture:nahua culture.language = language:maya
        culture = { has_culture_group = culture_group:mexica_group } religion = religion:x } }"""
    )
    assert selector.cultures == {"nahua"}
    assert selector.languages == {"maya"}
    assert selector.groups == {"mexica_group"}
    assert selector.religions == {"x"}
    by_language = selector_of("potential = { culture.language = language:nahuatl_language }")
    assert [p.key for p in places(POPS) if matches(by_language, p, TRAITS)] == ["l_a", "l_b", "l_c"]
    by_religion = selector_of("potential = { religion = religion:nahuatl }")
    assert [p.key for p in places(POPS) if matches(by_religion, p, TRAITS)] == ["l_a", "l_b"]


GAME_START = """on_game_start = {
\teffect = {
\t\tOR = {
\t\t\tNOT = { this = god:x }
\t\t\tAND = {
\t\t\t\tthis = god:x
\t\t\t\tscope:current_country = location:old_seat.owner
\t\t\t}
\t\t}
\t}
}
"""


def _scripts(root: Path, relative: str, text: str) -> Scripts:
    path = root / "game" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(b"\xef\xbb\xbf" + text.encode())
    return Scripts(script_files(root), {})


def test_the_start_effect_finds_the_seat_or_can_never_hold(tmp_path: Path) -> None:
    """With a seat the clause names it; without one the clause is ``always = no``."""
    file = "in_game/common/on_action/_hardcoded.txt"
    store = _scripts(tmp_path, file, GAME_START)
    assert rebind_game_start(store, file, old_seat="old_seat", seat="new_seat")
    assert "scope:current_country = location:new_seat.owner" in store.read(file)
    store = _scripts(tmp_path, file, GAME_START)
    assert not rebind_game_start(store, file, old_seat="old_seat", seat=None)
    assert "\t\t\t\talways = no\n" in store.read(file)
    with pytest.raises(ContentError, match=r"no longer names location:elsewhere\.owner"):
        _ = rebind_game_start(store, file, old_seat="elsewhere", seat="x")
    assert store.changed()[file].startswith(b"\xef\xbb\xbf")  # the byte order mark stays


DEFINITIONS = """america = {
\tnorth_america = {
\t\tr_one = {
\t\t\ta_one = { p_one = { v1 v2 v3 v4 v5 v6 } }
\t\t}
\t}
}
europe = { western_europe = { r_eu = { a_eu = { p_eu = { loc_eu } } } } }
"""
COUNTRIES = "countries = { countries = { AAA = { own_control_core = { v1 } } } }\n"
FORMABLES = """XXX_f = {
\tlevel = 3
\trequired_locations_fraction = 0.75
\tpotential = {
\t\tculture.language = language:nahuatl_language
\t}
\tallow = {
\t\towns = location:v2
\t}
\tname = XXX
\tregions = {
\t\tr_one
\t}
\tform_effect = { }
}
YYY_f = {
\tpotential = { culture = culture:rare }
\tareas = {
\t\ta_one
\t}
}
ZZZ_f = {
\tpotential = { always = yes }
\tregions = { r_one }
}
"""
CULTURES = """nahua = { language = nahuatl_language culture_groups = { mexica_group } }
nahuatl_kin = { language = nahuatl_language }
rare = { language = rare_language }
"""
START = GAME_START.replace("old_seat", "v1")
KNOWN = """trap.1 = { type = country_event trigger = { owns = location:v1 } }
trap.2 = { type = country_event }
"""


def _install(root: Path) -> Path:
    game = root / "game"
    for relative, text in {
        "in_game/map_data/definitions.txt": DEFINITIONS,
        "main_menu/setup/1337/10_countries.txt": COUNTRIES,
        "in_game/setup/countries/00_countries.txt": "AAA = { color = red }\n",
        "in_game/common/formable_countries/00.txt": FORMABLES,
        "in_game/common/cultures/c.txt": CULTURES,
        "in_game/common/on_action/_hardcoded.txt": START,
        "in_game/events/known.txt": KNOWN,
    }.items():
        path = game / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
    return root


def test_decisions_are_carried_out_on_the_scripts_of_a_world(tmp_path: Path) -> None:
    """A culture's formable takes its places; a thin one is closed; guarded objects stay."""
    root = _install(tmp_path)
    patched = {
        **TABLE,
        "common/formable_countries:XXX_f": Verdict(Decision.REBIND, "culture", "N1"),
        "common/formable_countries:YYY_f": Verdict(Decision.REBIND, "culture", "N1"),
        "common/formable_countries:ZZZ_f": Verdict(Decision.NEUTRALIZE, "identity"),
        "common/on_action:on_game_start": Verdict(Decision.REBIND, "culture", "N1"),
        "events:trap.1": Verdict(Decision.NEUTRALIZE, "identity"),
        "events:trap.2": Verdict(Decision.KEEP, "generic"),
    }
    checked = check_decisions(root, events=[], modifiers=[], removed_tags=[], table=patched)
    hierarchy = {
        key: Location(key, "america", "north_america", "r_one", "a_one", "p_one")
        for key in ("v1", "v2", "v3", "v4", "v5", "v6")
    }
    pops = {
        "g1": [_pop("9.000", "nahua", "nahuatl")],
        "g2": [_pop("7.000", "nahua", "nahuatl")],
        "g3": [_pop("3.000", "nahuatl_kin", "folk")],
        "g4": [_pop("1.000", "nahua", "nahuatl")],
        "g5": [_pop("1.000", "rare", "folk")],
    }
    scripts: dict[str, bytes] = {}
    stats = carry_out(root, scripts, checked, pops, hierarchy, {"tenochtitlan": "v1"})
    assert stats["formables_too_thin"] == ["YYY_f"]
    assert stats["game_start_bound"] is True
    formables = scripts["in_game/common/formable_countries/00.txt"].decode()
    assert "locations = {\n\t\tg1 g2 g3 g4\n\t}" in formables  # four of the six, the most populous
    assert "owns = location:g1" in formables  # the seat of the culture
    assert "regions = {\n\t\tr_one" not in formables.split("YYY_f")[0]
    assert formables.count("always = no") == 2  # the thin culture's formable and ZZZ_f
    events = scripts["in_game/events/known.txt"].decode()
    assert "trigger = {\n\t\talways = no owns = location:v1" in events
    assert "trap.2 = { type = country_event }" in events


def test_every_edit_the_table_asks_for_has_a_way_to_be_made() -> None:
    """Rows that neutralize have a gate (or need none); rows that rebind are known cases."""
    from rnw.content_decisions import TABLE  # noqa: PLC0415 - module level import cycles in tests.
    from rnw.eu5_content import GATES, NEUTRALIZED_REASONS, UNGATED  # noqa: PLC0415

    for key, verdict in TABLE.items():
        category = key.split(":", 1)[0]
        if verdict.decision in {Decision.NEUTRALIZE, Decision.REPLACE} and (
            verdict.reason in NEUTRALIZED_REASONS
        ):
            assert category in GATES or category in UNGATED, key
        if verdict.decision is Decision.REBIND:
            assert category == "common/formable_countries" or key in {
                "common/on_action:on_game_start",
                "common/scripted_triggers:discovered_any_in_americas_trigger",
            }
