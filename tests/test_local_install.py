"""Optional installation contract; skipped in CI without EU5_GAME_DIR."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from rnw.contract import CONTRACT_FILES, fingerprint
from rnw.eu5_biomes import template_attributes
from rnw.eu5_map import RIVER_LAND, RIVER_WATER, load_map
from rnw.eu5_slots import CLIMATE_GROUPS, COAST_SLOTS, TOPOGRAPHY_GROUPS, SlotTables, synthesize
from rnw.eu5_terrain import DecalStore
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


def test_local_slot_rules_reproduce_vanilla_structure() -> None:
    """The material-slot rules rebuild a vanilla decal crop's structure (C51).

    Structural classes are coast, coast transition, water edge, the three border bands,
    variation and no material; at least 80% of pixels must agree.
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    game_map = load_map(root)
    templates = (root / "game/in_game/map_data/location_templates.txt").read_text(
        encoding="utf-8-sig"
    )
    attributes = template_attributes(templates)

    def ids(values: list[str]) -> np.ndarray:
        names = {name: index for index, name in enumerate(sorted(set(values)))}
        return np.array([names[value] for value in values], dtype=np.int64)

    fields = [attributes.get(key, {}) for key in game_map.keys]
    topography = [row.get("topography", "") for row in fields]
    count = len(game_map.keys)
    tables = SlotTables(
        water=np.array([kind in WATER_CLASSES for kind in game_map.classes]),
        coast_slot=np.array([COAST_SLOTS.get(name, 0) for name in topography], dtype=np.int64),
        topography=ids([TOPOGRAPHY_GROUPS.get(name, name) for name in topography]),
        vegetation=ids([row.get("vegetation", "") for row in fields]),
        climate=ids([CLIMATE_GROUPS.get(c, c) for c in (row.get("climate", "") for row in fields)]),
        level_one=np.full(count, 400, dtype=np.int64),
        level_two=np.full(count, 450, dtype=np.int64),
        materials=np.full(count, 16, dtype=np.int64),
    )
    store = DecalStore(root, (int(game_map.labels.shape[0]), int(game_map.labels.shape[1])))
    decal = next(item for item in store.decals if item.name == "heightmap_6_16")
    _, materials = store.layer(decal.name, "materials")
    rows = slice(decal.row0, decal.row0 + 800)
    columns = slice(decal.column0 + 2900, decal.column0 + 4000)
    labels = np.repeat(np.repeat(game_map.labels[rows, columns], 2, axis=0), 2, axis=1)
    rivers = np.repeat(np.repeat(game_map.rivers[rows, columns] < 16, 2, axis=0), 2, axis=1)
    slots = synthesize(labels, ~tables.water[labels], rivers, tables, seed=1, origin=(0, 0))
    vanilla = materials[:1600, 5800:8000]
    edges = np.array([0, 5, 6, 7, 8, 9, 10, 17, 255, 256])
    assert np.mean(np.digitize(vanilla, edges) == np.digitize(slots, edges)) >= 0.8
