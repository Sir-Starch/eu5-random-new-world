"""The release check of L1: every text in every language, current against its English source."""

from __future__ import annotations

import tomllib
from importlib import resources
from typing import TYPE_CHECKING, cast

import pytest

from rnw import translations
from rnw.game_texts import Described, Text, localize, sources, untranslated
from rnw.translations import (
    GAME,
    TranslationError,
    catalog_languages,
    dump,
    fingerprint,
    problems,
    scaffold,
    tokens,
    translate,
)
from rnw.wording import Phrase

if TYPE_CHECKING:
    from collections.abc import Callable

# The game's official languages on 1.4.3 and 1.4.4 [V-LOCAL C268]; the local suite checks the
# installation itself (tests/test_local_install.py).
OFFICIAL = (
    "braz_por",
    "english",
    "french",
    "german",
    "japanese",
    "korean",
    "polish",
    "russian",
    "simp_chinese",
    "spanish",
    "turkish",
)


def _fixed(
    entries: dict[str, tuple[str, str]],
) -> Callable[[str, str], dict[str, tuple[str, str]]]:
    def catalog(_domain: str, _language: str) -> dict[str, tuple[str, str]]:
        return entries

    return catalog


def test_every_official_language_has_a_catalog() -> None:
    assert sorted(catalog_languages()) == sorted(OFFICIAL)
    assert untranslated(OFFICIAL) == []
    assert untranslated(("klingon",)) == ["klingon"]


def test_every_game_text_is_translated_and_current_in_every_language() -> None:
    """The release check: nothing missing, stale, empty, quoted or with lost script parts."""
    assert problems(GAME, sources(), OFFICIAL) == []


def test_the_catalogs_are_package_data_and_parse_as_toml() -> None:
    root = resources.files("rnw") / "locale"
    for language in OFFICIAL:
        if language == "english":
            continue
        text = (root / language / f"{GAME}.toml").read_text(encoding="utf-8")
        table = tomllib.loads(text)
        assert set(table) == set(sources()), language


def test_a_change_of_the_english_makes_its_translations_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    english = {"key": "The river turns."}
    entries = {"key": (fingerprint("The river turns."), "Река меняет русло.")}
    monkeypatch.setattr(translations, "catalog", _fixed(entries))
    assert translate(GAME, "russian", english) == {"key": "Река меняет русло."}
    with pytest.raises(TranslationError, match="stale"):
        _ = translate(GAME, "russian", {"key": "The river turned."})
    with pytest.raises(TranslationError, match="missing"):
        _ = translate(GAME, "russian", {"other": "Text"})
    assert translate(GAME, "english", english) == english
    assert problems(GAME, {"key": "The river turned."}, ["russian"]) == ["russian: key is stale"]


def test_the_check_finds_lost_tokens_quotes_and_orphans(monkeypatch: pytest.MonkeyPatch) -> None:
    english = {"a": "In [target_location.GetName] the {name} rose.", "b": "Plain."}
    entries = {
        "a": (fingerprint(english["a"]), "В [target_location.GetName|l] поднялось."),
        "b": (fingerprint("Plain."), 'Просто "так".'),
        "c": ("0", "Сирота."),
    }
    monkeypatch.setattr(translations, "catalog", _fixed(entries))
    found = problems(GAME, english, ["russian"])
    assert any(item.startswith("russian: a changes the scripted parts") for item in found)
    assert 'russian: b holds a straight double quote (")' in found
    assert "russian: c has no English source" in found


def test_a_case_format_is_the_same_scripted_part() -> None:
    assert tokens("[A.GetName|U] and [B] {name} $KEY$") == tokens("[A.GetName] {name} [B] $KEY$")
    assert tokens("[A.GetName]") != tokens("[A.GetAdjective]")


def test_dump_writes_what_toml_reads_back() -> None:
    entries = {
        "rnw_x.1.desc": ("abc", "Line one.\\n\\nLine two, it's here."),
        'odd "key"': ("def", "Ends with an apostrophe'"),
        "tab": ("ghi", "A\ttab"),
    }
    table = cast("dict[str, dict[str, str]]", tomllib.loads(dump(entries)))
    assert {key: (value["source"], value["text"]) for key, value in table.items()} == entries


def test_scaffold_keeps_current_entries_and_adds_empty_ones() -> None:
    english = {"a": "One.", "b": "Two."}
    current = {"a": (fingerprint("One."), "Один."), "z": ("0", "Лишний.")}
    assert scaffold(current, english) == {"a": current["a"], "b": (fingerprint("Two."), "")}


def test_localize_fills_names_into_translated_texts() -> None:
    key = "rnw_formation_river_union_desc"
    entries = {
        "XYZ": Phrase("formation.union", "Kaira"),
        "XYZ_desc": Described(key, Phrase("formation.union", "Kaira")),
        "rnw_river.1.title": Text("rnw_river.1.title"),
    }
    russian = localize(entries, "russian")
    assert russian["XYZ"] == "Кайрский союз"
    assert russian["XYZ_desc"].endswith("— Кайрский союз.")
    assert russian["rnw_river.1.title"] == "Река меняет русло"
    unknown = localize(entries, "klingon")
    assert unknown["rnw_river.1.title"] == "The River Turns"
    assert unknown["XYZ"] == "Kaira Union"
