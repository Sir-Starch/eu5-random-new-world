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
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import __version__
from rnw.artifacts import check_new_output, pixel_digest, staged, write_bytes
from rnw.eu5_biomes import (
    BIOME_DEFINITIONS,
    CLIMATE_STEP,
    TERRAIN_MATERIALS,
    CellBiomes,
    ClimateGrid,
    Generated,
    assign_biomes,
    biome_of,
    biome_rules,
    climate_grid,
    label_statistics,
    material_counts,
    template_attributes,
    vanilla_locations,
)
from rnw.eu5_canvas import NEW_WORLD, OCEANS, Canvas, select_canvas
from rnw.eu5_development import (
    VILLAGE,
    Development,
    DevelopmentCalibration,
    build_development,
    building_lines,
    calibrate,
    development_lines,
    hundredths_text,
    shelter,
    template_harbours,
)
from rnw.eu5_export import MOD_NAME, STATUS, resolve_build
from rnw.eu5_map import (
    ADJACENCIES,
    DEFAULT_MAP,
    DEFINITIONS,
    LOCATIONS,
    LOCATOR_FILES,
    LOCATOR_OVERRIDE,
    NAMED_COLORS,
    PORTS,
    RIVER_LAND,
    RIVER_WATER,
    RIVERS,
    Eu5Map,
    labels_from_rgb,
    load_map,
    open_png,
)
from rnw.eu5_natives import (
    DEFINITION_FILE,
    NativeWorld,
    build_natives,
    city_lines,
    country_definitions,
    country_names,
    country_records,
    holy_site_outputs,
    market_lines,
    vanilla_natives,
    vassal_lines,
)
from rnw.eu5_newworld import Plan, VanillaGeometry, plan_identities, vanilla_geometry
from rnw.eu5_objects import PixelClasses, object_outputs
from rnw.eu5_remap import build_remap, remap_scripts
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
from rnw.eu5_slots import (
    CLIMATE_GROUPS,
    COAST_SLOTS,
    LEVELS,
    SLOTS,
    TOPOGRAPHY_GROUPS,
    SlotTables,
)
from rnw.eu5_terrain import (
    LAND_CODE,
    OUTSIDE,
    WATER_CODE,
    DecalStore,
    TerrainInputs,
    level_shares,
    terrain_outputs,
)
from rnw.eu5_water import water_outputs
from rnw.geography import parse_locations, read_locations, read_named_colors
from rnw.model import CellClass
from rnw.newworld import NewWorld, generate_new_world, split_at_column
from rnw.pdx import Block, parse
from rnw.png import COLOR_PALETTE, COLOR_RGB, ZLIB_LEVEL, encode_png
from rnw.relief import COAST_HEIGHT
from rnw.rivers import JOIN, SOURCE, carve_valleys, flow_classes, generate_rivers, network_problems
from rnw.rivers import STEP as RIVER_STEP
from rnw.settings import canonical_json, run_spec, spec_digest
from rnw.topology import adjacency_pairs, distance_from, label_components, unpack_pairs

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.geography import Location
    from rnw.settings import Settings

TEMPLATES: Final[str] = "game/in_game/map_data/location_templates.txt"
MAX_LOCATIONS: Final[int] = 32_000
RIVER_CLASSES: Final[int] = 16
RIVER_SOURCE: Final[int] = 0
RIVER_JOIN: Final[int] = 1
# Vanilla uses widths 4, 5, 11 and 15 on 61.5%, 23.9%, 8.1% and 6.2% of Old World river
# pixels [V-EXEC C59]; valleys are cut in proportion (vanilla rivers lie a median 318
# and a quarter of them over 950 height units below the 17-pixel local mean).
RIVER_WIDTH_CODES: Final[tuple[int, ...]] = (4, 5, 11, 15)
RIVER_WIDTH_SHARES: Final[tuple[int, ...]] = (615, 239, 84, 62)
RIVER_VALLEY_DEPTHS: Final[tuple[int, ...]] = (350, 550, 850, 1150)
RIVER_VALLEY_PX: Final[int] = 6
MIN_LEVEL_PIXELS: Final[int] = 2000
SETUP_DIR: Final[str] = "game/main_menu/setup/1337"
LOCALIZATION_DIR: Final[str] = "game/main_menu/localization"
LANGUAGES: Final[tuple[str, ...]] = (
    "braz_por",
    "english",
    "french",
    "german",
    "japanese",
    "korean",
    "polish",
    "russian",
    "simp_chinese",
    "spanish",
)
ROTATION: Final[str] = "{ -0.000000 -0.000000 -0.000000 1.000000 }"
SCALE: Final[str] = "{ 1.000000 1.000000 1.000000 }"
TOPOGRAPHY: Final[re.Pattern[str]] = re.compile(r"topography\s*=\s*[A-Za-z_]+")
HARBOR: Final[re.Pattern[str]] = re.compile(r"\s*natural_harbor_suitability\s*=\s*-?[0-9.]+")
CURRENTS: Final[re.Pattern[str]] = re.compile(r"\s*movement_assistance\s*=\s*\{[^{}]*\}")
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
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
    (
        "Display-name overrides for reused area/region keys use a replace/ folder; whether "
        "EU5 honours it is unknown."
    ),
    "Colonisation, exploration, movement, naval routes, ports, save/load and startup time.",
    (
        "Development entries keyed by generated location keys, per-port harbour values and "
        "market villages in generated state capitals are untested; so is the estimate in "
        "the report (the river term is left out)."
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
# Blocks of the 1337 setup files that receive generated records, in the order of
# their additions in ``_text_outputs``.
SETUP_INSERTS: Final[dict[str, tuple[tuple[str, ...], ...]]] = {
    "10_countries.txt": (("countries", "countries"),),
    BUILDINGS_FILE: (("locations",), ("building_manager",)),
    "03_markets.txt": (("market_manager",),),
    "12_diplomacy.txt": (("diplomacy_manager",),),
    DEVELOPMENT_FILE: (("development",),),
}


class NewWorldExportError(ValueError):
    """Generated output failed an offline invariant."""


def _world_columns(canvas: Canvas, columns: NDArray[np.int64]) -> NDArray[np.int64]:
    width = int(canvas.rolled.shape[1])
    return (columns + canvas.col0 - canvas.roll) % width


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
    world: NewWorld,
    donors: list[str],
    bodies: dict[str, str],
    biomes: CellBiomes,
    harbours: dict[str, int],
) -> list[str]:
    coastal = _coastal(world)
    lines: list[str] = []
    for index, cell in enumerate(plan.cells):
        body = bodies[donors[index]]
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
        elif cell.kind is CellClass.SEA:
            kind = "coastal_ocean" if coastal[index] else "ocean"
            body = TOPOGRAPHY.sub(f"topography = {kind}", body, count=1)
            body = CURRENTS.sub("", body)
            body = _set_field(body, "climate", biomes.climate[index])
        else:
            body = _set_field(body, "climate", biomes.climate[index])
        lines.append(f"{cell.key} = {body}")
    return lines


def _ports(  # noqa: PLR0915 - port choice and dock placement share one pass.
    plan: Plan, world: NewWorld, canvas: Canvas
) -> tuple[list[str], dict[int, tuple[int, int]]]:
    """One port per coastal land cell, on its longest sea border, nearest its centre."""
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
    if not land_cells.size:
        return [], {}
    packed = land_cells * (len(plan.cells) + 1) + sea_cells
    values, counts = np.unique(packed, return_counts=True)
    best: dict[int, tuple[int, int]] = {}
    for value, length in zip(values.tolist(), counts.tolist(), strict=True):
        land_cell, sea_cell = divmod(value, len(plan.cells) + 1)
        current = best.get(land_cell)
        if current is None or length > current[1]:
            best[land_cell] = (sea_cell, length)
    rows_out: list[str] = []
    positions: dict[int, tuple[int, int]] = {}
    order = np.lexsort((pixels, packed))
    packed_sorted, pixels_sorted = packed[order], pixels[order]
    height = canvas.rolled.shape[0]
    for land_cell in sorted(best):
        sea_cell = best[land_cell][0]
        key = land_cell * (len(plan.cells) + 1) + sea_cell
        lo = np.searchsorted(packed_sorted, key, side="left")
        hi = np.searchsorted(packed_sorted, key, side="right")
        candidates = pixels_sorted[lo:hi]
        centre = world.interior[land_cell]
        distance = (candidates // width - centre[0]) ** 2 + (candidates % width - centre[1]) ** 2
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
    return rows_out, positions


def _instance(key: str, row: int, x: int, height: int) -> str:
    z = height - 1 - row
    return (
        f"\t\t{{\n\t\t\tid={key}\n\t\t\tposition={{ {x}.500000 0.000000 {z}.500000 }}\n"
        f"\t\t\trotation={ROTATION}\n\t\t\tscale={SCALE}\n\t\t}}\n"
    )


def _locator_instances(
    plan: Plan, world: NewWorld, canvas: Canvas, ports: dict[int, tuple[int, int]]
) -> dict[str, list[str]]:
    height = int(canvas.rolled.shape[0])
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
    for index, cell in enumerate(plan.cells):
        for name, kinds in wanted.items():
            if cell.kind in kinds:
                out[name].append(_instance(cell.key, int(rows[index]), int(columns[index]), height))
        if index in ports:
            row, x = ports[index]
            out["generated_map_object_locators_dock.txt"].append(
                _instance(cell.key, row, x, height)
            )
    return out


def _trimmed_instances(game_map: Eu5Map, canvas: Canvas) -> dict[str, str]:
    """Locator instances at the interior point of each trimmed ocean zone's remainder."""
    height, width = canvas.rolled.shape
    full = np.zeros(canvas.rolled.shape, dtype=bool)
    full[:, canvas.col0 : canvas.col0 + canvas.mask.shape[1]] = canvas.mask
    out: dict[str, str] = {}
    for zone in np.flatnonzero(canvas.trimmed).tolist():
        rows, columns = np.nonzero((canvas.rolled == zone) & ~full)
        top, bottom = int(rows.min()), int(rows.max()) + 1
        left, right = int(columns.min()), int(columns.max()) + 1
        mine = (canvas.rolled[top:bottom, left:right] == zone) & ~full[top:bottom, left:right]
        distance = distance_from(np.pad(~mine, 1, constant_values=True), 4096)[1:-1, 1:-1]
        best = int(np.argmax(np.where(mine, distance, -1)))
        row, column = divmod(best, mine.shape[1])
        x = (left + column - canvas.roll) % width
        key = game_map.keys[zone]
        out[key] = _instance(key, top + row, x, height)
    return out


def _additions(plan: Plan) -> HierarchyAdditions:
    additions = HierarchyAdditions()
    provinces: dict[str, list[str]] = {}
    area_of_province: dict[str, str] = {}
    for cell in plan.cells:
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


def _localization(plan: Plan, extra: dict[str, str], renamed: dict[str, str]) -> dict[str, bytes]:
    names = {cell.key: cell.name for cell in plan.cells}
    names.update(extra)
    names.update(plan.province_names)
    fresh = {area for area in plan.new_areas if area.startswith("rnw_")}
    names.update({area: plan.display_overrides[area] for area in sorted(fresh)})
    overrides = {key: value for key, value in plan.display_overrides.items() if key not in fresh}
    for table in (names, overrides):
        table.update({key: renamed[key] for key in table if key in renamed})
    files: dict[str, bytes] = {}
    for language in LANGUAGES:
        base = f"main_menu/localization/{language}"
        files[f"{base}/rnw_new_world_l_{language}.yml"] = _yaml(language, names)
        files[f"{base}/replace/rnw_new_world_replace_l_{language}.yml"] = _yaml(language, overrides)
    return files


def _final_labels(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> NDArray[np.int32]:
    final = game_map.labels.copy()
    rows, columns = np.nonzero(canvas.mask)
    final[rows, _world_columns(canvas, columns.astype(np.int64))] = world.labels[
        rows, columns
    ] + len(game_map.keys)
    return final


def _check_world(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> dict[str, int]:
    """Connectivity, sea reachability and Old World contact preservation."""
    count = len(world.classes)
    parts = label_components(world.labels)
    owner = np.full(int(parts.max()) + 1, -1, dtype=np.int64)
    owner[parts.ravel()] = world.labels.ravel()
    per_cell = np.bincount(owner[owner >= 0], minlength=count)
    if np.any(per_cell != 1):
        message = f"{int(np.count_nonzero(per_cell != 1))} generated cells are split or empty"
        raise NewWorldExportError(message)
    final = _final_labels(game_map, canvas, world)
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
    for zone in np.flatnonzero(canvas.trimmed).tolist():
        if not np.any(final == zone):
            message = f"Trimmed ocean zone vanished: {game_map.keys[zone]}"
            raise NewWorldExportError(message)
    return {
        "contacts_before": len(before),
        "contacts_after": len(after),
        "old_world_contacts_lost": 0,
        "generated_cells_split": 0,
        "generated_sea_zones_unreachable": 0,
    }


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


def _text_outputs(  # noqa: PLR0913 - every rewritten file needs the shared plan.
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
    new_world_keys: set[str],
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
    instances = _locator_instances(plan, world, canvas, port_pixels)
    trimmed = _trimmed_instances(game_map, canvas)
    for file_name in ("unit_stack", "combat", "vfx"):
        target = next(key for key in instances if file_name in key)
        instances[target].extend(trimmed.values())
    relocated = removed | set(trimmed)
    kept_provinces = {hierarchy[key].province for key in hierarchy if key not in removed}
    removed_provinces = {hierarchy[key].province for key in removed if key in hierarchy}
    gone = removed | (removed_provinces - kept_provinces) | set(plan.dropped_areas)
    outputs: dict[str, bytes] = {}
    outputs[_mod_path(NAMED_COLORS)] = _encode(
        game_dir,
        NAMED_COLORS,
        rewrite_named_colors(
            _read(game_dir, NAMED_COLORS), removed, [(c.key, c.color) for c in plan.cells]
        ),
    )
    outputs[_mod_path(DEFINITIONS)] = _encode(
        game_dir,
        DEFINITIONS,
        rewrite_definitions(_read(game_dir, DEFINITIONS), removed, _additions(plan)),
    )
    lists = {
        "sea_zones": [c.key for c in plan.cells if c.kind is CellClass.SEA],
        "lakes": [c.key for c in plan.cells if c.kind is CellClass.LAKE],
        "impassable_mountains": [c.key for c in plan.cells if c.kind is CellClass.WASTELAND],
    }
    outputs[_mod_path(DEFAULT_MAP)] = _encode(
        game_dir, DEFAULT_MAP, rewrite_class_lists(_read(game_dir, DEFAULT_MAP), removed, lists)
    )
    outputs[_mod_path(TEMPLATES)] = _encode(
        game_dir,
        TEMPLATES,
        rewrite_templates(
            _read(game_dir, TEMPLATES),
            removed,
            _template_lines(plan, world, donors, bodies, biomes, development.harbours),
        ),
    )
    outputs[_mod_path(PORTS)] = _encode(
        game_dir, PORTS, rewrite_csv(_read(game_dir, PORTS), removed, (0, 1), port_rows)
    )
    outputs[_mod_path(ADJACENCIES)] = _encode(
        game_dir, ADJACENCIES, rewrite_csv(_read(game_dir, ADJACENCIES), removed, (0, 1, 3), [])
    )
    for relative in LOCATOR_FILES:
        name = relative.rsplit("/", 1)[1]
        outputs[_mod_path(relative)] = _encode(
            game_dir,
            relative,
            rewrite_locators(_read(game_dir, relative), relocated, instances.get(name, [])),
        )
    outputs[_mod_path(LOCATOR_OVERRIDE)] = _encode(
        game_dir,
        LOCATOR_OVERRIDE,
        rewrite_override_locators(_read(game_dir, LOCATOR_OVERRIDE), removed),
    )
    setup = prune_setup(
        _setup_texts(game_dir), gone, {c.key: natives.pops.get(c.key, []) for c in plan.cells}
    )
    additions: dict[str, tuple[str, ...]] = {
        "10_countries.txt": (country_records(natives.countries),),
        BUILDINGS_FILE: (city_lines(natives.ranks), building_lines(development.villages)),
        "03_markets.txt": (market_lines(natives.markets),),
        "12_diplomacy.txt": (vassal_lines(natives.vassals),),
        DEVELOPMENT_FILE: (development_lines(development.terms),),
    }
    for name, text in setup.texts.items():
        relative = f"{SETUP_DIR}/{name}"
        if name == DEVELOPMENT_FILE:
            text = drop_block_entries(text, ("development",), new_world_keys)  # noqa: PLW2901
        for path, addition in zip(
            SETUP_INSERTS.get(name, ()), additions.get(name, ()), strict=True
        ):
            if addition:
                text = insert_into_block(text, path, addition)  # noqa: PLW2901
        if text != _read(game_dir, relative):
            outputs[_mod_path(relative)] = _encode(game_dir, relative, text)
    outputs[DEFINITION_FILE] = country_definitions(natives.countries)
    outputs.update(_localization(plan, country_names(natives.countries), natives.names))
    stats: dict[str, object] = {
        "ports": len(port_rows),
        "setup_records_deleted": {k: v for k, v in setup.deleted.items() if v},
        "setup_identifiers_removed": len(setup.removed_ids),
    }
    return outputs, stats


def _rasters(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, plan: Plan, river_codes: NDArray[np.uint8]
) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    rows, columns = np.nonzero(canvas.mask)
    world_columns = _world_columns(canvas, columns.astype(np.int64))
    cells = world.labels[rows, columns]
    colors = np.array([cell.color for cell in plan.cells], dtype=np.int64)[cells]
    rgb = game_map.rgb
    rgb[rows, world_columns, 0] = (colors >> 16) & 0xFF
    rgb[rows, world_columns, 1] = (colors >> 8) & 0xFF
    rgb[rows, world_columns, 2] = colors & 0xFF
    water = np.array(
        [cell.kind in {CellClass.SEA, CellClass.LAKE} for cell in plan.cells], dtype=bool
    )
    rivers = game_map.rivers
    rivers[rows, world_columns] = np.where(
        river_codes[rows, columns] < RIVER_CLASSES,
        river_codes[rows, columns],
        np.where(water[cells], RIVER_WATER, RIVER_LAND),
    )
    return rgb, rivers


def _rivers(
    world: NewWorld, canvas: Canvas, climate: ClimateGrid, seed: int
) -> tuple[NDArray[np.uint8], NDArray[np.int64], dict[str, object]]:
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
    world_width = int(canvas.rolled.shape[1])
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
    elevation = world.elevation.astype(np.int64)
    rivers = generate_rivers(land, elevation, rain, seed=seed)
    classes = flow_classes(rivers, RIVER_WIDTH_SHARES)
    codes = np.full(land.shape, RIVER_LAND, dtype=np.uint8)
    body = classes >= 0
    codes[body] = np.array(RIVER_WIDTH_CODES, dtype=np.uint8)[classes[body]]
    codes[rivers.role == SOURCE] = RIVER_SOURCE
    codes[rivers.role == JOIN] = RIVER_JOIN
    problems = network_problems(rivers.role, ~land)
    if any(problems.values()):
        message = f"generated rivers break the raster rules: {problems}"
        raise NewWorldExportError(message)
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
    return calibrate(
        rules_text=_read(game_dir, f"{SETUP_DIR}/{DEVELOPMENT_FILE}"),
        templates_text=_read(game_dir, TEMPLATES),
        buildings_text=_read(game_dir, f"{SETUP_DIR}/{BUILDINGS_FILE}"),
        countries_text=_read(game_dir, f"{SETUP_DIR}/10_countries.txt"),
        american=_vanilla_american(game_map, hierarchy),
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
) -> Development:
    wet = {CellClass.SEA, CellClass.LAKE}
    table = np.array([kind in wet for kind in (*game_map.classes, *world.classes)], dtype=bool)
    cells = sorted(docks)
    scores = shelter(table[labels], np.array([docks[cell] for cell in cells], dtype=np.int64))
    cell_fields = [
        (cell.key, biomes.vegetation[i], biomes.climate[i], biomes.topography[i])
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

    block = parse(text(f"{SETUP_DIR}/{DEVELOPMENT_FILE}")).block("development")
    if block is None:
        message = "No development block in the output"
        raise NewWorldExportError(message)
    kept = sorted(entry.key for entry in block.entries if entry.key in new_world_keys)
    if kept:
        message = f"Development entry {kept[0]} of the vanilla New World was kept"
        raise NewWorldExportError(message)
    found = _verify_terms(block, plan, development, calibration)
    generated = {cell.key for cell in plan.cells}
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


def export_new_world(  # noqa: PLR0913, PLR0915 - the CLI contract names each input.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
    replace: bool = False,
) -> dict[str, object]:
    """Generate, validate and stage one New World mod bundle; return its report."""
    check_new_output(output, MOD_NAME, game_dir, replace=replace)
    digest, build_label, accepted = resolve_build(game_dir, accept_build)
    spec = run_spec(seed, settings)
    game_map = load_map(game_dir)
    hierarchy = {location.key: location for location in read_locations(game_dir / DEFINITIONS)}
    canvas = select_canvas(game_map, settings.new_world.ocean_band_px)
    width = int(game_map.labels.shape[1])
    seam = (canvas.roll - canvas.col0) % width
    world = generate_new_world(
        canvas.mask.copy(), seed=seed, settings=settings.new_world, seam=seam
    )
    world = split_at_column(world, seam)
    total = len(game_map.keys) - int(np.count_nonzero(canvas.removed)) + len(world.classes)
    if total > MAX_LOCATIONS:
        message = (
            f"{total} locations exceed the {MAX_LOCATIONS} safety cap (vanilla has under "
            "28,600; a 16-bit limit is suspected); raise location_px or sea_zone_px"
        )
        raise NewWorldExportError(message)
    geometry = vanilla_geometry(game_map, canvas, hierarchy)
    plan = plan_identities(
        game_map, canvas, world, hierarchy, geometry, seed=seed, settings=settings.new_world
    )
    removed = {game_map.keys[index] for index in np.flatnonzero(canvas.removed).tolist()}
    world_checks = _check_world(game_map, canvas, world)
    store = DecalStore(game_dir, (int(game_map.labels.shape[0]), width))
    vanilla_attributes = template_attributes(_read(game_dir, TEMPLATES))
    new_world_keys = vanilla_new_world_keys(hierarchy, removed)
    calibration = calibrate_development(game_dir, game_map, hierarchy)
    biomes, biome_stats, climate = _biome_model(
        game_map, canvas=canvas, world=world, store=store, attributes=vanilla_attributes, seed=seed
    )
    river_codes, carved, river_stats = _rivers(world, canvas, climate, seed)
    river_pixels = np.bincount(
        world.labels[river_codes < RIVER_CLASSES].ravel(), minlength=len(world.classes) + 1
    )[: len(world.classes)]
    natives = build_natives(
        world=world,
        plan=plan,
        biomes=biomes,
        river_pixels=river_pixels.astype(np.int64),
        vanilla=vanilla_natives(game_dir, game_map, geometry, vanilla_attributes, hierarchy),
        settings=settings.natives,
        seed=seed,
    )
    slot_tables, slot_stats = _slot_tables(game_map, vanilla_attributes, biomes, store)
    biome_stats["materials"] = slot_stats
    final_labels = _final_labels(game_map, canvas, world)
    ports = _ports(plan, world, canvas)
    development = _plan_development(
        calibration,
        game_map=game_map,
        world=world,
        plan=plan,
        biomes=biomes,
        natives=natives,
        labels=final_labels,
        docks=ports[1],
    )
    texts, text_stats = _text_outputs(
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
        new_world_keys=new_world_keys,
    )
    text_checks = _verify_texts(texts, plan, removed)
    text_checks.update(_verify_natives(natives, plan))
    text_checks.update(
        verify_development(texts, plan, natives, development, calibration, new_world_keys)
    )
    remap = build_remap(
        [
            (game_map.keys[i], game_map.classes[i], int(geometry.rows[i]), int(geometry.columns[i]))
            for i in np.flatnonzero(canvas.removed).tolist()
        ],
        plan,
        np.stack([world.centroids[:, 0], world.centroids[:, 1] + canvas.col0], axis=1),
        _removed_provinces(hierarchy, removed),
    )
    scripts, remapped = remap_scripts(game_dir, remap)
    scripts.update(holy_site_outputs(game_dir, remap, natives.holy_sites))
    texts.update(scripts)
    text_stats["scripts_remapped"] = remapped
    rgb, rivers = _rasters(game_map, canvas, world, plan, river_codes)
    codes = _codes(game_map, canvas, world)
    canvas_world = codes != OUTSIDE
    vanilla_water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=bool
    )[game_map.labels]
    relief_world = np.zeros(game_map.labels.shape, dtype=np.int32)
    rows, columns = np.nonzero(canvas.mask)
    relief_world[rows, _world_columns(canvas, columns.astype(np.int64))] = carved[rows, columns]
    del carved
    terrain_inputs = TerrainInputs(
        codes=codes,
        vanilla_water=vanilla_water,
        relief=relief_world,
        labels=final_labels,
        rivers=rivers < RIVER_CLASSES,
    )
    terrain_files, materials_world, terrain_stats = terrain_outputs(
        store, terrain_inputs, slot_tables, seed
    )
    new_water = vanilla_water.copy()
    new_water[canvas_world] = codes[canvas_world] == WATER_CODE
    water_files, water_stats = water_outputs(game_dir, vanilla_water, new_water, canvas_world, seed)
    terrain_files.update(water_files)
    terrain_stats.update(water_stats)
    pixel_classes, class_count, coarse_count = _pixel_classes(
        game_map, vanilla_attributes, biomes, final_labels, materials_world
    )
    object_files, object_stats = object_outputs(
        game_dir,
        classes=pixel_classes,
        canvas=canvas_world,
        class_count=class_count,
        coarse_count=coarse_count,
        seed=seed,
    )
    del materials_world
    terrain_files.update(object_files)
    terrain_stats["objects"] = object_stats
    terrain_stats["rivers"] = river_stats
    name = output.name
    encoding = f"zlib level {ZLIB_LEVEL}, Up filter, zlib {zlib.ZLIB_RUNTIME_VERSION}"
    inputs = {record.path: record for record in game_map.inputs}
    with staged(output) as stage:
        files: list[dict[str, object]] = []
        for relative, source, pixels, mode, color_type, chunks in (
            ("in_game/map_data/locations.png", LOCATIONS, rgb, "RGB", COLOR_RGB,
             game_map.locations_chunks),
            ("in_game/map_data/rivers.png", RIVERS, rivers, "P", COLOR_PALETTE,
             game_map.rivers_chunks),
        ):  # fmt: skip
            data = encode_png(
                pixels, color_type=color_type, compression="zlib", extra_chunks=chunks
            )
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
        for relative, data in sorted(terrain_files.items()):
            files.append(write_bytes(stage, f"{name}/{relative}", data))
        files.append(
            write_bytes(
                stage, f"{name}/.metadata/metadata.json", _metadata(name, seed, settings.preset)
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
        rows, columns = np.nonzero(canvas.mask)
        outside[rows, _world_columns(canvas, columns.astype(np.int64))] = False
        if np.any(outside):
            message = "locations.png changed outside the New World canvas"
            raise NewWorldExportError(message)
        preview_record = write_bytes(
            stage, "preview.png", _preview(_class_preview(game_map, canvas, world))
        )
        settings_record = write_bytes(
            stage, "settings.json", canonical_json(spec["settings"]).encode()
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
            "spec": spec,
            "spec_sha256": spec_digest(spec),
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
            },
            "invariants": {**world_checks, **text_checks, "outside_canvas_identical": True},
            "text_stats": text_stats,
            "natives": natives.stats,
            "development": development.stats,
            "biomes": biome_stats,
            "terrain": terrain_stats,
            "files": [*files, preview_record, settings_record],
            "inputs": [
                {"path": record.path, "size": record.size, "sha256": record.sha256}
                for record in game_map.inputs
            ],
            "untested_engine_behaviors": list(UNTESTED),
        }
        manifest = {
            key: report[key]
            for key in ("schema", "status", "spec_sha256", "build", "inputs", "files")
        }
        _ = write_bytes(stage, "manifest.json", canonical_json(manifest).encode())
        _ = write_bytes(stage, "report.json", canonical_json(report).encode())
    return report


def _metadata(name: str, seed: int, preset: str) -> bytes:
    import json  # noqa: PLC0415

    payload: dict[str, object] = {
        "name": f"RNW New World {preset} seed {seed} ({STATUS})",
        "id": name,
        "version": __version__,
        "supported_game_version": "1.4.*",
        "short_description": f"Generated New World with new locations; local only; {STATUS}",
        "tags": ["Map"],
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def _codes(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> NDArray[np.int8]:
    """World-sized code map: -1 off the canvas, 0 generated water, 1 generated land."""
    codes = np.full(game_map.labels.shape, OUTSIDE, dtype=np.int8)
    rows, columns = np.nonzero(canvas.mask)
    table = np.array(
        [
            WATER_CODE if kind in {CellClass.SEA, CellClass.LAKE} else LAND_CODE
            for kind in world.classes
        ],
        dtype=np.int8,
    )
    codes[rows, _world_columns(canvas, columns.astype(np.int64))] = table[
        world.labels[rows, columns]
    ]
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


def _biome_model(  # noqa: PLR0913 - the biome model reads the map, the world and the decals.
    game_map: Eu5Map,
    *,
    canvas: Canvas,
    world: NewWorld,
    store: DecalStore,
    attributes: dict[str, dict[str, str]],
    seed: int,
) -> tuple[CellBiomes, dict[str, object], ClimateGrid]:
    """Climate, vegetation, topography and raw material of every generated cell."""
    vanilla_height = store.world_heights()
    vanilla = vanilla_locations(game_map.labels, vanilla_height)
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    final_sea = np.concatenate(
        [sea, np.array([kind is CellClass.SEA for kind in world.classes], dtype=bool)]
    )
    height = vanilla_height.astype(np.int64)
    rows, columns = np.nonzero(canvas.mask)
    world_columns = _world_columns(canvas, columns.astype(np.int64))
    height[rows, world_columns] = world.elevation[rows, columns]
    vanilla_grid = climate_grid(sea[game_map.labels], vanilla_height.astype(np.int64))
    final_grid = climate_grid(final_sea[_final_labels(game_map, canvas, world)], height)
    del height, vanilla_height
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
        vanilla=vanilla,
        vanilla_grid=vanilla_grid,
        final_grid=final_grid,
        cells=cells,
        seed=seed,
    )
    stats["coherence"] = _coherence(game_map, attributes, vanilla.pairs, world, biomes)
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


def _slot_tables(
    game_map: Eu5Map,
    attributes: dict[str, dict[str, str]],
    biomes: CellBiomes,
    store: DecalStore,
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
    vanilla_group = np.where(water[:vanilla_count], -1, group[:vanilla_count])
    counts = level_shares(store, game_map.labels, vanilla_group, len(group_names))
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
    rules = biome_rules(_read(store.game_dir, BIOME_DEFINITIONS))
    lists = material_counts(_read(store.game_dir, TERRAIN_MATERIALS))
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


def _class_preview(game_map: Eu5Map, canvas: Canvas, world: NewWorld) -> NDArray[np.uint8]:
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
    image[rows, world_columns] = table[world.labels[rows * step, columns * step]]
    return image
