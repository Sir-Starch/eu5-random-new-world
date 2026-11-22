"""Shared ownership plan for the geography of a world with selected continents."""

# NumPy stubs type boolean indexing and reductions as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from dataclasses import dataclass, replace
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_canvas import NEW_WORLD, CanvasError, roll_for, select_canvas
from rnw.eu5_pacific import IslandGroup, ocean_island_groups
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.progress import checkpoint
from rnw.rng import SplitMix64, derive_seed
from rnw.settings import PRESETS, REGIONAL_PRESETS, NewWorldSettings
from rnw.topology import (
    adjacency_lengths,
    adjacency_pairs,
    distance_from,
    label_components,
    unpack_pairs,
)
from rnw.watersheds import DENSITY_STEP

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map

REFERENCE_WIDTH: Final[int] = 16_384
BAND_ROWS: Final[int] = 256
RETAINED_SHORE_PX: Final[int] = 160
CONTINENTAL_SHORE_AREA_PX: Final[int] = 131_072
OCEAN_GRID_COLUMNS: Final[int] = 512
OPEN_OCEAN_BAND_PX: Final[int] = 1850
PACIFIC_SHELF_PX: Final[int] = 2750
ISLAND_POOL: Final[int] = 8  # Coast and offshore water radius, in ocean grid columns.
# In a shared world no regional shelf gets more than this fraction of the full
# map as new ocean. Existing land is always taken in full.
SHARED_OCEAN_DIVISOR: Final[int] = 6
AFRICA_LAND_CHANCE: Final[int] = 40
EUROPE_STRAIT_CHANCE: Final[int] = 35
EUROPE_STRAIT_GAP: Final[int] = 7
OCEAN_SPECK_PX: Final[int] = 1024
AFRICAN_NORTH_REACH_PX: Final[int] = 512
# Open water nearer to retained Eurasian land than to any generated continent stays
# Eurasian when Eurasian land lies within this reach on both sides of it along some
# line, as in a bay or a passage between shores. Open ocean stays generated.
EURASIAN_SPAN_PX: Final[int] = 1100
# Sight lines as (rows, columns) per step; slanted ones catch a passage between two
# shores that no row, column or diagonal joins, such as south of Greenland.
EURASIAN_LINES: Final[tuple[tuple[int, int], ...]] = (
    (0, 1),
    (1, 0),
    (1, 1),
    (1, -1),
    (1, 2),
    (1, -2),
    (2, 1),
    (2, -1),
)
# Fixed sea positions of the War of the Straits, the Battle of Lepanto and
# the installed exploration test. Their retained coasts keep these anchors.
NAVAL_ANCHORS: Final[frozenset[str]] = frozenset(
    {"cape_lecton", "dardanelles", "gulf_patras", "favaritx_cape"}
)


@dataclass(frozen=True, slots=True)
class Continent:
    key: str
    preset: str
    ocean_band_px: int | None = None
    land_neighbor: str | None = None
    island_band_px: int = 224

    def geography(self, preset: str | None = None) -> NewWorldSettings:
        """A supported preset expressed at this continent's shore scale."""
        name = self.preset if preset is None else preset
        if name not in PRESETS:
            message = f"Unknown land preset {name}"
            raise CanvasError(message)
        settings = PRESETS[name].new_world
        _validate_geography(self, settings)
        if self.ocean_band_px is None:
            return settings
        return replace(settings, ocean_band_px=self.ocean_band_px, expand_oceans=0)


CONTINENTS: Final[Mapping[str, Continent]] = MappingProxyType(
    {
        region.key: region
        for region in (
            Continent(NEW_WORLD, "continents"),
            Continent("africa", *REGIONAL_PRESETS["africa"], land_neighbor="asia"),
            Continent("oceania", *REGIONAL_PRESETS["oceania"]),
        )
    }
)


AFRICA: Final[str] = "africa"
AFRICA_NUMBER: Final[int] = tuple(CONTINENTS).index(AFRICA)


def _validate_geography(continent: Continent, settings: NewWorldSettings) -> None:
    if continent.key != NEW_WORLD and (
        settings.landform or settings.template_permille or settings.keep_geography
    ):
        message = "The Wall, Omerika and keeping vanilla geography are American options"
        raise CanvasError(message)


@dataclass(frozen=True, slots=True, eq=False)
class Domain:
    """A wrapped window with exclusive replacement pixels in its part of the map."""

    continent: Continent
    first_column: int
    map_width: int
    mask: NDArray[np.bool_]
    footprint: NDArray[np.bool_]
    first_row: int = 0
    # Local pixels where generated land can meet passable retained terrain.
    land_interface: NDArray[np.bool_] | None = None
    # Dry land of the eligible retained neighbor throughout the regional window.
    contact_land: NDArray[np.bool_] | None = None
    legacy_canvas: Canvas | None = None
    join_asia: bool = False
    # 1 keeps water at the European shore, 2 admits an African landing.
    strait: NDArray[np.uint8] | None = None
    island_sites: tuple[tuple[int, int, int], ...] = ()
    shared_ocean: bool = False
    north_water_rows: int = 0
    groups: tuple[IslandGroup, ...] = ()
    footprints: tuple[Footprint, ...] = ()

    def spans(self) -> tuple[tuple[slice, slice], ...]:
        """Regional and world column spans in west-to-east order."""
        width = int(self.mask.shape[1])
        first = min(width, self.map_width - self.first_column)
        initial = (slice(0, first), slice(self.first_column, self.first_column + first))
        if first == width:
            return (initial,)
        return (initial, (slice(first, width), slice(0, width - first)))

    @property
    def rows(self) -> slice:
        return slice(self.first_row, self.first_row + self.mask.shape[0])

    @property
    def seam(self) -> int | None:
        """Local column of the global wrap, when it lies inside the strip."""
        column = self.map_width - self.first_column
        return column if column < self.mask.shape[1] else None

    @property
    def watershed_seam(self) -> int | None:
        """The display cut when it lies within or exactly at an edge of the window."""
        if self.first_column == 0:
            return 0
        column = self.map_width - self.first_column
        return column if column <= self.mask.shape[1] else None


def _membership(game_map: Eu5Map, continent: str) -> NDArray[np.bool_]:
    return np.fromiter((name == continent for name in game_map.continents), dtype=bool)


def _coastal_claim(
    claim: NDArray[np.bool_], footprint: NDArray[np.bool_], marine: NDArray[np.bool_]
) -> NDArray[np.bool_]:
    """Keep claimed waters connected to the selected land, the sea margin or a map edge."""
    labels = label_components((claim | marine).astype(np.int32))
    open_ = np.zeros(int(labels.max()) + 1, dtype=bool)
    open_[labels[footprint]] = True
    for border in (labels[0], labels[-1], labels[:, 0], labels[:, -1]):
        open_[border] = True
    return claim & open_[labels]


def _legacy_domain(game_map: Eu5Map, settings: NewWorldSettings) -> Domain:
    canvas = select_canvas(
        game_map,
        settings.ocean_band_px,
        expanded=bool(settings.expand_oceans or settings.landform),
    )
    if canvas.template is None:
        message = "The American canvas has no vanilla footprint"
        raise CanvasError(message)
    return Domain(
        CONTINENTS[NEW_WORLD],
        int(canvas.world_column(0)),
        int(game_map.labels.shape[1]),
        canvas.mask,
        canvas.template,
        legacy_canvas=canvas,
    )


def _extent(used: NDArray[np.bool_], reach: int) -> tuple[int, int]:
    """Find the shortest wrapped column interval with enough padding for the shore."""
    roll = roll_for(used)
    columns = np.flatnonzero(np.roll(used, roll))
    if not columns.size:
        message = "A selected continent has no land footprint"
        raise CanvasError(message)
    first = max(0, int(columns[0]) - reach)
    stop = min(used.size, int(columns[-1]) + reach + 1)
    if stop - first >= used.size:
        message = "A selected continent leaves no open cut for its geography strip"
        raise CanvasError(message)
    return (first - roll) % used.size, stop - first


def _read[Pixel: np.generic](labels: NDArray[Pixel], first: int, width: int) -> NDArray[Pixel]:
    """Borrow an unwrapped window or copy only the two required pieces across the seam."""
    stop = first + width
    if stop <= labels.shape[1]:
        return labels[:, first:stop]
    return np.concatenate((labels[:, first:], labels[:, : stop - labels.shape[1]]), axis=1)


@dataclass(frozen=True, slots=True, eq=False)
class OceanClaims:
    """One coarse, wrapped claim for every open-water block in the map."""

    owners: NDArray[np.int8]
    step: int
    islands: tuple[tuple[int, int, int], ...] = ()
    # Square blocks of `step` pixels that retained Eurasian land reaches first.
    eurasian: NDArray[np.bool_] | None = None
    # First pixel row Africa may claim; its land and its water both stop above it.
    north_africa: int = 0
    # Blocks of the claim grid that Africa would have taken above that row.
    reserved: NDArray[np.bool_] | None = None

    def rows(self, rows: NDArray[np.int64]) -> NDArray[np.int64]:
        return rows // (2 * self.step)

    def columns(self, columns: NDArray[np.int64]) -> NDArray[np.int64]:
        return columns // self.step


@dataclass(frozen=True, slots=True, eq=False)
class SharedWater:
    """The preserved Eurasian waters and the continental claims around them."""

    owners: NDArray[np.int8]
    north_africa: int
    groups: tuple[tuple[int, IslandGroup], ...]


def ocean_speck_limit(width: int) -> int:
    return max(1, OCEAN_SPECK_PX * width**2 // REFERENCE_WIDTH**2)


def _continental_cores(
    game_map: Eu5Map, sea: NDArray[np.bool_]
) -> tuple[NDArray[np.bool_], NDArray[np.int8]]:
    """Keep substantial land with its own region; the shelf owns outlying islets."""
    numbers = {name: index for index, name in enumerate(CONTINENTS)}
    kinds = np.array([numbers.get(name, -1) for name in game_map.continents], dtype=np.int8)
    kinds[sea] = -1
    original = kinds[game_map.labels]
    land = original >= 0
    parts = label_components(original.astype(np.int32), wrap_x=True)
    area = np.bincount(parts[land], minlength=int(parts.max()) + 1)
    minimum = max(
        1, CONTINENTAL_SHORE_AREA_PX * game_map.labels.shape[1] ** 2 // REFERENCE_WIDTH**2
    )
    original[(area < minimum)[parts]] = -1
    return kinds >= 0, original


def _connect_owners(owners: NDArray[np.int8]) -> NDArray[np.int8]:
    """Grow each main canvas over adjacent unconnected fragments."""
    parts = label_components(owners.astype(np.int32), wrap_x=True)
    count = int(parts.max()) + 1
    values = np.full(count, -1, dtype=np.int8)
    sizes = np.zeros(count, dtype=np.int64)
    for first in range(0, len(parts), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        block = parts[rows]
        values[block] = owners[rows]
        sizes += np.bincount(block.ravel(), minlength=count)
    connected = np.full(count, -1, dtype=np.int8)
    for number in range(len(CONTINENTS)):
        candidates = np.flatnonzero(values == number)
        if candidates.size:
            connected[candidates[np.argmax(sizes[candidates])]] = number
    pairs, lengths = adjacency_lengths(parts, wrap_x=True)
    links: dict[int, list[tuple[int, int]]] = {}
    for (first, second), length in zip(unpack_pairs(pairs), lengths.tolist(), strict=True):
        if values[first] >= 0 and values[second] >= 0:
            links.setdefault(first, []).append((second, length))
            links.setdefault(second, []).append((first, length))
    heap = [
        (-length, int(connected[cell]), other)
        for cell in np.flatnonzero(connected >= 0).tolist()
        for other, length in links.get(cell, ())
    ]
    heapq.heapify(heap)
    while heap:
        _, number, cell = heapq.heappop(heap)
        if connected[cell] >= 0:
            continue
        connected[cell] = number
        for other, length in links.get(cell, ()):
            if connected[other] < 0:
                heapq.heappush(heap, (-length, number, other))
    return connected[parts]


def _own_enclosed_specks(
    owners: NDArray[np.int8], specks: NDArray[np.bool_], parts: NDArray[np.int32]
) -> NDArray[np.int8]:
    """Give a water speck to the one canvas that wholly surrounds it.

    A speck inside replaced land is part of that land's canvas, so its location is
    not cut. A speck that touches retained land or water stays with the retained map.
    """
    combined = np.empty(owners.shape, dtype=np.int32)
    for first in range(0, len(owners), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        combined[rows] = np.where(specks[rows], parts[rows] + len(CONTINENTS) + 1, owners[rows] + 1)
    around: dict[int, set[int]] = {}
    for first, second in unpack_pairs(adjacency_pairs(combined, wrap_x=True)):
        for speck, other in ((first, second), (second, first)):
            if speck > len(CONTINENTS) >= other:
                around.setdefault(speck, set()).add(other)
    del combined
    lookup = np.full(int(parts.max()) + 1, -1, dtype=np.int8)
    for speck, neighbours in around.items():
        if len(neighbours) == 1 and 0 not in neighbours:
            lookup[speck - len(CONTINENTS) - 1] = min(neighbours) - 1
    for first in range(0, len(owners), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        owners[rows] = np.where(specks[rows], lookup[parts[rows]], owners[rows])
    return owners


def _rejoin_fragments(
    labels: NDArray[np.int32],
    claimed: NDArray[np.int8],
    connected: NDArray[np.int8],
    solid: NDArray[np.bool_],
) -> NDArray[np.int8]:
    """Settle the fragments that touch no canvas through retained water.

    Replaced land is removed whole. A small fragment of a location whose body lies in a canvas
    stays out of it, among the retained waters round it, and the export gives it to them
    (``continent_world.absorb_land_fragments``): left with the canvas it would stand as a
    generated location of a few pixels with no neighbour. Any other fragment stays with the
    canvas that claimed it, and a larger location stranded wholly there is a planning error
    rather than a hole to leave quietly.
    """
    count = int(labels.max()) + 1
    limit = ocean_speck_limit(labels.shape[1])
    owned = np.zeros(count, dtype=np.int64)
    stranded = np.zeros(count, dtype=np.int64)
    for first in range(0, len(labels), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        block = labels[rows]
        owned += np.bincount(block[connected[rows] >= 0], minlength=count)
        stranded += np.bincount(
            block[(claimed[rows] >= 0) & (connected[rows] < 0)], minlength=count
        )
    whole = (stranded > 0) & (owned == 0)
    if np.any(stranded[whole] >= limit):
        message = "A generated location is stranded among retained waters"
        raise CanvasError(message)
    # The land of a location that has a body in a canvas; its stranded pieces are the fragments.
    bodied = solid & (owned > 0)
    land = np.zeros(labels.shape, dtype=bool)
    for first in range(0, len(labels), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        land[rows] = (claimed[rows] >= 0) & (connected[rows] < 0) & bodied[labels[rows]]
    if land.any():
        parts = label_components(land.astype(np.int32), wrap_x=True)
        sizes = np.bincount(parts[land])
        land &= (sizes < limit)[parts]
        del parts
    for first in range(0, len(labels), BAND_ROWS):
        rows = slice(first, first + BAND_ROWS)
        back = (claimed[rows] >= 0) & (connected[rows] < 0) & ~land[rows]
        connected[rows] = np.where(back, claimed[rows], connected[rows])
    return connected


def _eurasian_waters(
    game_map: Eu5Map, claims: OceanClaims, sea: NDArray[np.bool_], generated: Collection[str]
) -> NDArray[np.bool_]:
    """Open-ocean locations at least half enclosed by Eurasian shores and joined to them.

    A location the enclosure marks but that reaches no retained Eurasian location
    through other marked ones would be an isolated vanilla zone in generated water.
    """
    near, reserved = claims.eurasian, claims.reserved
    count = len(game_map.keys)
    if near is None or reserved is None:
        return np.zeros(count, dtype=bool)
    labels = game_map.labels
    columns = np.arange(labels.shape[1], dtype=np.int64)
    taken = np.zeros(count, dtype=np.int64)
    held = np.zeros(count, dtype=np.int64)
    total = np.zeros(count, dtype=np.int64)
    for first in range(0, len(labels), BAND_ROWS):
        stop = min(first + BAND_ROWS, len(labels))
        block = labels[first:stop]
        rows = np.arange(first, stop, dtype=np.int64)
        kept = reserved[np.ix_(claims.rows(rows), claims.columns(columns))]
        reached = near[np.ix_(rows // claims.step, columns // claims.step)] | kept
        total += np.bincount(block.ravel(), minlength=count)
        taken += np.bincount(block[reached], minlength=count)
        held += np.bincount(block[kept], minlength=count)
    open_water = np.fromiter(
        (name.endswith("_ocean_continent") for name in game_map.continents), dtype=bool
    )
    # Water filed under Africa is only withheld where its northern limit denied it, never
    # where Eurasian shores merely enclose it: Africa keeps its share of the Mediterranean.
    african = np.fromiter((name == "africa" for name in game_map.continents), dtype=bool)
    marked = (
        sea & (total > 0) & ((open_water & (2 * taken >= total)) | (african & (2 * held >= total)))
    )
    retained = np.fromiter(
        (
            bool(name) and name not in generated and not name.endswith("_ocean_continent")
            for name in game_map.continents
        ),
        dtype=bool,
    )
    links: dict[int, list[int]] = {}
    joined: list[int] = []
    for first, second in unpack_pairs(adjacency_pairs(labels, wrap_x=True)):
        for cell, other in ((first, second), (second, first)):
            if marked[cell]:
                if retained[other]:
                    joined.append(cell)
                elif marked[other]:
                    links.setdefault(cell, []).append(other)
    reached = np.zeros(count, dtype=bool)
    while joined:
        cell = joined.pop()
        if not reached[cell]:
            reached[cell] = True
            joined.extend(links.get(cell, ()))
    return reached


def _coastal_zones(game_map: Eu5Map, sea: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """The sea zones the game files under a continent, not under an ocean."""
    return sea & np.fromiter(
        (bool(name) and not name.endswith("_ocean_continent") for name in game_map.continents),
        dtype=bool,
    )


def _released_coasts(
    game_map: Eu5Map,
    kept: NDArray[np.bool_],
    selected: Collection[str],
    spared: Collection[str],
) -> NDArray[np.int8]:
    """The continent that takes each kept coastal zone whose only shore is replaced land.

    The game files some coastal zones under a continent that stays (the Red Sea and the
    Gulf of Aden under Asia, the delta mouths under Asia, Morocco's under Europe) although
    they wash the shores of a continent that is replaced. Kept whole, such a zone would
    face the generated water along the replaced coast, whose outline is then the border of
    a vanilla location in open water, and the islets of the replaced land inside it would
    stand as tiny generated enclaves. A zone that touches replaced land and no retained
    land goes to the canvas of the continent whose land it touches most (the lower number
    on a tie), whole; a zone that also touches a retained shore stays. ``spared`` names the
    zones the plan keeps for their ships. The result is that continent's number in
    ``CONTINENTS`` for each such zone and -1 for every other location.
    """
    classes = game_map.classes
    numbers = {key: number for number, key in enumerate(CONTINENTS)}
    named = np.fromiter((bool(name) for name in game_map.continents), dtype=bool)
    chosen = np.fromiter((name in selected for name in game_map.continents), dtype=bool)
    solid = np.fromiter(
        (kind not in {CellClass.SEA, CellClass.LAKE} for kind in classes), dtype=bool
    )
    owner = np.fromiter((numbers.get(name, -1) for name in game_map.continents), dtype=np.int8)
    replaced = solid & chosen
    retained = solid & named & ~chosen
    touching = np.zeros((len(kept), len(CONTINENTS)), dtype=np.int64)
    retained_front = np.zeros(len(kept), dtype=bool)
    for first, second in unpack_pairs(adjacency_pairs(game_map.labels, wrap_x=True)):
        for zone, other in ((first, second), (second, first)):
            if kept[zone]:
                if replaced[other]:
                    touching[zone, owner[other]] += 1
                retained_front[zone] |= retained[other]
    held = np.fromiter((key in spared for key in game_map.keys), dtype=bool)
    released = kept & touching.any(axis=1) & ~retained_front & ~held
    return np.where(released, touching.argmax(axis=1), -1).astype(np.int8)


def _shared_water(
    game_map: Eu5Map,
    claims: OceanClaims,
    sea: NDArray[np.bool_],
    selected: Collection[str],
    retained_tolls: Collection[str],
) -> SharedWater:
    selected_land, cores = _continental_cores(game_map, sea)
    eurasian = _eurasian_waters(game_map, claims, sea, CONTINENTS)
    kept = sea & np.array(
        [
            continent not in selected
            and (
                not continent.endswith("_ocean_continent")
                or key in retained_tolls
                or key in NAVAL_ANCHORS
            )
            for key, continent in zip(game_map.keys, game_map.continents, strict=True)
        ],
        dtype=bool,
    ) | (sea & eurasian)
    result = np.full(len(sea), -1, dtype=np.int8)
    groups = ocean_island_groups(game_map)
    members = np.zeros(len(sea), dtype=bool)
    for group in groups:
        members[list(group.locations)] = True
    island_rows, island_columns = np.nonzero(members[game_map.labels])
    values = game_map.labels[island_rows, island_columns]
    owner = claims.owners[claims.rows(island_rows), claims.columns(island_columns)]
    found: list[tuple[int, IslandGroup]] = []
    for group in groups:
        votes = owner[np.isin(values, group.locations)]
        chosen = int(np.bincount(votes).argmax())
        whole = [*group.locations, *group.zones]
        result[whole] = chosen
        kept[whole] = False
        found.append((chosen, group))
    kept &= _released_coasts(game_map, kept, selected, {*retained_tolls, *NAVAL_ANCHORS}) < 0
    # The installed open-ocean colours include a few disconnected specks
    # inside retained land. Keep their ownership, and let the identity pass
    # handle each original remainder rather than generating isolated ports.
    water = sea[game_map.labels]
    parts = label_components(water.astype(np.int32), wrap_x=True)
    counts = np.bincount(parts[water], minlength=int(parts.max()) + 1)
    specks = water & (counts < ocean_speck_limit(game_map.labels.shape[1]))[parts]
    labels = game_map.labels
    owners = np.full(labels.shape, -1, dtype=np.int8)
    columns = claims.columns(np.arange(labels.shape[1], dtype=np.int64))
    for first in range(0, len(labels), BAND_ROWS):
        stop = min(first + BAND_ROWS, len(labels))
        rows = slice(first, stop)
        coarse = claims.owners[np.ix_(claims.rows(np.arange(first, stop, dtype=np.int64)), columns)]
        block = labels[rows]
        water_or_land = (sea | selected_land)[block] & ~(kept[block] | specks[rows])
        belongs = np.where(cores[rows] >= 0, cores[rows], coarse)
        owners[rows] = np.where(
            result[block] >= 0, result[block], np.where(water_or_land, belongs, -1)
        )
    owners = _own_enclosed_specks(owners, specks, parts)
    owners = _rejoin_fragments(
        labels,
        owners,
        _connect_owners(owners),
        np.fromiter(
            (kind not in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes), dtype=bool
        ),
    )
    resolved: list[tuple[int, IslandGroup]] = []
    for _, group in found:
        picked = np.isin(values, group.locations)
        here = np.unique(owners[island_rows[picked], island_columns[picked]])
        if here.size != 1:
            message = "An installed ocean island group crosses disconnected canvases"
            raise CanvasError(message)
        if here[0] >= 0:
            resolved.append((int(here[0]), group))
    return SharedWater(owners, claims.north_africa, tuple(resolved))


def _pacific_shelf(mainland: NDArray[np.bool_], seed: int) -> NDArray[np.bool_]:
    """Put the shelf's centreline out in the Pacific.

    Its displacement varies with latitude and seed, and its ocean budget stays shared.
    """
    rows, columns = mainland.shape
    rnd = SplitMix64(derive_seed(seed, "continental_shelf"))
    bands = np.linspace(0, rows - 1, 6, dtype=np.int64)
    offsets = [-(15 + rnd.below(40)) for _ in bands]
    shift = np.zeros(rows, dtype=np.int64)
    for i, (a, b) in enumerate(pairwise(bands.tolist())):
        if a < b:
            shift[a:b] = offsets[i] + (np.arange(b - a) * (offsets[i + 1] - offsets[i]) // (b - a))
    shift[-1] = offsets[-1]
    return mainland[np.arange(rows)[:, None], (np.arange(columns) - shift[:, None]) % columns]


def _enclosed_claims(
    game_map: Eu5Map,
    sea: NDArray[np.bool_],
    solid: NDArray[np.bool_],
    selected: Collection[str],
    sample: NDArray[np.int32],
) -> NDArray[np.bool_]:
    """The blocks of the claim grid inside the whole locations that retained shores enclose."""
    step = game_map.labels.shape[1] // OCEAN_GRID_COLUMNS or 1
    square = _eurasian_blocks(game_map, solid, step, selected)
    claims = OceanClaims(
        np.zeros(sample.shape, dtype=np.int8),
        step,
        eurasian=square,
        reserved=np.zeros(sample.shape, dtype=bool),
    )
    return _eurasian_waters(game_map, claims, sea, selected)[sample]


def _ocean_claims(  # noqa: PLR0913, PLR0917 - the map, selection, water, land and retained closed water.
    game_map: Eu5Map,
    selected: Mapping[str, NewWorldSettings],
    sea: NDArray[np.bool_],
    solid: NDArray[np.bool_],
    seed: int | None,
    closed: Collection[str] = (),
) -> OceanClaims:
    """Divide competing ocean claims by distance to substantial land on a shared grid.

    A distant island retains its footprint and a local coast. It cannot reserve an
    ocean sector for its continent. Taller blocks give all continents room towards the
    poles without letting a fringe island dominate a whole latitude band. Africa and
    Oceania leave to the retained map the water that its shores enclose, and Africa
    claims nothing beyond its northern limit.
    """
    labels = game_map.labels
    height, width = labels.shape
    step = max(1, width // OCEAN_GRID_COLUMNS)
    rows = np.minimum(np.arange(0, height, 2 * step, dtype=np.int64) + step, height - 1)
    columns = np.minimum(np.arange(0, width, step, dtype=np.int64) + step // 2, width - 1)
    sample = labels[np.ix_(rows, columns)]
    best = np.full(sample.shape, max(sample.shape) + 1, dtype=np.int32)
    owners = np.full(sample.shape, -1, dtype=np.int8)
    minimum = max(1, CONTINENTAL_SHORE_AREA_PX * width**2 // REFERENCE_WIDTH**2 // (2 * step**2))
    enclosed = _enclosed_claims(game_map, sea, solid, selected, sample)
    north_africa = 0
    for number, key in enumerate(CONTINENTS):
        if key not in selected:
            continue
        land = (_membership(game_map, key) & ~sea)[sample]
        parts = label_components(land.astype(np.int32), wrap_x=True)
        sizes = np.bincount(parts[land], minlength=int(parts.max()) + 1)
        largest = int(sizes.max(initial=0))
        mainland = land & (sizes >= min(largest, minimum))[parts]
        settings = selected[key]
        reach = settings.ocean_band_px
        if key != NEW_WORLD:
            reach = reach * OPEN_OCEAN_BAND_PX // REGIONAL_PRESETS[key][1]
        if key == NEW_WORLD and (settings.expand_oceans or settings.landform):
            reach = max(reach, OPEN_OCEAN_BAND_PX)
        if key == NEW_WORLD and seed is not None and _expanded_america(settings):
            mainland = _pacific_shelf(mainland, seed)
            reach = max(reach, PACIFIC_SHELF_PX)
        radius = reach * width // (REFERENCE_WIDTH * step)
        distance = distance_from(mainland, radius + 1, octagonal=True, wrap_x=True)
        claim = (distance <= radius) & (distance < best)
        if key == AFRICA:
            north_africa = _african_limit(mainland, rows, step, width)
            claim &= (rows - step >= north_africa)[:, None]
        if key != NEW_WORLD:
            claim &= ~enclosed
        owners[claim] = number
        best[claim] = distance[claim]
    if len(selected) > 1:
        quota = sample.size // SHARED_OCEAN_DIVISOR
        marine = sea[sample]
        for number in range(len(CONTINENTS)):
            own = (owners == number) & marine
            scores = best[own]
            if len(scores) > quota:
                # Retire the farthest shell together, so a tied distance never
                # produces a straight row boundary to make a quota exact.
                cutoff = int(np.partition(scores, quota)[quota])
                owners[own & (best >= cutoff)] = -1
    islands = (
        _pacific_islands(
            game_map, sample, owners, rows, columns, step=step, seed=seed, closed=closed
        )
        if seed is not None and {"america", "oceania"}.issubset(selected)
        else ()
    )
    return OceanClaims(owners, step, islands, north_africa=north_africa)


def _expanded_america(settings: NewWorldSettings) -> bool:
    return bool(settings.expand_oceans and not (settings.landform or settings.template_permille))


def _shared_ocean_claims(
    game_map: Eu5Map, sea: NDArray[np.bool_], solid: NDArray[np.bool_], seed: int | None
) -> OceanClaims:
    """Partition every ocean block about the three substantial continental footprints.

    The retained Eurasian land competes for the nearest blocks with a bounded reach,
    so Africa and Oceania cannot dig into its bays and passages. It owns no block
    here; ``_eurasian_waters`` turns this reservation into whole retained locations.
    """
    height, width = game_map.labels.shape
    step = max(1, width // OCEAN_GRID_COLUMNS)
    rows = np.minimum(np.arange(0, height, 2 * step, dtype=np.int64) + step, height - 1)
    columns = np.minimum(np.arange(0, width, step, dtype=np.int64) + step // 2, width - 1)
    sample = game_map.labels[np.ix_(rows, columns)]
    limit = sample.shape[0] + sample.shape[1]
    minimum = max(1, CONTINENTAL_SHORE_AREA_PX * width**2 // REFERENCE_WIDTH**2 // (2 * step**2))
    north_africa = 0
    distances: list[tuple[int, NDArray[np.int32]]] = []
    for number, name in enumerate(CONTINENTS):
        core = _substantial_land(_membership(game_map, name) & ~sea, sample, minimum)
        if not core.any():
            continue
        if name == AFRICA:
            north_africa = _african_limit(core, rows, step, width)
        if seed is not None:
            shift = _shelf_drift(seed, name, len(rows), len(columns))
            core = core[
                np.arange(len(rows))[:, None],
                (np.arange(len(columns)) - shift[:, None]) % len(columns),
            ]
        distances.append((number, distance_from(core, limit, octagonal=True, wrap_x=True)))
    owners = _nearest_core(distances, sample.shape, limit, np.ones(len(rows), dtype=bool))
    held = _nearest_core(distances, sample.shape, limit, rows - step >= north_africa)
    reserved = (owners == AFRICA_NUMBER) & (held != AFRICA_NUMBER)
    return OceanClaims(
        held,
        step,
        eurasian=_eurasian_blocks(game_map, solid, step, CONTINENTS),
        north_africa=north_africa,
        reserved=reserved,
    )


def _african_limit(core: NDArray[np.bool_], rows: NDArray[np.int64], step: int, width: int) -> int:
    """The first pixel row Africa may claim: its northernmost land less its northern reach."""
    first = int(np.flatnonzero(core.any(axis=1))[0])
    return max(0, int(rows[first]) - step - AFRICAN_NORTH_REACH_PX * width // REFERENCE_WIDTH)


def _nearest_core(
    distances: list[tuple[int, NDArray[np.int32]]],
    shape: tuple[int, ...],
    limit: int,
    african: NDArray[np.bool_],
) -> NDArray[np.int8]:
    """The continent whose land is nearest each block; Africa claims only its ``african`` rows."""
    best = np.full(shape, limit + 1, dtype=np.int32)
    owners = np.zeros(shape, dtype=np.int8)
    for number, distance in distances:
        take = distance < best
        if number == AFRICA_NUMBER:
            take &= african[:, None]
        best[take] = distance[take]
        owners[take] = number
    return owners


def _substantial_land(
    land: NDArray[np.bool_], sample: NDArray[np.int32], minimum: int
) -> NDArray[np.bool_]:
    """The sampled land of a continent's largest landmasses, without its outlying islets."""
    main = land[sample]
    parts = label_components(main.astype(np.int32), wrap_x=True)
    sizes = np.bincount(parts[main], minlength=int(parts.max()) + 1)
    return main & (sizes >= min(int(sizes.max()), minimum))[parts]


def _eurasian_blocks(
    game_map: Eu5Map, solid: NDArray[np.bool_], step: int, generated: Collection[str]
) -> NDArray[np.bool_]:
    """Square blocks of water that retained shores enclose, whatever the generated continents.

    Every continent outside ``generated`` is retained land, so Eurasia and an unselected
    Africa enclose water alike.

    The claim grid is twice as coarse in latitude, so its distances would double the
    reach north and south. A square grid keeps the reach the same in every direction.
    A block is enclosed when its nearest land is Eurasian, and Eurasian land lies within
    reach on both sides of it along a row, a column or a diagonal with no generated
    continent's land in the way.
    """
    labels = game_map.labels
    height, width = labels.shape
    rows = np.minimum(np.arange(0, height, step, dtype=np.int64) + step // 2, height - 1)
    columns = np.minimum(np.arange(0, width, step, dtype=np.int64) + step // 2, width - 1)
    sample = labels[np.ix_(rows, columns)]
    limit = sample.shape[0] + sample.shape[1]
    nearest_generated = np.full(sample.shape, limit + 1, dtype=np.int32)
    minimum = max(1, CONTINENTAL_SHORE_AREA_PX * width**2 // REFERENCE_WIDTH**2 // step**2)
    for name in generated:
        core = _substantial_land(_membership(game_map, name) & solid, sample, minimum)
        if core.any():
            nearest_generated = np.minimum(
                nearest_generated, distance_from(core, limit, octagonal=True, wrap_x=True)
            )
    eurasia = np.fromiter(
        (
            bool(name) and name not in generated and not name.endswith("_ocean_continent")
            for name in game_map.continents
        ),
        dtype=bool,
    )
    land = (eurasia & solid)[sample]
    foreign = (_membership_any(game_map, generated) & solid)[sample]
    reach = max(1, EURASIAN_SPAN_PX * width // (REFERENCE_WIDTH * step))
    enclosed = np.zeros(sample.shape, dtype=bool)
    for dy, dx in EURASIAN_LINES:
        enclosed |= _sighted(land, foreign, dy, dx, reach) & _sighted(
            land, foreign, -dy, -dx, reach
        )
    nearest = distance_from(land, limit, octagonal=True, wrap_x=True)
    return enclosed & (nearest <= nearest_generated)


def _membership_any(game_map: Eu5Map, generated: Collection[str]) -> NDArray[np.bool_]:
    """Locations of any generated continent."""
    return np.fromiter((name in generated for name in game_map.continents), dtype=bool)


def _sighted(
    target: NDArray[np.bool_], blocking: NDArray[np.bool_], dy: int, dx: int, reach: int
) -> NDArray[np.bool_]:
    """Blocks with target land within ``reach`` steps in a direction before blocking land."""
    height = target.shape[0]
    found = np.zeros_like(target)
    clear = np.ones_like(target)
    for step in range(1, reach // max(abs(dy), abs(dx)) + 1):
        gone = step * dy
        if abs(gone) >= height:
            break
        hit = np.zeros_like(target)
        wall = np.zeros_like(target)
        top, bottom = max(0, -gone), height - max(0, gone)
        for source, sink in ((target, hit), (blocking, wall)):
            moved = np.roll(source, -step * dx, axis=1)
            sink[top:bottom] = moved[top + gone : bottom + gone]
        found |= clear & hit
        clear &= ~(hit | wall)
    return found


def _shelf_drift(seed: int, name: str, rows: int, columns: int) -> NDArray[np.int64]:
    """Give the shared frontier a seed-dependent drift on either side of the old shore."""
    rng = SplitMix64(derive_seed(seed, "shared_ocean_drift", name))
    reach = max(1, columns // 30)
    bands = np.linspace(0, rows - 1, 6, dtype=np.int64)
    offsets = [rng.below(2 * reach + 1) - reach for _ in bands]
    shift = np.full(rows, offsets[-1], dtype=np.int64)
    for i, (first, last) in enumerate(pairwise(bands.tolist())):
        if first < last:
            shift[first:last] = offsets[i] + (
                np.arange(last - first, dtype=np.int64)
                * (offsets[i + 1] - offsets[i])
                // (last - first)
            )
    return shift


def _pacific_islands(  # noqa: PLR0913 - reserve compact island groups on the shared ocean grid.
    game_map: Eu5Map,
    labels: NDArray[np.int32],
    owners: NDArray[np.int8],
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    *,
    step: int,
    seed: int,
    closed: Collection[str] = (),
) -> tuple[tuple[int, int, int], ...]:
    """Reserve a few widely spaced groups on the existing Pacific canvas.

    A group's water must meet navigable retained water: ``closed`` names the impassable
    ocean locations, and no group is placed beside them, where its sea would be cut off.
    """
    pacific = np.array([c == "pacific_ocean_continent" for c in game_map.continents], dtype=bool)[
        labels
    ]
    radius = ISLAND_POOL
    room = distance_from(~pacific | (owners == 0), radius + 1, octagonal=True, wrap_x=True)
    shut = np.array([key in closed for key in game_map.keys], dtype=bool)[labels]
    clear = distance_from(shut, radius + 2, octagonal=True, wrap_x=True)
    height, width = labels.shape
    yy = np.arange(height, dtype=np.int64)[:, None]
    xx = np.arange(width, dtype=np.int64)[None, :]
    seam = np.minimum(xx, width - xx)
    rng = SplitMix64(derive_seed(seed, "oceanian_pacific_islands"))
    sites: list[tuple[int, int, int]] = []
    for latitude, longitude in ((40, 2), (56, -4), (69, 8)):
        gold_y = (latitude + rng.below(9) - 4) * height // 100
        gold_x = (longitude + rng.below(7) - 3) * width // 100
        across = np.abs(xx - gold_x) % width
        distance = 2 * np.abs(yy - gold_y) + np.minimum(across, width - across)
        allowed = (
            (room > radius) & (clear > radius + 1) & (seam <= width // 7) & (distance < width // 12)
        )
        if not allowed.any():
            continue
        scores = distance.copy()
        scores[~allowed] = width
        row, column = np.unravel_index(np.argmin(scores), owners.shape)
        dx = np.abs(xx - column)
        halo = (2 * (yy - row)) ** 2 + np.minimum(dx, width - dx) ** 2 <= radius**2
        owners[halo] = 2
        room[halo] = 0
        sites.append((int(rows[row]), int(columns[column]), step))
    return tuple(sites)


def _interface(inside: NDArray[np.bool_], neighbor: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Original solid land contacts in the continuous regional window."""
    touching = np.zeros(inside.shape, dtype=bool)
    touching[1:] = neighbor[:-1]
    touching[:-1] |= neighbor[1:]
    touching[:, 1:] |= neighbor[:, :-1]
    touching[:, :-1] |= neighbor[:, 1:]
    return inside & touching


def _coastal_waters(
    footprint: NDArray[np.bool_],
    marine: NDArray[np.bool_],
    reach: int,
    island_reach: int,
    continental_area: int,
) -> NDArray[np.bool_]:
    """Use the wide coastal band around large landmasses and a local band around islands."""
    if island_reach >= reach:
        return marine & (distance_from(footprint, reach + 1, octagonal=True) <= reach)
    parts = label_components(footprint.astype(np.int32))
    sizes = np.zeros(int(parts.max()) + 1, dtype=np.int64)
    land_parts, counts = np.unique(parts[footprint], return_counts=True)
    sizes[land_parts] = counts
    shelves = (sizes >= continental_area)[parts]
    del parts
    claim = distance_from(footprint, island_reach + 1, octagonal=True) <= island_reach
    if shelves.any():
        claim |= distance_from(shelves, reach + 1, octagonal=True) <= reach
    return marine & claim


@dataclass(frozen=True, slots=True, eq=False)
class _Spread:
    """The columns and rows of the map that some zones reach, and how many pixels they have."""

    columns: NDArray[np.bool_]
    rows: NDArray[np.bool_]
    pixels: int


def _spread(labels: NDArray[np.int32], zones: NDArray[np.bool_] | None) -> _Spread:
    """Where the zones lie on the map; nowhere for ``None``."""
    columns = np.zeros(labels.shape[1], dtype=bool)
    rows = np.zeros(len(labels), dtype=bool)
    pixels = 0
    if zones is None:
        return _Spread(columns, rows, pixels)
    for first in range(0, len(labels), BAND_ROWS):
        checkpoint()
        stop = first + BAND_ROWS
        block = zones[labels[first:stop]]
        columns |= block.any(axis=0)
        rows[first:stop] = block.any(axis=1)
        pixels += int(np.count_nonzero(block))
    return _Spread(columns, rows, pixels)


def _with_released(
    mask: NDArray[np.bool_],
    released: NDArray[np.bool_] | None,
    local: NDArray[np.int32],
    taken: _Spread,
    key: str,
) -> NDArray[np.bool_]:
    """The mask with every zone released to the continent, all of it inside the window."""
    if released is None:
        return mask
    zones = released[local]
    if int(np.count_nonzero(zones)) != taken.pixels:
        message = f"A coastal zone released to {key} lies outside its window"
        raise CanvasError(message)
    return mask | zones


def _claim(  # noqa: PLR0913, PLR0915 - assemble a cropped domain and its coast contacts.
    game_map: Eu5Map,
    continent: Continent,
    number: int,
    claims: OceanClaims,
    *,
    sea: NDArray[np.bool_],
    solid: NDArray[np.bool_],
    join_asia: bool | None,
    europe_strait: bool,
    shared: SharedWater | None = None,
    released: NDArray[np.bool_] | None = None,
) -> Domain:
    labels = game_map.labels
    map_height, map_width = labels.shape
    reach = continent.island_band_px * map_width // REFERENCE_WIDTH
    identity = _membership(game_map, continent.key)
    taken = _spread(labels, released)
    member = identity & ~sea
    # The American hierarchy includes coastal seas that must be replaced in
    # full to keep American and retained continental identities separated.
    original_seas = (
        identity & sea if shared is None and continent.key == NEW_WORLD else np.zeros_like(sea)
    )
    source = (member | original_seas)[labels] if shared is None else shared.owners == number
    owner = (claims.owners == number) & (shared is None)
    owner_cols = owner.any(axis=0)[claims.columns(np.arange(map_width, dtype=np.int64))]
    owner_rows = owner.any(axis=1)[claims.rows(np.arange(map_height, dtype=np.int64))]
    owner_rows |= taken.rows
    first, width = _extent(source.any(axis=0) | owner_cols | taken.columns, reach + 1)
    active_rows = np.flatnonzero(source.any(axis=1))
    del source
    # Keep the regional density grid aligned to map rows, and leave a halo past
    # the last possible sea pixel. The world rows still determine the latitude.
    top = max(0, (int(active_rows[0]) - reach - 1) // DENSITY_STEP * DENSITY_STEP)
    end = min(map_height, -(-(int(active_rows[-1]) + reach + 2) // DENSITY_STEP) * DENSITY_STEP)
    owned_rows = np.flatnonzero(owner_rows)
    if owned_rows.size:
        top = min(top, int(owned_rows[0]) // DENSITY_STEP * DENSITY_STEP)
        end = min(
            map_height, max(end, -(-(int(owned_rows[-1]) + 1) // DENSITY_STEP) * DENSITY_STEP)
        )
    local = _read(labels[top:end], first, width)
    footprint = member[local]
    marine = sea[local]
    local_owners = (
        _read(shared.owners[top:end], first, width)
        if shared is not None
        else claims.owners[
            np.ix_(
                claims.rows(np.arange(top, end, dtype=np.int64)),
                claims.columns(np.arange(first, first + width, dtype=np.int64) % map_width),
            )
        ]
    )
    if (
        shared is not None
        and not europe_strait
        and (continent.land_neighbor is None or join_asia is False)
    ):
        return _whole_domain(
            continent,
            first,
            map_width,
            top,
            number,
            local,
            footprint,
            local_owners,
            interface=None,
            neighbor=None,
            join_asia=False,
            strait=None,
            shared=shared,
        )
    open_sea = np.fromiter(
        (
            name == continent.key or name.endswith("_ocean_continent")
            for name in game_map.continents
        ),
        dtype=bool,
    )[local]
    coast = _coastal_waters(footprint, marine, reach, reach, 0)
    candidate = marine & ((local_owners == number) | ((local_owners < 0) & coast))
    claim = candidate & open_sea
    # The original footprint has priority over sea claims. Keep ocean room around
    # other land, including the islands of continental shelves and adjacent Asia.
    guard = max(1, RETAINED_SHORE_PX * map_width // REFERENCE_WIDTH)
    # A halo around the window sees land just outside its edges.
    protected = solid & ~member
    low, high = max(0, top - guard), min(map_height, end + guard)
    halo_rows = slice(top - low, end - low)
    if width + 2 * guard < map_width:
        around = _read(labels[low:high], (first - guard) % map_width, width + 2 * guard)
        near = distance_from(protected[around], guard + 1, octagonal=True)[
            halo_rows, guard : guard + width
        ]
    else:
        near = _read(
            distance_from(protected[labels[low:high]], guard + 1, octagonal=True, wrap_x=True)[
                halo_rows
            ],
            first,
            width,
        )
    neighbor = (
        None
        if continent.land_neighbor is None or join_asia is False
        else (_membership(game_map, continent.land_neighbor) & solid)[local]
    )
    close = near > guard
    del near
    interface = None
    strait = None
    inland = footprint & solid[local]
    near_africa = _near_african_shores(inland, map_width) if join_asia or europe_strait else None
    passable = np.fromiter((kind is CellClass.LAND for kind in game_map.classes), dtype=bool)
    if neighbor is not None:
        contact = inland
        if join_asia and near_africa is not None:
            # Permit approach within the African domain along western Asia's
            # contiguous shore as well as across the old overland boundary.
            asian_shore = neighbor & near_africa
            approach = distance_from(asian_shore, guard + 1, octagonal=True) <= guard
            close |= approach
            claim |= candidate & approach
            contact = inland | (claim & close)
        interface = _interface(contact, neighbor & passable[local])
    if europe_strait and near_africa is not None:
        europe = (_membership(game_map, "europe") & passable)[local] & near_africa
        near_europe = distance_from(europe, guard + 1, octagonal=True)
        gap = min(guard, EUROPE_STRAIT_GAP)
        close |= near_europe <= guard
        claim |= candidate & (near_europe <= guard)
        landing = claim & (near_europe == gap)
        if landing.any():
            strait = np.where(landing, 2, near_europe < gap).astype(np.uint8)
    claim &= close
    if shared is not None:
        return _whole_domain(
            continent,
            first,
            map_width,
            top,
            number,
            local,
            footprint,
            local_owners,
            interface=interface,
            neighbor=neighbor,
            join_asia=bool(join_asia),
            strait=strait,
            shared=shared,
        )
    sites = (
        tuple((row - top, (col - first) % map_width, step) for row, col, step in claims.islands)
        if continent.key == "oceania"
        else ()
    )
    anchors = footprint.copy() if sites else footprint
    for row, col, _ in sites:
        anchors[row, col] = claim[row, col]
    mask = _attached_ocean(anchors, claim) | original_seas[local]
    mask = _with_released(mask, released, local, taken, continent.key)
    if interface is not None:
        interface &= mask
    if strait is not None:
        strait[~mask] = 0
    return Domain(
        continent,
        first,
        map_width,
        mask,
        footprint,
        first_row=top,
        land_interface=interface,
        contact_land=neighbor,
        join_asia=bool(join_asia),
        strait=strait,
        island_sites=sites,
    )


def _whole_domain(  # noqa: PLR0913, PLR0917 - complete ownership plus retained coastal identities.
    continent: Continent,
    first: int,
    width: int,
    top: int,
    number: int,
    local: NDArray[np.int32],
    footprint: NDArray[np.bool_],
    local_owners: NDArray[np.int8],
    *,
    interface: NDArray[np.bool_] | None,
    neighbor: NDArray[np.bool_] | None,
    join_asia: bool,
    strait: NDArray[np.uint8] | None,
    shared: SharedWater,
) -> Domain:
    mask = local_owners == number
    if interface is not None:
        interface = np.logical_and(interface, mask)
    if strait is not None:
        strait[~mask] = 0
    north_water_rows = max(0, shared.north_africa - top) if continent.key == "africa" else 0
    groups = tuple(group for owner, group in shared.groups if owner == number)
    footprints: list[Footprint] = []
    for group in groups:
        member = np.isin(local, (*group.locations, *group.zones)) & mask
        rows, cols = np.nonzero(member)
        footprints.append(Footprint(rows.astype(np.int32), cols.astype(np.int32)))
    return Domain(
        continent,
        first,
        width,
        mask,
        footprint & mask,
        first_row=top,
        land_interface=interface,
        contact_land=neighbor,
        join_asia=join_asia,
        strait=strait,
        shared_ocean=True,
        north_water_rows=north_water_rows,
        groups=groups,
        footprints=tuple(footprints),
    )


def _attached_ocean(footprint: NDArray[np.bool_], claim: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Keep shelves continuous with the continent or with one of its outlying islands."""
    mask = footprint | claim
    parts = label_components(mask.astype(np.int32))
    anchored = np.zeros(int(parts.max()) + 1, dtype=bool)
    anchored[parts[footprint]] = True
    return mask & anchored[parts]


def _near_african_shores(footprint: NDArray[np.bool_], width: int) -> NDArray[np.bool_]:
    reach = max(1, width * 720 // REFERENCE_WIDTH)
    return distance_from(footprint, reach + 1, octagonal=True) <= reach


def _claim_america(
    game_map: Eu5Map,
    selected: Mapping[str, NewWorldSettings],
    occupied: NDArray[np.bool_],
    sea: NDArray[np.bool_],
    claims: OceanClaims,
) -> Domain:
    source = _legacy_domain(game_map, selected[NEW_WORLD])
    mask = source.mask.copy()
    if source.legacy_canvas is not None:
        for island in source.legacy_canvas.footprints:
            mask[island.rows, island.columns] = False
    marine = np.empty_like(mask)
    retained = sea & np.fromiter(
        (name in CONTINENTS and name not in selected for name in game_map.continents),
        dtype=bool,
    )
    for columns, original in source.spans():
        for top in range(0, mask.shape[0], BAND_ROWS):
            rows = slice(top, min(top + BAND_ROWS, mask.shape[0]))
            labels = game_map.labels[rows, original]
            marine[rows, columns] = sea[labels]
            allowed = source.footprint[rows, columns] | marine[rows, columns]
            if not selected[NEW_WORLD].landform:
                owners = claims.owners[
                    np.ix_(
                        claims.rows(np.arange(rows.start, rows.stop, dtype=np.int64)),
                        claims.columns(np.arange(original.start, original.stop, dtype=np.int64)),
                    )
                ]
                allowed &= source.footprint[rows, columns] | (owners == 0)
            mask[rows, columns] &= allowed & ~occupied[rows, original] & ~retained[labels]
    return Domain(
        source.continent,
        source.first_column,
        source.map_width,
        _coastal_claim(mask, source.footprint, marine),
        source.footprint,
    )


def _protected_sea(
    game_map: Eu5Map, occupied: NDArray[np.bool_], selected: Mapping[str, NewWorldSettings]
) -> NDArray[np.bool_]:
    """Leave a partly claimed sea zone whole if the cut would sever a retained shore."""
    labels = game_map.labels
    size = len(game_map.keys)
    kept = np.empty_like(labels)
    inside = np.zeros(size, dtype=np.int64)
    outside = np.zeros(size, dtype=np.int64)
    for top in range(0, len(labels), BAND_ROWS):
        checkpoint()
        rows = slice(top, top + BAND_ROWS)
        mask = occupied[rows]
        block = labels[rows]
        kept[rows] = np.where(mask, -1, block)
        inside += np.bincount(block[mask], minlength=size)
        outside += np.bincount(block[~mask], minlength=size)
    previous = set(unpack_pairs(adjacency_pairs(labels, wrap_x=True)))
    remaining = set(unpack_pairs(adjacency_pairs(kept, wrap_x=True)))
    cut = (inside > 0) & (outside > 0)
    foreign = [
        name not in selected and not name.endswith("_ocean_continent")
        for name in game_map.continents
    ]
    protect = np.zeros(size, dtype=bool)
    for first, second in previous - remaining:
        if not (outside[first] and outside[second] and (foreign[first] or foreign[second])):
            continue
        for cell in (first, second):
            if (
                cut[cell]
                and game_map.classes[cell] is CellClass.SEA
                and not game_map.ambiguous[cell]
            ):
                protect[cell] = True
    return protect


def _keep_coastal_waters(game_map: Eu5Map, domain: Domain, protected: NDArray[np.bool_]) -> Domain:
    mask = domain.mask.copy()
    for crop, original in domain.spans():
        mask[:, crop] &= ~protected[game_map.labels[domain.rows, original]]
    if np.array_equal(mask, domain.mask):
        return domain
    if domain.continent.key != NEW_WORLD:
        anchors = domain.footprint.copy() if domain.island_sites else domain.footprint
        for row, col, _ in domain.island_sites:
            anchors[row, col] = mask[row, col]
        mask = _attached_ocean(anchors, mask)
    interface, strait = domain.land_interface, domain.strait
    return replace(
        domain,
        mask=mask,
        land_interface=None if interface is None else interface & mask,
        strait=None if strait is None else np.where(mask, strait, 0).astype(np.uint8),
    )


def _without_islets(game_map: Eu5Map, domains: Sequence[Domain]) -> tuple[Domain, ...]:
    """Leave out of every canvas the small pieces of replaced land that no canvas water joins up.

    An islet of a replaced location that lies among retained waters, with none of its own
    water claimed round it (the retained shores keep a guard of open water), stands in a canvas
    as a piece of a few pixels and becomes a generated location with no neighbour. A piece of
    the canvases below ``ocean_speck_limit`` that holds replaced land is left out of them, and
    the export gives its land to the water round it
    (``continent_world.absorb_land_fragments``). A piece that holds an island site stays.
    """
    labels = game_map.labels
    width = labels.shape[1]
    occupied = np.zeros(labels.shape, dtype=bool)
    for domain in domains:
        for crop, original in domain.spans():
            occupied[domain.rows, original] |= domain.mask[:, crop]
    parts = label_components(occupied.astype(np.int32), wrap_x=True)
    count = int(parts.max()) + 1
    sizes = np.bincount(parts[occupied], minlength=count)
    goes = (sizes > 0) & (sizes < ocean_speck_limit(width))
    del occupied
    holds_land = np.zeros(count, dtype=bool)
    for domain in domains:
        for crop, original in domain.spans():
            holds_land[parts[domain.rows, original][domain.footprint[:, crop]]] = True
        for row, column, _ in domain.island_sites:
            goes[parts[row + domain.first_row, (column + domain.first_column) % width]] = False
    goes &= holds_land
    if not goes.any():
        return tuple(domains)
    result: list[Domain] = []
    for domain in domains:
        mask = domain.mask.copy()
        for crop, original in domain.spans():
            mask[:, crop] &= ~goes[parts[domain.rows, original]]
        interface, strait = domain.land_interface, domain.strait
        result.append(
            replace(
                domain,
                mask=mask,
                footprint=domain.footprint & mask,
                land_interface=None if interface is None else interface & mask,
                strait=None if strait is None else np.where(mask, strait, 0).astype(np.uint8),
            )
        )
    return tuple(result)


def plan_domains(  # noqa: PLR0913 - the map, the selection and the retained facts it plans around.
    game_map: Eu5Map,
    selected: Mapping[str, NewWorldSettings],
    *,
    seed: int | None = None,
    require_asia_connection: bool = False,
    retained_tolls: Collection[str] = (),
    closed_waters: Collection[str] = (),
) -> tuple[Domain, ...]:
    """Plan selected regions once, dividing shared oceans before generating any land.

    Preserve the legacy canvas for America on its own. With all three regions enabled,
    preserve Eurasia's original coastline and internal seas as a fourth canvas,
    and assign every other ocean pixel to one generated region.
    """
    if not selected or set(selected) - CONTINENTS.keys():
        message = "Choose at least one supported continent"
        raise CanvasError(message)
    for key, settings in selected.items():
        _validate_geography(CONTINENTS[key], settings)
    if tuple(selected) == (NEW_WORLD,):
        return (_legacy_domain(game_map, selected[NEW_WORLD]),)

    sea = np.fromiter((kind is CellClass.SEA for kind in game_map.classes), dtype=bool)
    solid = np.fromiter(
        (kind not in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes), dtype=bool
    )
    occupied = np.zeros(game_map.labels.shape, dtype=bool)
    planned: dict[str, Domain] = {}
    complete = len(selected) == len(CONTINENTS)
    claims = (
        _shared_ocean_claims(game_map, sea, solid, seed)
        if complete
        else _ocean_claims(game_map, selected, sea, solid, seed, closed_waters)
    )
    shared = _shared_water(game_map, claims, sea, selected, retained_tolls) if complete else None
    released = (
        None
        if complete
        else _released_coasts(
            game_map,
            _coastal_zones(game_map, sea),
            selected,
            {*retained_tolls, *NAVAL_ANCHORS},
        )
    )
    connect = (
        None
        if seed is None
        else require_asia_connection
        or SplitMix64(derive_seed(seed, "africa", "asia_connection")).below(100)
        < AFRICA_LAND_CHANCE
    )
    strait = seed is not None and (
        SplitMix64(derive_seed(seed, "africa", "europe_strait")).below(100) < EUROPE_STRAIT_CHANCE
    )
    for number, (key, continent) in enumerate(CONTINENTS.items()):
        if key != NEW_WORLD and key in selected:
            checkpoint()
            domain = _claim(
                game_map,
                continent,
                number,
                claims,
                sea=sea,
                solid=solid,
                join_asia=connect if key == "africa" else None,
                europe_strait=strait and key == "africa",
                shared=shared,
                released=None if released is None else released == number,
            )
            for columns, original in domain.spans():
                domain.mask[:, columns] &= ~occupied[domain.rows, original]
                occupied[domain.rows, original] |= domain.mask[:, columns]
            planned[key] = domain
    if NEW_WORLD in selected:
        america = (
            _claim(
                game_map,
                CONTINENTS[NEW_WORLD],
                0,
                claims,
                sea=sea,
                solid=solid,
                join_asia=None,
                europe_strait=False,
                shared=shared,
                released=None if released is None else released == 0,
            )
            if complete or (seed is not None and _expanded_america(selected[NEW_WORLD]))
            else _claim_america(game_map, selected, occupied, sea, claims)
        )
        planned[NEW_WORLD] = america
        for crop, original in america.spans():
            america.mask[:, crop] &= ~occupied[america.rows, original]
            occupied[america.rows, original] |= america.mask[:, crop]
    if shared is not None:
        for first in range(0, len(game_map.labels), BAND_ROWS):
            rows = slice(first, first + BAND_ROWS)
            if not np.array_equal(occupied[rows], shared.owners[rows] >= 0):
                message = "The generated canvases do not partition the map around retained Eurasia"
                raise CanvasError(message)
        return tuple(planned[key] for key in CONTINENTS)
    protected = _protected_sea(game_map, occupied, selected)
    protected |= np.fromiter(
        (
            (key in retained_tolls or key in NAVAL_ANCHORS) and continent not in selected and is_sea
            for key, continent, is_sea in zip(game_map.keys, game_map.continents, sea, strict=True)
        ),
        dtype=bool,
    )
    return _without_islets(
        game_map,
        [
            _keep_coastal_waters(game_map, planned[key], protected)
            for key in CONTINENTS
            if key in planned
        ],
    )
