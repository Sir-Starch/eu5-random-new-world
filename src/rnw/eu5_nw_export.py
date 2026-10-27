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
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw import __version__, epoch, inputs, landcache, worldname
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
from rnw.content import plan_content
from rnw.content_check import check_decisions, check_outcomes
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
    TERRAIN_MATERIALS,
    CellBiomes,
    ClimateGrid,
    Generated,
    VanillaLocations,
    assign_biomes,
    biome_of,
    biome_rules,
    climate_grid,
    label_statistics,
    material_counts,
    template_attributes,
    vanilla_locations,
)
from rnw.eu5_canvas import NEW_WORLD, OCEANS, Canvas, remainder_boxes, select_canvas
from rnw.eu5_content import ContentError, carry_out, culture_traits
from rnw.eu5_content import places as content_places
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
from rnw.eu5_lobby import (
    CONTEXT_MENU,
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
    hide_select_entry,
    land_colour,
    sampler_include,
    samplers_bound,
    scripted_gui_text,
    shader_indexes,
    shader_samplers,
    unknown_colour,
)
from rnw.eu5_lobby_gui import GUI_FILES, patch_gui
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
    labels_from_rgb,
    load_map,
    open_png,
    read_class_lists,
)
from rnw.eu5_mountains import mountain_relief
from rnw.eu5_natives import (
    COUNTRY_DIR,
    DEFINITION_FILE,
    Country,
    NativeWorld,
    VanillaNatives,
    build_natives,
    city_lines,
    country_definitions,
    country_names,
    country_records,
    holy_site_outputs,
    market_lines,
    new_tags,
    vanilla_natives,
    vassal_lines,
)
from rnw.eu5_newworld import Plan, VanillaGeometry, plan_identities, vanilla_geometry
from rnw.eu5_objects import PixelClasses, object_outputs
from rnw.eu5_oceans import emitted_cells, plan_oceans
from rnw.eu5_places import OUTPUT as OUTPUT_PLACES
from rnw.eu5_places import SPECS, Cells, Spec, choose, modifiers_file, payloads
from rnw.eu5_places import texts as place_texts
from rnw.eu5_regionkeys import physical_keys
from rnw.eu5_remap import RemapAccess, build_remap, remap_scripts, remap_text
from rnw.eu5_rewrite import (
    HierarchyAdditions,
    drop_block_entries,
    insert_into_block,
    prune_setup,
    rewrite_class_lists,
    rewrite_csv,
    rewrite_definitions,
    rewrite_locators,
    rewrite_named_colors,
    rewrite_override_locators,
    rewrite_templates,
)
from rnw.eu5_rivers import RiverRasterError, encode_rivers
from rnw.eu5_seas import (
    NO_UNITS,
    VFX_LOCATORS,
    Coast,
    SeaError,
    VanillaPort,
    Water,
    current_bands,
    current_text,
    read_ports,
    read_waters,
    settle_coast,
    shape_water,
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
from rnw.eu5_story import Written, facts_of
from rnw.eu5_story import build as build_stories
from rnw.eu5_technology import written_records
from rnw.eu5_terrain import (
    LAND_CODE,
    OUTSIDE,
    WATER_CODE,
    DecalStore,
    TerrainInputs,
    level_shares,
    terrain_outputs,
)
from rnw.eu5_towns import plan_towns
from rnw.eu5_treaty import adapt as adapt_treaty
from rnw.eu5_treaty import coordinates as treaty_coordinates
from rnw.eu5_water import water_outputs
from rnw.game_texts import Text, localize, untranslated
from rnw.geography import parse_locations, read_locations, read_named_colors
from rnw.landmask import LandMask, fit
from rnw.languages import official_languages
from rnw.layers import PEOPLES, RESOURCES, layer_seed
from rnw.loc_keys import KeySpace, key_hash, key_hashes
from rnw.model import CellClass
from rnw.newworld import (
    NewWorld,
    unported_cells,
)
from rnw.parallel import GIB, Stages, configure, cores, require_memory, stage_workers
from rnw.pdx import Block, parse
from rnw.pictures import center_column, cover, tagged, thumbnail
from rnw.png import COLOR_PALETTE, COLOR_RGB, ZLIB_LEVEL, encode_png
from rnw.ports import ForeignCoast, coast_links, pair_lengths, plan_ports
from rnw.progress import Progress, active, checkpoint, run_stage, running
from rnw.record import FORMAT, GameRecord, Record, manifest_digest, output_entries
from rnw.record import canonical as record_json
from rnw.relief import COAST_HEIGHT
from rnw.rivers import STEP as RIVER_STEP
from rnw.rivers import carve_valleys, flow_classes, generate_rivers, network_problems
from rnw.rng import derive_seed
from rnw.sea_corridors import designed_corridors
from rnw.seas import Shape
from rnw.settings import canonical_json, run_spec, spec_digest
from rnw.societies import STATE
from rnw.splnet import SplineError
from rnw.topology import adjacency_pairs, distance_from, label_components, unpack_pairs
from rnw.wording import render

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.game_texts import Entry
    from rnw.geography import Location
    from rnw.settings import Settings
    from rnw.wording import Name
    from rnw.worldname import Label

TEMPLATES: Final[str] = "game/in_game/map_data/location_templates.txt"
MAX_LOCATIONS: Final[int] = 32_000
RIVER_CLASSES: Final[int] = 16
# Vanilla uses widths 4, 5, 11 and 15 on 61.5%, 23.9%, 8.1% and 6.2% of Old World river
# pixels [V-EXEC C59]; valleys are cut in proportion (vanilla rivers lie a median 318
# and a quarter of them over 950 height units below the 17-pixel local mean).
RIVER_WIDTH_CODES: Final[tuple[int, ...]] = (4, 5, 11, 15)
RIVER_WIDTH_SHARES: Final[tuple[int, ...]] = (615, 239, 84, 62)
RIVER_VALLEY_DEPTHS: Final[tuple[int, ...]] = (350, 550, 850, 1150)
RIVER_VALLEY_PX: Final[int] = 6
MIN_LEVEL_PIXELS: Final[int] = 2000
SETUP_DIR: Final[str] = "game/main_menu/setup/1337"
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
# (6.8 GiB on the continents preset, C103), rounded up.
EXPORT_MEMORY: Final[int] = 7 * GIB + GIB // 2


class NewWorldExportError(ValueError):
    """Generated output failed an offline invariant."""


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
        water.crossings,
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
    return rows


def _ports(  # noqa: PLR0915 - port choice and dock placement share one pass.
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
    pairs: list[tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]] = []
    flat = labels.ravel()
    for offset in (1, width):
        a = flat[:-offset]
        b = flat[offset:]
        index = np.arange(flat.size - offset, dtype=np.int64)
        if offset == 1:
            index = index[(index % width) != width - 1]
            a, b = flat[index], flat[index + 1]
        forward = land[a] & sea[b]
        backward = sea[a] & land[b]
        pairs.append((a[forward].astype(np.int64), b[forward].astype(np.int64), index[forward]))
        pairs.append(
            (b[backward].astype(np.int64), a[backward].astype(np.int64), index[backward] + offset)
        )
    land_cells = np.concatenate([item[0] for item in pairs])
    sea_cells = np.concatenate([item[1] for item in pairs])
    pixels = np.concatenate([item[2] for item in pairs])
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
            distance = (candidates // width - centre[0]) ** 2 + (
                candidates % width - centre[1]
            ) ** 2
            pixel = int(candidates[int(np.argmin(distance))])
            row, column = divmod(pixel, width)
            x = int(_world_columns(canvas, np.array([column], dtype=np.int64))[0])
            dock_row, dock_column = row, column
            for d_row, d_column in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                r, c = row + d_row, column + d_column
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


def _localization(
    game_dir: Path,
    plan: Plan,
    extra: Mapping[str, Entry],
    renamed: Mapping[str, Name],
    languages: tuple[str, ...],
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
            files.update(map_name_files(game_dir, language, written))
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


def _cover_outputs(
    game_dir: Path,
    game_map: Eu5Map,
    world: NewWorld,
    final: NDArray[np.int32],
    neighbours: frozenset[int],
) -> tuple[dict[str, bytes], dict[str, object]]:
    """The files that cover the New World at country selection, and what the cover holds.

    The cover takes the generated locations and the ocean wastelands among their vanilla
    ``neighbours`` (``rnw.eu5_lobby``). The game's own files are changed where it decides what
    to draw and offer; a game whose files read otherwise, or whose shaders would not bind the
    cover's samplers, stops the export instead of leaving the cover half made.
    """
    patched = {
        edit.path: cover_shader(edit, _read(game_dir, edit.source_path or edit.path))
        for edit in SHADERS
    }
    gui_patched = {path: patch_gui(path, _read(game_dir, path)) for path in GUI_FILES}
    menu = hide_select_entry(_read(game_dir, CONTEXT_MENU))
    land = land_colour(_read(game_dir, GRAPHICS_DEFINES))
    shaders = {path: text for path, text in patched.items() if text is not None}
    broken = sorted(path for path in patched if path not in shaders)
    guis = {path: text for path, text in gui_patched.items() if text is not None}
    broken.extend(path for path in gui_patched if path not in guis)
    if menu is None:
        broken.append(CONTEXT_MENU)
    if land is None:
        broken.append(GRAPHICS_DEFINES)
    if broken or menu is None or land is None:
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
    grid = cover_grid(final, covered)
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
        _mod_path(CONTEXT_MENU): _encode(game_dir, CONTEXT_MENU, menu),
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


def _check_world(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, final: NDArray[np.int32]
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
    parts = label_components(world.labels)
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
    old_world = np.array(
        [name not in OCEANS and name != NEW_WORLD for name in continents], dtype=bool
    )
    lost = [
        pair
        for pair in before - after
        if not canvas.removed[pair[0]]
        and not canvas.removed[pair[1]]
        and (old_world[pair[0]] or old_world[pair[1]])
    ]
    if lost:
        message = f"{len(lost)} Old World contacts were lost, e.g. {lost[:3]}"
        raise NewWorldExportError(message)
    sea = np.concatenate(
        [
            np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool),
            np.array([kind is CellClass.SEA for kind in world.classes], dtype=bool),
        ]
    )
    neighbours: dict[int, list[int]] = {}
    for first, second in after:
        if sea[first] and sea[second]:
            neighbours.setdefault(first, []).append(second)
            neighbours.setdefault(second, []).append(first)
    start = [i for i in range(vanilla_count) if sea[i] and old_world[i] and not canvas.removed[i]]
    seen = set(start)
    queue = deque(start)
    while queue:
        for other in neighbours.get(queue.popleft(), []):
            if other not in seen:
                seen.add(other)
                queue.append(other)
    orphan = [i for i in range(vanilla_count, vanilla_count + count) if sea[i] and i not in seen]
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
        "land_cells_without_port_access": 0,
    }
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


def _setup_texts(game_dir: Path) -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8-sig")
        for path in sorted((game_dir / SETUP_DIR).glob("*.txt"))
    }


def _read(game_dir: Path, relative: str) -> str:
    return (game_dir / relative).read_text(encoding="utf-8-sig")


def _has_bom(game_dir: Path, relative: str) -> bool:
    return (game_dir / relative).read_bytes().startswith(b"\xef\xbb\xbf")


def _encode(game_dir: Path, relative: str, text: str) -> bytes:
    return text.encode("utf-8-sig" if _has_bom(game_dir, relative) else "utf-8")


def _mod_path(relative: str) -> str:
    return relative.removeprefix("game/")


def _ai_assignment_records(
    game_dir: Path, natives: NativeWorld, world: NewWorld, plan: Plan
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


def _ai_active_countries(natives: NativeWorld) -> dict[str, Country]:
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


def _ai_diplomacy(natives: NativeWorld, tags: set[str]) -> _AiDiplomacy:
    alliances = _ai_mutual_links(natives.alliances, tags)
    confederated_members: dict[str, set[str]] = {tag: set() for tag in tags}
    for group in natives.confederations:
        members = set(group) & tags
        for tag in members:
            confederated_members[tag].update(members - {tag})
            alliances[tag].update(members - {tag})
    rivals = _ai_mutual_links(natives.rivals, tags)
    threatened_by, prey_targets = _ai_opinion_links(natives.opinions, tags)
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
    natives: NativeWorld, world: NewWorld, plan: Plan
) -> tuple[CountryContext, ...]:
    """Summarize generated power, geography and diplomacy for the contextual classifier."""
    active = _ai_active_countries(natives)
    owner = {key: tag for tag, country in active.items() for key in country.members}
    tags = set(active)
    neighbors, coastal = _ai_geography(world, plan, owner, tags)
    diplomacy = _ai_diplomacy(natives, tags)
    market_locations = set(natives.markets)
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
    natives: NativeWorld,
    development: Development,
    ports: tuple[list[str], dict[int, tuple[int, int]]],
    coast: Coast,
    water: Water,
    new_world_keys: set[str],
    resources_seed: int,
    area_replacements: dict[str, str],
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
    kept_provinces = {hierarchy[key].province for key in hierarchy if key not in removed}
    removed_provinces = {hierarchy[key].province for key in removed if key in hierarchy}
    gone = removed | (removed_provinces - kept_provinces) | set(plan.dropped_areas)
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
        lists["impassable_mountains"].extend(cell.key for cell in plan.oceans.extra)
    outputs[_mod_path(DEFAULT_MAP)] = _encode(
        game_dir, DEFAULT_MAP, rewrite_class_lists(_read(game_dir, DEFAULT_MAP), removed, lists)
    )
    outputs[_mod_path(TEMPLATES)] = _encode(
        game_dir,
        TEMPLATES,
        rewrite_templates(
            _read(game_dir, TEMPLATES),
            removed,
            _template_lines(plan, donors, bodies, biomes, development.harbours, places, water),
        ),
    )
    outputs[_mod_path(PORTS)] = _encode(
        game_dir, PORTS, rewrite_csv(_read(game_dir, PORTS), removed, (0, 1), port_rows)
    )
    outputs[_mod_path(ADJACENCIES)] = _encode(
        game_dir,
        ADJACENCIES,
        rewrite_csv(
            _read(game_dir, ADJACENCIES), removed, (0, 1, 3), _crossing_rows(plan, canvas, water)
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
            game_dir, relative, rewrite_locators(text, relocated, fresh)
        )
    override = _read(game_dir, LOCATOR_OVERRIDE)
    if (rewritten := rewrite_override_locators(override, removed)) != override:
        outputs[_mod_path(LOCATOR_OVERRIDE)] = _encode(game_dir, LOCATOR_OVERRIDE, rewritten)
    setup = prune_setup(
        {
            name: remap_text(text, area_replacements)[0]
            for name, text in _setup_texts(game_dir).items()
        },
        gone,
        {c.key: natives.pops.get(c.key, []) for c in plan.cells},
    )
    ai_decisions = _ai_assignment_records(game_dir, natives, world, plan)
    ai_records = ai_assignments(ai_decisions)
    additions: dict[str, tuple[str, ...]] = {
        COUNTRIES_FILE: (country_records(natives.countries),),
        PERSONALITIES: (ai_personality_lines(ai_records),),
        BUILDINGS_FILE: (city_lines(towns.ranks), building_lines(development.villages)),
        "03_markets.txt": (market_lines(natives.markets),),
        "09_roads.txt": (road_lines(natives.roads),),
        "12_diplomacy.txt": (vassal_lines(natives.vassals), alliance_lines(natives.alliances)),
        "15_international_organizations.txt": (
            confederation_lines(natives.confederation_date, natives.confederations),
        ),
        DEVELOPMENT_FILE: (development_lines(development.terms),),
        "18_opinions.txt": (opinion_lines(natives.opinions),),
        "20_rivals.txt": (rival_lines(natives.rivals),),
    }
    for name, original_text in setup.texts.items():
        relative = f"{SETUP_DIR}/{name}"
        setup_text = original_text
        if name == DEVELOPMENT_FILE:
            setup_text = drop_block_entries(setup_text, ("development",), new_world_keys)
        setup_text = _insert_setup_additions(name, setup_text, additions, ai_records)
        if setup_text != _read(game_dir, relative):
            outputs[_mod_path(relative)] = _encode(game_dir, relative, setup_text)
    outputs.update(country_definition_outputs(game_dir, setup.removed_ids))
    outputs.update(towns.files())
    retired = retired_base_modifiers(bodies, removed)
    if retired:
        outputs[_mod_path(BASE_VALUES)] = _encode(
            game_dir, BASE_VALUES, drop_block_entries(_read(game_dir, BASE_VALUES), (), retired)
        )
    outputs[DEFINITION_FILE] = country_definitions(natives.countries)
    languages = official_languages(game_dir)
    if used:
        outputs[OUTPUT_PLACES] = modifiers_file(used, payloads(game_dir))
    outputs.update(
        _localization(
            game_dir,
            plan,
            {**country_names(natives.countries), **{key: Text(key) for key in place_texts(used)}},
            natives.names,
            languages,
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


def _story_outputs(  # noqa: PLR0913 - the stories read the world, the peoples and the installation.
    game_dir: Path,
    *,
    plan: Plan,
    world: NewWorld,
    natives: NativeWorld,
    river_pixels: NDArray[np.int64],
    topography: Sequence[str],
    vanilla: VanillaNatives,
    loc_keys: KeySpace,
    seed: int,
) -> Written:
    """The stories and formables of this world, as files and statistics (content plan, N3, N4)."""
    keys = [cell.key for cell in plan.cells]
    land = [index for index, cell in enumerate(plan.cells) if cell.kind is CellClass.LAND]
    inhabited = content_places(natives.pops)
    dominant = {place.key: place.religion for place in inhabited}
    traits = culture_traits(game_dir)
    cultures = {place.key: place.culture for place in inhabited}
    states = [
        (country.tag, country.members, country.capital, country.religion)
        for country in natives.countries
        if country.kind == STATE
    ]
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
    return build_stories(
        game_dir,
        content,
        names=natives.names,
        tags=tags,
        languages=official_languages(game_dir),
        seed=seed,
        taken=taken,
        regions=regions,
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


def _rivers(
    world: NewWorld, canvas: Canvas, climate: ClimateGrid, seed: int
) -> tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]]:
    """River codes for ``rivers.png`` and relief with carved valleys, in crop coordinates.

    Rain comes from the final climate grid (world coordinates) at each coarse river
    cell's centre. Codes follow the vanilla raster: 0 source, 1 join, then widths 4, 5,
    11 and 15 in vanilla proportions by catchment [V-EXEC C59].
    """
    land_kind = np.array(
        [kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes] + [False]
    )
    land = land_kind[world.labels]
    height, width_crop = land.shape
    world_width = canvas.shape[1]
    coarse_rows = -(-height // RIVER_STEP)
    coarse_columns = -(-width_crop // RIVER_STEP)
    centre_rows = np.arange(coarse_rows, dtype=np.int64) * RIVER_STEP + RIVER_STEP // 2
    centre_columns = np.arange(coarse_columns, dtype=np.int64) * RIVER_STEP + RIVER_STEP // 2
    grid_rows = np.clip(centre_rows // CLIMATE_STEP, 0, climate.rain.shape[0] - 1)
    grid_columns = np.clip(
        _world_columns(canvas, centre_columns) % world_width // CLIMATE_STEP,
        0,
        climate.rain.shape[1] - 1,
    )
    rain = climate.rain[grid_rows[:, np.newaxis], grid_columns[np.newaxis, :]]
    elevation = world.elevation
    rivers = generate_rivers(land, elevation, rain, seed=seed)
    classes = flow_classes(rivers, RIVER_WIDTH_SHARES)
    problems = network_problems(rivers.role, ~land)
    if any(problems.values()):
        message = f"generated rivers break the raster rules: {problems}"
        raise NewWorldExportError(message)
    try:
        codes, raster_stats = encode_rivers(
            rivers, classes, RIVER_WIDTH_CODES, seam=(canvas.roll - canvas.col0) % world_width
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


def referenced_words(path: str, text: str) -> set[str]:
    """Identifier-like words of a script text, without comments.

    Named colours count only their keys: a colour such as ``dabaca`` can spell a
    location key (vanilla has one) without referring to it.
    """
    text = re.sub(r"#[^\n]*", "", text)
    if path == _mod_path(NAMED_COLORS):
        text = "\n".join(line.split("=", 1)[0] for line in text.splitlines())
    return set(WORD.findall(text))


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


def vanilla_localization_keys(game_dir: Path) -> set[str]:
    """Every localization key of the installation, over all languages and DLC folders."""
    keys: set[str] = set()
    for root in LOC_ROOTS:
        for path in sorted((game_dir / root).rglob("*.yml")):
            if "localization" in path.parts:
                checkpoint()
                keys |= set(LOC_KEY.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    return keys


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


def _verify_natives(natives: NativeWorld, plan: Plan) -> dict[str, object]:
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
    records: dict[str, tuple[list[str], list[str]]], natives: NativeWorld, vanilla: VanillaNatives
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
        if levels[after[2]] < levels[before[2]]
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
    outputs: dict[str, bytes], natives: NativeWorld, vanilla: VanillaNatives
) -> dict[str, object]:
    """Every state writes a level of the vanilla set and a fitting template, a tribe none.

    Levels never fall along the rising complexity of the capitals (great empires apart), a
    template is at most the level and at most one below it, and a vassal lord has the level
    and the template to lead (C99).
    """
    text = outputs[_mod_path(f"{SETUP_DIR}/{COUNTRIES_FILE}")].decode("utf-8-sig")
    records = written_records(text, {country.tag for country in natives.countries})
    problems = _technology_problems(records, natives, vanilla)
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


def _relations(natives: NativeWorld, plan: Plan, world: NewWorld) -> _Relations:
    countries = {country.tag: country for country in natives.countries}
    empires = {tag: country.capital for tag, country in countries.items() if country.great}
    land = {cell.key for cell in plan.cells if cell.kind is CellClass.LAND}
    owner = {key: tag for tag, c in countries.items() if c.kind == "state" for key in c.members}
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
    countries_text: str, natives: NativeWorld, calibration: EmpireCalibration
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


def _road_problems(
    text: str,
    original: str,
    relations: _Relations,
    planned: tuple[tuple[str, str], ...],
    gone: set[str],
) -> list[str]:
    """Old World roads are vanilla's; new ones are planned, once, in contact, inside one empire."""
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
            or len(heads) != 1
            or not heads <= set(relations.empires)
        ):
            problems.append(f"Road {first} = {second} is not a contact inside one empire")
        else:
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


def _opinion_problems(
    text: str,
    original: str,
    relations: _Relations,
    planned: tuple[tuple[str, str, str], ...],
    gone: set[str],
) -> list[str]:
    """Old World opinions are vanilla's; new ones are planned, once and between related states."""
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
        if kind not in OPINION_TYPES or not _related(kind, first, second, relations)
    ]
    return problems


def _knowledge_problems(countries_text: str, natives: NativeWorld, plan: Plan) -> list[str]:
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
    natives: NativeWorld,
    plan: Plan,
    world: NewWorld,
    vanilla: VanillaNatives,
    originals: dict[str, str],
    gone: set[str],
) -> dict[str, object]:
    """Great empires write their level and rank, their roads and their opinions as planned.

    Only empires have a rank. Every road pair joins two generated land locations in contact
    that an empire or its vassals hold, once, and the roads of each empire reach its capital.
    Every opinion line joins an empire to a state in contact or to its vassal, once, and its
    holder has discovered the area of its partner's capital. Nothing
    names a vanilla tag or location, and the Old World entries of ``09_roads.txt`` and
    ``18_opinions.txt`` are vanilla's (``gone``: what the export removed). ``originals`` holds
    the two vanilla texts by file name; a world without empires leaves ``09_roads.txt`` unchanged
    and so out of ``outputs``.
    """

    def text(name: str) -> str:
        # A file the export left unchanged is not among the outputs and is vanilla's.
        path = _mod_path(f"{SETUP_DIR}/{name}")
        return outputs[path].decode("utf-8-sig") if path in outputs else originals[name]

    calibration = vanilla.empire
    relations = _relations(natives, plan, world)
    if calibration is None:
        problems = ["No empire calibration"] if relations.empires else []
    else:
        problems = [
            *_rank_problems(text(COUNTRIES_FILE), natives, calibration),
            *_road_problems(
                text("09_roads.txt"), originals["09_roads.txt"], relations, natives.roads, gone
            ),
            *_opinion_problems(
                text("18_opinions.txt"),
                originals["18_opinions.txt"],
                relations,
                natives.opinions,
                gone,
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
    natives: NativeWorld,
    plan: Plan,
    vanilla: VanillaNatives,
    originals: dict[str, str],
    gone: set[str],
) -> dict[str, object]:
    """The extraordinary societies write what the plan says, and only that (R7d).

    Every generated country writes the template, government, currency and holding it was planned
    with; every group is disjoint, of free countries and of one kind, with the relations that
    kind has; the alliances, rivalries and confederations of the setup files are the plan's, once
    each, beside the vanilla entries of the Old World; and the holder of a relation has discovered
    the area of its partner's capital. ``originals`` holds the vanilla texts by file name; a file
    the export left unchanged is not among the outputs and is vanilla's.
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
    natives: NativeWorld,
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
    contacts = world_contacts(game_map, plan, world, final)
    try:
        data, stats = build_splines(
            vanilla,
            vanilla_keys=vanilla_keys,
            mod_keys=mod_keys,
            contacts=contacts,
            anchors=world_anchors(game_map, plan, world, canvas, final),
            map_width=int(final.shape[1]),
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
        contacts=list(contacts),
        roads=[*roads, *natives.roads],
        map_width=int(final.shape[1]),
    )
    if problems:
        extra = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        message = f"Spline network: {problems[0]}{extra}"
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
        widths=RIVER_WIDTH_CODES,
        limit=RIVER_CLASSES,
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
    natives: NativeWorld,
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
        widths=RIVER_WIDTH_CODES,
        limit=RIVER_CLASSES,
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
    manager: Block | None, natives: NativeWorld, development: Development
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
    natives: NativeWorld,
    development: Development,
    calibration: DevelopmentCalibration,
    new_world_keys: set[str],
) -> dict[str, object]:
    """No positional development is left; terms, harbours and villages are as planned."""

    def text(relative: str) -> str:
        return outputs[_mod_path(relative)].decode("utf-8-sig")

    rules_text = text(f"{SETUP_DIR}/{DEVELOPMENT_FILE}")
    block = parse(rules_text).block("development")
    if block is None:
        message = "No development block in the output"
        raise NewWorldExportError(message)
    kept = sorted(entry.key for entry in block.entries if entry.key in new_world_keys)
    if kept:
        message = f"Development entry {kept[0]} of the vanilla New World was kept"
        raise NewWorldExportError(message)
    generated = {cell.key for cell in plan.cells}
    old = {k: v for k, v in calibration.rules.items() if k not in new_world_keys}
    if {k: v for k, v in development_rules(rules_text).items() if k not in generated} != old:
        message = "Development rules outside the New World differ from vanilla"
        raise NewWorldExportError(message)
    found = _verify_terms(block, plan, development, calibration)
    harbours = {k: v for k, v in template_harbours(text(TEMPLATES)).items() if k in generated}
    if harbours != development.harbours or not set(harbours.values()) <= set(calibration.harbours):
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
        message = f"{final_count} final location identities exceed the {MAX_LOCATIONS} safety cap"
        raise NewWorldExportError(message)


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


def _ocean_pixels(world: NewWorld) -> NDArray[np.bool_]:
    """The generated sea mask, in bounded strips and independent of cell numbers."""
    sea_class = np.array([kind is CellClass.SEA for kind in world.classes] + [False])
    ocean = np.empty(world.labels.shape, dtype=np.bool_)
    for first in range(0, ocean.shape[0], 1024):
        rows = slice(first, min(ocean.shape[0], first + 1024))
        ocean[rows] = sea_class[world.labels[rows]]
    return ocean


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
    named = world_label or worldname.label(
        settings.preset, worldname.fallback_tag(world_code or spec_digest(spec))
    )

    def load() -> tuple[Eu5Map, dict[str, Location]]:
        loaded = load_map(game_dir)
        return loaded, {
            location.key: location for location in read_locations(game_dir / DEFINITIONS)
        }

    game_map, hierarchy = run_stage("load map", load)
    canvas = run_stage(
        "select canvas",
        lambda: select_canvas(
            game_map,
            settings.new_world.ocean_band_px,
            expanded=bool(settings.new_world.expand_oceans),
        ),
    )
    width = int(game_map.labels.shape[1])
    seam = (canvas.roll - canvas.col0) % width
    removed = {game_map.keys[index] for index in np.flatnonzero(canvas.removed).tolist()}
    with Stages(stage_workers()) as stages:
        # Everything that reads only the vanilla game runs beside the generation of the world.
        def read_vanilla() -> tuple[
            DecalStore, dict[str, dict[str, str]], set[str], DevelopmentCalibration
        ]:
            store = DecalStore(game_dir, (int(game_map.labels.shape[0]), width))
            return (
                store,
                template_attributes(_read(game_dir, TEMPLATES)),
                vanilla_new_world_keys(hierarchy, removed),
                calibrate_development(game_dir, game_map, hierarchy),
            )

        reads = stages.submit("vanilla reads", read_vanilla)
        geometries = stages.submit(
            "vanilla geometry", lambda: vanilla_geometry(game_map, canvas, hierarchy)
        )
        localization = stages.submit(
            "vanilla localization keys", lambda: key_hashes(vanilla_localization_keys(game_dir))
        )
        climates = stages.submit(
            "vanilla climate", lambda: _vanilla_climate(game_map, reads.result()[0])
        )
        levels = stages.submit(
            "vanilla material levels",
            lambda: _vanilla_level_counts(game_map, reads.result()[1], reads.result()[0]),
        )
        vanilla_start = stages.submit(
            "vanilla natives",
            lambda: vanilla_natives(
                game_dir, game_map, geometries.result(), reads.result()[1], hierarchy
            ),
        )
        vanilla_waters = read_waters(_read(game_dir, TEMPLATES))
        bands = current_bands(game_map, canvas, vanilla_waters)
        world = run_stage(
            "generate world",
            lambda: landcache.get_world(
                cache_dir,
                canvas.mask,
                seed=seed,
                settings=settings.new_world,
                drawn=None if land_mask is None else fit(land_mask, canvas.mask.shape),
                sea_bands=bands,
            ),
        )
        # The corridor planner depends on the physical water mask, not on cell
        # identities. Recompute it on cached worlds as well as freshly made ones.
        ocean = _ocean_pixels(world)
        designed = designed_corridors(ocean, bands, settings.new_world.sea_zone_px)
        del ocean
        vanilla_ports = read_ports(_read(game_dir, PORTS))
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
        total = len(game_map.keys) - int(np.count_nonzero(canvas.removed)) + len(world.classes)
        if total > MAX_LOCATIONS:
            message = (
                f"{total} locations exceed the {MAX_LOCATIONS} safety cap (vanilla has under "
                "28,600; a 16-bit limit is suspected); raise location_px or sea_zone_px"
            )
            raise NewWorldExportError(message)
        final_labels = _final_labels(game_map, canvas, world)

        def identify() -> tuple[KeySpace, Plan]:
            loc_keys = KeySpace(localization.result())
            geometry = geometries.result()
            physical = physical_keys(
                game_map,
                hierarchy,
                reads.result()[1],
                unpack_pairs(climates.result().locations.pairs),
                world=world,
                biomes=weathering.result()[0],
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
                biomes=weathering.result()[0],
            )
            if settings.new_world.expand_oceans:
                plan.oceans = plan_oceans(
                    game_map, canvas, world, plan, hierarchy, shapes.zones, loc_keys
                )
            return loc_keys, plan

        def build_water() -> dict[str, int]:
            """The water textures need only the generated world, so they are built early."""
            codes = _codes(game_map, canvas, world)
            canvas_world = codes != OUTSIDE
            vanilla_water = np.array(
                [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
            )[game_map.labels]
            new_water = vanilla_water.copy()
            new_water[canvas_world] = codes[canvas_world] == WATER_CODE
            files, stats = water_outputs(game_dir, vanilla_water, new_water, canvas_world, seed)
            spool.update(files)
            return stats

        water = stages.submit("water textures", build_water)
        checks = stages.submit(
            "world checks", lambda: _check_world(game_map, canvas, world, final_labels)
        )

        def weather() -> tuple[
            CellBiomes,
            dict[str, object],
            tuple[NDArray[np.uint8], NDArray[np.int32], dict[str, object]],
        ]:
            biomes, biome_stats, climate = _biome_model(
                game_map,
                canvas=canvas,
                world=world,
                final_labels=final_labels,
                vanilla=climates.result(),
                attributes=reads.result()[1],
                seed=seed,
                precious_permille=settings.new_world.precious_permille,
                material_seed=resources_seed,
            )
            return biomes, biome_stats, _rivers(world, canvas, climate, seed)

        weathering = stages.submit("biomes and rivers", weather)
        identities = stages.submit("identities", identify)
        store, vanilla_attributes, new_world_keys, calibration = reads.result()
        geometry = geometries.result()
        vanilla_hashes = localization.result()
        loc_keys, plan = identities.result()
        if plan.oceans is not None:
            removed -= plan.oceans.retained
        _check_identity_budget(game_map, removed, plan)
        biomes, biome_stats, (river_codes, carved, river_stats) = weathering.result()
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
                        canvas.mask[rows][:, local], carved[rows][:, local], 0
                    )
                    return window

                inputs = TerrainInputs(
                    codes=codes,
                    vanilla_water=vanilla_water,
                    relief=relief_window,
                    labels=final_labels,
                    rivers=rivers < RIVER_CLASSES,
                    noise_roll=seam,
                    mountains=mountain_relief(store, carved, seed=seed, column0=0),
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
                ),
            )
            return terrain_stats

        terraining = stages.submit("terrain", build_terrain)
        river_pixels = np.bincount(
            world.labels[river_codes < RIVER_CLASSES].ravel(), minlength=len(world.classes) + 1
        )[: len(world.classes)]
        natives = run_stage(
            "natives",
            lambda: build_natives(
                world=world,
                plan=plan,
                biomes=biomes,
                river_pixels=river_pixels.astype(np.int64),
                vanilla=vanilla_start.result(),
                settings=settings.natives,
                seed=peoples_seed,
                loc_keys=loc_keys,
            ),
        )
        atlas_json, atlas_png = run_stage(
            "atlas",
            lambda: atlas_files(
                build_atlas(
                    world=world, plan=plan, biomes=biomes, natives=natives, mask=canvas.mask
                )
            ),
        )
        checkpoint()
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
        development = _plan_development(
            calibration,
            game_map=game_map,
            world=world,
            plan=plan,
            biomes=biomes,
            natives=natives,
            labels=final_labels,
            docks=ports[1],
            river_codes=river_codes,
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
                development=development,
                ports=ports,
                coast=coast,
                water=shapes,
                new_world_keys=new_world_keys,
                resources_seed=resources_seed,
                area_replacements={key: remap[key] for key in plan.dropped_areas if key in remap},
            ),
        )
        written = run_stage(
            "stories",
            lambda: _story_outputs(
                game_dir,
                plan=plan,
                world=world,
                natives=natives,
                river_pixels=river_pixels.astype(np.int64),
                topography=biomes.topography,
                vanilla=vanilla_start.result(),
                loc_keys=loc_keys,
                seed=peoples_seed,
            ),
        )
        texts.update(written.files)
        text_stats["stories"] = written.stats
        checkpoint()
        text_checks = _verify_texts(texts, plan, removed)
        try:
            text_checks.update(
                verify_seas(
                    (
                        texts[_mod_path(PORTS)].decode("utf-8-sig"),
                        texts[_mod_path(TEMPLATES)].decode("utf-8-sig"),
                        texts[_mod_path(DEFAULT_MAP)].decode("utf-8-sig"),
                    ),
                    plan,
                    world,
                    coast,
                    shapes,
                )
            )
            text_checks.update(
                verify_locators(
                    {
                        name: texts[_mod_path(f"{MAP_OBJECTS}/{name}")].decode("utf-8-sig")
                        for name in (*NO_UNITS, VFX_LOCATORS)
                    },
                    plan,
                    shapes,
                    all_locations=frozenset(
                        location.key
                        for location in parse_locations(
                            texts[_mod_path(DEFINITIONS)].decode("utf-8-sig")
                        )
                    ),
                )
            )
            text_checks.update(
                verify_crossings(
                    texts[_mod_path(ADJACENCIES)].decode("utf-8-sig"),
                    plan,
                    world,
                    canvas,
                    shapes.crossings,
                )
            )
        except SeaError as error:
            raise NewWorldExportError(str(error)) from error
        text_checks.update(_verify_natives(natives, plan))
        text_checks.update(verify_technology(texts, natives, vanilla_start.result()))
        text_checks.update(
            verify_development(texts, plan, natives, development, calibration, new_world_keys)
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
            ),
        )
        texts[SPLINE_FILE] = spline_data
        text_stats["splines"] = spline_stats
        removed_tags = _defined_tags(game_dir, {}) - _defined_tags(game_dir, texts)
        text_checks.update(
            verify_empires(
                texts,
                natives,
                plan,
                world,
                vanilla_start.result(),
                {
                    name: _read(game_dir, f"{SETUP_DIR}/{name}")
                    for name in ("09_roads.txt", "18_opinions.txt")
                },
                removed | removed_tags,
            )
        )
        text_checks.update(
            verify_archetypes(
                texts,
                natives,
                plan,
                vanilla_start.result(),
                {name: _read(game_dir, f"{SETUP_DIR}/{name}") for name in ARCHETYPE_FILES},
                removed | removed_tags,
            )
        )
        rewrite = run_stage("script remap", lambda: remap_scripts(game_dir, remap, removed_tags))
        try:
            checked = check_decisions(
                game_dir,
                events=[event for found in rewrite.retired.values() for event in found],
                modifiers=[
                    *rewrite.modifiers,
                    *cast("list[str]", text_stats["base_modifiers_retired"]),
                ],
                removed_tags=removed_tags,
            )
        except ValueError as error:
            raise NewWorldExportError(str(error)) from error
        text_checks.update(checked.stats())
        scripts = rewrite.outputs
        scripts.update(holy_site_outputs(game_dir, remap, natives.holy_sites))
        try:
            text_stats["content"] = carry_out(
                game_dir,
                scripts,
                checked,
                natives.pops,
                hierarchy,
                remap,
                sea_areas=sorted(
                    {
                        cell.area
                        for cell in plan.cells
                        if cell.kind is CellClass.SEA and cell.continent == NEW_WORLD
                    }
                ),
            )
        except ContentError as error:
            raise NewWorldExportError(str(error)) from error
        try:
            text_stats["treaty_longitudes"] = adapt_treaty(
                game_dir,
                scripts,
                treaty_coordinates(
                    game_map,
                    canvas=canvas,
                    world=world,
                    plan=plan,
                    geometry=geometry,
                    definitions=texts[_mod_path(DEFINITIONS)].decode("utf-8-sig"),
                ),
            )
            text_stats["script_outcomes"] = check_outcomes(
                game_dir, scripts, checked, _present_keys(plan)
            )
        except ValueError as error:
            raise NewWorldExportError(str(error)) from error
        texts.update(scripts)
        checkpoint()
        text_checks.update(verify_country_tags(game_dir, texts))
        text_checks.update(verify_localization(texts, vanilla_hashes, game_dir=game_dir))
        text_stats["scripts_remapped"] = rewrite.remapped
        text_stats["illustrations_dropped"] = rewrite.illustrations
        text_stats["monuments_dropped"] = rewrite.monuments
        text_stats["events_retired"] = {path: len(ids) for path, ids in rewrite.retired.items()}
        text_stats["event_modifiers_retired"] = list(rewrite.modifiers)
        world_checks, neighbours = checks.result()
        cover, cover_stats = run_stage(
            "selection cover",
            lambda: _cover_outputs(game_dir, game_map, world, final_labels, neighbours),
        )
        texts.update(cover)
        text_stats["selection_cover"] = cover_stats
        rgb, rivers = locations.result()
        png_data = encodings.result()
        terrain_stats = terraining.result()
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
        revealed, hidden = _previews(game_map, canvas, world)
        files.append(
            write_bytes(
                stage,
                f"{name}/.metadata/thumbnail.png",
                _preview(tagged(thumbnail(hidden, center_column(hidden)), named.tag)),
            )
        )
        decoded = open_png(stage / name / "in_game/map_data/locations.png", "RGB")
        colors = np.array(
            [
                color
                for _, color in read_named_colors(
                    stage / name / "in_game/map_data/named_locations/00_default.txt"
                )
            ],
            dtype=np.int64,
        )
        _ = labels_from_rgb(decoded, colors)
        vanilla = open_png(game_dir / LOCATIONS, "RGB")
        changed = np.any(decoded != vanilla, axis=2)
        del vanilla, decoded
        outside = changed.copy()
        canvas.put(outside, np.zeros(canvas.mask.shape, dtype=bool))
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
        algorithm=epoch.CURRENT,
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


@dataclass(frozen=True, slots=True, eq=False)
class VanillaClimate:
    """What the biome model reads of the vanilla map; it does not depend on the generated world."""

    height: NDArray[np.uint16]
    locations: VanillaLocations
    grid: ClimateGrid


def _vanilla_climate(game_map: Eu5Map, store: DecalStore) -> VanillaClimate:
    """Vanilla heights, location statistics and climate grid (computed beside the world)."""
    height = store.world_heights()
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    return VanillaClimate(
        height=height,
        locations=vanilla_locations(game_map.labels, height),
        grid=climate_grid(sea[game_map.labels], height),
    )


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
    material_seed: int | None = None,
) -> tuple[CellBiomes, dict[str, object], ClimateGrid]:
    """Climate, vegetation, topography and raw material of every generated cell."""
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    final_sea = np.concatenate(
        [sea, np.array([kind is CellClass.SEA for kind in world.classes], dtype=bool)]
    )
    height = vanilla.height.astype(np.int32)
    canvas.put(height, world.elevation)
    final_grid = climate_grid(final_sea[final_labels], height)
    del height
    points = np.stack(
        [world.centroids[:, 0], _world_columns(canvas, world.centroids[:, 1])], axis=1
    )
    cells = Generated(
        kinds=world.classes,
        points=points,
        mean_height=world.mean_elevation,
        spread=world.spread,
        edges=world.edges,
        coastal=_coastal(world),
    )
    biomes, stats = assign_biomes(
        game_map=game_map,
        templates=attributes,
        vanilla=vanilla.locations,
        vanilla_grid=vanilla.grid,
        final_grid=final_grid,
        cells=cells,
        seed=seed,
        precious_permille=precious_permille,
        material_seed=material_seed,
    )
    stats["coherence"] = _coherence(game_map, attributes, vanilla.locations.pairs, world, biomes)
    return biomes, stats, final_grid


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
    game_map: Eu5Map, canvas: Canvas, world: NewWorld
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """The map at an eighth of its size with the New World drawn in, and with it covered."""
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
    hidden = cover(image, rows, world_columns)
    image[rows, world_columns] = table[world.labels[rows * step, columns * step]]
    return image, hidden
