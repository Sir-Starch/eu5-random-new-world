"""The society panel's data: a timeline, traits, opinions and a region, apart from the prose."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest

from rnw import atlas, eu5_history_text, game_texts, history_text, translations
from rnw.eu5_history_plan import project_start
from rnw.eu5_history_values import profile_positions
from rnw.gui.view import history_data
from rnw.history_archive import AimFact
from rnw.history_model import (
    Authority,
    Exchange,
    Livelihood,
    Military,
    Society,
    Strategy,
    TrajectoryKind,
)
from rnw.history_presenter import YEAR_PREFIX, Reader, encode
from rnw.history_values import AXES as VALUE_AXES
from rnw.history_values import SHOWN, SOURCE
from rnw.loc_keys import KeySpace, key_hashes

from .history_fixtures import divided_valley
from .test_history_archive import history_atlas, places
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


def test_the_society_shows_the_game_and_none_of_the_models_traits(built: atlas.Atlas) -> None:
    """Government and rank under the game's names; no technology level or trait meter, which
    the game does not show (plan D31)."""
    history = record(built)
    names = {"monarchy": "Monarchy", "republic": "Republic", "tribe": "Tribe", "theocracy": "T"}
    reader = Reader(built, "english", lambda key: names.get(key, key))
    for country in history.countries:
        dossier = reader.dossier(country.tag)
        assert dossier is not None
        assert dossier.government == names.get(country.government, country.government)
        # A setup that names no rank leaves the game's default, the county (C500).
        assert dossier.rank == (country.rank or "rank_county")
        assert not hasattr(dossier, "axes")
        assert not hasattr(dossier, "technology")
    lines = [line.text for line in reader.country(history.countries[0].tag)[0].lines]
    assert "Technology" not in lines[1]
    assert all(not line.startswith(("Centralization", "Authority", "Livelihood")) for line in lines)


def test_a_dossier_is_plain_json_and_the_text_sections_are_unchanged(built: atlas.Atlas) -> None:
    reader = Reader(built, "english", atlas.pretty)
    tag = record(built).countries[0].tag
    dossier = reader.dossier(tag)
    assert dossier is not None
    sent = cast("dict[str, object]", json.loads(json.dumps(encode(dossier))))
    assert set(sent) == {
        "government",
        "rank",
        "origin",
        "values",
        "chronicle",
        "partners",
        "more",
        "story_title",
        "story",
    }
    assert isinstance(sent["chronicle"], list)
    assert sent["story_title"] == "Our History"
    assert isinstance(sent["story"], list)
    assert sent["story"]
    titles = [section.title for section in reader.country(tag)]
    assert titles == ["Society in 1337", "Opinions on the first day", "Our History", "Chronicle"]


def test_each_side_of_a_treaty_has_the_engines_opinion_of_the_other(built: atlas.Atlas) -> None:
    """``vassal`` is (overlord, subject), ``guarantee`` (guarantor, protected), ``rival`` (the
    country that rivals, its rival); an exchange of goods gives the engine no opinion."""
    history = record(built)
    first, second, third = (country.actor for country in history.countries)
    tags = {country.actor: country.tag for country in history.countries}
    relations = (
        ("vassal", first, second),
        ("guarantee", second, third),
        ("alliance", first, third),
        ("exchange", first, third),
        ("rival", third, second),
    )
    reader = Reader(
        replace(built, history=replace(history, relations=relations, biases=())),
        "english",
        lambda key: key,
    )

    def lines(viewer: int, partner: int) -> list[tuple[str, int]]:
        dossier = reader.dossier(tags[viewer])
        assert dossier is not None
        return [
            (line.label, line.value)
            for found in dossier.partners
            if found.tag == tags[partner]
            for line in found.opinions
        ]

    assert lines(first, second) == [("vassal_overlord_opinion", 100)]
    assert lines(second, first) == [("vassal_subject_opinion", 50)]
    assert lines(second, third) == [("opinion_giving_guarantee", 5)]
    assert lines(third, second) == [("opinion_receiving_guarantee", 10), ("opinion_rival", -100)]
    assert lines(first, third) == [("opinion_alliance", 50)]
    assert lines(third, first) == [("opinion_alliance", 50)]
    dossier = reader.dossier(tags[third])
    assert dossier is not None
    assert [partner.total for partner in dossier.partners] == [-90, 50]


def test_a_historical_line_is_named_as_the_game_names_its_opinion(built: atlas.Atlas) -> None:
    """The window's line is the opinion's localized name in the written world, value and decay."""
    plan = project_start(inputs_for(divided_valley()))
    written = eu5_history_text.build(plan, KeySpace(key_hashes(plan.names)), places(plan))
    game = game_texts.localize(written.texts, "english")
    named = {
        (o.first, o.second, o.value, o.yearly_decay): game[o.key] for o in plan.historical_opinions
    }
    assert named
    reader = Reader(built, "english", atlas.pretty)
    shown: dict[tuple[str, str, int, int], str] = {}
    for country in record(built).countries:
        dossier = reader.dossier(country.tag)
        assert dossier is not None
        for partner in dossier.partners:
            for line in partner.opinions:
                if line.decay:
                    shown[country.tag, partner.tag, line.value, line.decay] = line.label
    assert shown == named


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


def test_each_value_is_projected_from_the_trait_the_window_names() -> None:
    """``SOURCE`` says which trait shaped a value; changing only that trait must move the value."""
    ranges = dict.fromkeys(VALUE_AXES, (-100, 100))
    base = Society()
    variants = {
        "centralization": replace(base, centralization=900),
        "authority": replace(base, authority=Authority.RULER),
        "livelihood": replace(base, livelihood=Livelihood.FARMING),
        "exchange": replace(base, exchange=Exchange.COASTAL),
        "religious_authority": replace(base, religious_authority=900),
        "military": replace(base, military=Military.OFFENSIVE),
        "integration": replace(base, integration=900),
        "tradition": replace(base, tradition=900),
    }
    start = dict(profile_positions(base, ranges))
    for trait, society in variants.items():
        moved = {axis for axis, place in profile_positions(society, ranges) if place != start[axis]}
        assert moved == {axis for axis, source in SOURCE.items() if source == trait}, trait


def test_the_dossier_shows_the_values_the_game_is_given(built: atlas.Atlas) -> None:
    reader = Reader(built, "english", atlas.pretty)
    history = record(built)
    for country in history.countries:
        dossier = reader.dossier(country.tag)
        assert dossier is not None
        written = {
            axis: value
            for axis, value in zip(VALUE_AXES, country.values, strict=True)
            if value != -101
        }
        # Every value the game shows, in its order; the history's own with their cause, the
        # template's without one.
        assert [value.key for value in dossier.values] == list(SHOWN)
        shown = dict(zip(SHOWN, country.shown, strict=True))
        for value in dossier.values:
            assert value.left
            assert value.right
            if value.key in written:
                assert value.position == written[value.key]
                assert value.cause
            else:
                assert value.position == (0 if shown[value.key] == -101 else shown[value.key])
                assert not value.cause


def test_an_archive_without_values_says_so_instead_of_showing_the_models_traits(
    built: atlas.Atlas,
) -> None:
    history = record(built)
    older = replace(
        built,
        history=replace(
            history,
            countries=tuple(replace(c, values=(), shown=()) for c in history.countries),
        ),
    )
    reader = Reader(older, "english", atlas.pretty)
    dossier = reader.dossier(history.countries[0].tag)
    assert dossier is not None
    assert dossier.values == ()
    lines = [line.text for line in reader.country(history.countries[0].tag)[0].lines]
    assert lines[-1].startswith("This world was made before its societal values were recorded")


def test_a_region_shows_only_the_extraordinary_peoples_the_player_can_set(
    built: atlas.Atlas,
) -> None:
    """The ordinary regional aims are the model's own; the extraordinary ones are a setting."""
    history = record(built)
    anchor = history.countries[0].actor
    seat = history.actors[anchor].seat
    cause = history.actors[anchor].origin
    aims = (
        AimFact(
            TrajectoryKind.REGIONAL_POWER, seat, (anchor,), cause, Strategy.PRUDENT, realized=True
        ),
        AimFact(
            TrajectoryKind.GREAT_EMPIRE, seat, (anchor,), cause, Strategy.PRUDENT, realized=False
        ),
    )
    reader = Reader(replace(built, history=replace(history, aims=aims)), "english", atlas.pretty)
    region = reader.place("region")
    assert region is not None
    assert [(aim.kind, aim.realized) for aim in region.ambitions] == [("great_empire", False)]
