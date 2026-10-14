"""Optional installation contract; skipped in CI without EU5_GAME_DIR."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from rnw.contract import CONTRACT_FILES, fingerprint
from rnw.eu5_map import RIVER_LAND, RIVER_WATER, load_map
from rnw.geography import color_summary, read_locations, summary
from rnw.model import WATER_CLASSES


def test_local_installation_has_consistent_parsed_hierarchy() -> None:
    """A local EU5 install remains parsable after a beta update."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    map_dir = Path(root_value) / "game/in_game/map_data"
    parsed = read_locations(map_dir / "definitions.txt")
    counts = summary(parsed)
    colors = color_summary(parsed, map_dir / "named_locations/00_default.txt")
    assert counts["location"] > 0
    assert counts["american_location"] > 0
    assert colors["duplicate_names"] == 0
    assert colors["duplicate_colors"] == 0
    assert colors["hierarchy_keys_without_color"] == 0
    assert len(fingerprint(Path(root_value))) == len(CONTRACT_FILES)


def test_local_raster_contract_matches_adapter_assumptions() -> None:
    """Raster colours, river water mask and locator rows behave as the exporter assumes."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    game_map = load_map(Path(root_value))
    counts = np.bincount(game_map.labels.ravel(), minlength=len(game_map.keys))
    unused = {game_map.keys[index] for index in np.flatnonzero(counts == 0).tolist()}
    outside = {
        key
        for key, continent in zip(game_map.keys, game_map.continents, strict=True)
        if not continent
    }
    assert unused == outside
    water = np.array([kind in WATER_CLASSES for kind in game_map.classes])[game_map.labels]
    background = (game_map.rivers == RIVER_WATER) | (game_map.rivers == RIVER_LAND)
    agree = np.where(water, RIVER_WATER, RIVER_LAND) == game_map.rivers
    assert np.count_nonzero(agree) * 1000 >= np.count_nonzero(background) * 999
    city = [point for point in game_map.points if point.source.endswith("locators_city.txt")]
    index = {key: position for position, key in enumerate(game_map.keys)}
    hits = sum(int(game_map.labels[point.y, point.x]) == index[point.key] for point in city)
    assert hits * 1000 >= len(city) * 999
