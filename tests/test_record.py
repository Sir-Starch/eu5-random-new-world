"""The reproducibility record: digests, its JSON layout, the settings it resolves, the verdicts."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from rnw import epoch
from rnw.record import (
    FORMAT,
    GameRecord,
    Manifest,
    NewerFormatError,
    Record,
    RecordError,
    Verdict,
    manifest_digest,
    output_entries,
    verdict,
)
from rnw.settings import build_settings


def _record() -> Record:
    settings = build_settings("continents", {"natives": {"empire_permille": 5}})
    return Record(
        format=FORMAT,
        algorithm=epoch.CURRENT,
        release="0.9.22",
        code="RNW1-TEST",
        preset="continents",
        seed=42,
        settings=settings.to_json_data(),
        game=GameRecord("EU5 1.4.2", "a" * 64, "1.4.*", "b" * 64, 3),
        output_sha256="c" * 64,
        output_count=7,
    )


def test_a_manifest_digest_does_not_depend_on_order_and_sees_every_change() -> None:
    """The same files in any order give one digest; a changed hash, name or file changes it."""
    one = {"a/x": "1", "b/y": "2"}
    assert manifest_digest(one) == manifest_digest({"b/y": "2", "a/x": "1"})
    assert manifest_digest(one) != manifest_digest({"a/x": "1", "b/y": "3"})
    assert manifest_digest(one) != manifest_digest({"a/x": "1", "b/z": "2"})
    assert manifest_digest(one) != manifest_digest({**one, "c": "0"})
    assert Manifest(one).digest == manifest_digest(one)


def test_the_output_of_a_mod_leaves_out_its_metadata_and_what_is_beside_it() -> None:
    """Only the files inside the mod count, and not the title, version and picture."""
    files = [
        {"path": "mod/in_game/map_data/locations.png", "sha256": "1"},
        {"path": "mod/.metadata/metadata.json", "sha256": "2"},
        {"path": "mod/.metadata/thumbnail.png", "sha256": "3"},
        {"path": "mod/main_menu/setup/x.txt", "sha256": "4"},
        {"path": "preview.png", "sha256": "5"},
        {"path": "selection_cover/a.txt", "sha256": "6"},
    ]
    assert output_entries(files, "mod") == {
        "in_game/map_data/locations.png": "1",
        "main_menu/setup/x.txt": "4",
    }


def test_a_record_survives_json_and_resolves_the_settings_it_holds() -> None:
    """The world is made again from the record's own settings, not from the presets."""
    record = _record()
    assert Record.from_json(record.to_json()) == record
    assert record.resolved_settings() == build_settings(
        "continents", {"natives": {"empire_permille": 5}}
    )
    assert replace(record, code=None).to_json()["code"] is None
    assert Record.from_json(replace(record, code=None).to_json()).code is None


def test_a_damaged_record_is_refused_and_a_newer_one_is_named() -> None:
    """Missing or mistyped fields raise, a layout from the future says which it is."""
    document = _record().to_json()
    for field in ("algorithm", "game", "output", "settings"):
        broken = {key: value for key, value in document.items() if key != field}
        with pytest.raises(RecordError):
            _ = Record.from_json(broken)
    with pytest.raises(RecordError):
        _ = Record.from_json({**document, "seed": "42"})
    with pytest.raises(RecordError):
        _ = Record.from_json({**document, "seed": True})
    with pytest.raises(RecordError):
        _ = Record.from_json("not a record")
    with pytest.raises(NewerFormatError) as caught:
        _ = Record.from_json({"format": FORMAT + 1})
    assert caught.value.found == FORMAT + 1
    broken_settings = {**document, "settings": {"schema": 1, "geography": {"nonsense": 1}}}
    with pytest.raises(RecordError):
        _ = Record.from_json(broken_settings).resolved_settings()


def test_a_manifest_survives_json_and_a_bad_one_is_refused() -> None:
    """Paths map to hashes in a document with a format; anything else raises."""
    manifest = Manifest({"game/a.txt": "1", "game/b.txt": "2"})
    assert Manifest.from_json(manifest.to_json()) == manifest
    bad_ones: list[object] = [None, [], {"format": FORMAT}, {"format": FORMAT, "files": {"a": 1}}]
    for bad in bad_ones:
        with pytest.raises(RecordError):
            _ = Manifest.from_json(bad)
    with pytest.raises(NewerFormatError):
        _ = Manifest.from_json({"format": FORMAT + 1, "files": {}})


def test_a_verdict_is_always_one_of_five_states() -> None:
    """Format first, then the algorithm, then the inputs; unchecked inputs are said, not assumed."""
    record = _record()
    assert verdict(record) is Verdict.SAME_ALGORITHM
    assert verdict(record, inputs_same=True) is Verdict.IDENTICAL
    assert verdict(record, inputs_same=False) is Verdict.OTHER_INPUTS
    other = replace(record, algorithm=epoch.CURRENT + 1)
    assert verdict(other, inputs_same=True) is Verdict.OTHER_ALGORITHM
    newer = replace(record, format=FORMAT + 1, algorithm=epoch.CURRENT + 1)
    assert verdict(newer, inputs_same=True) is Verdict.NEWER_FORMAT
    assert cast("object", Verdict.IDENTICAL.value) == "identical"
