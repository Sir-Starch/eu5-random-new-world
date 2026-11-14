"""Zonal-wind rainfall on a cylindrical raster (game-independent).

Air picks up moisture over the sea (fully over open ocean, little over a narrow strait)
and is carried along rows by the prevailing wind:
easterly trades below 30 degrees, westerlies between 30 and 60, polar easterlies above.
Over land it loses a fixed share per pixel plus an orographic share proportional to the
rise of the terrain, so windward slopes are wet and the lee of a range is dry (rain
shadow). The loss is the rainfall. Rows wrap around, as the map does. All arithmetic is
integer; equal inputs give equal outputs.

``seasonal_rainfall`` (epoch 64, ``epoch.OPEN_CLIMATE``) adds what the zonal scan lacks and the
game's climates follow: the belts move poleward in summer and back in winter; the air holds less
water the colder its latitude; it rains readily under the equatorial trough and the storm tracks
and hardly under the subtropical highs; summer air flows in from the seas on the equator side
(the monsoons) and a little in winter; and the sea off a west coast of the subtropics is cold
(an upwelling current) and gives little water, the sea off an east coast warm. Read on the game's
own map, its summer and winter rain let the climate vote find the dry climates of a continent
it did not learn from about twice as often as the yearly zonal rain: 23 % of Africa's, 32 % of
Oceania's (13 % and 10 %) [V-EXEC 2026-11-14].
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Final, final

import numpy as np

from rnw.fields import PERMILLE, box_blur, smoothstep

if TYPE_CHECKING:
    from numpy.typing import NDArray

SATURATED: Final[int] = 1 << 16
LAPS: Final[int] = 2


@dataclass(frozen=True, slots=True)
class RainSettings:
    """Rainfall model constants in grid pixels and height units."""

    decay_px: int
    recharge_px: int
    lift_units: int
    blur_px: int
    relief_blur_px: int


def _scan(
    sea: NDArray[np.bool_], height: NDArray[np.int64], settings: RainSettings
) -> NDArray[np.int64]:
    """Rain for wind blowing towards increasing column index, with wrap-around."""
    rows, columns = sea.shape
    moisture = np.full(rows, SATURATED, dtype=np.int64)
    previous = height[:, -1].copy()
    rain = np.zeros((rows, columns), dtype=np.int64)
    for lap in range(LAPS):
        for column in range(columns):
            here = height[:, column]
            rise = np.maximum(0, here - previous)
            loss = moisture // settings.decay_px + moisture * rise // settings.lift_units
            loss = np.minimum(loss, moisture)
            ocean = sea[:, column]
            recharged = moisture + (SATURATED - moisture) // settings.recharge_px
            moisture = np.where(ocean, recharged, moisture - loss)
            if lap == LAPS - 1:
                rain[:, column] = np.where(ocean, 0, loss)
            previous = here
    return rain


def westerly_weight(latitude_tenths: NDArray[np.int64]) -> NDArray[np.int64]:
    """Permille share of westerly wind per row from absolute latitude in tenths of a degree."""
    return (
        smoothstep(latitude_tenths, 250, 350)
        * (PERMILLE - smoothstep(latitude_tenths, 550, 650))
        // PERMILLE
    )


def rainfall(
    sea: NDArray[np.bool_],
    height: NDArray[np.int64],
    latitude_tenths: NDArray[np.int64],
    settings: RainSettings,
) -> NDArray[np.int64]:
    """Blurred rainfall index per pixel; ``latitude_tenths`` is absolute latitude per row.

    Orographic lift uses a smoothed height so that only ranges, not small-scale
    roughness, take moisture out of the air.
    """
    height = box_blur(height, settings.relief_blur_px)
    west = _scan(sea, height, settings)
    east = _scan(sea[:, ::-1], height[:, ::-1], settings)[:, ::-1]
    weight = westerly_weight(latitude_tenths)[:, np.newaxis]
    rain = (west * weight + east * (PERMILLE - weight)) // PERMILLE
    return box_blur(rain, settings.blur_px)


Knots = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class SeasonalSettings:
    """``seasonal_rainfall`` constants: grid pixels, height units, tenths of a degree of the
    effective latitude (moved poleward by ``shift`` in summer) and permille."""

    shift: int
    decay_px: int
    recharge_px: int
    lift_units: int
    blur_px: int
    relief_blur_px: int
    current_px: int
    capacity: Knots  # water the air holds, permille of SATURATED
    efficiency: Knots  # share of the air's loss that falls as rain
    easterly: Knots  # weights of the winds from the east, the west and the equator side
    westerly: Knots
    summer_inflow: Knots
    winter_inflow: Knots
    cold_current: Knots  # permille of the water a sea off a west coast gives
    warm_current: Knots  # and off an east coast


def piecewise(values: NDArray[np.int64], knots: Knots) -> NDArray[np.int64]:
    """The polyline through ``knots`` (increasing x) at ``values``, flat beyond its ends."""
    out = np.full(values.shape, knots[0][1], dtype=np.int64)
    for (x0, y0), (x1, y1) in pairwise(knots):
        inside = (values >= x0) & (values <= x1)
        out[inside] = y0 + (values[inside] - x0) * (y1 - y0) // (x1 - x0)
    out[values > knots[-1][0]] = knots[-1][1]
    return out


def _sea_run(sea: NDArray[np.bool_], limit: int) -> NDArray[np.int64]:
    """Per sea pixel, its distance along the row (wrapping) from the land behind it, towards
    increasing column, capped at ``limit``; 0 on land."""
    rows, columns = sea.shape
    run = np.full(rows, limit, dtype=np.int64)
    out = np.empty((rows, columns), dtype=np.int64)
    for lap in range(LAPS):
        for column in range(columns):
            run = np.where(sea[:, column], np.minimum(run + 1, limit), 0)
            if lap == LAPS - 1:
                out[:, column] = run
    return out


@final
class _Sea:
    """Where each season's air takes up water: the sea, with its currents."""

    def __init__(
        self, sea: NDArray[np.bool_], effective: NDArray[np.int64], settings: SeasonalSettings
    ) -> None:
        reach = settings.current_px
        from_west = _sea_run(sea, reach)
        from_east = _sea_run(sea[:, ::-1], reach)[:, ::-1]
        # A sea with land close to its east lies off a west coast; one with land close to its
        # west off an east coast.
        self.off_west = (from_east < reach) & (from_east < from_west)
        self.off_east = (from_west < reach) & (from_west <= from_east) & ~self.off_west
        del from_west, from_east
        self.sea = sea
        self.capacity = piecewise(effective, settings.capacity) * SATURATED // PERMILLE
        self.cold = self.capacity * piecewise(effective, settings.cold_current) // PERMILLE
        self.warm = self.capacity * piecewise(effective, settings.warm_current) // PERMILLE

    def column(self, column: int) -> NDArray[np.int64]:
        """The water the sea gives the air in a column, per season and row."""
        out = np.where(self.off_west[:, column], self.cold, self.capacity)
        return np.where(self.off_east[:, column], self.warm, out)

    def row(self, row: int) -> NDArray[np.int64]:
        """The water the sea gives the air in a row, per season and column."""
        out = np.where(self.off_west[row], self.cold[:, row, np.newaxis], 0)
        out = np.where(self.off_east[row], self.warm[:, row, np.newaxis], out)
        plain = ~(self.off_west[row] | self.off_east[row])
        return np.where(plain, self.capacity[:, row, np.newaxis], out)


def _zonal(  # noqa: PLR0913 - the sea, the relief, the rates and the two winds' weights.
    sources: _Sea,
    height: NDArray[np.int64],
    efficiency: NDArray[np.int64],
    *,
    weights: tuple[NDArray[np.int64], NDArray[np.int64]],
    settings: SeasonalSettings,
    total: NDArray[np.int64],
) -> None:
    """Add to ``total`` the rain of the wind towards increasing column (the westerlies), weighed
    by ``weights[0]``, and of the wind towards decreasing column, by ``weights[1]``, in each
    season (leading axis of ``efficiency``, the weights and ``total``); rows wrap around."""
    sea = sources.sea
    columns = int(sea.shape[1])
    last = columns - 1
    moisture = np.stack([sources.column(last), sources.column(0)], axis=1)
    previous = np.stack([height[:, last], height[:, 0]])
    rate = efficiency[:, np.newaxis, :]
    weight = np.stack(weights, axis=1)
    for lap in range(LAPS):
        for step in range(columns):
            back = last - step
            here = np.stack([height[:, step], height[:, back]])
            ocean = np.stack([sea[:, step], sea[:, back]])
            rise = np.maximum(0, here - previous)
            loss = np.minimum(
                moisture // settings.decay_px + moisture * rise // settings.lift_units, moisture
            )
            target = np.stack([sources.column(step), sources.column(back)], axis=1)
            moisture = np.where(
                ocean, moisture + (target - moisture) // settings.recharge_px, moisture - loss
            )
            if lap == LAPS - 1:
                fallen = np.where(ocean, 0, loss * rate // PERMILLE) * weight
                total[:, :, step] += fallen[:, 0]
                total[:, :, back] += fallen[:, 1]
            previous = here


def _inflow(  # noqa: PLR0913 - the sea, the relief, the rates, the weights and the equator.
    sources: _Sea,
    height: NDArray[np.int64],
    efficiency: NDArray[np.int64],
    *,
    weight: NDArray[np.int64],
    equator: int,
    settings: SeasonalSettings,
    total: NDArray[np.int64],
) -> None:
    """Add to ``total`` the rain of the air flowing from the equator towards each pole, weighed
    by ``weight``, in each season."""
    sea = sources.sea
    rows = int(sea.shape[0])
    start = min(max(equator, 0), rows - 1)
    for order in (range(start, -1, -1), range(start, rows)):
        moisture = sources.row(start)
        previous = height[start].copy()
        for row in order:
            here = height[row]
            rise = np.maximum(0, here - previous)
            loss = np.minimum(
                moisture // settings.decay_px + moisture * rise // settings.lift_units, moisture
            )
            moisture = np.where(
                sea[row],
                moisture + (sources.row(row) - moisture) // settings.recharge_px,
                moisture - loss,
            )
            fallen = np.where(sea[row], 0, loss * efficiency[:, row, np.newaxis] // PERMILLE)
            total[:, row] += fallen * weight[:, row, np.newaxis]
            previous = here


def seasonal_rainfall(
    sea: NDArray[np.bool_],
    height: NDArray[np.int64],
    latitude_tenths: NDArray[np.int64],
    equator: int,
    settings: SeasonalSettings,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Summer and winter rainfall indices per pixel (blurred); ``latitude_tenths`` is the
    absolute latitude per row and ``equator`` the row of the equator (it may lie outside).

    Each season moves the belts by ``shift`` (poleward in summer); the rain of the winds from
    the west, the east and the equator side are weighed by the season's effective latitude.
    """
    rows, columns = (int(size) for size in sea.shape)
    shift = np.array([settings.shift, -settings.shift], dtype=np.int64)
    effective = np.maximum(0, latitude_tenths[np.newaxis, :] - shift[:, np.newaxis])
    sources = _Sea(sea, effective, settings)
    efficiency = piecewise(effective, settings.efficiency)
    westerly = piecewise(effective, settings.westerly)
    easterly = piecewise(effective, settings.easterly)
    inflow = np.stack(
        [
            piecewise(effective[0], settings.summer_inflow),
            piecewise(effective[1], settings.winter_inflow),
        ]
    )
    relief = box_blur(height, settings.relief_blur_px)
    total = np.zeros((2, rows, columns), dtype=np.int64)
    _zonal(
        sources, relief, efficiency, weights=(westerly, easterly), settings=settings, total=total
    )
    _inflow(
        sources,
        relief,
        efficiency,
        weight=inflow,
        equator=equator,
        settings=settings,
        total=total,
    )
    del relief, sources
    total //= np.maximum(1, westerly + easterly + inflow)[:, :, np.newaxis]
    return box_blur(total[0], settings.blur_px), box_blur(total[1], settings.blur_px)
