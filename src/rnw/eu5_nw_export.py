"""Stage a generated New World mod (T3: new IDs, empty 1337 start) for EU5 1.4.1.

NOT GAME VALIDATED. The visual terrain (height decals) is not regenerated yet, so the
drawn relief stays vanilla even though locations, provinces and coasts are new.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
import zlib
from collections import deque
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.artifacts import check_new_output, pixel_digest, staged, write_bytes
from rnw.eu5_canvas import NEW_WORLD, OCEANS, Canvas, select_canvas
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
from rnw.eu5_newworld import Plan, VanillaGeometry, plan_identities, vanilla_geometry
from rnw.eu5_rewrite import (
    HierarchyAdditions,
    prune_setup,
    rewrite_class_lists,
    rewrite_csv,
    rewrite_definitions,
    rewrite_locators,
    rewrite_named_colors,
    rewrite_override_locators,
    rewrite_templates,
)
from rnw.geography import parse_locations, read_locations, read_named_colors
from rnw.model import CellClass
from rnw.newworld import NewWorld, generate_new_world
from rnw.pdx import Block, parse
from rnw.png import COLOR_PALETTE, COLOR_RGB, ZLIB_LEVEL, encode_png
from rnw.settings import canonical_json, run_spec, spec_digest
from rnw.topology import adjacency_pairs, label_components, unpack_pairs

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.geography import Location
    from rnw.settings import Settings

TEMPLATES: Final[str] = "game/in_game/map_data/location_templates.txt"
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
LAND_TOPOGRAPHY: Final[tuple[tuple[str, int], ...]] = (
    ("wetlands", 80),
    ("flatland", 490),
    ("hills", 720),
    ("plateau", 870),
    ("mountains", 1000),
)
ROTATION: Final[str] = "{ -0.000000 -0.000000 -0.000000 1.000000 }"
SCALE: Final[str] = "{ 1.000000 1.000000 1.000000 }"
TOPOGRAPHY: Final[re.Pattern[str]] = re.compile(r"topography\s*=\s*[A-Za-z_]+")
HARBOR: Final[re.Pattern[str]] = re.compile(r"\s*natural_harbor_suitability\s*=\s*[0-9.]+")
CURRENTS: Final[re.Pattern[str]] = re.compile(r"\s*movement_assistance\s*=\s*\{[^{}]*\}")
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
UNTESTED: Final[tuple[str, ...]] = (
    (
        "Visual terrain is NOT regenerated: height decals, material masks and mountain "
        "decals still draw the vanilla Americas under the new map."
    ),
    "Whether EU5 accepts thousands of new location keys and removed vanilla ones.",
    (
        "Around 700 script references to removed American locations (events, holy sites, "
        "expeditions, formables) will not resolve; their effect is untested."
    ),
    "nodes.dat and other derived caches are vanilla and may not match the new map.",
    (
        "Display-name overrides for reused area/region keys use a replace/ folder; whether "
        "EU5 honours it is unknown."
    ),
    "Colonisation, exploration, movement, naval routes, ports, save/load and startup time.",
)


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


def _template_lines(
    plan: Plan, world: NewWorld, donors: list[str], bodies: dict[str, str]
) -> list[str]:
    coastal = _coastal(world)
    land = [i for i, cell in enumerate(plan.cells) if cell.kind is CellClass.LAND]
    ranked = sorted(land, key=lambda index: (int(world.mean_elevation[index]), index))
    topography: dict[int, str] = {}
    for position, index in enumerate(ranked):
        share = (position * 1000) // max(1, len(ranked))
        topography[index] = next(name for name, limit in LAND_TOPOGRAPHY if share < limit)
    lines: list[str] = []
    for index, cell in enumerate(plan.cells):
        body = bodies[donors[index]]
        if cell.kind is CellClass.LAND:
            body = TOPOGRAPHY.sub(f"topography = {topography[index]}", body, count=1)
            body = HARBOR.sub("", body)
            if coastal[index]:
                body = body[:-1].rstrip() + " natural_harbor_suitability = 0.50 }"
        elif cell.kind is CellClass.SEA:
            kind = "coastal_ocean" if coastal[index] else "ocean"
            body = TOPOGRAPHY.sub(f"topography = {kind}", body, count=1)
            body = CURRENTS.sub("", body)
        lines.append(f"{cell.key} = {body}")
    return lines


def _ports(
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
        positions[land_cell] = (row, x)
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


def _localization(plan: Plan) -> dict[str, bytes]:
    names = {cell.key: cell.name for cell in plan.cells}
    names.update(plan.province_names)
    names.update({area: plan.display_overrides[area] for area in plan.new_areas})
    overrides = {
        key: value for key, value in plan.display_overrides.items() if key not in plan.new_areas
    }
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
    port_rows, port_pixels = _ports(plan, world, canvas)
    instances = _locator_instances(plan, world, canvas, port_pixels)
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
            _read(game_dir, TEMPLATES), removed, _template_lines(plan, world, donors, bodies)
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
            rewrite_locators(_read(game_dir, relative), removed, instances.get(name, [])),
        )
    outputs[_mod_path(LOCATOR_OVERRIDE)] = _encode(
        game_dir,
        LOCATOR_OVERRIDE,
        rewrite_override_locators(_read(game_dir, LOCATOR_OVERRIDE), removed),
    )
    setup = prune_setup(_setup_texts(game_dir), gone, [c.key for c in plan.cells])
    for name, text in setup.texts.items():
        relative = f"{SETUP_DIR}/{name}"
        if text != _read(game_dir, relative):
            outputs[_mod_path(relative)] = _encode(game_dir, relative, text)
    outputs.update(_localization(plan))
    stats: dict[str, object] = {
        "ports": len(port_rows),
        "setup_records_deleted": {k: v for k, v in setup.deleted.items() if v},
        "setup_identifiers_removed": len(setup.removed_ids),
    }
    return outputs, stats


def _rasters(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, plan: Plan
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
    rivers[rows, world_columns] = np.where(water[cells], RIVER_WATER, RIVER_LAND)
    return rgb, rivers


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
        text = re.sub(r"#[^\n]*", "", data.decode("utf-8-sig"))
        found = {word for word in WORD.findall(text) if word in removed}
        if found:
            leftovers[path] = len(found)
    if leftovers:
        message = f"Removed locations are still referenced: {leftovers}"
        raise NewWorldExportError(message)
    return {"definition_locations": len(keys), "template_locations": len(template_keys)}


def _preview(final_rgb_classes: NDArray[np.uint8]) -> bytes:
    return encode_png(final_rgb_classes, color_type=COLOR_RGB, compression="zlib")


def export_new_world(  # noqa: PLR0913 - the CLI contract names each input.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
) -> dict[str, object]:
    """Generate, validate and stage one New World mod bundle; return its report."""
    check_new_output(output, MOD_NAME, game_dir)
    digest, build_label, accepted = resolve_build(game_dir, accept_build)
    spec = run_spec(seed, settings)
    game_map = load_map(game_dir)
    hierarchy = {location.key: location for location in read_locations(game_dir / DEFINITIONS)}
    canvas = select_canvas(game_map, settings.new_world.ocean_band_px)
    world = generate_new_world(canvas.mask.copy(), seed=seed, settings=settings.new_world)
    geometry = vanilla_geometry(game_map, canvas, hierarchy)
    plan = plan_identities(
        game_map, canvas, world, hierarchy, geometry, seed=seed, settings=settings.new_world
    )
    removed = {game_map.keys[index] for index in np.flatnonzero(canvas.removed).tolist()}
    world_checks = _check_world(game_map, canvas, world)
    texts, text_stats = _text_outputs(
        game_dir,
        game_map=game_map,
        canvas=canvas,
        world=world,
        plan=plan,
        hierarchy=hierarchy,
        removed=removed,
        geometry=geometry,
    )
    text_checks = _verify_texts(texts, plan, removed)
    rgb, rivers = _rasters(game_map, canvas, world, plan)
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
            "tier": "T3 candidate: generated New World with new location IDs, empty 1337 start",
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
        "version": "0.3.0",
        "supported_game_version": "1.4.*",
        "short_description": f"Generated New World with new locations; local only; {STATUS}",
        "tags": ["Map"],
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


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
