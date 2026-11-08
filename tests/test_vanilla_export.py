"""The societies-only export on the vanilla Americas (ADR 0012)."""

# pyright: reportAny=false, reportPrivateUsage=false
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from rnw import eu5_vanilla_export as export
from rnw import wording, worldname
from rnw.eu5_biomes import CellBiomes
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.geography import Location
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.settings import build_settings
from rnw.vanilla_world import VanillaWorld

HIERARCHY = {
    "old": Location("old", "africa", "s_old", "r_old", "a_old", "p_old"),
    "tenochtitlan": Location("tenochtitlan", "america", "s_a", "r_a", "a_a", "p_a"),
    "texcoco": Location("texcoco", "america", "s_a", "r_a", "a_a", "p_b"),
    "cusco": Location("cusco", "america", "s_b", "r_b", "a_b", "p_c"),
}


def _vanilla() -> VanillaWorld:
    kinds = (CellClass.LAND, CellClass.WASTELAND, CellClass.SEA)
    labels = np.array([[0, 0, 1, 1, 2, 2]], dtype=np.int32)
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    cells = [
        PlannedCell(
            "tenochtitlan", "tenochtitlan", 1, kinds[0], "p_a", "a_a", "r_a", "s_a", "america"
        ),
        PlannedCell("cusco", "cusco", 2, kinds[1], "p_c", "a_b", "r_b", "s_b", "america"),
        PlannedCell("gulf", "gulf", 3, kinds[2], "", "a_gulf", "", "", "atlantic_ocean_continent"),
    ]
    biomes = CellBiomes(("", "", ""), ("", "", ""), ("", "", ""), ("", "", ""))
    return VanillaWorld((0, 1, 2), world, Plan(cells=cells), biomes, np.zeros(3, dtype=np.int64))


def test_what_the_world_replaces_is_the_footprint_the_content_is_read_from() -> None:
    gone, dropped = export._american_keys(HIERARCHY)
    assert gone == {"tenochtitlan", "texcoco", "cusco", "p_a", "p_b", "p_c"}
    assert dropped == gone | {"a_a", "a_b", "r_a", "r_b"}
    assert "old" not in dropped
    assert "a_old" not in dropped


def test_the_texts_name_places_areas_and_regions_of_the_land_not_the_sea() -> None:
    vanilla = _vanilla()
    assert export._named_keys(vanilla) == {
        "tenochtitlan",
        "a_a",
        "r_a",
        "cusco",
        "a_b",
        "r_b",
    }


def test_the_games_own_names_are_references_to_its_texts_where_it_has_them() -> None:
    vanilla = _vanilla()
    names = export._reference_names(vanilla, {"tenochtitlan", "r_a", "unrelated"})
    assert set(names) == {"tenochtitlan", "r_a"}
    assert names["tenochtitlan"] == wording.reference("tenochtitlan")


def test_the_present_keys_are_every_key_of_the_installed_hierarchy() -> None:
    present = export._present_keys(HIERARCHY)
    assert present["location"] == frozenset(HIERARCHY)
    assert present["area"] == {"a_old", "a_a", "a_b"}
    assert present["subcontinent"] == {"s_old", "s_a", "s_b"}


def test_the_mod_says_what_it_is_and_names_the_world_and_its_code() -> None:
    data = export._metadata("rnw_exp_world_x", "RNW: Omerika ABCD", "RNW1-CODE").decode("utf-8-sig")
    payload = json.loads(data)
    assert payload["id"] == "rnw_exp_world_x"
    assert payload["name"] == "RNW: Omerika ABCD"
    assert "RNW1-CODE" in payload["short_description"]
    assert "original Americas" in payload["short_description"]
    assert payload["tags"] == ["Map"]


def test_omerika_that_keeps_the_americas_is_still_named_omerika() -> None:
    kept = build_settings("omerika", {"new_world": {"keep_geography": 1}})
    assert worldname.display_name("omerika", "TAG1", settings=kept) == "Omerika TAG1"
    changed = build_settings("omerika", {"new_world": {"keep_geography": 1, "land_permille": 300}})
    assert worldname.display_name("omerika", "TAG1", settings=changed) == "Custom world TAG1"
    other = build_settings("continents", {"new_world": {"keep_geography": 1}})
    assert worldname.display_name("continents", "TAG1", settings=other) == "Custom world TAG1"


def test_a_world_that_keeps_the_americas_takes_no_drawn_land(tmp_path: Path) -> None:
    from rnw.eu5_nw_export import NewWorldExportError  # noqa: PLC0415
    from rnw.eu5_world_export import export_world  # noqa: PLC0415
    from rnw.landmask import LandMask  # noqa: PLC0415

    kept = build_settings("omerika", {"new_world": {"keep_geography": 1}})
    mask = LandMask(np.ones((64, 128), dtype=bool))
    with pytest.raises(NewWorldExportError, match="no drawn land"):
        _ = export_world(
            tmp_path, tmp_path / "generated" / "rnw_exp_x", seed=1, settings=kept, land_mask=mask
        )


@pytest.mark.skipif(
    "EU5_GAME_DIR" not in os.environ, reason="needs the installed game (EU5_GAME_DIR)"
)
def test_the_installed_americas_get_their_societies_and_no_physical_file(
    tmp_path: Path,
) -> None:
    from rnw.eu5_world_export import export_world  # noqa: PLC0415

    game = Path(os.environ["EU5_GAME_DIR"])
    output = tmp_path / "generated" / "rnw_exp_world_vanillatest"
    settings = build_settings("omerika", {"new_world": {"keep_geography": 1}})
    report = export_world(game, output, seed=7, settings=settings, cache_dir=tmp_path / "cache")
    mod = output / output.name
    files = [path.relative_to(mod).as_posix() for path in mod.rglob("*") if path.is_file()]
    # No geography is written: nothing of the map's own data, no picture but the mod's thumbnail.
    assert not [name for name in files if name.startswith("in_game/map_data")]
    pictures = [name for name in files if name.endswith((".png", ".dds"))]
    assert pictures == [".metadata/thumbnail.png"]
    countries = (mod / "main_menu/setup/1337/10_countries.txt").read_text(encoding="utf-8-sig")
    assert str(report["title"]).startswith("RNW: Omerika")
    generated = cast("dict[str, object]", report["generated"])
    invariants = cast("dict[str, int]", report["invariants"])
    assert cast("int", generated["locations"]) > 4000
    assert generated["geography"] == "the installed game's own"
    assert invariants["native_countries"] > 100
    assert countries
    # No file is a copy of the game's own: a mod file that overrides one changes it.
    for name in files:
        original = game / "game" / name
        if original.is_file():
            assert original.read_bytes() != (mod / name).read_bytes(), name
