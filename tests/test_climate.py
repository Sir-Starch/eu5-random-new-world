"""Seasonal rainfall on a synthetic world (``climate.seasonal_rainfall``)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.climate import piecewise, seasonal_rainfall
from rnw.eu5_biomes import SEASONAL


def _world() -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """One continent from 40 degrees north to 40 south in an ocean, the equator at row 400."""
    rows, columns, equator = 1000, 1200, 400
    latitude = np.abs(np.arange(rows, dtype=np.int64) - equator)  # a tenth of a degree a row
    sea = np.ones((rows, columns), dtype=bool)
    sea[equator - 400 : equator + 400, 300:900] = False
    height = np.where(sea, 0, 6000).astype(np.int64)
    return sea, height, latitude, equator


def test_piecewise_is_the_polyline_and_flat_beyond_it() -> None:
    knots = ((0, 0), (100, 1000), (200, 400))
    values = np.array([-5, 0, 50, 100, 150, 200, 900], dtype=np.int64)
    assert piecewise(values, knots).tolist() == [0, 0, 500, 1000, 700, 400, 400]


def test_seasons_put_the_deserts_on_the_west_of_the_subtropics_and_rain_at_the_equator() -> None:
    sea, height, latitude, equator = _world()
    summer, winter = seasonal_rainfall(sea, height, latitude, equator, SEASONAL)
    again = seasonal_rainfall(sea, height, latitude, equator, SEASONAL)
    assert np.array_equal(summer, again[0])
    assert np.array_equal(winter, again[1])
    year = summer + winter
    north = equator - 220  # 22 degrees north, under the subtropical high
    west, east = year[north, 320:360].mean(), year[north, 840:880].mean()
    assert west < east  # the trades bring the sea's water to the east coast
    assert year[equator, 560:640].mean() > 2 * year[north, 560:640].mean()
    # The belts move poleward in summer: at 12 degrees the summer is the rainy season.
    assert summer[equator - 120, 400:800].mean() > winter[equator - 120, 400:800].mean()
