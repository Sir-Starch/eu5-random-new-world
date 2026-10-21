"""EU5 terrain material slots rebuilt from location data with the vanilla rules.

A height decal's material layer stores, per pixel, a slot of the location's biome in
``gfx/terrain2/materials.txt``, not a texture: 0-4 coast by topography (flatland,
hills, plateau, mountains, wetlands), 5 coast transition, 6 rivers and lake or sea
edges, 7 topography borders, 8 vegetation borders, 9 climate borders and 10-15 two
families of three variations [V-LOCAL C50]. Vanilla follows fixed rules measured on
four decals of build 25905365 [V-EXEC C51]: coast slots reach 1-4 pixels inland and 2-6
offshore, the transition 4-10 inland, the water edge 5-10 offshore; border bands are
centred on location borders where the attribute changes, about 0-4 pixels on each side,
topography first, then vegetation, then climate; rivers get a 0-3 pixel band; the
variation families form blobs about 25 pixels across and the levels about 8, with level
shares that depend on vegetation and topography (forest is level 1 only).

Most biomes list fewer than 16 materials (93 of 191 list 13). The shader clamps the slot
to 15 and reads the biome's material table, whose unlisted entries point at
``fallback_material`` (dead grass) [V-LOCAL C54; INFERRED]. Vanilla writes such slots
anyway; generated land does not: a slot the biome does not list falls back to the same
variation level of the first family, else to the highest listed level, else to slot 0.

All thresholds are wobbled by integer noise in absolute decal coordinates, so adjacent
decals agree. Pixels here are decal pixels, two per location pixel.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.noise import fractal_noise
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from numpy.typing import NDArray

NO_MATERIAL: Final[int] = 255
COAST_TRANSITION: Final[int] = 5
WATER_EDGE: Final[int] = 6
TOPOGRAPHY_BORDER: Final[int] = 7
VEGETATION_BORDER: Final[int] = 8
CLIMATE_BORDER: Final[int] = 9
VARIATION: Final[int] = 10
LEVELS: Final[int] = 3
SLOTS: Final[int] = 16
COAST_SLOTS: Final[dict[str, int]] = {
    "flatland": 0,
    "flatland_wasteland": 0,
    "hills": 1,
    "hills_wasteland": 1,
    "plateau": 2,
    "plateau_wasteland": 2,
    "mountains": 3,
    "mountain_wasteland": 3,
    "wetlands": 4,
    "wetlands_wasteland": 4,
}
# Attribute changes that vanilla does not mark with a border band [V-EXEC C51].
TOPOGRAPHY_GROUPS: Final[dict[str, str]] = {"flatland_wasteland": "flatland"}
CLIMATE_GROUPS: Final[dict[str, str]] = {
    "hot_semi_arid": "arid",
    "cold_semi_arid": "cold_arid",
    "subpolar": "arctic",
}
# (lowest, span) of each band's reach in pixels; a uniform noise picks within the span.
LAND_COAST: Final[tuple[int, int]] = (1, 4)
LAND_TRANSITION: Final[tuple[int, int]] = (4, 7)
WATER_COAST: Final[tuple[int, int]] = (2, 4)
WATER_SHELF: Final[tuple[int, int]] = (5, 5)
BORDER: Final[tuple[int, int]] = (3, 6)  # in half pixels: 1.5-4.5
RIVER: Final[tuple[int, int]] = (0, 3)
REACH: Final[int] = 16
BAND_PERIOD: Final[int] = 16
FAMILY_PERIOD: Final[int] = 24
LEVEL_PERIOD: Final[int] = 8
INTERIOR: Final[int] = 6
PERMILLE: Final[int] = 1000
CDF_SIZE: Final[int] = 512


@cache
def quantiles(period: int, octaves: int) -> NDArray[np.int64]:
    """Fixed 1000-quantile table of the noise distribution, independent of any window."""
    sample = fractal_noise(
        0, 0, 0, CDF_SIZE, CDF_SIZE, period=period, octaves=octaves, persistence_permille=500
    )
    ordered = np.sort(sample.ravel())
    return ordered[(np.arange(1, PERMILLE) * ordered.size) // PERMILLE]


@dataclass(frozen=True, slots=True, eq=False)
class SlotTables:
    """Per-label values for the labels of one window (indexes of the label raster)."""

    water: NDArray[np.bool_]
    coast_slot: NDArray[np.int64]
    topography: NDArray[np.int64]
    vegetation: NDArray[np.int64]
    climate: NDArray[np.int64]
    level_one: NDArray[np.int64]
    level_two: NDArray[np.int64]
    materials: NDArray[np.int64]


@cache
def slot_remap() -> NDArray[np.int64]:
    """Row ``n``: the slot written in place of each slot 0-15 for a biome of ``n`` materials."""
    table = np.tile(np.arange(SLOTS, dtype=np.int64), (SLOTS + 1, 1))
    table[0] = 0
    for count in range(1, SLOTS):
        for slot in range(count, SLOTS):
            level = min(VARIATION + (slot - VARIATION) % LEVELS, count - 1)
            table[count, slot] = level if slot >= VARIATION and level >= VARIATION else 0
    return table


def synthesize(  # noqa: PLR0913 - the rules read labels, coast, rivers, tables and noise.
    labels: NDArray[np.int32],
    land: NDArray[np.bool_],
    rivers: NDArray[np.bool_],
    tables: SlotTables,
    *,
    seed: int,
    origin: tuple[int, int],
    core: tuple[slice, slice] | None = None,
) -> NDArray[np.uint8]:
    """Material slot per pixel of a window whose top-left decal pixel is ``origin``.

    With ``core`` (row and column slices of the window) only those pixels are computed and
    returned: the distance fields look at the whole window, the noise and the rules run on
    the core. The result equals the same slice of the whole window's slots.
    """
    rows, columns_slice = core if core is not None else (slice(None), slice(None))
    row0, row1, _ = rows.indices(int(labels.shape[0]))
    column0, column1, _ = columns_slice.indices(int(labels.shape[1]))
    streams = ("slot_coast", "slot_shelf", "slot_border", "slot_family", "slot_level")
    columns = (
        tables.coast_slot,
        tables.topography,
        tables.vegetation,
        tables.climate,
        tables.level_one,
        tables.level_two,
        tables.materials,
    )
    return _native.synthesize_slots(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(land, dtype=np.bool_),
        np.ascontiguousarray(rivers, dtype=np.bool_),
        [np.ascontiguousarray(column, dtype=np.int64) for column in columns],
        np.ascontiguousarray(tables.water, dtype=np.bool_),
        [derive_seed(seed, stream) for stream in streams],
        [BAND_PERIOD, FAMILY_PERIOD, LEVEL_PERIOD],
        [quantiles(period, 2) for period in (BAND_PERIOD, FAMILY_PERIOD, LEVEL_PERIOD)],
        origin[0],
        origin[1],
        np.ascontiguousarray(slot_remap(), dtype=np.int64).reshape(-1),
        (row0, row1 - row0, column0, column1 - column0),
    )


def level_counts(
    materials: NDArray[np.integer], labels: NDArray[np.int32], group: NDArray[np.int64], groups: int
) -> NDArray[np.int64]:
    """Count variation levels in location interiors per label group (-1 = ignore).

    ``materials`` is a decal material layer and ``labels`` its location raster crop at
    half resolution. A pixel is interior when the labels ``INTERIOR`` pixels away in all
    four directions are the same.
    """
    full = np.repeat(np.repeat(labels, 2, axis=0), 2, axis=1)
    keep = np.zeros(full.shape, dtype=bool)
    d = INTERIOR
    keep[d:-d, d:-d] = (
        (full[d:-d, d:-d] == full[: -2 * d, d:-d])
        & (full[d:-d, d:-d] == full[2 * d :, d:-d])
        & (full[d:-d, d:-d] == full[d:-d, : -2 * d])
        & (full[d:-d, d:-d] == full[d:-d, 2 * d :])
    )
    variation = (materials >= VARIATION) & (materials < VARIATION + 2 * LEVELS)
    keep &= variation
    owner = group[full[keep]]
    level = (materials[keep].astype(np.int64) - VARIATION) % LEVELS
    valid = owner >= 0
    counts = np.bincount(owner[valid] * LEVELS + level[valid], minlength=groups * LEVELS)
    return counts.reshape(groups, LEVELS).astype(np.int64)
