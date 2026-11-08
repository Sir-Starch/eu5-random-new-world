"""Whole-raster cell sums and coasts: the specification of the strip-by-strip ``rnw.newworld``.

Moved from ``rnw.newworld`` (``derive_world``, ``_land``, ``_coasts``) when they went strip
by strip (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.fields import warped_noise
from rnw.gulfs import carve_inland_seas
from rnw.isthmuses import raise_isthmuses
from rnw.lakes import carve_lakes
from rnw.newworld import (
    COAST_WARP_PERMILLE,
    EDGE_RAMP_MARGINS,
    EDGE_SHIFT_PERIOD_PERMILLE,
    EDGE_SHIFT_RAMPS,
    EDGE_WATER_PERMILLE,
    MAX_STRAITS,
    OUTSIDE,
    PERMILLE,
    SEA_SCALE_MAX_PX,
    SEA_SCALE_MIN_PX,
    _field,  # pyright: ignore[reportPrivateUsage]
    _ocean,  # pyright: ignore[reportPrivateUsage]
    open_sea,
    stray_strait,
)
from rnw.noise import NOISE_SCALE
from rnw.rng import derive_seed
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings


def _weighted(
    owner: NDArray[np.int32], weights: NDArray[np.int64] | NDArray[np.int32], count: int
) -> NDArray[np.int64]:
    sums = cast("NDArray[np.float64]", np.bincount(owner, weights=weights, minlength=count))
    return sums.astype(np.int64)


def cell_sums(
    labels: NDArray[np.int32], elevation: NDArray[np.int32], count: int
) -> tuple[NDArray[np.int64], ...]:
    """Pixels, row sum, column sum, elevation sum and elevation square sum per cell."""
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    owner = flat[inside]
    width = labels.shape[1]
    pixels = np.bincount(owner, minlength=count).astype(np.int64)
    rows = _weighted(owner, inside // width, count)
    columns = _weighted(owner, inside % width, count)
    values = elevation.ravel()[inside].astype(np.int64)
    return (
        pixels,
        rows,
        columns,
        _weighted(owner, values, count),
        _weighted(owner, values * values, count),
    )


def _with_water_band(
    domain: NDArray[np.bool_], sources: NDArray[np.bool_], settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NewWorldSettings]:
    """No land within EDGE_WATER_PERMILLE of the canvas's width of its boundary with the game's map.

    Returns the sources with the band, and the settings whose land share the narrower interior
    holds as much land as the settings asked for.
    """
    margin = settings.coast_margin_px
    band_px = domain.shape[1] * EDGE_WATER_PERMILLE // PERMILLE
    if band_px <= margin:
        return sources, settings
    before = np.count_nonzero(domain & (distance_from(sources, margin, octagonal=True) >= margin))
    banded = sources | (distance_from(sources, band_px, octagonal=True) < band_px)
    after = np.count_nonzero(domain & (distance_from(banded, margin, octagonal=True) >= margin))
    share = min(PERMILLE, -(-settings.land_permille * int(before) // max(1, int(after))))
    return banded, replace(settings, land_permille=share)


def land_model(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Return land, ocean, lake masks and the shaped elevation."""
    margin = settings.coast_margin_px
    ramp = EDGE_RAMP_MARGINS * margin
    shift_px = EDGE_SHIFT_RAMPS * ramp
    shift_period = max(8, ramp * EDGE_SHIFT_PERIOD_PERMILLE // PERMILLE)
    sources = ~domain
    sources[:, [0, -1]] = True
    guard = sources.copy()
    sources, settings = _with_water_band(domain, sources, settings)
    guard = sources.copy()
    relief = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
        warp_permille=COAST_WARP_PERMILLE,
    )
    opening = min(domain.shape[1], max(8 * settings.location_px, 4 * ramp + 1))
    if opening < domain.shape[1]:
        for edge, sample in (
            (0, min(domain.shape[0] - 1, 2 * ramp)),
            (domain.shape[0] - 1, max(0, domain.shape[0] - 1 - 2 * ramp)),
        ):
            valid = domain[edge] & domain[sample]
            sources[edge] = True
            if np.any(valid):
                scores = np.where(valid, relief[sample], -10 * NOISE_SCALE).astype(np.int64)
                totals = np.convolve(scores, np.ones(opening, dtype=np.int64), mode="valid")
                start = int(np.argmax(totals))
                sources[edge, start : start + opening] = ~domain[edge, start : start + opening]
        guard = sources.copy()
    wobble = _field(
        seed,
        "new_world_edge",
        shape=domain.shape,
        period=max(8, ramp // 2),
        octaves=3,
        persistence_permille=500,
    )
    shift = warped_noise(
        derive_seed(seed, "new_world_edge_shift"),
        (int(domain.shape[0]), int(domain.shape[1])),
        step=8,
        period=shift_period,
        octaves=4,
        warp_px=shift_period // 4,
    )
    # Warped noise mostly stays within +-0.4 of NOISE_SCALE; stretch it over the shift.
    inland = shift_px * np.clip(NOISE_SCALE // 2 + shift * 5 // 4, 0, NOISE_SCALE) // NOISE_SCALE
    offset = wobble.astype(np.int64) * ramp // (3 * NOISE_SCALE) - inland
    open_shore = distance_from(open_sea(domain), margin, octagonal=True) < margin
    # A sea cut off from open water (around a protected islet) gets a strait: its shortest
    # path to open water joins the guard and the coasts are drawn again, so the strait has
    # the same ragged shores as every other coast instead of a straight canal [V-EXEC C64].
    land, shore, elevation = _coasts(domain, guard, relief, offset, ramp=ramp, settings=settings)
    for _ in range(MAX_STRAITS):
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        guard |= path
        land, shore, elevation = _coasts(
            domain, guard, relief, offset, ramp=ramp, settings=settings
        )
    # The isthmus, inland sea and lake stages work on windows of the whole raster, not on
    # strips; this specification runs the same functions in the same order.
    scale = max(SEA_SCALE_MIN_PX, min(settings.feature_px, SEA_SCALE_MAX_PX))
    _, ocean_now = _ocean(domain, land, shore)
    land |= raise_isthmuses(land, ocean_now, domain & ~shore, seed, scale_px=scale)
    _, ocean_now = _ocean(domain, land, shore)
    land &= ~carve_inland_seas(land, ocean_now, seed, scale_px=scale)
    land &= ~carve_lakes(
        land, seed, smallest=settings.min_lake_px, largest=settings.max_lake_px * 9 // 10
    )
    parts = label_components(land.astype(np.int32))
    land &= np.bincount(parts.ravel())[parts] >= settings.min_island_px
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    ocean_parts = np.unique(parts[water & shore])
    ocean = water & np.isin(parts, ocean_parts)
    enclosed = water & ~ocean
    size = np.bincount(parts.ravel())[parts]
    small = enclosed & (size < settings.min_lake_px)
    inland = enclosed & (
        size
        >= max(
            settings.max_lake_px + 1,
            settings.min_lake_px,
            4 * max(settings.sea_zone_px**2, settings.min_sea_cell_px),
        )
    )
    return land | small, ocean | inland, enclosed & ~small & ~inland, elevation


def _coasts(  # noqa: PLR0913 - the coast model needs the guard, both fields and the ramp.
    domain: NDArray[np.bool_],
    guard: NDArray[np.bool_],
    relief: NDArray[np.int32],
    offset: NDArray[np.int64],
    *,
    ramp: int,
    settings: NewWorldSettings,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Lower the relief over a ramp from the guard and keep the land budget.

    Returns land, shore (no land within a coast margin of the guard) and the elevation.
    """
    # The cap must exceed every reach, or the wobble would dent the interior too.
    edge = distance_from(guard, ramp - int(offset.min()) + 2, octagonal=True)
    reach = edge.astype(np.int64) + offset
    penalty = (ramp - reach) * NOISE_SCALE * 3 // ramp
    # No land in slivers of the domain too thin to hold a full ramp.
    opened = distance_from(edge >= ramp, ramp + 1, octagonal=True) <= ramp
    penalty = np.where(opened, penalty, 3 * NOISE_SCALE)
    shore = edge < settings.coast_margin_px
    elevation = (relief - np.maximum(0, penalty)).astype(np.int32)
    interior = domain & ~shore
    values = elevation[interior]
    keep = values.size * settings.land_permille // PERMILLE
    threshold = np.partition(values, values.size - keep)[values.size - keep]
    return interior & (elevation >= threshold), shore, elevation
