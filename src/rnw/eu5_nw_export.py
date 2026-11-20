"""Stage a generated New World mod (T3: new IDs, native 1337 start) for EU5 1.4.1.

NOT GAME VALIDATED as a whole; the first generated start loaded in game [V-GAME C45].
Locations, provinces, coasts, relief, biomes (location templates), terrain decals,
water, vegetation instances and native societies are generated from one model; the
Old World is kept.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
import zlib
from collections import Counter, deque
from contextlib import suppress
from dataclasses import asdict, dataclass, replace
from functools import partial
from itertools import pairwise
from operator import attrgetter
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw import (
    __version__,
    _native,
    epoch,
    eu5_history_text,
    eu5_memories,
    game_texts,
    inputs,
    landcache,
    text_references,
    worldname,
)
from rnw import calibration as input_calibration
from rnw.app.gamenames import game_names
from rnw.app.worldcode import WorldCodeError, decode
from rnw.artifacts import (
    Spool,
    check_new_output,
    pixel_digest,
    spool_path,
    staged,
    write_bytes,
)
from rnw.atlas import JSON_FILE as ATLAS_JSON
from rnw.atlas import LABELS_FILE as ATLAS_LABELS
from rnw.atlas import to_files as atlas_files
from rnw.bundle import COVER_COPY
from rnw.content import OCEANS as OPEN_OCEANS
from rnw.content import plan_content
from rnw.content_check import check_decisions, check_outcomes
from rnw.content_inventory import world_footprint
from rnw.continent_domains import SHARED_OCEAN_DIVISOR, plan_domains
from rnw.continent_world import WorldRegion, absorb_ocean_specks, compose_regions, relocated_canvas
from rnw.eu5_ai import (
    PERSONALITIES,
    AiDecision,
    AiPersonalityError,
    Assignments,
    CountryContext,
    vanilla_profiles,
)
from rnw.eu5_ai import (
    assignments as ai_assignments,
)
from rnw.eu5_ai import (
    decide as decide_ai_personalities,
)
from rnw.eu5_ai import (
    lines as ai_personality_lines,
)
from rnw.eu5_ai import (
    verify as verify_ai_personalities,
)
from rnw.eu5_archetypes import (
    Bonds,
    Expected,
    alliance_lines,
    archetype_problems,
    confederation_lines,
    rival_lines,
)
from rnw.eu5_atlas import build_atlas
from rnw.eu5_biomes import (
    BIOME_DEFINITIONS,
    CLIMATE_STEP,
    GROUND_BLUR,
    TERRAIN_MATERIALS,
    CellBiomes,
    ClimateGrid,
    Generated,
    MaterialRegion,
    SizeModel,
    VanillaLocations,
    WastelandRegion,
    assign_biomes,
    biome_of,
    biome_rules,
    cell_ground_scores,
    cell_mean,
    cell_ruggedness,
    climate_grid,
    ground_field,
    label_statistics,
    material_counts,
    size_model,
    template_attributes,
    vanilla_locations,
    wasteland_settings,
    water_climates,
)
from rnw.eu5_canvas import (
    NEW_WORLD,
    OCEANS,
    Canvas,
    moved_pixels,
    open_map,
    place_islands,
    remainder_boxes,
)
from rnw.eu5_content import TENOCHTITLAN, ContentError, carry_out, cohort_places, culture_traits
from rnw.eu5_development import (
    VILLAGE,
    Development,
    DevelopmentCalibration,
    build_development,
    building_lines,
    calibrate,
    development_lines,
    development_rules,
    hundredths_text,
    river_sizes,
    shelter,
    template_harbours,
)
from rnw.eu5_empires import (
    FEAR,
    IRRITATED,
    OPINION_TYPES,
    PREY,
    TYRANT,
    EmpireCalibration,
    opinion_lines,
    road_lines,
    written_discoveries,
    written_ranks,
)
from rnw.eu5_export import MOD_NAME, STATUS, resolve_build
from rnw.eu5_history import installed_rules
from rnw.eu5_history_build import build_history_start as build_start_plan
from rnw.eu5_islands import moved_pixels_of, relocate_map, shifts
from rnw.eu5_lobby import (
    COVER_INCLUDE,
    DRAWINGS_INCLUDE,
    GRAPHICS_DEFINES,
    INCLUDE_DIRS,
    OWN_SAMPLERS,
    SCRIPTED_GUI_FILE,
    SHADER_DIR,
    SHADERS,
    binding_problem,
    cover_files,
    cover_grid,
    cover_include,
    cover_shader,
    drawings_include,
    land_colour,
    sampler_include,
    samplers_bound,
    shader_indexes,
    shader_samplers,
    unknown_colour,
)
from rnw.eu5_lobby_gui import GUI_FILES, patch_gui, scripted_gui_text
from rnw.eu5_localization import LocalizationError, map_name_files
from rnw.eu5_map import (
    ADJACENCIES,
    DEFAULT_MAP,
    DEFINITIONS,
    LOCATIONS,
    LOCATOR_FILES,
    LOCATOR_OVERRIDE,
    MAP_OBJECTS,
    NAMED_COLORS,
    PORTS,
    RIVER_LAND,
    RIVER_WATER,
    RIVERS,
    Eu5Map,
    differing_pixels,
    labels_from_rgb,
    load_map,
    open_png,
    read_class_lists,
)
from rnw.eu5_morocco import algeciras, apply_morocco_start, reserve_morocco
from rnw.eu5_mountains import mountain_relief
from rnw.eu5_natives import (
    COUNTRY_DIR,
    DEFINITION_FILE,
    VanillaNatives,
    city_lines,
    country_definitions,
    country_names,
    country_records,
    holy_site_outputs,
    market_lines,
    new_tags,
    pop_lines,
    regional_populations,
    regional_projection_inputs,
    regional_societies,
    vanilla_natives,
    vassal_lines,
)
from rnw.eu5_newworld import (
    Plan,
    RegionalLand,
    VanillaGeometry,
    plan_composed_identities,
    plan_identities,
    plan_regional_land,
    vanilla_geometry,
)
from rnw.eu5_objects import PixelClasses, object_outputs
from rnw.eu5_oceans import emitted_cells, plan_oceans
from rnw.eu5_overseas import overseas_flags, passable_contacts
from rnw.eu5_places import OUTPUT as OUTPUT_PLACES
from rnw.eu5_places import SPECS, Cells, Spec, choose, modifiers_file, payloads
from rnw.eu5_places import texts as place_texts
from rnw.eu5_regional_history import project_regional_start, shared_routes, simulate_region
from rnw.eu5_regionkeys import physical_keys
from rnw.eu5_remap import (
    RemapAccess,
    RemapRegions,
    build_remap,
    mounted_text_files,
    remap_discoveries,
    remap_scripts,
    remap_text,
)
from rnw.eu5_reveal import RevealError
from rnw.eu5_reveal import files as reveal_files
from rnw.eu5_reveal import verify as verify_reveal
from rnw.eu5_rewrite import (
    HierarchyAdditions,
    drop_block_entries,
    insert_into_block,
    prune_regional_setup,
    prune_setup,
    retained_capitals,
    rewrite_class_lists,
    rewrite_csv,
    rewrite_definitions,
    rewrite_locators,
    rewrite_named_colors,
    rewrite_override_locators,
    rewrite_templates,
    sound_toll_locations,
)
from rnw.eu5_rivers import RiverRasterError, encode_rivers, watershed_spans
from rnw.eu5_seas import (
    NO_UNITS,
    VFX_LOCATORS,
    Coast,
    SeaError,
    VanillaPort,
    Water,
    current_bands,
    current_text,
    mediterranean_crossing,
    read_ports,
    read_waters,
    settle_coast,
    shape_water,
    straddles_seam,
    verify_crossings,
    verify_locators,
    verify_seas,
)
from rnw.eu5_slots import (
    CLIMATE_GROUPS,
    COAST_SLOTS,
    LEVELS,
    SLOTS,
    TOPOGRAPHY_GROUPS,
    SlotTables,
)
from rnw.eu5_splines import (
    GAME_FILE as SPLINE_GAME_FILE,
)
from rnw.eu5_splines import (
    MOD_FILE as SPLINE_FILE,
)
from rnw.eu5_splines import (
    build_splines,
    spline_problems,
    world_anchors,
    world_contacts,
)
from rnw.eu5_start import combine_starts
from rnw.eu5_story import Written, facts_of
from rnw.eu5_story import build as build_stories
from rnw.eu5_technology import written_records
from rnw.eu5_terrain import (
    LAND_CODE,
    MARGIN,
    OUTSIDE,
    WATER_CODE,
    DecalStore,
    ShiftedStore,
    TerrainInputs,
    level_shares,
    surface_heights,
    terrain_outputs,
)
from rnw.eu5_towns import plan_towns
from rnw.eu5_treaty import adapt as adapt_treaty
from rnw.eu5_treaty import coordinates as treaty_coordinates
from rnw.eu5_water import water_outputs
from rnw.game_texts import Text, localize, untranslated
from rnw.geography import parse_locations, parse_named_colors, read_locations, read_named_colors
from rnw.history_content import composed_facts as composed_history_facts
from rnw.history_content import country_starts
from rnw.history_content import facts as historical_content_facts
from rnw.history_model import Factor, Military
from rnw.history_output_checks import verify_combined_text, verify_diplomacy
from rnw.history_output_checks import verify_text as verify_history_text
from rnw.history_plan_checks import validate_projection
from rnw.land_contact import ContactTerrain, contact_box
from rnw.landmask import Fitted, LandMask, fit_drawing
from rnw.languages import official_languages
from rnw.layers import PEOPLES, RESOURCES, layer_seed
from rnw.loc_keys import KeySpace, key_hash, key_hashes
from rnw.model import CellClass
from rnw.newworld import (
    NewWorld,
    inland_sea_min_area,
    unported_cells,
)
from rnw.parallel import (
    GIB,
    Stages,
    available_memory,
    collector_paused,
    configure,
    cores,
    require_memory,
    stage_workers,
)
from rnw.pdx import Block, parse
from rnw.pictures import center_column, cover, tagged, thumbnail
from rnw.png import COLOR_PALETTE, COLOR_RGB, ZLIB_LEVEL, encode_png
from rnw.ports import ForeignCoast, coast_links, pair_lengths, plan_ports
from rnw.progress import (
    Progress,
    active,
    checkpoint,
    mark_ready,
    quiet_stages,
    run_stage,
    running,
    skip_stages,
)
from rnw.record import FORMAT, GameRecord, Record, manifest_digest, output_entries
from rnw.record import canonical as record_json
from rnw.relief import COAST_HEIGHT
from rnw.rivers import (
    NONE,
    RiverGenerationError,
    Rivers,
    carve_valleys,
    flow_classes,
    generate_rivers,
    network_problems,
    outlet_problems,
)
from rnw.rivers import STEP as RIVER_STEP
from rnw.rng import derive_seed
from rnw.sea_corridors import corridor_paths, draw_corridors
from rnw.seas import Shape, Topography, inland_seas
from rnw.settings import RESOURCES as RESOURCE_DEFAULTS
from rnw.settings import MoroccoPolicy, ResourceSettings, canonical_json, run_spec, spec_digest
from rnw.societies import STATE
from rnw.splnet import SplineError
from rnw.timing import measured
from rnw.topology import (
    adjacency_pairs,
    component_counts,
    distance_from,
    label_components,
    unpack_pairs,
)
from rnw.vanilla_world import with_real_americas
from rnw.watersheds import domain_climate, domain_rivers
from rnw.wording import reference, render

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from concurrent.futures import Future
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.barrens import WastelandSettings
    from rnw.continent_domains import Domain
    from rnw.continent_world import ComposedWorld
    from rnw.eu5_islands import Moved
    from rnw.eu5_morocco import MoroccoStart
    from rnw.eu5_remap import GeographicRemap
    from rnw.eu5_rewrite import SetupResult
    from rnw.eu5_start import Country, FinalStartPlan, PopCohort
    from rnw.game_texts import Entry
    from rnw.geography import Location
    from rnw.land_contact import ContactBlend
    from rnw.settings import NewWorldSettings, Settings
    from rnw.vanilla_world import VanillaWorld
    from rnw.wording import Name
    from rnw.worldname import Label

TEMPLATES: Final[str] = "game/in_game/map_data/location_templates.txt"
MAX_LOCATIONS: Final[int] = 32_000
AMERICAN_GENERATION: Final[frozenset[str]] = frozenset({NEW_WORLD})
RIVER_CLASSES: Final[int] = 16
# Vanilla uses widths 4, 5, 11 and 15 on 61.5%, 23.9%, 8.1% and 6.2% of Old World river
# pixels [V-EXEC C59]; valleys are cut in proportion (vanilla rivers lie a median 318
# and a quarter of them over 950 height units below the 17-pixel local mean).
RIVER_WIDTH_CODES: Final[tuple[int, ...]] = (4, 5, 11, 15)
# The river size the game's development rule (`river = 0.5`) multiplies, by width code: the start
# development of an owner's 1.4.4 save gives 2, 2, 4 and 6 for 4, 5, 11 and 15 [V-LOCAL C500].
RIVER_SIZES: Final[dict[int, int]] = {4: 2, 5: 2, 11: 4, 15: 6}
RIVER_WIDTH_SHARES: Final[tuple[int, ...]] = (615, 239, 84, 62)
RIVER_VALLEY_DEPTHS: Final[tuple[int, ...]] = (350, 550, 850, 1150)
RIVER_VALLEY_PX: Final[int] = 6
MIN_LEVEL_PIXELS: Final[int] = 2000
SETUP_DIR: Final[str] = "game/main_menu/setup/1337"
SETUP_TEMPLATES: Final[str] = "game/main_menu/setup/templates"
# The game versions a world's mod says it supports, and the file of the inputs beside the world.
SUPPORTED_GAME: Final[str] = "1.4.*"
INPUTS_FILE: Final[str] = "inputs.json"
LAND_MASK_FILE: Final[str] = "land_mask.png"
ROTATION: Final[str] = "{ -0.000000 -0.000000 -0.000000 1.000000 }"
SCALE: Final[str] = "{ 1.000000 1.000000 1.000000 }"
TOPOGRAPHY: Final[re.Pattern[str]] = re.compile(r"topography\s*=\s*[A-Za-z_]+")
HARBOR: Final[re.Pattern[str]] = re.compile(r"\s*natural_harbor_suitability\s*=\s*-?[0-9.]+")
CURRENTS: Final[re.Pattern[str]] = re.compile(r"\s*movement_assistance\s*=\s*\{[^{}]*\}")
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# A localization entry: an indented key, an optional version number, then the text.
LOC_KEY: Final[re.Pattern[str]] = re.compile(r"^\s+([^\s:#\"]+):\d*\s", re.MULTILINE)
# Folders of the installation whose localization the engine loads.
LOC_ROOTS: Final[tuple[str, ...]] = ("game", "jomini", "clausewitz")
UNTESTED: Final[tuple[str, ...]] = (
    (
        "Terrain: height and material decal layers are rebuilt as compiled .info/.bin only; "
        "the vanilla PNG sources and terrain_cache/checksum.json are not changed."
    ),
    (
        "Vegetation instance files (*_generator_*.bin, jungle_dense text) are whole-file "
        "overrides with new instance counts; that EU5 loads them and their memory and "
        "startup cost are untested."
    ),
    (
        "Every generated (climate, vegetation, topography) combination resolves to a biome "
        "through the priority rules of biomes.txt; rare combinations may fall back to a "
        "partial match."
    ),
    (
        "Slots a biome's material list lacks are replaced on generated land; that the engine "
        "renders such slots with fallback_material is inferred from the shader."
    ),
    (
        "Generated rivers follow the vanilla rivers.png conventions measured on 1.4.1 "
        "(one source per network, join pixels, free tributary heads, mouths into water); "
        "that EU5 builds river meshes and river modifiers from them is untested."
    ),
    "nodes.dat and other derived caches are vanilla and may not match the new map.",
    "Colonisation, exploration, movement, naval routes, ports, save/load and startup time.",
    (
        "Development entries keyed by generated location keys, per-port harbour values and "
        "market villages in generated state capitals are untested; so is the estimate in "
        "the report (river size is inferred from the widest river pixel)."
    ),
    (
        "Native countries use new three-letter tags defined in "
        "in_game/setup/countries/rnw_natives.txt without scripted coats of arms; that EU5 "
        "accepts them, pop-type tribes on generated locations and engine-drawn coats of "
        "arms is untested."
    ),
    (
        "Holy sites of placed American religions move into their generated religion zones; "
        "religions and situations with special mechanics may still expect vanilla geography."
    ),
)
DEVELOPMENT_FILE: Final[str] = "14_development.txt"
BUILDINGS_FILE: Final[str] = "07_cities_and_buildings.txt"
COUNTRIES_FILE: Final[str] = "10_countries.txt"
TRIMMED_LOCATORS: Final[tuple[str, ...]] = ("unit_stack", "combat", "vfx")
LOCATOR_ID: Final[re.Pattern[str]] = re.compile(r"\bid=([A-Za-z0-9_]+)")
BASE_VALUES: Final[str] = (
    "game/main_menu/common/static_modifiers/location_historical_base_values.txt"
)
TEMPLATE_MODIFIER: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])modifier\s*=\s*([A-Za-z0-9_]+)"
)
# A donor's historical base value (Potosi's silver, say) belongs to that place alone.
DONOR_MODIFIER: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])modifier\s*=\s*[A-Za-z0-9_]+\s*"
)
# Blocks of the 1337 setup files that receive generated records, in the order of
# their additions in ``_text_outputs``.
SETUP_INSERTS: Final[dict[str, tuple[tuple[str, ...], ...]]] = {
    COUNTRIES_FILE: (("countries", "countries"),),
    PERSONALITIES: (("countries", "countries"),),
    BUILDINGS_FILE: (("locations",), ("building_manager",)),
    "03_markets.txt": (("market_manager",),),
    "09_roads.txt": (("road_network",),),
    "12_diplomacy.txt": (("diplomacy_manager",), ("diplomacy_manager",)),
    "15_international_organizations.txt": (("international_organization_manager",),),
    DEVELOPMENT_FILE: (("development",),),
    "18_opinions.txt": (("diplomacy_manager",),),
    "20_rivals.txt": (("diplomacy_manager",),),
}


# The setup files the extraordinary societies of R7d write into or read back.
ARCHETYPE_FILES: Final[tuple[str, ...]] = (
    COUNTRIES_FILE,
    "12_diplomacy.txt",
    "15_international_organizations.txt",
    "20_rivals.txt",
)


# The smallest working set of an export: its peak with one thread and the thinnest bands
# (6.8 GiB on the continents preset since the strips of the written-map check, 8.1 GiB in
# 1.2.0, ADR 0006), plus the margin the ADR keeps.
EXPORT_MEMORY: Final[int] = 8 * GIB
# A background region needs its raster fields, cells, and the native stage's scratch space.
REGIONAL_BYTES_PER_PIXEL: Final[int] = 64


class NewWorldExportError(ValueError):
    """Generated output failed an offline invariant."""


class LocationLimitError(NewWorldExportError):
    """A generated world exceeds the safety limit on location identities."""

    def __init__(self, count: int, limit: int) -> None:
        self.count: int = count
        self.limit: int = limit
        super().__init__(f"{count} locations exceed the {limit} safety cap")


def _canvas_pixels(canvas: Canvas, final: NDArray[np.int32]) -> NDArray[np.bool_]:
    """Where the canvas lies on the map (``final``'s shape), as the map holds it, seam wrapped."""
    pixels = np.zeros(final.shape, dtype=bool)
    canvas.put(pixels, np.ones(canvas.mask.shape, dtype=bool))
    return pixels


def _world_columns(canvas: Canvas, columns: NDArray[np.int64]) -> NDArray[np.int64]:
    return (columns + canvas.col0 - canvas.roll) % canvas.shape[1]


def _coastal(world: NewWorld) -> NDArray[np.bool_]:
    flags = np.zeros(len(world.classes), dtype=bool)
    for first, second in world.edges:
        first_sea = world.classes[first] is CellClass.SEA
        second_sea = world.classes[second] is CellClass.SEA
        if first_sea != second_sea:
            flags[second if first_sea else first] = True
    return flags


def _land_count(world: NewWorld) -> int:
    """How many cells are land. The generator numbers land first, then sea, then lakes, and the
    coast stages only fold sea cells together, so the land cells keep their numbers from the
    plan of their wastelands to the written world."""
    count = sum(kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes)
    if any(kind not in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes[:count]):
        message = "The generated land cells do not come before its water cells"
        raise NewWorldExportError(message)
    return count


def _generated(
    canvas: Canvas,
    world: NewWorld,
    count: int | None = None,
    *,
    surface: NDArray[np.uint16] | None = None,
    ground: tuple[SizeModel, ClimateGrid] | None = None,
) -> Generated:
    """The first ``count`` cells of ``world`` (all by default) as the biome model reads them;
    with the ``surface`` the decals show (epoch 64, ``epoch.ROUGH_HILLS``; ``_surface``) their
    mean height, roughness and ruggedness are read from it, as vanilla's are from its decals,
    and with the ``ground`` model and the world's climate grid the ground votes of their land
    (``eu5_biomes.ground_field``, ``cell_ground_scores``)."""
    count = len(world.classes) if count is None else count
    votes = None
    if surface is not None and ground is not None:
        field = ground_field(
            ground[0],
            (world.labels >= 0) & (world.labels < count),
            surface,
            ground[1],
            columns=partial(_world_columns, canvas),
        )
        votes = cell_ground_scores(world.labels, count, field)
        del field
    points = np.stack(
        [world.centroids[:count, 0], _world_columns(canvas, world.centroids[:count, 1])], axis=1
    )
    return Generated(
        kinds=world.classes[:count],
        points=points,
        mean_height=(
            world.mean_elevation[:count]
            if surface is None
            else cell_mean(world.labels, surface, count)
        ),
        spread=world.spread[:count],
        edges=tuple((a, b) for a, b in world.edges if a < count and b < count),
        coastal=_coastal(world)[:count],
        pixels=world.pixels[:count],
        ruggedness=(
            None
            if surface is None
            else cell_ruggedness(world.labels, surface, count, blur=GROUND_BLUR)
        ),
        ground=votes,
    )


def _surface(game_map: Eu5Map, canvas: Canvas, world: NewWorld, seed: int) -> NDArray[np.uint16]:
    """The primary height the decals will show over ``world`` (``eu5_terrain.surface_heights``),
    in its own coordinates: the codes and the vanilla water of the map around the canvas as the
    decals read them, its relief before the rivers carve their valleys and its coasts settle.
    On world gady3byywf the ground vote on it agreed on 96 % of the 6682 land locations with the
    vote on the written primary heights; most of the rest are wetlands against flatland on the
    coasts that settle later [V-EXEC 2026-11-14]."""
    rows, span = (int(size) for size in world.labels.shape)
    width = int(game_map.labels.shape[1])
    columns = (
        np.arange(-MARGIN, span + MARGIN, dtype=np.int64) + canvas.col0 - canvas.roll
    ) % width
    water_kind = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
    )
    world_codes = _codes(game_map, canvas, world)
    codes = np.empty((rows, columns.size), dtype=np.int8)
    water = np.empty((rows, columns.size), dtype=bool)
    strip = 1024  # rows of the map's labels copied at a time
    for start in range(0, rows, strip):
        window = slice(start, min(rows, start + strip))
        codes[window] = np.take(world_codes[window], columns, axis=1)
        water[window] = water_kind[np.take(game_map.labels[window], columns, axis=1)]
    del world_codes
    return surface_heights(codes, water, world.elevation, seed=seed)


def _wasteland_settings(game_dir: Path, world: NewWorld, settings: Settings) -> WastelandSettings:
    """What the wasteland plan needs of the game and of the land cells of ``world``."""
    count = _land_count(world)
    polar = np.zeros(count, dtype=bool)
    edge = np.unique(world.labels[[0, -1], :])
    polar[edge[(edge >= 0) & (edge < count)]] = True
    barrier = np.zeros(count, dtype=bool)
    barrier[world.barrier] = True
    return wasteland_settings(
        biome_rules(_read(game_dir, BIOME_DEFINITIONS)),
        material_counts(_read(game_dir, TERRAIN_MATERIALS)),
        budget=count * settings.new_world.wasteland_permille // 1000,
        polar=polar,
        barrier=barrier,
    )


@measured
def _land_character(  # noqa: PLR0913 - the plan reads the map, the world, the vanilla climate and the game.
    game_map: Eu5Map,
    *,
    canvas: Canvas,
    world: NewWorld,
    vanilla: VanillaClimate,
    attributes: dict[str, dict[str, str]],
    game_dir: Path,
    settings: Settings,
    seed: int,
    material_seed: int,
    sizes: SizeModel | None,
) -> tuple[NewWorld, CellBiomes, dict[str, object]]:
    """The land of ``world`` with its wastelands planned (epoch 64 on), before its coasts.

    The ports, the docks and the strait crossings of the coast stage are made for the passable
    land beside the sea, so which cells are wasteland has to be known first. The climate and
    vegetation vote needs only the land cells and where the sea is, none of which the coast stages
    change, so it is made here once; the later biome stage adds the climates of the waters that
    remain. Returns the world with the planned classes, the biomes of its land cells and the
    statistics of their model.
    """
    count = _land_count(world)
    grid = _final_climate(game_map, canvas, world, _final_labels(game_map, canvas, world), vanilla)
    biomes, stats = assign_biomes(
        game_map=game_map,
        templates=attributes,
        vanilla=vanilla.locations,
        vanilla_grid=vanilla.grid,
        final_grid=grid,
        cells=_generated(
            canvas,
            world,
            count,
            surface=(
                _surface(game_map, canvas, world, seed)
                if settings.algorithm >= epoch.ROUGH_HILLS
                else None
            ),
            ground=None if sizes is None else (sizes, grid),
        ),
        seed=seed,
        precious_permille=settings.new_world.precious_permille,
        resources=settings.resources,
        material_seed=material_seed,
        wastelands=_wasteland_settings(game_dir, world, settings),
        open_climate=settings.algorithm >= epoch.OPEN_CLIMATE,
        ground=sizes,
        pooled_resources=settings.algorithm >= epoch.POOLED_RESOURCES,
    )
    if biomes.kinds is None:
        message = "The wasteland plan did not give the class of the land cells"
        raise NewWorldExportError(message)
    return replace(world, classes=(*biomes.kinds, *world.classes[count:])), biomes, stats


def composed_land_character(  # noqa: PLR0913 - common map, calibration and independent land plans.
    game_map: Eu5Map,
    shared: ComposedWorld,
    islands: Sequence[WorldRegion],
    *,
    geography: Mapping[str, NewWorldSettings],
    resources: Mapping[str, Mapping[str, int]],
    vanilla: VanillaClimate,
    attributes: dict[str, dict[str, str]],
    game_dir: Path,
    seed: int,
    material_seed: int,
    sizes: SizeModel,
) -> tuple[ComposedWorld, CellBiomes, dict[str, object]]:
    """Vote on all terrain once, with each continent's own wasteland and resource settings."""
    canvas, world = shared.canvas, shared.world
    count = _land_count(world)
    grid = _final_climate(game_map, canvas, world, _final_labels(game_map, canvas, world), vanilla)
    rules = biome_rules(_read(game_dir, BIOME_DEFINITIONS))
    materials = material_counts(_read(game_dir, TERRAIN_MATERIALS))
    resource_regions: dict[str, MaterialRegion] = {}
    wasteland_regions: dict[str, WastelandRegion] = {}
    boundary_votes: dict[int, tuple[int, int]] = {}
    polar = np.zeros(count, dtype=bool)
    touches = np.unique(world.labels[[0, -1], :])
    polar[touches[(touches >= 0) & (touches < count)]] = True
    for region in islands:
        local = region.world
        name = region.domain.continent.key
        land = _land_count(local)
        first = int(shared.cell_ids[name][0])
        cells = range(first, first + land)
        parameters = geography[name]
        if region.contact is not None:
            rows, columns = region.contact.box
            span = np.arange(int(columns.start), int(columns.stop), dtype=np.int64)
            span %= canvas.shape[1]
            boundary_votes.update(
                region.contact.biome_votes(
                    np.take(world.labels[rows], span, axis=1),
                    np.take(game_map.labels[rows], span, axis=1),
                    len(game_map.keys),
                )
            )
        barrier = np.zeros(land, dtype=bool)
        barrier[local.barrier] = True
        resource_regions[name] = MaterialRegion(
            cells,
            derive_seed(material_seed, "continent", name),
            resources.get(name, {}),
            parameters.precious_permille,
        )
        wasteland_regions[name] = WastelandRegion(
            cells,
            replace(
                wasteland_settings(
                    rules,
                    materials,
                    budget=land * parameters.wasteland_permille // 1000,
                    polar=polar[first : first + land],
                    barrier=barrier,
                ),
                land_connection=frozenset(local.land_link.tolist()),
            ),
            derive_seed(seed, "continent", name),
        )
    biomes, stats = assign_biomes(
        game_map=game_map,
        templates=attributes,
        vanilla=vanilla.locations,
        vanilla_grid=vanilla.grid,
        final_grid=grid,
        cells=_generated(
            canvas,
            world,
            count,
            surface=_surface(game_map, canvas, world, seed),
            ground=(sizes, grid),
        ),
        seed=seed,
        open_climate=True,
        ground=sizes,
        pooled_resources=True,
        regional_resources=resource_regions,
        regional_wastelands=wasteland_regions,
        boundary_votes=boundary_votes,
    )
    if biomes.kinds is None:
        message = "The composed wasteland plans did not classify the land cells"
        raise NewWorldExportError(message)
    kinds = (*biomes.kinds, *world.classes[count:])
    waters = water_climates(
        game_map,
        templates=attributes,
        vanilla=vanilla.locations,
        vanilla_grid=vanilla.grid,
        final_grid=grid,
        cells=_generated(canvas, world),
    )
    return (
        replace(shared, world=replace(world, classes=kinds)),
        _with_waters(biomes, waters, len(kinds)),
        stats,
    )


def settled_biomes(biomes: CellBiomes, source: NewWorld, coast: Coast) -> CellBiomes:
    """Keep each surviving cell's climate, with merged water taking its largest part's climate."""
    largest = [-1] * len(coast.world.classes)
    for old, new in enumerate(coast.source_cells):
        previous = largest[new]
        if previous < 0 or source.pixels[old] > source.pixels[previous]:
            largest[new] = old
    if min(largest, default=0) < 0:
        message = "A settled location has no source for its climate"
        raise NewWorldExportError(message)
    return CellBiomes(
        tuple(biomes.climate[i] for i in largest),
        tuple(biomes.vegetation[i] for i in largest),
        tuple(biomes.topography[i] for i in largest),
        tuple(biomes.raw_material[i] for i in largest),
    )


def _template_bodies(text: str) -> dict[str, str]:
    root = parse(text)
    return {
        entry.key: text[entry.value.open : entry.value.close + 1]
        for entry in root.entries
        if entry.key is not None and isinstance(entry.value, Block)
    }


def retired_base_modifiers(bodies: dict[str, str], removed: set[str]) -> set[str]:
    """Historical base values that only removed locations' templates use.

    The file's values are applied by ``modifier = name`` in location templates alone
    [V-LOCAL 1.4.2, C95], so a value no kept template names is never used again and the
    engine would log it as unused.
    """
    gone: set[str] = set()
    kept: set[str] = set()
    for key, body in bodies.items():
        (gone if key in removed else kept).update(TEMPLATE_MODIFIER.findall(body))
    return gone - kept


def _donor_map(  # noqa: PLR0913 - donor search needs map, canvas, world and geometry.
    game_map: Eu5Map,
    *,
    canvas: Canvas,
    world: NewWorld,
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    bodies: dict[str, str],
) -> list[str]:
    """Nearest removed vanilla location of the same family, per generated cell."""
    family = {
        CellClass.LAND: (CellClass.LAND, CellClass.NON_OWNABLE),
        CellClass.WASTELAND: (CellClass.WASTELAND,),
        CellClass.SEA: (CellClass.SEA,),
        CellClass.LAKE: (CellClass.LAKE,),
    }
    touched = canvas.removed | canvas.trimmed
    donors: dict[CellClass, NDArray[np.int64]] = {}
    for kind, members in family.items():
        found = [
            index
            for index in np.flatnonzero(touched).tolist()
            if game_map.classes[index] in members and game_map.keys[index] in bodies
        ]
        donors[kind] = np.array(found or donors.get(CellClass.LAND, []), dtype=np.int64)
    centres = np.stack([world.centroids[:, 0], world.centroids[:, 1] + canvas.col0], axis=1)
    chosen = [""] * len(world.classes)
    for kind, pool in donors.items():
        cells = np.array([i for i, k in enumerate(world.classes) if k is kind], dtype=np.int64)
        if not cells.size or not pool.size:
            continue
        donor_points = np.stack([rows[pool], columns[pool]], axis=1)
        for start in range(0, cells.size, 2048):
            chunk = cells[start : start + 2048]
            delta = centres[chunk][:, np.newaxis, :] - donor_points[np.newaxis, :, :]
            best = np.argmin((delta * delta).sum(axis=2), axis=1)
            for cell, donor in zip(chunk.tolist(), pool[best].tolist(), strict=True):
                chosen[cell] = game_map.keys[donor]
    return chosen


def _set_field(body: str, name: str, value: str) -> str:
    """Set ``name = value`` in a one-line template body, appending it when absent."""
    pattern = re.compile(rf"\b{name}\s*=\s*[A-Za-z_]+")
    if not value:
        return pattern.sub("", body, count=1)
    if pattern.search(body):
        return pattern.sub(f"{name} = {value}", body, count=1)
    return body[:-1].rstrip() + f" {name} = {value} }}"


def _template_lines(  # noqa: PLR0913, PLR0917 - a template line reads every generated input.
    plan: Plan,
    donors: list[str],
    bodies: dict[str, str],
    biomes: CellBiomes,
    harbours: dict[str, int],
    places: dict[int, Spec],
    water: Water,
    *,
    regional_pops: Mapping[str, tuple[PopCohort, ...]] | None = None,
) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    retained: set[str] = plan.oceans.retained if plan.oceans is not None else set()
    for index, cell in enumerate(plan.cells):
        if cell.key in seen or cell.key in retained:
            continue
        seen.add(cell.key)
        body = DONOR_MODIFIER.sub("", bodies[donors[index]])
        if cell.kind in {CellClass.LAND, CellClass.WASTELAND}:
            for name, values in (
                ("topography", biomes.topography),
                ("vegetation", biomes.vegetation),
                ("climate", biomes.climate),
                ("raw_material", biomes.raw_material),
            ):
                body = _set_field(body, name, values[index])
            if regional_pops is not None and (cohorts := regional_pops.get(cell.key)):
                primary = max(cohorts, key=attrgetter("amount"))
                body = _set_field(body, "culture", primary.culture)
                body = _set_field(body, "religion", primary.religion)
            body = HARBOR.sub("", body)
            if cell.key in harbours:
                value = hundredths_text(harbours[cell.key])
                body = body[:-1].rstrip() + f" natural_harbor_suitability = {value} }}"
            if index in places:
                body = body[:-1].rstrip() + f" modifier = {places[index].modifier} }}"
        elif cell.kind is CellClass.SEA:
            body = TOPOGRAPHY.sub(f"topography = {water.waters.topography[index]}", body, count=1)
            body = CURRENTS.sub("", body)
            if index in water.flows:
                body = body[:-1].rstrip() + f" {current_text(water.flows[index])} }}"
            body = _set_field(body, "climate", biomes.climate[index])
        else:
            body = _set_field(body, "climate", biomes.climate[index])
        lines.append(f"{cell.key} = {body}")
    if plan.oceans is not None:
        lines.extend(
            f"{cell.key} = {bodies[plan.oceans.sources[cell.key]]}" for cell in plan.oceans.extra
        )
    return lines


def _crossing_rows(plan: Plan, canvas: Canvas, water: Water) -> list[str]:
    """The rows of ``adjacencies.csv`` for the straits between generated lands (``rnw.straits``).

    As the game writes them: the two land locations, ``sea``, the sea zone between, the point on
    the first and the point on the second (map x, then y from the south), a comment.
    """
    rows: list[str] = []
    height = canvas.shape[0]
    for item in sorted(
        (item for item in water.crossings if not straddles_seam(canvas, item)),
        key=lambda crossing: (plan.cells[crossing.first].key, plan.cells[crossing.second].key),
    ):
        columns = _world_columns(
            canvas, np.array([item.start[1], item.stop[1]], dtype=np.int64)
        ).tolist()
        first, second = plan.cells[item.first].key, plan.cells[item.second].key
        through = plan.cells[item.through].key
        start_y, stop_y = height - 1 - item.start[0], height - 1 - item.stop[0]
        rows.append(
            f"{first};{second};sea;{through};{columns[0]};{start_y};{columns[1]};{stop_y};xxx"
        )
    return rows + [crossing.row(height) for crossing in water.external_crossings]


def _port_contacts(
    world: NewWorld, land: NDArray[np.bool_], sea: NDArray[np.bool_]
) -> NDArray[np.int64]:
    labels = world.labels
    width = labels.shape[1]
    contacts = _native.coastal_pixels(np.ascontiguousarray(labels), land, sea)
    if not world.wrap_x:
        return contacts
    across: list[NDArray[np.int64]] = []
    for shore, water in ((0, width - 1), (width - 1, 0)):
        bank, neighbour = labels[:, shore], labels[:, water]
        rows = np.flatnonzero(land[bank] & sea[neighbour])
        across.append(
            np.column_stack((bank[rows], neighbour[rows], rows * width + shore)).astype(np.int64)
        )
    return np.concatenate((contacts, *across))


@measured
def _ports(
    plan: Plan,
    world: NewWorld,
    canvas: Canvas,
    foreign: ForeignCoast,
    vanilla: Mapping[str, VanillaPort],
) -> tuple[list[str], dict[int, tuple[int, int]]]:
    """One port per land location, a port for every coastal sea zone (``rnw.ports``).

    A land cell's port stands on its border with the sea it is given, nearest its centre. The
    vanilla land whose port row named a replaced sea zone gets a row to the generated sea cell it
    is given, with the coordinates of its old row.
    """
    links, needed = coast_links(world, foreign, pair_lengths(world))
    chosen = plan_ports(links, needed)
    if chosen.unserved:
        names = ", ".join(plan.cells[sea].key for sea in chosen.unserved[:5])
        message = f"{len(chosen.unserved)} coastal sea zones cannot be given a port: {names}"
        raise NewWorldExportError(message)
    labels = world.labels
    width = labels.shape[1]
    land = np.array([cell.kind is CellClass.LAND for cell in plan.cells] + [False])
    sea = np.array([cell.kind is CellClass.SEA for cell in plan.cells] + [False])
    land_cells, sea_cells, pixels = _port_contacts(world, land, sea).T
    rows_out: list[str] = []
    positions: dict[int, tuple[int, int]] = {}
    if land_cells.size:
        stride = len(plan.cells) + 1
        packed = land_cells * stride + sea_cells
        order = np.lexsort((pixels, packed))
        packed_sorted, pixels_sorted = packed[order], pixels[order]
        height = canvas.shape[0]
        for land_cell in sorted(cell for cell in chosen.port if cell >= 0):
            sea_cell = chosen.port[land_cell]
            key = land_cell * stride + sea_cell
            lo = np.searchsorted(packed_sorted, key, side="left")
            hi = np.searchsorted(packed_sorted, key, side="right")
            candidates = pixels_sorted[lo:hi]
            centre = world.interior[land_cell]
            horizontal = np.abs(candidates % width - centre[1])
            if world.wrap_x:
                horizontal = np.minimum(horizontal, width - horizontal)
            distance = (candidates // width - centre[0]) ** 2 + horizontal**2
            pixel = int(candidates[int(np.argmin(distance))])
            row, column = divmod(pixel, width)
            x = int(_world_columns(canvas, np.array([column], dtype=np.int64))[0])
            dock_row, dock_column = row, column
            for d_row, d_column in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                r, c = row + d_row, column + d_column
                if world.wrap_x:
                    c %= width
                if 0 <= r < labels.shape[0] and 0 <= c < width and int(labels[r, c]) == sea_cell:
                    dock_row, dock_column = r, c
                    break
            dock_x = int(_world_columns(canvas, np.array([dock_column], dtype=np.int64))[0])
            positions[land_cell] = (dock_row, dock_x)
            rows_out.append(
                f"{plan.cells[land_cell].key};{plan.cells[sea_cell].key};{x};{height - 1 - row};x"
            )
    for number, key in enumerate(sorted(foreign.free), start=1):
        row = vanilla[key]
        rows_out.append(f"{key};{plan.cells[chosen.port[-number]].key};{row.x};{row.y};x")
    return rows_out, positions


def _instance(key: str, row: int, x: int, height: int) -> str:
    z = height - 1 - row
    return (
        f"\t\t{{\n\t\t\tid={key}\n\t\t\tposition={{ {x}.500000 0.000000 {z}.500000 }}\n"
        f"\t\t\trotation={ROTATION}\n\t\t\tscale={SCALE}\n\t\t}}\n"
    )


def _locator_instances(
    plan: Plan,
    world: NewWorld,
    canvas: Canvas,
    ports: dict[int, tuple[int, int]],
    closed: frozenset[int],
) -> dict[str, list[str]]:
    height = canvas.shape[0]
    columns = _world_columns(canvas, world.interior[:, 1])
    rows = world.interior[:, 0]
    wanted = {
        "generated_locators_city.txt": {CellClass.LAND},
        "generated_map_object_locators_unit_stack.txt": {
            CellClass.LAND,
            CellClass.SEA,
            CellClass.LAKE,
        },
        "generated_map_object_locators_combat.txt": {
            CellClass.LAND,
            CellClass.SEA,
            CellClass.LAKE,
        },
        "generated_locators_vfx.txt": set(CellClass),
    }
    out: dict[str, list[str]] = {name: [] for name in wanted}
    out["generated_map_object_locators_dock.txt"] = []
    seen: set[str] = set()
    for index, cell in enumerate(plan.cells):
        if cell.key in seen or (plan.oceans is not None and cell.key in plan.oceans.retained):
            continue
        seen.add(cell.key)
        for name, kinds in wanted.items():
            if cell.kind in kinds and not (index in closed and name in NO_UNITS):
                out[name].append(_instance(cell.key, int(rows[index]), int(columns[index]), height))
        if index in ports:
            row, x = ports[index]
            out["generated_map_object_locators_dock.txt"].append(
                _instance(cell.key, row, x, height)
            )
    if plan.oceans is not None:
        out["generated_locators_vfx.txt"].extend(
            _instance(cell.key, *plan.oceans.anchors[cell.key], height)
            for cell in plan.oceans.extra
        )
    return out


def _trimmed_instances(game_map: Eu5Map, canvas: Canvas) -> dict[str, str]:
    """Locator instances at the interior point of each trimmed ocean zone's remainder."""
    height, width = canvas.shape
    rolled = canvas.rolled(game_map.labels)
    full = np.zeros(canvas.shape, dtype=bool)
    full[:, canvas.col0 : canvas.col0 + canvas.mask.shape[1]] = canvas.mask
    out: dict[str, str] = {}
    zones = np.flatnonzero(canvas.trimmed).astype(np.int32)
    boxes = remainder_boxes(rolled, full, zones, len(game_map.keys))
    for zone in zones.tolist():
        window = boxes[zone]
        top, left = window[0].start, window[1].start
        mine = (rolled[window] == zone) & ~full[window]
        distance = distance_from(np.pad(~mine, 1, constant_values=True), 4096)[1:-1, 1:-1]
        best = int(np.argmax(np.where(mine, distance, -1)))
        row, column = divmod(best, mine.shape[1])
        x = (left + column - canvas.roll) % width
        key = game_map.keys[zone]
        out[key] = _instance(key, top + row, x, height)
    return out


def _present_keys(plan: Plan) -> dict[str, frozenset[str]]:
    """The map keys of each kind that the generated world defines."""
    return {
        "location": frozenset(cell.key for cell in plan.cells),
        "province": frozenset(cell.province for cell in plan.cells),
        "area": frozenset(cell.area for cell in plan.cells),
        "region": frozenset(cell.region for cell in plan.cells),
        "subcontinent": frozenset(cell.subcontinent for cell in plan.cells),
    }


def _additions(plan: Plan) -> HierarchyAdditions:
    additions = HierarchyAdditions()
    provinces: dict[str, list[str]] = {}
    area_of_province: dict[str, str] = {}
    for cell in emitted_cells(plan):
        provinces.setdefault(cell.province, []).append(cell.key)
        area_of_province[cell.province] = cell.area
    new_area_provinces = {p for members in plan.new_areas.values() for p in members}
    for province, keys in provinces.items():
        if province not in new_area_provinces:
            additions.provinces.setdefault(area_of_province[province], []).append((province, keys))
    for area, members in plan.new_areas.items():
        region = plan.area_region[area]
        additions.areas.setdefault(region, []).append(
            (area, [(province, provinces[province]) for province in members])
        )
    return additions


def _yaml(language: str, entries: dict[str, str]) -> bytes:
    lines = [f"l_{language}:"] + [f' {key}: "{value}"' for key, value in entries.items()]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def _localization(  # noqa: PLR0913 - the world names come from three typed sources.
    game_dir: Path,
    plan: Plan,
    extra: Mapping[str, Entry],
    renamed: Mapping[str, Name],
    languages: tuple[str, ...],
    *,
    include_provinces: bool = False,
) -> dict[str, bytes]:
    """The world's names and texts, written in each language (``wording``, ``translations``)."""
    names: dict[str, Entry] = {cell.key: cell.name for cell in emitted_cells(plan)}
    names.update(extra)
    names.update(plan.province_names)
    fresh = {area for area in plan.new_areas if area.startswith("rnw_")}
    names.update({area: plan.display_overrides[area] for area in sorted(fresh)})
    overrides = {key: value for key, value in plan.display_overrides.items() if key not in fresh}
    names.update({key: renamed[key] for key in names if key in renamed})
    overrides.update({key: renamed[key] for key in overrides if key in renamed})
    files: dict[str, bytes] = {}
    for language in languages:
        base = f"main_menu/localization/{language}"
        files[f"{base}/rnw_new_world_l_{language}.yml"] = _yaml(language, localize(names, language))
        written = {key: render(name, language) for key, name in overrides.items()}
        try:
            files.update(
                map_name_files(game_dir, language, written, include_provinces=include_provinces)
            )
        except LocalizationError as error:
            raise NewWorldExportError(str(error)) from error
    return files


def binding_problems(
    game_dir: Path, shaders: dict[str, str], mod_includes: dict[str, str]
) -> list[str]:
    """Why patched shaders would not bind as the cover expects (C137, C138); empty when fine.

    Includes use the mod's own files and patched game includes before installed originals.
    """

    def read(name: str) -> str | None:
        if name in mod_includes:
            return mod_includes[name]
        for folder in INCLUDE_DIRS:
            if (relative := f"{folder}/{name}") in shaders:
                return shaders[relative]
        for folder in INCLUDE_DIRS:
            if (game_dir / folder / name).is_file():
                return _read(game_dir, f"{folder}/{name}")
        return None

    broken = [
        f"{edit.path}: {problem}"
        for edit in SHADERS
        if (
            problem := binding_problem(
                edit,
                shader_samplers(shaders[edit.path], read),
                shader_indexes(shaders[edit.path], read),
            )
        )
    ]
    broken.extend(
        f"{name}: a sampler names no engine slot"
        for name, text in mod_includes.items()
        if not samplers_bound(text)
    )
    return broken


def _cover_outputs(  # noqa: PLR0913, PLR0917 - the cover reads the map, its labels and the canvas.
    game_dir: Path,
    game_map: Eu5Map,
    world: NewWorld,
    final: NDArray[np.int32],
    neighbours: frozenset[int],
    within: NDArray[np.bool_] | None = None,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """The files that cover the New World at country selection, and what the cover holds.

    The cover takes the generated locations, the ocean wastelands among their vanilla
    ``neighbours`` and every pixel ``within`` the canvas as it was before its island groups were
    placed: the groups stay or have moved inside it and, as vanilla locations, would otherwise
    stand open in the covered ocean (``rnw.eu5_lobby``). The game's own files are changed where
    it decides what to draw and offer; a game whose files read otherwise, or whose shaders would
    not bind the cover's samplers, stops the export instead of leaving the cover half made.
    """
    patched = {
        edit.path: cover_shader(edit, _read(game_dir, edit.source_path or edit.path))
        for edit in SHADERS
    }
    gui_patched = {path: patch_gui(path, _read(game_dir, path)) for path in GUI_FILES}
    land = land_colour(_read(game_dir, GRAPHICS_DEFINES))
    shaders = {path: text for path, text in patched.items() if text is not None}
    broken = sorted(path for path in patched if path not in shaders)
    guis = {path: text for path, text in gui_patched.items() if text is not None}
    broken.extend(path for path in gui_patched if path not in guis)
    if land is None:
        broken.append(GRAPHICS_DEFINES)
    if broken or land is None:
        message = (
            "The game's files are not laid out as the cover of the New World expects "
            f"({', '.join(broken)}); check the build before making a world"
        )
        raise NewWorldExportError(message)
    lists = read_class_lists(game_dir / DEFAULT_MAP)
    wastes = set(lists["sea_zones"]) & set(lists["impassable_mountains"])
    seas = sorted(i for i in neighbours if game_map.keys[i] in wastes)
    vanilla = len(game_map.keys)
    covered = np.ones(vanilla + len(world.classes), dtype=bool)
    covered[:vanilla] = False
    covered[seas] = True
    grid = cover_grid(final, covered, within)
    rows, columns = final.shape
    mod_includes = {
        COVER_INCLUDE: cover_include((rows, columns), grid, unknown_colour(land)),
        DRAWINGS_INCLUDE: drawings_include(),
        **{name: sampler_include(name) for name in OWN_SAMPLERS},
    }
    broken = binding_problems(game_dir, shaders, mod_includes)
    if broken:
        message = (
            "The cover of the New World would not bind in this build of the game "
            f"({'; '.join(broken)}); check the build before making a world"
        )
        raise NewWorldExportError(message)
    outputs = {
        **{f"{SHADER_DIR}/{name}": text.encode("utf-8") for name, text in mod_includes.items()},
        **{_mod_path(path): _encode(game_dir, path, text) for path, text in guis.items()},
        SCRIPTED_GUI_FILE: scripted_gui_text().encode("utf-8-sig"),
    }
    for edit in SHADERS:
        outputs[_mod_path(edit.path)] = _encode(
            game_dir, edit.source_path or edit.path, shaders[edit.path]
        )
    if sorted(outputs) != sorted(cover_files()):
        message = "the cover's files differ from the list the library copies"
        raise NewWorldExportError(message)
    stats: dict[str, object] = {
        "grid": [int(grid.shape[1]), int(grid.shape[0])],
        "grid_cells": int(np.count_nonzero(grid)),
        "ocean_wastelands": [game_map.keys[i] for i in seas],
        "shaders": [_mod_path(path) for path in shaders],
    }
    return outputs, stats


def _final_labels(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> NDArray[np.int32]:
    final = game_map.labels.copy()
    canvas.put(final, world.labels + len(game_map.keys))
    return final


def _held(game_map: Eu5Map, canvas: Canvas) -> NDArray[np.bool_]:
    """Vanilla locations and zones of the island groups.

    A group stands in new water, so its old neighbours (replaced or trimmed waters) are no
    contacts to keep; the sea reachability check covers its new ones.
    """
    held = np.zeros(len(game_map.keys), dtype=bool)
    for group in canvas.groups:
        held[list(group.locations)] = True
        held[list(group.zones)] = True
    return held


def _check_overseas_contacts(
    game_map: Eu5Map,
    plan: Plan,
    impassable: set[int] | frozenset[int],
    contacts: set[tuple[int, int]],
    *,
    oceans: frozenset[str] = OCEANS,
) -> None:
    """Reject passable map contacts that destroy American overseas eligibility."""
    passable = [kind is not CellClass.WASTELAND for kind in game_map.classes]
    passable.extend(
        cell.kind is not CellClass.WASTELAND and index not in impassable
        for index, cell in enumerate(plan.cells)
    )
    memberships = list(game_map.continents) + [cell.continent for cell in plan.cells]
    bad = [
        (first, second)
        for first, second in contacts
        if passable[first]
        and passable[second]
        and (
            (memberships[first] == NEW_WORLD and memberships[second] not in oceans | {NEW_WORLD})
            or (memberships[second] == NEW_WORLD and memberships[first] not in oceans | {NEW_WORLD})
        )
    ]
    if bad:
        first, second = min(bad)
        names = list(game_map.keys) + [cell.key for cell in plan.cells]
        message = (
            f"{len(bad)} passable American/Old World contacts, "
            f"e.g. {names[first]} / {names[second]}"
        )
        raise NewWorldExportError(message)


def _check_written_contacts(
    map_dir: Path,
    written: NDArray[np.int32],
    game_map: Eu5Map,
    canvas: Canvas,
    *,
    oceans: frozenset[str] = OCEANS,
) -> None:
    """Reject passable American/Old World contacts in the files as the game reads them.

    ``_check_overseas_contacts`` judges the labels held in memory; this reads the written
    ``locations.png`` (as labels of its named colours), ``definitions.txt`` and ``default.map``,
    so recoloured ocean remainders and every other difference between the held map and the
    file count too (W4). The waters the canvas took over keep the ocean status that
    ``open_map`` gave them.
    """
    named = read_named_colors(map_dir / "named_locations/00_default.txt")
    keys = [key for key, _ in named]
    hierarchy = {location.key: location for location in read_locations(map_dir / "definitions.txt")}
    impassable = set(read_class_lists(map_dir / "default.map")["impassable_mountains"])
    opened: set[str] = set()
    if canvas.opened is not None:
        opened.update(game_map.keys[index] for index in np.flatnonzero(canvas.opened).tolist())
    bad = passable_contacts(
        written, overseas_flags(keys, hierarchy, impassable, opened, oceans=oceans)
    )
    if bad:
        first, second = bad[0]
        message = (
            f"{len(bad)} passable American/Old World contacts in the written map, "
            f"e.g. {keys[first]} / {keys[second]}"
        )
        raise NewWorldExportError(message)


def _inland_sea_cells(
    world: NewWorld,
    settings: NewWorldSettings,
    *,
    by_continent: Mapping[str, int] | None = None,
    plan: Plan | None = None,
) -> frozenset[int]:
    """Allow substantial, physically enclosed seas; a small basin should have been a lake."""
    basins = inland_seas(world)
    for basin in basins:
        minimum = (
            by_continent[plan.cells[basin[0]].continent]
            if by_continent is not None and plan is not None
            else inland_sea_min_area(settings)
        )
        area = sum(int(world.pixels[cell]) for cell in basin)
        if area < minimum:
            message = f"An inland sea has only {area} pixels (minimum {minimum}); expected a lake"
            raise NewWorldExportError(message)
    return frozenset(cell for basin in basins for cell in basin)


def _replacement_water_links(
    game_map: Eu5Map,
    lost: list[tuple[int, int]],
    neighbours: Mapping[int, list[int]],
    generated_continents: frozenset[str],
    closed: Collection[int],
) -> set[tuple[int, int]]:
    """A cut contact at a selected coast can go through its new navigable waters."""
    offset = len(game_map.keys)
    linked: set[tuple[int, int]] = set()
    for low, high in lost:
        first, target = (high, low) if game_map.classes[high] is CellClass.LAND else (low, high)
        coast = game_map.classes[first] is CellClass.LAND
        if not coast and not any(
            game_map.continents[node] in generated_continents for node in (first, target)
        ):
            continue
        if any(
            game_map.classes[node] is not CellClass.SEA or bool(game_map.ambiguous[node])
            for node in ((target,) if coast else (first, target))
        ):
            continue
        pending = deque(neighbours.get(first, ()))
        seen = {first}
        while pending:
            cell = pending.popleft()
            if cell == target:
                linked.add((min(first, target), max(first, target)))
                break
            if cell >= offset and cell - offset not in closed and cell not in seen:
                seen.add(cell)
                pending.extend(neighbours.get(cell, ()))
    return linked


def _sea_neighbours(
    game_map: Eu5Map,
    world: NewWorld,
    contacts: Collection[tuple[int, int]],
    shores: Collection[int] = (),
) -> tuple[NDArray[np.bool_], dict[int, list[int]]]:
    sea = np.fromiter(
        (kind is CellClass.SEA for kinds in (game_map.classes, world.classes) for kind in kinds),
        dtype=bool,
    )
    neighbours: dict[int, list[int]] = {}
    for first, second in contacts:
        if sea[first] and sea[second]:
            neighbours.setdefault(first, []).append(second)
            neighbours.setdefault(second, []).append(first)
        elif first in shores and sea[second]:
            neighbours.setdefault(first, []).append(second)
        elif second in shores and sea[first]:
            neighbours.setdefault(second, []).append(first)
    return sea, neighbours


def _check_world(  # noqa: C901, PLR0913, PLR0915, PLR0917 - check the raster and hierarchy together.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    final: NDArray[np.int32],
    plan: Plan,
    impassable: set[int] | frozenset[int],
    settings: NewWorldSettings,
    *,
    generated_continents: frozenset[str] = AMERICAN_GENERATION,
    inland_sizes: Mapping[str, int] | None = None,
) -> tuple[dict[str, int], frozenset[int]]:
    """Connectivity, sea reachability and Old World contact preservation.

    ``final`` is the label raster of the finished map (``_final_labels``). Also returns the
    vanilla locations that touch a generated one, which the selection cover reads.
    """
    count = len(world.classes)
    unported = unported_cells(world)
    if unported:
        message = f"{len(unported)} land cells reach no port, e.g. cell {unported[0]}"
        raise NewWorldExportError(message)
    parts = label_components(world.labels, wrap_x=world.wrap_x)
    owner = np.full(int(parts.max()) + 1, -1, dtype=np.int64)
    owner[parts.ravel()] = world.labels.ravel()
    per_cell = np.bincount(owner[owner >= 0], minlength=count)
    if np.any(per_cell != 1):
        message = f"{int(np.count_nonzero(per_cell != 1))} generated cells are split or empty"
        raise NewWorldExportError(message)
    vanilla_count = len(game_map.keys)
    before = set(unpack_pairs(adjacency_pairs(game_map.labels, wrap_x=True)))
    after = set(unpack_pairs(adjacency_pairs(final, wrap_x=True)))
    continents = game_map.continents
    oceans = (
        frozenset(key for key in continents if key.endswith("_ocean_continent"))
        if world.wrap_x
        else OCEANS
    )
    if NEW_WORLD in generated_continents:
        _check_overseas_contacts(game_map, plan, impassable, after, oceans=oceans)
    old_world = np.array(
        [name not in oceans and name not in generated_continents for name in continents], dtype=bool
    )
    held = _held(game_map, canvas)
    lost = [
        pair
        for pair in before - after
        if not canvas.removed[pair[0]]
        and not canvas.removed[pair[1]]
        and not held[pair[0]]
        and not held[pair[1]]
        and (old_world[pair[0]] or old_world[pair[1]])
    ]
    shores = (
        {cell for pair in lost for cell in pair if game_map.classes[cell] is CellClass.LAND}
        if world.wrap_x
        else set[int]()
    )
    sea, neighbours = _sea_neighbours(game_map, world, after, shores)
    linked = (
        _replacement_water_links(game_map, lost, neighbours, generated_continents, impassable)
        if world.wrap_x
        else set[tuple[int, int]]()
    )
    impassable_ocean_edges = {
        pair
        for pair in lost
        if world.wrap_x
        and all(sea[i] for i in pair)
        and any(game_map.ambiguous[i] and continents[i] in oceans for i in pair)
    }
    missing = sorted(set(lost) - linked - impassable_ocean_edges)
    if missing:
        message = f"{len(missing)} Old World contacts were lost, e.g. {missing[:3]}"
        raise NewWorldExportError(message)
    start = [i for i in range(vanilla_count) if sea[i] and old_world[i] and not canvas.removed[i]]
    seen = set(start)
    queue = deque(start)
    while queue:
        for other in neighbours.get(queue.popleft(), []):
            if other not in seen:
                seen.add(other)
                queue.append(other)
    inland = _inland_sea_cells(world, settings, by_continent=inland_sizes, plan=plan)
    orphan = [
        i
        for i in range(vanilla_count, vanilla_count + count)
        if sea[i] and i not in seen and i - vanilla_count not in inland
    ]
    if orphan:
        message = f"{len(orphan)} generated sea zones cannot reach the Old World seas"
        raise NewWorldExportError(message)
    present = np.bincount(final.ravel(), minlength=vanilla_count + count)
    for zone in np.flatnonzero(canvas.trimmed).tolist():
        if not present[zone]:
            message = f"Trimmed ocean zone vanished: {game_map.keys[zone]}"
            raise NewWorldExportError(message)
    stats = {
        "contacts_before": len(before),
        "contacts_after": len(after),
        "old_world_contacts_lost": 0,
        "generated_cells_split": 0,
        "generated_sea_zones_unreachable": 0,
        "generated_inland_sea_zones": len(inland),
        "land_cells_without_port_access": 0,
    }
    if world.wrap_x:
        stats["selected_coastal_water_links_replaced"] = len(linked)
        stats["impassable_ocean_borders_changed"] = len(impassable_ocean_edges)
        if "africa" in generated_continents:
            stats["africa_asia_land_contacts"] = sum(
                low < vanilla_count <= high
                and continents[low] == "asia"
                and game_map.classes[low] is CellClass.LAND
                and plan.cells[high - vanilla_count].continent == "africa"
                and world.classes[high - vanilla_count] is CellClass.LAND
                for low, high in after
            )
    return stats, frozenset(low for low, high in after if low < vanilla_count <= high)


def _removed_provinces(hierarchy: dict[str, Location], removed: set[str]) -> dict[str, list[str]]:
    """Locations of every province that loses all of them, in definition order."""
    provinces: dict[str, list[str]] = {}
    for key, location in hierarchy.items():
        provinces.setdefault(location.province, []).append(key)
    return {
        province: keys
        for province, keys in provinces.items()
        if all(key in removed for key in keys)
    }


def _removed_areas(
    hierarchy: dict[str, Location], removed: set[str], dropped: list[str]
) -> dict[str, list[str]]:
    """Wholly replaced areas that the generated geography no longer uses."""
    wanted = set(dropped)
    areas: dict[str, list[str]] = {}
    for key, location in hierarchy.items():
        if location.area in wanted:
            areas.setdefault(location.area, []).append(key)
    return {area: members for area, members in areas.items() if all(k in removed for k in members)}


def missing_area_keys(
    hierarchy: Mapping[str, Location], removed: set[str], plan: Plan
) -> list[str]:
    """Original areas with no remaining or generated member on the composed map."""
    removed_areas = {hierarchy[key].area for key in removed if key in hierarchy}
    retained_areas = {place.area for key, place in hierarchy.items() if key not in removed}
    used_areas = {cell.area for cell in emitted_cells(plan)}
    return sorted(removed_areas - retained_areas - used_areas)


def composed_bindings(  # noqa: PLR0913 - finished coast and original geographic keys.
    game_map: Eu5Map,
    canvas: Canvas,
    water: Water,
    plan: Plan,
    hierarchy: dict[str, Location],
    *,
    geometry: VanillaGeometry,
    removed: set[str],
    vanilla_ports: Mapping[str, VanillaPort],
) -> tuple[tuple[list[str], dict[int, tuple[int, int]]], GeographicRemap]:
    """Find the final port rows and replacements for all removed geographic identities."""
    world = water.coast.world
    ports = _ports(plan, world, canvas, water.coast.foreign, vanilla_ports)
    remap = build_remap(
        [
            (game_map.keys[i], game_map.classes[i], int(geometry.rows[i]), int(geometry.columns[i]))
            for i in np.flatnonzero(canvas.removed).tolist()
            if game_map.keys[i] in removed
        ],
        plan,
        world.centroids,
        _removed_provinces(hierarchy, removed),
        areas=_removed_areas(hierarchy, removed, plan.dropped_areas),
        access=RemapAccess(
            port_keys=frozenset(vanilla_ports),
            port_cells=frozenset(ports[1]),
            navigable_keys=frozenset(
                key
                for i, key in enumerate(game_map.keys)
                if game_map.classes[i] is CellClass.SEA and not game_map.ambiguous[i]
            ),
            closed_seas=water.zones,
        ),
        regions=RemapRegions(
            dict(zip(game_map.keys, game_map.continents, strict=True)), canvas.shape[1]
        ),
    )
    return ports, remap


def check_composed_map(
    game_map: Eu5Map,
    canvas: Canvas,
    plan: Plan,
    water: Water,
    geography: Mapping[str, NewWorldSettings],
) -> dict[str, int]:
    """Run the geographic export checks against one finished multi-continent map."""
    world = water.coast.world
    counts, _ = _check_world(
        game_map,
        canvas,
        world,
        _final_labels(game_map, canvas, world),
        plan,
        water.zones,
        next(iter(geography.values())),
        generated_continents=frozenset(geography),
        inland_sizes={name: inland_sea_min_area(settings) for name, settings in geography.items()},
    )
    return counts


def _setup_paths(game_dir: Path, *, regional: bool) -> dict[str, Path]:
    if regional:
        return {
            path.name: path
            for path in mounted_text_files(game_dir, (SETUP_DIR,)).values()
            if path.parent.name == "1337"
        }
    return {path.name: path for path in sorted((game_dir / SETUP_DIR).glob("*.txt"))}


def _setup_texts(sources: Mapping[str, Path]) -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8-sig") for name, path in sources.items()}


def _discovery_outputs(game_dir: Path, remap: GeographicRemap | None) -> dict[str, bytes]:
    if remap is None:
        return {}
    files: dict[str, bytes] = {}
    for relative, source in mounted_text_files(game_dir, (SETUP_TEMPLATES,)).items():
        original = source.read_text(encoding="utf-8-sig")
        changed = remap_discoveries(original, remap)
        if changed != original:
            files[relative] = _encode(game_dir, source.relative_to(game_dir).as_posix(), changed)
    return files


def _read(game_dir: Path, relative: str) -> str:
    return (game_dir / relative).read_text(encoding="utf-8-sig")


def _has_bom(game_dir: Path, relative: str) -> bool:
    return (game_dir / relative).read_bytes().startswith(b"\xef\xbb\xbf")


def _encode(game_dir: Path, relative: str, text: str) -> bytes:
    return text.encode("utf-8-sig" if _has_bom(game_dir, relative) else "utf-8")


def _mod_path(relative: str) -> str:
    return relative.removeprefix("game/")


def _ai_assignment_records(
    game_dir: Path, natives: FinalStartPlan, world: NewWorld, plan: Plan
) -> tuple[AiDecision, ...]:
    try:
        return decide_ai_personalities(
            _ai_country_contexts(natives, world, plan), vanilla_profiles(game_dir)
        )
    except AiPersonalityError as error:
        raise NewWorldExportError(str(error)) from error


@dataclass(frozen=True, slots=True)
class _AiDiplomacy:
    allies: dict[str, set[str]]
    rivals: dict[str, set[str]]
    threatened_by: dict[str, set[str]]
    prey_targets: dict[str, set[str]]
    subjects: dict[str, set[str]]
    overlords: dict[str, str]
    confederated: dict[str, set[str]]


def _ai_active_countries(natives: FinalStartPlan) -> dict[str, Country]:
    active = {
        country.tag: country
        for country in natives.countries
        if country.kind == STATE or country.landed
    }
    if len(active) != sum(country.kind == STATE or country.landed for country in natives.countries):
        message = "Generated AI-country tags are not unique"
        raise AiPersonalityError(message)
    owner: dict[str, str] = {}
    for tag, country in active.items():
        for key in country.members:
            previous = owner.setdefault(key, tag)
            if previous != tag:
                message = f"AI-personality ownership overlaps at {key}: {previous} and {tag}"
                raise AiPersonalityError(message)
    return active


def _ai_geography(
    world: NewWorld, plan: Plan, owner: Mapping[str, str], tags: set[str]
) -> tuple[dict[str, set[str]], set[str]]:
    neighbors: dict[str, set[str]] = {tag: set() for tag in tags}
    coastal: set[str] = set()
    for first, second in world.edges:
        if not (0 <= first < len(plan.cells) and 0 <= second < len(plan.cells)):
            message = f"AI-personality context has an invalid generated edge: {(first, second)}"
            raise AiPersonalityError(message)
        first_cell, second_cell = plan.cells[first], plan.cells[second]
        kinds = first_cell.kind, second_cell.kind
        if kinds in {(CellClass.LAND, CellClass.SEA), (CellClass.SEA, CellClass.LAND)}:
            land_cell = first_cell if kinds[0] is CellClass.LAND else second_cell
            tag = owner.get(land_cell.key)
            if tag is not None:
                coastal.add(tag)
        elif kinds == (CellClass.LAND, CellClass.LAND):
            first_tag, second_tag = owner.get(first_cell.key), owner.get(second_cell.key)
            if first_tag and second_tag and first_tag != second_tag:
                neighbors[first_tag].add(second_tag)
                neighbors[second_tag].add(first_tag)
    return neighbors, coastal


def _ai_mutual_links(pairs: Sequence[tuple[str, str]], tags: set[str]) -> dict[str, set[str]]:
    links: dict[str, set[str]] = {tag: set() for tag in tags}
    for first, second in pairs:
        if first in tags and second in tags:
            links[first].add(second)
            links[second].add(first)
    return links


def _ai_opinion_links(
    opinions: Sequence[tuple[str, str, str]], tags: set[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    threatened_by: dict[str, set[str]] = {tag: set() for tag in tags}
    prey_targets: dict[str, set[str]] = {tag: set() for tag in tags}
    for first, second, kind in opinions:
        if first in tags and second in tags:
            if kind == FEAR:
                threatened_by[first].add(second)
            elif kind == PREY:
                prey_targets[first].add(second)
    return threatened_by, prey_targets


def _ai_diplomacy(natives: FinalStartPlan, tags: set[str]) -> _AiDiplomacy:
    alliances = _ai_mutual_links(natives.alliances, tags)
    confederated_members: dict[str, set[str]] = {tag: set() for tag in tags}
    for group in natives.confederations:
        members = set(group) & tags
        for tag in members:
            confederated_members[tag].update(members - {tag})
            alliances[tag].update(members - {tag})
    rivals = _ai_mutual_links(natives.rivals, tags)
    threatened_by, prey_targets = _ai_opinion_links(natives.opinions, tags)
    if natives.history is not None:
        actors = {actor.key: actor for actor in natives.history.state.actors}
        for memory in natives.history.state.memories:
            first = natives.history_tags.get(memory.first, "")
            second = natives.history_tags.get(memory.second, "")
            if first in tags and second in tags and memory.at(natives.history.state.year):
                if memory.factor is Factor.FEAR:
                    threatened_by[first].add(second)
                elif memory.factor is Factor.COMPETITION and (
                    actors[memory.first].society.military is Military.OFFENSIVE
                ):
                    prey_targets[first].add(second)
    subjects: dict[str, set[str]] = {tag: set() for tag in tags}
    overlords: dict[str, str] = {}
    for lord, subject in natives.vassals:
        if lord in tags and subject in tags:
            subjects[lord].add(subject)
            overlords[subject] = lord
    return _AiDiplomacy(
        allies=alliances,
        rivals=rivals,
        threatened_by=threatened_by,
        prey_targets=prey_targets,
        subjects=subjects,
        overlords=overlords,
        confederated=confederated_members,
    )


def _ai_country_contexts(
    natives: FinalStartPlan, world: NewWorld, plan: Plan
) -> tuple[CountryContext, ...]:
    """Summarize generated power, geography and diplomacy for the contextual classifier."""
    active = _ai_active_countries(natives)
    owner = {key: tag for tag, country in active.items() for key in country.members}
    tags = set(active)
    neighbors, coastal = _ai_geography(world, plan, owner, tags)
    diplomacy = _ai_diplomacy(natives, tags)
    market_locations = set(natives.markets)
    guarantors: dict[str, set[str]] = {tag: set() for tag in tags}
    guarantees: dict[str, set[str]] = {tag: set() for tag in tags}
    for giver, receiver in natives.protections:
        if giver in tags and receiver in tags:
            guarantors[receiver].add(giver)
            guarantees[giver].add(receiver)
    result: list[CountryContext] = []
    for tag, country in active.items():
        population = sum(natives.population.get(key, 0) for key in country.members)
        level = max(0, country.level or 0)
        power = max(1, population) * (2 + level)
        result.append(
            CountryContext(
                tag=tag,
                landed=True,
                great=country.great,
                archetype=country.archetype,
                level=level,
                population=population,
                power=power,
                coastal=tag in coastal,
                market=bool(market_locations.intersection(country.members)),
                neighbors=tuple(sorted(neighbors[tag])),
                allies=tuple(sorted(diplomacy.allies[tag])),
                rivals=tuple(sorted(diplomacy.rivals[tag])),
                threatened_by=tuple(sorted(diplomacy.threatened_by[tag])),
                prey_targets=tuple(sorted(diplomacy.prey_targets[tag])),
                subjects=tuple(sorted(diplomacy.subjects[tag])),
                overlord=diplomacy.overlords.get(tag, ""),
                confederated=bool(diplomacy.confederated[tag]),
                archetypes=country.archetypes,
                guarantors=tuple(sorted(guarantors[tag])),
                guarantees=tuple(sorted(guarantees[tag])),
                historical=natives.history is not None,
            )
        )
    return tuple(result)


def _insert_setup_additions(
    name: str,
    text: str,
    additions: Mapping[str, tuple[str, ...]],
    ai_assignments: Assignments,
) -> str:
    for path, addition in zip(SETUP_INSERTS.get(name, ()), additions.get(name, ()), strict=True):
        if addition:
            text = insert_into_block(text, path, addition)
    if name == PERSONALITIES:
        try:
            verify_ai_personalities(text, ai_assignments)
        except AiPersonalityError as error:
            raise NewWorldExportError(str(error)) from error
    return text


def map_identity_files(
    game_dir: Path, plan: Plan, water: Water, removed: set[str]
) -> dict[str, bytes]:
    """Write the named colours, hierarchy and location classes from one plan."""
    outputs: dict[str, bytes] = {}
    outputs[_mod_path(NAMED_COLORS)] = _encode(
        game_dir,
        NAMED_COLORS,
        rewrite_named_colors(
            _read(game_dir, NAMED_COLORS), removed, [(c.key, c.color) for c in emitted_cells(plan)]
        ),
    )
    outputs[_mod_path(DEFINITIONS)] = _encode(
        game_dir,
        DEFINITIONS,
        rewrite_definitions(_read(game_dir, DEFINITIONS), removed, _additions(plan)),
    )
    lists = {
        "sea_zones": [c.key for c in emitted_cells(plan) if c.kind is CellClass.SEA],
        "lakes": [c.key for c in emitted_cells(plan) if c.kind is CellClass.LAKE],
        "impassable_mountains": [
            cell.key
            for index, cell in enumerate(plan.cells)
            if (cell.kind is CellClass.WASTELAND or index in water.zones)
            and (plan.oceans is None or cell.key not in plan.oceans.retained)
        ],
    }
    lists["impassable_mountains"] = list(dict.fromkeys(lists["impassable_mountains"]))
    if plan.oceans is not None:
        lists["impassable_mountains"].extend(
            cell.key for cell in plan.oceans.extra if cell.key in plan.oceans.closed_extra
        )
    outputs[_mod_path(DEFAULT_MAP)] = _encode(
        game_dir, DEFAULT_MAP, rewrite_class_lists(_read(game_dir, DEFAULT_MAP), removed, lists)
    )
    return outputs


@dataclass(frozen=True, slots=True)
class ComposedStart:
    """The regional histories and the decisions about retained territory."""

    histories: tuple[FinalStartPlan, ...]
    remap: GeographicRemap
    morocco: MoroccoStart | None = None
    emirate: Country | None = None
    calibrations: tuple[VanillaNatives, ...] = ()
    real_america: VanillaWorld | None = None


def _rewrite_setup(  # noqa: PLR0913 - the start uses the final map and its bound identities.
    start: ComposedStart | None,
    texts: dict[str, str],
    natives: FinalStartPlan,
    *,
    game_map: Eu5Map,
    geometry: VanillaGeometry,
    plan: Plan,
    removed: set[str],
    gone: set[str],
) -> SetupResult:
    written = pop_lines(natives.pops)
    if start is None:
        return prune_setup(texts, gone, {c.key: written.get(c.key, []) for c in plan.cells})
    texts[COUNTRIES_FILE] = remap_discoveries(texts[COUNTRIES_FILE], start.remap)
    kept = start.real_america
    restored = frozenset(() if kept is None else (game_map.keys[i] for i in kept.keep))
    pops = {cell.key: written.get(cell.key, []) for cell in emitted_cells(plan)}
    if kept is not None:
        pops.update({game_map.keys[i]: written.get(game_map.keys[i], []) for i in kept.keep})
    original = {
        key: (int(row), int(column))
        for key, row, column in zip(game_map.keys, geometry.rows, geometry.columns, strict=True)
    }
    final = set(game_map.keys).difference(removed) | {cell.key for cell in emitted_cells(plan)}
    replacements = retained_capitals(
        texts[COUNTRIES_FILE],
        gone,
        original,
        game_map.labels.shape[1],
        preferred={"MAM": "damascus"},
    )
    if start.morocco is not None:
        holdings = set(start.morocco.africa)
        if holdings - written.keys() or any(
            holdings.intersection(country.members) for country in natives.countries
        ):
            message = "Morocco's reserved holdings must have populations and no generated owner"
            raise NewWorldExportError(message)
        return apply_morocco_start(
            start.morocco,
            texts,
            gone,
            pops,
            location_replacements=start.remap.locations,
            replacement_capitals=replacements,
            final_locations=final,
            emirate=start.emirate,
            surviving_places=restored,
        )
    return prune_regional_setup(
        texts,
        gone,
        pops,
        location_replacements=start.remap.locations,
        replacement_capitals=replacements,
        final_locations=final,
        surviving_places=restored,
    )


def _history_outputs(
    natives: FinalStartPlan, loc_keys: KeySpace, plan: Plan, composed: ComposedStart | None
) -> eu5_history_text.WrittenHistory | None:
    locations = tuple(cell.key for cell in plan.cells)
    if composed is not None:
        history = eu5_history_text.build_combined(
            composed.histories, loc_keys, tuple(dict.fromkeys(locations))
        )
        verify_combined_text(composed.histories, history)
        return history
    if natives.history is None:
        return None
    history = eu5_history_text.build(natives, loc_keys, locations)
    verify_history_text(natives, history)
    return history


def _gone_setup_places(
    hierarchy: Mapping[str, Location], plan: Plan, removed: set[str], retained: Collection[str]
) -> set[str]:
    kept_provinces = {hierarchy[key].province for key in hierarchy if key not in removed}
    removed_provinces = {hierarchy[key].province for key in removed if key in hierarchy}
    retired = {name for key in retained for name in (key, hierarchy[key].province)}
    return removed | (removed_provinces - kept_provinces) | set(plan.dropped_areas) | retired


def _text_outputs(  # noqa: PLR0913, PLR0915 - every rewritten file needs the shared plan.
    game_dir: Path,
    *,
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    plan: Plan,
    hierarchy: dict[str, Location],
    removed: set[str],
    geometry: VanillaGeometry,
    biomes: CellBiomes,
    natives: FinalStartPlan,
    loc_keys: KeySpace,
    development: Development,
    ports: tuple[list[str], dict[int, tuple[int, int]]],
    coast: Coast,
    water: Water,
    new_world_keys: set[str],
    resources_seed: int,
    area_replacements: dict[str, str],
    composed: ComposedStart | None = None,
) -> tuple[dict[str, bytes], dict[str, object]]:
    bodies = _template_bodies(_read(game_dir, TEMPLATES))
    donors = _donor_map(
        game_map,
        canvas=canvas,
        world=world,
        rows=geometry.rows,
        columns=geometry.columns,
        bodies=bodies,
    )
    port_rows, port_pixels = ports
    places = choose(
        Cells(
            land=[cell.kind is CellClass.LAND for cell in plan.cells],
            material=biomes.raw_material,
            topography=biomes.topography,
            coastal=_coastal(world).tolist(),
        ),
        resources_seed,
    )
    used = [spec for spec in SPECS if spec in places.values()]
    towns = plan_towns(game_dir, natives.ranks, development.initial, natives.population)
    instances = _locator_instances(plan, world, canvas, port_pixels, water.zones)
    trimmed = _trimmed_instances(game_map, canvas)
    relocated = removed | set(trimmed)
    outputs = map_identity_files(game_dir, plan, water, removed)
    outputs[_mod_path(TEMPLATES)] = _encode(
        game_dir,
        TEMPLATES,
        rewrite_templates(
            _read(game_dir, TEMPLATES),
            removed,
            _template_lines(
                plan,
                donors,
                bodies,
                biomes,
                development.harbours,
                places,
                water,
                regional_pops=None if composed is None else natives.pops,
            ),
        ),
    )
    moved = shifts(game_map, canvas)
    width = int(game_map.labels.shape[1])
    outputs[_mod_path(PORTS)] = _encode(
        game_dir,
        PORTS,
        rewrite_csv(
            _read(game_dir, PORTS), removed, (0, 1), port_rows, moved, ((0, (2, 3)),), width
        ),
    )
    outputs[_mod_path(ADJACENCIES)] = _encode(
        game_dir,
        ADJACENCIES,
        rewrite_csv(
            _read(game_dir, ADJACENCIES),
            removed,
            (0, 1, 3),
            _crossing_rows(plan, canvas, water),
            moved,
            ((0, (4, 5)), (1, (6, 7))),
            width,
        ),
    )
    for relative in LOCATOR_FILES:
        name = relative.rsplit("/", 1)[1]
        text = _read(game_dir, relative)
        fresh = list(instances.get(name, []))
        if any(kind in name for kind in TRIMMED_LOCATORS):
            # A trimmed ocean zone moves its locator only where vanilla has one.
            held = set(LOCATOR_ID.findall(text))
            fresh += [instance for key, instance in trimmed.items() if key in held]
        outputs[_mod_path(relative)] = _encode(
            game_dir, relative, rewrite_locators(text, relocated, fresh, moved, width)
        )
    override = _read(game_dir, LOCATOR_OVERRIDE)
    if (rewritten := rewrite_override_locators(override, removed)) != override:
        outputs[_mod_path(LOCATOR_OVERRIDE)] = _encode(game_dir, LOCATOR_OVERRIDE, rewritten)
    society = None if composed is None else composed.real_america
    society_plan = plan if society is None else society.plan
    society_world = world if society is None else society.world
    gone = _gone_setup_places(
        hierarchy,
        plan,
        removed,
        () if society is None else [game_map.keys[i] for i in society.keep],
    )
    history_text = _history_outputs(natives, loc_keys, society_plan, composed)
    if history_text is not None:
        outputs.update(history_text.files)
    setup_paths = _setup_paths(game_dir, regional=composed is not None)
    installed_setup = _setup_texts(setup_paths)
    setup_texts = {
        name: remap_text(text, area_replacements)[0] for name, text in installed_setup.items()
    }
    outputs.update(_discovery_outputs(game_dir, None if composed is None else composed.remap))
    setup = _rewrite_setup(
        composed,
        setup_texts,
        natives,
        game_map=game_map,
        geometry=geometry,
        plan=plan,
        removed=removed,
        gone=gone,
    )
    ai_decisions = _ai_assignment_records(game_dir, natives, society_world, society_plan)
    ai_records = ai_assignments(ai_decisions)
    additions: dict[str, tuple[str, ...]] = {
        COUNTRIES_FILE: (country_records(natives.countries),),
        PERSONALITIES: (ai_personality_lines(ai_records),),
        BUILDINGS_FILE: (city_lines(towns.ranks), building_lines(development.villages)),
        "03_markets.txt": (market_lines(natives.markets),),
        "09_roads.txt": (road_lines(natives.roads),),
        "12_diplomacy.txt": (
            vassal_lines(natives.vassals) + eu5_history_text.guarantee_lines(natives.protections),
            alliance_lines(natives.alliances),
        ),
        "15_international_organizations.txt": (
            confederation_lines(natives.confederation_date, natives.confederations),
        ),
        DEVELOPMENT_FILE: (development_lines(development.terms),),
        "18_opinions.txt": (opinion_lines(natives.opinions),),
        "20_rivals.txt": (rival_lines(natives.rivals),),
    }
    for name, original_text in setup.texts.items():
        setup_text = original_text
        if name == DEVELOPMENT_FILE:
            setup_text = drop_block_entries(setup_text, ("development",), new_world_keys)
        setup_text = _insert_setup_additions(name, setup_text, additions, ai_records)
        if name == "12_diplomacy.txt" and history_text is not None:
            verify_diplomacy(natives, setup_text, installed_setup[name], gone | setup.removed_ids)
        if setup_text != installed_setup[name]:
            source = setup_paths[name].relative_to(game_dir).as_posix()
            outputs[_mod_path(f"{SETUP_DIR}/{name}")] = _encode(game_dir, source, setup_text)
    outputs.update(country_definition_outputs(game_dir, setup.removed_ids))
    outputs.update(towns.files())
    retired = retired_base_modifiers(bodies, removed)
    if retired:
        outputs[_mod_path(BASE_VALUES)] = _encode(
            game_dir, BASE_VALUES, drop_block_entries(_read(game_dir, BASE_VALUES), (), retired)
        )
    countries = natives.countries
    if composed is not None and composed.emirate is not None:
        countries += (composed.emirate,)
    outputs[DEFINITION_FILE] = country_definitions(countries)
    languages = official_languages(game_dir)
    if used:
        outputs[OUTPUT_PLACES] = modifiers_file(used, payloads(game_dir))
    outputs.update(
        _localization(
            game_dir,
            plan,
            {
                **country_names(countries),
                **{key: Text(key) for key in place_texts(used)},
                **(history_text.texts if history_text is not None else {}),
            },
            natives.names,
            languages,
            include_provinces=composed is not None,
        )
    )
    stats: dict[str, object] = {
        "starting_towns": {
            "adjusted_locations": towns.adjusted_locations,
            "derived_templates": len(towns.definitions),
        },
        "ports": len(port_rows),
        "oceans": {} if plan.oceans is None else plan.oceans.stats,
        "vanilla_ports_relinked": sorted(coast.foreign.free),
        "sea_cells_merged": coast.merged,
        "strait_crossings": len(water.crossings),
        "water": {
            "bodies": [len(cells) for cells in water.waters.bodies],
            "passages": dict(sorted(Counter(p.kind.value for p in water.waters.passages).items())),
            "shapes": dict(
                sorted(
                    Counter(
                        Shape(water.waters.shape[cell]).name.lower() for cell in water.waters.sea()
                    ).items()
                )
            ),
            "lanes": len(water.lanes),
            "lanes_without_current": water.uncurrented,
            "lanes_added_to_link": water.linked,
            "local_route_pairs": water.local_pairs,
            "lanes_added_for_local_routes": water.shortcuts,
            "lanes_added_for_course_ends": water.completed,
            "closed_seas": water.sealed,
            "impassable_zones": len(water.zones),
            "topography": dict(
                sorted(Counter(str(kind) for kind in water.waters.topography if kind).items())
            ),
        },
        "setup_records_deleted": {k: v for k, v in setup.deleted.items() if v},
        "setup_identifiers_removed": len(setup.removed_ids),
        "ai_personalities": dict(sorted(Counter(profile for _, profile in ai_records).items())),
        "ai_personality_decisions": [
            {
                "tag": decision.tag,
                "profile": decision.profile,
                "reason": decision.reason,
                "context": {
                    "population": decision.context.population,
                    "technology_level": decision.context.level,
                    "power_proxy": decision.context.power,
                    "great_empire": decision.context.great,
                    "archetype": decision.context.archetype,
                    "neighbors": list(decision.context.neighbors),
                    "allies": list(decision.context.allies),
                    "rivals": list(decision.context.rivals),
                    "threatened_by": list(decision.context.threatened_by),
                    "prey_targets": list(decision.context.prey_targets),
                    "subjects": list(decision.context.subjects),
                    "overlord": decision.context.overlord,
                    "confederated": decision.context.confederated,
                    "market": decision.context.market,
                    "coastal": decision.context.coastal,
                },
            }
            for decision in ai_decisions
        ],
        "base_modifiers_retired": sorted(retired),
        "languages": list(languages),
        "untranslated_languages": untranslated(languages),
        "exceptional_places": {
            spec.modifier: plan.cells[index].key for index, spec in sorted(places.items())
        },
    }
    return outputs, stats


def _sea_zones(plan: Plan, world: NewWorld) -> dict[str, set[str]]:
    """The sea zones each generated land cell touches, by key (a coast; empty inland)."""
    touching: dict[str, set[str]] = {}
    for first, second in world.edges:
        pair = (first, second)
        kinds = [plan.cells[index].kind for index in pair]
        if (CellClass.SEA in kinds) and (CellClass.LAND in kinds):
            land, sea = (first, second) if kinds[0] is CellClass.LAND else (second, first)
            touching.setdefault(plan.cells[land].key, set()).add(plan.cells[sea].key)
    return touching


def _ocean_sides(plan: Plan, world: NewWorld) -> dict[str, str]:
    """The open ocean each generated sea zone opens onto, nearest over sea contacts.

    The coastal waters of the Americas belong to the American continent in the hierarchy, so the
    ocean of a coast is found by water: a multi-source search from the sea zones of the open
    oceans (``content.OCEANS``), the first ocean in their order winning a tie.
    """
    near: dict[int, list[int]] = {}
    for first, second in world.edges:
        if plan.cells[first].kind is CellClass.SEA and plan.cells[second].kind is CellClass.SEA:
            near.setdefault(first, []).append(second)
            near.setdefault(second, []).append(first)
    side: dict[int, str] = {}
    queue: deque[int] = deque()
    for ocean in OPEN_OCEANS:
        for index, cell in enumerate(plan.cells):
            if cell.kind is CellClass.SEA and cell.continent == ocean and index not in side:
                side[index] = ocean
                queue.append(index)
    while queue:
        here = queue.popleft()
        for there in sorted(near.get(here, ())):
            if there not in side:
                side[there] = side[here]
                queue.append(there)
    return {plan.cells[index].key: ocean for index, ocean in side.items()}


def _story_outputs(  # noqa: PLR0913 - the stories read the world, the peoples and the installation.
    game_dir: Path,
    *,
    plan: Plan,
    world: NewWorld,
    natives: FinalStartPlan,
    river_pixels: NDArray[np.int64],
    topography: Sequence[str],
    vanilla: VanillaNatives,
    loc_keys: KeySpace,
    seed: int,
    composed: ComposedStart | None = None,
) -> Written:
    """The stories and formables of this world, as files and statistics (content plan, N3, N4)."""
    keys = [cell.key for cell in plan.cells]
    land = [index for index, cell in enumerate(plan.cells) if cell.kind is CellClass.LAND]
    inhabited = cohort_places(natives.pops)
    dominant = {place.key: place.religion for place in inhabited}
    traits = culture_traits(game_dir)
    cultures = {place.key: place.culture for place in inhabited}
    states = country_starts(natives)
    facts = facts_of(
        keys=[keys[index] for index in land],
        population=natives.population,
        ranks={key: rank for key, (rank, _) in natives.ranks.items()},
        religion=dominant,
        river={keys[index]: int(river_pixels[index]) for index in land},
        states=states,
        holy=list(natives.holy_sites.values()),
        links=[
            (keys[first], keys[second])
            for first, second in world.edges
            if plan.cells[first].kind is CellClass.LAND
            and plan.cells[second].kind is CellClass.LAND
        ],
        relief={keys[index]: topography[index] for index in land},
        culture=cultures,
        seas=_sea_zones(plan, world),
        groups={name: traits[name][1] for name in set(cultures.values()) if name in traits},
        subjects=natives.vassals,
        history=historical_content_facts(natives)
        if composed is None
        else composed_history_facts(composed.histories),
        regions={keys[index]: plan.cells[index].region for index in land},
        continents={keys[index]: plan.cells[index].continent for index in land},
        oceans=_ocean_sides(plan, world),
    )
    content = plan_content(facts, seed)
    reserved = vanilla.reserved_tags | {country.tag for country in natives.countries}
    tags = new_tags(
        len(content.formations), reserved, derive_seed(seed, "content", "tags"), loc_keys
    )
    taken = vanilla.colors | {
        colour for country in natives.countries for colour in (country.color, country.color2)
    }
    regions = {
        region: natives.names.get(region) or plan.display_overrides.get(region, region)
        for region in sorted({cell.region for cell in plan.cells if cell.kind is CellClass.LAND})
    }
    fallen = facts.history.fallen if facts.history is not None else ()
    return build_stories(
        game_dir,
        content,
        names=natives.names,
        tags=tags,
        languages=official_languages(game_dir),
        seed=seed,
        taken=taken,
        regions=regions,
        memories=eu5_memories.select(
            natives, content, fallen, seed, regional=() if composed is None else composed.histories
        ),
        keys=loc_keys,
    )


def _rasters(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, plan: Plan, river_codes: NDArray[np.uint8]
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    colors = np.array([cell.color for cell in plan.cells], dtype=np.int64)
    palette = np.stack([(colors >> 16) & 0xFF, (colors >> 8) & 0xFF, colors & 0xFF], axis=1)
    rgb = game_map.rgb
    if plan.oceans is not None:
        plan.oceans.paint(rgb, canvas)
    canvas.put(rgb, palette.astype(np.uint8)[world.labels])
    water = np.array(
        [cell.kind in {CellClass.SEA, CellClass.LAKE} for cell in plan.cells], dtype=bool
    )
    rivers = game_map.rivers
    canvas.put(
        rivers,
        np.where(
            river_codes < RIVER_CLASSES,
            river_codes,
            np.where(water[world.labels], RIVER_WATER, RIVER_LAND),
        ).astype(np.uint8),
    )
    return rgb, rivers


def _connected_painted_cells(labels: NDArray[np.int32], keys: Sequence[str], plan: Plan) -> int:
    """Every generated colour and redistributed ocean remainder is one connected location."""
    generated = {cell.key for cell in emitted_cells(plan)}
    remainders = plan.oceans.sources if plan.oceans is not None else {}
    components = component_counts(labels, wrap_x=True, label_count=len(keys))
    broken = [
        key
        for number, key in enumerate(keys)
        if components[number] != 1 and (key in generated or key in remainders)
    ]
    if broken:
        message = f"{len(broken)} painted locations are split or empty: {', '.join(broken[:5])}"
        raise NewWorldExportError(message)
    return len(generated)


def check_composed_rasters(  # noqa: PLR0913 - the output map, its setup and its river raster.
    game_dir: Path,
    game_map: Eu5Map,
    canvas: Canvas,
    water: Water,
    plan: Plan,
    *,
    river_codes: NDArray[np.uint8],
) -> dict[str, int]:
    """Check the actual output colours and rivers in memory, with the ocean runs painted."""
    world = water.coast.world
    removed = {game_map.keys[i] for i in np.flatnonzero(canvas.removed).tolist()}
    if plan.oceans is not None:
        removed -= plan.oceans.retained
    _check_identity_budget(game_map, removed, plan)
    candidate = replace(game_map, rgb=game_map.rgb.copy(), rivers=game_map.rivers.copy())
    rgb, rivers = _rasters(candidate, canvas, world, plan, river_codes)
    outside = differing_pixels(rgb, game_map.rgb) & ~canvas.mask
    if plan.oceans is not None:
        plan.oceans.paint(outside, canvas, clear=True)
    if outside.any() or np.any((rivers != game_map.rivers) & ~canvas.mask):
        message = "Generated rasters changed locations or rivers outside their planned footprints"
        raise NewWorldExportError(message)
    emitted = emitted_cells(plan)
    retained = [
        (key, color)
        for key, color in zip(game_map.keys, game_map.colors.tolist(), strict=True)
        if key not in removed
    ]
    tables = map_identity_files(game_dir, plan, water, removed)
    named = parse_named_colors(tables[_mod_path(NAMED_COLORS)].decode("utf-8-sig"))
    defined = parse_locations(tables[_mod_path(DEFINITIONS)].decode("utf-8-sig"))
    keys = [*(key for key, _ in retained), *(cell.key for cell in emitted)]
    expected = dict(retained) | {cell.key: cell.color for cell in emitted}
    original_hierarchy = parse_locations(_read(game_dir, DEFINITIONS))
    expected_definitions = ({c.key for c in original_hierarchy} - removed) | {
        cell.key for cell in emitted
    }
    wrong_colors = sorted(dict(named).items() ^ expected.items())
    missing_keys = sorted({c.key for c in defined} ^ expected_definitions)
    if wrong_colors or missing_keys or len(named) != len(keys):
        message = (
            f"Combined map tables disagree ({len(named)} names for {len(keys)} keys, "
            f"{len(wrong_colors)} color bindings, {len(missing_keys)} hierarchy keys). "
            f"Examples: {wrong_colors[:3]} {missing_keys[:5]}"
        )
        raise NewWorldExportError(message)
    colors = np.array([expected[key] for key in keys], dtype=np.int64)
    labels = labels_from_rgb(rgb, colors)
    return {
        "location_colors": len(colors),
        "connected_new_location_colors": _connected_painted_cells(labels, keys, plan),
    }


def _basin_rain(
    shape: tuple[int, int], left: int, canvas: Canvas, climate: ClimateGrid
) -> NDArray[np.int64]:
    """Sample rain at this basin grid's centres, including an unaligned divide."""
    height, width_crop = shape
    world_width = canvas.shape[1]
    coarse_rows = -(-height // RIVER_STEP)
    coarse_columns = -(-width_crop // RIVER_STEP)
    centre_rows = np.arange(coarse_rows, dtype=np.int64) * RIVER_STEP + RIVER_STEP // 2
    centre_columns = left + np.minimum(
        np.arange(coarse_columns, dtype=np.int64) * RIVER_STEP + RIVER_STEP // 2,
        width_crop - 1,
    )
    grid_rows = np.clip(centre_rows // CLIMATE_STEP, 0, climate.rain.shape[0] - 1)
    grid_columns = np.clip(
        _world_columns(canvas, centre_columns) % world_width // CLIMATE_STEP,
        0,
        climate.rain.shape[1] - 1,
    )
    return climate.rain[grid_rows[:, np.newaxis], grid_columns[np.newaxis, :]]


def _river_basins(  # noqa: PLR0913 - the land, relief, canvas, climate, seed and lakes.
    land: NDArray[np.bool_],
    elevation: NDArray[np.int32],
    canvas: Canvas,
    climate: ClimateGrid,
    seed: int,
    *,
    lakes: NDArray[np.bool_] | None = None,
) -> Rivers:
    """Plan separate sea-draining basins; the seam contributes no synthetic water.

    Lakes are water that rivers flow into and out of within their basin.
    """
    seam = (canvas.roll - canvas.col0) % canvas.shape[1]
    spans = watershed_spans(land.shape[1], seam)
    rivers = Rivers(
        np.empty(land.shape, dtype=np.int8),
        np.empty(land.shape, dtype=np.int64),
        dict.fromkeys(("streams", "mouths", "joins", "dropped", "pixels"), 0),
    )
    for column in (seam - 1, seam):
        if 0 <= column < land.shape[1]:
            rivers.role[:, column] = NONE
            rivers.flow[:, column] = 0
    thresholds: list[int] = []
    for left, right in spans:
        domain = land[:, left:right]
        target = Rivers(rivers.role[:, left:right], rivers.flow[:, left:right], {})
        try:
            found = generate_rivers(
                domain,
                elevation[:, left:right],
                _basin_rain(domain.shape, left, canvas, climate),
                seed=derive_seed(seed, f"river_basin_{left}"),
                output=target,
                lakes=None if lakes is None else lakes[:, left:right],
            )
        except RiverGenerationError as exc:
            raise NewWorldExportError(str(exc)) from exc
        problems = outlet_problems(found.role, ~domain)
        if any(problems.values()):
            message = f"river basin {left}:{right} has invalid outlets: {problems}"
            raise NewWorldExportError(message)
        thresholds.append(found.stats["threshold"])
        for key, value in found.stats.items():
            if key != "threshold":
                rivers.stats[key] = rivers.stats.get(key, 0) + value
    rivers.stats.update(
        watershed_domains=len(spans),
        outlets_checked=rivers.stats["mouths"],
        threshold_min=min(thresholds, default=0),
        threshold_max=max(thresholds, default=0),
    )
    return rivers


def _rivers(
    world: NewWorld, canvas: Canvas, climate: ClimateGrid, seed: int, algorithm: int = 0
) -> tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]]:
    """River codes and valleys from the same independently planned watershed domains.

    From ``epoch.RIVERS_FIRST`` they are the rivers the cells were grown along: drawn again along
    the world's own drainage plan (``NewWorld.drainage``) with the rain of its land, lakes and
    relief (``rnw.watersheds``), not from the climate of the whole map.
    """
    land_kind = np.array(
        [kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes] + [False]
    )
    land = land_kind[world.labels]
    lake_kind = np.array([kind is CellClass.LAKE for kind in world.classes] + [False])
    elevation = world.elevation
    lakes = lake_kind[world.labels]
    if algorithm >= epoch.RIVERS_FIRST:
        plan = world.drainage
        seam = (canvas.roll - canvas.col0) % canvas.shape[1]
        if plan is None or plan.seam != seam:
            message = "The world carries no drainage plan split at this map's seam"
            raise NewWorldExportError(message)
        try:
            rivers = domain_rivers(
                land,
                plan,
                lakes=lakes,
                rain=domain_climate(land, lakes, elevation).rain,
                seed=seed,
            )
        except RiverGenerationError as exc:
            raise NewWorldExportError(str(exc)) from exc
    else:
        rivers = _river_basins(land, elevation, canvas, climate, seed, lakes=lakes)
    del lakes
    return _river_rasters(
        rivers, land, ~land, elevation, seam=(canvas.roll - canvas.col0) % canvas.shape[1]
    )


def _river_rasters(
    rivers: Rivers,
    land: NDArray[np.bool_],
    water: NDArray[np.bool_],
    elevation: NDArray[np.int32],
    *,
    seam: int,
) -> tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]]:
    classes = flow_classes(rivers, RIVER_WIDTH_SHARES)
    problems = network_problems(rivers.role, water)
    if any(problems.values()):
        message = f"generated rivers break the raster rules: {problems}"
        raise NewWorldExportError(message)
    try:
        codes, raster_stats = encode_rivers(
            rivers,
            classes,
            RIVER_WIDTH_CODES,
            seam=seam,
        )
    except RiverRasterError as exc:
        raise NewWorldExportError(str(exc)) from exc
    carved = carve_valleys(
        elevation,
        classes,
        depths=RIVER_VALLEY_DEPTHS,
        radius_px=RIVER_VALLEY_PX,
        floor=COAST_HEIGHT,
    )
    land_pixels = int(np.count_nonzero(land))
    stats: dict[str, object] = dict(rivers.stats)
    stats["pixels_per_1000_land"] = int(rivers.stats["pixels"]) * 1000 // max(1, land_pixels)
    stats["problems"] = problems
    stats["raster"] = raster_stats
    stats["width_pixels"] = {
        str(code): int(np.count_nonzero(codes == code)) for code in RIVER_WIDTH_CODES
    }
    return codes, carved, stats


def composed_rivers(
    shape: tuple[int, int], regions: Sequence[WorldRegion], seed: int
) -> tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]]:
    """Draw each existing watershed once and place it in the assembled world."""
    codes = np.full(shape, RIVER_LAND, dtype=np.uint8)
    carved = np.zeros(shape, dtype=np.int32)
    stats: dict[str, object] = {}
    for region in regions:
        domain, world = region.domain, region.world
        name = domain.continent.key
        local_seed = seed if name == NEW_WORLD else derive_seed(seed, "continent", name)
        seam = domain.watershed_seam
        plan = world.drainage
        if plan is None or plan.seam != seam:
            message = f"The drainage plan of {name} has the wrong watershed boundary"
            raise NewWorldExportError(message)
        land = np.array(
            [kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes] + [False]
        )[world.labels]
        lakes = np.array([kind is CellClass.LAKE for kind in world.classes] + [False])[world.labels]
        rain = domain_climate(
            land, lakes, world.elevation, row0=domain.first_row, outside_land=domain.contact_land
        ).rain
        try:
            rivers = domain_rivers(
                land,
                plan,
                lakes=lakes,
                rain=rain,
                seed=local_seed,
                outside_land=domain.contact_land,
            )
        except RiverGenerationError as error:
            message = f"{name}: {error}"
            raise NewWorldExportError(message) from error
        water = ~land
        if domain.contact_land is not None:
            water &= ~domain.contact_land
        local, valleys, details = _river_rasters(
            rivers,
            land,
            water,
            world.elevation,
            seam=world.labels.shape[1] + 1 if seam is None else seam,
        )
        stats[name] = details
        for crop, original in domain.spans():
            mask = domain.mask[:, crop]
            np.copyto(codes[domain.rows, original], local[:, crop], where=mask)
            np.copyto(carved[domain.rows, original], valleys[:, crop], where=mask)
    return codes, carved, stats


def referenced_words(path: str, text: str) -> set[str]:
    """Identifier-like words of a script text, without comments.

    Named colours count only their keys: a colour such as ``dabaca`` can spell a
    location key (vanilla has one) without referring to it. Location templates
    and population records name locations only in their respective record keys.
    """
    if path in {_mod_path(TEMPLATES), _mod_path(f"{SETUP_DIR}/06_pops.txt")}:
        root = parse(text)
        holder = root if path == _mod_path(TEMPLATES) else root.block("locations")
        if holder is None:
            message = f"{path} has no location records"
            raise NewWorldExportError(message)
        return {entry.key for entry in holder.entries if entry.key is not None}
    text = re.sub(r"#[^\n]*", "", text)
    if path == _mod_path(NAMED_COLORS):
        text = "\n".join(line.split("=", 1)[0] for line in text.splitlines())
    return set(WORD.findall(text))


def _add_reveal(
    texts: dict[str, bytes], *, enabled: bool, continents: Collection[str] = AMERICAN_GENERATION
) -> dict[str, object]:
    """With the world setting on, write the reveal of the chosen continents and check against the
    written ``definitions.txt``; the statistics to keep, none when the setting is off."""
    if not enabled:
        return {}
    definitions = texts[_mod_path(DEFINITIONS)].decode("utf-8-sig")
    try:
        texts.update(reveal_files(definitions, continents=continents))
        return {"reveal": verify_reveal(texts, definitions, continents=continents)}
    except RevealError as error:
        raise NewWorldExportError(str(error)) from error


def _verify_texts(outputs: dict[str, bytes], plan: Plan, removed: set[str]) -> dict[str, object]:
    """Cross-file consistency of the written text files."""
    definitions = outputs[_mod_path(DEFINITIONS)].decode("utf-8-sig")
    keys = {location.key for location in parse_locations(definitions)}
    generated = {cell.key for cell in plan.cells}
    if not generated <= keys or keys & removed:
        message = "definitions.txt does not contain exactly the kept and generated locations"
        raise NewWorldExportError(message)
    templates = parse(outputs[_mod_path(TEMPLATES)].decode("utf-8-sig"))
    template_keys = {entry.key for entry in templates.entries if entry.key}
    if template_keys != keys:
        message = f"Template keys differ from definitions: {len(template_keys ^ keys)}"
        raise NewWorldExportError(message)
    leftovers: dict[str, int] = {}
    for path, data in outputs.items():
        if not path.endswith((".txt", ".map", ".csv")) or "localization" in path:
            continue
        found = referenced_words(path, data.decode("utf-8-sig")) & removed
        if found:
            leftovers[path] = len(found)
    if leftovers:
        message = f"Removed locations are still referenced: {leftovers}"
        raise NewWorldExportError(message)
    return {"definition_locations": len(keys), "template_locations": len(template_keys)}


def verify_map_texts(
    outputs: dict[str, bytes], plan: Plan, canvas: Canvas, water: Water, removed: set[str]
) -> dict[str, object]:
    """Check the written locations, ports, straits and sea routes against the same plan."""
    checks = _verify_texts(outputs, plan, removed)
    coast = water.coast
    world = coast.world
    try:
        checks.update(
            verify_seas(
                (
                    outputs[_mod_path(PORTS)].decode("utf-8-sig"),
                    outputs[_mod_path(TEMPLATES)].decode("utf-8-sig"),
                    outputs[_mod_path(DEFAULT_MAP)].decode("utf-8-sig"),
                ),
                plan,
                world,
                coast,
                water,
            )
        )
        checks.update(
            verify_locators(
                {
                    name: outputs[_mod_path(f"{MAP_OBJECTS}/{name}")].decode("utf-8-sig")
                    for name in (*NO_UNITS, VFX_LOCATORS)
                },
                plan,
                water,
                all_locations=frozenset(
                    location.key
                    for location in parse_locations(
                        outputs[_mod_path(DEFINITIONS)].decode("utf-8-sig")
                    )
                ),
            )
        )
        checks.update(
            verify_crossings(
                outputs[_mod_path(ADJACENCIES)].decode("utf-8-sig"),
                plan,
                world,
                canvas,
                water.crossings,
            )
        )
    except SeaError as error:
        raise NewWorldExportError(str(error)) from error
    if water.external_crossings:
        rows = outputs[_mod_path(ADJACENCIES)].decode("utf-8-sig").splitlines()
        for crossing in water.external_crossings:
            if rows.count(crossing.row(canvas.shape[0])) != 1:
                message = "A crossing between Africa and Europe was not written exactly once"
                raise NewWorldExportError(message)
        checks["africa_europe_straits"] = len(water.external_crossings)
    return checks


def vanilla_localization_keys(game_dir: Path) -> set[str]:
    """Every localization key of the installation, over all languages and DLC folders."""
    keys: set[str] = set()
    for root in LOC_ROOTS:
        for path in sorted((game_dir / root).rglob("*.yml")):
            if "localization" in path.parts:
                checkpoint()
                keys |= set(LOC_KEY.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    return keys


def static_hashes() -> set[int]:
    """The hashes of the mod's static localization keys, which no generated key may take.

    Raises if two static keys share a hash with each other.
    """
    found = key_hashes(game_texts.sources())
    if len(found) != len(game_texts.sources()):
        message = "Two static localization keys share the engine's key hash"
        raise NewWorldExportError(message)
    return found


def verify_localization(
    outputs: dict[str, bytes], vanilla_hashes: set[int], *, game_dir: Path | None = None
) -> dict[str, object]:
    """Generated localization keys share no hash with each other or with vanilla keys.

    A localization file overriding an installed path must retain exactly its original keys.
    Every other file defines new keys; a ``replace/`` directory grants no exception.
    """
    keys: set[str] = set()
    for path, data in outputs.items():
        if not path.endswith(".yml") or "/localization/" not in path:
            continue
        written = Counter(LOC_KEY.findall(data.decode("utf-8-sig")))
        original = None if game_dir is None else game_dir / "game" / path
        if original is not None and original.is_file():
            expected = Counter(LOC_KEY.findall(original.read_text(encoding="utf-8-sig")))
            if written != expected:
                message = f"Localization override {path} changes the installed keys"
                raise NewWorldExportError(message)
        else:
            keys.update(written)
    hashes = [key_hash(key) for key in sorted(keys)]
    clashes = len(hashes) - len(set(hashes)) + len(set(hashes) & vanilla_hashes)
    if clashes:
        message = f"{clashes} generated localization keys collide in the engine's key hash"
        raise NewWorldExportError(message)
    return {"localization_keys": len(keys)}


def country_definition_outputs(game_dir: Path, removed: set[str]) -> dict[str, bytes]:
    """Vanilla tag definition files without the tags whose 1337 setup entry was removed.

    Vanilla defines a tag only together with its setup entry, and the engine creates every
    defined tag as a country, so a definition left behind is a country without a
    government (C86). Every other byte of a rewritten file stays.
    """
    outputs: dict[str, bytes] = {}
    for path in sorted((game_dir / COUNTRY_DIR).glob("*.txt")):
        relative = f"{COUNTRY_DIR}/{path.name}"
        text = path.read_text(encoding="utf-8-sig")
        tags = {entry.key for entry in parse(text).entries if entry.key} & removed
        if tags:
            outputs[_mod_path(relative)] = _encode(
                game_dir, relative, drop_block_entries(text, (), tags)
            )
    return outputs


def _setup_tags(text: str) -> set[str]:
    holder = parse(text).block("countries", "countries")
    return {entry.key for entry in holder.entries if entry.key} if holder is not None else set()


def _defined_tags(game_dir: Path, outputs: dict[str, bytes]) -> set[str]:
    """Tags of the vanilla country files, each file replaced by its output if written."""
    prefix = f"{_mod_path(COUNTRY_DIR)}/"
    names = {path.name for path in (game_dir / COUNTRY_DIR).glob("*.txt")}
    names |= {path.removeprefix(prefix) for path in outputs if path.startswith(prefix)}
    tags: set[str] = set()
    for name in sorted(names):
        relative = f"{COUNTRY_DIR}/{name}"
        data = outputs.get(_mod_path(relative))
        text = data.decode("utf-8-sig") if data is not None else _read(game_dir, relative)
        tags |= {entry.key for entry in parse(text).entries if entry.key}
    return tags


def verify_country_tags(game_dir: Path, outputs: dict[str, bytes]) -> dict[str, object]:
    """Defined tags and 1337 setup entries agree exactly as they do in vanilla."""
    relative = f"{SETUP_DIR}/{COUNTRIES_FILE}"
    data = outputs.get(_mod_path(relative))
    vanilla_setup = _setup_tags(_read(game_dir, relative))
    setup = _setup_tags(data.decode("utf-8-sig")) if data is not None else vanilla_setup
    vanilla_defined, tags = _defined_tags(game_dir, {}), _defined_tags(game_dir, outputs)
    unused, undefined = tags - setup, setup - tags
    if unused != vanilla_defined - vanilla_setup or undefined != vanilla_setup - vanilla_defined:
        message = (
            f"Tag definitions and 1337 setup disagree: {len(unused)} defined without a setup "
            f"entry (vanilla {len(vanilla_defined - vanilla_setup)}), {len(undefined)} set up "
            "without a definition"
        )
        raise NewWorldExportError(message)
    return {"country_tags_defined": len(tags), "country_tags_without_setup": sorted(unused)}


def _verify_natives(natives: FinalStartPlan, plan: Plan) -> dict[str, object]:
    """Countries own or hold generated land only, once each, under fresh tags."""
    land = {cell.key for cell in plan.cells if cell.kind is CellClass.LAND}
    tags = [country.tag for country in natives.countries]
    if len(set(tags)) != len(tags) or not all(re.fullmatch(r"[A-Z]{3}", tag) for tag in tags):
        message = "Native tags are not unique three-letter tags"
        raise NewWorldExportError(message)
    seen: set[str] = set()
    for country in natives.countries:
        members = set(country.members)
        if not members <= land or country.capital not in members or members & seen:
            message = f"Native country {country.tag} has invalid or shared locations"
            raise NewWorldExportError(message)
        seen |= members
    states = {country.tag for country in natives.countries if country.kind == "state"}
    vassals = [vassal for _, vassal in natives.vassals]
    if len(set(vassals)) != len(vassals) or not all(
        lord in states and vassal in states and lord != vassal for lord, vassal in natives.vassals
    ):
        message = "Native vassals must be distinct states with one overlord each"
        raise NewWorldExportError(message)
    if not set(natives.pops) <= land or not set(natives.ranks) <= land:
        message = "Native pops or ranks lie outside generated land"
        raise NewWorldExportError(message)
    return {"native_countries": len(tags), "native_locations_held": len(seen)}


def _technology_problems(
    records: dict[str, tuple[list[str], list[str]]],
    natives: FinalStartPlan,
    vanilla: VanillaNatives,
) -> list[str]:
    problems: list[str] = []
    allowed = set(vanilla.state_levels)
    empire_level: set[int] = {vanilla.empire.level} if vanilla.empire is not None else set()
    levels: dict[str, int] = {}
    for country in natives.countries:
        includes, written = records.get(country.tag, ([], []))
        if includes != ([country.include] if country.include else []):
            problems.append(f"{country.tag} does not write its template {country.include}")
        elif country.kind != "state":
            if written:
                problems.append(f"Tribe {country.tag} writes a technology level")
        elif (
            len(written) != 1
            or not written[0].isdigit()
            or int(written[0]) not in allowed | (empire_level if country.great else set())
        ):
            problems.append(f"{country.tag} writes {written} as its technology level")
        else:
            level, template = int(written[0]), vanilla.levels.get(country.include, 0)
            levels[country.tag] = level
            if country.include and not template <= level <= template + 1:
                problems.append(
                    f"{country.tag} has level {level}, its template {country.include} {template}"
                )
    ordinary = sorted(
        (natives.complexity[c.capital], natives.population[c.capital], c.tag)
        for c in natives.countries
        if c.kind == "state" and not c.great and c.tag in levels
    )
    problems += [
        f"{after[2]} has a lower level than {before[2]}, which is less complex"
        for before, after in pairwise(ordinary)
        if natives.history is None and levels[after[2]] < levels[before[2]]
    ]
    if natives.history is not None:
        problems += [
            f"{country.tag} writes a technology level different from its lineage"
            for country in natives.countries
            if country.kind == "state" and levels.get(country.tag) != country.level
        ]
    template_of = {c.tag: vanilla.levels.get(c.include, 0) for c in natives.countries}
    problems += [
        f"{lord} leads {vassal} without the level or the template to lead"
        for lord, vassal in natives.vassals
        if levels.get(lord, -1) < vanilla.overlord_level
        or template_of.get(lord, -1) < vanilla.overlord_level
    ]
    return problems


def verify_technology(
    outputs: dict[str, bytes],
    natives: FinalStartPlan,
    vanilla: VanillaNatives,
    *,
    composed: ComposedStart | None = None,
) -> dict[str, object]:
    """Every state writes a level of the vanilla set and a fitting template, a tribe none.

    Levels never fall along the rising complexity of the capitals (great empires apart), a
    template is at most the level and at most one below it, and a vassal lord has the level
    and the template to lead (C99).
    """
    text = outputs[_mod_path(f"{SETUP_DIR}/{COUNTRIES_FILE}")].decode("utf-8-sig")
    records = written_records(text, {country.tag for country in natives.countries})
    starts = (
        ((natives, vanilla),)
        if composed is None
        else tuple(zip(composed.histories, composed.calibrations, strict=True))
    )
    problems = [
        problem
        for start, calibration in starts
        for problem in _technology_problems(records, start, calibration)
    ]
    if problems:
        extra = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        message = f"Technology of the native states: {problems[0]}{extra}"
        raise NewWorldExportError(message)
    return {
        "technology_levels_written": sum(1 for c in natives.countries if c.kind == "state"),
        "technology_vassal_lords": len({lord for lord, _ in natives.vassals}),
    }


def _pairs_of(text: str, block: str) -> list[tuple[str, str]]:
    """The ``a = b`` pairs of a block of a setup file, in file order."""
    holder = parse(text).block(block)
    return [
        (entry.key, entry.value)
        for entry in (holder.entries if holder is not None else [])
        if entry.key is not None and isinstance(entry.value, str)
    ]


def _opinions_of(text: str) -> list[tuple[str, str, str]]:
    """The (first, second, type) of the ``opinion`` records of ``diplomacy_manager``."""
    holder = parse(text).block("diplomacy_manager")
    found: list[tuple[str, str, str]] = []
    for entry in holder.find("opinion") if holder is not None else ():
        if isinstance(entry.value, Block):
            fields = {e.key: e.value for e in entry.value.entries if isinstance(e.value, str)}
            found.append(
                (fields.get("first", ""), fields.get("second", ""), fields.get("type", ""))
            )
    return found


@dataclass(frozen=True, slots=True, eq=False)
class _Relations:
    """Who holds, leads and touches whom in the generated world, for the empire checks."""

    tags: frozenset[str]
    empires: dict[str, str]
    owner: dict[str, str]
    lord: dict[str, str]
    subjects: frozenset[str]
    generated: frozenset[str]
    land: frozenset[str]
    contact: frozenset[tuple[str, str]]
    near: dict[str, set[str]]


def _relations(natives: FinalStartPlan, plan: Plan, world: NewWorld) -> _Relations:
    countries = {country.tag: country for country in natives.countries}
    empires = {tag: country.capital for tag, country in countries.items() if country.great}
    land = {cell.key for cell in plan.cells if cell.kind is CellClass.LAND}
    owner = {
        key: tag
        for tag, c in countries.items()
        if c.kind == "state" or c.landed
        for key in c.members
    }
    contact: set[tuple[str, str]] = set()
    near: dict[str, set[str]] = {}
    for first, second in world.edges:
        keys = (plan.cells[first].key, plan.cells[second].key)
        if keys[0] in land and keys[1] in land:
            contact |= {keys, (keys[1], keys[0])}
            one, other = owner.get(keys[0]), owner.get(keys[1])
            if one and other and one != other:
                near.setdefault(one, set()).add(other)
                near.setdefault(other, set()).add(one)
    return _Relations(
        tags=frozenset(countries),
        empires=empires,
        owner=owner,
        lord={vassal: lord for lord, vassal in natives.vassals if lord in empires},
        subjects=frozenset(vassal for _, vassal in natives.vassals),
        generated=frozenset(cell.key for cell in plan.cells),
        land=frozenset(land),
        contact=frozenset(contact),
        near=near,
    )


def _rank_problems(
    countries_text: str, natives: FinalStartPlan, calibration: EmpireCalibration
) -> list[str]:
    tags = {country.tag for country in natives.countries}
    ranks = written_ranks(countries_text, tags)
    levels = written_records(countries_text, tags)
    problems: list[str] = []
    for country in natives.countries:
        wanted = [calibration.rank] if country.great else []
        if ranks.get(country.tag, []) != wanted:
            problems.append(
                f"{country.tag} writes the ranks {ranks.get(country.tag)}, not {wanted}"
            )
        if country.great and levels.get(country.tag, ([], []))[1] != [str(calibration.level)]:
            problems.append(f"Great empire {country.tag} does not write level {calibration.level}")
    return problems


def _road_problems(  # noqa: PLR0913 - written, original, planned and physical context.
    text: str,
    original: str,
    relations: _Relations,
    planned: tuple[tuple[str, str], ...],
    gone: set[str],
    *,
    historical: bool = False,
) -> list[str]:
    """Preserve vanilla roads and match planned physical contacts.

    Historical road permissions are checked against causal exchange/empire facts
    by validate_projection; the legacy path additionally enforces one empire.
    """
    problems: list[str] = []
    roads = _pairs_of(text, "road_network")
    old = [pair for pair in roads if not set(pair) & relations.generated]
    if old != [pair for pair in _pairs_of(original, "road_network") if not set(pair) & gone]:
        problems.append("The Old World roads differ from vanilla")
    new = [(min(pair), max(pair)) for pair in roads if set(pair) & relations.generated]
    if len(set(new)) != len(new) or set(new) != set(planned):
        problems.append("The generated road pairs are repeated or differ from the plan")
    joined: dict[str, set[tuple[str, str]]] = {}
    for first, second in new:
        heads = {
            relations.lord.get(tag, tag) if tag else ""
            for tag in (relations.owner.get(first), relations.owner.get(second))
        }
        if (
            first not in relations.land
            or second not in relations.land
            or (first, second) not in relations.contact
            or (not historical and (len(heads) != 1 or not heads <= set(relations.empires)))
        ):
            problems.append(f"Road {first} = {second} is not a contact inside one empire")
        elif not historical:
            joined.setdefault(next(iter(heads)), set()).add((first, second))
    for tag, pairs in joined.items():
        reached = {relations.empires[tag]}
        grew = True
        while grew:
            before = len(reached)
            for first, second in pairs:
                if first in reached or second in reached:
                    reached |= {first, second}
            grew = len(reached) > before
        if reached != {key for pair in pairs for key in pair} | {relations.empires[tag]}:
            problems.append(f"The roads of {tag} are not connected to its capital")
    return problems


def _related(kind: str, first: str, second: str, relations: _Relations) -> bool:
    """Whether (first, second) stand in the relation the opinion type is written for."""
    if kind == FEAR:
        touching = first in relations.near.get(second, ())
        return second in relations.empires and touching and first not in relations.subjects
    if kind == PREY:
        touching = second in relations.near.get(first, ())
        return first in relations.empires and touching and second not in relations.subjects
    if kind == TYRANT:
        return relations.lord.get(first) == second
    return kind == IRRITATED and relations.lord.get(second) == first


def _opinion_problems(  # noqa: PLR0913 - written, original, planned and causal context.
    text: str,
    original: str,
    relations: _Relations,
    planned: tuple[tuple[str, str, str], ...],
    gone: set[str],
    *,
    historical: bool = False,
) -> list[str]:
    """Preserve vanilla opinions and match the plan, whose history verifies each new cause."""
    problems: list[str] = []
    found = _opinions_of(text)
    old = [line for line in found if not {line[0], line[1]} & relations.tags]
    kept = [line for line in _opinions_of(original) if not {line[0], line[1]} & gone]
    if old != kept:
        problems.append("The Old World opinions differ from vanilla")
    added = [line for line in found if {line[0], line[1]} & relations.tags]
    if len(set(added)) != len(added) or set(added) != set(planned):
        problems.append("The generated opinions are repeated or differ from the plan")
    problems += [
        f"Opinion {first} {second} {kind} joins unrelated states"
        for first, second, kind in added
        if not historical
        and (kind not in OPINION_TYPES or not _related(kind, first, second, relations))
    ]
    return problems


def _knowledge_problems(countries_text: str, natives: FinalStartPlan, plan: Plan) -> list[str]:
    """Every holder of a generated opinion has discovered the area of its partner's capital.

    Read from the written country records, so that the game's warning about a scripted bias
    toward an undiscovered capital (C170) cannot come from a generated opinion.
    """
    area_of = {cell.key: cell.area for cell in plan.cells}
    written = written_discoveries(countries_text, {country.tag for country in natives.countries})
    problems: list[str] = []
    for first, second, kind in natives.opinions:
        area = area_of.get(written.get(second, ("", frozenset()))[0])
        if area is None or area not in written.get(first, ("", frozenset()))[1]:
            problems.append(f"{first} holds {kind} of {second} without discovering its capital")
    return problems


def verify_empires(  # noqa: PLR0913, PLR0917 - every cause and weakness is checked on the final texts.
    outputs: dict[str, bytes],
    natives: FinalStartPlan,
    plan: Plan,
    world: NewWorld,
    vanilla: VanillaNatives,
    originals: dict[str, str],
    gone: set[str],
    *,
    composed: ComposedStart | None = None,
) -> dict[str, object]:
    """Great empires write their level and rank, their roads and their opinions as planned.

    History revalidates rank, road permissions and each opinion's cause before
    comparing the written records; the legacy diagnostics retain static empire
    rules. Both paths require discovered capitals and preserve Old World roads
    and opinions. Unchanged setup files are read from ``originals``.
    """

    def text(name: str) -> str:
        # A file the export left unchanged is not among the outputs and is vanilla's.
        path = _mod_path(f"{SETUP_DIR}/{name}")
        return outputs[path].decode("utf-8-sig") if path in outputs else originals[name]

    calibration = vanilla.empire
    historical = natives.history is not None or composed is not None
    if natives.history is not None:
        validate_projection(
            natives,
            vanilla=vanilla,
            positions=vanilla.history_positions,
            areas={cell.key: cell.area for cell in plan.cells if cell.kind is CellClass.LAND},
        )
    relations = _relations(natives, plan, world)
    if calibration is None:
        problems = ["No empire calibration"] if relations.empires else []
    else:
        starts = (
            ((natives, vanilla),)
            if composed is None
            else tuple(zip(composed.histories, composed.calibrations, strict=True))
        )
        problems = [
            *(
                problem
                for start, local in starts
                for problem in _rank_problems(
                    text(COUNTRIES_FILE), start, local.empire or calibration
                )
            ),
            *_road_problems(
                text("09_roads.txt"),
                originals["09_roads.txt"],
                relations,
                natives.roads,
                gone,
                historical=historical,
            ),
            *_opinion_problems(
                text("18_opinions.txt"),
                originals["18_opinions.txt"],
                relations,
                natives.opinions,
                gone,
                historical=historical,
            ),
            *_knowledge_problems(text(COUNTRIES_FILE), natives, plan),
        ]
    if problems:
        extra = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        message = f"Great empires: {problems[0]}{extra}"
        raise NewWorldExportError(message)
    return {
        "empire_countries": len(relations.empires),
        "empire_road_pairs": len(natives.roads),
        "empire_opinions": len(natives.opinions),
    }


def verify_archetypes(  # noqa: PLR0913, PLR0917 - every record of the plan is checked on the final texts.
    outputs: dict[str, bytes],
    natives: FinalStartPlan,
    plan: Plan,
    vanilla: VanillaNatives,
    originals: dict[str, str],
    gone: set[str],
    *,
    composed: ComposedStart | None = None,
) -> dict[str, object]:
    """The extraordinary societies write what the plan says, and only that (R7d).

    Every country writes its planned institutions and holdings. Setup relations
    agree with the plan beside the retained vanilla entries, and their holders
    discover partner capitals. Historical memberships and causal relations have
    already passed validate_projection; only legacy diagnostics require disjoint
    groups, alliance rings and paired rivalries. Unchanged files use ``originals``.
    """

    def text(name: str) -> str:
        path = _mod_path(f"{SETUP_DIR}/{name}")
        return outputs[path].decode("utf-8-sig") if path in outputs else originals[name]

    calibration = vanilla.archetypes
    groups = cast("list[dict[str, object]]", natives.archetypes.get("groups", []))
    if calibration is None:
        problems = ["No archetype calibration"] if groups else []
    else:
        subjects = {tag for pair in natives.vassals for tag in pair}
        area_of = {cell.key: cell.area for cell in plan.cells}
        problems = archetype_problems(
            texts={name: text(name) for name in ARCHETYPE_FILES},
            originals=originals,
            countries={
                country.tag: Expected(
                    tag=country.tag,
                    state=country.kind == "state",
                    landed=country.landed,
                    include=country.include,
                    government=country.government,
                    currency=country.currency,
                    members=country.members,
                    capital=country.capital,
                    archetype=country.archetype,
                    free=not country.great and country.tag not in subjects,
                    laws=country.laws,
                    parliament=country.parliament,
                    religion=country.religion,
                )
                for country in natives.countries
            },
            bonds=Bonds(
                groups=tuple(
                    (str(group["kind"]), tuple(cast("list[str]", group["tags"])))
                    for group in groups
                ),
                alliances=natives.alliances,
                rivals=natives.rivals,
                confederations=natives.confederations,
            ),
            calibration=calibration,
            capital_areas={country.tag: area_of[country.capital] for country in natives.countries},
            gone=gone,
            historical=natives.history is not None or composed is not None,
        )
    if problems:
        extra = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        message = f"Extraordinary societies: {problems[0]}{extra}"
        raise NewWorldExportError(message)
    return {
        "archetype_groups": len(groups),
        "archetype_alliances": len(natives.alliances),
        "archetype_rivalries": len(natives.rivals),
        "archetype_confederations": len(natives.confederations),
    }


def _spline_outputs(  # noqa: PLR0913 - the roads' strips read the map, the plan and the setup.
    game_dir: Path,
    *,
    game_map: Eu5Map,
    plan: Plan,
    world: NewWorld,
    canvas: Canvas,
    final: NDArray[np.int32],
    hierarchy: dict[str, Location],
    texts: dict[str, bytes],
    natives: FinalStartPlan,
    real_america: VanillaWorld | None = None,
) -> tuple[bytes, dict[str, object]]:
    """The mod's spline network, made from the game's, and its statistics (R7d).

    Every land contact of a generated location gets a strip, so that no road between generated
    locations, set up or built in play, lacks one (C161). It fails if the file, the contacts or the
    roads of ``09_roads.txt`` are not as ``rnw.eu5_splines`` expects.
    """
    vanilla = (game_dir / SPLINE_GAME_FILE).read_bytes()
    vanilla_keys = list(hierarchy)
    mod_keys = [
        location.key
        for location in parse_locations(texts[_mod_path(DEFINITIONS)].decode("utf-8-sig"))
    ]
    extra: dict[tuple[str, str], tuple[float, float]] = {}
    anchors = world_anchors(game_map, plan, world, canvas, final)
    if real_america is None:
        contacts = world_contacts(game_map, plan, world, final)
    else:
        kept = frozenset(game_map.keys[i] for i in real_america.keep)
        all_contacts = world_contacts(game_map, plan, world, final, retained=kept)
        contacts = {
            pair: point for pair, point in all_contacts.items() if not kept.intersection(pair)
        }
        roads = {frozenset(pair) for pair in natives.roads if kept.issuperset(pair)}
        extra = {pair: point for pair, point in all_contacts.items() if frozenset(pair) in roads}
        needed = {key for pair in extra for key in pair}
        for i, cell in enumerate(real_america.plan.cells):
            if cell.key in needed:
                row, column = real_america.world.interior[i]
                anchors[cell.key] = (float(column) + 0.5, canvas.shape[0] - float(row) - 0.5)
    try:
        data, stats = build_splines(
            vanilla,
            vanilla_keys=vanilla_keys,
            mod_keys=mod_keys,
            contacts=contacts,
            anchors=anchors,
            map_width=int(final.shape[1]),
            retained_contacts=extra,
        )
    except SplineError as error:
        message = f"Spline network: {error}"
        raise NewWorldExportError(message) from error
    roads = _pairs_of(_read(game_dir, f"{SETUP_DIR}/09_roads.txt"), "road_network")
    problems = spline_problems(
        data,
        vanilla,
        vanilla_keys=vanilla_keys,
        mod_keys=mod_keys,
        contacts=[*contacts, *extra],
        roads=[*roads, *natives.roads],
        map_width=int(final.shape[1]),
    )
    if problems:
        remaining = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        message = f"Spline network: {problems[0]}{remaining}"
        raise NewWorldExportError(message)
    return data, stats | {"land_contacts": len(contacts)}


def vanilla_new_world_keys(hierarchy: dict[str, Location], removed: set[str]) -> set[str]:
    """Region, area, province and location keys of the vanilla New World.

    Their development entries are dropped, so no kept vanilla location may lie under one.
    """
    keys = {
        name
        for location in hierarchy.values()
        if location.continent == NEW_WORLD
        for name in (location.region, location.area, location.province, location.key)
    }
    under = [
        location.key
        for location in hierarchy.values()
        if location.key not in removed
        and keys & {location.region, location.area, location.province, location.key}
    ]
    if under:
        message = (
            f"{len(under)} kept vanilla locations (for example {under[0]}) lie under "
            "New World keys whose development entries are dropped"
        )
        raise NewWorldExportError(message)
    return keys


def _vanilla_american(game_map: Eu5Map, hierarchy: dict[str, Location]) -> dict[str, Location]:
    index = {key: number for number, key in enumerate(game_map.keys)}
    return {
        key: location
        for key, location in hierarchy.items()
        if location.continent == NEW_WORLD
        and key in index
        and game_map.classes[index[key]] is CellClass.LAND
    }


def calibrate_development(
    game_dir: Path, game_map: Eu5Map, hierarchy: dict[str, Location]
) -> DevelopmentCalibration:
    """Development calibration on the vanilla 1337 Americas of the installation."""
    american = _vanilla_american(game_map, hierarchy)
    sizes = river_sizes(
        game_map.labels,
        game_map.rivers,
        len(game_map.keys),
        sizes=RIVER_SIZES,
    )
    index = {key: number for number, key in enumerate(game_map.keys)}
    return calibrate(
        rules_text=_read(game_dir, f"{SETUP_DIR}/{DEVELOPMENT_FILE}"),
        templates_text=_read(game_dir, TEMPLATES),
        buildings_text=_read(game_dir, f"{SETUP_DIR}/{BUILDINGS_FILE}"),
        countries_text=_read(game_dir, f"{SETUP_DIR}/10_countries.txt"),
        american=american,
        rivers={key: int(sizes[index[key]]) for key in american},
    )


def _plan_development(  # noqa: PLR0913 - development reads the calibration, world and ports.
    calibration: DevelopmentCalibration,
    *,
    game_map: Eu5Map,
    world: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    natives: FinalStartPlan,
    labels: NDArray[np.int32],
    docks: dict[int, tuple[int, int]],
    river_codes: NDArray[np.uint8],
) -> Development:
    wet = {CellClass.SEA, CellClass.LAKE}
    table = np.array([kind in wet for kind in (*game_map.classes, *world.classes)], dtype=bool)
    cells = sorted(docks)
    scores = shelter(table[labels], np.array([docks[cell] for cell in cells], dtype=np.int64))
    sizes = river_sizes(
        world.labels,
        river_codes,
        len(world.classes) + 1,
        sizes=RIVER_SIZES,
    )
    cell_fields = [
        (cell.key, biomes.vegetation[i], biomes.climate[i], biomes.topography[i], int(sizes[i]))
        for i, cell in enumerate(plan.cells)
        if cell.kind is CellClass.LAND
    ]
    return build_development(
        calibration=calibration,
        natives=natives,
        cells=cell_fields,
        scores={
            plan.cells[cell].key: score for cell, score in zip(cells, scores.tolist(), strict=True)
        },
    )


def _verify_terms(
    block: Block, plan: Plan, development: Development, calibration: DevelopmentCalibration
) -> dict[str, int]:
    land = {cell.key for cell in plan.cells if cell.kind is CellClass.LAND}
    generated = {cell.key for cell in plan.cells}
    found: dict[str, int] = {}
    for entry in block.entries:
        if entry.key in generated:
            if entry.key in found or entry.key not in land or not isinstance(entry.value, str):
                message = f"Development entry {entry.key} is repeated or not on land"
                raise NewWorldExportError(message)
            found[entry.key] = int(entry.value)
    if found != development.terms or not all(
        1 <= term <= calibration.society_max for term in found.values()
    ):
        message = "Generated development entries differ from the plan or exceed the maximum"
        raise NewWorldExportError(message)
    return found


def _verify_villages(
    manager: Block | None, natives: FinalStartPlan, development: Development
) -> list[tuple[str, str]]:
    states = {c.tag: c.capital for c in natives.countries if c.kind == "state"}
    villages: list[tuple[str, str]] = []
    for entry in manager.find(VILLAGE) if manager is not None else ():
        if not isinstance(entry.value, Block):
            continue
        tag, where = entry.value.first("tag"), entry.value.first("location")
        if tag is not None and where is not None and tag.value in states:
            villages.append((str(tag.value), str(where.value)))
    if (
        len({where for _, where in villages}) != len(villages)
        or any(states[tag] != where for tag, where in villages)
        or sorted(villages) != sorted(development.villages)
    ):
        message = "Generated market villages are not one per planned state capital"
        raise NewWorldExportError(message)
    return villages


def verify_development(  # noqa: PLR0913, PLR0917 - every generated development record is checked.
    outputs: dict[str, bytes],
    plan: Plan,
    natives: FinalStartPlan,
    development: Development,
    calibration: DevelopmentCalibration,
    new_world_keys: set[str],
    *,
    unchanged_geography: Collection[str] = (),
) -> dict[str, object]:
    """No positional development is left; terms, harbours and villages are as planned."""

    def text(relative: str) -> str:
        return outputs[_mod_path(relative)].decode("utf-8-sig")

    rules_text = text(f"{SETUP_DIR}/{DEVELOPMENT_FILE}")
    block = parse(rules_text).block("development")
    if block is None:
        message = "No development block in the output"
        raise NewWorldExportError(message)
    kept = sorted(
        entry.key
        for entry in block.entries
        if entry.key in new_world_keys and entry.key not in unchanged_geography
    )
    if kept:
        message = f"Development entry {kept[0]} of the vanilla New World was kept"
        raise NewWorldExportError(message)
    generated = {cell.key for cell in plan.cells}
    old = {k: v for k, v in calibration.rules.items() if k not in new_world_keys}
    if {k: v for k, v in development_rules(rules_text).items() if k not in generated} != old:
        message = "Development rules outside the New World differ from vanilla"
        raise NewWorldExportError(message)
    found = _verify_terms(block, plan, development, calibration)
    redrawn = generated.difference(unchanged_geography)
    harbours = {k: v for k, v in template_harbours(text(TEMPLATES)).items() if k in redrawn}
    planned = {k: v for k, v in development.harbours.items() if k in redrawn}
    if harbours != planned or not set(harbours.values()) <= set(calibration.harbours):
        message = "Generated harbour values differ from the ports or the vanilla values"
        raise NewWorldExportError(message)
    manager = parse(text(f"{SETUP_DIR}/{BUILDINGS_FILE}")).block("building_manager")
    villages = _verify_villages(manager, natives, development)
    return {
        "development_entries": len(found),
        "harbour_values": len(harbours),
        "market_villages": len(villages),
    }


def _preview(final_rgb_classes: NDArray[np.uint8]) -> bytes:
    return encode_png(final_rgb_classes, color_type=COLOR_RGB, compression="zlib")


def _check_identity_budget(game_map: Eu5Map, removed: set[str], plan: Plan) -> None:
    """The final cap includes split remainders and counts shared identities once."""
    final_count = len(game_map.keys) - len(removed) + len(emitted_cells(plan))
    if final_count > MAX_LOCATIONS:
        raise LocationLimitError(final_count, MAX_LOCATIONS)


def export_new_world(  # noqa: PLR0913 - the CLI contract names each input.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
    replace: bool = False,
    check_memory: bool = True,
    progress: Progress | None = None,
    world_code: str | None = None,
    world_label: Label | None = None,
    land_mask: LandMask | None = None,
    cache_dir: Path | None = None,
) -> dict[str, object]:
    """Generate, validate and stage one New World mod bundle; return its report.

    The large files (terrain layers, vegetation instances) go to a spool directory beside
    the output as they are made, and join the bundle when it is written. Unless
    ``check_memory`` is false the export first checks that the machine has the memory its
    smallest working set needs (``EXPORT_MEMORY``); more memory only makes it faster.
    ``progress`` receives the stages as they run and can cancel the job, which raises
    ``Cancelled`` and leaves nothing behind. ``world_label`` is the title the game's mod list
    shows and the tag drawn on a covered picture (``rnw.worldname``); without one the world is
    titled by its type and a tag made from its code. ``land_mask`` is the land drawn in an image
    (``rnw.landmask``): the settings' mask id must be its id, and the world is made on it.
    """
    check_new_output(output, MOD_NAME, game_dir, replace=replace)
    if check_memory:
        require_memory(EXPORT_MEMORY, "The New World export")
    with (
        active(progress),
        collector_paused(),
        Spool(spool_path(output)) as spool,
        inputs.recording(game_dir) as recorder,
    ):
        return _export_new_world(
            spool,
            recorder,
            game_dir,
            output,
            seed=seed,
            settings=settings,
            accept_build=accept_build,
            settings_file=settings_file,
            world_code=world_code,
            world_label=world_label,
            land_mask=land_mask,
            cache_dir=cache_dir,
        )


def _require_algorithm(settings: Settings) -> None:
    """Refuse an epoch this generator cannot make a world by, in words, before any work."""
    try:
        _ = epoch.require_selectable(settings.algorithm)
    except epoch.EpochError as error:
        raise NewWorldExportError(str(error)) from error
    if settings.continents.regions and settings.algorithm < epoch.CONTINENT_SELECTION:
        message = (
            f"Additional continents require algorithm epoch {epoch.CONTINENT_SELECTION} or later"
        )
        raise NewWorldExportError(message)


def _ocean_pixels(world: NewWorld) -> NDArray[np.bool_]:
    """The generated sea mask, in bounded strips and independent of cell numbers."""
    sea_class = np.array([kind is CellClass.SEA for kind in world.classes] + [False])
    ocean = np.empty(world.labels.shape, dtype=np.bool_)
    for first in range(0, ocean.shape[0], 1024):
        rows = slice(first, min(ocean.shape[0], first + 1024))
        ocean[rows] = sea_class[world.labels[rows]]
    return ocean


type _VanillaReads = tuple[DecalStore, dict[str, dict[str, str]], set[str], DevelopmentCalibration]


@dataclass(frozen=True, slots=True)
class _PreparedVanilla:
    game_map: Eu5Map
    canvas: Canvas
    moved: Moved | None
    removed: set[str]
    moves: tuple[tuple[int, int], ...]
    reads: Future[_VanillaReads]
    geometries: Future[VanillaGeometry]
    climates: Future[VanillaClimate]
    levels: Future[dict[str, NDArray[np.int64]]]
    natives: Future[VanillaNatives]


def _prepare_vanilla(  # noqa: PLR0913, PLR0917 - original inputs and their fixed island placement.
    stages: Stages,
    game_dir: Path,
    original: Eu5Map,
    clean: Canvas,
    hierarchy: dict[str, Location],
    algorithm: int,
    moves: tuple[tuple[int, int], ...],
    *,
    composed: bool = False,
    complete_ocean: bool = False,
) -> _PreparedVanilla:
    if composed and (clean.groups or complete_ocean):
        source, fixed = (
            absorb_ocean_specks(original, clean) if complete_ocean else (original, clean)
        )
        game_map = relocate_map(source, fixed)
        canvas = relocated_canvas(game_map, fixed)
    else:
        canvas = place_islands(original, clean, list(moves))
        game_map = relocate_map(open_map(original, canvas), canvas)
    width = int(game_map.labels.shape[1])
    moved = moved_pixels_of(canvas)
    removed = {game_map.keys[index] for index in np.flatnonzero(canvas.removed).tolist()}
    mark_ready("island placements")

    def read_vanilla() -> _VanillaReads:
        return (
            ShiftedStore(game_dir, (int(game_map.labels.shape[0]), width), moved),
            template_attributes(_read(game_dir, TEMPLATES)),
            set() if composed else vanilla_new_world_keys(hierarchy, removed),
            calibrate_development(game_dir, game_map, hierarchy),
        )

    reads = stages.submit("vanilla reads", read_vanilla)
    geometries = stages.submit(
        "vanilla geometry", lambda: vanilla_geometry(game_map, canvas, hierarchy, wrap_x=composed)
    )
    climates = stages.submit(
        "vanilla climate",
        lambda: _vanilla_climate(
            game_map, reads.result()[0], seasonal=algorithm >= epoch.OPEN_CLIMATE
        ),
    )
    levels = stages.submit(
        "vanilla material levels",
        lambda: _vanilla_level_counts(game_map, reads.result()[1], reads.result()[0]),
    )
    natives = stages.submit(
        "vanilla natives",
        lambda: vanilla_natives(
            game_dir, game_map, geometries.result(), reads.result()[1], hierarchy
        ),
    )
    return _PreparedVanilla(
        game_map, canvas, moved, removed, moves, reads, geometries, climates, levels, natives
    )


@dataclass(slots=True, eq=False)
class _ExportGeography:
    game_map: Eu5Map
    canvas: Canvas
    cover_canvas: Canvas
    moved: Moved | None
    shape: Water
    final: NDArray[np.int32]
    removed: set[str]
    store: DecalStore
    attributes: dict[str, dict[str, str]]
    new_world_keys: set[str]
    calibration: DevelopmentCalibration
    geometry: VanillaGeometry
    vanilla_hashes: set[int]
    loc_keys: KeySpace
    plan: Plan
    checks: dict[str, int]
    neighbours: frozenset[int]
    biomes: CellBiomes
    biome_stats: dict[str, object]
    rivers: tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]]
    levels: Future[dict[str, NDArray[np.int64]]]
    vanilla_start: Future[VanillaNatives]
    water_textures: Future[dict[str, int]]
    vanilla_ports: dict[str, VanillaPort]
    vanilla_locations: VanillaLocations | None = None
    contact: ContactBlend | None = None


def _water_textures(  # noqa: PLR0913 - read the fixed map plus the new mask and coastline.
    spool: Spool,
    game_dir: Path,
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    *,
    seed: int,
    moved: Moved | None,
    regional_water: Water | None = None,
) -> dict[str, int]:
    codes = _codes(game_map, canvas, world)
    canvas_world = codes != OUTSIDE
    vanilla_water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
    )[game_map.labels]
    new_water = vanilla_water.copy()
    new_water[canvas_world] = codes[canvas_world] == WATER_CODE
    inland = None
    if regional_water is not None:
        enclosed = np.array(
            [kind is Topography.INLAND_SEA for kind in regional_water.waters.topography] + [False],
            dtype=bool,
        )
        inland = enclosed[world.labels]
    files, stats = water_outputs(
        game_dir, vanilla_water, new_water, canvas_world, seed, moved, inland=inland
    )
    spool.update(files)
    return stats


def _prepare_american_geography(  # noqa: PLR0913, PLR0915 - preserve the legacy geography stages.
    stages: Stages,
    spool: Spool,
    game_dir: Path,
    game_map: Eu5Map,
    hierarchy: dict[str, Location],
    *,
    seed: int,
    resources_seed: int,
    settings: Settings,
    land_mask: LandMask | None,
    cache_dir: Path | None,
) -> _ExportGeography:
    """Run the legacy American map pipeline, including vanilla island movement."""
    clean = run_stage(
        "select canvas",
        lambda: landcache.get_canvas(
            cache_dir,
            game_map,
            settings.new_world.ocean_band_px,
            expanded=bool(settings.new_world.expand_oceans or settings.new_world.landform),
        ),
    )
    vanilla_waters = read_waters(_read(game_dir, TEMPLATES))
    bands = current_bands(game_map, clean, vanilla_waters)
    # The land is made on the whole canvas; the island groups it covers stay or move, and the
    # rest is built round them (``rnw.islands``). Everything after this reads the moved map.
    drawing: Fitted | None = (
        None if land_mask is None else fit_drawing(land_mask, clean.mask.shape, settings.algorithm)
    )

    preparations: list[_PreparedVanilla] = []

    def prepare(moves: tuple[tuple[int, int], ...]) -> None:
        nonlocal game_map
        if preparations:
            message = "The world's island placements were published more than once"
            raise NewWorldExportError(message)
        preparations.append(
            _prepare_vanilla(
                stages, game_dir, game_map, clean, hierarchy, settings.algorithm, moves
            )
        )
        # The generator now owns its domain masks. Its calibration is complete,
        # so all further readers can share the moved map and release the original.
        game_map = preparations[0].game_map

    localizations: list[Future[set[int]]] = []

    def generate() -> tuple[NewWorld, SizeModel | None]:
        # The game's own locations size the cells (epoch 64) and vote their ground later.
        sizes = (
            input_calibration.get_sizes(
                cache_dir, game_dir, game_map, lambda: _vanilla_sizes(game_dir, game_map)
            )
            if settings.algorithm >= epoch.RIVERS_FIRST
            else None
        )
        # Close the calibration recorder before unrelated parallel game reads.
        localizations.append(
            stages.submit(
                "vanilla localization keys",
                lambda: key_hashes(vanilla_localization_keys(game_dir)),
            )
        )
        made = landcache.get_world(
            cache_dir,
            clean.mask,
            seed=seed,
            settings=settings.new_world,
            drawn=None if drawing is None else drawing.land,
            sea_bands=bands,
            groups=clean.footprints,
            template=clean.template,
            lakes_drawn=None if drawing is None else drawing.lakes,
            hints=None if drawing is None else drawing.hints,
            algorithm=settings.algorithm,
            seam=(clean.roll - clean.col0) % clean.shape[1],
            sizes=sizes,
            on_placed=prepare,
        )
        return made, sizes

    world, sizes = run_stage("generate world", generate)
    localization = localizations[0]
    drawing = None
    moves = tuple((int(row), int(column)) for row, column in world.moves.tolist())
    if not preparations:
        # Kept worlds and diagnostic providers may return their finished placement.
        prepare(moves)
    prepared = preparations[0]
    if prepared.moves != moves:
        message = "The completed world differs from its published island placements"
        raise NewWorldExportError(message)
    game_map, canvas = prepared.game_map, prepared.canvas
    moved_groups, removed = prepared.moved, prepared.removed
    reads, geometries = prepared.reads, prepared.geometries
    climates, levels, vanilla_start = prepared.climates, prepared.levels, prepared.natives
    # The corridor planner depends on the physical water mask, not on cell
    # identities. Recompute it on cached worlds as well as freshly made ones.
    ocean = _ocean_pixels(world)
    designed = draw_corridors(
        corridor_paths(ocean, bands, settings.new_world.sea_zone_px, domain=canvas.mask),
        ocean,
        1,
    )
    del ocean
    vanilla_ports = read_ports(_read(game_dir, PORTS))
    land_biomes: tuple[CellBiomes, dict[str, object]] | None = None
    if settings.algorithm >= epoch.NATURAL_WASTELANDS:
        # The coasts (ports, docks, strait crossings) are made for the passable land beside
        # the sea, so the wasteland plan comes first and the coast stages see its classes.
        world, land_cells, land_stats = run_stage(
            "land character",
            lambda: _land_character(
                game_map,
                canvas=canvas,
                world=world,
                vanilla=climates.result(),
                attributes=reads.result()[1],
                game_dir=game_dir,
                settings=settings,
                seed=seed,
                material_seed=resources_seed,
                sizes=sizes,
            ),
        )
        land_biomes = (land_cells, land_stats)
    else:
        skip_stages("land character")
    settled = run_stage(
        "settle coasts",
        lambda: settle_coast(
            game_map,
            canvas,
            world,
            ports=vanilla_ports,
            vanilla=vanilla_waters,
            removed=removed,
            designed=designed,
        ),
    )
    shapes = run_stage("water shapes", lambda: shape_water(settled))
    coast = shapes.coast
    world = coast.world
    # The exact budget is checked after identities are planned: an early
    # cell count double-counts generated sea cells sharing retained oceans.
    final_labels = _final_labels(game_map, canvas, world)

    def identify() -> tuple[KeySpace, Plan]:
        loc_keys = KeySpace(localization.result() | static_hashes())
        geometry = geometries.result()
        biomes = biome_readings.result()[0]
        physical = physical_keys(
            game_map,
            hierarchy,
            reads.result()[1],
            unpack_pairs(climates.result().locations.pairs),
            world=world,
            biomes=biomes,
            pixels=geometry.pixels.tolist(),
        )
        plan = plan_identities(
            game_map,
            canvas,
            world,
            hierarchy,
            geometry,
            seed=seed,
            settings=settings.new_world,
            keys=loc_keys,
            waters=shapes.waters,
            physical=physical,
            biomes=biomes,
            algorithm=settings.algorithm,
        )
        if settings.new_world.expand_oceans or settings.new_world.landform:
            plan.oceans = plan_oceans(
                game_map, canvas, world, plan, hierarchy, shapes.zones, loc_keys
            )
        return loc_keys, plan

    water = stages.submit(
        "water textures",
        lambda: _water_textures(
            spool, game_dir, game_map, canvas, world, seed=seed, moved=moved_groups
        ),
    )

    def read_biomes() -> tuple[CellBiomes, dict[str, object], ClimateGrid]:
        found = _biome_model(
            game_map,
            canvas=canvas,
            world=world,
            final_labels=final_labels,
            vanilla=climates.result(),
            attributes=reads.result()[1],
            seed=seed,
            precious_permille=settings.new_world.precious_permille,
            resources=settings.resources,
            material_seed=resources_seed,
            land=land_biomes,
        )
        mark_ready("biome readings")
        return found

    # Identities read the finished biome model, not the rivers. Submit its shared
    # future first so errors (including cancellation) reach both consumers and a
    # one-worker export keeps the original sequential order.
    biome_readings = stages.prepare("biome readings", read_biomes)

    def weather() -> tuple[
        CellBiomes,
        dict[str, object],
        tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]],
    ]:
        biomes, biome_stats, climate = biome_readings.result()
        return biomes, biome_stats, _rivers(world, canvas, climate, seed, settings.algorithm)

    weathering = stages.submit("biomes and rivers", weather)
    identities = stages.submit("identities", identify)
    checks = stages.submit(
        "world checks",
        lambda: _check_world(
            game_map,
            canvas,
            world,
            final_labels,
            identities.result()[1],
            shapes.zones,
            settings.new_world,
        ),
    )
    store, vanilla_attributes, new_world_keys, calibration = reads.result()
    geometry = geometries.result()
    vanilla_hashes = localization.result()
    loc_keys, plan = identities.result()
    world_checks, neighbours = checks.result()
    if plan.oceans is not None:
        removed -= plan.oceans.retained
    _check_identity_budget(game_map, removed, plan)
    biomes, biome_stats, (river_codes, carved, river_stats) = weathering.result()
    return _ExportGeography(
        game_map,
        canvas,
        clean,
        moved_groups,
        shapes,
        final_labels,
        removed,
        store,
        vanilla_attributes,
        new_world_keys,
        calibration,
        geometry,
        vanilla_hashes,
        loc_keys,
        plan,
        world_checks,
        neighbours,
        biomes,
        biome_stats,
        (river_codes, carved, river_stats),
        levels,
        vanilla_start,
        water,
        vanilla_ports,
    )


def _composed_identities(  # noqa: PLR0913 - country-independent location geography and localization.
    game_map: Eu5Map,
    shared: ComposedWorld,
    regions: Sequence[WorldRegion],
    water: Water,
    hierarchy: dict[str, Location],
    *,
    geometry: VanillaGeometry,
    training: VanillaLocations,
    attributes: dict[str, dict[str, str]],
    biomes: CellBiomes,
    geography: Mapping[str, NewWorldSettings],
    keys: KeySpace,
    seed: int,
) -> Plan:
    pairs = unpack_pairs(training.pairs)
    source_cells = water.coast.source_cells
    numbered: dict[str, tuple[RegionalLand, list[int]]] = {}
    for region in regions:
        domain = region.domain
        name = domain.continent.key
        source: list[int] = shared.cell_ids[name].tolist()
        local = replace(region.world, classes=tuple(shared.world.classes[cell] for cell in source))

        def values(field: tuple[str, ...], source: list[int] = source) -> tuple[str, ...]:
            return tuple(field[i] if i < len(field) else "" for i in source)

        local_biomes = CellBiomes(
            values(biomes.climate),
            values(biomes.vegetation),
            values(biomes.topography),
            values(biomes.raw_material),
        )
        regional = plan_regional_land(
            game_map,
            domain,
            local,
            hierarchy,
            attributes=attributes,
            pairs=pairs,
            biomes=local_biomes,
            settings=geography[name],
            keys=keys,
            replaced=shared.canvas.removed,
            original=geometry,
        )
        numbered[name] = regional, [source_cells[cell] for cell in source]
    world, canvas = water.coast.world, shared.canvas
    plan = plan_composed_identities(
        game_map,
        canvas,
        world,
        hierarchy,
        geometry=geometry,
        regions=numbered,
        topography=biomes.topography + ("",) * (len(world.classes) - len(biomes.topography)),
        seed=seed,
        keys=keys,
        waters=water.waters,
    )
    plan.oceans = plan_oceans(game_map, canvas, world, plan, hierarchy, water.zones, keys)
    plan.oceans.patches.extend(canvas.enclosed_ocean)
    plan.oceans.stats["ocean_identity_recolours"] += sum(
        part.pixels for part, _ in canvas.enclosed_ocean
    )
    return plan


def _shared_ocean_boundaries(shared: ComposedWorld, water: Water) -> dict[str, int]:
    """Verify that each common boundary has deep water and no merged land."""
    owner = [-1] * len(shared.world.classes)
    names = list(shared.cell_ids)
    for number, cells in enumerate(shared.cell_ids.values()):
        for cell in cells.tolist():
            owner[cell] = number
    deep: Counter[tuple[int, int]] = Counter()
    kinds = shared.world.classes
    translated = water.coast.source_cells
    depth = water.waters.topography
    deep_types = {Topography.DEEP_OCEAN, Topography.OCEAN_WASTELAND}
    for first, second in shared.world.edges:
        a, b = owner[first], owner[second]
        if a == b or min(a, b) < 0:
            continue
        if kinds[first] is not CellClass.SEA or kinds[second] is not CellClass.SEA:
            message = f"The {names[a]} and {names[b]} canvases meet outside the ocean"
            raise NewWorldExportError(message)
        if depth[translated[first]] in deep_types and depth[translated[second]] in deep_types:
            deep[min(a, b), max(a, b)] += 1
    results = {
        f"deep_sea_contacts_{names[a]}_{names[b]}": deep[a, b]
        for a in range(len(names))
        for b in range(a + 1, len(names))
    }
    if not all(results.values()):
        message = "A pair of generated continents has no shared deep-ocean boundary"
        raise NewWorldExportError(message)
    return results


def _regional_worlds(  # noqa: PLR0913 - settings and the inputs shared by each physical window.
    stages: Stages,
    game_map: Eu5Map,
    geography: Mapping[str, NewWorldSettings],
    *,
    seed: int,
    algorithm: int,
    sizes: SizeModel,
    land_mask: LandMask | None,
    cache_dir: Path | None,
    require_asia_connection: bool,
    retained_tolls: Collection[str],
    store: DecalStore,
    southern_passage: int = 0,
) -> tuple[WorldRegion, ...]:
    domains = plan_domains(
        game_map,
        geography,
        seed=seed,
        require_asia_connection=require_asia_connection,
        retained_tolls=retained_tolls,
    )

    def build(domain: Domain) -> WorldRegion:
        checkpoint()
        name = domain.continent.key
        mask = domain.mask
        knobs = geography[name]
        south = max(0, domain.rows.stop - (game_map.labels.shape[0] - southern_passage))
        if domain.shared_ocean and not knobs.landform:
            area = int(np.count_nonzero(mask[domain.north_water_rows : len(mask) - south]))
            land = int(np.count_nonzero(domain.footprint))
            nominal = min(area, land + game_map.labels.size // SHARED_OCEAN_DIVISOR)
            knobs = replace(knobs, land_permille=knobs.land_permille * nominal // area)
        drawing = (
            fit_drawing(land_mask, domain.mask.shape, algorithm)
            if name == NEW_WORLD and land_mask is not None
            else None
        )
        terrain = None
        world_box: tuple[slice, slice] | None = None
        box = contact_box(domain.land_interface) if domain.land_interface is not None else None
        if domain.join_asia and box is not None:
            rows, columns = box
            global_rows = slice(domain.first_row + rows.start, domain.first_row + rows.stop)
            first = (domain.first_column + columns.start) % domain.map_width
            global_columns = slice(first, first + columns.stop - columns.start)
            samples = np.arange(first, first + columns.stop - columns.start, dtype=np.int64)
            samples %= domain.map_width
            terrain = ContactTerrain(box, store.height_window(global_rows, samples))
            world_box = global_rows, global_columns
        world = landcache.get_world(
            cache_dir,
            mask,
            seed=seed if name == NEW_WORLD else derive_seed(seed, "continent", name),
            settings=knobs,
            groups=domain.footprints,
            template=domain.footprint,
            drawn=None if drawing is None else drawing.land,
            lakes_drawn=None if drawing is None else drawing.lakes,
            hints=None if drawing is None else drawing.hints,
            seam=domain.watershed_seam,
            sizes=sizes,
            algorithm=algorithm,
            map_rows=(domain.first_row, game_map.labels.shape[0]),
            outside_land=domain.contact_land,
            land_interface=domain.land_interface if domain.join_asia else None,
            strait=domain.strait,
            contact_terrain=terrain,
            island_sites=domain.island_sites,
            reserve_south=south,
            reserve_north=domain.north_water_rows,
        )
        if terrain is None or world_box is None or domain.contact_land is None:
            return WorldRegion(domain, world)
        dry = np.array(
            [kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes] + [False]
        )[world.labels]
        joint = terrain.blend(dry, domain.contact_land)
        return WorldRegion(
            domain,
            world,
            None if joint is None else replace(joint, box=world_box),
        )

    if len(domains) == 1:
        return (build(domains[0]),)
    first, *additional = domains
    memory = available_memory()
    background = sum(domain.mask.size for domain in additional) * REGIONAL_BYTES_PER_PIXEL
    if memory is None or memory < EXPORT_MEMORY + background or stage_workers() == 1:
        return tuple(build(domain) for domain in domains)

    def quiet_build(domain: Domain) -> WorldRegion:
        with quiet_stages():
            return build(domain)

    if (
        len(additional) > 1
        and stage_workers() >= len(domains)
        and memory >= EXPORT_MEMORY + background + first.mask.size * REGIONAL_BYTES_PER_PIXEL
    ):
        pending = [
            stages.prepare(f"{domain.continent.key} geography", partial(quiet_build, domain))
            for domain in additional
        ]
        return build(first), *(future.result() for future in pending)

    def other_regions() -> tuple[WorldRegion, ...]:
        return tuple(quiet_build(domain) for domain in additional)

    others = stages.prepare("other continents geography", other_regions)
    main = build(first)
    return (main, *others.result())


def _replaced_development(hierarchy: Mapping[str, Location], removed: set[str]) -> set[str]:
    """Retire positional development only when that key has lost every original location."""
    gone: set[str] = set()
    retained: set[str] = set()
    for key, location in hierarchy.items():
        holder = gone if key in removed else retained
        holder.update((key, location.province, location.area, location.region))
    return gone - retained


def _prepare_composed_geography(  # noqa: PLR0913, PLR0915 - stages share geography and calibration.
    stages: Stages,
    spool: Spool,
    game_dir: Path,
    game_map: Eu5Map,
    hierarchy: dict[str, Location],
    *,
    seed: int,
    resources_seed: int,
    settings: Settings,
    land_mask: LandMask | None,
    cache_dir: Path | None,
) -> _ExportGeography:
    """Compose regional surfaces before running the common geography and texture stages."""
    geography = {region.key: region.new_world for region in settings.continents.regions}
    resources = {region.key: dict(region.resources) for region in settings.continents.regions}
    if settings.continents.america and not settings.new_world.keep_geography:
        geography[NEW_WORLD] = settings.new_world
        resources[NEW_WORLD] = cast("dict[str, int]", asdict(settings.resources))
    sizes = input_calibration.get_sizes(
        cache_dir, game_dir, game_map, lambda: _vanilla_sizes(game_dir, game_map)
    )
    localization = stages.submit(
        "vanilla localization keys", lambda: key_hashes(vanilla_localization_keys(game_dir))
    )
    terrain_store = DecalStore(game_dir, game_map.labels.shape)
    southern_passage = (
        max(4, 160 * game_map.labels.shape[1] // 16_384)
        if settings.continents.sea_circumnavigation
        and not (settings.continents.america and settings.new_world.landform)
        else 0
    )
    regions = run_stage(
        "generate world",
        lambda: _regional_worlds(
            stages,
            game_map,
            geography,
            seed=seed,
            algorithm=settings.algorithm,
            sizes=sizes,
            land_mask=land_mask,
            cache_dir=cache_dir,
            require_asia_connection=any(
                region.require_asia_connection for region in settings.continents.regions
            ),
            retained_tolls=sound_toll_locations(_read(game_dir, DEFAULT_MAP)),
            store=terrain_store,
            southern_passage=southern_passage,
        ),
    )
    composed = run_stage(
        "select canvas",
        lambda: compose_regions(game_map, regions, southern_passage=southern_passage, seed=seed),
    )
    complete_ocean = all(region.domain.shared_ocean for region in regions)
    vanilla = _prepare_vanilla(
        stages,
        game_dir,
        game_map,
        composed.canvas,
        hierarchy,
        settings.algorithm,
        composed.canvas.moves,
        composed=True,
        complete_ocean=complete_ocean,
    )
    game_map, canvas = vanilla.game_map, vanilla.canvas
    composed = replace(composed, canvas=canvas)
    # The river rasters depend on regional drainage, not on the later sea
    # identities. Let them share the existing worker budget with the biome pass.
    rivers = stages.submit(
        "biomes and rivers", lambda: composed_rivers(canvas.shape, regions, seed)
    )
    store, attributes, _, calibration = vanilla.reads.result()
    training = vanilla.climates.result()
    shared, base_biomes, biome_stats = run_stage(
        "land character",
        lambda: composed_land_character(
            game_map,
            composed,
            regions,
            geography=geography,
            resources=resources,
            vanilla=training,
            attributes=attributes,
            game_dir=game_dir,
            seed=seed,
            material_seed=resources_seed,
            sizes=sizes,
        ),
    )
    vanilla_ports = read_ports(_read(game_dir, PORTS))
    vanilla_waters = read_waters(_read(game_dir, TEMPLATES))
    coast = run_stage(
        "settle coasts",
        lambda: settle_coast(
            game_map,
            canvas,
            shared.world,
            ports=vanilla_ports,
            vanilla=vanilla_waters,
            removed=vanilla.removed,
            minimum_sea=min(knobs.min_sea_cell_px for knobs in geography.values())
            if complete_ocean
            else 0,
        ),
    )
    shapes = run_stage(
        "water shapes",
        lambda: shape_water(coast, regular_grid=True, southern_passage=southern_passage),
    )
    world = shapes.coast.world
    water_textures = stages.submit(
        "water textures",
        lambda: _water_textures(
            spool,
            game_dir,
            game_map,
            canvas,
            world,
            seed=seed,
            moved=vanilla.moved,
            regional_water=shapes,
        ),
    )
    biomes = settled_biomes(base_biomes, shared.world, shapes.coast)
    mark_ready("biome readings")
    geometry = vanilla.geometries.result()
    hashes = localization.result()
    keys = KeySpace(hashes | static_hashes())
    plan = run_stage(
        "identities",
        lambda: _composed_identities(
            game_map,
            shared,
            regions,
            shapes,
            hierarchy,
            geometry=geometry,
            training=training.locations,
            attributes=attributes,
            biomes=base_biomes,
            geography=geography,
            keys=keys,
            seed=seed,
        ),
    )
    for region in regions:
        if (landing := region.world.strait_landing) is None:
            continue
        r, c = landing
        point = (
            r + region.domain.first_row,
            (c + region.domain.first_column) % region.domain.map_width,
        )
        if (crossing := mediterranean_crossing(game_map, shapes, plan, point)) is not None:
            shapes = replace(shapes, external_crossings=(crossing,))
    removed = vanilla.removed
    if plan.oceans is not None:
        removed = removed - plan.oceans.retained
    plan.dropped_areas = missing_area_keys(hierarchy, removed, plan)
    _check_identity_budget(game_map, removed, plan)
    final = _final_labels(game_map, canvas, world)
    if southern_passage:
        passable = np.array(
            [
                kind is CellClass.SEA and not closed
                for kind, closed in zip(game_map.classes, game_map.ambiguous, strict=True)
            ]
            + [
                kind is CellClass.SEA and i not in shapes.zones
                for i, kind in enumerate(world.classes)
            ],
            dtype=bool,
        )
        if not passable[final[-1]].all():
            message = "The southern sea route has a break before it returns around the map"
            raise NewWorldExportError(message)
    checks, neighbours = run_stage(
        "world checks",
        lambda: _check_world(
            game_map,
            canvas,
            world,
            final,
            plan,
            shapes.zones,
            settings.new_world,
            generated_continents=frozenset(geography),
            inland_sizes={name: inland_sea_min_area(knobs) for name, knobs in geography.items()},
        ),
    )
    if (
        any(region.domain.join_asia for region in regions)
        and not checks["africa_asia_land_contacts"]
    ):
        message = "The African land approach does not join a passable Asian location"
        raise NewWorldExportError(message)
    if southern_passage:
        checks["circumnavigation_sea_locations"] = int(np.unique(final[-1]).size)
    if complete_ocean:
        checks.update(_shared_ocean_boundaries(shared, shapes))
    return _ExportGeography(
        game_map,
        canvas,
        canvas,
        vanilla.moved,
        shapes,
        final,
        removed,
        store,
        attributes,
        _replaced_development(hierarchy, removed),
        calibration,
        geometry,
        hashes,
        keys,
        plan,
        checks,
        neighbours,
        biomes,
        biome_stats,
        rivers.result(),
        vanilla.levels,
        vanilla.natives,
        water_textures,
        vanilla_ports,
        training.locations,
        next((region.contact for region in regions if region.contact is not None), None),
    )


def _build_composed_start(  # noqa: PLR0913 - regional settings and the completed physical world.
    game_dir: Path,
    prepared: _ExportGeography,
    hierarchy: Mapping[str, Location],
    river_pixels: NDArray[np.int64],
    remap: GeographicRemap,
    *,
    settings: Settings,
    seed: int,
    real_america: VanillaWorld | None = None,
) -> ComposedStart:
    map_ = prepared.game_map
    world, plan, biomes = prepared.shape.coast.world, prepared.plan, prepared.biomes
    if real_america is not None:
        world, plan, biomes = real_america.world, real_america.plan, real_america.biomes
        river_pixels = real_america.river_pixels
    base = prepared.vanilla_start.result()
    if prepared.vanilla_locations is None:
        message = "Regional start needs installed population geography"
        raise NewWorldExportError(message)
    regions = settings.continents.regions
    profiles = regional_populations(
        game_dir, map_, prepared.vanilla_locations, prepared.attributes, {r.key for r in regions}
    )
    original = {
        key: (int(row), int(column))
        for key, row, column in zip(
            map_.keys, prepared.geometry.rows, prepared.geometry.columns, strict=True
        )
    }
    policy = next((region.morocco for region in regions if region.key == "africa"), None)
    morocco = None if policy is None else reserve_morocco(plan, world, original, policy)
    if morocco is not None and morocco.capital:
        remap = remap.with_locations({"fez": morocco.capital})
    rules = installed_rules(base)
    routes = shared_routes(world, plan, biomes, max_sea_steps=rules.max_sea_steps)
    starts: list[FinalStartPlan] = []
    calibrations: list[VanillaNatives] = []

    def add(start: FinalStartPlan, calibration: VanillaNatives) -> None:
        nonlocal base
        starts.append(start)
        calibrations.append(calibration)
        base = replace(
            base,
            reserved_tags=base.reserved_tags | {country.tag for country in start.countries},
            colors=base.colors | {country.color for country in start.countries},
        )

    if settings.continents.america:
        start = build_start_plan(
            world=world,
            plan=plan,
            biomes=biomes,
            river_pixels=river_pixels,
            vanilla=base,
            settings=settings.natives,
            seed=seed,
            loc_keys=prepared.loc_keys,
            algorithm=settings.algorithm,
            selection={i for i, cell in enumerate(plan.cells) if cell.continent == NEW_WORLD},
            routes=routes,
        )
        if real_america is not None:
            keys = _american_names(real_america, map_)
            start = replace(
                start,
                names={
                    key: reference(key)
                    for key in sorted(keys)
                    if key_hash(key) in prepared.vanilla_hashes
                },
            )
        add(start, base)
    for region in regions:
        name, knobs = region.key, region.natives
        held = morocco.africa if name == "africa" and morocco is not None else ()
        sacred = {
            site.name: remap.locations[site.location]
            for site in base.holy_sites
            if site.location in remap.locations and hierarchy[site.location].continent == name
        }
        calibration = regional_projection_inputs(base, profiles[name], name)
        boot = regional_societies(
            world,
            plan,
            biomes,
            river_pixels,
            continent=name,
            vanilla=profiles[name],
            settings=knobs,
            seed=derive_seed(seed, "peoples", name),
            reserved=held,
            routes=routes,
        )
        historical = simulate_region(
            plan,
            boot,
            routes,
            vanilla=profiles[name],
            settings=knobs,
            rules=rules,
            seed=derive_seed(seed, "history", name),
            reserved=held,
            sacred=sacred.values(),
        )
        add(
            project_regional_start(
                world,
                plan,
                boot,
                historical,
                vanilla=calibration,
                settings=knobs,
                holy_sites=sacred,
                loc_keys=prepared.loc_keys,
            ),
            calibration,
        )
    emirate = (
        algeciras(seed, base.reserved_tags, prepared.loc_keys, base.colors)
        if policy is MoroccoPolicy.EMIRATE
        else None
    )
    return ComposedStart(tuple(starts), remap, morocco, emirate, tuple(calibrations), real_america)


def _american_names(america: VanillaWorld, game_map: Eu5Map) -> frozenset[str]:
    keep = {game_map.keys[index] for index in america.keep}
    return frozenset(
        name
        for cell in america.plan.cells
        if cell.key in keep and cell.kind in {CellClass.LAND, CellClass.WASTELAND}
        for name in (cell.key, cell.area, cell.region)
    )


def _kept_american_ports(
    america: VanillaWorld, ports: Mapping[str, VanillaPort], height: int
) -> dict[int, tuple[int, int]]:
    """Retained docks keep their vanilla coordinates in the shared economy model."""
    return {
        index: (height - 1 - round(float(port.y)), round(float(port.x)))
        for index, cell in enumerate(america.plan.cells)
        if cell.continent == NEW_WORLD and cell.kind is CellClass.LAND
        if (port := ports.get(cell.key)) is not None
    }


def _campaign_scripts(  # noqa: PLR0913 - scenario scope, startup data and the files being written.
    game_dir: Path,
    prepared: _ExportGeography,
    *,
    settings: Settings,
    natives: FinalStartPlan,
    hierarchy: dict[str, Location],
    remap: GeographicRemap,
    removed_tags: set[str],
    texts: dict[str, bytes],
    text_stats: dict[str, object],
) -> dict[str, object]:
    """Rebind installed mechanics only to the geographical and political changes they read."""
    game_map, canvas, plan = prepared.game_map, prepared.canvas, prepared.plan
    geometry, world = prepared.geometry, prepared.shape.coast.world
    removed = prepared.removed
    composed = bool(settings.continents.regions)
    american_geography = settings.continents.america and not settings.new_world.keep_geography
    real_america = settings.continents.america and settings.new_world.keep_geography
    rewrite = run_stage("script remap", lambda: remap_scripts(game_dir, remap, removed_tags))
    footprint = (
        world_footprint(
            hierarchy.values(),
            continents={region.key for region in settings.continents.regions}
            | ({NEW_WORLD} if american_geography else set()),
            removed=removed,
            tags=removed_tags,
        )
        if composed
        else None
    )
    try:
        checked = check_decisions(
            game_dir,
            events=[event for found in rewrite.retired.values() for event in found],
            modifiers=[
                *rewrite.modifiers,
                *cast("list[str]", text_stats["base_modifiers_retired"]),
            ],
            removed_tags=removed_tags,
            footprint=footprint,
        )
    except ValueError as error:
        raise NewWorldExportError(str(error)) from error
    scripts = rewrite.outputs
    sites = remap
    if real_america:
        sites = remap.with_locations(
            {key: key for key in natives.holy_sites if key not in remap and key in hierarchy}
        )
    scripts.update(holy_site_outputs(game_dir, sites, natives.holy_sites))
    try:
        text_stats["content"] = carry_out(
            game_dir,
            scripts,
            checked,
            cohort_places(natives.pops),
            hierarchy,
            remap.with_locations({TENOCHTITLAN: TENOCHTITLAN}) if real_america else remap,
            sea_areas=sorted(
                {
                    cell.area
                    for cell in plan.cells
                    if cell.kind is CellClass.SEA and cell.continent == NEW_WORLD
                }
            ),
            american_geography=american_geography,
            american_societies=settings.continents.america,
            continents={cell.key: cell.continent for cell in plan.cells} if composed else None,
        )
    except ContentError as error:
        raise NewWorldExportError(str(error)) from error
    try:
        definitions = texts[_mod_path(DEFINITIONS)].decode("utf-8-sig")
        if american_geography:
            text_stats["treaty_longitudes"] = adapt_treaty(
                game_dir,
                scripts,
                treaty_coordinates(
                    game_map,
                    canvas=canvas,
                    world=world,
                    plan=plan,
                    geometry=geometry,
                    definitions=definitions,
                ),
            )
        present: Mapping[str, frozenset[str]] = _present_keys(plan)
        if composed:
            written_hierarchy = parse_locations(definitions)
            present = world_footprint(
                written_hierarchy,
                continents={location.continent for location in written_hierarchy},
                removed=set(),
                tags=set(),
            ).keys
        text_stats["script_outcomes"] = check_outcomes(game_dir, scripts, checked, present)
    except ValueError as error:
        raise NewWorldExportError(str(error)) from error
    texts.update(scripts)
    text_stats["scripts_remapped"] = rewrite.remapped
    text_stats["illustrations_dropped"] = rewrite.illustrations
    text_stats["monuments_dropped"] = rewrite.monuments
    text_stats["events_retired"] = {path: len(ids) for path, ids in rewrite.retired.items()}
    text_stats["event_modifiers_retired"] = list(rewrite.modifiers)
    return checked.stats()


def _export_new_world(  # noqa: C901, PLR0913, PLR0915 - one pass over every stage of the export.
    spool: Spool,
    recorder: inputs.InputRecorder,
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None,
    settings_file: str | None,
    world_code: str | None,
    world_label: Label | None,
    land_mask: LandMask | None,
    cache_dir: Path | None,
) -> dict[str, object]:
    _ = configure()
    _require_algorithm(settings)
    if settings.mask.id != (0 if land_mask is None else land_mask.id):
        message = (
            "The settings name a drawn land that was not given, or the given one is not it"
            if land_mask is None
            else "The land image is not the one the settings name (its id differs)"
        )
        raise NewWorldExportError(message)
    digest, build_label, accepted = resolve_build(game_dir, accept_build)
    spec = run_spec(seed, settings)
    resources_seed = layer_seed(seed, RESOURCES, settings.rolls.resources)
    peoples_seed = layer_seed(seed, PEOPLES, settings.rolls.peoples)
    origin = ""
    with suppress(WorldCodeError):
        origin = decode(world_code or "").origin
    named = world_label or worldname.label(
        settings.preset,
        worldname.fallback_tag(world_code or spec_digest(spec)),
        settings=settings,
        origin=origin,
    )

    def load() -> tuple[Eu5Map, dict[str, Location]]:
        loaded = load_map(game_dir)
        return loaded, {
            location.key: location for location in read_locations(game_dir / DEFINITIONS)
        }

    game_map, hierarchy = run_stage("load map", load)
    composed = bool(settings.continents.regions)
    with Stages(stage_workers()) as stages:
        prepare = _prepare_composed_geography if composed else _prepare_american_geography
        prepared = prepare(
            stages,
            spool,
            game_dir,
            game_map,
            hierarchy,
            seed=seed,
            resources_seed=resources_seed,
            settings=settings,
            land_mask=land_mask,
            cache_dir=cache_dir,
        )
        game_map, canvas, clean = prepared.game_map, prepared.canvas, prepared.cover_canvas
        shapes, final_labels, moved_groups = prepared.shape, prepared.final, prepared.moved
        coast = shapes.coast
        world = coast.world
        removed, store, vanilla_attributes = prepared.removed, prepared.store, prepared.attributes
        new_world_keys, calibration = prepared.new_world_keys, prepared.calibration
        geometry, vanilla_hashes = prepared.geometry, prepared.vanilla_hashes
        loc_keys, plan = prepared.loc_keys, prepared.plan
        world_checks, neighbours = prepared.checks, prepared.neighbours
        biomes, biome_stats = prepared.biomes, prepared.biome_stats
        river_codes, carved, river_stats = prepared.rivers
        levels, vanilla_start, water = (
            prepared.levels,
            prepared.vanilla_start,
            prepared.water_textures,
        )
        vanilla_ports = prepared.vanilla_ports
        terrain_contact = prepared.contact
        seam = (canvas.roll - canvas.col0) % canvas.shape[1]
        slot_tables, slot_stats = run_stage(
            "slot tables",
            lambda: _slot_tables(game_map, vanilla_attributes, biomes, game_dir, levels.result()),
        )
        biome_stats["materials"] = slot_stats

        def build_locations() -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
            return _rasters(game_map, canvas, world, plan, river_codes)

        locations = stages.submit("location rasters", build_locations)

        def encode_rasters() -> list[bytes]:
            rgb, rivers = locations.result()
            return [
                encode_png(pixels, color_type=color_type, compression="zlib", extra_chunks=chunks)
                for pixels, color_type, chunks in (
                    (rgb, COLOR_RGB, game_map.locations_chunks),
                    (rivers, COLOR_PALETTE, game_map.rivers_chunks),
                )
            ]

        encodings = stages.submit("png encoding", encode_rasters)

        def build_terrain() -> dict[str, object]:
            rivers = locations.result()[1]

            def decals() -> tuple[NDArray[np.uint8], dict[str, object]]:
                codes = _codes(game_map, canvas, world)
                vanilla_water = np.array(
                    [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes],
                    dtype=bool,
                )[game_map.labels]

                def relief_window(rows: slice, columns: slice) -> NDArray[np.int32]:
                    """Carved relief of a window of the world, zero off the canvas mask."""
                    world_columns = np.arange(columns.start, columns.stop, dtype=np.int64)
                    inside = (world_columns - canvas.col0 + canvas.roll) % canvas.shape[1]
                    valid = inside < canvas.mask.shape[1]
                    window = np.zeros((rows.stop - rows.start, world_columns.size), dtype=np.int32)
                    local = inside[valid]
                    window[:, valid] = np.where(
                        np.take(canvas.mask[rows], local, axis=1),
                        np.take(carved[rows], local, axis=1),  # noqa: F821 - deleted after the stages
                        0,
                    )
                    return window

                inputs = TerrainInputs(
                    codes=codes,
                    vanilla_water=vanilla_water,
                    relief=relief_window,
                    labels=final_labels,
                    rivers=rivers < RIVER_CLASSES,
                    noise_roll=seam,
                    mountains=mountain_relief(store, carved, seed=seed, column0=0),  # noqa: F821 - deleted after the stages
                    moved=moved_groups,
                    contact=terrain_contact,
                )
                return terrain_outputs(store, inputs, slot_tables, seed, spool)

            materials_world, terrain_stats = run_stage("terrain decals", decals)
            terrain_stats.update(water.result())
            canvas_world = np.zeros(game_map.labels.shape, dtype=bool)
            canvas.put(canvas_world, canvas.mask)
            pixel_classes, class_count, coarse_count = _pixel_classes(
                game_map, vanilla_attributes, biomes, final_labels, materials_world
            )
            terrain_stats["objects"] = run_stage(
                "vegetation instances",
                lambda: object_outputs(
                    game_dir,
                    classes=pixel_classes,
                    canvas=canvas_world,
                    class_count=class_count,
                    coarse_count=coarse_count,
                    seed=seed,
                    sink=spool,
                    moved=moved_groups,
                ),
            )
            return terrain_stats

        terraining = stages.submit("terrain", build_terrain)

        def prepare_geography() -> tuple[
            tuple[list[str], dict[int, tuple[int, int]]], GeographicRemap
        ]:
            if composed:
                return composed_bindings(
                    game_map,
                    canvas,
                    shapes,
                    plan,
                    hierarchy,
                    geometry=geometry,
                    removed=removed,
                    vanilla_ports=vanilla_ports,
                )
            ports = _ports(plan, world, canvas, coast.foreign, vanilla_ports)
            remap = build_remap(
                [
                    (
                        game_map.keys[i],
                        game_map.classes[i],
                        int(geometry.rows[i]),
                        int(geometry.columns[i]),
                    )
                    for i in np.flatnonzero(canvas.removed).tolist()
                    if game_map.keys[i] in removed
                ],
                plan,
                np.stack([world.centroids[:, 0], world.centroids[:, 1] + canvas.col0], axis=1),
                _removed_provinces(hierarchy, removed),
                areas=_removed_areas(hierarchy, removed, plan.dropped_areas),
                access=RemapAccess(
                    port_keys=frozenset(vanilla_ports),
                    port_cells=frozenset(ports[1]),
                    navigable_keys=frozenset(
                        key
                        for i, key in enumerate(game_map.keys)
                        if game_map.classes[i] is CellClass.SEA and not game_map.ambiguous[i]
                    ),
                    closed_seas=shapes.zones,
                ),
            )
            return ports, remap

        geographic = stages.prepare("ports and geographic remap", prepare_geography)
        river_pixels = np.bincount(
            world.labels[river_codes < RIVER_CLASSES].ravel(), minlength=len(world.classes) + 1
        )[: len(world.classes)].astype(np.int64)
        real_america = (
            run_stage(
                "vanilla Americas",
                lambda: with_real_americas(
                    game_map,
                    hierarchy,
                    vanilla_attributes,
                    final=final_labels,
                    generated=world,
                    plan=plan,
                    biomes=biomes,
                    height=store.world_heights(),
                    rivers=river_codes,
                ),
            )
            if composed and settings.continents.america and settings.new_world.keep_geography
            else None
        )
        society_plan = plan if real_america is None else real_america.plan
        society_world = world if real_america is None else real_america.world
        society_biomes = biomes if real_america is None else real_america.biomes
        society_rivers = river_pixels if real_america is None else real_america.river_pixels
        if real_america is not None:
            new_world_keys = new_world_keys | vanilla_new_world_keys(
                hierarchy, removed | {game_map.keys[i] for i in real_america.keep}
            )

        def prepare_natives() -> tuple[FinalStartPlan, ComposedStart | None]:
            if composed:
                start = _build_composed_start(
                    game_dir,
                    prepared,  # noqa: F821 - released once the export stages finish
                    hierarchy,
                    river_pixels,
                    geographic.result()[1],
                    settings=settings,
                    seed=peoples_seed,
                    real_america=real_america,
                )
                return combine_starts(start.histories), start
            return build_start_plan(
                world=world,
                plan=plan,
                biomes=biomes,
                river_pixels=river_pixels,
                vanilla=vanilla_start.result(),
                settings=settings.natives,
                seed=peoples_seed,
                loc_keys=loc_keys,
                algorithm=settings.algorithm,
            ), None

        natives, composed_start = run_stage("natives", prepare_natives)
        checkpoint()
        ports, remap = geographic.result()
        if composed_start is not None:
            remap = composed_start.remap
        docks = (
            ports[1]
            if real_america is None
            else ports[1] | _kept_american_ports(real_america, vanilla_ports, canvas.shape[0])
        )
        development = _plan_development(
            calibration,
            game_map=game_map,
            world=society_world,
            plan=society_plan,
            biomes=society_biomes,
            natives=natives,
            labels=final_labels,
            docks=docks,
            river_codes=river_codes if real_america is None else locations.result()[1],
        )
        atlas_json, atlas_png = run_stage(
            "atlas",
            lambda: atlas_files(
                build_atlas(
                    world=society_world,
                    plan=society_plan,
                    biomes=society_biomes,
                    natives=natives,
                    mask=canvas.mask if real_america is None else society_world.labels >= 0,
                    development=development.initial,
                )
            ),
        )
        texts, text_stats = run_stage(
            "texts",
            lambda: _text_outputs(
                game_dir,
                game_map=game_map,
                canvas=canvas,
                world=world,
                plan=plan,
                hierarchy=hierarchy,
                removed=removed,
                geometry=geometry,
                biomes=biomes,
                natives=natives,
                loc_keys=loc_keys,
                development=development,
                ports=ports,
                coast=coast,
                water=shapes,
                new_world_keys=new_world_keys,
                resources_seed=resources_seed,
                area_replacements={
                    key: remap.areas[key] for key in plan.dropped_areas if key in remap.areas
                },
                composed=composed_start,
            ),
        )
        spoken = (
            natives
            if real_america is None
            else replace(
                natives,
                names=natives.names
                | game_names(game_dir, "english", _american_names(real_america, game_map)),
            )
        )
        written = run_stage(
            "stories",
            lambda: _story_outputs(
                game_dir,
                plan=society_plan,
                world=society_world,
                natives=spoken,
                river_pixels=society_rivers,
                topography=society_biomes.topography,
                vanilla=vanilla_start.result(),
                loc_keys=loc_keys,
                seed=peoples_seed,
                composed=composed_start,
            ),
        )
        texts.update(written.files)
        text_stats["stories"] = written.stats
        revealed_continents = {
            region.key for region in settings.continents.regions if region.new_world.reveal_at_start
        }
        if settings.continents.america and settings.new_world.reveal_at_start:
            revealed_continents.add(NEW_WORLD)
        text_stats.update(
            _add_reveal(texts, enabled=bool(revealed_continents), continents=revealed_continents)
        )
        checkpoint()
        text_checks = verify_map_texts(texts, plan, canvas, shapes, removed)
        text_checks.update(_verify_natives(natives, society_plan))
        text_checks.update(
            verify_technology(texts, natives, vanilla_start.result(), composed=composed_start)
        )
        text_checks.update(
            verify_development(
                texts,
                society_plan,
                natives,
                development,
                calibration,
                new_world_keys,
                unchanged_geography=()
                if real_america is None
                else {game_map.keys[i] for i in real_america.keep},
            )
        )
        checkpoint()
        spline_data, spline_stats = run_stage(
            "spline network",
            lambda: _spline_outputs(
                game_dir,
                game_map=game_map,
                plan=plan,
                world=world,
                canvas=canvas,
                final=final_labels,
                hierarchy=hierarchy,
                texts=texts,
                natives=natives,
                real_america=real_america,
            ),
        )
        texts[SPLINE_FILE] = spline_data
        text_stats["splines"] = spline_stats
        removed_tags = _defined_tags(game_dir, {}) - _defined_tags(game_dir, texts)
        text_checks.update(
            verify_empires(
                texts,
                natives,
                society_plan,
                society_world,
                vanilla_start.result(),
                {
                    name: _read(game_dir, f"{SETUP_DIR}/{name}")
                    for name in ("09_roads.txt", "18_opinions.txt")
                },
                removed | removed_tags | (new_world_keys if real_america is not None else set()),
                composed=composed_start,
            )
        )
        text_checks.update(
            verify_archetypes(
                texts,
                natives,
                society_plan,
                vanilla_start.result(),
                {name: _read(game_dir, f"{SETUP_DIR}/{name}") for name in ARCHETYPE_FILES},
                removed | removed_tags | (new_world_keys if real_america is not None else set()),
                composed=composed_start,
            )
        )
        text_checks.update(
            _campaign_scripts(
                game_dir,
                prepared,
                settings=settings,
                natives=natives,
                hierarchy=hierarchy,
                remap=remap,
                removed_tags=removed_tags,
                texts=texts,
                text_stats=text_stats,
            )
        )
        checkpoint()
        text_checks.update(verify_country_tags(game_dir, texts))
        text_checks.update(verify_localization(texts, vanilla_hashes, game_dir=game_dir))
        try:
            text_checks.update(text_references.verify(texts, vanilla_hashes))
        except text_references.TextReferenceError as error:
            raise NewWorldExportError(str(error)) from error
        cover, cover_stats = run_stage(
            "selection cover",
            lambda: _cover_outputs(
                game_dir,
                game_map,
                world,
                final_labels,
                neighbours,
                _canvas_pixels(clean, final_labels),
            ),
        )
        texts.update(cover)
        text_stats["selection_cover"] = cover_stats
        rgb, rivers = locations.result()
        png_data = encodings.result()
        terrain_stats = terraining.result()
    # Nothing below reads these, yet they held 1 GiB until the function returned. Ruff
    # reads this del before the closures above that use them (the F821 noqa marks).
    del prepared, carved
    terrain_stats["rivers"] = river_stats
    name = output.name
    encoding = f"zlib level {ZLIB_LEVEL}, Up filter, zlib {zlib.ZLIB_RUNTIME_VERSION}"
    inputs = {record.path: record for record in game_map.inputs}
    with running("write files"), staged(output) as stage:
        files: list[dict[str, object]] = []
        for (relative, source, pixels, mode), data in zip(
            (
                ("in_game/map_data/locations.png", LOCATIONS, rgb, "RGB"),
                ("in_game/map_data/rivers.png", RIVERS, rivers, "P"),
            ),
            png_data,
            strict=True,
        ):
            record = write_bytes(stage, f"{name}/{relative}", data)
            record |= {
                "derived_from": source,
                "input_sha256": inputs[source].sha256,
                "pixels_sha256": pixel_digest(pixels, mode),
                "encoding": encoding,
            }
            files.append(record)
        for relative, data in sorted(texts.items()):
            files.append(write_bytes(stage, f"{name}/{relative}", data))
        files.extend(
            write_bytes(stage, f"{COVER_COPY}/{relative}", texts[relative])
            for relative in cover_files()
        )
        files.extend(spool.install(stage, name))
        files.append(
            write_bytes(
                stage,
                f"{name}/.metadata/metadata.json",
                mod_metadata(name, named.title, world_code),
            )
        )
        revealed, hidden = _previews(game_map, canvas, world, clean.mask)
        files.append(
            write_bytes(
                stage,
                f"{name}/.metadata/thumbnail.png",
                _preview(tagged(thumbnail(hidden, center_column(hidden)), named.tag)),
            )
        )
        decoded = open_png(stage / name / "in_game/map_data/locations.png", "RGB")
        named_colors = read_named_colors(
            stage / name / "in_game/map_data/named_locations/00_default.txt"
        )
        colors = np.array([color for _, color in named_colors], dtype=np.int64)
        written = labels_from_rgb(decoded, colors)
        if composed:
            world_checks["connected_new_location_colors"] = _connected_painted_cells(
                written, [key for key, _ in named_colors], plan
            )
        if not composed or (settings.continents.america and not settings.new_world.keep_geography):
            oceans = (
                frozenset(key for key in game_map.continents if key.endswith("_ocean_continent"))
                if composed
                else OCEANS
            )
            _check_written_contacts(
                stage / name / "in_game/map_data", written, game_map, canvas, oceans=oceans
            )
        del written
        vanilla = open_png(game_dir / LOCATIONS, "RGB")
        changed = differing_pixels(decoded, vanilla)
        del vanilla, decoded
        outside = changed.copy()
        canvas.put(outside, np.zeros(canvas.mask.shape, dtype=bool))
        outside[moved_pixels(canvas)] = False
        if plan.oceans is not None:
            plan.oceans.paint(outside, canvas, clear=True)
        if np.any(outside):
            message = "locations.png changed outside the New World canvas"
            raise NewWorldExportError(message)
        preview_record = write_bytes(stage, "preview.png", _preview(revealed))
        hidden_record = write_bytes(stage, "preview_hidden.png", _preview(hidden))
        settings_record = write_bytes(
            stage, "settings.json", canonical_json(spec["settings"]).encode()
        )
        atlas_records = [
            write_bytes(stage, ATLAS_JSON, atlas_json),
            write_bytes(stage, ATLAS_LABELS, atlas_png),
        ]
        if land_mask is not None:
            atlas_records.append(write_bytes(stage, LAND_MASK_FILE, land_mask.png()))
        record, inputs_record = _reproducibility(
            stage,
            recorder,
            game_dir,
            files,
            mod=name,
            seed=seed,
            settings=settings,
            spec=spec,
            game=(digest, build_label),
            world_code=world_code,
        )
        kinds = [cell.kind for cell in plan.cells]
        report: dict[str, object] = {
            "schema": 1,
            "status": STATUS,
            "tier": (
                "T3 candidate: generated New World with new location IDs and generated "
                "native societies in the 1337 start"
            ),
            "mod": name,
            "title": named.title,
            "land_mask": None
            if land_mask is None
            else {"id": land_mask.id, "sha256": land_mask.sha256, "size": list(land_mask.size)},
            "spec": spec,
            "spec_sha256": spec_digest(spec),
            "record": record.to_json(),
            "settings_source": settings_file or f"preset {settings.preset}",
            "build": {"fingerprint_sha256": digest, "label": build_label, "explicit": accepted},
            "canvas": {
                "pixels": int(np.count_nonzero(canvas.mask)),
                "removed_vanilla_locations": len(removed),
                "trimmed_ocean_zones": int(np.count_nonzero(canvas.trimmed)),
                "island_groups": len(canvas.groups),
                "island_groups_moved": sum(1 for move in canvas.moves if move != (0, 0)),
                "changed_pixels_on_disk": int(np.count_nonzero(changed)),
            },
            "generated": {
                "locations": sum(kind is CellClass.LAND for kind in kinds),
                "wastelands": sum(kind is CellClass.WASTELAND for kind in kinds),
                "sea_zones": sum(kind is CellClass.SEA for kind in kinds),
                "lakes": sum(kind is CellClass.LAKE for kind in kinds),
                "provinces": len({cell.province for cell in plan.cells}),
                "new_areas": len(plan.new_areas),
                "reused_areas": len({cell.area for cell in plan.cells} - set(plan.new_areas)),
                "regions": len({cell.region for cell in plan.cells}),
                "dropped_vanilla_areas": plan.dropped_areas,
                "sea_areas_grown_from_their_remainder": plan.anchored_sea_areas,
                "physical_keys": plan.physical_keys,
            },
            "invariants": {
                **world_checks,
                **text_checks,
                "outside_canvas_identical": plan.oceans is None or not plan.oceans.patches,
                "outside_canvas_except_ocean_identities_identical": True,
            },
            "text_stats": text_stats,
            "natives": natives.stats,
            "technology": natives.technology,
            "extraordinary": natives.extraordinary,
            "archetypes": natives.archetypes,
            "development": development.stats,
            "biomes": biome_stats,
            "terrain": terrain_stats,
            "files": [
                *files,
                preview_record,
                hidden_record,
                settings_record,
                inputs_record,
                *atlas_records,
            ],
            "inputs": [
                {"path": record.path, "size": record.size, "sha256": record.sha256}
                for record in game_map.inputs
            ],
            "untested_engine_behaviors": list(UNTESTED),
        }
        manifest = {
            key: report[key]
            for key in ("schema", "status", "spec_sha256", "record", "build", "inputs", "files")
        }
        _ = write_bytes(stage, "manifest.json", canonical_json(manifest).encode())
        _ = write_bytes(stage, "report.json", canonical_json(report).encode())
    return report


def _reproducibility(  # noqa: PLR0913 - what a record is made of
    stage: Path,
    recorder: inputs.InputRecorder,
    game_dir: Path,
    files: list[dict[str, object]],
    *,
    mod: str,
    seed: int,
    settings: Settings,
    spec: dict[str, object],
    game: tuple[str, str],
    world_code: str | None,
) -> tuple[Record, dict[str, object]]:
    """The world's reproducibility record (ADR 0010, G) and the file of inputs beside it.

    Called after the last read of the game: the recording ends here, and a read after it fails.
    The inputs are hashed with the cores the machine gives the export.
    """
    manifest = recorder.manifest(game_dir, workers=cores())
    entries = output_entries(files, mod)
    fingerprint, label = game
    record = Record(
        format=FORMAT,
        algorithm=settings.algorithm,
        release=__version__,
        code=world_code,
        preset=settings.preset,
        seed=seed,
        settings=cast("dict[str, object]", spec["settings"]),
        game=GameRecord(
            label=label,
            fingerprint_sha256=fingerprint,
            supported=SUPPORTED_GAME,
            inputs_sha256=manifest.digest,
            inputs_count=len(manifest.files),
        ),
        output_sha256=manifest_digest(entries),
        output_count=len(entries),
    )
    written = write_bytes(stage, INPUTS_FILE, record_json(manifest.to_json()).encode("ascii"))
    return record, written


def mod_metadata(name: str, title: str, world_code: str | None) -> bytes:
    """The mod's metadata: a complete map mod that names its world and how to make it again."""
    import json  # noqa: PLC0415

    code = f" World code: {world_code}." if world_code else ""
    payload: dict[str, object] = {
        "name": title,
        "id": name,
        "version": __version__,
        "supported_game_version": SUPPORTED_GAME,
        "short_description": (
            "A procedurally generated New World for Europa Universalis V, made with "
            f"Random New World Generator.{code} Play this map on its own; get the generator "
            "on Steam Workshop to create your own worlds."
        ),
        "tags": ["Map"],
        "picture": "thumbnail.png",
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def _codes(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> NDArray[np.int8]:
    """World-sized code map: -1 off the canvas, 0 generated water, 1 generated land."""
    codes = np.full(game_map.labels.shape, OUTSIDE, dtype=np.int8)
    table = np.array(
        [
            WATER_CODE if kind in {CellClass.SEA, CellClass.LAKE} else LAND_CODE
            for kind in world.classes
        ],
        dtype=np.int8,
    )
    canvas.put(codes, table[world.labels])
    return codes


def _vocabulary(values: list[str]) -> tuple[list[str], NDArray[np.int64]]:
    names = sorted(set(values))
    index = {name: number for number, name in enumerate(names)}
    return names, np.array([index[value] for value in values], dtype=np.int64)


def _final_field(
    game_map: Eu5Map, attributes: dict[str, dict[str, str]], generated: tuple[str, ...], name: str
) -> list[str]:
    return [attributes.get(key, {}).get(name, "") for key in game_map.keys] + list(generated)


def _old_world_land(game_map: Eu5Map) -> NDArray[np.bool_]:
    return np.array(
        [
            kind in {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
            and continent not in OCEANS
            and continent != NEW_WORLD
            for kind, continent in zip(game_map.classes, game_map.continents, strict=True)
        ],
        dtype=bool,
    )


@measured
def _vanilla_sizes(game_dir: Path, game_map: Eu5Map) -> SizeModel:
    """How large the game makes its land locations of each class (``eu5_biomes.size_model``),
    read from its map as it ships, before anything is moved or generated."""
    shape = (int(game_map.labels.shape[0]), int(game_map.labels.shape[1]))
    height = DecalStore(game_dir, shape).world_heights()
    return size_model(game_map, template_attributes(_read(game_dir, TEMPLATES)), height)


@dataclass(frozen=True, slots=True, eq=False)
class VanillaClimate:
    """What the biome model reads of the vanilla map; it does not depend on the generated world."""

    height: NDArray[np.uint16]
    locations: VanillaLocations
    grid: ClimateGrid


def _vanilla_climate(game_map: Eu5Map, store: DecalStore, *, seasonal: bool) -> VanillaClimate:
    """Vanilla heights, location statistics and climate grid (computed beside the world); with
    ``seasonal`` (epoch 64, ``epoch.OPEN_CLIMATE``) the rain of each season."""
    height = store.world_heights()
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    return VanillaClimate(
        height=height,
        locations=vanilla_locations(game_map.labels, height),
        grid=climate_grid(sea[game_map.labels], height, seasonal=seasonal),
    )


def _final_climate(
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    final_labels: NDArray[np.int32],
    vanilla: VanillaClimate,
) -> ClimateGrid:
    """The climate grid of the whole map as ``world`` shapes it: its sea and its relief, with
    the seasons when the vanilla grid has them."""
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    final_sea = np.concatenate(
        [sea, np.array([kind is CellClass.SEA for kind in world.classes], dtype=bool)]
    )
    height = vanilla.height.astype(np.int32)
    canvas.put(height, world.elevation)
    seasonal = vanilla.grid.winter is not None
    return climate_grid(final_sea[final_labels], height, seasonal=seasonal)


@measured
def _biome_model(  # noqa: PLR0913 - the biome model reads the map, the world and the vanilla climate.
    game_map: Eu5Map,
    *,
    canvas: Canvas,
    world: NewWorld,
    final_labels: NDArray[np.int32],
    vanilla: VanillaClimate,
    attributes: dict[str, dict[str, str]],
    seed: int,
    precious_permille: int = 1000,
    resources: ResourceSettings = RESOURCE_DEFAULTS,
    material_seed: int | None = None,
    land: tuple[CellBiomes, dict[str, object]] | None = None,
) -> tuple[CellBiomes, dict[str, object], ClimateGrid]:
    """Climate, vegetation, topography and raw material of every generated cell.

    With ``land`` (epoch 64 on) the land cells were made before the coasts (``_land_character``)
    and only the waters that remain get their climate here.
    """
    final_grid = _final_climate(game_map, canvas, world, final_labels, vanilla)
    cells = _generated(canvas, world)
    if land is None:
        biomes, stats = assign_biomes(
            game_map=game_map,
            templates=attributes,
            vanilla=vanilla.locations,
            vanilla_grid=vanilla.grid,
            final_grid=final_grid,
            cells=cells,
            seed=seed,
            precious_permille=precious_permille,
            resources=resources,
            material_seed=material_seed,
        )
    else:
        waters = water_climates(
            game_map,
            templates=attributes,
            vanilla=vanilla.locations,
            vanilla_grid=vanilla.grid,
            final_grid=final_grid,
            cells=cells,
        )
        biomes = _with_waters(land[0], waters, len(cells.kinds))
        stats = dict(land[1])
    stats["coherence"] = _coherence(game_map, attributes, vanilla.locations.pairs, world, biomes)
    return biomes, stats, final_grid


def _with_waters(land: CellBiomes, waters: dict[int, str], count: int) -> CellBiomes:
    """The biomes of the land cells (numbered first) and the climates of ``count - len(land)``
    water cells after them."""
    rest = count - len(land.climate)
    climate = [*land.climate, *[""] * rest]
    for cell, name in waters.items():
        climate[cell] = name
    blank = ("",) * rest
    return CellBiomes(
        tuple(climate),
        (*land.vegetation, *blank),
        (*land.topography, *blank),
        (*land.raw_material, *blank),
    )


def _coherence(
    game_map: Eu5Map,
    attributes: dict[str, dict[str, str]],
    pairs: NDArray[np.int64],
    world: NewWorld,
    biomes: CellBiomes,
) -> dict[str, object]:
    """Same-label edge share and region sizes of climate and vegetation, vanilla vs ours."""
    old = _old_world_land(game_map)
    low = (pairs >> np.int64(32)).astype(np.int64)
    high = (pairs & np.int64((1 << 32) - 1)).astype(np.int64)
    keep = old[low] & old[high]
    index = np.full(len(game_map.keys), -1, dtype=np.int64)
    members = np.flatnonzero(old)
    index[members] = np.arange(members.size)
    vanilla_edges = np.stack([index[low[keep]], index[high[keep]]], axis=1)
    land = [kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes]
    local = np.full(len(world.classes), -1, dtype=np.int64)
    generated_members = [i for i, flag in enumerate(land) if flag]
    local[generated_members] = np.arange(len(generated_members))
    generated_edges = np.array(
        [(local[a], local[b]) for a, b in world.edges if land[a] and land[b]], dtype=np.int64
    ).reshape(-1, 2)
    out: dict[str, object] = {}
    for name, values in (("climate", biomes.climate), ("vegetation", biomes.vegetation)):
        vanilla_values = [attributes.get(game_map.keys[i], {}).get(name, "") for i in members]
        out[name] = {
            "vanilla_old_world": label_statistics(vanilla_values, vanilla_edges),
            "generated": label_statistics([values[i] for i in generated_members], generated_edges),
        }
    return out


def _vanilla_level_counts(
    game_map: Eu5Map, attributes: dict[str, dict[str, str]], store: DecalStore
) -> dict[str, NDArray[np.int64]]:
    """Variation-level counts of the vanilla decals per ``vegetation|topography`` group."""
    topography = [attributes.get(key, {}).get("topography", "") for key in game_map.keys]
    vegetation = [attributes.get(key, {}).get("vegetation", "") for key in game_map.keys]
    water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
    )
    names, group = _vocabulary([f"{v}|{t}" for v, t in zip(vegetation, topography, strict=True)])
    counts = level_shares(store, game_map.labels, np.where(water, -1, group), len(names))
    return dict(zip(names, counts, strict=True))


def _slot_tables(
    game_map: Eu5Map,
    attributes: dict[str, dict[str, str]],
    biomes: CellBiomes,
    game_dir: Path,
    vanilla_counts: dict[str, NDArray[np.int64]],
) -> tuple[SlotTables, dict[str, object]]:
    """Per final label (vanilla, then generated) inputs of the material slot rules."""
    vanilla_count = len(game_map.keys)
    water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes]
        + [not value for value in biomes.vegetation],
        dtype=bool,
    )
    topography = _final_field(game_map, attributes, biomes.topography, "topography")
    vegetation = _final_field(game_map, attributes, biomes.vegetation, "vegetation")
    climate = _final_field(game_map, attributes, biomes.climate, "climate")
    _, topography_group = _vocabulary([TOPOGRAPHY_GROUPS.get(t, t) for t in topography])
    _, vegetation_id = _vocabulary(vegetation)
    _, climate_group = _vocabulary([CLIMATE_GROUPS.get(c, c) for c in climate])
    group_names, group = _vocabulary(
        [f"{v}|{t}" for v, t in zip(vegetation, topography, strict=True)]
    )
    no_levels = np.zeros(LEVELS, dtype=np.int64)
    counts = np.array([vanilla_counts.get(name, no_levels) for name in group_names]).reshape(
        len(group_names), LEVELS
    )
    by_vegetation: dict[str, NDArray[np.int64]] = {}
    for name, row in zip(group_names, counts, strict=True):
        key = name.split("|")[0]
        by_vegetation[key] = by_vegetation.get(key, np.zeros(LEVELS, dtype=np.int64)) + row
    overall = counts.sum(axis=0)
    shares = np.zeros((len(group_names), LEVELS), dtype=np.int64)
    for number, name in enumerate(group_names):
        row = counts[number]
        if row.sum() < MIN_LEVEL_PIXELS:
            row = by_vegetation.get(name.split("|")[0], overall)
        if row.sum() < MIN_LEVEL_PIXELS:
            row = overall
        shares[number] = row * 1000 // max(1, int(row.sum()))
    rules = biome_rules(_read(game_dir, BIOME_DEFINITIONS))
    lists = material_counts(_read(game_dir, TERRAIN_MATERIALS))
    resolved: dict[tuple[str, str, str], str] = {}
    materials = np.full(len(vegetation), SLOTS, dtype=np.int64)
    generated: Counter[str] = Counter()
    for label in range(vanilla_count, len(vegetation)):
        if water[label]:
            continue
        triple = (climate[label], vegetation[label], topography[label])
        if triple not in resolved:
            resolved[triple] = biome_of(rules, *triple)
        biome = resolved[triple]
        materials[label] = lists.get(biome, SLOTS)
        generated[biome] += 1
    tables = SlotTables(
        water=water,
        coast_slot=np.array([COAST_SLOTS.get(t, 0) for t in topography], dtype=np.int64),
        topography=topography_group,
        vegetation=vegetation_id,
        climate=climate_group,
        level_one=shares[group, 0],
        level_two=shares[group, 1],
        materials=materials,
    )
    short = materials[vanilla_count:][~water[vanilla_count:]]
    stats: dict[str, object] = {
        "generated_biomes": dict(sorted(generated.items())),
        "default_biome_locations": generated.get("default_biome", 0),
        "locations_by_material_count": {
            str(count): int(number)
            for count, number in zip(*np.unique(short, return_counts=True), strict=True)
        },
    }
    return tables, stats


def _pixel_classes(
    game_map: Eu5Map,
    attributes: dict[str, dict[str, str]],
    biomes: CellBiomes,
    labels: NDArray[np.int32],
    materials: NDArray[np.uint8],
) -> tuple[PixelClasses, int, int]:
    """Vegetation-object classes per final label: fine (vegetation, climate, topography)."""
    topography = _final_field(game_map, attributes, biomes.topography, "topography")
    vegetation = _final_field(game_map, attributes, biomes.vegetation, "vegetation")
    climate = _final_field(game_map, attributes, biomes.climate, "climate")
    vanilla_land = np.array(
        [kind in {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
         for kind in game_map.classes] + [bool(value) for value in biomes.vegetation]
    )  # fmt: skip
    fine_names, fine = _vocabulary(
        [
            f"{v}|{c}|{TOPOGRAPHY_GROUPS.get(t, t)}"
            for v, c, t in zip(vegetation, climate, topography, strict=True)
        ]
    )
    coarse_names, coarse = _vocabulary(vegetation)
    calibrate = np.concatenate([_old_world_land(game_map), np.zeros(len(biomes.vegetation), bool)])
    classes = PixelClasses(
        labels=labels,
        materials=materials,
        label_class=np.where(vanilla_land, fine, -1),
        label_coarse=np.where(vanilla_land, coarse, -1),
        calibrate=calibrate & vanilla_land,
    )
    return classes, len(fine_names), len(coarse_names)


def _previews(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, whole: NDArray[np.bool_]
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """The map at an eighth of its size with the New World drawn in, and with it covered.

    ``whole`` is the canvas before its island groups were placed. The covered picture hides all
    of it: the groups' holes in ``canvas.mask`` are where the vanilla islands stay or have moved
    to, which depends on the seed and would show as small uncovered discs of sea and islands.
    The drawn picture keeps the holes, where the vanilla map stands.
    """
    step = 8
    water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
    )
    small = game_map.labels[::step, ::step]
    sea_color = np.array([25, 45, 90], dtype=np.uint8)
    land_color = np.array([70, 110, 60], dtype=np.uint8)
    image = np.where(water[small][..., np.newaxis], sea_color, land_color).astype(np.uint8)
    palette = {
        CellClass.LAND: (96, 160, 72),
        CellClass.WASTELAND: (140, 140, 140),
        CellClass.SEA: (40, 75, 160),
        CellClass.LAKE: (90, 150, 220),
    }
    table = np.array([palette[kind] for kind in world.classes], dtype=np.uint8)
    rows, columns = np.nonzero(canvas.mask[::step, ::step])
    world_columns = _world_columns(canvas, columns.astype(np.int64) * step) // step
    covered_rows, covered_columns = np.nonzero(whole[::step, ::step])
    hidden = cover(
        image,
        covered_rows,
        _world_columns(canvas, covered_columns.astype(np.int64) * step) // step,
    )
    image[rows, world_columns] = table[world.labels[rows * step, columns * step]]
    return image, hidden
