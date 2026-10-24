"""Plan EU5 identities for a generated New World: keys, colours, hierarchy, names.

The hierarchy is built from the generated cells, top-down, as compact connected parts
(``hierarchy.py``): the land is split into the vanilla American subcontinents and
regions, each region into areas and each area into provinces; the sea into the vanilla
sea areas the canvas touches, then into provinces. Vanilla keys go to the generated part
by physical similarity within their original parent (N5), so script references keep
resolving on comparable land; subcontinents keep their positions. Areas a
region needs beyond its vanilla ones get new keys. Water near a shore belongs to the
region of that shore, as in vanilla. Provinces and locations are new.
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

from rnw.eu5_canvas import NEW_WORLD, OCEANS
from rnw.hierarchy import (
    absorb_small_pieces,
    balanced_parts,
    centre_of,
    contact_graph,
    keyed_parts,
    match,
    piece_counts,
    pieces,
    split,
    split_landmasses,
)
from rnw.model import CellClass
from rnw.names import NameGenerator
from rnw.rng import SplitMix64, derive_seed
from rnw.seanames import Placement, name_waters
from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_regionkeys import KeyMatcher
    from rnw.geography import Location
    from rnw.hierarchy import ContactGraph
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld
    from rnw.seas import Waters
    from rnw.settings import NewWorldSettings

KEY_PREFIX: Final[dict[CellClass, str]] = {
    CellClass.LAND: "rnw_loc_",
    CellClass.WASTELAND: "rnw_waste_",
    CellClass.SEA: "rnw_sea_",
    CellClass.LAKE: "rnw_lake_",
}
# Water is named for its shape (``seanames``), not by a suffix.
NAME_SUFFIX: Final[dict[CellClass, str]] = {
    CellClass.LAND: "",
    CellClass.WASTELAND: " Highlands",
    CellClass.LAKE: " Lake",
}
# Vanilla American land holds 6.2 locations per province and 5.8 provinces per area, its
# sea areas 8.6 zones per province and 52 per area (local 1.4.1 definitions.txt and
# default.map).
AREA_PROVINCES: Final[int] = 6
SEA_PROVINCE_ZONES: Final[int] = 9
SEA_AREA_ZONES: Final[int] = 52
# A region keeps its largest piece of water; other pieces below this join the water
# around them, as an island below half a part joins its nearest part.
MIN_SHORE_PIECE: Final[int] = SEA_AREA_ZONES // 4
# A region's water is at least this many zones for each sea area the game gives it, whatever
# its shore: the scripts name those areas, so each must have water (vanilla areas hold 11 to 52).
MIN_AREA_ZONES: Final[int] = 6
TARGET_SCALE: Final[int] = 1000
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
    physical_keys: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True, eq=False)
class VanillaGeometry:
    """Per-label centroids in rolled coordinates and area lookups."""

    rows: NDArray[np.int64]
    columns: NDArray[np.int64]
    areas: tuple[str, ...]
    pixels: NDArray[np.int64]


def vanilla_geometry(
    game_map: Eu5Map, canvas: Canvas, hierarchy: dict[str, Location]
) -> VanillaGeometry:
    """Pixel-weighted centroid of every vanilla label on the rolled raster."""
    count = len(game_map.keys)
    height, width = canvas.shape
    pixels = np.maximum(1, np.bincount(game_map.labels.ravel(), minlength=count))
    row_sum = np.zeros(count, dtype=np.float64)
    column_sum = np.zeros(count, dtype=np.float64)
    for start in range(0, height, 1024):
        block = canvas.rolled(game_map.labels, slice(start, start + 1024))
        rows = np.repeat(np.arange(start, start + block.shape[0], dtype=np.int64), width)
        columns = np.tile(np.arange(width, dtype=np.int64), block.shape[0])
        row_sum += np.bincount(block.ravel(), weights=rows, minlength=count)
        column_sum += np.bincount(block.ravel(), weights=columns, minlength=count)
    areas = tuple(hierarchy[key].area if key in hierarchy else "" for key in game_map.keys)
    return VanillaGeometry(
        rows=(row_sum.astype(np.int64) // pixels),
        columns=(column_sum.astype(np.int64) // pixels),
        areas=areas,
        pixels=pixels,
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


def _land_areas(  # noqa: PLR0913 - partition geometry, vanilla hierarchy and physical matching.
    graph: ContactGraph,
    cells: list[int],
    tally: _Tally,
    province_size: int,
    keys: KeySpace,
    *,
    physical: KeyMatcher,
) -> list[_Area]:
    """Top-down: subcontinents and regions keep their vanilla keys, areas reuse theirs.

    Subcontinents retain their positions and relative sizes. Regions start as equal
    compact parts without identities: the old positional rebalance could shrink a
    region below its count of child areas (three cells for Chaco's four in the reference).
    Final region and area boundaries receive keys by physical similarity before
    provinces are made; size is scored, never rebalanced after scoring.
    """
    areas: list[_Area] = []
    subcontinents = sorted(tally.children[NEW_WORLD])
    for subcontinent, sub_cells in zip(
        subcontinents, _keyed(graph, cells, tally, subcontinents), strict=True
    ):
        regions = sorted(tally.children[subcontinent])
        region_parts = split(graph, sub_cells, len(regions))
        positional = match(
            [centre_of(graph, part) for part in region_parts],
            [tally.centre(key) for key in regions],
        )
        regional_keys = physical.pair(
            region_parts,
            regions,
            positional,
            minimum={region: len(tally.children[region]) for region in regions},
        )
        for region_cells, region_key in zip(region_parts, regional_keys, strict=True):
            region = regions[region_key]
            vanilla = sorted(tally.children[region])
            wanted = _rounded(len(region_cells), province_size * AREA_PROVINCES)
            parts = split(graph, region_cells, min(len(region_cells), max(len(vanilla), wanted)))
            pairing = match(
                [centre_of(graph, part) for part in parts], [tally.centre(key) for key in vanilla]
            )
            pairing = physical.pair(parts, vanilla, pairing)
            for part, key in zip(parts, pairing, strict=True):
                name = vanilla[key] if key >= 0 else keys.next("rnw_area_", 4)
                provinces = split(graph, part, max(1, _rounded(len(part), province_size)))
                areas.append(_Area(name, (region, subcontinent, NEW_WORLD), provinces, key < 0))
    return areas


@dataclass(frozen=True, slots=True)
class _SeaArea:
    """A vanilla sea area the canvas touches: replaced zones and what stays outside.

    A coastal area lies under an American land region; the others are ocean areas.
    """

    name: str
    region: str
    coastal: bool
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
        first = hierarchy[game_map.keys[labels[0]]]
        replaced = [label for label in labels if canvas.removed[label]]
        placed = replaced or [label for label in labels if canvas.trimmed[label]]
        row = sum(int(geometry.rows[label]) for label in placed) // len(placed)
        column = sum(int(geometry.columns[label]) for label in placed) // len(placed)
        seas.append(
            _SeaArea(
                name,
                first.region,
                first.continent == NEW_WORLD,
                len(replaced),
                (row, column - canvas.col0),
                frozenset(label for label in labels if not canvas.removed[label]),
            )
        )
    return seas


def _coasts(
    world: NewWorld, sea: Sequence[bool], region_of: dict[int, str]
) -> dict[str, list[int]]:
    """Sea zones by the region whose land they touch most (lowest name on ties)."""
    touches: dict[int, dict[str, int]] = {}
    for first, second in world.edges:
        for zone, land in ((first, second), (second, first)):
            if sea[zone] and land in region_of:
                counts = touches.setdefault(zone, {})
                counts[region_of[land]] = counts.get(region_of[land], 0) + 1
    coasts: dict[str, list[int]] = {}
    for zone in sorted(touches):
        counts = touches[zone]
        coasts.setdefault(min(counts, key=lambda name: (-counts[name], name)), []).append(zone)
    return coasts


def outside_contacts(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, offset: int
) -> set[tuple[int, int]]:
    """(vanilla label, generated cell) pairs that touch across the canvas edge."""
    height, width = canvas.shape
    stop = canvas.col0 + int(canvas.mask.shape[1]) + 1
    columns = np.arange(canvas.col0 - 1, stop, dtype=np.int64) % width
    contacts: set[tuple[int, int]] = set()
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS + 1))
        generated = np.pad(world.labels[rows], ((0, 0), (1, 1)), constant_values=-1)
        combined = np.where(
            generated >= 0,
            generated + offset,
            canvas.rolled(game_map.labels, rows)[:, columns],
        ).astype(np.int32)
        for low, high in unpack_pairs(adjacency_pairs(combined)):
            if low < offset <= high:
                contacts.add((low, high - offset))
    return contacts


def _reserve(
    graph: ContactGraph,
    shores: dict[str, list[int]],
    needs: dict[str, int],
    taken: set[int],
) -> dict[str, list[int]]:
    """Give a region with too little shore the nearest free water to make up its need.

    The scripts name the sea areas of a region (a handful of islands may have five), and an
    area needs water. A region that has fewer zones on its shore than its areas need takes
    the nearest zones, ring by ring (the lowest number first), that no other region's shore
    and no ocean area has. Regions go in the order of their names.
    """
    held = set(taken) | {cell for cells in shores.values() for cell in cells}
    reserved = {region: list(cells) for region, cells in shores.items()}
    for region in sorted(shores):
        shortfall = needs[region] - len(shores[region])
        seen = set(shores[region])
        frontier = sorted(seen)
        extra: list[int] = []
        while frontier and len(extra) < shortfall:
            ring = sorted(
                {
                    other
                    for cell in frontier
                    for other, _ in graph.links[cell]
                    if other not in seen and other not in held
                }
            )
            seen.update(ring)
            extra.extend(ring[: shortfall - len(extra)])
            frontier = ring
        held.update(extra)
        reserved[region] = sorted([*shores[region], *extra])
    return reserved


def _sea_areas(  # noqa: PLR0913 - sea areas read the vanilla seas, coasts and parents.
    graph: ContactGraph,
    cells: list[int],
    seas: list[_SeaArea],
    contacts: set[tuple[int, int]],
    *,
    coasts: dict[str, list[int]],
    parents: dict[str, tuple[str, str, str]],
    keys: KeySpace,
) -> tuple[list[_Area], set[str]]:
    """Coastal water joins the region of its shore; the open ocean keeps the ocean areas.

    Every land region grows its water from the zones on its shore, so each piece of a
    region's sea touches that region's land. The coastal share of all water is the
    vanilla one, and a region's share follows its shore length; a small piece of a
    region's water beside its largest one joins the water around it. A region's water is
    split into its vanilla sea areas (nearest first) and new ones as its size needs.
    An ocean area cut by the canvas grows from the generated zones that touch its
    remainder (the first by name if a zone touches several), so it stays joined to it;
    every other ocean area starts at the open zone nearest its replaced zones. Returns
    the areas and the names of the cut ocean areas, which may have one piece per
    stretch of remainder.
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
    oceans = [
        sea for sea in seas if not sea.coastal and (not sea.remaining or anchors.get(sea.name))
    ]
    regions = sorted(coasts)
    shore = {zone for zones in coasts.values() for zone in zones}
    hosting = [
        cell
        for piece in pieces(graph, cells)
        if 2 * len(piece) * (len(oceans) + len(regions)) >= len(cells)
        for cell in piece
        if cell not in touching and cell not in shore
    ]
    free = [sea for sea in oceans if not sea.remaining]
    pairing = match(
        [sea.centre for sea in free], [(int(r), int(c)) for r, c in graph.centres[hosting].tolist()]
    )
    if any(choice < 0 for choice in pairing):
        message = f"{len(hosting)} open sea zones cannot start {len(free)} ocean areas"
        raise IdentityError(message)
    start = {sea.name: [hosting[choice]] for sea, choice in zip(free, pairing, strict=True)}
    coastal = sum(sea.replaced for sea in seas if sea.coastal)
    length = max(1, len(shore))
    own = {
        region: sum(1 for sea in seas if sea.coastal and sea.region == region) for region in regions
    }
    ocean_sources = [
        sorted(anchors[sea.name]) if sea.remaining else start[sea.name] for sea in oceans
    ]
    need = {region: own[region] * MIN_AREA_ZONES for region in regions}
    floor = {region: need[region] * TARGET_SCALE for region in regions}
    reserved = _reserve(
        graph,
        {region: coasts[region] for region in regions},
        need,
        {cell for nodes in ocean_sources for cell in nodes},
    )
    parts, _ = balanced_parts(
        graph,
        cells,
        [reserved[region] for region in regions] + ocean_sources,
        [
            max(len(coasts[region]) * coastal * TARGET_SCALE // length, floor[region])
            for region in regions
        ]
        + [sea.replaced * TARGET_SCALE for sea in oceans],
        movable=[False] * len(regions) + [not sea.remaining for sea in oceans],
        pinned=[True] * len(regions) + [not sea.remaining for sea in oceans],
    )
    parts = absorb_small_pieces(graph, parts, first=len(regions), minimum=MIN_SHORE_PIECE)
    areas: list[_Area] = []
    for region, part in zip(regions, parts, strict=False):
        coastal_seas = [sea for sea in seas if sea.coastal and sea.region == region]
        found = pieces(graph, part)
        split_parts = [
            area
            for piece, count in zip(
                found, piece_counts(found, SEA_AREA_ZONES, at_least=len(coastal_seas)), strict=True
            )
            for area in split(graph, piece, count)
        ]
        pairing = match(
            [centre_of(graph, area) for area in split_parts], [sea.centre for sea in coastal_seas]
        )
        for area, key in zip(split_parts, pairing, strict=True):
            name = coastal_seas[key].name if key >= 0 else keys.next("rnw_sea_area_", 4)
            provinces = split(graph, area, max(1, _rounded(len(area), SEA_PROVINCE_ZONES)))
            areas.append(_Area(name, parents[region], provinces, key < 0))
    for sea, part in zip(oceans, parts[len(regions) :], strict=True):
        # An unpinned ocean may give every generated zone to the shore regions. Its vanilla
        # remainder still defines the area; it needs no generated area with zero provinces.
        if not part and sea.remaining:
            continue
        provinces = [
            province
            for piece in (pieces(graph, part) if sea.remaining else [part])
            for province in split(graph, piece, max(1, _rounded(len(piece), SEA_PROVINCE_ZONES)))
        ]
        areas.append(_Area(sea.name, parents[sea.name], provinces, new=False))
    return areas, {sea.name for sea in oceans if sea.remaining}


def _check_shores(graph: ContactGraph, areas: list[_Area], coasts: dict[str, list[int]]) -> None:
    """Every piece of a land region's water touches that region's land."""
    water: dict[str, list[int]] = {}
    for area in areas:
        if area.parents[0] in coasts:
            water.setdefault(area.parents[0], []).extend(
                cell for province in area.provinces for cell in province
            )
    for region, cells in sorted(water.items()):
        shore = set(coasts[region])
        if any(not shore & set(piece) for piece in pieces(graph, cells)):
            message = f"Water of {region} has a piece away from the region's shore"
            raise IdentityError(message)


def _check_pieces(graph: ContactGraph, areas: list[_Area], *, depth: int, exempt: set[str]) -> None:
    """No group of the first ``depth`` levels has two pieces on one landmass or sea.

    The levels are province, area, region and subcontinent; ``exempt`` areas are only
    checked at the province level.
    """
    levels: list[dict[str, list[int]]] = [{} for _ in range(depth)]
    for area in areas:
        if not area.provinces or any(not cells for cells in area.provinces):
            message = f"Generated area {area.name} has an empty province or no provinces"
            raise IdentityError(message)
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


def _hierarchy(  # noqa: PLR0913, PLR0917 - the hierarchy reads the map, canvas and world.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    settings: NewWorldSettings,
    keys: KeySpace,
    physical: KeyMatcher,
) -> tuple[list[_Area], set[str]]:
    """Land areas, then sea areas, all checked; and the names of the cut ocean areas."""
    count = len(game_map.keys)
    is_land = [kind in LAND_FAMILY for kind in world.classes]
    is_sea = [kind is CellClass.SEA for kind in world.classes]
    land = contact_graph(world.centroids, world.edges, is_land)
    sea = contact_graph(world.centroids, world.edges, is_sea)
    areas = _land_areas(
        land,
        [cell for cell, flag in enumerate(is_land) if flag],
        _vanilla_land(game_map, canvas, hierarchy, geometry, geometry.pixels),
        settings.province_size,
        keys,
        physical=physical,
    )
    region_of = {
        cell: area.parents[0] for area in areas for cells in area.provinces for cell in cells
    }
    coasts = _coasts(world, is_sea, region_of)
    parents = _area_parents(hierarchy)
    parents.update({area.parents[0]: area.parents for area in areas})
    sea_areas, anchored = _sea_areas(
        sea,
        [cell for cell, flag in enumerate(is_sea) if flag],
        _vanilla_seas(game_map, canvas, hierarchy, geometry),
        outside_contacts(game_map, canvas, world, count),
        coasts=coasts,
        parents=parents,
        keys=keys,
    )
    _check_pieces(land, areas, depth=len(LEVELS), exempt=set())
    _check_pieces(sea, sea_areas, depth=2, exempt=anchored)
    _check_shores(sea, sea_areas, coasts)
    return areas + sea_areas, anchored


def plan_identities(  # noqa: PLR0913 - planning reads the map, canvas, world, hierarchy and water.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    *,
    seed: int,
    settings: NewWorldSettings,
    keys: KeySpace,
    waters: Waters,
    physical: KeyMatcher,
) -> Plan:
    """Assign keys, colours, names and parents to every generated cell.

    Land is split top-down into the vanilla subcontinents and regions, then into areas
    and provinces. Water near a shore joins the region of that shore and is split into
    its sea areas, the open ocean into the vanilla ocean areas the canvas touches; both
    then into provinces. Every part is compact and connected on its landmass or water
    body, and every piece of a region's water touches the region's land. Land is named at
    random; water is named for its shape (``seanames``): one sea, one name.
    """
    areas, anchored = _hierarchy(
        game_map, canvas, world, hierarchy, geometry, settings, keys, physical
    )
    plan = Plan(cells=[], anchored_sea_areas=sorted(anchored), physical_keys=physical.assignments)
    province_names = NameGenerator(seed, "provinces")
    area_names = NameGenerator(seed, "areas")
    province_of = [""] * len(world.classes)
    area_of: list[_Area | None] = [None] * len(world.classes)
    for area in areas:
        water = world.classes[area.provinces[0][0]] is CellClass.SEA
        if area.new:
            plan.new_areas[area.name] = []
            plan.area_region[area.name] = area.parents[0]
            if not water:
                plan.display_overrides[area.name] = area_names.next()
        for cells in area.provinces:
            name = keys.next("rnw_prov_", 5)
            if not water:
                plan.province_names[name] = province_names.next()
            if area.new:
                plan.new_areas[area.name].append(name)
            for cell in cells:
                province_of[cell] = name
                area_of[cell] = area
    placed: list[Placement | None] = [
        None
        if (area := area_of[cell]) is None or kind is not CellClass.SEA
        else Placement(province_of[cell], area.name, area.parents[2] in OCEANS)
        for cell, kind in enumerate(world.classes)
    ]
    sea = name_waters(world, waters, placed, seed=seed)
    plan.province_names.update(sea.provinces)
    plan.display_overrides.update(sea.areas)
    used = set(game_map.colors.tolist())
    colors = _colors(seed, len(world.classes), {int(value) for value in used})
    location_names = NameGenerator(seed, "locations")
    for index, kind in enumerate(world.classes):
        area = area_of[index]
        if area is None:
            message = f"Generated cell {index} ({kind.value}) has no area"
            raise IdentityError(message)
        region, subcontinent, continent = area.parents
        plan.cells.append(
            PlannedCell(
                key=keys.next(KEY_PREFIX[kind], 5),
                name=sea.cells[index]
                if kind is CellClass.SEA
                else location_names.next() + NAME_SUFFIX[kind],
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
