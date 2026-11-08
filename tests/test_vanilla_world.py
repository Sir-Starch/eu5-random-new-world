"""The vanilla Americas, wrapped as the types the societies stage reads (ADR 0012)."""

# pyright: reportAny=false
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest

from rnw.eu5_canvas import select_canvas
from rnw.eu5_map import RIVER_LAND, RIVER_WATER, Eu5Map
from rnw.geography import Location
from rnw.model import CellClass
from rnw.settings import SettingsError, build_settings
from rnw.vanilla_world import VanillaWorldError, build, cell_labels

KEYS = ("old", "new_a", "new_b", "bay", "ocean", "lake", "far_sea")


def _location(key: str, continent: str, area: str) -> Location:
    return Location(key, continent, "sub", "region", area, f"prov_{area}")


def _map() -> Eu5Map:
    labels = np.full((400, 800), 4, dtype=np.int32)  # the ocean
    labels[40:350, 200:240] = 1  # a land location of the Americas
    labels[40:200, 240:260] = 2  # another, touching the first
    labels[200:260, 240:280] = 3  # a bay
    labels[100:120, 205:215] = 5  # a lake inside the first
    labels[40:350, 700:760] = 0  # the Old World, east
    labels[380:400, 400:420] = 6  # a sea the canvas does not take in
    rivers = np.full(labels.shape, RIVER_LAND, dtype=np.uint8)
    rivers[labels == 4] = RIVER_WATER
    rivers[60:300, 220] = 3  # a river down the first location
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=KEYS,
                colors=np.arange(len(KEYS), dtype=np.int64) + 100,
                labels=labels,
                rivers=rivers,
                continents=(
                    "africa",
                    "america",
                    "america",
                    "atlantic_ocean_continent",
                    "atlantic_ocean_continent",
                    "america",
                    "atlantic_ocean_continent",
                ),
                classes=(
                    CellClass.LAND,
                    CellClass.LAND,
                    CellClass.WASTELAND,
                    CellClass.SEA,
                    CellClass.SEA,
                    CellClass.LAKE,
                    CellClass.SEA,
                ),
                ambiguous=np.array([False, False, False, False, True, False, False]),
            ),
        ),
    )


HIERARCHY = {
    "old": _location("old", "africa", "a_old"),
    "new_a": _location("new_a", "america", "a_new"),
    "new_b": _location("new_b", "america", "a_new"),
    "bay": _location("bay", "atlantic_ocean_continent", "a_bay"),
    "ocean": _location("ocean", "atlantic_ocean_continent", "a_ocean"),
    "lake": _location("lake", "america", "a_new"),
}
ATTRIBUTES = {
    "new_a": {"climate": "tropical", "vegetation": "forest", "topography": "flatland"},
    "new_b": {"climate": "arid", "vegetation": "desert", "topography": "mountains"},
}


def test_the_cells_are_the_americas_and_the_waters_the_canvas_holds() -> None:
    game = _map()
    canvas = select_canvas(game, 8, expanded=False)
    found = [game.keys[label] for label in cell_labels(game, HIERARCHY, canvas)]
    assert "new_a" in found
    assert "new_b" in found
    assert "lake" in found
    assert "old" not in found
    assert "far_sea" not in found


def test_the_world_plan_and_biomes_are_the_games_own() -> None:
    game = _map()
    canvas = select_canvas(game, 8, expanded=False)
    vanilla = build(game, HIERARCHY, ATTRIBUTES, canvas)
    keys = [cell.key for cell in vanilla.plan.cells]
    assert len(keys) == len(vanilla.world.classes) == len(vanilla.biomes.climate)
    assert keys == [game.keys[label] for label in vanilla.keep]
    first = keys.index("new_a")
    second = keys.index("new_b")
    assert vanilla.world.classes[first] is CellClass.LAND
    assert vanilla.world.classes[second] is CellClass.WASTELAND
    assert vanilla.plan.cells[first].area == "a_new"
    assert vanilla.plan.cells[first].region == "region"
    assert vanilla.plan.cells[first].continent == "america"
    assert vanilla.biomes.climate[first] == "tropical"
    assert vanilla.biomes.topography[second] == "mountains"
    assert vanilla.biomes.vegetation[keys.index("bay")] == ""
    assert vanilla.plan.cells[first].color == 101
    # The cells are the game's pixels: no cell grew or shrank, and each one is a single place.
    crop = canvas.rolled(game.labels)[:, canvas.col0 : canvas.col0 + canvas.mask.shape[1]]
    assert int(vanilla.world.pixels[first]) == int(((crop == 1) & canvas.mask).sum())
    # Contacts are the vanilla contacts: the two locations touch, and the land touches its bay.
    assert (first, second) in vanilla.world.edges or (second, first) in vanilla.world.edges
    bay = keys.index("bay")
    assert any(bay in pair and second in pair for pair in vanilla.world.edges)


def test_the_rivers_are_counted_for_the_cell_they_run_through() -> None:
    game = _map()
    canvas = select_canvas(game, 8, expanded=False)
    vanilla = build(game, HIERARCHY, ATTRIBUTES, canvas)
    first = [cell.key for cell in vanilla.plan.cells].index("new_a")
    assert vanilla.river_pixels[first] > 0
    assert vanilla.river_pixels[[cell.key for cell in vanilla.plan.cells].index("new_b")] == 0


def test_the_same_installation_gives_the_same_cells() -> None:
    game = _map()
    canvas = select_canvas(game, 8, expanded=False)
    first = build(game, HIERARCHY, ATTRIBUTES, canvas)
    again = build(game, HIERARCHY, ATTRIBUTES, canvas)
    assert first.keep == again.keep
    assert np.array_equal(first.world.labels, again.world.labels)


def test_an_installation_without_americas_is_refused() -> None:
    game = _map()
    canvas = select_canvas(game, 8, expanded=False)
    nowhere = {key: location for key, location in HIERARCHY.items() if key == "old"}
    with pytest.raises(VanillaWorldError, match="no land"):
        _ = build(game, nowhere, ATTRIBUTES, canvas)


def test_keeping_the_geography_is_a_setting_that_cannot_meet_a_drawn_land_or_the_wall() -> None:
    kept = build_settings("omerika", {"new_world": {"keep_geography": 1}})
    assert kept.new_world.keep_geography == 1
    assert build_settings("omerika").new_world.keep_geography == 0
    with pytest.raises(SettingsError, match="real Americas"):
        _ = build_settings("continents", {"new_world": {"keep_geography": 1}, "mask": {"id": 4}})
    with pytest.raises(SettingsError, match="real Americas"):
        _ = build_settings("wall", {"new_world": {"keep_geography": 1}})


def test_a_world_that_keeps_the_geography_changes_only_its_own_settings_document() -> None:
    plain = build_settings("continents").to_json_data()
    assert "keep_geography" not in cast("dict[str, dict[str, int]]", plain)["new_world"]
    kept = build_settings("continents", {"new_world": {"keep_geography": 1}}).to_json_data()
    assert cast("dict[str, dict[str, int]]", kept)["new_world"]["keep_geography"] == 1


@pytest.mark.skipif(
    "EU5_GAME_DIR" not in os.environ, reason="needs the installed game (EU5_GAME_DIR)"
)
def test_the_installed_americas_are_wrapped() -> None:
    from rnw.eu5_biomes import template_attributes  # noqa: PLC0415
    from rnw.eu5_map import load_map  # noqa: PLC0415
    from rnw.geography import read_locations  # noqa: PLC0415

    game_dir = Path(os.environ["EU5_GAME_DIR"])
    game = load_map(game_dir)
    hierarchy = {
        item.key: item
        for item in read_locations(game_dir / "game/in_game/map_data/definitions.txt")
    }
    templates = (game_dir / "game/in_game/map_data/location_templates.txt").read_text(
        encoding="utf-8-sig"
    )
    canvas = select_canvas(game, build_settings("continents").new_world.ocean_band_px)
    vanilla = build(game, hierarchy, template_attributes(templates), canvas)
    lands = [i for i, kind in enumerate(vanilla.world.classes) if kind is CellClass.LAND]
    assert len(lands) > 4000
    assert all(vanilla.plan.cells[i].continent == "america" for i in lands)
    assert all(vanilla.biomes.climate[i] for i in lands)
