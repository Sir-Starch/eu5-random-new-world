"""Pure NumPy terrain material slots: the specification of the Rust kernel.

Moved from ``rnw.eu5_slots`` when ``synthesize`` became native
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_slots import (
    BAND_PERIOD,
    BORDER,
    CLIMATE_BORDER,
    COAST_TRANSITION,
    FAMILY_PERIOD,
    LAND_COAST,
    LAND_TRANSITION,
    LEVEL_PERIOD,
    LEVELS,
    NO_MATERIAL,
    PERMILLE,
    REACH,
    RIVER,
    SLOTS,
    TOPOGRAPHY_BORDER,
    VARIATION,
    VEGETATION_BORDER,
    WATER_COAST,
    WATER_EDGE,
    WATER_SHELF,
    SlotTables,
    quantiles,
    slot_remap,
)
from rnw.noise import fractal_noise
from rnw.rng import derive_seed
from rnw.topology import distance_from, nearest_label

if TYPE_CHECKING:
    from numpy.typing import NDArray


def uniform_noise(
    seed: int, stream: str, *, origin: tuple[int, int], shape: tuple[int, int], period: int
) -> NDArray[np.int64]:
    """Noise remapped to a near-uniform permille in [0, 1000); ``origin`` is (x, y)."""
    x0, y0 = origin
    raw = fractal_noise(
        derive_seed(seed, stream),
        x0,
        y0,
        shape[1],
        shape[0],
        period=period,
        octaves=2,
        persistence_permille=500,
    )
    return np.searchsorted(quantiles(period, 2), raw, side="right").astype(np.int64)


def _border(attribute: NDArray[np.int64]) -> NDArray[np.bool_]:
    """Land pixels with a 4-neighbouring land pixel of a different attribute (-1 = water)."""
    out = np.zeros(attribute.shape, dtype=bool)
    for a, b, first, second in (
        (attribute[:-1], attribute[1:], (slice(None, -1),), (slice(1, None),)),
        (attribute[:, :-1], attribute[:, 1:], (slice(None), slice(None, -1)),
         (slice(None), slice(1, None))),
    ):  # fmt: skip
        differ = (a != b) & (a >= 0) & (b >= 0)
        out[first] |= differ
        out[second] |= differ
    return out


def _within(
    distance: NDArray[np.int32], reach: tuple[int, int], u: NDArray[np.int64]
) -> NDArray[np.bool_]:
    lowest, span = reach
    return distance.astype(np.int64) * PERMILLE <= lowest * PERMILLE + u * span


def synthesize(  # noqa: PLR0913 - the rules read labels, coast, rivers, tables and noise.
    labels: NDArray[np.int32],
    land: NDArray[np.bool_],
    rivers: NDArray[np.bool_],
    tables: SlotTables,
    *,
    seed: int,
    origin: tuple[int, int],
) -> NDArray[np.int64]:
    """Material slot per pixel of a window whose top-left decal pixel is ``origin``."""
    shape = (int(labels.shape[0]), int(labels.shape[1]))
    label_land = ~tables.water[labels]
    near = nearest_label(labels, label_land, REACH)
    owner = np.where(near >= 0, near, labels)
    inland = distance_from(~land, REACH, octagonal=True)
    offshore = distance_from(land, REACH, octagonal=True)
    u_coast = uniform_noise(seed, "slot_coast", origin=origin, shape=shape, period=BAND_PERIOD)
    u_shelf = uniform_noise(seed, "slot_shelf", origin=origin, shape=shape, period=BAND_PERIOD)
    u_border = uniform_noise(seed, "slot_border", origin=origin, shape=shape, period=BAND_PERIOD)
    out = np.full(shape, NO_MATERIAL, dtype=np.int64)
    coast_slot = tables.coast_slot[owner]
    water = ~land
    out[water & _within(offshore, WATER_SHELF, u_shelf)] = WATER_EDGE
    water_coast = water & _within(offshore, WATER_COAST, u_coast)
    out[water_coast] = coast_slot[water_coast]
    coast = land & _within(inland, LAND_COAST, u_coast)
    out[coast] = coast_slot[coast]
    free = land & ~coast
    transition = free & _within(inland, LAND_TRANSITION, u_shelf)
    out[transition] = COAST_TRANSITION
    free &= ~transition
    if np.any(rivers):
        river = free & _within(distance_from(rivers, REACH, octagonal=True), RIVER, u_border)
        out[river] = WATER_EDGE
        free &= ~river
    for table, slot in (
        (tables.topography, TOPOGRAPHY_BORDER),
        (tables.vegetation, VEGETATION_BORDER),
        (tables.climate, CLIMATE_BORDER),
    ):
        attribute = np.where(label_land, table[labels], -1)
        distance = distance_from(_border(attribute), REACH, octagonal=True)
        band = free & _within(distance * 2, BORDER, u_border)
        out[band] = slot
        free &= ~band
    family = (
        uniform_noise(seed, "slot_family", origin=origin, shape=shape, period=FAMILY_PERIOD)
        >= PERMILLE // 2
    )
    level_u = uniform_noise(seed, "slot_level", origin=origin, shape=shape, period=LEVEL_PERIOD)
    level = np.where(
        level_u < tables.level_one[owner],
        0,
        np.where(level_u < tables.level_one[owner] + tables.level_two[owner], 1, 2),
    )
    out[free] = (VARIATION + LEVELS * family + level)[free]
    count = np.clip(tables.materials[owner], 0, SLOTS)
    listed = land & (out < SLOTS)
    out[listed] = slot_remap()[count[listed], out[listed]]
    return out
