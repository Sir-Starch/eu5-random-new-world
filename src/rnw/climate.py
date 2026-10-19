"""Zonal-wind rainfall on a cylindrical raster (game-independent).

Air picks up moisture over the sea (fully over open ocean, little over a narrow strait)
and is carried along rows by the prevailing wind:
easterly trades below 30 degrees, westerlies between 30 and 60, polar easterlies above.
Over land it loses a fixed share per pixel plus an orographic share proportional to the
rise of the terrain, so windward slopes are wet and the lee of a range is dry (rain
shadow). The loss is the rainfall. Rows wrap around, as the map does. All arithmetic is
integer; equal inputs give equal outputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

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
