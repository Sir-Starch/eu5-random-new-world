"""Plan EU5 identities for a generated New World: keys, colours, hierarchy, names.

Areas, regions, subcontinents and continents reuse vanilla names chosen by position
(the vanilla area under a cell's centre, or the nearest candidate), so script
references to them keep resolving. Provinces and locations are new. Land outside every
vanilla New World area gets new areas attached to the nearest vanilla region.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw.eu5_canvas import NEW_WORLD
from rnw.model import CellClass
from rnw.names import NameGenerator
from rnw.rng import SplitMix64, derive_seed
from rnw.synth import group_adjacent, lift_groups

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.geography import Location
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
AREA_SIZE: Final[int] = 5
COLOR_BITS: Final[int] = 24


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


def _area_centroids(
    geometry: VanillaGeometry, labels: NDArray[np.int64], weights: NDArray[np.int64]
) -> dict[str, tuple[int, int]]:
    sums: dict[str, list[int]] = {}
    pairs = zip(
        cast("list[int]", labels.tolist()), cast("list[int]", weights.tolist()), strict=True
    )
    for label, weight in pairs:
        area = geometry.areas[label]
        if not area:
            continue
        entry = sums.setdefault(area, [0, 0, 0])
        entry[0] += int(geometry.rows[label]) * weight
        entry[1] += int(geometry.columns[label]) * weight
        entry[2] += weight
    return {area: (r // max(1, w), c // max(1, w)) for area, (r, c, w) in sums.items()}


def _nearest(points: NDArray[np.int64], candidates: dict[str, tuple[int, int]]) -> list[str]:
    names = sorted(candidates)
    if not names or not points.size:
        return [""] * len(points)
    centres = np.array([candidates[name] for name in names], dtype=np.int64)
    chosen: list[str] = []
    for start in range(0, len(points), 2048):
        chunk = points[start : start + 2048]
        delta = chunk[:, np.newaxis, :] - centres[np.newaxis, :, :]
        distance = (delta * delta).sum(axis=2)
        nearest = cast("list[int]", np.argmin(distance, axis=1).tolist())
        chosen.extend(names[index] for index in nearest)
    return chosen


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


def plan_identities(  # noqa: PLR0912, PLR0913, PLR0915, C901 - one pass over all identity rules.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    *,
    seed: int,
    settings: NewWorldSettings,
) -> Plan:
    """Assign keys, colours, names and parents to every generated cell."""
    count = len(game_map.keys)
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    touched = canvas.removed | canvas.trimmed
    pixel_counts = np.bincount(canvas.rolled.ravel(), minlength=count).astype(np.int64)
    candidates = np.flatnonzero(touched)
    sea_labels = candidates[sea[candidates]]
    land_labels = candidates[
        ~sea[candidates]
        & np.array([game_map.continents[index] == NEW_WORLD for index in candidates.tolist()])
    ]
    sea_areas = _area_centroids(geometry, sea_labels, pixel_counts[sea_labels])
    land_areas = _area_centroids(geometry, land_labels, pixel_counts[land_labels])
    centre_columns = world.centroids[:, 1] + canvas.col0
    prior = canvas.rolled[world.centroids[:, 0], centre_columns]
    rolled_centres = np.stack([world.centroids[:, 0], centre_columns], axis=1)
    area_of: list[str] = [""] * len(world.classes)
    homeless: list[int] = []
    sea_fallback = _nearest(rolled_centres, sea_areas)
    for index, kind in enumerate(world.classes):
        prior_area = geometry.areas[int(prior[index])]
        if kind is CellClass.SEA:
            area_of[index] = prior_area if prior_area in sea_areas else sea_fallback[index]
        elif prior_area in land_areas:
            area_of[index] = prior_area
        else:
            homeless.append(index)
    neighbours: dict[int, set[int]] = {}
    for first, second in world.edges:
        neighbours.setdefault(first, set()).add(second)
        neighbours.setdefault(second, set()).add(first)
    by_area: dict[str, list[int]] = {}
    for index, area in enumerate(area_of):
        if area:
            by_area.setdefault(area, []).append(index)
    province_of: list[str] = [""] * len(world.classes)
    province_names = NameGenerator(seed, "provinces")
    plan = Plan(cells=[])
    serial = 0
    for area in sorted(by_area):
        for group in group_adjacent(by_area[area], neighbours, settings.province_size):
            serial += 1
            name = f"rnw_prov_{serial:05d}"
            plan.province_names[name] = province_names.next()
            for index in group:
                province_of[index] = name
    homeless_provinces = group_adjacent(homeless, neighbours, settings.province_size)
    links = lift_groups(homeless_provinces, neighbours)
    area_names = NameGenerator(seed, "areas")
    for number, members in enumerate(
        group_adjacent(list(range(len(homeless_provinces))), links, AREA_SIZE), start=1
    ):
        area = f"rnw_area_{number:04d}"
        cells = [index for province in members for index in homeless_provinces[province]]
        plan.new_areas[area] = []
        plan.display_overrides[area] = area_names.next()
        centre = (rolled_centres[cells].sum(axis=0) // len(cells)).reshape(1, 2)
        nearest_area = _nearest(centre, land_areas)[0]
        plan.area_region[area] = hierarchy_region(hierarchy, game_map, nearest_area)
        for province in members:
            serial += 1
            name = f"rnw_prov_{serial:05d}"
            plan.province_names[name] = province_names.next()
            plan.new_areas[area].append(name)
            for index in homeless_provinces[province]:
                province_of[index] = name
                area_of[index] = area
    parents = _area_parents(hierarchy)
    for area, region in plan.area_region.items():
        parents[area] = (region, *parents_of_region(parents, region))
    used = set(game_map.colors.tolist())
    colors = _colors(seed, len(world.classes), {int(value) for value in used})
    location_names = NameGenerator(seed, "locations")
    serials = dict.fromkeys(KEY_PREFIX, 0)
    for index, kind in enumerate(world.classes):
        serials[kind] += 1
        region, subcontinent, continent = parents[area_of[index]]
        plan.cells.append(
            PlannedCell(
                key=f"{KEY_PREFIX[kind]}{serials[kind]:05d}",
                name=location_names.next() + NAME_SUFFIX[kind],
                color=colors[index],
                kind=kind,
                province=province_of[index],
                area=area_of[index],
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


def parents_of_region(parents: dict[str, tuple[str, str, str]], region: str) -> tuple[str, str]:
    """Subcontinent and continent of a vanilla region."""
    for found_region, subcontinent, continent in parents.values():
        if found_region == region:
            return subcontinent, continent
    message = f"Unknown region: {region}"
    raise KeyError(message)


def hierarchy_region(hierarchy: dict[str, Location], game_map: Eu5Map, area: str) -> str:
    """Region of a vanilla area (the first location found)."""
    for key in game_map.keys:
        location = hierarchy.get(key)
        if location is not None and location.area == area:
            return location.region
    message = f"Unknown area: {area}"
    raise KeyError(message)


def _is_new_world(hierarchy: dict[str, Location], name: str) -> bool:
    return any(
        location.continent == NEW_WORLD and name in {location.area, location.region}
        for location in hierarchy.values()
    )
