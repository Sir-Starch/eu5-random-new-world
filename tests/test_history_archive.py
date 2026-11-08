"""Portable historical facts: complete causes, hostile input and common presentation."""

from __future__ import annotations

import base64
import json
import lzma
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import atlas, eu5_history_text, game_texts, history_text
from rnw import history_archive as archive
from rnw.eu5_history_plan import project_start
from rnw.history_archive_checks import validate
from rnw.history_model import TrajectoryKind
from rnw.history_presenter import Reader
from rnw.translations import catalog_languages

from .history_fixtures import divided_valley
from .test_history_plan import inputs_for, realized_network

if TYPE_CHECKING:
    from rnw.eu5_start import FinalStartPlan


@pytest.fixture
def plan() -> FinalStartPlan:
    return project_start(inputs_for(divided_valley()))


def places(plan: FinalStartPlan) -> tuple[str, ...]:
    """The location keys of a test world, as its atlas orders them."""
    assert plan.history is not None
    return tuple(sorted(place.key for place in plan.history.geography.districts))


def history_atlas(plan: FinalStartPlan) -> atlas.Atlas:
    assert plan.history is not None
    keys = places(plan)
    index = {key: number for number, key in enumerate(keys)}
    owners = {
        key: number for number, country in enumerate(plan.countries) for key in country.members
    }
    zero = np.zeros(len(keys), dtype=np.int32)
    return atlas.Atlas(
        1,
        np.arange(1, len(keys) + 1, dtype=np.int32).reshape(1, -1),
        keys,
        tuple(plan.names[key] for key in keys),
        zero.astype(np.uint8),
        ("area",) * len(keys),
        ("region",) * len(keys),
        np.array([owners.get(key, -1) for key in keys], dtype=np.int32),
        zero,
        zero,
        zero,
        zero,
        zero,
        zero,
        zero,
        zero.astype(np.int64),
        zero.astype(np.int64),
        np.zeros((len(keys), 2), dtype=np.int32),
        tuple(
            atlas.Country(c.tag, c.name, c.kind, c.color, index[c.capital], 0, 0, len(c.members))
            for c in plan.countries
        ),
        dict.fromkeys(
            (
                "culture",
                "religion",
                "material",
                "climate",
                "vegetation",
                "topography",
                "settlement",
            ),
            ("word",),
        ),
        archive.build(plan, keys),
    )


def test_portable_roundtrip_replays_the_written_atlas(plan: FinalStartPlan) -> None:
    built = history_atlas(plan)
    assert built.history is not None
    validate(built.history, atlas.history_links(built))
    encoded = archive.pack(built.history)
    assert archive.unpack(encoded) == built.history
    document, picture = atlas.to_files(built)
    restored = atlas.from_files(document, picture)
    assert restored.history == built.history
    assert atlas.to_files(restored) == (document, picture)
    assert json.loads(document)["format"] == 3


@pytest.mark.parametrize("language", catalog_languages())
def test_portable_chronicles_equal_game_chronicles(plan: FinalStartPlan, language: str) -> None:
    """The window tells each country's story as the game's Our History does, word for word,
    and lists the chronicle's events below it."""
    built = history_atlas(plan)
    reader = Reader(built, language, atlas.pretty)
    expected = history_text.chronicles(plan)
    stories = eu5_history_text.stories(plan, places(plan))
    texts = game_texts.localize(dict(stories), language)
    for tag, chronicle in expected.items():
        story, timeline = reader.country(tag)[2:4]
        assert "\\n\\n".join(row.text for row in story.lines) == texts[tag]
        assert story.title == reader.game["rnw_chronicle.1.title"]
        assert [row.text for row in timeline.lines] == [
            history_text.render(row.text, language, reader.game) for row in chronicle.rows
        ]
        assert all(
            -1 <= row.place < built.cells
            for section in reader.country(tag)
            for row in section.lines
        )


@pytest.mark.parametrize("format_number", [1, 2])
def test_legacy_atlases_have_no_invented_history(plan: FinalStartPlan, format_number: int) -> None:
    document, picture = atlas.to_files(history_atlas(plan))
    data = cast("dict[str, object]", json.loads(document))
    data["format"] = format_number
    del data["history"]
    legacy = atlas.from_files(json.dumps(data).encode(), picture)
    assert legacy.history is None
    assert (
        Reader(legacy, "english", atlas.pretty).country("AAA")[0].lines[0].text
        == "No recorded history"
    )


def _ancestors(events: tuple[archive.EventFact, ...], key: int) -> set[int]:
    result: set[int] = set()
    pending = list(events[key].causes)
    while pending:
        current = pending.pop()
        if current not in result:
            result.add(current)
            pending.extend(events[current].causes)
    return result


def test_compaction_preserves_every_causal_ancestor(plan: FinalStartPlan) -> None:
    assert plan.history is not None
    record = archive.build(plan, tuple(sorted(plan.names)))
    original = plan.history.events
    actor_keys = sorted(actor.key for actor in plan.history.state.actors)
    mapping: dict[int, str] = {}
    by_key = {candidate.key: candidate for candidate in original}
    for number, event in enumerate(record.events):
        candidates = [
            candidate
            for candidate in original
            if (candidate.year, candidate.kind, candidate.outcome, candidate.actors)
            == (event.year, event.kind, event.outcome, tuple(actor_keys[i] for i in event.actors))
        ]
        assert len(candidates) == 1
        mapping[number] = candidates[0].key
    for number, original_key in mapping.items():
        pending = list(by_key[original_key].causes)
        found: set[str] = set()
        while pending:
            key = pending.pop()
            if key not in found:
                found.add(key)
                pending.extend(by_key[key].causes)
        assert {mapping[i] for i in _ancestors(record.events, number)} == found


@pytest.mark.parametrize(
    "mutation", ["cycle", "missing", "chronology", "owner", "profile", "lineage"]
)
def test_import_rejects_broken_references_and_replay(plan: FinalStartPlan, mutation: str) -> None:
    built = history_atlas(plan)
    record = built.history
    assert record is not None
    if mutation in {"cycle", "missing", "chronology"}:
        number = len(record.events) - 1
        event = record.events[number]
        event = (
            replace(event, causes=(number if mutation == "cycle" else len(record.events),))
            if mutation != "chronology"
            else replace(event, year=1037)
        )
        record = replace(record, events=(*record.events[:number], event))
    elif mutation == "owner":
        record = replace(record, changes=record.changes[1:])
    elif mutation == "profile":
        actor = replace(record.actors[0], axis_causes=(len(record.events),) * 8)
        record = replace(record, actors=(actor, *record.actors[1:]))
    else:
        actor = replace(record.actors[0], parents=(0,))
        record = replace(record, actors=(actor, *record.actors[1:]))
    with pytest.raises(archive.HistoryArchiveError):
        validate(record, atlas.history_links(built))


@pytest.mark.parametrize(
    "mutation",
    ["expansion", "trailing", "nesting", "string", "columns", "version", "count", "bool"],
)
def test_bounded_decoder_rejects_hostile_payloads(plan: FinalStartPlan, mutation: str) -> None:
    record = history_atlas(plan).history
    assert record is not None
    wrapper = archive.pack(record)
    raw = lzma.decompress(base64.b85decode(cast("str", wrapper["data"])))
    if mutation == "expansion":
        wrapper["raw_size"] = 1
    elif mutation == "trailing":
        wrapper["data"] = base64.b85encode(lzma.compress(raw) + b"extra").decode()
    else:
        data = cast("dict[str, object]", json.loads(raw))
        if mutation == "nesting":
            raw = b"[" * 30 + b"0" + b"]" * 30
        elif mutation == "string":
            raw = json.dumps({"digest": "x" * 200}).encode()
        else:
            if mutation == "columns":
                data["a"] = [[0], []]
            elif mutation == "version":
                data["v"] = 99
            elif mutation == "count":
                data["a"] = [[0] * (archive.MAX_ROWS + 1)]
            else:
                cast("list[list[object]]", data["a"])[0][0] = True
            raw = json.dumps(data).encode()
        wrapper["data"] = base64.b85encode(lzma.compress(raw)).decode()
        wrapper["raw_size"] = len(raw)
    with pytest.raises(archive.HistoryArchiveError):
        _ = archive.unpack(wrapper)


@pytest.mark.parametrize("kind", [TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION])
def test_extraordinary_membership_preserves_tribal_tenure(kind: TrajectoryKind) -> None:
    plan = project_start(
        inputs_for(realized_network(kind, overlap=kind is TrajectoryKind.HIGHLAND_CONFEDERATION))
    )
    built = history_atlas(plan)
    assert built.history is not None
    validate(built.history, atlas.history_links(built))


def test_the_archive_keeps_the_societal_values_written_to_the_game(plan: FinalStartPlan) -> None:
    from rnw.history_values import AXES as VALUE_AXES  # noqa: PLC0415 - one test's need

    record = history_atlas(plan).history
    assert record is not None
    written = {country.tag: dict(country.government) for country in plan.countries}
    for fact in record.countries:
        assert len(fact.values) == len(VALUE_AXES)
        for axis, value in zip(VALUE_AXES, fact.values, strict=True):
            expected = written[fact.tag].get(axis)
            assert value == (int(expected) if expected is not None else archive.UNWRITTEN)
    assert archive.unpack(archive.pack(record)) == record


def test_an_archive_without_values_still_loads_and_bad_values_are_refused(
    plan: FinalStartPlan,
) -> None:
    built = history_atlas(plan)
    record = built.history
    assert record is not None
    data = archive.to_data(record)
    del data["u"]
    older = archive.from_data(data)
    assert all(country.values == () for country in older.countries)
    validate(older, atlas.history_links(built))
    broken = replace(
        record,
        countries=(replace(record.countries[0], values=(101,) * 8), *record.countries[1:]),
    )
    with pytest.raises(archive.HistoryArchiveError, match="societal values"):
        validate(broken, atlas.history_links(built))


def test_a_country_is_named_as_the_map_names_it_in_both_chronicles(plan: FinalStartPlan) -> None:
    """A society that is a country is named by its country, in the game's text and the window's."""
    renamed = replace(
        plan, countries=tuple(replace(c, name=f"Realm {c.tag}") for c in plan.countries)
    )
    reader = Reader(history_atlas(renamed), "english", atlas.pretty)
    game = history_text.chronicles(renamed)
    stories = game_texts.localize(
        dict(eu5_history_text.stories(renamed, places(renamed))), "english"
    )
    assert game
    for tag, chronicle in game.items():
        story, window = reader.country(tag)[2:4]
        assert "\\n\\n".join(row.text for row in story.lines) == stories[tag]
        assert [row.text for row in window.lines] == [
            history_text.render(row.text, "english", reader.game) for row in chronicle.rows
        ]
        # The country shows in its own rows by its map name; a predecessor keeps its seat's name.
        assert any(f"Realm {tag}" in line.text for line in window.lines)
        assert any("Seat" in line.text for line in window.lines)
        assert f"Realm {tag}" in stories[tag]
