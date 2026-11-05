"""The society panel's data: a timeline, traits, standings and a region, apart from the prose."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest

from rnw import atlas, history_text, translations
from rnw.eu5_history_plan import project_start
from rnw.gui.view import history_data
from rnw.history_presenter import STANDING_ORDER, YEAR_PREFIX, Reader, encode

from .history_fixtures import divided_valley
from .test_history_archive import history_atlas
from .test_history_plan import inputs_for

if TYPE_CHECKING:
    from rnw.history_archive import Archive
    from rnw.wording import Name


@pytest.fixture
def built() -> atlas.Atlas:
    return history_atlas(project_start(inputs_for(divided_valley())))


def record(built: atlas.Atlas) -> Archive:
    assert built.history is not None
    return built.history


@pytest.mark.parametrize("language", translations.catalog_languages())
def test_every_chronicle_sentence_opens_with_its_year(language: str) -> None:
    """The timeline draws the year apart; each language's template must keep its leading shape."""
    texts = translations.translate(translations.GAME, language, history_text.sources())
    names = {"year": 1232, "first": "A", "second": "B", "third": "C"}
    for key in history_text.sources():
        if key.startswith("rnw_history_") and key.rsplit("_", 1)[-1] in {"0", "1"}:
            sentence = texts[key].format_map(names)
            assert re.match(YEAR_PREFIX.format(year=1232), sentence), (language, key, sentence)


def test_a_chronicle_row_keeps_its_year_and_place_apart_from_the_sentence(
    built: atlas.Atlas,
) -> None:
    reader = Reader(built, "english", atlas.pretty)
    for country in record(built).countries:
        dossier = reader.dossier(country.tag)
        assert dossier is not None
        assert dossier.chronicle
        years = [row.year for row in dossier.chronicle]
        assert years == sorted(years)
        for row in dossier.chronicle:
            assert not row.text[:1].isdigit()
            assert "Recorded place" not in row.text
            assert row.label
        assert dossier.origin.text


def test_the_traits_are_four_scales_and_four_names(built: atlas.Atlas) -> None:
    reader = Reader(built, "english", atlas.pretty)
    dossier = reader.dossier(record(built).countries[0].tag)
    assert dossier is not None
    assert [axis.key for axis in dossier.axes][:2] == ["centralization", "authority"]
    scales = [axis for axis in dossier.axes if axis.number >= 0]
    names = [axis for axis in dossier.axes if axis.number < 0]
    assert (len(scales), len(names)) == (4, 4)
    assert all(0 <= axis.number <= 1000 and not axis.word for axis in scales)
    assert all(axis.word and axis.cause for axis in names)


def test_a_dossier_is_plain_json_and_the_text_sections_are_unchanged(built: atlas.Atlas) -> None:
    reader = Reader(built, "english", atlas.pretty)
    tag = record(built).countries[0].tag
    dossier = reader.dossier(tag)
    assert dossier is not None
    sent = cast("dict[str, object]", json.loads(json.dumps(encode(dossier))))
    assert set(sent) == {
        "government",
        "rank",
        "technology",
        "origin",
        "axes",
        "chronicle",
        "partners",
        "more",
    }
    assert isinstance(sent["chronicle"], list)
    titles = [section.title for section in reader.country(tag)]
    assert titles == ["Organization in 1337", "Relationships and reasons", "Chronicle"]


def test_a_partner_is_named_by_its_role_toward_the_viewed_country(built: atlas.Atlas) -> None:
    """``vassal`` is (overlord, subject) and ``guarantee`` (guarantor, protected)."""
    history = record(built)
    first, second, third = (country.actor for country in history.countries)
    tags = {country.actor: country.tag for country in history.countries}
    relations = (
        ("vassal", first, second),
        ("guarantee", second, third),
        ("alliance", first, third),
        ("exchange", first, third),
    )
    reader = Reader(
        replace(built, history=replace(history, relations=relations)), "english", atlas.pretty
    )

    def standing(viewer: int, partner: int) -> list[str]:
        dossier = reader.dossier(tags[viewer])
        assert dossier is not None
        return [s.kind for p in dossier.partners if p.tag == tags[partner] for s in p.standing]

    assert standing(first, second) == ["subject"]
    assert standing(second, first) == ["lord"]
    assert standing(second, third) == ["protected"]
    assert standing(third, second) == ["guarantor"]
    assert standing(first, third) == ["alliance", "trade"]
    assert set(STANDING_ORDER) >= {"lord", "subject", "guarantor", "protected", "alliance", "trade"}


def test_a_region_lists_changes_inheritances_and_aims_with_places(built: atlas.Atlas) -> None:
    reader = Reader(built, "english", atlas.pretty)
    region = reader.place("region")
    assert region is not None
    assert region.changes
    assert all(change.count > 0 and change.place >= 0 for change in region.changes)
    assert all(len(heritage.members) > 1 and heritage.labels for heritage in region.heritage)
    held = [tuple(link.place for link in heritage.members) for heritage in region.heritage]
    assert len(held) == len(set(held))  # one row for each set of societies
    elsewhere = reader.place("elsewhere")
    assert elsewhere is not None
    assert not elsewhere.changes


def test_a_world_without_history_has_no_dossiers(built: atlas.Atlas) -> None:
    reader = Reader(replace(built, history=None), "english", atlas.pretty)
    assert reader.place("region") is None
    assert not reader.countries


def test_the_window_finds_a_region_by_the_name_it_shows(built: atlas.Atlas) -> None:
    """A region's history is stored under the shown name, though the reader names it otherwise."""
    reader = Reader(built, "english", atlas.pretty)
    data = history_data(reader, built, lambda value: f"Shown {reader.name(cast('Name', value))}")
    regions = cast("dict[str, dict[str, object]]", data["regions"])
    assert regions
    assert all(name.startswith("Shown ") for name in regions)
    assert any(summary["changes"] for summary in regions.values())
    countries = cast("dict[str, object]", data["countries"])
    assert set(countries) == {country.tag for country in built.countries}
