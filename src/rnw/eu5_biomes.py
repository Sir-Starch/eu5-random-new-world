"""Climate, vegetation, topography and raw materials for generated EU5 locations.

EU5 1.4.1 renders each location with the biome that its template's climate, vegetation
and topography select in ``gfx/map/biome_definitions/biomes.txt`` [V-LOCAL C50], so a
coherent look needs coherent templates. Each generated location gets physical features
from the same model that is applied to the vanilla map: absolute latitude, mean height,
distance to the sea and zonal-wind rainfall (``climate.py``). An integer
k-nearest-neighbour vote over Old World locations calibrates climate and vegetation as joint
(climate, vegetation) pairs; the votes are then smoothed over the location adjacency graph so
zones are contiguous, and a cell's vegetation is chosen among the pairs of its own climate.
Topography comes from relief ranks with vanilla shares, from epoch 64 from a vote of vanilla's
locations alike in height, relief and distance to the sea (``vote_grounds``); raw materials are
drawn from vanilla frequencies. The New World starts empty, so farmland is learned as grassland;
from epoch 64 the vote leaves farmland out and learns from the vanilla Americas as well
(``OPEN_CLIMATE``).
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
from fractions import Fraction
from functools import partial
from itertools import pairwise
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.barrens import (
    FLAT_SPREAD,
    GROUND_KINDS,
    MOUNTAIN_FLOOR,
    Terrain,
    WastelandPlan,
    WastelandSettings,
    calibrate,
    legacy_topography,
    plan_wastelands,
)
from rnw.climate import RainSettings, SeasonalSettings, rainfall, seasonal_rainfall
from rnw.eu5_canvas import NEW_WORLD, OCEANS
from rnw.fields import block_mean
from rnw.model import CellClass
from rnw.parallel import worker_count
from rnw.progress import checkpoint
from rnw.relief import HILL_STEP, blurred_window, cell_roughness, strip_bend
from rnw.rng import derive_seed, hash_point
from rnw.settings import RESOURCES, ResourceSettings, SettingsError
from rnw.timing import measured
from rnw.topology import adjacency_pairs, distance_from

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

PERMILLE: Final[int] = 1000
# Materials whose weight the precious setting scales.
PRECIOUS: Final[frozenset[str]] = frozenset({"goods_gold", "silver", "gems", "pearls"})
# Epoch 64 (``epoch.POOLED_RESOURCES``): a class of raw materials counts its broader class as
# ``RESOURCE_PRIOR`` locations more (``_pooled``). Of the vanilla New World's 282 classes 137 have
# five locations or fewer, and taking such a class whole left subtropical jungle and arid desert
# flatland without food and gave 45 vanilla locations' classes none. Leaving each vanilla New World
# location out in turn, the old rule gave 816 of 4,434 no chance of their own material and pooling
# 2; 32 scores best by Brier score (0.818 against 0.857), 64 by log-likelihood (-2.41 against
# -2.44; the old rule -3.21) [V-EXEC 2026-11-15].
RESOURCE_PRIOR: Final[int] = 32
POOL_SCALE: Final[int] = 1 << 20  # shares of a class, far below the 64-bit key of ``_pick``
FACTOR_ONE: Final[int] = 1 << 16  # a material's calibrated weight 1 (``_material_factors``)
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
# Epoch 64 (``epoch.OPEN_CLIMATE``): the rain of each season (``climate.seasonal_rainfall``), its
# belts moved by 7 degrees. Latitudes in tenths of a degree of the season's effective latitude.
SEASONAL: Final[SeasonalSettings] = SeasonalSettings(
    shift=70,
    decay_px=120,
    recharge_px=30,
    lift_units=6000,
    blur_px=12,
    relief_blur_px=8,
    current_px=120,
    capacity=((0, 1000), (200, 1000), (400, 650), (600, 350), (800, 120)),
    efficiency=(
        (0, 1000), (80, 1000), (130, 700), (180, 300), (220, 150), (300, 150), (360, 500),
        (420, 900), (600, 900), (700, 600), (850, 300),
    ),
    easterly=((0, 700), (250, 700), (330, 0), (620, 0), (700, 600)),
    westerly=((0, 0), (250, 0), (330, 1000), (620, 1000), (700, 400)),
    summer_inflow=((0, 300), (80, 600), (300, 600), (400, 300), (550, 0)),
    winter_inflow=((0, 300), (80, 100), (300, 100), (400, 150), (550, 0)),
    cold_current=((0, 1000), (80, 1000), (150, 450), (380, 450), (450, 1000)),
    warm_current=((0, 1000), (150, 1150), (400, 1150), (500, 1000)),
)  # fmt: skip
SEA_HEIGHT: Final[int] = 5700
COAST_LIMIT: Final[int] = 160
NEIGHBOURS: Final[int] = 32
CHUNK: Final[int] = 128
# Feature weights in tenths: latitude, rainfall, height, distance to sea; with the seasons
# (``ClimateGrid.winter``) the rainfall is the summer's and the winter's follows at the end.
LAND_WEIGHTS: Final[tuple[int, ...]] = (50, 30, 25, 10)
WINTER_WEIGHT: Final[int] = 30
RAIN_ROOT_SHIFT: Final[int] = 32  # the features read the fourth root of rain << 32
RAIN_ROOT_CAP: Final[int] = (1 << 19) - 1  # keeps rain << 32 below 2^51, where sqrt is exact
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
# (1.7 % semi-arid and cold arid land against vanilla's 9.3 %) [V-EXEC 2026-11-13]. Unsmoothed,
# the vote speckled the land instead: 51 passable locations in a thousand had a climate none of
# their neighbours shared (vanilla's Old World 13, the Americas 30) and a climate region held 9.3
# locations (26 and 13). One round, its weights matched to the world through the smoothing
# (``matched_weights``, ``smoothed_pairs``), leaves 13 in a thousand and 20 cells a region and
# keeps every climate's share: semi-arid, cold arid and Mediterranean land 203 cells in a
# thousand where the neighbours hold 196 (unsmoothed 199) [V-EXEC 2026-11-15, four worlds].
CULTIVATED: Final[frozenset[str]] = frozenset({"farmland"})
OPEN_CLIMATE_ROUNDS: Final[int] = 1
OPEN_VEGETATION_ROUNDS: Final[int] = 1
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
# Weights calibrated on vanilla make the vote read vanilla's own land as it is, but a world's land
# is spread otherwise over the readings, and there a plurality again gives a class its neighbours
# hold in part fewer rows than they hold of it: on world seed 42 the vote gave 31 permille of
# wetlands and 213 of hills where the neighbours of its locations hold 39 and 235, and mountains
# 151 for 134; its climates, subtropical 91 for 122. From epoch 64 the weights are matched to each
# world's own land (``matched_weights``): the same rounds, towards the rows that the neighbours of
# its locations hold of each class (their rank-weighted votes per row, in ``SOFT_SCALE``ths of a
# row), so that the world has as much of a class as land like its own holds [V-EXEC 2026-11-14].
SOFT_SCALE: Final[int] = 1000
CALIBRATION_THREADS: Final[int] = 8  # each searches the neighbours of its own CHUNK rows
WEIGHT_TOP: Final[int] = 1 << 20
# Seeds are spaced by the size vanilla gives a location of the class the vote will choose
# (epoch 64, ``epoch.RIVERS_FIRST``, ``SizeModel``); sizes are log2 of a location's pixels over
# its region's median in ``OCTAVE_PARTS``ths of an octave. A class sizes a location by the
# vanilla locations of its pair nearest in latitude and the seasons' rain (``SIZE_COLUMNS``):
# read by height and distance to the sea as well, the size of a cell followed its own extent
# (a small coastal cell reads the coast and was sized as a coastal one) and could not tell hills
# from plateaus of one height. The ground and the coast then move it by how far vanilla's
# mainland locations of that ground and coast lie off that size, read against the flatland of
# their pair beside them (``SizeModel.offsets``, ``_local_offsets``). Their mean offsets mix in
# their regions: mountains -0.16 of an octave inland and +0.11 on the coast, for the land of a
# mountain region is all subdivided alike, which made the mountain cells 0.16 smaller inland
# and larger on the coast than the plain beside them (vanilla -0.09 to -0.02 and -0.05 to +0.04).
# Read against their neighbours, mountains lie 0.07 under the flatland inland and on the coast,
# hills 0.06 and 0.03 over it, wetlands as large and coastal flatland 0.11 under the inland's
# [V-EXEC 2026-11-15]. The locations of landmasses of fewer than ``MAINLAND`` locations lie 0.5
# to 1.7 octaves below their pair, as large as their islands allow, so they size no class
# [V-EXEC 2026-11-15].
SIZE_COLUMNS: Final[tuple[int, ...]] = (0, 1, 4)  # latitude, summer and winter rain
MAINLAND: Final[int] = 100
RELIEF_ROWS: Final[int] = 512  # rows of a strip read for the relief of the size blocks
# Epoch 64 (``epoch.ROUGH_HILLS``): the ground of the land is voted, as its climate is, by the
# ``NEIGHBOURS`` most like it of vanilla's Old World land, a ``GROUND_STEP`` block at a time
# (``ground_field``; a vanilla block has the ground of the location holding most of it), in
# ``GROUND_COLUMNS`` readings: mean height, ruggedness (``cell_ruggedness``), roughness
# (``relief.cell_roughness``) and distance to the sea, the relief blurred over the land by
# ``GROUND_BLUR`` pixels first, for vanilla's decals have twice the fine bend of the generated
# relief and the blurred readings of the two compare (lowland bend 88 against 61 to 74). The
# readings are taken as they are, scaled by vanilla's spread (``GROUND_WEIGHTS``), and each
# ground's votes weigh what makes vanilla read as it is (``calibrated_weights``), so a world has
# as much of each ground as its land holds, not the Old World's shares. A cell sums the votes of
# the land it covers (``cell_ground_scores``). Read on vanilla, each block voted by the blocks of
# the other locations, the summed votes name the ground of 704 Old World locations in a thousand
# and 43 % of their wetlands [V-EXEC 2026-11-15]. The rainfall adds nothing (voted by location,
# the Americas named 640 with it against 660) and is left out [V-EXEC 2026-11-14].
GROUND_COLUMNS: Final[int] = 4
GROUND_BLUR: Final[int] = 8
GROUND_WEIGHTS: Final[tuple[int, ...]] = (30, 30, 30, 15)
GROUND_STEP: Final[int] = 16  # pixels per block of the ground field (``ground_field``)
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
    # The winter's share of ``rain`` (epoch 64, ``seasonal_rainfall``); None: the yearly zonal
    # rain alone.
    winter: NDArray[np.int64] | None = None


def land_weights(columns: int) -> tuple[int, ...]:
    """The weights of ``land_features`` with ``columns`` columns."""
    return LAND_WEIGHTS if columns == len(LAND_WEIGHTS) else (*LAND_WEIGHTS, WINTER_WEIGHT)


def rain_root(values: NDArray[np.int64]) -> NDArray[np.int64]:
    """The fourth root of ``values << RAIN_ROOT_SHIFT``, rounded down (exact: the float square
    roots of integers below 2^51 round down to the integer roots). Rain's long tail of wet
    coasts would otherwise squeeze the dry land together in the vote."""
    shifted = np.clip(values, 0, RAIN_ROOT_CAP).astype(np.float64) * float(1 << RAIN_ROOT_SHIFT)
    return np.floor(np.sqrt(np.floor(np.sqrt(shifted)))).astype(np.int64)


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


def climate_grid(
    sea: NDArray[np.bool_], height: NDArray[np.integer], *, seasonal: bool = False
) -> ClimateGrid:
    """Rainfall, distance to the sea (land) and distance to land (water), in pixels; with
    ``seasonal`` (epoch 64) the rain of the summer and the winter (``seasonal_rainfall``)."""
    step = CLIMATE_STEP
    share, mean = _block_means(sea, height, CLIMATE_STRIP)
    sea_grid = share >= 500  # noqa: PLR2004 - half
    height_grid = np.maximum(mean, SEA_HEIGHT)
    del share, mean
    rows = np.arange(sea_grid.shape[0], dtype=np.int64) * step + step // 2
    winter = None
    if seasonal:
        summer, winter = seasonal_rainfall(
            sea_grid, height_grid, latitude_tenths(rows), EQUATOR_ROW // step, SEASONAL
        )
        rain = summer + winter
        del summer
    else:
        rain = rainfall(sea_grid, height_grid, latitude_tenths(rows), RAIN)
    coast = distance_from(sea_grid, COAST_LIMIT, octagonal=True).astype(np.int64) * step
    shore = distance_from(~sea_grid, COAST_LIMIT, octagonal=True).astype(np.int64) * step
    return ClimateGrid(rain=rain, coast=coast, shore=shore, winter=winter)


def _sample(grid: NDArray[np.int64], points: NDArray[np.int64]) -> NDArray[np.int64]:
    rows = np.clip(points[:, 0] // CLIMATE_STEP, 0, grid.shape[0] - 1)
    columns = np.clip(points[:, 1] // CLIMATE_STEP, 0, grid.shape[1] - 1)
    return grid[rows, columns]


def land_features(
    grid: ClimateGrid, points: NDArray[np.int64], mean_height: NDArray[np.int64]
) -> NDArray[np.int64]:
    """Latitude, rainfall, mean height and distance to the sea per location; with the seasons
    the rainfall is the ``rain_root`` of the summer's and that of the winter's follows.

    Height spread is left out: vanilla decals carry far more fine relief than the
    location-scale relief field, so the two would not be comparable.
    """
    rain = _sample(grid.rain, points)
    columns = [latitude_tenths(points[:, 0]), rain, mean_height, _sample(grid.coast, points)]
    if grid.winter is not None:
        winter = _sample(grid.winter, points)
        columns[1] = rain_root(rain - winter)
        columns.append(rain_root(winter))
    return np.stack(columns, axis=1)


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
    """The ``k`` nearest training rows of each row of ``block``, nearest first (ties by index,
    but which of the rows as far as the ``k``-th it keeps is the partition's).

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


def smoothed_pairs(
    scores: NDArray[np.int64],
    climate_of: NDArray[np.int64],
    *,
    edges: NDArray[np.int64],
    rounds: int,
) -> NDArray[np.int64]:
    """The pair each row of ``scores`` chooses after ``rounds`` of ``smooth_scores`` over
    ``edges`` (pairs of rows): ``chosen_pairs`` of the smoothed scores, which is what
    ``regularize_votes`` gives with as many climate and vegetation rounds."""
    smoothed = smooth_scores(scores, edges, rounds) if rounds else scores
    return chosen_pairs(smoothed, climate_of)


def _rescaled(weights: NDArray[np.int64]) -> NDArray[np.int64]:
    top = int(weights.max()) if weights.size else 0
    if top <= 0:
        return weights
    return np.where(weights > 0, np.maximum(1, weights * WEIGHT_TOP // top), 0)


def matched_weights(
    scores: NDArray[np.int64],
    weights: NDArray[np.int64],
    choose: Callable[[NDArray[np.int64]], NDArray[np.int64]],
) -> NDArray[np.int64]:
    """``weights`` matched to the rows of ``scores`` (unweighed ``knn_scores``): over
    ``CALIBRATION_ROUNDS`` rounds the weight of a class is multiplied by the square root of the
    rows its neighbours hold (each row's votes over their sum, in ``SOFT_SCALE``ths) over the rows
    ``choose`` gives it from the weighed scores, and rescaled to ``WEIGHT_TOP``. A class that
    weighs nothing stays so. Integers."""
    count = int(weights.size)
    weights = _rescaled(weights)
    total = np.maximum(scores.sum(axis=1, keepdims=True), 1)
    held: list[int] = (scores * SOFT_SCALE // total).sum(axis=0).tolist()
    for _ in range(CALIBRATION_ROUNDS):
        found: list[int] = np.bincount(
            choose(scores * weights[np.newaxis, :]), minlength=count
        ).tolist()
        weights = _rescaled(
            np.array(
                [
                    math.isqrt(weight * weight * (rows + SOFT_SCALE) // ((chosen + 1) * SOFT_SCALE))
                    if weight
                    else 0
                    for weight, rows, chosen in zip(weights.tolist(), held, found, strict=True)
                ],
                dtype=np.int64,
            )
        )
    return weights


def nearest_others(train: NDArray[np.int64], start: int, k: int) -> NDArray[np.int64]:
    """The ``k`` nearest rows of ``train`` to each of its ``CHUNK`` rows from ``start``, the row
    itself left out (nearest first, ties by index)."""
    size = min(CHUNK, int(train.shape[0]) - start)
    nearest = _nearest(train, train[start : start + size], k + 1)
    own = nearest == np.arange(start, start + size, dtype=np.int64)[:, np.newaxis]
    # A row behind k + 1 identical rows is not among its own nearest; it drops the last.
    own[~own.any(axis=1), -1] = True
    return nearest[~own].reshape(size, k)


def _scores_by_chunks(
    train: NDArray[np.int64], classes: NDArray[np.int64], count: int, k: int
) -> NDArray[np.int64]:
    """The rank-weighted votes of each row's ``k`` nearest other rows (``nearest_others``), a
    ``CHUNK`` of rows per thread."""
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
    return scores


def _scores_without_self(
    train: NDArray[np.int64], classes: NDArray[np.int64], count: int, k: int
) -> NDArray[np.int64]:
    """The rank-weighted votes of each row's ``k`` nearest other rows, taken as
    ``nearest_others`` takes them from ``nearest_rows``."""
    size = int(train.shape[0])
    nearest = nearest_rows(train, train, k + 1)
    own = nearest == np.arange(size, dtype=np.int64)[:, np.newaxis]
    own[~own.any(axis=1), -1] = True
    nearest = nearest[~own].reshape(size, k)
    checkpoint()
    scores = np.zeros((size, count), dtype=np.int64)
    np.add.at(
        scores,
        (np.repeat(np.arange(size, dtype=np.int64), k), classes[nearest].ravel()),
        np.tile(np.arange(k, 0, -1, dtype=np.int64), size),
    )
    return scores


def nearest_rows(train: NDArray[np.int64], query: NDArray[np.int64], k: int) -> NDArray[np.int64]:
    """The ``k`` nearest rows of ``train`` to each row of ``query``, nearest first, ties by index
    (also those ``_nearest`` leaves to its partition at the ``k``-th row), all the rows at once,
    by the native k-d tree (ADR 0005)."""
    return _native.nearest_rows(
        np.ascontiguousarray(train, dtype=np.int64), np.ascontiguousarray(query, dtype=np.int64), k
    )


@measured
def calibrated_weights(
    train: NDArray[np.int64],
    classes: NDArray[np.int64],
    climate_of: NDArray[np.int64],
    *,
    exact_ties: bool = False,
) -> NDArray[np.int64]:
    """The weight of each pair's votes with which the vote reads the training rows as they are.

    Each row of ``train`` (standardized) is voted on by its ``NEIGHBOURS`` nearest other rows
    (``nearest_others``; with ``exact_ties``, as the ground model of epoch 64 is made,
    ``nearest_rows``); over ``CALIBRATION_ROUNDS`` rounds from ``prior_weights`` the weight of a
    pair is multiplied by the square root of the rows that hold it over the rows it is chosen for,
    so that every pair is chosen about as often as vanilla holds it. A pair without rows weighs
    nothing.
    """
    count = int(climate_of.size)
    weights = _rescaled(prior_weights(classes, count))
    k = min(NEIGHBOURS, int(train.shape[0]) - 1)
    if k <= 0:
        return weights
    held = np.bincount(classes, minlength=count).tolist()
    scores = (
        _scores_without_self(train, classes, count, k)
        if exact_ties
        else _scores_by_chunks(train, classes, count, k)
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


@measured
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
    winter = None
    if grid.winter is not None:
        winter = block_mean(grid.winter * weight * cells, ratio)[: shape[0], : shape[1]] // weights
        rain = rain_root(rain - winter)
        winter = rain_root(winter)
    found = count > 0
    centres = np.arange(shape[0], dtype=np.int64) * step + step // 2
    latitude = np.broadcast_to(latitude_tenths(centres)[:, np.newaxis], shape)
    columns = [latitude[found], rain[found], (total // np.maximum(count, 1))[found], coast[found]]
    if winter is not None:
        columns.append(winter[found])
    return found, np.stack(columns, axis=1)


def block_relief(
    land: NDArray[np.bool_],
    height: NDArray[np.integer],
    found: NDArray[np.bool_],
    *,
    blur: int = 0,
    rough: bool = True,
) -> NDArray[np.int64]:
    """The spread and the bend of the height of the land of each ``found`` ``SIZE_STEP`` block,
    in raster order (``block_features``): the standard deviation of its height and the mean of
    ``relief.strip_bend``, which ``_topography`` ranks as it ranks the cells' (integers). With
    ``blur`` the height is first blurred over the land (``relief.land_blur``)."""
    step = SIZE_STEP
    rows = int(land.shape[0])
    blocks = int(found.size)
    totals = np.zeros((5, blocks), dtype=np.int64)
    for start in range(0, rows, RELIEF_ROWS):
        checkpoint()
        stop = min(rows, start + RELIEF_ROWS)
        low, high = max(0, start - HILL_STEP), min(rows, stop + HILL_STEP)
        window = (
            height[low:high].astype(np.int64)
            if not blur
            else blurred_window(land, height, low, high, blur)
        )
        bend = strip_bend(land[low:high], window, start, stop, rows) if rough else None
        totals += _native.block_relief(
            np.ascontiguousarray(land[start:stop]),
            np.ascontiguousarray(window[start - low : stop - low]),
            bend,
            blocks,
            step,
            start,
        )
    count, total, square, bent, read = totals
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
    *,
    blur: int = 0,
) -> NDArray[np.int64]:
    """How broken the ground of each of the first ``count`` cells (the land cells) is: the mean,
    over its pixels, of the spread of the height of the land of the ``SIZE_STEP`` block each
    lies in (``block_relief``). A cell's own spread grows with the cell, as the variance of a
    fractal relief grows with the area read, so ranked by it the largest cells became mountains
    and the smallest plateaus; this reads every cell at the same scale, as the size model reads
    its blocks. ``land`` marks the land pixels when the land cells are not simply the first
    ``count`` labels (vanilla's map, ``size_model``); ``blur`` blurs the height over the land
    first (``relief.land_blur``). Integers."""
    rows, columns = (int(size) for size in labels.shape)
    step = SIZE_STEP
    shape = (-(-rows // step), -(-columns // step))
    on_land = (labels >= 0) & (labels < count) if land is None else land
    relief = block_relief(on_land, elevation, np.ones(shape, dtype=bool), blur=blur, rough=False)
    del on_land
    cells = max(count, int(labels.max()) + 1)
    pixels, sums = _location_sums(labels, relief[:, :1], shape, cells)
    return sums[:count, 0] // np.maximum(pixels[:count], 1)


def cell_mean(
    labels: NDArray[np.int32], values: NDArray[np.integer], count: int
) -> NDArray[np.int64]:
    """The mean of ``values`` over the pixels of each of the first ``count`` cells, a strip of
    ``RELIEF_ROWS`` rows at a time (exact: a strip's sums stay below 2^53). Integers."""
    totals = np.zeros((4, count), dtype=np.int64)
    for start in range(0, int(labels.shape[0]), RELIEF_ROWS):
        checkpoint()
        totals += _native.label_moments(
            np.ascontiguousarray(labels[start : start + RELIEF_ROWS]),
            np.ascontiguousarray(values[start : start + RELIEF_ROWS], dtype=np.int64),
            count,
            start,
        )
    return totals[3] // np.maximum(totals[0], 1)


def ground_scores(model: SizeModel, readings: NDArray[np.int64]) -> NDArray[np.int64]:
    """The votes for each ground of the ``NEIGHBOURS`` vanilla blocks (``SizeModel.ground_table``)
    nearest each row of ``readings`` in ``GROUND_COLUMNS`` (mean height, ruggedness, roughness,
    distance to the sea), scaled as vanilla's (``GROUND_WEIGHTS``), rank-weighted as
    ``knn_scores`` weighs them (``nearest_rows``)."""
    if model.grounds.size == 0:
        message = "The size model has no ground to learn from"
        raise ValueError(message)
    train, rows = _standardize(model.ground_table, readings, GROUND_WEIGHTS)
    k = min(NEIGHBOURS, int(train.shape[0]))
    size = int(rows.shape[0])
    nearest = nearest_rows(train, rows, k)
    checkpoint()
    scores = np.zeros((size, len(TOPOGRAPHIES)), dtype=np.int64)
    np.add.at(
        scores,
        (np.repeat(np.arange(size, dtype=np.int64), k), model.grounds[nearest].ravel()),
        np.tile(np.arange(k, 0, -1, dtype=np.int64), size),
    )
    return scores


def choose_grounds(
    model: SizeModel,
    scores: NDArray[np.int64],
    dry: NDArray[np.bool_],
    *,
    matched: bool = False,
) -> NDArray[np.int64]:
    """The ground (an index of ``TOPOGRAPHIES``) of each row of ``scores`` (``ground_scores``, or
    their sums over a cell's land, ``cell_ground_scores``), each ground's votes weighed by
    ``SizeModel.ground_weights``, ``matched`` to these rows (``matched_weights``); a ``dry`` row is
    never wetland and its wetland votes count for no ground. Ties go to the earlier ground."""
    wet = TOPOGRAPHIES.index("wetlands")
    scores = scores.copy()
    scores[dry, wet] = 0

    def choose(weighed: NDArray[np.int64]) -> NDArray[np.int64]:
        weighed[dry, wet] = -1
        return np.argmax(weighed, axis=1).astype(np.int64)

    weights = model.ground_weights
    if matched:
        weights = matched_weights(scores, weights, choose)
    return choose(scores * weights[np.newaxis, :])


def vote_grounds(
    model: SizeModel,
    query: NDArray[np.int64],
    dry: NDArray[np.bool_],
    *,
    matched: bool = False,
) -> NDArray[np.int64]:
    """The ground of each row of ``query`` (``GROUND_COLUMNS`` readings), voted by the nearest
    vanilla blocks (``ground_scores``, ``choose_grounds``)."""
    return choose_grounds(model, ground_scores(model, query), dry, matched=matched)


@dataclass(frozen=True, slots=True, eq=False)
class GroundField:
    """The ground votes of a land (``ground_field``): one row of ``ground_scores`` per
    ``GROUND_STEP`` block in raster order (``shape`` blocks), zero where a block holds no land,
    and the land pixels of each block."""

    shape: tuple[int, int]
    scores: NDArray[np.int64]
    pixels: NDArray[np.int64]


def _block_raster(land: NDArray[np.bool_]) -> tuple[NDArray[np.int32], NDArray[np.int64]]:
    """The ``GROUND_STEP`` block (raster order) of each pixel of ``land`` (-1 elsewhere) and the
    land pixels of every block, a strip of ``RELIEF_ROWS`` rows at a time."""
    checkpoint()
    out = _native.block_labels(np.ascontiguousarray(land), GROUND_STEP)
    checkpoint()
    return out


@measured
def _ground_readings(  # noqa: PLR0913 - the blocks, the height, the grid and how to read them.
    blocks: NDArray[np.int32],
    count: int,
    height: NDArray[np.integer],
    grid: ClimateGrid,
    *,
    land: NDArray[np.bool_] | None,
    columns: Callable[[NDArray[np.int64]], NDArray[np.int64]] | None,
) -> NDArray[np.int64]:
    """The ``GROUND_COLUMNS`` readings of each of the ``count`` blocks of ``blocks``
    (``_block_raster``): the mean height of its land, its ruggedness and roughness
    (``cell_ruggedness``, ``relief.cell_roughness``, the height blurred by ``GROUND_BLUR``; the
    relief read over ``land`` when given) and the distance to the sea at its land's centre, whose
    column ``columns`` takes to ``grid``'s when the blocks lie elsewhere on the map."""
    mean_height = cell_mean(blocks, height, count)
    rugged = cell_ruggedness(blocks, height, count, land, blur=GROUND_BLUR)
    rough = cell_roughness(blocks, height, count, land, blur=GROUND_BLUR)
    centres = _cell_centres(blocks, count)
    if columns is not None:
        centres[:, 1] = columns(centres[:, 1])
    return np.stack([mean_height, rugged, rough, _sample(grid.coast, centres)], axis=1)


@measured
def ground_field(
    model: SizeModel,
    land: NDArray[np.bool_],
    height: NDArray[np.integer],
    grid: ClimateGrid,
    *,
    columns: Callable[[NDArray[np.int64]], NDArray[np.int64]] | None = None,
) -> GroundField:
    """The ground votes of every ``GROUND_STEP`` block of ``land`` (``ground_scores`` of its
    ``_ground_readings`` on ``height`` and ``grid``).

    The ground is a property of the land a cell covers, as vanilla's is of its regions, not of
    the cell's own extent: read at a cell's centre, the distance to the sea grows with the cell
    (rank correlation +0.58 among vanilla's coastal Old World locations of one ground), so the
    vote made the smallest coastal cells wetland and those reaching inland hills. Voted on
    vanilla's own locations, each without itself, its coastal wetlands came out 0.27 of an
    octave smaller than vanilla's within their pair and its coastal hills 0.14 larger; voted by
    blocks of a fixed footprint (each block without those of its own location) and summed over
    each location, 0.08 smaller and 0.03 larger, naming the ground of 704 locations in a
    thousand (by location 711) and 43 % of the wetlands (33 %) [V-EXEC 2026-11-15].
    """
    blocks, pixels = _block_raster(land)
    count = int(pixels.size)
    readings = _ground_readings(blocks, count, height, grid, land=None, columns=columns)
    del blocks
    found = np.flatnonzero(pixels)
    scores = np.zeros((count, len(TOPOGRAPHIES)), dtype=np.int64)
    scores[found] = ground_scores(model, readings[found])
    rows, width = (int(size) for size in land.shape)
    shape = (-(-rows // GROUND_STEP), -(-width // GROUND_STEP))
    return GroundField(shape=shape, scores=scores, pixels=pixels)


def cell_ground_scores(
    labels: NDArray[np.int32], count: int, field: GroundField
) -> NDArray[np.int64]:
    """The ground votes of each of the first ``count`` cells of ``labels`` (-1: none): the
    ``GroundField`` votes of the block of each of its pixels, summed (``choose_grounds``)."""
    own = np.where((labels >= 0) & (labels < count), labels, -1).astype(np.int32)
    _, sums = _location_sums(own, field.scores, field.shape, count, step=GROUND_STEP)
    return sums


def block_ground_scores(field: GroundField, found: NDArray[np.bool_]) -> NDArray[np.int64]:
    """The ground votes of the ``SIZE_STEP`` blocks of ``found`` (``block_features``) in raster
    order: those of the ``GroundField`` blocks within each, weighed by their land pixels."""
    ratio = SIZE_STEP // GROUND_STEP
    rows, columns = field.shape
    weighed = (field.scores * field.pixels[:, np.newaxis]).reshape(rows, columns, -1)
    padded = np.zeros(
        (-(-rows // ratio) * ratio, -(-columns // ratio) * ratio, weighed.shape[2]),
        dtype=np.int64,
    )
    padded[:rows, :columns] = weighed
    summed = padded.reshape(
        padded.shape[0] // ratio, ratio, padded.shape[1] // ratio, ratio, -1
    ).sum(axis=(1, 3))
    return summed[: found.shape[0], : found.shape[1]][found]


@measured
def _ground_training(  # noqa: PLR0913 - the map, its voters, their grounds, height, grid and land.
    labels: NDArray[np.int32],
    voters: NDArray[np.bool_],
    truth: NDArray[np.int64],
    height: NDArray[np.integer],
    grid: ClimateGrid,
    *,
    land: NDArray[np.bool_],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The ``GROUND_COLUMNS`` readings of the ``GROUND_STEP`` blocks of the land of the
    ``voters`` (per label, one more for -1) and the ground (``truth``, per label) of the voter
    holding most of each block's pixels (ties: the lower label), the relief read over ``land``."""
    blocks, pixels = _block_raster(voters[labels])
    count = int(pixels.size)
    readings = _ground_readings(blocks, count, height, grid, land=land, columns=None)
    labelled = int(voters.size)
    owner = np.full(count, -1, dtype=np.int64)
    strip = GROUND_STEP * (RELIEF_ROWS // GROUND_STEP)
    for start in range(0, int(labels.shape[0]), strip):
        checkpoint()
        block = blocks[start : start + strip]
        here = block >= 0
        keys, held = np.unique(
            block[here].astype(np.int64) * labelled + labels[start : start + strip][here],
            return_counts=True,
        )
        order = np.lexsort((keys % labelled, -held, keys // labelled))
        first = np.ones(order.size, dtype=bool)
        first[1:] = keys[order][1:] // labelled != keys[order][:-1] // labelled
        chosen = keys[order][first]
        owner[chosen // labelled] = chosen % labelled
    del blocks
    found = np.flatnonzero(pixels)
    return readings[found], truth[owner[found]]


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
    of the pairs' votes (``size_table``); they are the mainland's (``MAINLAND``). ``dry`` are the
    pairs that are never wetland and ``offsets`` how far, in thousandths of an octave, vanilla's
    locations of each ground lie off the size of their class, inland (row 0) and on the coast
    (row 1), read against the flatland beside them (``_local_offsets``). ``ground_table`` holds
    the ``GROUND_COLUMNS`` readings of the ``GROUND_STEP`` blocks of the Old World's passable
    land, ``grounds`` the ground of the location holding most of each (``_ground_training``) and
    ``ground_weights`` the ``calibrated_weights`` of each ground's votes (``ground_scores``,
    ``choose_grounds``). ``vote_table`` holds the
    ``land_features`` the climate vote of the cells learns from (``assign_biomes`` with open
    climates: each vanilla location read at its centre), ``vote_pairs`` their pairs, of which
    ``vote_climate_of`` gives the climate, ``vote_weights`` the vote's ``calibrated_weights``,
    ``vote_dry`` the pairs that are never wetland and ``vote_size`` the index of each among
    ``pairs`` (-1: a pair the size model has no location of), for ``cell_sizes``.
    """

    features: NDArray[np.int64]
    pairs: NDArray[np.int64]
    climate_of: NDArray[np.int64]
    size: NDArray[np.int64]
    weights: NDArray[np.int64]
    dry: NDArray[np.bool_]
    offsets: NDArray[np.int64]
    ground_table: NDArray[np.int64]
    grounds: NDArray[np.int64]
    ground_weights: NDArray[np.int64]
    vote_table: NDArray[np.int64]
    vote_pairs: NDArray[np.int64]
    vote_climate_of: NDArray[np.int64]
    vote_weights: NDArray[np.int64]
    vote_dry: NDArray[np.bool_]
    vote_size: NDArray[np.int64]

    def digest(self) -> str:
        """SHA-256 of the model, for the keys of the worlds made with it."""
        found = hashlib.sha256()
        for array in (
            self.features,
            self.pairs,
            self.climate_of,
            self.size,
            self.weights,
            self.dry,
            self.offsets,
            self.ground_table,
            self.grounds,
            self.ground_weights,
            self.vote_table,
            self.vote_pairs,
            self.vote_climate_of,
            self.vote_weights,
            self.vote_dry,
            self.vote_size,
        ):
            found.update(repr(array.shape).encode("ascii"))
            found.update(np.ascontiguousarray(array, dtype=np.int64).tobytes())
        return found.hexdigest()


@measured
def size_model(
    game_map: Eu5Map,
    templates: dict[str, dict[str, str]],
    height: NDArray[np.uint16],
    *,
    mainland: int = MAINLAND,
) -> SizeModel:
    """The ``SizeModel`` of the game's own map, read before anything is moved or generated.

    The locations are the passable ones the vote learns from with open climates
    (``assign_biomes``): the Old World and the Americas, without the cultivated land.
    Wastelands are planned on the cells later (``rnw.barrens``); vanilla's are vast and would
    make the land beside them as large. A location is read as the blocks it lies in, the way a
    generated domain is (``watersheds.spacing_grid``), not at its centre, which lies the nearer
    the coast the smaller a coastal location is. ``height`` is the vanilla height at location
    resolution (``DecalStore.world_heights``). The sizes are learned from the locations of
    landmasses of at least ``mainland`` locations.
    """
    labels = game_map.labels
    count = len(game_map.keys)
    kinds = np.array([kind in LAND_KINDS for kind in game_map.classes] + [False])
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes] + [False])
    land = kinds[labels]
    grid = climate_grid(sea[labels], height, seasonal=True)
    found, features = block_features(land, height, grid)
    table = np.zeros((found.size, features.shape[1]), dtype=np.int64)
    table[found.ravel()] = features
    pixels, sums = _location_sums(labels, table, (int(found.shape[0]), int(found.shape[1])), count)
    attributes = [templates.get(key, {}) for key in game_map.keys]
    learned, joint = _land_training(game_map, attributes, pixels, open_climate=True)
    passable = [
        slot
        for slot, i in enumerate(learned)
        if pixels[i] > 0 and game_map.classes[i] is CellClass.LAND
    ]
    contacts = adjacency_pairs(labels, wrap_x=True)
    coastal = _vanilla_coastal(game_map, contacts)
    landmass = _landmass_sizes(
        contacts, np.array([kind not in WATER_KINDS for kind in game_map.classes])
    )
    old_world = _old_world(game_map)
    # Each region's median is its passable land's, islands among them.
    medians: dict[bool, int] = {}
    for region in (True, False):
        values = sorted(
            int(pixels[learned[slot]])
            for slot in passable
            if bool(old_world[learned[slot]]) is region
        )
        if values:
            medians[region] = values[(len(values) - 1) // 2]
    kept = [slot for slot in passable if landmass[learned[slot]] >= mainland]
    index = np.array([learned[slot] for slot in kept], dtype=np.int64)
    neighbours = _contact_rows(contacts, index, count)
    del contacts
    names, pairs = _vocabulary([joint[slot] for slot in kept])
    _, climate_of = _vocabulary([name.split("|")[0] for name in names])
    size = np.array(
        [octave_parts(int(pixels[i]), medians[bool(old_world[i])]) for i in index.tolist()],
        dtype=np.int64,
    )
    grounds = [attributes[learned[slot]].get("topography", "") for slot in kept]
    centred, points, mean_height = _label_centres(labels, height, count)
    voters = np.array(
        [
            kind is CellClass.LAND
            and bool(old_world[i])
            and centred[i] > 0
            and attributes[i].get("topography", "") in TOPOGRAPHIES
            for i, kind in enumerate(game_map.classes)
        ]
        + [False],
        dtype=bool,
    )
    truth = np.array(
        [
            TOPOGRAPHIES.index(row["topography"])
            if row.get("topography", "") in TOPOGRAPHIES
            else -1
            for row in attributes
        ]
        + [-1],
        dtype=np.int64,
    )
    ground = _ground_training(labels, voters, truth, height, grid, land=land)
    del land
    # The climate vote of the cells, as ``assign_biomes`` makes it with open climates.
    vote_names, vote_pairs = _vocabulary(joint)
    _, vote_climate_of = _vocabulary([name.split("|")[0] for name in vote_names])
    learned_index = np.array(learned, dtype=np.int64)
    known = {name: number for number, name in enumerate(names)}
    vote = (
        land_features(grid, points[learned_index], mean_height[learned_index]),
        vote_pairs,
        vote_climate_of,
        np.array([name.split("|")[1] in NO_WETLANDS for name in vote_names], dtype=bool),
        np.array([known.get(name, -1) for name in vote_names], dtype=np.int64),
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
        dry=np.array([name.split("|")[1] in NO_WETLANDS for name in names], dtype=bool),
        coastal=coastal[index],
        contacts=neighbours,
        ground=ground,
        vote=vote,
    )


def _contact_rows(
    contacts: NDArray[np.int64], index: NDArray[np.int64], count: int
) -> NDArray[np.int64]:
    """The ``contacts`` (``adjacency_pairs`` of ``count`` labels) of two labels of ``index``, as
    pairs of their rows in ``index``."""
    row = np.full(count, -1, dtype=np.int64)
    row[index] = np.arange(index.size, dtype=np.int64)
    low = contacts >> np.int64(32)
    high = contacts & np.int64((1 << 32) - 1)
    known = (low >= 0) & (high >= 0) & (low < count) & (high < count)
    first, second = row[low[known]], row[high[known]]
    keep = (first >= 0) & (second >= 0)
    return np.stack([first[keep], second[keep]], axis=1)


def size_table(  # noqa: PLR0913 - the locations, their classes, sizes and grounds.
    features: NDArray[np.int64],
    pairs: NDArray[np.int64],
    climate_of: NDArray[np.int64],
    size: NDArray[np.int64],
    *,
    topography: NDArray[np.int64],
    dry: NDArray[np.bool_],
    coastal: NDArray[np.bool_],
    contacts: NDArray[np.int64],
    ground: tuple[NDArray[np.int64], NDArray[np.int64]],
    vote: tuple[
        NDArray[np.int64],
        NDArray[np.int64],
        NDArray[np.int64],
        NDArray[np.bool_],
        NDArray[np.int64],
    ],
) -> SizeModel:
    """The ``SizeModel`` of these locations, its votes weighed as the vote reads them.

    A location's size off its class is its size less the size its class gives it, read without
    itself: the mean size of the ``NEIGHBOURS`` other locations of its pair nearest in
    ``SIZE_COLUMNS`` (``class_sizes``). The offsets of the grounds (``topography``, indices of
    ``TOPOGRAPHIES``) inland and on the coast (``coastal``) are read from the locations that
    touch (``contacts``: pairs of rows, ``_local_offsets``). A location
    of a ground no passable cell is given (-1: vanilla's few passable atolls and mountain
    wastelands) still sizes its class but sets no offset. ``ground`` is the vote's table of
    readings and the grounds of its rows (``SizeModel.ground_table``, ``SizeModel.grounds``),
    whose votes are weighed as they read vanilla (``SizeModel.ground_weights``). ``vote`` is the
    climate vote of the cells: its table, pairs, their climates, which are dry and their index
    among ``pairs`` (``SizeModel.vote_table`` and after), its votes weighed as they read vanilla.
    """
    train, _ = _standardize(features, features[:0], land_weights(int(features.shape[1])))
    by_size = _size_train(features, features[:0])[0]
    given = np.zeros(size.size, dtype=np.int64)
    for pair in np.unique(pairs).tolist():
        members = np.flatnonzero(pairs == pair)
        k = min(NEIGHBOURS, int(members.size) - 1)
        if k <= 0:
            given[members] = size[members] * PERMILLE // OCTAVE_PARTS
            continue
        for start in range(0, int(members.size), CHUNK):
            nearest = nearest_others(by_size[members], start, k)
            here = members[start : start + int(nearest.shape[0])]
            given[here] = np.floor_divide(
                size[members][nearest].sum(axis=1) * PERMILLE, OCTAVE_PARTS * k
            )
    off = size * PERMILLE // OCTAVE_PARTS - given
    offsets = _local_offsets(off, topography, coastal, pairs, contacts)
    return SizeModel(
        features=features,
        pairs=pairs,
        climate_of=climate_of,
        size=size,
        weights=calibrated_weights(train, pairs, climate_of),
        dry=dry,
        offsets=offsets,
        ground_table=ground[0],
        grounds=ground[1],
        ground_weights=calibrated_weights(
            _standardize(ground[0], ground[0][:0], GROUND_WEIGHTS)[0],
            ground[1],
            np.arange(len(TOPOGRAPHIES), dtype=np.int64),
            exact_ties=True,
        ),
        vote_table=vote[0],
        vote_pairs=vote[1],
        vote_climate_of=vote[2],
        vote_weights=calibrated_weights(
            _standardize(vote[0], vote[0][:0], land_weights(int(vote[0].shape[1])))[0],
            vote[1],
            vote[2],
        ),
        vote_dry=vote[3],
        vote_size=vote[4],
    )


def _local_offsets(
    off: NDArray[np.int64],
    topography: NDArray[np.int64],
    coastal: NDArray[np.bool_],
    pairs: NDArray[np.int64],
    contacts: NDArray[np.int64],
) -> NDArray[np.int64]:
    """How far, in thousandths of an octave, the locations of each ground lie off the size of
    their class inland (row 0) and on the coast (row 1), read against the flatland beside them.

    ``off`` is each location's size off its class (``size_table``). Over the ``contacts`` (pairs
    of rows) of two locations of one pair, one of them flatland and the two of different ground
    or coast, the offsets are those whose differences fit the differences of ``off`` best (least
    squares, exactly, in fractions; floored). The grounds linked by such contacts keep the mean
    ``off`` of their locations; a ground linked to none is its locations' mean, one with no
    location (``topography`` -1 counts for none) none. Read so, the land beside a location
    stands for its region: vanilla's mountains lie 0.16 of an octave under their class inland
    and 0.11 over it on the coast, as a mountain region's locations are all smaller or all
    larger, but within 0.07 of the flatland beside them [V-EXEC 2026-11-15].
    """
    kinds = len(TOPOGRAPHIES)
    groups = 2 * kinds
    flat = TOPOGRAPHIES.index("flatland")
    known = topography >= 0
    group = np.where(known, coastal.astype(np.int64) * kinds + topography, -1)
    first, second = contacts[:, 0], contacts[:, 1]
    star = (
        known[first]
        & known[second]
        & (pairs[first] == pairs[second])
        & ((topography[first] == flat) | (topography[second] == flat))
        & (group[first] != group[second])
    )
    one, other = group[first[star]], group[second[star]]
    difference = off[first[star]] - off[second[star]]
    links = np.zeros((groups, groups), dtype=np.int64)
    np.add.at(links, (one, other), 1)
    np.add.at(links, (other, one), 1)
    right = np.zeros(groups, dtype=np.int64)
    np.add.at(right, one, difference)
    np.add.at(right, other, -difference)
    members = np.bincount(group[known], minlength=groups)
    totals = np.zeros(groups, dtype=np.int64)
    np.add.at(totals, group[known], off[known])
    root = list(range(groups))

    def find(node: int) -> int:
        while root[node] != node:
            node = root[node]
        return node

    for a, b in zip(*np.nonzero(links), strict=True):
        root[find(int(a))] = find(int(b))
    found = [0] * groups
    for component in sorted({find(g) for g in range(groups) if members[g]}):
        chosen = [g for g in range(groups) if members[g] and find(g) == component]
        # The normal equations of the component, the first replaced by the mean that it keeps.
        matrix = [
            [Fraction(int(-links[g, h]) + (int(links[g].sum()) if g == h else 0)) for h in chosen]
            for g in chosen
        ]
        values = [Fraction(int(right[g])) for g in chosen]
        matrix[0] = [Fraction(int(members[g])) for g in chosen]
        values[0] = Fraction(int(totals[chosen].sum()))
        for g, value in zip(chosen, _solved(matrix, values), strict=True):
            found[g] = math.floor(value)
    return np.array(found, dtype=np.int64).reshape(2, kinds)


def _solved(matrix: list[list[Fraction]], values: list[Fraction]) -> list[Fraction]:
    """The solution of a square, regular linear system, exactly (Gauss-Jordan elimination)."""
    size = len(values)
    rows = [[*row, value] for row, value in zip(matrix, values, strict=True)]
    for column in range(size):
        pivot = next(row for row in range(column, size) if rows[row][column] != 0)
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for row in range(size):
            if row != column and rows[row][column] != 0:
                factor = rows[row][column] / rows[column][column]
                rows[row] = [a - factor * b for a, b in zip(rows[row], rows[column], strict=True)]
    return [rows[row][size] / rows[row][row] for row in range(size)]


@measured
def _location_sums(
    labels: NDArray[np.int32],
    table: NDArray[np.int64],
    shape: tuple[int, int],
    count: int,
    *,
    step: int = SIZE_STEP,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The pixels of each of ``count`` labels and the sums of ``table`` (one row per ``step``
    block in raster order, ``shape`` blocks) over them; a label of -1 is none."""
    pixels = np.zeros(count, dtype=np.int64)
    sums = np.zeros((count, table.shape[1]), dtype=np.int64)
    table = np.ascontiguousarray(table)
    for first in range(0, int(labels.shape[0]), step * 8):
        checkpoint()
        found, total = _native.location_sums(
            np.ascontiguousarray(labels[first : first + step * 8]),
            table,
            count,
            step,
            shape[1],
            first,
        )
        pixels += found
        sums += total
    return pixels, sums


def class_sizes(
    model: SizeModel,
    query: NDArray[np.int64],
    ground: NDArray[np.int64],
    coastal: NDArray[np.bool_],
) -> NDArray[np.int64]:
    """How large vanilla makes its locations on land like each row of ``query``
    (``block_features``), as log2 over its region's median in thousandths of an octave.

    The row takes the (climate, vegetation) pair the vote would give it with open climates
    (``assign_biomes``, ``regularize_votes`` without smoothing), then the mean size of the
    ``NEIGHBOURS`` vanilla locations of that pair nearest in ``SIZE_COLUMNS``: vanilla sizes its
    locations by what they are, deserts and the cold large and the wet lowlands small, so a size
    read from the neighbours of every class would pull each class towards the median. The row's
    ground, chosen from the ground votes of its land (``ground``: ``block_ground_scores``,
    ``choose_grounds``), moves the size by that ground's offset inland or on the coast
    (``coastal``: the block holds sea).
    """
    if model.pairs.size == 0:
        message = "The size model has no land location to learn from"
        raise ValueError(message)
    count = int(model.climate_of.size)
    train, rows = _standardize(model.features, query, land_weights(int(query.shape[1])))
    scores = knn_scores(train, model.pairs, rows, count) * model.weights[np.newaxis, :]
    chosen = chosen_pairs(scores, model.climate_of)
    kinds = choose_grounds(model, ground, model.dry[chosen])
    return _pair_sizes(model, chosen, query) + model.offsets[coastal.astype(np.int64), kinds]


def _size_train(
    features: NDArray[np.int64], query: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """``features`` and ``query`` (``block_features``) standardised in ``SIZE_COLUMNS``, weighed
    as the vote weighs those columns."""
    weights = land_weights(int(features.shape[1]))
    columns = [column for column in SIZE_COLUMNS if column < features.shape[1]]
    return _standardize(
        features[:, columns], query[:, columns], tuple(weights[column] for column in columns)
    )


def _pair_sizes(
    model: SizeModel, pair: NDArray[np.int64], features: NDArray[np.int64]
) -> NDArray[np.int64]:
    """The mean size of the ``NEIGHBOURS`` locations of each row's ``pair`` nearest to its
    ``features`` in ``SIZE_COLUMNS``, thousandths of an octave."""
    train, rows = _size_train(model.features, features)
    out = np.zeros(rows.shape[0], dtype=np.int64)
    for kind in np.unique(pair).tolist():
        members = np.flatnonzero(model.pairs == kind)
        here = np.flatnonzero(pair == kind)
        totals, k = knn_totals(train[members], model.size[members], rows[here])
        out[here] = np.floor_divide(totals * PERMILLE, OCTAVE_PARTS * k)
    return out


@measured
def cell_readings(  # noqa: PLR0913 - the cells, the height, grid, sea and ground of the land.
    labels: NDArray[np.int32],
    count: int,
    height: NDArray[np.integer],
    grid: ClimateGrid,
    sea: NDArray[np.bool_],
    *,
    ground: GroundField,
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64], NDArray[np.bool_]]:
    """What ``cell_sizes`` reads of each of the ``count`` cells of ``labels`` (-1: none) on
    ``height`` and ``grid``: the ``block_features`` averaged over its pixels, the
    ``land_features`` at its centre, the votes of the ``ground`` of its land
    (``cell_ground_scores``), each as the export reads its cells (``assign_biomes``), and whether
    it touches the ``sea`` (not a lake), as the export's coastal cells do."""
    land = (labels >= 0) & (labels < count)
    found, blocks = block_features(land, height, grid)
    table = np.zeros((found.size, blocks.shape[1]), dtype=np.int64)
    table[found.ravel()] = blocks
    pixels, sums = _location_sums(
        np.where(land, labels, -1).astype(np.int32),
        table,
        (int(found.shape[0]), int(found.shape[1])),
        count,
    )
    del land, table
    features = sums // np.maximum(pixels, 1)[:, np.newaxis]
    centred, votes, coastal = _centred_readings(labels, count, height, grid, sea, ground=ground)
    return features, centred, votes, coastal


def _centred_readings(  # noqa: PLR0913 - the same inputs as cell_readings, without block means.
    labels: NDArray[np.int32],
    count: int,
    height: NDArray[np.integer],
    grid: ClimateGrid,
    sea: NDArray[np.bool_],
    *,
    ground: GroundField,
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.bool_]]:
    """Centre features, ground votes and sea contacts, without the unused block statistics."""
    centred = land_features(grid, _cell_centres(labels, count), cell_mean(labels, height, count))
    votes = cell_ground_scores(labels, count, ground)
    return centred, votes, _cells_touching(labels, count, sea)


def _cells_touching(
    labels: NDArray[np.int32], count: int, mask: NDArray[np.bool_]
) -> NDArray[np.bool_]:
    """Which of the first ``count`` labels touch a pixel of ``mask`` (4-neighbours), a strip of
    ``RELIEF_ROWS`` rows (and the next row) at a time."""
    found = np.zeros(count + 1, dtype=bool)
    rows = int(labels.shape[0])
    for start in range(0, rows, RELIEF_ROWS):
        checkpoint()
        stop = min(rows, start + RELIEF_ROWS + 1)
        cell = labels[start:stop]
        own = np.where((cell >= 0) & (cell < count), cell, count)
        near = mask[start:stop]
        for first, second, first_near, second_near in (
            (own[:, :-1], own[:, 1:], near[:, :-1], near[:, 1:]),
            (own[:-1], own[1:], near[:-1], near[1:]),
        ):
            found[first[second_near]] = True
            found[second[first_near]] = True
    return found[:count]


def _landmass_sizes(contacts: NDArray[np.int64], land: NDArray[np.bool_]) -> NDArray[np.int64]:
    """The number of ``land`` labels of the landmass each label belongs to (0 for the others),
    landmasses joined by the ``contacts`` (``adjacency_pairs``) of two land labels."""
    low = contacts >> np.int64(32)
    high = contacts & np.int64((1 << 32) - 1)
    known = (low >= 0) & (low < land.size) & (high >= 0) & (high < land.size)
    low, high = low[known], high[known]
    keep = land[low] & land[high]
    low, high = low[keep], high[keep]
    root = np.arange(land.size, dtype=np.int64)
    while True:
        lowest = np.minimum(root[low], root[high])
        joined = root.copy()
        np.minimum.at(joined, low, lowest)
        np.minimum.at(joined, high, lowest)
        joined = joined[joined]
        if np.array_equal(joined, root):
            break
        root = joined
    sizes = np.bincount(root[land], minlength=land.size)
    return np.where(land, sizes[root], 0)


def _cell_centres(labels: NDArray[np.int32], count: int) -> NDArray[np.int64]:
    """The centre (row, column) of each of the first ``count`` labels, floored as
    ``newworld.derive_world`` floors them, a strip of ``RELIEF_ROWS`` rows at a time."""
    totals = np.zeros((4, count), dtype=np.int64)
    for start in range(0, int(labels.shape[0]), RELIEF_ROWS):
        checkpoint()
        totals += _native.label_moments(
            np.ascontiguousarray(labels[start : start + RELIEF_ROWS]), None, count, start
        )
    return (totals[1:3] // np.maximum(totals[0], 1)).T.copy()


def cell_edges(labels: NDArray[np.int32], count: int) -> NDArray[np.int64]:
    """The contacts of the first ``count`` labels of ``labels`` (4-neighbours, as
    ``newworld.derive_world`` reads a world's), one (lower, higher) row per pair."""
    pairs = adjacency_pairs(labels)
    low = pairs >> np.int64(32)
    high = pairs & np.int64((1 << 32) - 1)
    keep = (low >= 0) & (high >= 0) & (low < count) & (high < count)
    return np.stack([low[keep], high[keep]], axis=1).astype(np.int64)


def cell_pairs(
    model: SizeModel, centred: NDArray[np.int64], *, edges: NDArray[np.int64]
) -> NDArray[np.int64]:
    """The (climate, vegetation) pair (an index of ``SizeModel.vote_pairs``) ``assign_biomes``
    gives each cell with open climates, from the ``land_features`` read at its centre
    (``centred``): the weights matched to these cells through ``OPEN_CLIMATE_ROUNDS`` of
    smoothing over their contacts (``edges``, ``smoothed_pairs``)."""
    vote_train, vote_rows = _standardize(
        model.vote_table, centred, land_weights(int(centred.shape[1]))
    )
    scores = knn_scores(vote_train, model.vote_pairs, vote_rows, int(model.vote_climate_of.size))
    choose = partial(
        smoothed_pairs, climate_of=model.vote_climate_of, edges=edges, rounds=OPEN_CLIMATE_ROUNDS
    )
    weights = matched_weights(scores, model.vote_weights, choose)
    return choose(scores * weights[np.newaxis, :])


def cell_sizes(  # noqa: PLR0913 - the model, the cells' readings, coast and contacts.
    model: SizeModel,
    features: NDArray[np.int64],
    centred: NDArray[np.int64],
    ground: NDArray[np.int64],
    coastal: NDArray[np.bool_],
    *,
    edges: NDArray[np.int64],
) -> NDArray[np.int64]:
    """How large vanilla makes its locations of the class and ground each cell will be given,
    as log2 over its region's median in thousandths of an octave (``class_sizes``).

    Each cell's pair is voted as ``assign_biomes`` votes it (``cell_pairs``: on the
    ``land_features`` read at its centre, ``centred``, by ``SizeModel.vote_table``, smoothed
    over the cells' contacts, ``edges``, the weights matched to these cells); its
    ground as the final cells' is, from the votes of its land (``ground``,
    ``cell_ground_scores``; ``choose_grounds``, matched; a desert is never wetland). The size is
    the mean of the ``NEIGHBOURS`` vanilla locations of that pair
    nearest in the ``SIZE_COLUMNS`` of ``features`` (``block_features`` averaged over the cell,
    ``SizeModel.features``) and that ground's offset inland or on the coast (``coastal``: the
    cell touches the sea). A pair the size model holds no location of takes the pair the
    blocks' vote gives those features (``class_sizes``). Read by blocks instead, the class of a
    cell had been another than the cell's own for 43 % of the cells and its ground for 58 % of
    the wetlands [V-EXEC 2026-11-15].
    """
    if model.vote_pairs.size == 0 or model.pairs.size == 0:
        message = "The size model has no land location to learn from"
        raise ValueError(message)
    voted = cell_pairs(model, centred, edges=edges)
    pair = model.vote_size[voted]
    missing = pair < 0
    if missing.any():
        train, rows = _standardize(
            model.features, features[missing], land_weights(int(features.shape[1]))
        )
        fallback = knn_scores(train, model.pairs, rows, int(model.climate_of.size))
        pair[missing] = chosen_pairs(fallback * model.weights[np.newaxis, :], model.climate_of)
    kinds = choose_grounds(model, ground, model.vote_dry[voted], matched=True)
    return _pair_sizes(model, pair, features) + model.offsets[coastal.astype(np.int64), kinds]


@measured
def coastal_offsets(  # noqa: PLR0913 - the model, the cells, the height, grid, sea and ground.
    model: SizeModel,
    labels: NDArray[np.int32],
    count: int,
    *,
    height: NDArray[np.integer],
    grid: ClimateGrid,
    sea: NDArray[np.bool_],
    ground: GroundField,
) -> NDArray[np.int64]:
    """How far vanilla's locations of the ground each of the ``count`` cells of ``labels`` will
    be given lie off its inland flatland, on the coast, in thousandths of an octave
    (``SizeModel.offsets``): the pair and the ground voted as ``cell_sizes`` votes them; 0 for a
    cell that does not touch the ``sea``."""
    centred, votes, coastal = _centred_readings(labels, count, height, grid, sea, ground=ground)
    voted = cell_pairs(model, centred, edges=cell_edges(labels, count))
    kinds = choose_grounds(model, votes, model.vote_dry[voted], matched=True)
    flatland = model.offsets[0, TOPOGRAPHIES.index("flatland")]
    return np.where(coastal, model.offsets[1, kinds] - flatland, 0).astype(np.int64)


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
    # The ground votes of each cell's land (``cell_ground_scores``), which choose its ground.
    ground: NDArray[np.int64] | None = None


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
    exact = np.zeros((4, count), dtype=np.int64)
    for start in range(0, labels.shape[0], 1024):
        checkpoint()
        exact += _native.label_moments(
            np.ascontiguousarray(labels[start : start + 1024]),
            np.ascontiguousarray(height[start : start + 1024], dtype=np.int64),
            count,
            start,
        )
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
    """Rainfall, distance to the sea and latitude of every cell (zero for water); with the
    seasons the rainfall is the sum of the two seasons' ``rain_root``."""
    columns = [np.zeros(count, dtype=np.int64) for _ in range(3)]
    for column, source in zip(columns, (1, 3, 0), strict=True):
        column[land_cells] = query_x[:, source]
    if query_x.shape[1] > len(LAND_WEIGHTS):
        columns[0][land_cells] += query_x[:, len(LAND_WEIGHTS)]
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
    voted: dict[int, str] | None,
) -> list[str]:
    """The topography of every land cell: for the passable ones the ground ``voted`` for them
    (epoch 64, with ``Generated.ruggedness``; ``_voted_grounds``) or ranks of relief, the plan's
    (or the epoch 63 rule's) for the wastelands."""
    topography = [""] * len(cells.kinds)
    plain = [i for i in land_cells.tolist() if cells.kinds[i] is CellClass.LAND]
    ranked = (
        _topography(
            plain,
            shares=shares,
            mean_height=cells.mean_height,
            spread=cells.spread,
            rain=rain,
            coast=coast,
            dry=frozenset(i for i in plain if vegetation[i] in NO_WETLANDS),
        )
        if voted is None
        else {cell: voted[cell] for cell in plain}
    )
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


def _voted_grounds(
    chosen: list[int],
    cells: Generated,
    *,
    vegetation: list[str],
    ground: SizeModel | None,
) -> dict[int, str]:
    """The ground of the ``chosen`` cells, chosen from the votes of their land
    (``Generated.ground``) with the weights matched to these cells (epoch 64, ``choose_grounds``);
    dry cells are no wetlands."""
    if ground is None or cells.ground is None:
        message = "The ground of the land is voted by the game's own land, not read"
        raise ValueError(message)
    index = np.array(chosen, dtype=np.int64)
    voted = choose_grounds(
        ground,
        cells.ground[index],
        np.array([vegetation[i] in NO_WETLANDS for i in chosen], dtype=bool),
        matched=True,
    )
    kinds: list[int] = voted.tolist()
    return {cell: TOPOGRAPHIES[kind] for cell, kind in zip(chosen, kinds, strict=True)}


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
    pooled_resources: bool = False,
) -> tuple[CellBiomes, dict[str, object]]:
    """Template attributes for every generated cell and calibration statistics.

    The raw materials are drawn from ``material_seed`` when given (the resources part of the
    world, ``rnw.layers``), else from ``seed``; everything else is the land's, from ``seed``.
    With ``wastelands`` (epoch 64) the wastelands are planned from the climate and vegetation
    just chosen (``rnw.barrens``) and ``CellBiomes.kinds`` holds the class of every cell; without
    it the cells keep the class they came with, the highest ones being wasteland. With
    ``open_climate`` (epoch 64, ``epoch.OPEN_CLIMATE``) the vote learns from the Americas too,
    without the cultivated land, weighs each pair so that it reads vanilla as it is
    (``calibrated_weights``), smooths over ``OPEN_*_ROUNDS`` and matches those weights to the
    world's own land through the smoothing (``matched_weights``, ``smoothed_pairs``). The ground
    of cells with a ``Generated.ruggedness`` (epoch
    64) is voted once over all the land by the vanilla locations of ``ground`` (the ``SizeModel``
    of the game's map, ``vote_grounds``, matched alike), which they then require. With
    ``pooled_resources`` (epoch 64, ``epoch.POOLED_RESOURCES``) the raw materials are drawn from
    pooled classes (``_raw_materials``).
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
    train_s, query_s = _standardize(train_x, query_x, land_weights(int(query_x.shape[1])))
    scores = knn_scores(train_s, joint_ids, query_s, len(joint_names))
    position = np.full(count, -1, dtype=np.int64)
    position[land_cells] = np.arange(land_cells.size)
    edges = _edge_array(cells.edges, land)
    local_edges = position[edges] if edges.size else edges
    if open_climate:
        # Matched through the smoothing, so that the smoothed vote keeps each pair's share.
        weights = matched_weights(
            scores,
            calibrated_weights(train_s, joint_ids, joint_climate),
            partial(
                smoothed_pairs,
                climate_of=joint_climate,
                edges=local_edges,
                rounds=OPEN_CLIMATE_ROUNDS,
            ),
        )
        scores = scores * weights[np.newaxis, :]
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
    grounds = {name: shares[name] for name in TOPOGRAPHIES}
    # The ground of every land cell, voted once: the plan reads it before it chooses the
    # wastelands among them, and the passable cells keep it.
    voted = (
        None
        if cells.ruggedness is None
        else _voted_grounds(land_cells.tolist(), cells, vegetation=vegetation, ground=ground)
    )
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
            grounds=voted,
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
        shares=grounds,
        vegetation=vegetation,
        rain=rain,
        coast=coast,
        voted=voted,
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
        pooled=pooled_resources,
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
    grounds: dict[int, str] | None,
    edges: NDArray[np.int64],
    settings: WastelandSettings,
    seed: int,
) -> WastelandPlan:
    """The wasteland plan of ``rnw.barrens`` for the cells, the climate and vegetation chosen and
    the voted ground of every land cell (``grounds``)."""
    if vanilla.pixels is None or cells.pixels is None:
        message = "The wasteland plan needs the pixel counts of the vanilla and generated cells"
        raise ValueError(message)
    if cells.ruggedness is None or grounds is None:
        message = "The wasteland plan needs the ruggedness and the voted ground of the cells"
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
        ground=tuple(
            GROUND_KINDS[grounds[cell]] if cell in grounds else ""
            for cell in range(len(cells.kinds))
        ),
        height=cells.mean_height,
        spread=cells.spread,
        rugged=cells.ruggedness,
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
    pooled: bool = False,
) -> tuple[str, ...]:
    """Draw each land cell's raw material from vanilla frequencies of similar locations.

    The frequencies are those of the vanilla New World (``source``): drawing them from the
    Old World gave a generated America elephants, horses, wheat, rice, silk and tea and none
    of its maize, potatoes, cocoa, tobacco or chili (C116). Similar means the same climate,
    vegetation, topography and coast. ``precious_permille`` weighs gold, silver, gems and
    pearls against the rest (1000: their vanilla share); ordinary materials use their
    individual ``resources`` weights. No material comes to the coast or inland that the
    vanilla New World does not have there; if a cell's coastal/inland pool is empty,
    generation fails explicitly.

    Up to epoch 63 a cell takes the first class of the four that vanilla has, so a class of two
    locations decides all its cells, and fewer of them only when a weight empties it. With
    ``pooled`` (epoch 64, ``epoch.POOLED_RESOURCES``) every class is blended with the broader
    ones by how many vanilla locations stand behind it (``_pooled``), and the materials are
    weighed so that vanilla's own classes expect vanilla's own counts (``_material_factors``).
    """
    if pooled:
        return _pooled_materials(
            game_map,
            attributes=attributes,
            vanilla=vanilla,
            source=source,
            cells=cells,
            fields=fields,
            seed=seed,
            weights=(precious_permille, resources),
        )
    tables = [
        {key: _weighted(counter, precious_permille, resources) for key, counter in table.items()}
        for table in _material_tables(game_map, attributes, vanilla, source)
    ]
    climate, vegetation, topography = fields
    stream = derive_seed(seed, "raw_material")
    out: list[str] = []
    for cell, kind in enumerate(cells.kinds):
        if kind is not CellClass.LAND:
            out.append("")
            continue
        flag = "coast" if cells.coastal[cell] else "inland"
        keys = _material_keys(climate[cell], vegetation[cell], topography[cell], flag)
        counter = next(
            (table[key] for table, key in zip(tables, keys, strict=True) if table.get(key)),
            None,
        )
        if counter is None:
            message = f"No enabled raw materials for {flag} locations; increase resource weights"
            raise SettingsError(message)
        out.append(_pick(counter, hash_point(stream, cell, 0)))
    return tuple(out)


def _material_keys(
    climate: str, vegetation: str, topography: str, flag: str
) -> tuple[tuple[str, ...], ...]:
    """The classes of a location for its raw material, finest first; the coast flag stays."""
    return (
        (climate, vegetation, topography, flag),
        (climate, vegetation, flag),
        (vegetation, flag),
        (flag,),
    )


def _material_tables(
    game_map: Eu5Map,
    attributes: list[dict[str, str]],
    vanilla: VanillaLocations,
    source: NDArray[np.bool_],
) -> list[dict[tuple[str, ...], Counter[str]]]:
    """The raw materials of the vanilla New World's land counted in each class of
    ``_material_keys``, one table per level."""
    coastal = _vanilla_coastal(game_map, vanilla.pairs)
    tables: list[dict[tuple[str, ...], Counter[str]]] = [{}, {}, {}, {}]
    for i, kind in enumerate(game_map.classes):
        if kind is not CellClass.LAND or not source[i] or "raw_material" not in attributes[i]:
            continue
        row = attributes[i]
        vegetation = EMPTY_LAND.get(row.get("vegetation", ""), row.get("vegetation", ""))
        keys = _material_keys(
            row.get("climate", ""),
            vegetation,
            row.get("topography", ""),
            "coast" if coastal[i] else "inland",
        )
        for table, key in zip(tables, keys, strict=True):
            table.setdefault(key, Counter())[row["raw_material"]] += 1
    return tables


def _pooled(
    tables: list[dict[tuple[str, ...], Counter[str]]], keys: tuple[tuple[str, ...], ...]
) -> dict[str, int]:
    """The share of each material in the finest class of ``keys``, in ``POOL_SCALE``ths, each
    class blended with the next broader one as if that one stood behind it with
    ``RESOURCE_PRIOR`` locations: a class of two locations takes mostly the broader shares, one
    of hundreds keeps its own. An unknown class takes the broader shares whole. Integers."""
    shares: dict[str, int] = {}
    for table, key in reversed(tuple(zip(tables, keys, strict=True))):
        counter = table.get(key, Counter())
        total = sum(counter.values())
        if not shares:
            if total:
                shares = {name: count * POOL_SCALE // total for name, count in counter.items()}
            continue
        shares = {
            name: (counter.get(name, 0) * POOL_SCALE + RESOURCE_PRIOR * shares.get(name, 0))
            // (total + RESOURCE_PRIOR)
            for name in sorted(shares.keys() | counter.keys())
        }
    return {name: share for name, share in shares.items() if share > 0}


def _material_factors(
    tables: list[dict[tuple[str, ...], Counter[str]]],
) -> dict[str, int]:
    """The weight of each material, in ``FACTOR_ONE``ths, with which the pooled shares of the
    vanilla New World's own classes expect its own counts of every material.

    Pooling lends each class some of the broader classes' materials, which moves the totals:
    on vanilla's own classes gold, silver, gems and pearls together would expect 166 locations
    for its 179. Over ``CALIBRATION_ROUNDS`` rounds each weight is multiplied by the count over
    the expectation, so the precious slider's 1x is again vanilla's share [V-EXEC 2026-11-15].
    """
    finest = tables[0]
    target: Counter[str] = Counter()
    for counter in finest.values():
        target.update(counter)
    classes = [
        (sum(counter.values()), _pooled(tables, _material_keys(*key)))
        for key, counter in sorted(finest.items())
    ]
    factors = dict.fromkeys(sorted(target), FACTOR_ONE)
    for _ in range(CALIBRATION_ROUNDS):
        expected: Counter[str] = Counter()
        for count, shares in classes:
            weighed = {name: share * factors.get(name, 0) for name, share in shares.items()}
            total = sum(weighed.values())
            if total:
                for name, value in weighed.items():
                    expected[name] += count * value * POOL_SCALE // total
        factors = {
            name: max(1, factor * target[name] * POOL_SCALE // max(1, expected[name]))
            for name, factor in factors.items()
        }
    return factors


def _pooled_materials(  # noqa: PLR0913 - the same inputs as ``_raw_materials``.
    game_map: Eu5Map,
    *,
    attributes: list[dict[str, str]],
    vanilla: VanillaLocations,
    source: NDArray[np.bool_],
    cells: Generated,
    fields: tuple[list[str], list[str], list[str]],
    seed: int,
    weights: tuple[int, ResourceSettings],
) -> tuple[str, ...]:
    """Each land cell's raw material from the pooled shares of its class (epoch 64)."""
    tables = _material_tables(game_map, attributes, vanilla, source)
    factors = _material_factors(tables)
    precious_permille, resources = weights
    climate, vegetation, topography = fields
    stream = derive_seed(seed, "raw_material")
    pools: dict[tuple[str, ...], Counter[str]] = {}
    out: list[str] = []
    for cell, kind in enumerate(cells.kinds):
        if kind is not CellClass.LAND:
            out.append("")
            continue
        flag = "coast" if cells.coastal[cell] else "inland"
        keys = _material_keys(climate[cell], vegetation[cell], topography[cell], flag)
        pool = pools.get(keys[0])
        if pool is None:
            shares = _pooled(tables, keys)
            pool = _weighted(
                Counter(
                    {
                        name: share * factors.get(name, 0) // FACTOR_ONE
                        for name, share in shares.items()
                    }
                ),
                precious_permille,
                resources,
            )
            pool = +pool
            pools[keys[0]] = pool
        if not pool:
            message = f"No enabled raw materials for {flag} locations; increase resource weights"
            raise SettingsError(message)
        out.append(_pick(pool, hash_point(stream, cell, 0)))
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
