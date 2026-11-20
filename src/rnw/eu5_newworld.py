"""Plan EU5 identities for a generated New World: keys, colours, hierarchy, names.

The hierarchy is built from the generated cells, top-down, as compact connected parts
(``hierarchy.py``): the land is split into the vanilla American subcontinents and
regions, each region into areas and each area into provinces; the sea into the vanilla
sea areas the canvas touches, then into provinces. Subcontinents are bands from north to
south in their vanilla order and shares. Within its original parent a vanilla key goes to
the part that lies where the key lies in vanilla, and among comparable places to the most
similar land (N5), so the map reads as the Americas do and script references keep
resolving on comparable land. Areas a region needs beyond its vanilla ones get new keys.
Water near a shore belongs to the region of that shore, as in vanilla. Provinces and
locations are new.
Stamping vanilla areas onto cells by position instead left areas and regions in pieces
inside one another [V-GAME owner, 1.4.1].
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import itertools
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import wording
from rnw.epoch import CURRENT, NATURAL_WASTELANDS, SUBCONTINENT_WAISTS
from rnw.eu5_canvas import NEW_WORLD, OCEANS
from rnw.eu5_regionkeys import (
    AREA_PLACE_WEIGHT,
    REGION_PLACE_WEIGHT,
    minimum_assignment,
    physical_keys,
    place_distance,
    standard,
    unstandard,
)
from rnw.hierarchy import (
    absorb_small_pieces,
    balanced_parts,
    banded_parts,
    centre_of,
    contact_graph,
    match,
    neck_parts,
    piece_counts,
    pieces,
    split,
    split_landmasses,
    spread_sources,
)
from rnw.model import CellClass
from rnw.names import NameGenerator
from rnw.rng import SplitMix64, derive_seed
from rnw.seanames import Placement, name_waters
from rnw.seas import inland_seas
from rnw.topology import LOW_BITS, PAIR_SHIFT, adjacency_pairs, unpack_pairs
from rnw.wastelands import location_units
from rnw.wording import Name, Phrase

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.continent_domains import Domain
    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_canvas import Canvas, OceanRemainder
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_regionkeys import KeyMatcher
    from rnw.geography import Location
    from rnw.hierarchy import ContactGraph
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld
    from rnw.seas import Waters
    from rnw.settings import NewWorldSettings
    from rnw.wastelands import LocationUnits

KEY_PREFIX: Final[dict[CellClass, str]] = {
    CellClass.LAND: "rnw_loc_",
    CellClass.WASTELAND: "rnw_waste_",
    CellClass.SEA: "rnw_sea_",
    CellClass.LAKE: "rnw_lake_",
}
# Water is named for its shape (``seanames``); wastelands and lakes by a term (``wording``).
NAME_TERM: Final[dict[CellClass, str]] = {
    CellClass.WASTELAND: wording.HIGHLANDS,
    CellClass.LAKE: wording.LAKE,
}
# A wasteland of a flat or a dune topography is no highland: from epoch 64 it is a wild or a desert.
WASTE_TERMS: Final[dict[str, str]] = {
    "flatland_wasteland": wording.WILDS,
    "dune_wasteland": wording.DESERT,
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
NO_CELLS: Final[frozenset[int]] = frozenset()


class IdentityError(ValueError):
    """The generated New World cannot take the vanilla hierarchy keys."""


@dataclass(frozen=True, slots=True)
class PlannedCell:
    """Identity of one generated cell."""

    key: str
    name: Name
    color: int
    kind: CellClass
    province: str
    area: str
    region: str
    subcontinent: str
    continent: str


@dataclass(slots=True)
class OceanPlan:
    """Final shared keys, additional remainder locations and bounded pixel assignments."""

    retained: set[str] = field(default_factory=set)
    extra: list[PlannedCell] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    closed_extra: set[str] = field(default_factory=set)
    patches: list[tuple[OceanRemainder, int]] = field(default_factory=list)
    anchors: dict[str, tuple[int, int]] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict)

    def paint(self, target: NDArray[np.generic], canvas: Canvas, *, clear: bool = False) -> None:
        """Apply only the planned remainder runs (or clear their allowed-change mask)."""
        width = canvas.shape[1]
        for part, color in self.patches:
            value = False if clear else ((color >> 16) & 255, (color >> 8) & 255, color & 255)
            for row, left, right in part.runs.tolist():
                start = (left - canvas.roll) % width
                length = right - left
                first = min(length, width - start)
                target[row, start : start + first] = value
                if first < length:
                    target[row, : length - first] = value


@dataclass(slots=True)
class Plan:
    """All identities and display names for one generated New World."""

    cells: list[PlannedCell]
    province_names: dict[str, Name] = field(default_factory=dict)
    new_areas: dict[str, list[str]] = field(default_factory=dict)
    area_region: dict[str, str] = field(default_factory=dict)
    display_overrides: dict[str, Name] = field(default_factory=dict)
    dropped_areas: list[str] = field(default_factory=list)
    anchored_sea_areas: list[str] = field(default_factory=list)
    physical_keys: list[dict[str, object]] = field(default_factory=list)
    oceans: OceanPlan | None = None


@dataclass(frozen=True, slots=True, eq=False)
class VanillaGeometry:
    """Per-label centroids in rolled coordinates and area lookups."""

    rows: NDArray[np.int64]
    columns: NDArray[np.int64]
    areas: tuple[str, ...]
    pixels: NDArray[np.int64]


def vanilla_geometry(
    game_map: Eu5Map, canvas: Canvas, hierarchy: dict[str, Location], *, wrap_x: bool = False
) -> VanillaGeometry:
    """Pixel-weighted centroid of every vanilla label on the rolled raster."""
    count = len(game_map.keys)
    height, width = canvas.shape
    pixels = np.maximum(1, np.bincount(game_map.labels.ravel(), minlength=count))
    row_sum = np.zeros(count, dtype=np.float64)
    column_sum = np.zeros(count, dtype=np.float64)
    crossing = (
        np.intersect1d(game_map.labels[:, 0], game_map.labels[:, -1])
        if wrap_x
        else np.empty(0, dtype=np.int32)
    )
    for start in range(0, height, 1024):
        block = canvas.rolled(game_map.labels, slice(start, start + 1024))
        rows = np.repeat(np.arange(start, start + block.shape[0], dtype=np.int64), width)
        columns = np.tile(np.arange(width, dtype=np.int64), block.shape[0])
        row_sum += np.bincount(block.ravel(), weights=rows, minlength=count)
        column_sum += np.bincount(block.ravel(), weights=columns, minlength=count)
        if crossing.size:
            left = np.bincount(block[:, : width // 2].ravel(), minlength=count)
            column_sum[crossing] += width * left[crossing]
    areas = tuple(hierarchy[key].area if key in hierarchy else "" for key in game_map.keys)
    return VanillaGeometry(
        rows=(row_sum.astype(np.int64) // pixels),
        columns=(column_sum.astype(np.int64) // pixels) % width,
        areas=areas,
        pixels=pixels,
    )


def regional_geometry(
    game_map: Eu5Map, domain: Domain, hierarchy: dict[str, Location]
) -> VanillaGeometry:
    """Measure retained hierarchy keys in this domain's continuous coordinates."""
    count = len(game_map.keys)
    pixels = np.zeros(count, dtype=np.int64)
    row_sum = np.zeros(count, dtype=np.float64)
    column_sum = np.zeros(count, dtype=np.float64)
    for local, original in domain.spans():
        for first in range(0, domain.mask.shape[0], 256):
            stop = min(first + 256, domain.mask.shape[0])
            r, c = np.nonzero(domain.footprint[first:stop, local])
            rows = slice(domain.first_row + first, domain.first_row + stop)
            labels = game_map.labels[rows, original][r, c]
            pixels += np.bincount(labels, minlength=count)
            row_sum += np.bincount(labels, weights=r + first, minlength=count)
            column_sum += np.bincount(labels, weights=c + int(local.start), minlength=count)
    safe = np.maximum(pixels, 1)
    return VanillaGeometry(
        rows=row_sum.astype(np.int64) // safe,
        columns=column_sum.astype(np.int64) // safe,
        areas=tuple(hierarchy[key].area if key in hierarchy else "" for key in game_map.keys),
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
    continent: str = NEW_WORLD

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
    return _land_tally(
        game_map, hierarchy, geometry, pixels, canvas.removed, col0=canvas.col0, continent=NEW_WORLD
    )


def _land_tally(  # noqa: PLR0913 - scope and geometry are independent.
    game_map: Eu5Map,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    pixels: NDArray[np.int64],
    removed: NDArray[np.bool_],
    *,
    col0: int,
    continent: str,
) -> _Tally:
    """Subcontinents, regions and land areas of one replaced continent.

    The generated hierarchy replaces all of them, so a vanilla location left on the
    map under one of these keys would end up in a generated area or region.
    """
    index = {key: number for number, key in enumerate(game_map.keys)}
    sea_areas = {
        location.area
        for location in hierarchy.values()
        if game_map.classes[index[location.key]] is CellClass.SEA
    }
    tally = _Tally(col0, continent=continent)
    for location in hierarchy.values():
        if location.continent != continent or location.area in sea_areas:
            continue
        label = index[location.key]
        if not removed[label]:
            message = f"Vanilla location {location.key} stays on the map in {location.area}"
            raise IdentityError(message)
        chain = (continent, location.subcontinent, location.region, location.area)
        tally.add(
            chain, int(geometry.rows[label]), int(geometry.columns[label]), int(pixels[label])
        )
    return tally


def _bands(
    graph: ContactGraph, cells: list[int], tally: _Tally, keys: list[str], algorithm: int
) -> list[list[int]]:
    """The subcontinents from north to south, in their vanilla order and about their shares.

    Cut at the land's waists (``neck_parts``); before epoch 63 in bands of rows (``banded_parts``).
    """
    if len(keys) > len(cells):
        message = f"{len(cells)} generated cells cannot hold the {len(keys)} keys {keys}"
        raise IdentityError(message)
    order = sorted(range(len(keys)), key=lambda key: (tally.centre(keys[key])[0], keys[key]))
    weights = [tally.count[keys[key]] for key in order]
    if algorithm < SUBCONTINENT_WAISTS:
        return _in_order(banded_parts(graph, cells, weights), order)
    total = sum(weights)
    # A piece of a subcontinent on a landmass it shares with another piece must be able to hold
    # a region: as many cells as an average region of the subcontinent's share of the cells.
    lowest = [
        max(1, len(cells) * weight // total // max(1, len(tally.children[keys[key]])))
        for key, weight in zip(order, weights, strict=True)
    ]
    return _in_order(neck_parts(graph, cells, weights, lowest), order)


def _in_order(found: list[list[int]], order: list[int]) -> list[list[int]]:
    """The parts, cut north to south, by the subcontinent each belongs to."""
    parts: list[list[int]] = [[] for _ in order]
    for key, part in zip(order, found, strict=True):
        parts[key] = part
    return parts


def _placed(  # noqa: PLR0913 - graph, source positions and their partition budgets.
    graph: ContactGraph,
    members: list[int],
    count: int,
    places: list[tuple[int, int]],
    *,
    minimum: Sequence[int] = (),
    weights: Sequence[int] = (),
) -> list[list[int]]:
    """``count`` compact parts, grown from sources laid out as the vanilla ``places`` lie.

    The sources start well spread, landmasses taking them by size (``spread_sources``).
    The places, standardized as one cloud, go to the sources, standardized as another, in
    one exact assignment; each matched source then moves, on its own landmass, to the cell
    nearest its place in the sources' frame. Sources without a place stay. The parts then
    balance and relax as ``split``'s do.
    """
    sources = spread_sources(graph, members, count)
    spots = [(int(row), int(column)) for row, column in graph.centres[sources].tolist()]
    here, there = standard(spots), standard(places)
    chosen = minimum_assignment([[place_distance(point, spot) for spot in here] for point in there])
    landmass = {cell: piece for piece in pieces(graph, members) for cell in piece}
    matched = set(chosen)
    taken = {source for number, source in enumerate(sources) if number not in matched}
    for point, number in zip(there, chosen, strict=True):
        # A landmass holds at least as many cells as sources, so one is always free; the
        # lowest cell wins a tie (pieces are sorted).
        free = np.array([cell for cell in landmass[sources[number]] if cell not in taken])
        gap = ((graph.centres[free] - np.array(unstandard(point, spots))) ** 2).sum(axis=1)
        sources[number] = int(free[int(np.argmin(gap))])
        taken.add(sources[number])
    targets = [1] * count
    for source, weight in zip(chosen, weights, strict=bool(weights)):
        targets[source] = weight
    parts, _ = balanced_parts(
        graph,
        members,
        [[source] for source in sources],
        targets,
        movable=[True] * count,
        minimum=minimum,
    )
    return parts


def _continent_parts(  # noqa: PLR0913 - graph, geography and physical templates.
    graph: ContactGraph,
    cells: list[int],
    tally: _Tally,
    keys: list[str],
    *,
    physical: KeyMatcher,
    algorithm: int,
) -> list[list[int]]:
    if tally.continent == NEW_WORLD:
        return _bands(graph, cells, tally, keys, algorithm)
    minimum = [sum(len(tally.children[region]) for region in tally.children[key]) for key in keys]
    places = [tally.centre(key) for key in keys]
    parts = _placed(
        graph, cells, len(keys), places, minimum=minimum, weights=[tally.count[key] for key in keys]
    )
    pairing = physical.pair(
        parts,
        keys,
        centres=[centre_of(graph, part) for part in parts],
        places=places,
        place_weight=REGION_PLACE_WEIGHT,
        minimum=dict(zip(keys, minimum, strict=True)),
    )
    return _in_order(parts, pairing)


def _land_areas(  # noqa: PLR0913 - partition geometry, vanilla hierarchy and physical matching.
    graph: ContactGraph,
    cells: list[int],
    tally: _Tally,
    province_size: int,
    keys: KeySpace,
    *,
    physical: KeyMatcher,
    algorithm: int = CURRENT,
) -> list[_Area]:
    """Top-down: subcontinents and regions keep their vanilla keys, areas reuse theirs.

    Subcontinents are cut from the north at the land's waists, in their vanilla order and about
    their relative sizes (``neck_parts``); regions and below keep one piece per landmass.
    A subcontinent's regions are equal compact parts grown from sources laid out as the
    vanilla regions lie in it (``_placed``), with room for every original child area; they
    take their keys by place first, physical similarity second. A region's areas are equal
    compact parts that take their keys by physical similarity, place breaking ties
    (``KeyMatcher.pair``). Keys are chosen before provinces are made; size is scored, never
    rebalanced after scoring.
    """
    areas: list[_Area] = []
    subcontinents = sorted(tally.children[tally.continent])
    for subcontinent, sub_cells in zip(
        subcontinents,
        _continent_parts(
            graph, cells, tally, subcontinents, physical=physical, algorithm=algorithm
        ),
        strict=True,
    ):
        regions = sorted(tally.children[subcontinent])
        needs = [len(tally.children[region]) for region in regions]
        places = [tally.centre(region) for region in regions]
        region_parts = _placed(graph, sub_cells, len(regions), places, minimum=needs)
        regional_keys = physical.pair(
            region_parts,
            regions,
            centres=[centre_of(graph, part) for part in region_parts],
            places=places,
            place_weight=REGION_PLACE_WEIGHT,
            minimum=dict(zip(regions, needs, strict=True)),
        )
        for region_cells, region_key in zip(region_parts, regional_keys, strict=True):
            region = regions[region_key]
            vanilla = sorted(tally.children[region])
            wanted = _rounded(len(region_cells), province_size * AREA_PROVINCES)
            parts = split(graph, region_cells, min(len(region_cells), max(len(vanilla), wanted)))
            pairing = physical.pair(
                parts,
                vanilla,
                centres=[centre_of(graph, part) for part in parts],
                places=[tally.centre(key) for key in vanilla],
                place_weight=AREA_PLACE_WEIGHT,
            )
            for part, key in zip(parts, pairing, strict=True):
                name = vanilla[key] if key >= 0 else keys.next("rnw_area_", 4)
                provinces = split(graph, part, max(1, _rounded(len(part), province_size)))
                areas.append(
                    _Area(name, (region, subcontinent, tally.continent), provinces, key < 0)
                )
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


def _vanilla_seas(  # noqa: PLR0913 - base geometry, region scope and retained shores.
    game_map: Eu5Map,
    canvas: Canvas,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    *,
    selected: Collection[str] = (NEW_WORLD,),
    adjacent: Collection[int] = (),
) -> list[_SeaArea]:
    index = {key: number for number, key in enumerate(game_map.keys)}
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    touched = canvas.removed | canvas.trimmed
    members: dict[str, list[int]] = {}
    for location in hierarchy.values():
        members.setdefault(location.area, []).append(index[location.key])
    names = sorted(
        {
            hierarchy[game_map.keys[label]].area
            for label in set(np.flatnonzero(touched & sea).tolist()).union(adjacent)
        }
    )
    seas: list[_SeaArea] = []
    for name in names:
        labels = members[name]
        first = hierarchy[game_map.keys[labels[0]]]
        replaced = [label for label in labels if canvas.removed[label]]
        placed = (
            replaced
            or [label for label in labels if canvas.trimmed[label]]
            or [label for label in labels if label in adjacent]
        )
        row = sum(int(geometry.rows[label]) for label in placed) // len(placed)
        column = sum(int(geometry.columns[label]) for label in placed) // len(placed)
        seas.append(
            _SeaArea(
                name,
                first.region,
                first.continent in selected,
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


def _independent_coasts(coasts: dict[str, list[int]], boundary: set[int]) -> dict[str, list[int]]:
    """Keep only shores that can start a regional sea without touching the Old World."""
    return {
        region: inland
        for region, cells in coasts.items()
        if (inland := [cell for cell in cells if cell not in boundary])
    }


def outside_contacts(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, offset: int
) -> set[tuple[int, int]]:
    """(vanilla label, generated cell) pairs that touch across the canvas edge."""
    height, width = canvas.shape
    stop = canvas.col0 + int(canvas.mask.shape[1]) + 1
    columns = (np.arange(canvas.col0 - 1, stop, dtype=np.int64) - canvas.roll) % width
    contacts: set[tuple[int, int]] = set()
    full = canvas.mask.shape[1] == width
    if full:
        columns = columns[1:-1]
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS + 1))
        generated = (
            world.labels[rows]
            if full
            else np.pad(world.labels[rows], ((0, 0), (1, 1)), constant_values=-1)
        )
        combined = np.where(
            generated >= 0,
            generated + offset,
            np.take(game_map.labels[rows], columns, axis=1),
        ).astype(np.int32)
        pairs = adjacency_pairs(combined, wrap_x=full)
        low, high = pairs >> PAIR_SHIFT, pairs & LOW_BITS
        across = pairs[(low < offset) & (high >= offset)]
        contacts.update((low, high - offset) for low, high in unpack_pairs(across))
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


def _protect_ocean_boundary(
    graph: ContactGraph,
    ocean_sources: list[list[int]],
    shore: set[int],
    boundary: set[int],
) -> set[int]:
    """Pin connected ocean paths between passable Old World seas and open water."""
    if not boundary:
        return set()
    frontier: list[tuple[int, int, int]] = []
    routes: dict[int, tuple[int, int]] = {}
    for number, sources in enumerate(ocean_sources):
        for source in sources:
            heapq.heappush(frontier, (0, number, source))
    while frontier and not boundary.issubset(routes):
        distance, number, cell = heapq.heappop(frontier)
        if cell in routes:
            continue
        routes[cell] = (number, distance)
        for other, length in graph.links[cell]:
            if other not in routes:
                heapq.heappush(
                    frontier,
                    (distance + length + (100_000 if other in shore else 0), number, other),
                )
    if not boundary.issubset(routes):
        message = "Old World sea boundary cannot reach an open ocean area"
        raise IdentityError(message)
    protected: set[int] = set()

    def order(other: int) -> tuple[int, int]:
        return routes[other][1], other

    for target in sorted(boundary):
        number = routes[target][0]
        protected.add(number)
        current = target
        while current not in ocean_sources[number]:
            ocean_sources[number].append(current)
            current = min(
                (
                    other
                    for other, _ in graph.links[current]
                    if other in routes
                    and routes[other][0] == number
                    and routes[other][1] < routes[current][1]
                ),
                key=order,
            )
    return protected


def _sea_areas(  # noqa: PLR0913, PLR0915 - sea areas read the vanilla seas, coasts and parents.
    graph: ContactGraph,
    cells: list[int],
    seas: list[_SeaArea],
    contacts: set[tuple[int, int]],
    *,
    coasts: dict[str, list[int]],
    parents: dict[str, tuple[str, str, str]],
    keys: KeySpace,
    boundary: set[int] | None = None,
    oceans_continents: Collection[str] = OCEANS,
    compose: bool = False,
    intercontinental: Collection[int] = (),
) -> tuple[list[_Area], set[str]]:
    """Independent coastal water joins its land region; the open ocean keeps its areas.

    Every land region grows its water from the zones on its shore, so each piece of a
    region's sea touches that region's land. The coastal share of all water is the
    vanilla one, and a region's share follows its shore length; a small piece of a
    region's water beside its largest one joins the water around it. A region's water is
    split into its vanilla sea areas (nearest first) and new ones as its size needs.
    An ocean area cut by the canvas grows from the generated zones that touch its
    remainder (the first by name if a zone touches several), so it stays joined to it;
    every other ocean area starts at the open zone nearest its replaced zones. Returns
    the areas and the names of the cut ocean areas, which may have one piece per
    stretch of remainder. A region whose only generated shore is at the Old World
    boundary has no independent coastal sea; those zones stay in the protected ocean
    hierarchy instead.
    """
    ocean_names = {
        sea.name for sea in seas if not sea.coastal and parents[sea.name][2] in oceans_continents
    }
    owner = {
        label: sea.name
        for sea in reversed(seas)
        if not compose or sea.name in ocean_names
        for label in sea.remaining
    }
    water = set(cells)
    touching: dict[int, set[str]] = {}
    for label, cell in contacts:
        if label in owner and cell in water:
            touching.setdefault(cell, set()).add(owner[label])
    anchors: dict[str, list[int]] = {}
    for cell in sorted(touching):
        anchors.setdefault(min(touching[cell]), []).append(cell)
    oceans = [
        sea
        for sea in seas
        if sea.name in ocean_names and (not sea.remaining or anchors.get(sea.name))
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
    original_sources = {cell for sources in ocean_sources for cell in sources}
    common_oceans = [
        number for number, sea in enumerate(oceans) if parents[sea.name][2] in oceans_continents
    ]
    protected_crossings = _protect_ocean_boundary(
        graph, [ocean_sources[i] for i in common_oceans], shore, set(intercontinental)
    )
    protected_oceans = _protect_ocean_boundary(graph, ocean_sources, shore, boundary or set())
    protected_oceans.update(common_oceans[i] for i in protected_crossings)
    reserved_ocean = {cell for sources in ocean_sources for cell in sources} - original_sources
    for region in regions:
        coasts[region] = [cell for cell in coasts[region] if cell not in reserved_ocean]
        if not coasts[region]:
            message = f"Region {region} has no coastal sea outside the ocean boundary"
            raise IdentityError(message)
    shore = {zone for zones in coasts.values() for zone in zones}
    length = max(1, len(shore))
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
        movable=[False] * len(regions)
        + [
            not sea.remaining and number not in protected_oceans
            for number, sea in enumerate(oceans)
        ],
        pinned=[True] * len(regions)
        + [not sea.remaining or number in protected_oceans for number, sea in enumerate(oceans)],
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


def _check_shores(
    graph: ContactGraph,
    areas: list[_Area],
    coasts: dict[str, list[int]],
    retained: Collection[int] = (),
) -> None:
    """Every piece touches that region's land or the retained water it continues."""
    water: dict[str, list[int]] = {}
    for area in areas:
        if area.parents[0] in coasts:
            water.setdefault(area.parents[0], []).extend(
                cell for province in area.provinces for cell in province
            )
    for region, cells in sorted(water.items()):
        shore = set(coasts[region])
        shore.update(retained)
        if any(not shore.intersection(piece) for piece in pieces(graph, cells)):
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


def _inland_areas(
    graph: ContactGraph,
    basins: tuple[tuple[int, ...], ...],
    coasts: dict[str, list[int]],
    parents: dict[str, tuple[str, str, str]],
    keys: KeySpace,
) -> list[_Area]:
    """Give each closed sea new areas in its dominant shore region, never an ocean identity."""
    areas: list[_Area] = []
    for basin in basins:
        inside = set(basin)
        shores = {region: len(inside.intersection(cells)) for region, cells in coasts.items()}
        if not any(shores.values()):
            message = "An inland sea has no generated shore region"
            raise IdentityError(message)
        region = min(shores, key=lambda name: (-shores[name], name))
        for area in split(graph, list(basin), max(1, _rounded(len(basin), SEA_AREA_ZONES))):
            provinces = split(graph, area, max(1, _rounded(len(area), SEA_PROVINCE_ZONES)))
            areas.append(_Area(keys.next("rnw_sea_area_", 4), parents[region], provinces, new=True))
    return areas


def _retained_pockets(  # noqa: PLR0913 - physical sea pieces and the retained areas they meet.
    graph: ContactGraph,
    cells: list[int],
    coasts: dict[str, list[int]],
    *,
    contacts: set[tuple[int, int]],
    seas: list[_SeaArea],
    parents: dict[str, tuple[str, str, str]],
    oceans: Collection[str] = OCEANS,
) -> tuple[list[_Area], set[int], set[int]]:
    """Keep disconnected generation cutouts with the vanilla coastal waters around them.

    This occurs where an international coast includes water in the selected continent's
    hierarchy that also borders retained land. A cutout with no generated shore and no
    open-ocean contact cannot be assigned by proximity to a different stretch of coast.
    """
    inside = set(cells)
    sources = {label: sea for sea in seas for label in sea.remaining}
    laid = {cell for water in coasts.values() for cell in water}
    touches: dict[int, Counter[str]] = {}
    for label, cell in contacts:
        source = sources.get(label)
        if source is None or cell not in inside:
            continue
        if parents[source.name][2] in oceans:
            laid.add(cell)
        else:
            touches.setdefault(cell, Counter())[source.name] += 1
    assigned: dict[str, list[list[int]]] = {}
    used, roots = set[int](), set[int]()
    for piece in pieces(graph, cells):
        if laid.intersection(piece):
            continue
        totals: Counter[str] = Counter()
        for cell in piece:
            totals.update(touches.get(cell, ()))
        if not totals:
            message = f"Sea cutout at cell {piece[0]} has no coast or retained sea"
            raise IdentityError(message)
        name = min(totals, key=lambda key: (-totals[key], key))
        roots.update(cell for cell in piece if cell in touches and name in touches[cell])
        used.update(piece)
        assigned.setdefault(name, []).extend(
            split(graph, piece, max(1, _rounded(len(piece), SEA_PROVINCE_ZONES)))
        )
    return (
        [_Area(key, parents[key], parts, new=False) for key, parts in sorted(assigned.items())],
        used,
        roots,
    )


def _land_partition(  # noqa: PLR0913 - cell graph, regional hierarchy and portable keys.
    is_land: list[bool],
    tally: _Tally,
    units: LocationUnits,
    province_size: int,
    keys: KeySpace,
    *,
    physical: KeyMatcher,
    algorithm: int,
) -> list[_Area]:
    representatives = [
        cell for cell, flag in enumerate(is_land) if flag and units.owner[cell] == cell
    ]
    land = contact_graph(
        units.centres,
        units.edges,
        [flag and units.owner[cell] == cell for cell, flag in enumerate(is_land)],
    )
    areas = _land_areas(
        land, representatives, tally, province_size, keys, physical=physical, algorithm=algorithm
    )
    return [
        replace(
            area,
            provinces=[
                sorted(member for cell in province for member in units.members[cell])
                for province in area.provinces
            ],
        )
        for area in areas
    ]


@dataclass(frozen=True, slots=True)
class RegionalLand:
    """Authoritative land partitions and their physical location units."""

    areas: list[_Area]
    units: LocationUnits
    physical_keys: list[dict[str, object]]


def plan_regional_land(  # noqa: PLR0913 - installed inputs and one generated region.
    game_map: Eu5Map,
    domain: Domain,
    world: NewWorld,
    hierarchy: dict[str, Location],
    *,
    attributes: dict[str, dict[str, str]],
    pairs: Sequence[tuple[int, int]],
    biomes: CellBiomes,
    settings: NewWorldSettings,
    keys: KeySpace,
    algorithm: int = CURRENT,
) -> RegionalLand:
    """Assign the region's own hierarchy before the common water identity pass."""
    continent = domain.continent.key
    geometry = regional_geometry(game_map, domain, hierarchy)
    tally = _land_tally(
        game_map,
        hierarchy,
        geometry,
        geometry.pixels,
        geometry.pixels > 0,
        col0=0,
        continent=continent,
    )
    physical = physical_keys(
        game_map,
        hierarchy,
        attributes,
        pairs,
        world=world,
        biomes=biomes,
        pixels=geometry.pixels.tolist(),
        continent=continent,
    )
    units = _units(world, biomes)
    is_land = [kind in LAND_FAMILY for kind in world.classes]
    areas = _land_partition(
        is_land, tally, units, settings.province_size, keys, physical=physical, algorithm=algorithm
    )
    _check_pieces(
        contact_graph(world.centroids, world.edges, is_land),
        areas,
        depth=len(LEVELS) - 1,
        exempt=set(),
    )
    return RegionalLand(areas, units, physical.assignments)


def _hierarchy(  # noqa: PLR0913, PLR0917 - the hierarchy reads the map, canvas and world.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    settings: NewWorldSettings,
    keys: KeySpace,
    physical: KeyMatcher,
    units: LocationUnits,
    algorithm: int,
) -> tuple[list[_Area], set[str]]:
    """Land areas, then sea areas, all checked; and the names of the cut ocean areas."""
    is_land = [kind in LAND_FAMILY for kind in world.classes]
    areas = _land_partition(
        is_land,
        _vanilla_land(game_map, canvas, hierarchy, geometry, geometry.pixels),
        units,
        settings.province_size,
        keys,
        physical=physical,
        algorithm=algorithm,
    )
    sea_areas, anchored = _water_areas(
        game_map, canvas, world, hierarchy, geometry, areas=areas, keys=keys
    )
    physical_land = contact_graph(world.centroids, world.edges, is_land)
    # A subcontinent may hold two pieces of a landmass since epoch 63; before, one (bands).
    one_piece_up_to = len(LEVELS) - (1 if algorithm >= SUBCONTINENT_WAISTS else 0)
    _check_pieces(physical_land, areas, depth=one_piece_up_to, exempt=set())
    return areas + sea_areas, anchored


def _water_areas(  # noqa: PLR0913 - shared waters read the final coast and its land hierarchy.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    *,
    areas: list[_Area],
    keys: KeySpace,
    selected: Collection[str] = (NEW_WORLD,),
    oceans_continents: frozenset[str] = OCEANS,
    intercontinental: frozenset[int] = NO_CELLS,
) -> tuple[list[_Area], set[str]]:
    count = len(game_map.keys)
    is_sea = [kind is CellClass.SEA for kind in world.classes]
    sea = contact_graph(world.centroids, world.edges, is_sea)
    region_of = {
        cell: area.parents[0] for area in areas for cells in area.provinces for cell in cells
    }
    contacts = outside_contacts(game_map, canvas, world, count)
    boundary = {
        cell
        for label, cell in contacts
        if (
            game_map.classes[label] is CellClass.SEA
            or (world.wrap_x and is_sea[cell] and game_map.classes[label] is CellClass.LAND)
        )
        and (is_sea[cell] or not world.wrap_x)
        and game_map.continents[label] not in oceans_continents.union(selected)
    }
    adjacent: set[int] = (
        {
            label
            for label, cell in contacts
            if is_sea[cell] and game_map.classes[label] is CellClass.SEA
        }
        if world.wrap_x
        else set()
    )
    basins = inland_seas(world)
    inland = {cell for basin in basins for cell in basin}
    all_coasts = _coasts(world, is_sea, region_of)
    coasts = _independent_coasts(
        {
            region: [cell for cell in cells if cell not in inland]
            for region, cells in all_coasts.items()
        },
        boundary | intercontinental,
    )
    parents = _area_parents(hierarchy)
    parents.update({area.parents[0]: area.parents for area in areas})
    seas = _vanilla_seas(
        game_map, canvas, hierarchy, geometry, selected=selected, adjacent=adjacent
    )
    open_cells = [cell for cell, flag in enumerate(is_sea) if flag and cell not in inland]
    pockets, assigned, roots = (
        _retained_pockets(
            sea,
            open_cells,
            coasts,
            contacts=contacts,
            seas=seas,
            parents=parents,
            oceans=oceans_continents,
        )
        if world.wrap_x
        else ([], set[int](), set[int]())
    )
    retained_coasts = {area.name for area in pockets}
    sea_areas, anchored = _sea_areas(
        sea,
        [cell for cell in open_cells if cell not in assigned],
        [place for place in seas if place.name not in retained_coasts],
        contacts,
        coasts=coasts,
        parents=parents,
        keys=keys,
        boundary=boundary - assigned,
        oceans_continents=oceans_continents,
        compose=world.wrap_x,
        intercontinental=intercontinental,
    )
    anchored.update(retained_coasts)
    sea_areas.extend(pockets)
    sea_areas.extend(_inland_areas(sea, basins, all_coasts, parents, keys))
    _check_pieces(sea, sea_areas, depth=2, exempt=anchored)
    _check_shores(sea, sea_areas, all_coasts, roots)
    return sea_areas, anchored


def _units(world: NewWorld, biomes: CellBiomes) -> LocationUnits:
    return location_units(
        world,
        list(
            zip(
                biomes.climate,
                biomes.vegetation,
                biomes.topography,
                biomes.raw_material,
                strict=True,
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class _NamedAreas:
    areas: list[_Area]
    anchored: set[str]
    owner: Sequence[int]
    physical_keys: list[dict[str, object]]
    continents: Collection[str] = (NEW_WORLD,)
    oceans_continents: Collection[str] = OCEANS


def plan_composed_identities(  # noqa: PLR0913 - regional assignments and the common finished coast.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    *,
    geometry: VanillaGeometry,
    regions: Mapping[str, tuple[RegionalLand, Sequence[int]]],
    topography: Sequence[str],
    seed: int,
    keys: KeySpace,
    waters: Waters,
    algorithm: int = CURRENT,
) -> Plan:
    """Assign one key and colour space after combining land and settling the shared seas."""
    areas: list[_Area] = []
    owner = list(range(len(world.classes)))
    physical: list[dict[str, object]] = []
    origins: list[set[str]] = [set() for _ in world.classes]
    for name, (regional, cells) in regions.items():
        for cell in cells:
            origins[cell].add(name)
        areas.extend(
            replace(area, provinces=[[cells[cell] for cell in p] for p in area.provinces])
            for area in regional.areas
        )
        for cell, root in enumerate(regional.units.owner):
            if cell != root:
                owner[cells[cell]] = cells[root]
        physical.extend(regional.physical_keys)
    oceans = frozenset(name for name in game_map.continents if name.endswith("_ocean_continent"))
    intercontinental = frozenset(
        cell
        for first, second in world.edges
        if len(origins[first] | origins[second]) > 1
        for cell in (first, second)
        if world.classes[cell] is CellClass.SEA
    )
    sea_areas, anchored = _water_areas(
        game_map,
        canvas,
        world,
        hierarchy,
        geometry,
        areas=areas,
        keys=keys,
        selected=regions.keys(),
        oceans_continents=oceans,
        intercontinental=intercontinental,
    )
    return _name_areas(
        game_map,
        world,
        hierarchy,
        _NamedAreas(areas + sea_areas, anchored, owner, physical, regions.keys(), oceans),
        seed=seed,
        keys=keys,
        waters=waters,
        topography=topography,
        algorithm=algorithm,
    )


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
    biomes: CellBiomes,
    algorithm: int = CURRENT,
) -> Plan:
    """Assign keys, colours, names and parents to every generated cell.

    Land is split top-down into the vanilla subcontinents and regions, then into areas
    and provinces. Water near a shore joins the region of that shore and is split into
    its sea areas, the open ocean into the vanilla ocean areas the canvas touches; both
    then into provinces. Every part is compact and connected on its landmass or water
    body, and every piece of a region's water touches the region's land. Land is named at
    random; water is named for its shape (``seanames``): one sea, one name.
    """
    units = _units(world, biomes)
    areas, anchored = _hierarchy(
        game_map, canvas, world, hierarchy, geometry, settings, keys, physical, units, algorithm
    )
    return _name_areas(
        game_map,
        world,
        hierarchy,
        _NamedAreas(areas, anchored, units.owner, physical.assignments),
        seed=seed,
        keys=keys,
        waters=waters,
        topography=biomes.topography,
        algorithm=algorithm,
    )


def _name_areas(  # noqa: PLR0913 - geography, seeds and water conventions for one key space.
    game_map: Eu5Map,
    world: NewWorld,
    hierarchy: dict[str, Location],
    named: _NamedAreas,
    *,
    seed: int,
    keys: KeySpace,
    waters: Waters,
    topography: Sequence[str],
    algorithm: int,
) -> Plan:
    plan = Plan(
        cells=[], anchored_sea_areas=sorted(named.anchored), physical_keys=named.physical_keys
    )
    province_names = NameGenerator(seed, "provinces")
    area_names = NameGenerator(seed, "areas")
    province_of = [""] * len(world.classes)
    area_of: list[_Area | None] = [None] * len(world.classes)
    for area in named.areas:
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
        else Placement(province_of[cell], area.name, area.parents[2] in named.oceans_continents)
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
                else _land_name(location_names.next(), kind, topography[index], algorithm),
                color=colors[index],
                kind=kind,
                province=province_of[index],
                area=area.name,
                region=region,
                subcontinent=subcontinent,
                continent=continent,
            )
        )
    plan.cells = [plan.cells[unit] for unit in named.owner]
    reused = {cell.area for cell in plan.cells} | {cell.region for cell in plan.cells}
    override_names = NameGenerator(seed, "overrides")
    for name in sorted(reused):
        if name not in plan.display_overrides and _in_continents(hierarchy, name, named.continents):
            plan.display_overrides[name] = override_names.next()
    vanilla_new_world_areas = {
        location.area for location in hierarchy.values() if location.continent in named.continents
    }
    plan.dropped_areas = sorted(vanilla_new_world_areas - {cell.area for cell in plan.cells})
    return plan


def _area_parents(hierarchy: dict[str, Location]) -> dict[str, tuple[str, str, str]]:
    return {
        location.area: (location.region, location.subcontinent, location.continent)
        for location in hierarchy.values()
    }


def _land_name(word: str, kind: CellClass, topography: str, algorithm: int) -> Name:
    """A land cell's name: its word, with the term of a wasteland (by its topography since epoch
    64) or a lake."""
    term = NAME_TERM.get(kind)
    if term is not None and kind is CellClass.WASTELAND and algorithm >= NATURAL_WASTELANDS:
        term = WASTE_TERMS.get(topography, term)
    return word if term is None else Phrase(term, word)


def _in_continents(hierarchy: dict[str, Location], name: str, continents: Collection[str]) -> bool:
    return any(
        location.continent in continents and name in {location.area, location.region}
        for location in hierarchy.values()
    )
