"""Climate, vegetation, topography and raw materials for generated EU5 locations.

EU5 1.4.1 renders each location with the biome that its template's climate, vegetation
and topography select in ``gfx/map/biome_definitions/biomes.txt`` [V-LOCAL C50], so a
coherent look needs coherent templates. Each generated location gets physical features
from the same model that is applied to the vanilla map: absolute latitude, mean height,
distance to the sea and zonal-wind rainfall (``climate.py``). An integer
k-nearest-neighbour vote over Old World locations calibrates climate and vegetation;
scores are then smoothed over the location adjacency graph so zones are contiguous.
Topography comes from relief ranks with vanilla shares; raw materials are drawn from
vanilla frequencies. The New World starts empty, so farmland is learned as grassland.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.climate import RainSettings, rainfall
from rnw.eu5_canvas import NEW_WORLD, OCEANS
from rnw.fields import block_mean
from rnw.model import CellClass
from rnw.rng import derive_seed, hash_point
from rnw.topology import adjacency_pairs, distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

FIELDS: Final[re.Pattern[str]] = re.compile(
    r"\b(climate|vegetation|topography|raw_material)\s*=\s*([A-Za-z_]+)"
)
TEMPLATE: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*\{([^{}]*)\}", re.MULTILINE)
RULE: Final[re.Pattern[str]] = re.compile(r"^\s*[A-Za-z0-9_]+\s*=\s*\{([^{}]*)\}", re.MULTILINE)
ASSIGNMENT: Final[re.Pattern[str]] = re.compile(r"\b([a-z_]+)\s*=\s*([A-Za-z0-9_]+)")
MATERIAL_LIST: Final[re.Pattern[str]] = re.compile(
    r"\bname\s*=\s*([A-Za-z0-9_]+)\s+materials\s*=\s*\{([^{}]*)\}"
)
BIOME_KEYS: Final[tuple[str, ...]] = ("climate", "vegetation", "topography")
BIOME_DEFINITIONS: Final[str] = "game/in_game/gfx/map/biome_definitions/biomes.txt"
TERRAIN_MATERIALS: Final[str] = "game/in_game/gfx/terrain2/materials.txt"
CLIMATE_STEP: Final[int] = 4
# Rows per strip of the whole-raster climate passes; a multiple of CLIMATE_STEP.
CLIMATE_STRIP: Final[int] = 1024
# Row of the equator and (pixels from it, absolute latitude in tenths of a degree), from
# city locators of build 25905365 [V-LOCAL C49]: Quito, Mogadishu and Singapore near
# the equator, Cairo 30.0, London 51.5, Oslo 59.9, Arkhangelsk 64.5, Hammerfest 70.7.
EQUATOR_ROW: Final[int] = 4839
LATITUDE_ANCHORS: Final[tuple[tuple[int, int], ...]] = (
    (0, 0), (1689, 300), (3029, 515), (3622, 599), (3985, 645), (4455, 707),
)  # fmt: skip
RAIN: Final[RainSettings] = RainSettings(
    decay_px=225, recharge_px=40, lift_units=8000, blur_px=16, relief_blur_px=8
)
SEA_HEIGHT: Final[int] = 5700
COAST_LIMIT: Final[int] = 160
NEIGHBOURS: Final[int] = 32
CHUNK: Final[int] = 128
# Feature weights in tenths: latitude, rainfall, height, distance to sea.
LAND_WEIGHTS: Final[tuple[int, ...]] = (50, 30, 25, 10)
WATER_WEIGHTS: Final[tuple[int, ...]] = (40, 10)
CLIMATE_ROUNDS: Final[int] = 3
VEGETATION_ROUNDS: Final[int] = 1
SELF_WEIGHT: Final[int] = 2
TOPOGRAPHIES: Final[tuple[str, ...]] = ("mountains", "plateau", "hills", "wetlands", "flatland")
EMPTY_LAND: Final[dict[str, str]] = {"farmland": "grasslands"}
# biomes.txt defines no desert wetlands biome; such templates fall to default_biome, whose
# only material is fallback_material [V-LOCAL C54].
NO_WETLANDS: Final[frozenset[str]] = frozenset({"desert"})
MOUNTAIN_WASTE_HEIGHT: Final[int] = 14000
FLAT_WASTE_SPREAD: Final[int] = 900
LAND_KINDS: Final[frozenset[CellClass]] = frozenset(
    {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
)
WATER_KINDS: Final[frozenset[CellClass]] = frozenset({CellClass.SEA, CellClass.LAKE})


def template_attributes(text: str) -> dict[str, dict[str, str]]:
    """Climate, vegetation, topography and raw material of every template."""
    return {key: dict(FIELDS.findall(body)) for key, body in TEMPLATE.findall(text)}


def _without_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


@dataclass(frozen=True, slots=True)
class BiomeRule:
    """One ``biomes.txt`` definition: accepted values per attribute (empty = any)."""

    climate: frozenset[str]
    vegetation: frozenset[str]
    topography: frozenset[str]
    biome: str


def biome_rules(text: str) -> list[BiomeRule]:
    """Definitions of ``gfx/map/biome_definitions/biomes.txt`` in file order."""
    rules: list[BiomeRule] = []
    for body in RULE.findall(_without_comments(text)):
        values: dict[str, set[str]] = {key: set() for key in BIOME_KEYS}
        biome = ""
        for key, value in ASSIGNMENT.findall(body):
            if key == "biome":
                biome = value
            elif key in values:
                values[key].add(value)
        if biome:
            rules.append(
                BiomeRule(
                    climate=frozenset(values["climate"]),
                    vegetation=frozenset(values["vegetation"]),
                    topography=frozenset(values["topography"]),
                    biome=biome,
                )
            )
    return rules


def biome_of(rules: list[BiomeRule], climate: str, vegetation: str, topography: str) -> str:
    """Biome of the matching rule that names the most attributes; the first wins ties."""
    best, named = "", -1
    values = (climate, vegetation, topography)
    for rule in rules:
        sets = (rule.climate, rule.vegetation, rule.topography)
        pairs = zip(sets, values, strict=True)
        if all(not accepted or value in accepted for accepted, value in pairs):
            count = sum(1 for accepted in sets if accepted)
            if count > named:
                best, named = rule.biome, count
    return best


def material_counts(text: str) -> dict[str, int]:
    """Number of material slots each biome of ``gfx/terrain2/materials.txt`` defines."""
    return {
        name: len(body.split()) for name, body in MATERIAL_LIST.findall(_without_comments(text))
    }


def latitude_tenths(rows: NDArray[np.int64]) -> NDArray[np.int64]:
    """Absolute latitude in tenths of a degree for raster rows (piecewise linear)."""
    offset = np.abs(rows - EQUATOR_ROW)
    out = np.zeros(offset.shape, dtype=np.int64)
    pairs = list(pairwise(LATITUDE_ANCHORS))
    for (p0, l0), (p1, l1) in pairs:
        inside = (offset >= p0) & (offset <= p1)
        out[inside] = l0 + (offset[inside] - p0) * (l1 - l0) // (p1 - p0)
    (p0, l0), (p1, l1) = pairs[-1]
    beyond = offset > p1
    out[beyond] = l1 + (offset[beyond] - p1) * (l1 - l0) // (p1 - p0)
    return out


@dataclass(frozen=True, slots=True, eq=False)
class ClimateGrid:
    """Climate fields on a grid ``CLIMATE_STEP`` times coarser than the location raster."""

    rain: NDArray[np.int64]
    coast: NDArray[np.int64]
    shore: NDArray[np.int64]


def _block_means(
    sea: NDArray[np.bool_], height: NDArray[np.integer], strip: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Block means of the sea share (permille) and of the height, a strip of rows at a time.

    ``strip`` is a multiple of ``CLIMATE_STEP``, so every block lies in one strip and the
    result is the same as for the whole raster, without an eight-byte copy of it.
    """
    step = CLIMATE_STEP
    rows, columns = (int(size) for size in sea.shape)
    shape = (-(-rows // step), -(-columns // step))
    share = np.empty(shape, dtype=np.int64)
    mean = np.empty(shape, dtype=np.int64)
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        blocks = slice(first // step, -(-window.stop // step))
        share[blocks] = block_mean(sea[window].astype(np.int64) * 1000, step)
        mean[blocks] = block_mean(height[window].astype(np.int64), step)
    return share, mean


def climate_grid(sea: NDArray[np.bool_], height: NDArray[np.integer]) -> ClimateGrid:
    """Rainfall, distance to the sea (land) and distance to land (water), in pixels."""
    step = CLIMATE_STEP
    share, mean = _block_means(sea, height, CLIMATE_STRIP)
    sea_grid = share >= 500  # noqa: PLR2004 - half
    height_grid = np.maximum(mean, SEA_HEIGHT)
    rows = np.arange(sea_grid.shape[0], dtype=np.int64) * step + step // 2
    rain = rainfall(sea_grid, height_grid, latitude_tenths(rows), RAIN)
    coast = distance_from(sea_grid, COAST_LIMIT, octagonal=True).astype(np.int64) * step
    shore = distance_from(~sea_grid, COAST_LIMIT, octagonal=True).astype(np.int64) * step
    return ClimateGrid(rain=rain, coast=coast, shore=shore)


def _sample(grid: NDArray[np.int64], points: NDArray[np.int64]) -> NDArray[np.int64]:
    rows = np.clip(points[:, 0] // CLIMATE_STEP, 0, grid.shape[0] - 1)
    columns = np.clip(points[:, 1] // CLIMATE_STEP, 0, grid.shape[1] - 1)
    return grid[rows, columns]


def land_features(
    grid: ClimateGrid, points: NDArray[np.int64], mean_height: NDArray[np.int64]
) -> NDArray[np.int64]:
    """Latitude, rainfall, mean height and distance to the sea per location.

    Height spread is left out: vanilla decals carry far more fine relief than the
    location-scale relief field, so the two would not be comparable.
    """
    return np.stack(
        [
            latitude_tenths(points[:, 0]),
            _sample(grid.rain, points),
            mean_height,
            _sample(grid.coast, points),
        ],
        axis=1,
    )


def water_features(grid: ClimateGrid, points: NDArray[np.int64]) -> NDArray[np.int64]:
    """Latitude and distance to land per water location."""
    return np.stack([latitude_tenths(points[:, 0]), _sample(grid.shore, points)], axis=1)


def _standardize(
    train: NDArray[np.int64], query: NDArray[np.int64], weights: tuple[int, ...]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    count = max(1, train.shape[0])
    mean = train.sum(axis=0) // count
    variance = ((train - mean) ** 2).sum(axis=0) // count
    std = np.array([max(1, math.isqrt(int(value))) for value in variance.tolist()])
    scale = np.array(weights, dtype=np.int64) * 100
    return (train - mean) * scale // std, (query - mean) * scale // std


def knn_scores(
    train: NDArray[np.int64], classes: NDArray[np.int64], query: NDArray[np.int64], count: int
) -> NDArray[np.int64]:
    """Rank-weighted votes of the nearest training rows (ties by training index)."""
    k = min(NEIGHBOURS, train.shape[0])
    scores = np.zeros((query.shape[0], count), dtype=np.int64)
    if k == 0:
        return scores
    weights = np.arange(k, 0, -1, dtype=np.int64)
    for start in range(0, query.shape[0], CHUNK):
        block = query[start : start + CHUNK]
        distance = ((block[:, np.newaxis, :] - train[np.newaxis, :, :]) ** 2).sum(axis=2)
        nearest = np.argpartition(distance, k - 1, axis=1)[:, :k]
        near_distance = np.take_along_axis(distance, nearest, axis=1)
        order = np.lexsort((nearest, near_distance), axis=-1)
        nearest = np.take_along_axis(nearest, order, axis=1)
        size = int(block.shape[0])
        rows = np.repeat(np.arange(size, dtype=np.int64), k)
        np.add.at(
            scores[start : start + size], (rows, classes[nearest].ravel()), np.tile(weights, size)
        )
    return scores


def smooth_scores(
    scores: NDArray[np.int64], edges: NDArray[np.int64], rounds: int
) -> NDArray[np.int64]:
    """Average each node's class scores with its neighbours' (integer, per round)."""
    if not edges.size:
        return scores
    degree = np.bincount(edges.ravel(), minlength=scores.shape[0]).astype(np.int64)
    for _ in range(rounds):
        total = scores * SELF_WEIGHT
        np.add.at(total, edges[:, 0], scores[edges[:, 1]])
        np.add.at(total, edges[:, 1], scores[edges[:, 0]])
        scores = total * 64 // (SELF_WEIGHT + degree)[:, np.newaxis]
        scores //= max(1, int(scores.max()) >> 40)
    return scores


@dataclass(frozen=True, slots=True, eq=False)
class Generated:
    """Generated cells as seen by the biome model (world raster coordinates)."""

    kinds: tuple[CellClass, ...]
    points: NDArray[np.int64]
    mean_height: NDArray[np.int64]
    spread: NDArray[np.int64]
    edges: tuple[tuple[int, int], ...]
    coastal: NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class CellBiomes:
    """Template attributes per generated cell ("" where a field does not apply)."""

    climate: tuple[str, ...]
    vegetation: tuple[str, ...]
    topography: tuple[str, ...]
    raw_material: tuple[str, ...]


@dataclass(frozen=True, slots=True, eq=False)
class VanillaLocations:
    """Per vanilla label: centre and mean height; plus its contact pairs."""

    points: NDArray[np.int64]
    mean_height: NDArray[np.int64]
    pairs: NDArray[np.int64]


def vanilla_locations(labels: NDArray[np.int32], height: NDArray[np.uint16]) -> VanillaLocations:
    """Pixel-weighted centre and mean height of every vanilla label."""
    count = int(labels.max()) + 1
    width = labels.shape[1]
    sums = np.zeros((4, count), dtype=np.float64)
    for start in range(0, labels.shape[0], 1024):
        block = labels[start : start + 1024].ravel()
        values = height[start : start + 1024].ravel().astype(np.float64)
        index = np.arange(block.size, dtype=np.int64)
        sums[0] += np.bincount(block, minlength=count)
        sums[1] += np.bincount(block, weights=(index // width + start).astype(np.float64),
                               minlength=count)  # fmt: skip
        sums[2] += np.bincount(block, weights=(index % width).astype(np.float64), minlength=count)
        sums[3] += np.bincount(block, weights=values, minlength=count)
    exact = sums.astype(np.int64)
    pixels = np.maximum(1, exact[0])
    return VanillaLocations(
        points=np.stack([exact[1] // pixels, exact[2] // pixels], axis=1),
        mean_height=exact[3] // pixels,
        pairs=adjacency_pairs(labels, wrap_x=True),
    )


def _vocabulary(values: list[str]) -> tuple[list[str], NDArray[np.int64]]:
    names = sorted(set(values))
    index = {name: number for number, name in enumerate(names)}
    return names, np.array([index[value] for value in values], dtype=np.int64)


def _edge_array(edges: tuple[tuple[int, int], ...], keep: NDArray[np.bool_]) -> NDArray[np.int64]:
    kept = [(a, b) for a, b in edges if keep[a] and keep[b]]
    return np.array(kept, dtype=np.int64).reshape(-1, 2)


def _topography(  # noqa: PLR0913 - ranks use height, spread, rain and coast together.
    cells: list[int],
    *,
    shares: dict[str, int],
    mean_height: NDArray[np.int64],
    spread: NDArray[np.int64],
    rain: NDArray[np.int64],
    coast: NDArray[np.int64],
    dry: frozenset[int],
) -> dict[int, str]:
    """Assign topographies in vanilla proportions by relief and wetness ranks.

    Cells in ``dry`` never become wetlands.
    """
    remaining = list(cells)
    out: dict[int, str] = {}
    total = sum(shares.values())
    rain_rank = _ranks(rain, cells)
    height_rank = _ranks(mean_height, cells)
    coast_rank = _ranks(coast, cells)

    def score(name: str, i: int) -> int:
        if name == "mountains":
            return int(mean_height[i] + 2 * spread[i])
        if name == "plateau":
            return int(mean_height[i] - 3 * spread[i])
        if name == "hills":
            return int(spread[i])
        return rain_rank[i] - height_rank[i] - coast_rank[i] // 2

    for name in TOPOGRAPHIES[:-1]:
        wanted = len(cells) * shares.get(name, 0) // max(1, total)
        candidates = [i for i in remaining if name != "wetlands" or i not in dry]
        ranked = sorted(candidates, key=lambda i: (-score(name, i), i))
        chosen = set(ranked[:wanted])
        out.update(dict.fromkeys(chosen, name))
        remaining = [i for i in remaining if i not in chosen]
    out.update(dict.fromkeys(remaining, "flatland"))
    return out


def _ranks(values: NDArray[np.int64], cells: list[int]) -> dict[int, int]:
    """Permille rank of each cell's value among ``cells`` (ties by index)."""
    ordered = sorted(cells, key=lambda i: (int(values[i]), i))
    return {cell: position * 1000 // max(1, len(ordered)) for position, cell in enumerate(ordered)}


def _waste_topography(height: int, spread: int) -> str:
    if height >= MOUNTAIN_WASTE_HEIGHT:
        return "mountain_wasteland"
    return "plateau_wasteland" if spread < FLAT_WASTE_SPREAD else "hills_wasteland"


def _pick(counter: Counter[str], key: int) -> str:
    total = sum(counter.values())
    target = key % total
    for name in sorted(counter):
        target -= counter[name]
        if target < 0:
            return name
    return max(counter)


def _old_world(game_map: Eu5Map) -> NDArray[np.bool_]:
    return np.array(
        [name not in OCEANS and name != NEW_WORLD for name in game_map.continents], dtype=bool
    )


def assign_biomes(  # noqa: PLR0913, PLR0915 - one pass over the calibrated biome model.
    *,
    game_map: Eu5Map,
    templates: dict[str, dict[str, str]],
    vanilla: VanillaLocations,
    vanilla_grid: ClimateGrid,
    final_grid: ClimateGrid,
    cells: Generated,
    seed: int,
) -> tuple[CellBiomes, dict[str, object]]:
    """Template attributes for every generated cell and calibration statistics."""
    count = len(cells.kinds)
    old = _old_world(game_map)
    attributes = [templates.get(key, {}) for key in game_map.keys]
    land_train = [
        i
        for i, kind in enumerate(game_map.classes)
        if kind in LAND_KINDS and old[i] and "climate" in attributes[i]
        and "vegetation" in attributes[i]
    ]  # fmt: skip
    joint = [
        "|".join(
            (
                attributes[i]["climate"],
                EMPTY_LAND.get(attributes[i]["vegetation"], attributes[i]["vegetation"]),
            )
        )
        for i in land_train
    ]
    joint_names, joint_ids = _vocabulary(joint)
    climate_names, joint_climate = _vocabulary([name.split("|")[0] for name in joint_names])
    vegetation_names, joint_vegetation = _vocabulary([name.split("|")[1] for name in joint_names])
    train_index = np.array(land_train, dtype=np.int64)
    train_x = land_features(
        vanilla_grid,
        vanilla.points[train_index],
        vanilla.mean_height[train_index],
    )
    land = np.array([kind in LAND_KINDS for kind in cells.kinds], dtype=bool)
    land_cells = np.flatnonzero(land)
    query_x = land_features(
        final_grid,
        cells.points[land_cells],
        cells.mean_height[land_cells],
    )
    train_s, query_s = _standardize(train_x, query_x, LAND_WEIGHTS)
    scores = knn_scores(train_s, joint_ids, query_s, len(joint_names))
    position = np.full(count, -1, dtype=np.int64)
    position[land_cells] = np.arange(land_cells.size)
    edges = _edge_array(cells.edges, land)
    local_edges = position[edges] if edges.size else edges
    climate_scores = np.zeros((land_cells.size, len(climate_names)), dtype=np.int64)
    np.add.at(climate_scores.T, joint_climate, scores.T)
    climate_scores = smooth_scores(climate_scores, local_edges, CLIMATE_ROUNDS)
    climate_choice = np.argmax(climate_scores, axis=1)
    allowed = joint_climate[np.newaxis, :] == climate_choice[:, np.newaxis]
    vegetation_scores = np.zeros((land_cells.size, len(vegetation_names)), dtype=np.int64)
    np.add.at(vegetation_scores.T, joint_vegetation, np.where(allowed, scores, 0).T)
    empty = vegetation_scores.sum(axis=1) == 0
    if np.any(empty):
        fallback = np.zeros_like(vegetation_scores)
        np.add.at(fallback.T, joint_vegetation, scores.T)
        vegetation_scores[empty] = fallback[empty]
    vegetation_scores = smooth_scores(vegetation_scores, local_edges, VEGETATION_ROUNDS)
    vegetation_choice = np.argmax(vegetation_scores, axis=1)
    climate = [""] * count
    vegetation = [""] * count
    for slot, cell in enumerate(land_cells.tolist()):
        climate[cell] = climate_names[int(climate_choice[slot])]
        vegetation[cell] = vegetation_names[int(vegetation_choice[slot])]
    shares = Counter(
        attributes[i].get("topography", "")
        for i, kind in enumerate(game_map.classes)
        if kind is CellClass.LAND and old[i]
    )
    topography = [""] * count
    plain = [i for i in land_cells.tolist() if cells.kinds[i] is CellClass.LAND]
    rain = np.zeros(count, dtype=np.int64)
    coast = np.zeros(count, dtype=np.int64)
    rain[land_cells] = query_x[:, 1]
    coast[land_cells] = query_x[:, 3]
    ranked = _topography(
        plain,
        shares={name: shares[name] for name in TOPOGRAPHIES},
        mean_height=cells.mean_height,
        spread=cells.spread,
        rain=rain,
        coast=coast,
        dry=frozenset(i for i in plain if vegetation[i] in NO_WETLANDS),
    )
    for cell, name in ranked.items():
        topography[cell] = name
    for cell in land_cells.tolist():
        if cells.kinds[cell] is CellClass.WASTELAND:
            topography[cell] = _waste_topography(
                int(cells.mean_height[cell]), int(cells.spread[cell])
            )
    water_train = [
        i
        for i, kind in enumerate(game_map.classes)
        if kind in WATER_KINDS and old[i] and "climate" in attributes[i]
    ]
    water_cells = np.flatnonzero(~land)
    if water_train and water_cells.size:
        water_names, water_ids = _vocabulary([attributes[i]["climate"] for i in water_train])
        water_index = np.array(water_train, dtype=np.int64)
        water_s, water_q = _standardize(
            water_features(vanilla_grid, vanilla.points[water_index]),
            water_features(final_grid, cells.points[water_cells]),
            WATER_WEIGHTS,
        )
        water_choice = np.argmax(knn_scores(water_s, water_ids, water_q, len(water_names)), axis=1)
        for slot, cell in enumerate(water_cells.tolist()):
            climate[cell] = water_names[int(water_choice[slot])]
    raw = _raw_materials(
        game_map,
        attributes=attributes,
        vanilla=vanilla,
        old=old,
        cells=cells,
        fields=(climate, vegetation, topography),
        seed=seed,
    )
    result = CellBiomes(tuple(climate), tuple(vegetation), tuple(topography), raw)
    stats: dict[str, object] = {
        "training_land_locations": len(land_train),
        "climate_classes": climate_names,
        "vegetation_classes": vegetation_names,
        "topography_shares": {name: shares[name] for name in TOPOGRAPHIES},
    }
    return result, stats


def _raw_materials(  # noqa: PLR0913 - raw materials depend on every template field.
    game_map: Eu5Map,
    *,
    attributes: list[dict[str, str]],
    vanilla: VanillaLocations,
    old: NDArray[np.bool_],
    cells: Generated,
    fields: tuple[list[str], list[str], list[str]],
    seed: int,
) -> tuple[str, ...]:
    """Draw each land cell's raw material from vanilla frequencies of similar locations."""
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    mask = np.int64((1 << 32) - 1)
    low = vanilla.pairs >> np.int64(32)
    high = vanilla.pairs & mask
    coastal = np.zeros(len(game_map.keys), dtype=bool)
    coastal[low[sea[high]]] = True
    coastal[high[sea[low]]] = True
    tables: list[dict[tuple[str, ...], Counter[str]]] = [{}, {}, {}, {}]
    for i, kind in enumerate(game_map.classes):
        if kind is not CellClass.LAND or not old[i] or "raw_material" not in attributes[i]:
            continue
        row = attributes[i]
        vegetation = EMPTY_LAND.get(row.get("vegetation", ""), row.get("vegetation", ""))
        flag = "coast" if coastal[i] else "inland"
        keys = (
            (row.get("climate", ""), vegetation, row.get("topography", ""), flag),
            (row.get("climate", ""), vegetation, flag),
            (vegetation, flag),
            (flag,),
        )
        for table, key in zip(tables, keys, strict=True):
            table.setdefault(key, Counter())[row["raw_material"]] += 1
    climate, vegetation, topography = fields
    stream = derive_seed(seed, "raw_material")
    out: list[str] = []
    for cell, kind in enumerate(cells.kinds):
        if kind is not CellClass.LAND:
            out.append("")
            continue
        flag = "coast" if cells.coastal[cell] else "inland"
        keys = (
            (climate[cell], vegetation[cell], topography[cell], flag),
            (climate[cell], vegetation[cell], flag),
            (vegetation[cell], flag),
            (flag,),
        )
        counter = next(
            (table[key] for table, key in zip(tables, keys, strict=True) if key in table),
            Counter({"stone": 1}),
        )
        out.append(_pick(counter, hash_point(stream, cell, 0)))
    return tuple(out)


def label_statistics(labels: list[str], edges: NDArray[np.int64]) -> dict[str, int]:
    """Coherence of a labelling on a graph: same-label edge share and region sizes."""
    count = len(labels)
    if count == 0:
        return {"nodes": 0}
    parent = list(range(count))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    same = 0
    for a, b in edges.tolist():
        if labels[a] == labels[b]:
            same += 1
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[max(root_a, root_b)] = min(root_a, root_b)
    sizes = Counter(find(i) for i in range(count))
    values = sorted(sizes.values())
    return {
        "nodes": count,
        "same_label_edges_permille": same * 1000 // max(1, len(edges)),
        "regions": len(values),
        "mean_region_size_x10": count * 10 // max(1, len(values)),
        "singleton_regions_permille": sum(1 for v in values if v == 1) * 1000 // len(values),
        "largest_region": values[-1],
    }
