"""Climate, vegetation, topography and raw materials for generated EU5 locations.

EU5 1.4.1 renders each location with the biome that its template's climate, vegetation
and topography select in ``gfx/map/biome_definitions/biomes.txt`` [V-LOCAL C50], so a
coherent look needs coherent templates. Each generated location gets physical features
from the same model that is applied to the vanilla map: absolute latitude, mean height,
distance to the sea and zonal-wind rainfall (``climate.py``). An integer
k-nearest-neighbour vote over Old World locations calibrates climate and vegetation as joint
(climate, vegetation) pairs; the votes are then smoothed over the location adjacency graph so
zones are contiguous, and a cell's vegetation is chosen among the pairs of its own climate.
Topography comes from relief ranks with vanilla shares; raw materials are drawn from
vanilla frequencies. The New World starts empty, so farmland is learned as grassland; from epoch
64 the vote leaves farmland out and learns from the vanilla Americas as well (``OPEN_CLIMATE``).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from itertools import pairwise
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.barrens import (
    FLAT_SPREAD,
    MOUNTAIN_FLOOR,
    Terrain,
    WastelandPlan,
    WastelandSettings,
    calibrate,
    legacy_topography,
    plan_wastelands,
)
from rnw.climate import RainSettings, rainfall
from rnw.eu5_canvas import NEW_WORLD, OCEANS
from rnw.fields import block_mean
from rnw.model import CellClass
from rnw.parallel import worker_count
from rnw.progress import checkpoint
from rnw.relief import HILL_STEP, cell_roughness, strip_bend
from rnw.rng import derive_seed, hash_point
from rnw.settings import RESOURCES, ResourceSettings, SettingsError
from rnw.topology import adjacency_pairs, distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

PERMILLE: Final[int] = 1000
# Materials whose weight the precious setting scales.
PRECIOUS: Final[frozenset[str]] = frozenset({"goods_gold", "silver", "gems", "pearls"})
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
DEFAULT_BIOME: Final[str] = "default_biome"
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
# Epoch 64 (``epoch.OPEN_CLIMATE``): the vote learns from the vanilla Americas as well as the Old
# World, leaves out the cultivated locations (``CULTIVATED``) instead of reading them as grassland,
# so that the land they were cleared from votes there, and smooths over fewer rounds: three
# rounds left 59 cells per climate region against vanilla's 13 and ate the transitional climates
# (1.7 % semi-arid and cold arid land against vanilla's 9.3 %) [V-EXEC 2026-11-13].
CULTIVATED: Final[frozenset[str]] = frozenset({"farmland"})
OPEN_CLIMATE_ROUNDS: Final[int] = 0
OPEN_VEGETATION_ROUNDS: Final[int] = 0
# A plurality of 32 neighbours seldom names a class that is rare among them: read without itself,
# a vanilla location was given a semi-arid or cold arid climate 72 times in a thousand where 91
# are, and a Mediterranean one where it is not. The votes of each (climate, vegetation) pair are
# therefore weighed so that the vote gives every pair about as many of the training locations,
# each read without itself, as hold it (``calibrated_weights``): ``CALIBRATION_ROUNDS`` rounds
# from the cube root of the inverse of its share (``prior_weights``), each multiplying a weight by
# the square root of its rows over the rows it was chosen for, rescaled to ``WEIGHT_TOP``.
# Calibrated on the Old World alone, the vote gives the Americas 89 permille of those climates
# (they hold 87; the cube root gave 82) [V-EXEC 2026-11-13]. ``PRIOR_SCALE`` keeps the integer
# root fine-grained.
PRIOR_SCALE: Final[int] = 10**12
CALIBRATION_ROUNDS: Final[int] = 10
CALIBRATION_THREADS: Final[int] = 8  # each searches the neighbours of its own CHUNK rows
WEIGHT_TOP: Final[int] = 1 << 20
# Seeds are spaced by the size vanilla gives a location of the class the vote will choose
# (epoch 64, ``epoch.RIVERS_FIRST``, ``SizeModel``); sizes are log2 of a location's pixels over
# its region's median in ``OCTAVE_PARTS``ths of an octave. Vanilla also sizes a location by its
# ground: by distance to the sea alike, its mountains are smaller and its plateaus and wetlands
# larger than the flatland of the same class (its hills are not). A generated block's ground is
# voted as the cells' is (``vote_grounds``), and its size moves by the mean amount vanilla's
# locations of that ground lie off the size of their class (``SizeModel.offsets``)
# [V-EXEC 2026-11-13].
RELIEF_ROWS: Final[int] = 512  # rows of a strip read for the relief of the size blocks
# Epoch 64 (``epoch.ROUGH_HILLS``): the ground of the land is voted, as its climate is, by the
# ``NEIGHBOURS`` vanilla Old World locations most like it (``vote_grounds``) in
# ``GROUND_COLUMNS`` readings, each ranked within its own map's land so that vanilla's decal
# relief and the generated relief compare: mean height, ruggedness (``cell_ruggedness``),
# roughness (``relief.cell_roughness``), rainfall and distance to the sea; each ground then takes
# its share of the Old World's locations. Read on vanilla itself, each location without itself,
# the former hand-made ranks (height and spread for mountains, rain against height and the sea
# for wetlands) named the ground of 635 Old World locations in a thousand (597 in the Americas),
# 19 % of their wetlands rightly, none of them over 120 px from the sea (384 are) and 116 coastal
# mountains (417 are); the vote names 750 (659), 42 % of the wetlands, 326 beyond 120 px and 360
# coastal mountains [V-EXEC 2026-11-13].
GROUND_COLUMNS: Final[int] = 5
OCTAVE_PARTS: Final[int] = 64
SIZE_STEP: Final[int] = 64  # pixels per block of the size model; a multiple of CLIMATE_STEP
# biomes.txt defines no desert wetlands biome; such templates fall to default_biome, whose
# only material is fallback_material [V-LOCAL C54].
NO_WETLANDS: Final[frozenset[str]] = frozenset({"desert"})
MOUNTAIN_WASTE_HEIGHT: Final[int] = MOUNTAIN_FLOOR
FLAT_WASTE_SPREAD: Final[int] = FLAT_SPREAD
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
        checkpoint()
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


def _nearest(train: NDArray[np.int64], block: NDArray[np.int64], k: int) -> NDArray[np.int64]:
    """The ``k`` nearest training rows of each row of ``block``, nearest first (ties by index).

    The squared distance is |a|^2 + |b|^2 - 2 a.b, exact in integers (standardized features are
    a few times 10^4, so every term stays far below 2^63) and the same as the sum of squared
    differences, at a third of the time.
    """
    distance = (train * train).sum(axis=1)[np.newaxis, :] - 2 * (block @ train.T)
    distance += (block * block).sum(axis=1)[:, np.newaxis]
    nearest = np.argpartition(distance, k - 1, axis=1)[:, :k]
    near_distance = np.take_along_axis(distance, nearest, axis=1)
    order = np.lexsort((nearest, near_distance), axis=-1)
    return np.take_along_axis(nearest, order, axis=1)


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
        nearest = _nearest(train, block, k)
        size = int(block.shape[0])
        rows = np.repeat(np.arange(size, dtype=np.int64), k)
        np.add.at(
            scores[start : start + size], (rows, classes[nearest].ravel()), np.tile(weights, size)
        )
    return scores


def knn_totals(
    train: NDArray[np.int64], values: NDArray[np.int64], query: NDArray[np.int64]
) -> tuple[NDArray[np.int64], int]:
    """The sum of ``values`` over the nearest training rows of each query row, and how many
    rows that is (``NEIGHBOURS``, or every row of a smaller ``train``)."""
    k = min(NEIGHBOURS, train.shape[0])
    totals = np.zeros(query.shape[0], dtype=np.int64)
    if k == 0:
        return totals, 0
    for start in range(0, query.shape[0], CHUNK):
        nearest = _nearest(train, query[start : start + CHUNK], k)
        totals[start : start + CHUNK] = values[nearest].sum(axis=1)
    return totals, k


def integer_cube_root(value: int) -> int:
    """The integer cube root of a non-negative integer (exact, by bisection)."""
    low, high = 0, 1 << ((value.bit_length() + 2) // 3 + 1)
    while low < high:
        middle = (low + high + 1) // 2
        if middle * middle * middle <= value:
            low = middle
        else:
            high = middle - 1
    return low


def prior_weights(classes: NDArray[np.int64], count: int) -> NDArray[np.int64]:
    """The weight of each class's votes: the integer cube root of ``PRIOR_SCALE`` over its share
    of ``classes`` (0 for a class with no row)."""
    rows = np.bincount(classes, minlength=count).tolist()
    total = sum(rows)
    return np.array(
        [integer_cube_root(PRIOR_SCALE * total // found) if found else 0 for found in rows],
        dtype=np.int64,
    )


def chosen_pairs(scores: NDArray[np.int64], climate_of: NDArray[np.int64]) -> NDArray[np.int64]:
    """The pair each row of ``scores`` chooses without smoothing: the climate whose pairs have
    the most votes, then that climate's pair with the most (``regularize_votes`` with no rounds).
    """
    climates = np.zeros((scores.shape[0], int(climate_of.max()) + 1), dtype=np.int64)
    np.add.at(climates.T, climate_of, scores.T)
    allowed = climate_of[np.newaxis, :] == np.argmax(climates, axis=1)[:, np.newaxis]
    return np.argmax(np.where(allowed, scores, 0), axis=1)


def _rescaled(weights: NDArray[np.int64]) -> NDArray[np.int64]:
    top = int(weights.max()) if weights.size else 0
    if top <= 0:
        return weights
    return np.where(weights > 0, np.maximum(1, weights * WEIGHT_TOP // top), 0)


def nearest_others(train: NDArray[np.int64], start: int, k: int) -> NDArray[np.int64]:
    """The ``k`` nearest rows of ``train`` to each of its ``CHUNK`` rows from ``start``, the row
    itself left out (nearest first, ties by index)."""
    size = min(CHUNK, int(train.shape[0]) - start)
    nearest = _nearest(train, train[start : start + size], k + 1)
    own = nearest == np.arange(start, start + size, dtype=np.int64)[:, np.newaxis]
    # A row behind k + 1 identical rows is not among its own nearest; it drops the last.
    own[~own.any(axis=1), -1] = True
    return nearest[~own].reshape(size, k)


def calibrated_weights(
    train: NDArray[np.int64], classes: NDArray[np.int64], climate_of: NDArray[np.int64]
) -> NDArray[np.int64]:
    """The weight of each pair's votes with which the vote reads the training rows as they are.

    Each row of ``train`` (standardized) is voted on by its ``NEIGHBOURS`` nearest other rows;
    over ``CALIBRATION_ROUNDS`` rounds from ``prior_weights`` the weight of a pair is multiplied
    by the square root of the rows that hold it over the rows it is chosen for, so that every pair
    is chosen about as often as vanilla holds it. A pair without rows weighs nothing.
    """
    count = int(climate_of.size)
    weights = _rescaled(prior_weights(classes, count))
    k = min(NEIGHBOURS, int(train.shape[0]) - 1)
    if k <= 0:
        return weights
    held = np.bincount(classes, minlength=count).tolist()
    scores = np.zeros((train.shape[0], count), dtype=np.int64)
    rank = np.arange(k, 0, -1, dtype=np.int64)
    starts = range(0, int(train.shape[0]), CHUNK)

    def search(first: int) -> NDArray[np.int64]:
        return nearest_others(train, first, k)

    # A distance row and its partition per training row and thread, four arrays of int64.
    workers = worker_count(CALIBRATION_THREADS, bytes_each=32 * CHUNK * int(train.shape[0]))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        searched = pool.map(search, starts)
        for start, nearest in zip(starts, searched, strict=True):
            checkpoint()
            size = int(nearest.shape[0])
            rows = np.repeat(np.arange(size, dtype=np.int64), k)
            np.add.at(
                scores[start : start + size], (rows, classes[nearest].ravel()), np.tile(rank, size)
            )
    for _ in range(CALIBRATION_ROUNDS):
        chosen = np.bincount(
            chosen_pairs(scores * weights[np.newaxis, :], climate_of), minlength=count
        ).tolist()
        weights = _rescaled(
            np.array(
                [
                    math.isqrt(weight * weight * (rows + 1) // (found + 1)) if rows else 0
                    for weight, rows, found in zip(weights.tolist(), held, chosen, strict=True)
                ],
                dtype=np.int64,
            )
        )
    return weights


def block_features(
    land: NDArray[np.bool_], height: NDArray[np.integer], grid: ClimateGrid
) -> tuple[NDArray[np.bool_], NDArray[np.int64]]:
    """The ``SIZE_STEP`` blocks with land and the ``land_features`` of their land, in raster
    order: the latitude of the block's centre, and the mean rainfall, height and distance to the
    sea over its land. The vanilla map (``size_model``) and a generated domain
    (``watersheds.spacing_grid``) are read alike."""
    step = SIZE_STEP
    rows, columns = (int(size) for size in land.shape)
    shape = (-(-rows // step), -(-columns // step))
    # Means scaled by the pixels of a whole block are sums there, so a block with one pixel of
    # land has it and the ratios below are exact for whole blocks.
    area = step * step
    count = np.empty(shape, dtype=np.int64)
    total = np.empty(shape, dtype=np.int64)
    strip = step * 16
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        blocks = slice(first // step, -(-window.stop // step))
        on_land = land[window]
        count[blocks] = block_mean(on_land.astype(np.int64) * area, step)
        total[blocks] = block_mean(
            np.where(on_land, height[window], 0).astype(np.int64) * area, step
        )
    # The land share of each climate cell weighs its rain and distance to the sea.
    weight = _climate_share(land)
    ratio = step // CLIMATE_STEP
    cells = ratio * ratio
    weights = np.maximum(block_mean(weight * cells, ratio)[: shape[0], : shape[1]], 1)
    rain = block_mean(grid.rain * weight * cells, ratio)[: shape[0], : shape[1]] // weights
    coast = block_mean(grid.coast * weight * cells, ratio)[: shape[0], : shape[1]] // weights
    found = count > 0
    centres = np.arange(shape[0], dtype=np.int64) * step + step // 2
    latitude = np.broadcast_to(latitude_tenths(centres)[:, np.newaxis], shape)
    features = np.stack(
        [latitude[found], rain[found], (total // np.maximum(count, 1))[found], coast[found]],
        axis=1,
    )
    return found, features


def block_relief(
    land: NDArray[np.bool_], height: NDArray[np.integer], found: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """The spread and the bend of the height of the land of each ``found`` ``SIZE_STEP`` block,
    in raster order (``block_features``): the standard deviation of its height and the mean of
    ``relief.strip_bend``, which ``_topography`` ranks as it ranks the cells' (integers)."""
    step = SIZE_STEP
    rows, columns = (int(size) for size in land.shape)
    width = -(-columns // step)
    blocks = int(found.size)
    count = np.zeros(blocks, dtype=np.int64)
    total = np.zeros(blocks, dtype=np.int64)
    square = np.zeros(blocks, dtype=np.int64)
    bent = np.zeros(blocks, dtype=np.int64)
    read = np.zeros(blocks, dtype=np.int64)
    column_block = np.arange(columns, dtype=np.int64) // step
    for start in range(0, rows, RELIEF_ROWS):
        checkpoint()
        stop = min(rows, start + RELIEF_ROWS)
        low, high = max(0, start - HILL_STEP), min(rows, stop + HILL_STEP)
        bend = strip_bend(land[low:high], height[low:high], start, stop, rows)
        on_land = land[start:stop]
        values = height[start:stop].astype(np.int64)
        index = (np.arange(start, stop, dtype=np.int64)[:, np.newaxis] // step) * width
        index = np.broadcast_to(index + column_block[np.newaxis, :], on_land.shape)
        owner = index[on_land]
        # Exact: integer sums below 2^53 in a strip.
        count += np.bincount(owner, minlength=blocks)
        total += np.bincount(owner, weights=values[on_land], minlength=blocks).astype(np.int64)
        square += np.bincount(
            owner, weights=values[on_land] * values[on_land], minlength=blocks
        ).astype(np.int64)
        kept = on_land & (bend >= 0)
        bent += np.bincount(index[kept], weights=bend[kept], minlength=blocks).astype(np.int64)
        read += np.bincount(index[kept], minlength=blocks)
    where = np.flatnonzero(found.ravel())
    pixels = np.maximum(count[where], 1)
    mean = total[where] // pixels
    variance = np.maximum(square[where] // pixels - mean * mean, 0)
    spread = np.array([math.isqrt(int(value)) for value in variance.tolist()], dtype=np.int64)
    return np.stack([spread, bent[where] // np.maximum(read[where], 1)], axis=1)


def cell_ruggedness(
    labels: NDArray[np.int32],
    elevation: NDArray[np.integer],
    count: int,
    land: NDArray[np.bool_] | None = None,
) -> NDArray[np.int64]:
    """How broken the ground of each of the first ``count`` cells (the land cells) is: the mean,
    over its pixels, of the spread of the height of the land of the ``SIZE_STEP`` block each
    lies in (``block_relief``). A cell's own spread grows with the cell, as the variance of a
    fractal relief grows with the area read, so ranked by it the largest cells became mountains
    and the smallest plateaus; this reads every cell at the same scale, as the size model reads
    its blocks. ``land`` marks the land pixels when the land cells are not simply the first
    ``count`` labels (vanilla's map, ``size_model``). Integers."""
    rows, columns = (int(size) for size in labels.shape)
    step = SIZE_STEP
    shape = (-(-rows // step), -(-columns // step))
    on_land = (labels >= 0) & (labels < count) if land is None else land
    relief = block_relief(on_land, elevation, np.ones(shape, dtype=bool))
    del on_land
    cells = max(count, int(labels.max()) + 1)
    pixels, sums = _location_sums(labels, relief[:, :1], shape, cells)
    return sums[:count, 0] // np.maximum(pixels[:count], 1)


def ground_ranks(table: NDArray[np.int64]) -> NDArray[np.int64]:
    """Each column of ``table`` as the permille rank of its rows among them (ties by row)."""
    count = int(table.shape[0])
    order = np.arange(count, dtype=np.int64)
    out = np.empty_like(table)
    for column in range(int(table.shape[1])):
        out[np.lexsort((order, table[:, column])), column] = order * PERMILLE // max(1, count)
    return out


def vote_grounds(
    model: SizeModel,
    query: NDArray[np.int64],
    dry: NDArray[np.bool_],
    shares: NDArray[np.int64],
) -> NDArray[np.int64]:
    """The ground (an index of ``TOPOGRAPHIES``) of each row of ``query``: its ``GROUND_COLUMNS``
    readings (mean height, ruggedness, roughness, rainfall, distance to the sea) are ranked among
    the rows of ``query`` and the vanilla locations nearest in rank vote
    (``SizeModel.ground_table``, ``knn_scores``). In the order of ``TOPOGRAPHIES`` each ground
    takes the rows that vote most for it, as many as its ``shares`` give, wetlands never ``dry``
    rows; the rest is flatland. Ties go by the row's order."""
    if model.grounds.size == 0:
        message = "The size model has no ground to learn from"
        raise ValueError(message)
    count = int(query.shape[0])
    kinds = len(TOPOGRAPHIES)
    scores = knn_scores(model.ground_table, model.grounds, ground_ranks(query), kinds)
    total = max(1, int(shares.sum()))
    ground = np.full(count, kinds - 1, dtype=np.int64)
    free = np.ones(count, dtype=bool)
    for kind in range(kinds - 1):
        wanted = count * int(shares[kind]) // total
        open_rows = free & ~dry if TOPOGRAPHIES[kind] == "wetlands" else free
        candidates = np.flatnonzero(open_rows)
        chosen = candidates[np.lexsort((candidates, -scores[candidates, kind]))][:wanted]
        ground[chosen] = kind
        free[chosen] = False
    return ground


def _climate_share(land: NDArray[np.bool_]) -> NDArray[np.int64]:
    """The land share (permille) of every ``CLIMATE_STEP`` cell, a strip of rows at a time."""
    step = CLIMATE_STEP
    rows, columns = (int(size) for size in land.shape)
    out = np.empty((-(-rows // step), -(-columns // step)), dtype=np.int64)
    strip = step * 256
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        out[first // step : -(-window.stop // step)] = block_mean(
            land[window].astype(np.int64) * PERMILLE, step
        )
    return out


def octave_parts(pixels: int, median: int) -> int:
    """``floor(OCTAVE_PARTS * log2(pixels / median))``, exactly (both positive)."""
    above, below = pixels**OCTAVE_PARTS, median**OCTAVE_PARTS
    parts = above.bit_length() - below.bit_length()
    too_far = (below << parts > above) if parts >= 0 else (below > above << -parts)
    return parts - int(too_far)


@dataclass(frozen=True, slots=True, eq=False)
class SizeModel:
    """The vanilla land locations the seed spacing learns from (``size_model``).

    ``features`` are the ``block_features`` of the ``SIZE_STEP`` blocks of each location, averaged
    over its pixels; ``pairs`` are their (climate, vegetation) pairs, ``climate_of`` the climate of
    each pair, ``size`` log2 of their pixels over the median of their region (the Old World,
    the Americas) in ``OCTAVE_PARTS``ths of an octave and ``weights`` the ``calibrated_weights``
    of the pairs' votes (``size_table``). ``shares`` are vanilla's counts of each of
    ``TOPOGRAPHIES``, ``dry`` the pairs that are never wetland and ``offsets`` how far, in
    thousandths of an octave, vanilla's locations of each ground lie off the size of their class.
    ``ground_table`` holds
    the ``ground_ranks`` of the ``GROUND_COLUMNS`` readings of the Old World's passable locations
    and ``grounds`` their ground (``vote_grounds``).
    """

    features: NDArray[np.int64]
    pairs: NDArray[np.int64]
    climate_of: NDArray[np.int64]
    size: NDArray[np.int64]
    weights: NDArray[np.int64]
    shares: NDArray[np.int64]
    dry: NDArray[np.bool_]
    offsets: NDArray[np.int64]
    ground_table: NDArray[np.int64]
    grounds: NDArray[np.int64]

    def digest(self) -> str:
        """SHA-256 of the model, for the keys of the worlds made with it."""
        found = hashlib.sha256()
        for array in (
            self.features,
            self.pairs,
            self.climate_of,
            self.size,
            self.weights,
            self.shares,
            self.dry,
            self.offsets,
            self.ground_table,
            self.grounds,
        ):
            found.update(repr(array.shape).encode("ascii"))
            found.update(np.ascontiguousarray(array, dtype=np.int64).tobytes())
        return found.hexdigest()


def size_model(
    game_map: Eu5Map, templates: dict[str, dict[str, str]], height: NDArray[np.uint16]
) -> SizeModel:
    """The ``SizeModel`` of the game's own map, read before anything is moved or generated.

    The locations are the passable ones the vote learns from with open climates
    (``assign_biomes``): the Old World and the Americas, without the cultivated land.
    Wastelands are planned on the cells later (``rnw.barrens``); vanilla's are vast and would
    make the land beside them as large. A location is read as the blocks it lies in, the way a
    generated domain is (``watersheds.spacing_grid``), not at its centre, which lies the nearer
    the coast the smaller a coastal location is. ``height`` is the vanilla height at location
    resolution (``DecalStore.world_heights``).
    """
    labels = game_map.labels
    count = len(game_map.keys)
    kinds = np.array([kind in LAND_KINDS for kind in game_map.classes] + [False])
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes] + [False])
    land = kinds[labels]
    grid = climate_grid(sea[labels], height)
    found, features = block_features(land, height, grid)
    rugged = cell_ruggedness(labels, height, count, land)
    rough = cell_roughness(labels, height, count, land)
    del land
    table = np.zeros((found.size, features.shape[1]), dtype=np.int64)
    table[found.ravel()] = features
    pixels, sums = _location_sums(labels, table, (int(found.shape[0]), int(found.shape[1])), count)
    attributes = [templates.get(key, {}) for key in game_map.keys]
    learned, joint = _land_training(game_map, attributes, pixels, open_climate=True)
    kept = [
        slot
        for slot, i in enumerate(learned)
        if pixels[i] > 0 and game_map.classes[i] is CellClass.LAND
    ]
    index = np.array([learned[slot] for slot in kept], dtype=np.int64)
    names, pairs = _vocabulary([joint[slot] for slot in kept])
    _, climate_of = _vocabulary([name.split("|")[0] for name in names])
    old_world = _old_world(game_map)
    old = old_world[index]
    size = np.zeros(index.size, dtype=np.int64)
    for region in (old, ~old):
        rows = np.flatnonzero(region)
        if rows.size:
            values = pixels[index[rows]]
            median = int(np.sort(values)[(rows.size - 1) // 2])
            size[rows] = [octave_parts(value, median) for value in values.tolist()]
    grounds = [attributes[learned[slot]].get("topography", "") for slot in kept]
    # The cells' shares (``assign_biomes``): the Old World's passable land.
    counted = Counter(
        attributes[i].get("topography", "")
        for i, kind in enumerate(game_map.classes)
        if kind is CellClass.LAND and old_world[i]
    )
    centred, points, mean_height = _label_centres(labels, height, count)
    voters = np.array(
        [
            i
            for i, kind in enumerate(game_map.classes)
            if kind is CellClass.LAND
            and old_world[i]
            and centred[i] > 0
            and attributes[i].get("topography", "") in TOPOGRAPHIES
        ],
        dtype=np.int64,
    )
    read = land_features(grid, points[voters], mean_height[voters])
    readings = np.stack(
        [mean_height[voters], rugged[voters], rough[voters], read[:, 1], read[:, 3]], axis=1
    )
    return size_table(
        sums[index] // pixels[index][:, np.newaxis],
        pairs,
        climate_of,
        size,
        topography=np.array(
            [TOPOGRAPHIES.index(name) if name in TOPOGRAPHIES else -1 for name in grounds],
            dtype=np.int64,
        ),
        shares=np.array([counted[name] for name in TOPOGRAPHIES], dtype=np.int64),
        dry=np.array([name.split("|")[1] in NO_WETLANDS for name in names], dtype=bool),
        ground=(
            ground_ranks(readings),
            np.array(
                [TOPOGRAPHIES.index(attributes[i]["topography"]) for i in voters.tolist()],
                dtype=np.int64,
            ),
        ),
    )


def size_table(  # noqa: PLR0913 - the locations, their classes, sizes and grounds.
    features: NDArray[np.int64],
    pairs: NDArray[np.int64],
    climate_of: NDArray[np.int64],
    size: NDArray[np.int64],
    *,
    topography: NDArray[np.int64],
    shares: NDArray[np.int64],
    dry: NDArray[np.bool_],
    ground: tuple[NDArray[np.int64], NDArray[np.int64]],
) -> SizeModel:
    """The ``SizeModel`` of these locations, its votes weighed as the vote reads them.

    The offset of a ground (``topography``, indices of ``TOPOGRAPHIES``) is the mean of its
    locations' sizes less the size their class gives them, each read without itself: the mean
    size of the ``NEIGHBOURS`` nearest other locations of its pair (``class_sizes``). A location
    of a ground no passable cell is given (-1: vanilla's few passable atolls and mountain
    wastelands) still sizes its class but sets no offset. ``ground`` is the vote's table of ranks
    and the grounds of its rows (``SizeModel.ground_table``, ``SizeModel.grounds``).
    """
    train, _ = _standardize(features, features[:0], LAND_WEIGHTS)
    given = np.zeros(size.size, dtype=np.int64)
    for pair in np.unique(pairs).tolist():
        members = np.flatnonzero(pairs == pair)
        k = min(NEIGHBOURS, int(members.size) - 1)
        if k <= 0:
            given[members] = size[members] * PERMILLE // OCTAVE_PARTS
            continue
        for start in range(0, int(members.size), CHUNK):
            nearest = nearest_others(train[members], start, k)
            here = members[start : start + int(nearest.shape[0])]
            given[here] = np.floor_divide(
                size[members][nearest].sum(axis=1) * PERMILLE, OCTAVE_PARTS * k
            )
    off = size * PERMILLE // OCTAVE_PARTS - given
    found = np.bincount(topography[topography >= 0], minlength=len(TOPOGRAPHIES))
    offsets = np.array(
        [
            int(off[topography == kind].sum()) // int(found[kind]) if found[kind] else 0
            for kind in range(len(TOPOGRAPHIES))
        ],
        dtype=np.int64,
    )
    return SizeModel(
        features=features,
        pairs=pairs,
        climate_of=climate_of,
        size=size,
        weights=calibrated_weights(train, pairs, climate_of),
        shares=shares,
        dry=dry,
        offsets=offsets,
        ground_table=ground[0],
        grounds=ground[1],
    )


def _location_sums(
    labels: NDArray[np.int32], table: NDArray[np.int64], shape: tuple[int, int], count: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The pixels of each of ``count`` labels and the sums of ``table`` (one row per ``SIZE_STEP``
    block in raster order, ``shape`` blocks) over them; a label of -1 is none."""
    step = SIZE_STEP
    pixels = np.zeros(count, dtype=np.int64)
    sums = np.zeros((count, table.shape[1]), dtype=np.int64)
    columns = np.arange(int(labels.shape[1]), dtype=np.int64) // step
    for first in range(0, int(labels.shape[0]), step * 8):
        checkpoint()
        window = labels[first : first + step * 8].ravel()
        rows = np.arange(first, first + step * 8, dtype=np.int64)[: labels.shape[0] - first]
        block = (rows[:, np.newaxis] // step * shape[1] + columns[np.newaxis, :]).ravel()
        here = window >= 0
        block, owner = block[here], window[here]
        pixels += np.bincount(owner, minlength=count)
        for column in range(table.shape[1]):
            # Exact: integer sums below 2^53 in a strip.
            found = np.bincount(owner, weights=table[block, column], minlength=count)
            sums[:, column] += found.astype(np.int64)
    return pixels, sums


def class_sizes(
    model: SizeModel, query: NDArray[np.int64], relief: NDArray[np.int64]
) -> NDArray[np.int64]:
    """How large vanilla makes its locations on land like each row of ``query``
    (``block_features``), as log2 over its region's median in thousandths of an octave.

    The row takes the (climate, vegetation) pair the vote would give it with open climates
    (``assign_biomes``, ``regularize_votes`` without smoothing), then the mean size of the
    ``NEIGHBOURS`` nearest vanilla locations of that pair: vanilla sizes its locations by what
    they are, deserts and the cold large and the wet lowlands small, so a size read from the
    neighbours of every class would pull each class towards the median. The row's ground, voted
    from its height, its ``relief`` (``block_relief``: spread and bend), rain and distance to the
    sea among all of ``query`` (``vote_grounds``), moves the size by that ground's offset.
    """
    if model.pairs.size == 0:
        message = "The size model has no land location to learn from"
        raise ValueError(message)
    count = int(model.climate_of.size)
    train, rows = _standardize(model.features, query, LAND_WEIGHTS)
    scores = knn_scores(train, model.pairs, rows, count) * model.weights[np.newaxis, :]
    chosen = chosen_pairs(scores, model.climate_of)
    out = np.zeros(rows.shape[0], dtype=np.int64)
    for pair in np.unique(chosen).tolist():
        members = np.flatnonzero(model.pairs == pair)
        here = np.flatnonzero(chosen == pair)
        totals, k = knn_totals(train[members], model.size[members], rows[here])
        out[here] = np.floor_divide(totals * PERMILLE, OCTAVE_PARTS * k)
    readings = np.stack([query[:, 2], relief[:, 0], relief[:, 1], query[:, 1], query[:, 3]], axis=1)
    ground = vote_grounds(model, readings, model.dry[chosen], model.shares)
    return out + model.offsets[ground]


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
    # The pixels of each cell; the wasteland plan weighs the world's patches by them.
    pixels: NDArray[np.int64] | None = None
    # How rough each cell is, the mean bend of its height (``relief.cell_roughness``), and how
    # broken its ground, whatever its size (``cell_ruggedness``): with the height, rain and the
    # sea they vote its ground (epoch 64, ``epoch.ROUGH_HILLS``, ``vote_grounds``). None: the
    # ground is ranked by height and the cell's own spread (``_topography``).
    roughness: NDArray[np.int64] | None = None
    ruggedness: NDArray[np.int64] | None = None


@dataclass(frozen=True, slots=True)
class CellBiomes:
    """Template attributes per generated cell ("" where a field does not apply)."""

    climate: tuple[str, ...]
    vegetation: tuple[str, ...]
    topography: tuple[str, ...]
    raw_material: tuple[str, ...]
    # The class of each cell when the wasteland plan (``rnw.barrens``) chose it; None: as given.
    kinds: tuple[CellClass, ...] | None = None


@dataclass(frozen=True, slots=True, eq=False)
class VanillaLocations:
    """Per vanilla label: centre and mean height; plus its contact pairs and pixel counts."""

    points: NDArray[np.int64]
    mean_height: NDArray[np.int64]
    pairs: NDArray[np.int64]
    pixels: NDArray[np.int64] | None = None


def vanilla_locations(labels: NDArray[np.int32], height: NDArray[np.uint16]) -> VanillaLocations:
    """Pixel-weighted centre and mean height of every vanilla label."""
    pixels, points, mean_height = _label_centres(labels, height, int(labels.max()) + 1)
    return VanillaLocations(
        points=points,
        mean_height=mean_height,
        pairs=adjacency_pairs(labels, wrap_x=True),
        pixels=pixels,
    )


def _label_centres(
    labels: NDArray[np.int32], height: NDArray[np.uint16], count: int
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """The pixels, pixel-weighted centre (row, column) and mean height of the first ``count``
    labels (no label of -1)."""
    count = max(count, int(labels.max()) + 1)
    width = labels.shape[1]
    sums = np.zeros((4, count), dtype=np.float64)
    for start in range(0, labels.shape[0], 1024):
        checkpoint()
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
    points = np.stack([exact[1] // pixels, exact[2] // pixels], axis=1)
    return exact[0], points, exact[3] // pixels


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
    """Assign topographies in vanilla proportions by relief and wetness ranks (epoch 63 and
    older; epoch 64 votes them, ``vote_grounds``).

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
    return legacy_topography(height, spread)


def _pick(counter: Counter[str], key: int) -> str:
    total = sum(counter.values())
    target = key % total
    for name in sorted(counter):
        target -= counter[name]
        if target < 0:
            return name
    return max(counter)


def _new_world(game_map: Eu5Map) -> NDArray[np.bool_]:
    return np.array([name == NEW_WORLD for name in game_map.continents], dtype=bool)


def _old_world(game_map: Eu5Map) -> NDArray[np.bool_]:
    return np.array(
        [name not in OCEANS and name != NEW_WORLD for name in game_map.continents], dtype=bool
    )


def _land_training(
    game_map: Eu5Map,
    attributes: list[dict[str, str]],
    pixels: NDArray[np.int64] | None,
    open_climate: bool,  # noqa: FBT001 - the vote's own switch, passed through.
) -> tuple[list[int], list[str]]:
    """The vanilla land locations the vote learns from and their "climate|vegetation" pairs.

    The Old World's; with ``open_climate`` also the Americas' locations that have ``pixels``,
    and none of the cultivated land.
    """
    learned = _old_world(game_map)
    if open_climate:
        measured = np.zeros(len(game_map.keys), dtype=bool)
        if pixels is not None:
            known = min(measured.size, pixels.size)
            measured[:known] = pixels[:known] > 0
        learned = learned | (_new_world(game_map) & measured)
    train = [
        i
        for i, kind in enumerate(game_map.classes)
        if kind in LAND_KINDS and learned[i] and "climate" in attributes[i]
        and "vegetation" in attributes[i]
        and not (open_climate and attributes[i]["vegetation"] in CULTIVATED)
    ]  # fmt: skip
    joint = [
        "|".join(
            (
                attributes[i]["climate"],
                EMPTY_LAND.get(attributes[i]["vegetation"], attributes[i]["vegetation"]),
            )
        )
        for i in train
    ]
    return train, joint


def regularize_votes(  # noqa: PLR0913, PLR0917 - the votes, the pairs, the graph and the rounds.
    scores: NDArray[np.int64],
    joint_climate: NDArray[np.int64],
    joint_vegetation: NDArray[np.int64],
    edges: NDArray[np.int64],
    climates: int,
    rounds: tuple[int, int] = (CLIMATE_ROUNDS, VEGETATION_ROUNDS),
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Climate and vegetation of every cell from its smoothed joint (climate, vegetation) votes.

    The climate is the largest of the joint votes smoothed over ``CLIMATE_ROUNDS``, summed per
    climate. The vegetation comes from the same votes smoothed over ``VEGETATION_ROUNDS`` and
    limited to the climate the cell itself took, so a neighbour's vote counts only for a pair
    that the calibration holds in that climate and never for another climate's vegetation. When
    that climate has no vote left in the cell's neighbourhood, the neighbourhood widens by one
    smoothing round at a time, up to the climate's own rounds, in which the climate was
    chosen and so has a vote. A cell with no vote at all is refused, not guessed. ``rounds`` are
    the climate's and the vegetation's rounds (``OPEN_*_ROUNDS`` from epoch 64).
    """
    climate_rounds, vegetation_rounds = rounds
    layers = [scores]
    for _ in range(climate_rounds):
        layers.append(smooth_scores(layers[-1], edges, 1))
    climate_scores = np.zeros((scores.shape[0], climates), dtype=np.int64)
    np.add.at(climate_scores.T, joint_climate, layers[-1].T)
    climate_choice = np.argmax(climate_scores, axis=1)
    allowed = joint_climate[np.newaxis, :] == climate_choice[:, np.newaxis]
    votes = np.zeros_like(scores)
    waiting = np.ones(scores.shape[0], dtype=bool)
    for layer in layers[min(vegetation_rounds, climate_rounds) :]:
        local = np.where(allowed, layer, 0)
        found = waiting & local.any(axis=1)
        votes[found] = local[found]
        waiting &= ~found
    if waiting.any():
        message = f"{int(waiting.sum())} cells have no climate or vegetation vote to classify"
        raise ValueError(message)
    return climate_choice, joint_vegetation[np.argmax(votes, axis=1)]


def _land_columns(
    count: int, land_cells: NDArray[np.int64], query_x: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """Rainfall, distance to the sea and latitude of every cell (zero for water)."""
    columns = [np.zeros(count, dtype=np.int64) for _ in range(3)]
    for column, source in zip(columns, (1, 3, 0), strict=True):
        column[land_cells] = query_x[:, source]
    return columns[0], columns[1], columns[2]


def _topographies(  # noqa: PLR0913 - topography reads the classes, the plan, the vote and the ranks.
    land_cells: NDArray[np.int64],
    cells: Generated,
    plan: WastelandPlan | None,
    *,
    shares: dict[str, int],
    vegetation: list[str],
    rain: NDArray[np.int64],
    coast: NDArray[np.int64],
    ground: SizeModel | None,
) -> list[str]:
    """The topography of every land cell: for the passable ones voted by vanilla's locations
    like them (epoch 64, with ``Generated.ruggedness``; ``vote_grounds``) or ranks of relief,
    the plan's (or the epoch 63 rule's) for the wastelands."""
    topography = [""] * len(cells.kinds)
    plain = [i for i in land_cells.tolist() if cells.kinds[i] is CellClass.LAND]
    ranked: dict[int, str]
    if cells.ruggedness is None:
        ranked = _topography(
            plain,
            shares=shares,
            mean_height=cells.mean_height,
            spread=cells.spread,
            rain=rain,
            coast=coast,
            dry=frozenset(i for i in plain if vegetation[i] in NO_WETLANDS),
        )
    else:
        if ground is None or cells.roughness is None:
            message = "The ground of the land is voted by the game's own locations, not read"
            raise ValueError(message)
        index = np.array(plain, dtype=np.int64)
        readings = np.stack(
            [
                cells.mean_height[index],
                cells.ruggedness[index],
                cells.roughness[index],
                rain[index],
                coast[index],
            ],
            axis=1,
        )
        voted = vote_grounds(
            ground,
            readings,
            np.array([vegetation[i] in NO_WETLANDS for i in plain], dtype=bool),
            np.array([shares[name] for name in TOPOGRAPHIES], dtype=np.int64),
        )
        kinds: list[int] = voted.tolist()
        ranked = {cell: TOPOGRAPHIES[kind] for cell, kind in zip(plain, kinds, strict=True)}
    for cell, name in ranked.items():
        topography[cell] = name
    for cell in land_cells.tolist():
        if cells.kinds[cell] is CellClass.WASTELAND:
            topography[cell] = (
                plan.topography[cell]
                if plan is not None
                else _waste_topography(int(cells.mean_height[cell]), int(cells.spread[cell]))
            )
    return topography


def assign_biomes(  # noqa: PLR0913 - one pass over the calibrated biome model.
    *,
    game_map: Eu5Map,
    templates: dict[str, dict[str, str]],
    vanilla: VanillaLocations,
    vanilla_grid: ClimateGrid,
    final_grid: ClimateGrid,
    cells: Generated,
    seed: int,
    precious_permille: int = 1000,
    resources: ResourceSettings = RESOURCES,
    material_seed: int | None = None,
    wastelands: WastelandSettings | None = None,
    open_climate: bool = False,
    ground: SizeModel | None = None,
) -> tuple[CellBiomes, dict[str, object]]:
    """Template attributes for every generated cell and calibration statistics.

    The raw materials are drawn from ``material_seed`` when given (the resources part of the
    world, ``rnw.layers``), else from ``seed``; everything else is the land's, from ``seed``.
    With ``wastelands`` (epoch 64) the wastelands are planned from the climate and vegetation
    just chosen (``rnw.barrens``) and ``CellBiomes.kinds`` holds the class of every cell; without
    it the cells keep the class they came with, the highest ones being wasteland. With
    ``open_climate`` (epoch 64, ``epoch.OPEN_CLIMATE``) the vote learns from the Americas too,
    without the cultivated land, weighs each pair so that it reads vanilla as it is
    (``calibrated_weights``) and smooths over ``OPEN_*_ROUNDS``. The ground of cells with a
    ``Generated.ruggedness`` (epoch 64) is voted by the vanilla locations of ``ground`` (the
    ``SizeModel`` of the game's map, ``vote_grounds``), which they then require.
    """
    count = len(cells.kinds)
    old = _old_world(game_map)
    attributes = [templates.get(key, {}) for key in game_map.keys]
    land_train, joint = _land_training(game_map, attributes, vanilla.pixels, open_climate)
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
    if open_climate:
        scores = scores * calibrated_weights(train_s, joint_ids, joint_climate)[np.newaxis, :]
    position = np.full(count, -1, dtype=np.int64)
    position[land_cells] = np.arange(land_cells.size)
    edges = _edge_array(cells.edges, land)
    local_edges = position[edges] if edges.size else edges
    climate_choice, vegetation_choice = regularize_votes(
        scores,
        joint_climate,
        joint_vegetation,
        local_edges,
        len(climate_names),
        (OPEN_CLIMATE_ROUNDS, OPEN_VEGETATION_ROUNDS)
        if open_climate
        else (CLIMATE_ROUNDS, VEGETATION_ROUNDS),
    )
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
    rain, coast, latitude = _land_columns(count, land_cells, query_x)
    plan = (
        None
        if wastelands is None
        else _plan_wastelands(
            game_map=game_map,
            attributes=attributes,
            vanilla=vanilla,
            old=old,
            cells=cells,
            fields=(climate, vegetation),
            features=(rain, latitude),
            edges=edges,
            settings=wastelands,
            seed=seed,
        )
    )
    if plan is not None:
        cells = replace(cells, kinds=plan.kinds)
    topography = _topographies(
        land_cells,
        cells,
        plan,
        shares={name: shares[name] for name in TOPOGRAPHIES},
        vegetation=vegetation,
        rain=rain,
        coast=coast,
        ground=ground,
    )
    waters = water_climates(
        game_map,
        templates=templates,
        vanilla=vanilla,
        vanilla_grid=vanilla_grid,
        final_grid=final_grid,
        cells=cells,
    )
    for cell, name in waters.items():
        climate[cell] = name
    raw = _raw_materials(
        game_map,
        attributes=attributes,
        vanilla=vanilla,
        source=_new_world(game_map),
        cells=cells,
        fields=(climate, vegetation, topography),
        seed=seed if material_seed is None else material_seed,
        precious_permille=precious_permille,
        resources=resources,
    )
    result = CellBiomes(
        tuple(climate),
        tuple(vegetation),
        tuple(topography),
        raw,
        kinds=None if plan is None else plan.kinds,
    )
    stats: dict[str, object] = {
        "training_land_locations": len(land_train),
        "climate_classes": climate_names,
        "vegetation_classes": vegetation_names,
        "topography_shares": {name: shares[name] for name in TOPOGRAPHIES},
    }
    if plan is not None:
        stats["wastelands"] = plan.stats
    return result, stats


def water_climates(  # noqa: PLR0913 - the waters read the map, the templates and both grids.
    game_map: Eu5Map,
    *,
    templates: dict[str, dict[str, str]],
    vanilla: VanillaLocations,
    vanilla_grid: ClimateGrid,
    final_grid: ClimateGrid,
    cells: Generated,
) -> dict[int, str]:
    """The climate of every sea and lake cell of ``cells``, by the vanilla waters nearest in
    place and height; empty when ``cells`` has no water or the game has no water template."""
    old = _old_world(game_map)
    attributes = [templates.get(key, {}) for key in game_map.keys]
    water_train = [
        i
        for i, kind in enumerate(game_map.classes)
        if kind in WATER_KINDS and old[i] and "climate" in attributes[i]
    ]
    water_cells = np.array(
        [cell for cell, kind in enumerate(cells.kinds) if kind not in LAND_KINDS], dtype=np.int64
    )
    if not water_train or not water_cells.size:
        return {}
    water_names, water_ids = _vocabulary([attributes[i]["climate"] for i in water_train])
    water_index = np.array(water_train, dtype=np.int64)
    water_s, water_q = _standardize(
        water_features(vanilla_grid, vanilla.points[water_index]),
        water_features(final_grid, cells.points[water_cells]),
        WATER_WEIGHTS,
    )
    water_choice = np.argmax(knn_scores(water_s, water_ids, water_q, len(water_names)), axis=1)
    return {
        cell: water_names[int(water_choice[slot])] for slot, cell in enumerate(water_cells.tolist())
    }


def climate_groups(rules: list[BiomeRule]) -> dict[str, str]:
    """The climates that ``biomes.txt`` draws alike, each named for the first of its group."""
    groups: dict[str, str] = {}
    for rule in rules:
        if rule.climate:
            first = min(rule.climate)
            for name in sorted(rule.climate):
                _ = groups.setdefault(name, first)
    return groups


def wasteland_settings(
    rules: list[BiomeRule],
    materials: dict[str, int],
    *,
    budget: int,
    polar: NDArray[np.bool_],
    barrier: NDArray[np.bool_],
) -> WastelandSettings:
    """What the wasteland plan needs of the game: the climate groups and a test that a
    (climate, vegetation, topography) is drawn by a biome of its own with materials, not by
    ``default_biome``."""
    known: dict[tuple[str, str, str], bool] = {}

    def biome_ok(climate: str, vegetation: str, topography: str) -> bool:
        key = (climate, vegetation, topography)
        if key not in known:
            biome = biome_of(rules, climate, vegetation, topography)
            known[key] = bool(biome) and biome != DEFAULT_BIOME and materials.get(biome, 0) > 0
        return known[key]

    return WastelandSettings(budget, polar, barrier, climate_groups(rules), biome_ok)


def _plan_wastelands(  # noqa: PLR0913 - the plan reads the map, the world and the vote.
    *,
    game_map: Eu5Map,
    attributes: list[dict[str, str]],
    vanilla: VanillaLocations,
    old: NDArray[np.bool_],
    cells: Generated,
    fields: tuple[list[str], list[str]],
    features: tuple[NDArray[np.int64], NDArray[np.int64]],
    edges: NDArray[np.int64],
    settings: WastelandSettings,
    seed: int,
) -> WastelandPlan:
    """The wasteland plan of ``rnw.barrens`` for the cells and the climate and vegetation chosen."""
    if vanilla.pixels is None or cells.pixels is None:
        message = "The wasteland plan needs the pixel counts of the vanilla and generated cells"
        raise ValueError(message)
    pixels = np.zeros(len(game_map.keys), dtype=np.int64)
    known = min(pixels.size, vanilla.pixels.size)
    pixels[:known] = vanilla.pixels[:known]
    calibration = calibrate(
        classes=game_map.classes,
        climate=[row.get("climate", "") for row in attributes],
        vegetation=[row.get("vegetation", "") for row in attributes],
        topography=[row.get("topography", "") for row in attributes],
        coastal=_vanilla_coastal(game_map, vanilla.pairs),
        pixels=pixels,
        include=old,
        groups=settings.groups,
    )
    climate, vegetation = fields
    rain, latitude = features
    terrain = Terrain(
        kinds=cells.kinds,
        climate=tuple(climate),
        vegetation=tuple(vegetation),
        height=cells.mean_height,
        spread=cells.spread,
        pixels=cells.pixels,
        rain=rain,
        latitude=latitude,
        coastal=cells.coastal,
        polar=settings.polar,
        barrier=settings.barrier,
        edges=edges,
    )
    return plan_wastelands(terrain, calibration, settings, seed=seed)


def _vanilla_coastal(game_map: Eu5Map, pairs: NDArray[np.int64]) -> NDArray[np.bool_]:
    """Which vanilla locations touch a sea zone (a contact in ``pairs`` is low << 32 | high)."""
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    low = pairs >> np.int64(32)
    high = pairs & np.int64((1 << 32) - 1)
    coastal = np.zeros(len(game_map.keys), dtype=bool)
    coastal[low[sea[high]]] = True
    coastal[high[sea[low]]] = True
    return coastal


def _raw_materials(  # noqa: PLR0913 - raw materials depend on every template field.
    game_map: Eu5Map,
    *,
    attributes: list[dict[str, str]],
    vanilla: VanillaLocations,
    source: NDArray[np.bool_],
    cells: Generated,
    fields: tuple[list[str], list[str], list[str]],
    seed: int,
    precious_permille: int = 1000,
    resources: ResourceSettings = RESOURCES,
) -> tuple[str, ...]:
    """Draw each land cell's raw material from vanilla frequencies of similar locations.

    The frequencies are those of the vanilla New World (``source``): drawing them from the
    Old World gave a generated America elephants, horses, wheat, rice, silk and tea and none
    of its maize, potatoes, cocoa, tobacco or chili (C116). Similar means the same climate,
    vegetation, topography and coast, falling back to fewer of them. ``precious_permille``
    weighs gold, silver, gems and pearls against the rest (1000: their vanilla share); a
    class whose only materials it removes falls back to a coarser class. Ordinary materials
    use their individual ``resources`` weights. No new material is introduced into a class;
    if even its coastal/inland pool is empty, generation fails explicitly.
    """
    coastal = _vanilla_coastal(game_map, vanilla.pairs)
    tables: list[dict[tuple[str, ...], Counter[str]]] = [{}, {}, {}, {}]
    for i, kind in enumerate(game_map.classes):
        if kind is not CellClass.LAND or not source[i] or "raw_material" not in attributes[i]:
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
    tables = [
        {key: _weighted(counter, precious_permille, resources) for key, counter in table.items()}
        for table in tables
    ]
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
            (table[key] for table, key in zip(tables, keys, strict=True) if table.get(key)),
            None,
        )
        if counter is None:
            message = f"No enabled raw materials for {flag} locations; increase resource weights"
            raise SettingsError(message)
        out.append(_pick(counter, hash_point(stream, cell, 0)))
    return tuple(out)


def _weighted(
    counter: Counter[str], precious_permille: int, resources: ResourceSettings = RESOURCES
) -> Counter[str]:
    """Scale placement frequencies, keeping the original counts at vanilla defaults."""
    if precious_permille == PERMILLE and resources == RESOURCES:
        return counter
    weighted = Counter(
        {
            name: count
            * (precious_permille if name in PRECIOUS else getattr(resources, name, PERMILLE))
            for name, count in counter.items()
        }
    )
    return +weighted


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
