"""Plan EU5 identities for a generated New World: keys, colours, hierarchy, names.

The hierarchy is built from the generated cells, top-down, as compact connected parts
(``hierarchy.py``): the land is split into the vanilla American subcontinents and
regions, each region into areas and each area into provinces; the sea into the vanilla
sea areas the canvas touches, then into provinces. Vanilla keys go to the generated part
nearest their vanilla position, so script references to them keep resolving; areas a
region needs beyond its vanilla ones get new keys. Provinces and locations are new.
Stamping vanilla areas onto cells by position instead left areas and regions in pieces
inside one another [V-GAME owner, 1.4.1].
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_canvas import NEW_WORLD
from rnw.hierarchy import (
    balanced_parts,
    centre_of,
    contact_graph,
    keyed_parts,
    match,
    pieces,
    split,
    split_landmasses,
)
from rnw.model import CellClass
from rnw.names import NameGenerator
from rnw.rng import SplitMix64, derive_seed
from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.geography import Location
    from rnw.hierarchy import ContactGraph
    from rnw.newworld import NewWorld
    from rnw.settings import NewWorldSettings

KEY_PREFIX: Final[dict[CellClass, str]] = {
    CellClass.LAND: "rnw_loc_",
    CellClass.WASTELAND: "rnw_waste_",
    CellClass.SEA: "rnw_sea_",
    CellClass.LAKE: "rnw_lake_",
}
NAME_SUFFIX: Final[dict[CellClass, str]] = {
    CellClass.LAND: "",
    CellClass.WASTELAND: " Highlands",
    CellClass.SEA: " Sea",
    CellClass.LAKE: " Lake",
}
# Vanilla American land holds 6.2 locations per province and 5.8 provinces per area, its
# sea areas 8.6 zones per province (local 1.4.1 definitions.txt and default.map).
AREA_PROVINCES: Final[int] = 6
SEA_PROVINCE_ZONES: Final[int] = 9
COLOR_BITS: Final[int] = 24
STRIP_ROWS: Final[int] = 1024
LAND_FAMILY: Final[frozenset[CellClass]] = frozenset(
    {CellClass.LAND, CellClass.WASTELAND, CellClass.LAKE}
)
LEVELS: Final[tuple[str, ...]] = ("province", "area", "region", "subcontinent")


class IdentityError(ValueError):
    """The generated New World cannot take the vanilla hierarchy keys."""


@dataclass(frozen=True, slots=True)
class PlannedCell:
    """Identity of one generated cell."""

    key: str
    name: str
    color: int
    kind: CellClass
    province: str
    area: str
    region: str
    subcontinent: str
    continent: str


@dataclass(slots=True)
class Plan:
    """All identities and display names for one generated New World."""

    cells: list[PlannedCell]
    province_names: dict[str, str] = field(default_factory=dict)
    new_areas: dict[str, list[str]] = field(default_factory=dict)
    area_region: dict[str, str] = field(default_factory=dict)
    display_overrides: dict[str, str] = field(default_factory=dict)
    dropped_areas: list[str] = field(default_factory=list)
    anchored_sea_areas: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, eq=False)
class VanillaGeometry:
    """Per-label centroids in rolled coordinates and area lookups."""

    rows: NDArray[np.int64]
    columns: NDArray[np.int64]
    areas: tuple[str, ...]


def vanilla_geometry(
    game_map: Eu5Map, canvas: Canvas, hierarchy: dict[str, Location]
) -> VanillaGeometry:
    """Pixel-weighted centroid of every vanilla label on the rolled raster."""
    count = len(game_map.keys)
    height, width = canvas.rolled.shape
    flat = canvas.rolled.ravel()
    pixels = np.maximum(1, np.bincount(flat, minlength=count))
    row_sum = np.zeros(count, dtype=np.float64)
    column_sum = np.zeros(count, dtype=np.float64)
    for start in range(0, height, 1024):
        block = canvas.rolled[start : start + 1024]
        rows = np.repeat(np.arange(start, start + block.shape[0], dtype=np.int64), width)
        columns = np.tile(np.arange(width, dtype=np.int64), block.shape[0])
        row_sum += np.bincount(block.ravel(), weights=rows, minlength=count)
        column_sum += np.bincount(block.ravel(), weights=columns, minlength=count)
    areas = tuple(hierarchy[key].area if key in hierarchy else "" for key in game_map.keys)
    return VanillaGeometry(
        rows=(row_sum.astype(np.int64) // pixels),
        columns=(column_sum.astype(np.int64) // pixels),
        areas=areas,
    )


def _colors(seed: int, count: int, used: set[int]) -> list[int]:
    rng = SplitMix64(derive_seed(seed, "nw_colors"))
    taken = set(used) | {0}
    colors: list[int] = []
    while len(colors) < count:
        color = rng.next_u64() >> (64 - COLOR_BITS)
        if color not in taken:
            taken.add(color)
            colors.append(color)
    return colors


@dataclass(slots=True)
class _Tally:
    """Vanilla keys: their children, replaced locations and pixel-weighted centres."""

    col0: int
    children: dict[str, set[str]] = field(default_factory=dict)
    count: dict[str, int] = field(default_factory=dict)
    sums: dict[str, list[int]] = field(default_factory=dict)

    def add(self, chain: tuple[str, ...], row: int, column: int, pixels: int) -> None:
        """Count one location under every key of ``chain`` (outermost first)."""
        for parent, child in itertools.pairwise(chain):
            self.children.setdefault(parent, set()).add(child)
        for name in chain[1:]:
            self.count[name] = self.count.get(name, 0) + 1
            entry = self.sums.setdefault(name, [0, 0, 0])
            entry[0] += row * pixels
            entry[1] += column * pixels
            entry[2] += pixels

    def centre(self, name: str) -> tuple[int, int]:
        """Centre of ``name`` in canvas-crop coordinates."""
        row, column, pixels = self.sums[name]
        return row // max(1, pixels), column // max(1, pixels) - self.col0


@dataclass(frozen=True, slots=True)
class _Area:
    """One generated area: its key, vanilla parents and province cells."""

    name: str
    parents: tuple[str, str, str]
    provinces: list[list[int]]
    new: bool


def _rounded(value: int, size: int) -> int:
    return (value + size // 2) // size


def _vanilla_land(
    game_map: Eu5Map,
    canvas: Canvas,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    pixels: NDArray[np.int64],
) -> _Tally:
    """Subcontinents, regions and land areas of the vanilla New World.

    The generated hierarchy replaces all of them, so a vanilla location left on the
    map under one of these keys would end up in a generated area or region.
    """
    index = {key: number for number, key in enumerate(game_map.keys)}
    sea_areas = {
        location.area
        for location in hierarchy.values()
        if game_map.classes[index[location.key]] is CellClass.SEA
    }
    tally = _Tally(canvas.col0)
    for location in hierarchy.values():
        if location.continent != NEW_WORLD or location.area in sea_areas:
            continue
        label = index[location.key]
        if not canvas.removed[label]:
            message = f"Vanilla location {location.key} stays on the map in {location.area}"
            raise IdentityError(message)
        chain = (NEW_WORLD, location.subcontinent, location.region, location.area)
        tally.add(
            chain, int(geometry.rows[label]), int(geometry.columns[label]), int(pixels[label])
        )
    return tally


def _keyed(
    graph: ContactGraph, cells: list[int], tally: _Tally, keys: list[str]
) -> list[list[int]]:
    if len(keys) > len(cells):
        message = f"{len(cells)} generated cells cannot hold the {len(keys)} keys {keys}"
        raise IdentityError(message)
    return keyed_parts(
        graph, cells, [tally.centre(key) for key in keys], [tally.count[key] for key in keys]
    )


def _land_areas(
    graph: ContactGraph, cells: list[int], tally: _Tally, province_size: int
) -> list[_Area]:
    """Top-down: subcontinents and regions keep their vanilla keys, areas reuse theirs.

    Every vanilla region and subcontinent gets one part sized by its vanilla location
    count; a region has at least as many areas as its vanilla counterpart, so every
    vanilla area key is reused by the generated area nearest to it.
    """
    areas: list[_Area] = []
    fresh = 0
    subcontinents = sorted(tally.children[NEW_WORLD])
    for subcontinent, sub_cells in zip(
        subcontinents, _keyed(graph, cells, tally, subcontinents), strict=True
    ):
        regions = sorted(tally.children[subcontinent])
        for region, region_cells in zip(
            regions, _keyed(graph, sub_cells, tally, regions), strict=True
        ):
            vanilla = sorted(tally.children[region])
            wanted = _rounded(len(region_cells), province_size * AREA_PROVINCES)
            parts = split(graph, region_cells, min(len(region_cells), max(len(vanilla), wanted)))
            pairing = match(
                [centre_of(graph, part) for part in parts], [tally.centre(key) for key in vanilla]
            )
            for part, key in zip(parts, pairing, strict=True):
                if key < 0:
                    fresh += 1
                name = vanilla[key] if key >= 0 else f"rnw_area_{fresh:04d}"
                provinces = split(graph, part, max(1, _rounded(len(part), province_size)))
                areas.append(_Area(name, (region, subcontinent, NEW_WORLD), provinces, key < 0))
    return areas


@dataclass(frozen=True, slots=True)
class _SeaArea:
    """A vanilla sea area the canvas touches: replaced zones and what stays outside."""

    name: str
    replaced: int
    centre: tuple[int, int]
    remaining: frozenset[int]


def _vanilla_seas(
    game_map: Eu5Map, canvas: Canvas, hierarchy: dict[str, Location], geometry: VanillaGeometry
) -> list[_SeaArea]:
    index = {key: number for number, key in enumerate(game_map.keys)}
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    touched = canvas.removed | canvas.trimmed
    members: dict[str, list[int]] = {}
    for location in hierarchy.values():
        members.setdefault(location.area, []).append(index[location.key])
    names = sorted(
        {hierarchy[game_map.keys[label]].area for label in np.flatnonzero(touched & sea).tolist()}
    )
    seas: list[_SeaArea] = []
    for name in names:
        labels = members[name]
        replaced = [label for label in labels if canvas.removed[label]]
        placed = replaced or [label for label in labels if canvas.trimmed[label]]
        row = sum(int(geometry.rows[label]) for label in placed) // len(placed)
        column = sum(int(geometry.columns[label]) for label in placed) // len(placed)
        remaining = frozenset(label for label in labels if not canvas.removed[label])
        seas.append(_SeaArea(name, len(replaced), (row, column - canvas.col0), remaining))
    return seas


def _outside_contacts(canvas: Canvas, world: NewWorld, offset: int) -> set[tuple[int, int]]:
    """(vanilla label, generated cell) pairs that touch across the canvas edge."""
    height, width = int(canvas.rolled.shape[0]), int(canvas.rolled.shape[1])
    stop = canvas.col0 + int(canvas.mask.shape[1]) + 1
    columns = np.arange(canvas.col0 - 1, stop, dtype=np.int64) % width
    contacts: set[tuple[int, int]] = set()
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS + 1))
        generated = np.pad(world.labels[rows], ((0, 0), (1, 1)), constant_values=-1)
        combined = np.where(
            generated >= 0, generated + offset, canvas.rolled[rows][:, columns]
        ).astype(np.int32)
        for low, high in unpack_pairs(adjacency_pairs(combined)):
            if low < offset <= high:
                contacts.add((low, high - offset))
    return contacts


def _sea_areas(
    graph: ContactGraph,
    cells: list[int],
    seas: list[_SeaArea],
    contacts: set[tuple[int, int]],
    parents: dict[str, tuple[str, str, str]],
) -> tuple[list[_Area], set[str]]:
    """Sea areas keep their vanilla keys; a cut one grows from what stays outside.

    A generated zone touching the remainder of a vanilla sea area cut by the canvas
    anchors that area (the first by name if it touches several), so the area stays
    joined to its remainder. Every other sea area starts at the generated zone nearest
    its replaced zones, on water large enough to hold half an area. Returns the areas
    and the names of the anchored ones, which may have one piece per anchor stretch.
    """
    owner = {label: sea.name for sea in reversed(seas) for label in sea.remaining}
    water = set(cells)
    touching: dict[int, set[str]] = {}
    for label, cell in contacts:
        if label in owner and cell in water:
            touching.setdefault(cell, set()).add(owner[label])
    anchors: dict[str, list[int]] = {}
    for cell in sorted(touching):
        anchors.setdefault(min(touching[cell]), []).append(cell)
    used = [sea for sea in seas if not sea.remaining or anchors.get(sea.name)]
    hosting = [
        cell
        for piece in pieces(graph, cells)
        if 2 * len(piece) * len(used) >= len(cells)
        for cell in piece
        if cell not in touching
    ]
    free = [sea for sea in used if not sea.remaining]
    pairing = match(
        [sea.centre for sea in free], [(int(r), int(c)) for r, c in graph.centres[hosting].tolist()]
    )
    if any(choice < 0 for choice in pairing):
        message = f"{len(hosting)} open sea zones cannot start {len(free)} sea areas"
        raise IdentityError(message)
    start = {sea.name: [hosting[choice]] for sea, choice in zip(free, pairing, strict=True)}
    sources = [sorted(anchors[sea.name]) if sea.remaining else start[sea.name] for sea in used]
    parts, _ = balanced_parts(
        graph,
        cells,
        sources,
        [sea.replaced for sea in used],
        movable=[not sea.remaining for sea in used],
    )
    areas: list[_Area] = []
    for sea, part in zip(used, parts, strict=True):
        provinces = [
            province
            for piece in (pieces(graph, part) if sea.remaining else [part])
            for province in split(graph, piece, max(1, _rounded(len(piece), SEA_PROVINCE_ZONES)))
        ]
        areas.append(_Area(sea.name, parents[sea.name], provinces, new=False))
    return areas, {sea.name for sea in used if sea.remaining}


def _check_pieces(graph: ContactGraph, areas: list[_Area], *, depth: int, exempt: set[str]) -> None:
    """No group of the first ``depth`` levels has two pieces on one landmass or sea.

    The levels are province, area, region and subcontinent; ``exempt`` areas are only
    checked at the province level.
    """
    levels: list[dict[str, list[int]]] = [{} for _ in range(depth)]
    for area in areas:
        names = (area.name, *area.parents[:2])
        for number, cells in enumerate(area.provinces):
            levels[0][f"{area.name}/{number}"] = cells
            for groups, name in zip(levels[1:], names, strict=False):
                _ = groups.setdefault(name, [])
                groups[name].extend(cells)
    for level, groups in zip(LEVELS, levels, strict=False):
        names = sorted(groups)
        skipped = {
            number for number, name in enumerate(names) if level != LEVELS[0] and name in exempt
        }
        broken = split_landmasses(graph, [groups[name] for name in names], exempt=skipped)
        if broken:
            message = f"Generated {level} {names[broken[0]]} has two pieces on one landmass"
            raise IdentityError(message)


def plan_identities(  # noqa: PLR0913 - planning reads the map, canvas, world and hierarchy.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    *,
    seed: int,
    settings: NewWorldSettings,
) -> Plan:
    """Assign keys, colours, names and parents to every generated cell.

    Land is split top-down into the vanilla subcontinents and regions, then into areas
    and provinces; sea zones into the vanilla sea areas the canvas touches, then into
    provinces. Every part is compact and connected on its landmass or water body.
    """
    count = len(game_map.keys)
    pixels = np.bincount(canvas.rolled.ravel(), minlength=count).astype(np.int64)
    is_land = [kind in LAND_FAMILY for kind in world.classes]
    is_sea = [kind is CellClass.SEA for kind in world.classes]
    land = contact_graph(world.centroids, world.edges, is_land)
    sea = contact_graph(world.centroids, world.edges, is_sea)
    land_cells = [cell for cell, flag in enumerate(is_land) if flag]
    sea_cells = [cell for cell, flag in enumerate(is_sea) if flag]
    areas = _land_areas(
        land,
        land_cells,
        _vanilla_land(game_map, canvas, hierarchy, geometry, pixels),
        settings.province_size,
    )
    sea_areas, anchored = _sea_areas(
        sea,
        sea_cells,
        _vanilla_seas(game_map, canvas, hierarchy, geometry),
        _outside_contacts(canvas, world, count),
        _area_parents(hierarchy),
    )
    _check_pieces(land, areas, depth=len(LEVELS), exempt=set())
    _check_pieces(sea, sea_areas, depth=2, exempt=anchored)
    areas.extend(sea_areas)
    plan = Plan(cells=[], anchored_sea_areas=sorted(anchored))
    province_names = NameGenerator(seed, "provinces")
    area_names = NameGenerator(seed, "areas")
    province_of = [""] * len(world.classes)
    area_of: list[_Area | None] = [None] * len(world.classes)
    serial = 0
    for area in areas:
        if area.new:
            plan.new_areas[area.name] = []
            plan.area_region[area.name] = area.parents[0]
            plan.display_overrides[area.name] = area_names.next()
        for cells in area.provinces:
            serial += 1
            name = f"rnw_prov_{serial:05d}"
            plan.province_names[name] = province_names.next()
            if area.new:
                plan.new_areas[area.name].append(name)
            for cell in cells:
                province_of[cell] = name
                area_of[cell] = area
    used = set(game_map.colors.tolist())
    colors = _colors(seed, len(world.classes), {int(value) for value in used})
    location_names = NameGenerator(seed, "locations")
    serials = dict.fromkeys(KEY_PREFIX, 0)
    for index, kind in enumerate(world.classes):
        serials[kind] += 1
        area = area_of[index]
        if area is None:
            message = f"Generated cell {index} ({kind.value}) has no area"
            raise IdentityError(message)
        region, subcontinent, continent = area.parents
        plan.cells.append(
            PlannedCell(
                key=f"{KEY_PREFIX[kind]}{serials[kind]:05d}",
                name=location_names.next() + NAME_SUFFIX[kind],
                color=colors[index],
                kind=kind,
                province=province_of[index],
                area=area.name,
                region=region,
                subcontinent=subcontinent,
                continent=continent,
            )
        )
    reused = {cell.area for cell in plan.cells} | {cell.region for cell in plan.cells}
    override_names = NameGenerator(seed, "overrides")
    for name in sorted(reused):
        if name not in plan.display_overrides and _is_new_world(hierarchy, name):
            plan.display_overrides[name] = override_names.next()
    vanilla_new_world_areas = {
        location.area for location in hierarchy.values() if location.continent == NEW_WORLD
    }
    plan.dropped_areas = sorted(vanilla_new_world_areas - {cell.area for cell in plan.cells})
    return plan


def _area_parents(hierarchy: dict[str, Location]) -> dict[str, tuple[str, str, str]]:
    return {
        location.area: (location.region, location.subcontinent, location.continent)
        for location in hierarchy.values()
    }


def _is_new_world(hierarchy: dict[str, Location], name: str) -> bool:
    return any(
        location.continent == NEW_WORLD and name in {location.area, location.region}
        for location in hierarchy.values()
    )
