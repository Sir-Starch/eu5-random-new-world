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

from rnw import colonial_names, content_report, epoch, splnet
from rnw.app.discovery import find_games
from rnw.app.worldcode import decode, encode, rolled
from rnw.content import FAMILIES
from rnw.contract import CONTRACT_FILES, fingerprint
from rnw.eu5_biomes import PRECIOUS, template_attributes
from rnw.eu5_canvas import select_canvas
from rnw.eu5_formation import FORMABLES_FILE
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
from rnw.eu5_map import DEFINITIONS, RIVER_LAND, RIVER_WATER, load_map, read_class_lists
from rnw.eu5_natives import DEFAULT_CITY, DEFAULT_TOWN, DEFINITION_FILE, vanilla_natives
from rnw.eu5_newworld import vanilla_geometry
from rnw.eu5_nw_export import binding_problems, calibrate_development, export_new_world
from rnw.eu5_places import SPECS
from rnw.eu5_slots import CLIMATE_GROUPS, COAST_SLOTS, TOPOGRAPHY_GROUPS, SlotTables, synthesize
from rnw.eu5_splines import GAME_FILE as SPLINE_GAME_FILE
from rnw.eu5_splines import land_contacts
from rnw.eu5_story import START_FILE
from rnw.eu5_terrain import DecalStore
from rnw.eu5_towns import plan_towns
from rnw.formations import SPECS as FORMATION_SPECS
from rnw.game_texts import sources, untranslated
from rnw.geography import color_summary, read_locations, summary
from rnw.languages import official_languages
from rnw.model import WATER_CLASSES, CellClass
from rnw.pdx import parse
from rnw.record import Record
from rnw.settings import RESOURCE_FIELDS
from rnw.stories import STORIES
from rnw.storymodel import render_events, render_hook
from rnw.translations import GAME, problems

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
    assert vanilla.state_floor.peasants == 338
    assert vanilla.state_floor.share == 122
    assert {"amerindian_tribe", "amerindian_monarchy"} <= vanilla.templates
    assert "PAM" in vanilla.reserved_tags
    assert any(culture.state_include for culture in vanilla.cultures.values())
    assert any(culture.city_setup for culture in vanilla.cultures.values())
    # Every urban template the generator can select must support the native-capacity adapter,
    # including cultures absent from this epoch's reference world.
    templates = {("city", DEFAULT_CITY), ("town", DEFAULT_TOWN)}
    templates.update(
        (rank, setup)
        for culture in vanilla.cultures.values()
        for rank, setup in (("city", culture.city_setup), ("town", culture.town_setup))
        if setup
    )
    ranks = {f"{rank}_{setup}": (rank, setup) for rank, setup in sorted(templates)}
    towns = plan_towns(root, ranks, dict.fromkeys(ranks, 0), dict.fromkeys(ranks, 0))
    assert towns.ranks.keys() == ranks.keys()
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
    # R7d: the republic, the theocracy, the confederates and the positions of the four societies
    archetypes = vanilla.archetypes
    assert archetypes is not None
    assert archetypes.republic_include == "amerindian_advanced_republic_not_nahuatl_no_coast"
    assert dict(archetypes.republic_government) == {
        "type": "republic",
        "heir_selection": "oligarchic_elective",
    }
    assert archetypes.republic_level == 2
    assert dict(archetypes.theocracy) == {
        "type": "theocracy",
        "heir_selection": "theocratic_elective",
    }
    assert dict(archetypes.cohesion) == {"gold": 100, "stability": 33, "tribal_cohesion": 90}
    assert 1500 <= archetypes.confederate_density <= 1800
    assert dict(archetypes.sliders["sea_league"]) == {"land_vs_naval": 60}
    assert dict(archetypes.sliders["sacred_centre"]) == {
        "spiritualist_vs_humanist": -90,
        "traditionalist_vs_innovative": -90,
    }
    assert (archetypes.alliances, archetypes.rivals, archetypes.confederations) == (22, 45, 1)


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
    assert inventory.uncarried == []  # a replaced object says what carries it, or that none does
    assert inventory.stale_carriers == []
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
    # The release check of L1: every language the game ships has current translations.
    assert untranslated(languages) == []
    assert problems(GAME, sources(), languages) == []


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


WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _vanilla_words(root_value: str) -> set[str]:
    """Every word of the game's own scripts."""
    game = Path(root_value) / "game"
    found: set[str] = set()
    for directory in ("in_game/common", "in_game/events", "main_menu/common"):
        for path in (game / directory).rglob("*.txt"):
            found.update(WORD.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    # the names of places, provinces and areas are in the map's definitions
    found.update(WORD.findall((game / "in_game/map_data/definitions.txt").read_text("utf-8-sig")))
    return found


def _unknown_words(root_value: str, written: str, ours: set[str]) -> list[str]:
    """The words of ``written`` that are neither the game's, nor the mod's own (``rnw_*``)."""
    script = re.sub(r"rnw_[\w.]*", " ", re.sub(r"#[^\n]*", "", written))  # comments, own keys
    used = {
        found
        for found in WORD.findall(script)
        if not found.startswith(("rnw_", "var")) and found not in ours and not found.isdigit()
    }
    return sorted(used - _vanilla_words(root_value))


def test_local_story_scripts_use_only_words_the_game_uses() -> None:
    """Every effect, trigger and key the stories write is a word of the game's own scripts.

    A story names no game object the game lacks: a misspelt effect would be an unknown one at
    load and its event would not work. The mod's own names (``rnw_*``), the scopes the stories
    save and the event keys are the only words that are not vanilla's.
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    ours = {"target_location", "other_location", "target_country", "home_place", "seat_place"}
    written = "\n".join(render_events(story) for story in STORIES)
    written += "\n" + render_hook(STORIES) + "\n" + colonial_names.script(["mesoamerica_region"])
    # the formables' words are checked on the vanilla names they use
    for spec in FORMATION_SPECS:
        written += f"\n{spec.rank} {spec.emblem[:-4]} " + " ".join((*spec.allow, *spec.potential))
    assert _unknown_words(root_value, written, ours) == []


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
    original = read_locations(game_dir / DEFINITIONS)
    seas = set(read_class_lists(game_dir / "game/in_game/map_data/default.map")["sea_zones"])
    sea_areas = {place.area for place in original if place.key in seas}
    land = [
        place for place in original if place.continent == "america" and place.area not in sea_areas
    ]
    physical = cast(
        "list[dict[str, object]]", cast("dict[str, object]", report["generated"])["physical_keys"]
    )
    expected = {name for place in land for name in (place.region, place.area)}
    assert {row["key"] for row in physical} == expected
    assert len(physical) == len(expected)  # every original land key exactly once, N5
    assert sum(cast("int", row["cost"]) for row in physical) <= sum(
        cast("int", row["positional_cost"]) for row in physical
    )
    stats = cast("dict[str, dict[str, dict[str, int]]]", report["text_stats"])
    guarded = stats["content"]["guarded"]
    # On 1.4.5: 83 events (including the DLC diaspora), the canal chain's advance and decisions,
    # the pilgrimage and eight scripted names; formables vary with the world's cultures.
    assert {name: guarded[name] for name in guarded if name != "common/formable_countries"} == {
        "common/advances": 1,
        "common/decisions": 3,
        "common/generic_actions": 1,
        "common/scripted_country_names": 8,
        "events": 83,
    }
    assert 3 <= guarded["common/formable_countries"] <= 8
    # The two American monuments of the DLC packs (Teotihuacan, Cholula) are dropped with their
    # places, as their pictures are; no object of the game's scripts is left naming a key the
    # world lacks (the export refuses it, ``check_outcomes``).
    monuments = cast(
        "dict[str, int]", cast("dict[str, object]", report["text_stats"])["monuments_dropped"]
    )
    assert sum(monuments.values()) == 2
    places = cast("dict[str, dict[str, str]]", report["text_stats"])["exceptional_places"]
    assert len(places) >= 3  # silver, mercury and fish are found in any New World
    assert set(places) <= {spec.modifier for spec in SPECS}
    stories = cast("dict[str, dict[str, object]]", report["text_stats"])["stories"]
    offered = cast("dict[str, int]", stories["opportunities"])
    assert all(offered[family] >= 1 for family in FAMILIES)  # the reference world offers each
    if record.game.fingerprint_sha256 != golden["game_fingerprint_sha256"]:
        pytest.skip(f"the reference world is for {golden['game_label']}, not {record.game.label}")
    output = cast("dict[str, object]", golden["output"])
    assert record.output_sha256 == output["sha256"]
    assert record.output_count == output["count"]


# The one file the resources layer writes: the raw material of every location and the exceptional
# places. The peoples layer writes the start, the countries, the formables, the stories and the
# texts, and no file of the land (``in_game/map_data``, ``in_game/gfx``, ``main_menu/gfx``).
RESOURCES_FILE = "in_game/map_data/location_templates.txt"
PEOPLES_DIRS = (
    "main_menu/setup/1337/",
    "in_game/setup/countries/",
    "in_game/common/",
    "in_game/events/",
    "main_menu/common/",
    "main_menu/localization/",
)


def test_local_layers_keep_to_themselves(tmp_path: Path) -> None:
    """Rerolling the peoples leaves the land and the resources, rerolling the resources the rest.

    Every file of the three mods is compared, not a chosen few (content plan, F2): the resources'
    reroll changes exactly one file; the peoples' reroll changes files of the start, the
    countries, the formables, the stories and the texts only, and never the resources' file. The
    exceptional places are the resources', the countries and the stories the peoples'.
    Three exports, about five minutes, so only with ``RNW_LAYERS=1`` (content plan, N1 and N3).
    """
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None or os.environ.get("RNW_LAYERS") != "1":
        pytest.skip("EU5_GAME_DIR and RNW_LAYERS=1 are needed")
    golden = cast("dict[str, object]", json.loads(GOLDEN_WORLD.read_text(encoding="utf-8")))
    code = decode(str(golden["code"]))

    def made(name: str, text: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        part = decode(text)
        report = export_new_world(
            Path(root_value),
            tmp_path / "generated" / f"rnw_exp_{name}",
            seed=part.seed,
            settings=part.settings(),
            world_code=text,
        )
        stats = cast("dict[str, object]", report["text_stats"])
        places = cast("dict[str, str]", stats["exceptional_places"])
        starts = cast("dict[str, str]", cast("dict[str, object]", stats["stories"])["starts"])
        files = cast("list[dict[str, str]]", report["files"])
        digests = {
            record["path"].partition("/")[2]: record["sha256"]
            for record in files
            if not record["path"].partition("/")[2].startswith(".metadata/")
        }
        return places, starts, digests

    def changed(first: dict[str, str], second: dict[str, str]) -> set[str]:
        return {
            path for path in first.keys() | second.keys() if first.get(path) != second.get(path)
        }

    base_places, base_starts, base_files = made("base", str(golden["code"]))
    peoples_places, peoples_starts, peoples_files = made("peoples", encode(rolled(code, "peoples")))
    resource_places, resource_starts, resource_files = made(
        "resources", encode(rolled(code, "resources"))
    )
    assert base_places
    assert base_starts
    assert peoples_places == base_places
    assert peoples_starts != base_starts
    assert resource_places != base_places
    assert resource_starts == base_starts
    assert changed(base_files, resource_files) == {RESOURCES_FILE}
    by_peoples = changed(base_files, peoples_files)
    assert by_peoples
    assert RESOURCES_FILE not in by_peoples
    assert {path for path in by_peoples if not path.startswith(PEOPLES_DIRS)} == set()
    # What the peoples own: the countries, their story starts, the formables over their land.
    for owned in (
        "main_menu/setup/1337/10_countries.txt",
        DEFINITION_FILE,
        START_FILE,
        FORMABLES_FILE,
        "main_menu/localization/english/rnw_story_l_english.yml",
    ):
        assert owned in by_peoples, owned
    # The names of colonies follow the land's regions, whoever lives there.
    assert colonial_names.NAMES_FILE not in by_peoples


def test_local_new_world_ordinary_resources_have_individual_controls() -> None:
    """A game patch adding a New World RGO requires a deliberate control/catalog update."""
    root_value = os.environ.get("EU5_GAME_DIR")
    if root_value is None:
        pytest.skip("EU5_GAME_DIR is not set")
    root = Path(root_value)
    attributes = template_attributes(
        (root / "game/in_game/map_data/location_templates.txt").read_text(encoding="utf-8-sig")
    )
    places = read_locations(root / DEFINITIONS)
    materials = {
        attributes[place.key]["raw_material"]
        for place in places
        if place.continent == "america" and "raw_material" in attributes.get(place.key, {})
    }
    assert materials - PRECIOUS == set(RESOURCE_FIELDS)
