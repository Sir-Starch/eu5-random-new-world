"""Optional installation contract; skipped in CI without EU5_GAME_DIR."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from rnw import epoch
from rnw.app.discovery import find_games
from rnw.app.worldcode import decode
from rnw.contract import CONTRACT_FILES, fingerprint
from rnw.eu5_biomes import template_attributes
from rnw.eu5_canvas import select_canvas
from rnw.eu5_lobby import (
    CONTEXT_MENU,
    COVER_INCLUDE,
    GRAPHICS_DEFINES,
    INCLUDE_DIRS,
    OWN_SAMPLERS,
    SHADERS,
    binding_problem,
    cover_include,
    cover_shader,
    hide_select_entry,
    land_colour,
    sampler_include,
    shader_samplers,
)
from rnw.eu5_map import DEFINITIONS, RIVER_LAND, RIVER_WATER, load_map
from rnw.eu5_natives import vanilla_natives
from rnw.eu5_newworld import vanilla_geometry
from rnw.eu5_nw_export import calibrate_development, export_new_world
from rnw.eu5_slots import CLIMATE_GROUPS, COAST_SLOTS, TOPOGRAPHY_GROUPS, SlotTables, synthesize
from rnw.eu5_terrain import DecalStore
from rnw.geography import color_summary, read_locations, summary
from rnw.model import WATER_CLASSES
from rnw.record import Record

GOLDEN_WORLD = Path(__file__).with_name("golden_world.json")


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


def test_local_native_calibration_reads_the_vanilla_americas() -> None:
    """Native calibration finds American pops, cultures, religions and setups."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    game_map = load_map(root)
    hierarchy = {location.key: location for location in read_locations(root / DEFINITIONS)}
    canvas = select_canvas(game_map, 1600)
    attributes = template_attributes(
        (root / "game/in_game/map_data/location_templates.txt").read_text(encoding="utf-8-sig")
    )
    vanilla = vanilla_natives(
        root, game_map, vanilla_geometry(game_map, canvas, hierarchy), attributes, hierarchy
    )
    assert len(vanilla.cultures) > 500
    assert len(vanilla.religions) > 50
    assert vanilla.density["tropical"] > 5 * vanilla.density["subpolar"]
    assert vanilla.population_per_location > 1000
    assert {"amerindian_tribe", "amerindian_monarchy"} <= vanilla.templates
    assert "PAM" in vanilla.reserved_tags
    assert any(culture.state_include for culture in vanilla.cultures.values())
    assert any(culture.city_setup for culture in vanilla.cultures.values())


def test_local_development_calibration_reads_the_vanilla_americas() -> None:
    """Keyed maximum, harbour distribution and market-village share of vanilla 1.4.1."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    game_map = load_map(root)
    hierarchy = {location.key: location for location in read_locations(root / DEFINITIONS)}
    calibration = calibrate_development(root, game_map, hierarchy)
    assert calibration.society_max == 12
    assert len(calibration.harbours) == 1092
    assert calibration.harbours.count(0) == 828
    assert calibration.harbours[0] == -10
    assert calibration.village_permille == 393  # 79 of the 201 capitals that are no city or town
    assert calibration.vanilla_means["city"][0] == 9
    assert calibration.vanilla_means["unorganised"][0] == 2088


def test_local_discovery_finds_the_installation() -> None:
    """The search over this machine's Steam libraries includes the installation under test."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    games = find_games()
    assert any(game.directory.resolve() == Path(root_value).resolve() for game in games)
    steam = [game for game in games if game.library is not None]
    if steam:
        assert steam[0].build_id.isdigit()


def test_local_game_files_take_the_selection_cover() -> None:
    """Every game file the cover of C136 changes or reads is laid out as the cover expects."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    grid = np.zeros((256, 512), dtype=bool)
    mod = {COVER_INCLUDE: cover_include((8192, 16384), grid, (0.1, 0.1, 0.1))}
    mod.update({name: sampler_include(name) for name in OWN_SAMPLERS})

    def read(name: str) -> str | None:
        if name in mod:
            return mod[name]
        found = [
            root / folder / name for folder in INCLUDE_DIRS if (root / folder / name).is_file()
        ]
        return found[0].read_text(encoding="utf-8-sig") if found else None

    for edit in SHADERS:
        patched = cover_shader(edit, (root / edit.path).read_text(encoding="utf-8-sig"))
        assert patched, edit.path
        assert binding_problem(edit, shader_samplers(patched, read)) is None, edit.path
    assert hide_select_entry((root / CONTEXT_MENU).read_text(encoding="utf-8-sig"))
    assert land_colour((root / GRAPHICS_DEFINES).read_text(encoding="utf-8-sig"))


def test_local_reference_world_comes_out_the_same(tmp_path: Path) -> None:
    """The reference world of this epoch is made again byte for byte (ADR 0010, G).

    Slow, about two minutes and 7.5 GiB, so only with ``RNW_REPRODUCE=1``. Skipped on another
    game build than the one the digest was taken on: that is a different world, and a new
    reference is recorded for it. A failure with the same build means a change of the generator
    altered a world without a new epoch (``rnw.epoch``), or the game's files changed.
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None or os.environ.get("RNW_REPRODUCE") != "1":
        pytest.skip("EU5_GAME_DIR and RNW_REPRODUCE=1 are needed")
    golden = cast("dict[str, object]", json.loads(GOLDEN_WORLD.read_text(encoding="utf-8")))
    assert golden["epoch"] == epoch.CURRENT, "a new epoch needs a new reference world"
    code = decode(str(golden["code"]))
    game_dir = Path(root_value)
    report = export_new_world(
        game_dir,
        tmp_path / "generated" / "rnw_exp_reference",
        seed=code.seed,
        settings=code.settings(),
        world_code=str(golden["code"]),
    )
    record = Record.from_json(report["record"])
    if record.game.fingerprint_sha256 != golden["game_fingerprint_sha256"]:
        pytest.skip(f"the reference world is for {golden['game_label']}, not {record.game.label}")
    output = cast("dict[str, object]", golden["output"])
    assert record.output_sha256 == output["sha256"]
    assert record.output_count == output["count"]
