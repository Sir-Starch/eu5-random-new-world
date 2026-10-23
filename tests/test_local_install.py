"""Optional installation contract; skipped in CI without EU5_GAME_DIR."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from rnw import content_report, epoch, eu5_probe, splnet
from rnw.app.discovery import find_games
from rnw.app.worldcode import decode, encode, rolled
from rnw.contract import CONTRACT_FILES, fingerprint
from rnw.eu5_biomes import template_attributes
from rnw.eu5_canvas import select_canvas
from rnw.eu5_lobby import (
    CONTEXT_MENU,
    COVER_INCLUDE,
    DRAWINGS_FILE,
    DRAWINGS_INCLUDE,
    DRAWINGS_INDEX,
    GRAPHICS_DEFINES,
    OWN_SAMPLERS,
    SHADERS,
    cover_include,
    cover_shader,
    drawings_include,
    hide_select_entry,
    land_colour,
    sampler_include,
)
from rnw.eu5_lobby_gui import GUI_FILES, patch_gui
from rnw.eu5_map import DEFINITIONS, RIVER_LAND, RIVER_WATER, load_map
from rnw.eu5_natives import DEFINITION_FILE, vanilla_natives
from rnw.eu5_newworld import vanilla_geometry
from rnw.eu5_nw_export import binding_problems, calibrate_development, export_new_world
from rnw.eu5_places import SPECS
from rnw.eu5_slots import CLIMATE_GROUPS, COAST_SLOTS, TOPOGRAPHY_GROUPS, SlotTables, synthesize
from rnw.eu5_splines import GAME_FILE as SPLINE_GAME_FILE
from rnw.eu5_splines import land_contacts
from rnw.eu5_terrain import DecalStore
from rnw.geography import color_summary, read_locations, summary
from rnw.languages import official_languages
from rnw.model import WATER_CLASSES, CellClass
from rnw.pdx import parse
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
    # R7b: the vanilla state levels (4 landed countries have none) and the family triggers
    assert vanilla.state_levels == (0,) * 11 + (1,) * 17 + (2,) * 191
    assert vanilla.families.by_region == dict.fromkeys(
        ("mesoamerica_region", "central_america_region"), "mesoamerica"
    ) | dict.fromkeys(
        (
            "colombia_region",
            "andes_region",
            "brazil_region",
            "chaco_region",
            "la_plata_region",
            "caribbean_region",
        ),
        "south_america",
    )
    assert vanilla.families.by_area == dict.fromkeys(
        ("xalisco_area", "zacatecas_area"), "mesoamerica"
    )
    shares = Counter(culture.family for culture in vanilla.cultures.values())
    assert shares == {"north_america": 380, "south_america": 276, "mesoamerica": 74}
    # R7c: the great empire's level, rank, road bound and its four opinion types (C155, C158)
    assert vanilla.empire is not None
    assert (vanilla.empire.level, vanilla.empire.rank) == (3, "rank_duchy")
    assert 900 <= vanilla.empire.road_permille <= 1100
    assert vanilla.empire.opinions == (
        "opinion_threatens_conquest",
        "opinion_prey_to_conquest",
        "opinion_tyrant_overlord",
        "opinion_irritated",
    )
    assert len(vanilla.empire.largest) == 5


def test_local_spline_network_is_read_and_written_back_exactly() -> None:
    """Vanilla's spline network round-trips byte for byte and has a strip for every land contact.

    It also has one for each road of the 1337 setup, and its anchors are the locations'
    indexes in the order of ``definitions.txt`` (C162).
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    data = (root / SPLINE_GAME_FILE).read_bytes()
    network = splnet.parse(data)
    assert splnet.serialize(network) == data
    # a map that lost nothing gets vanilla's own bytes back: order and numbering are kept
    same = splnet.rebuild(network, {int(a): int(a) for a in network.anchors.tolist()}, {}, [])
    assert splnet.serialize(same) == data
    assert (len(network.anchors), len(network.point_xy)) == (21_046, 589_062)
    assert (len(network.segments), len(network.strips)) == (110_111, 51_095)
    game_map = load_map(root)
    keys = [location.key for location in read_locations(root / DEFINITIONS)]
    index = {key: number + 1 for number, key in enumerate(keys)}
    land = np.array([kind is CellClass.LAND for kind in game_map.classes], dtype=bool)
    contacts = land_contacts(game_map.labels, land, np.ones(len(land), dtype=bool))
    pairs = {splnet.strip_id(index[game_map.keys[a]], index[game_map.keys[b]]) for a, b in contacts}
    assert pairs <= network.strips.keys()
    assert len(pairs) == 50_580
    roads = parse(
        (root / "game/main_menu/setup/1337/09_roads.txt").read_text(encoding="utf-8-sig")
    ).block("road_network")
    assert roads is not None
    wanted = {
        splnet.strip_id(index[entry.key], index[entry.value])
        for entry in roads.entries
        if entry.key in index and isinstance(entry.value, str) and entry.value in index
    }
    assert len(wanted) == 1_646
    assert wanted <= network.strips.keys()


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


def test_local_content_consumers_all_have_a_decision() -> None:
    """The scripts that name the replaced New World match the decision table, both ways.

    Fails after a patch that adds or removes such an object, until the table is updated
    (content plan, N0). The counts are those of the plan: the 58 retired events, the 39
    modifiers only they applied, the five historical natural-resource bonuses, the eight
    American scripted country names and the eight American formables.
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    inventory = content_report.build(Path(root_value))
    assert inventory.missing == []
    assert inventory.stale == []
    assert (inventory.events, inventory.modifiers, inventory.base_values) == (58, 39, 5)
    names = [
        c for c in inventory.consumers.values() if c.category == "common/scripted_country_names"
    ]
    formables = [
        c for c in inventory.consumers.values() if c.category == "common/formable_countries"
    ]
    assert len(names) == len(formables) == 8
    assert all(inventory.verdicts[c.key] is not None for c in (*names, *formables))
    # The positional mechanics that option N5 would make semantic: all 14 American regions.
    positional = content_report.report(inventory)["positional"]
    assert isinstance(positional, dict)
    assert positional["keys"]["region"] == 14


def test_local_languages_are_the_installations_own() -> None:
    """The mod writes every language the game ships localization for, Turkish included."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    languages = official_languages(Path(root_value))
    assert "english" in languages
    assert len(languages) >= 11
    shipped = {
        folder.name
        for folder in (Path(root_value) / "game/main_menu/localization").iterdir()
        if folder.is_dir()
    }
    assert set(languages) == shipped


def test_local_hook_probe_anchors_hold() -> None:
    """The hook probe of N2 finds every vanilla anchor it leans on and its scripts read."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    game_dir = Path(root_value)
    assert eu5_probe.anchor_problems(game_dir) == []
    files = eu5_probe.build(game_dir)
    eu5_probe.check(files)
    assert len(files) == 10 + len(official_languages(game_dir))


def test_local_game_files_take_the_selection_cover() -> None:
    """Every game file the cover of C136 changes or reads is laid out as the cover expects."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    grid = np.zeros((256, 512), dtype=bool)
    mod = {
        COVER_INCLUDE: cover_include((8192, 16384), grid, (0.1, 0.1, 0.1)),
        DRAWINGS_INCLUDE: drawings_include(),
    }
    mod.update({name: sampler_include(name) for name in OWN_SAMPLERS})

    shaders: dict[str, str] = {}
    for edit in SHADERS:
        patched = cover_shader(
            edit, (root / (edit.source_path or edit.path)).read_text(encoding="utf-8-sig")
        )
        assert patched, edit.path
        shaders[edit.path] = patched
    assert not binding_problems(root, shaders, mod)
    assert hide_select_entry((root / CONTEXT_MENU).read_text(encoding="utf-8-sig"))
    for path in GUI_FILES:
        assert patch_gui(path, (root / path).read_text(encoding="utf-8-sig")), path
    assert land_colour((root / GRAPHICS_DEFINES).read_text(encoding="utf-8-sig"))


def test_local_game_has_the_drawings_the_cover_relies_on() -> None:
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    assert (root / "game/in_game" / DRAWINGS_FILE).is_file()
    shader = (root / "game/main_menu/gfx/FX/terra_incognita.shader").read_text(encoding="utf-8-sig")
    declared = re.search(
        r"TextureSampler\s+TerraIncognitaWorldTexture\s*\{(.*?)\}", shader, re.DOTALL
    )
    assert declared is not None
    assert re.search(rf"\bIndex\s*=\s*{DRAWINGS_INDEX}\b", declared.group(1))
    assert re.search(rf'(?i)\bfile\s*=\s*"{re.escape(DRAWINGS_FILE)}"', declared.group(1))


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
    stats = cast("dict[str, dict[str, dict[str, int]]]", report["text_stats"])
    guarded = stats["content"]["guarded"]
    # The same in every world: 82 events, the canal chain's advance and decisions, the
    # pilgrimage, the eight scripted names; formables vary with the cultures a world holds.
    assert {name: guarded[name] for name in guarded if name != "common/formable_countries"} == {
        "common/advances": 1,
        "common/decisions": 3,
        "common/generic_actions": 1,
        "common/scripted_country_names": 8,
        "events": 82,
    }
    assert 3 <= guarded["common/formable_countries"] <= 8
    places = cast("dict[str, dict[str, str]]", report["text_stats"])["exceptional_places"]
    assert len(places) >= 3  # silver, mercury and fish are found in any New World
    assert set(places) <= {spec.modifier for spec in SPECS}
    if record.game.fingerprint_sha256 != golden["game_fingerprint_sha256"]:
        pytest.skip(f"the reference world is for {golden['game_label']}, not {record.game.label}")
    output = cast("dict[str, object]", golden["output"])
    assert record.output_sha256 == output["sha256"]
    assert record.output_count == output["count"]


def test_local_layers_keep_to_themselves(tmp_path: Path) -> None:
    """Rerolling the peoples leaves the exceptional places, rerolling the resources the countries.

    Three exports, about five minutes, so only with ``RNW_LAYERS=1`` (content plan, N1).
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None or os.environ.get("RNW_LAYERS") != "1":
        pytest.skip("EU5_GAME_DIR and RNW_LAYERS=1 are needed")
    golden = cast("dict[str, object]", json.loads(GOLDEN_WORLD.read_text(encoding="utf-8")))
    code = decode(str(golden["code"]))

    def made(name: str, text: str) -> tuple[dict[str, str], dict[str, str]]:
        part = decode(text)
        report = export_new_world(
            Path(root_value),
            tmp_path / "generated" / f"rnw_exp_{name}",
            seed=part.seed,
            settings=part.settings(),
            world_code=text,
        )
        stats = cast("dict[str, dict[str, str]]", report["text_stats"])
        files = cast("list[dict[str, str]]", report["files"])
        wanted = ("main_menu/setup/1337/10_countries.txt", DEFINITION_FILE)
        digests = {
            record["path"].partition("/")[2]: record["sha256"]
            for record in files
            if record["path"].partition("/")[2] in wanted
        }
        assert len(digests) == len(wanted)
        return stats["exceptional_places"], digests

    base_places, base_countries = made("base", str(golden["code"]))
    peoples_places, peoples_countries = made("peoples", encode(rolled(code, "peoples")))
    resource_places, resource_countries = made("resources", encode(rolled(code, "resources")))
    assert base_places
    assert peoples_places == base_places
    assert peoples_countries != base_countries
    assert resource_places != base_places
    assert resource_countries == base_countries
