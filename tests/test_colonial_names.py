"""The colonial names: one scripted name for each tradition in each region (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.colonial_names import (
    GROUPS_DIR,
    LANGUAGES_DIR,
    TRADITIONS,
    ColonialNameError,
    block,
    check_installation,
    entry_id,
    script,
    texts,
)
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from pathlib import Path

REGIONS = {"north_region": "Ingari", "south_region": "Taku"}


def test_every_tradition_has_a_colony_name_in_every_region() -> None:
    """The file holds one entry for each pair, and each reads like the game's own."""
    root = parse(script(list(REGIONS)))
    keys = [entry.key for entry in root.entries if entry.key]
    assert keys == [
        entry_id(tradition, region) for region in sorted(REGIONS) for tradition in TRADITIONS
    ]
    for entry in root.entries:
        assert isinstance(entry.value, Block)
        assert entry.value.block("country_trigger") is not None
        assert entry.value.block("capital_trigger") is not None
        assert entry.value.block("location_trigger") is not None


def test_a_colony_is_named_by_its_founder_and_the_region_of_its_capital() -> None:
    """The country asks the overlord's language, the capital the region; nothing else."""
    spanish, dutch = TRADITIONS[0], TRADITIONS[-1]
    text = block(spanish, "north_region")
    assert "overlord ?= { culture.language = language:spanish_language }" in text
    assert "region = region:north_region" in text
    assert "culture_group:netherlandish_group" in block(dutch, "north_region")
    assert len({tradition.name for tradition in TRADITIONS}) == len(TRADITIONS)


def test_the_names_put_the_regions_name_after_the_word_for_new() -> None:
    """A template of the tradition's language, with the generated name left as it is."""
    found = texts(REGIONS)
    english = next(t for t in TRADITIONS if t.name == "english")
    assert found[entry_id(english, "north_region")] == "New Ingari"
    assert found[f"{entry_id(english, 'north_region')}_ADJ"] == "New Ingari"
    assert found[entry_id(TRADITIONS[0], "south_region")] == "Nueva Taku"
    assert len(found) == 2 * len(REGIONS) * len(TRADITIONS)
    assert all('"' not in value for value in found.values())


def _install(root: Path, *, drop: str = "") -> Path:
    for directory, keys in (
        (LANGUAGES_DIR, [t.needs for t in TRADITIONS if t.needs.endswith("_language")]),
        (GROUPS_DIR, [t.needs for t in TRADITIONS if t.needs.endswith("_group")]),
    ):
        path = root / directory / "00_x.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("".join(f"{key} = {{ }}\n" for key in keys if key != drop))
    return root


def test_a_language_or_group_the_game_lacks_stops_the_export(tmp_path: Path) -> None:
    """Nothing is replaced: a tradition that leans on a missing key is an error."""
    check_installation(_install(tmp_path / "ok"))
    with pytest.raises(ColonialNameError, match="french_language"):
        check_installation(_install(tmp_path / "bad", drop="french_language"))
    with pytest.raises(ColonialNameError, match="netherlandish_group"):
        check_installation(_install(tmp_path / "worse", drop="netherlandish_group"))
