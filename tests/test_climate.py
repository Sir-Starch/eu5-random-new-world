"""Seasonal rainfall on a synthetic world (``climate.seasonal_rainfall``)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.climate import piecewise, seasonal_rainfall
from rnw.eu5_biomes import (
    CLIMATE_SAMPLE_STEP,
    CLIMATE_STEP,
    SEASONAL,
    ClimateGrid,
    _climate_training,  # pyright: ignore[reportPrivateUsage]
    climate_samples,
)


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


def test_climate_training_counts_patches_and_preserves_unsampled_pairs() -> None:
    step = CLIMATE_SAMPLE_STEP
    labels = np.zeros((step * 2, step * 4), dtype=np.int32)
    labels[:, step * 2] = 1  # a small location of an already sampled climate
    labels[:, step * 2 + 1 : step * 3] = 2  # a different pair, sampled on the grid
    labels[:, step * 3 :] = 8  # a location whose class is excluded
    labels[0, 0:2] = (3, 4)  # a rare pair, neither donor on the grid
    labels[0, 2] = 4
    labels[step // 2, step * 3 + step // 2] = -1
    height = np.full(labels.shape, 6000, dtype=np.uint16)
    height[step // 2, step // 2] = 7000
    zero = np.zeros(
        (labels.shape[0] // CLIMATE_STEP, labels.shape[1] // CLIMATE_STEP), dtype=np.int64
    )
    grid = ClimateGrid(zero, zero, zero, winter=zero)
    samples = climate_samples(grid, labels, height)
    centres = np.full((5, samples.features.shape[1]), -1, dtype=np.int64)
    centres[4] = -2
    train, pairs = _climate_training(
        samples,
        centres,
        np.arange(len(centres), dtype=np.int64),
        np.array([0, 0, 1, 2, 2], dtype=np.int64),
        np.array([step * step * 4, step * 2, step * step, 1, 2], dtype=np.int64),
    )
    assert pairs.tolist() == [0, 0, 1, 0, 0, 1, 2]
    assert train[:-1, 2].tolist() == [7000, 6000, 6000, 6000, 6000, 6000]
    assert np.array_equal(train[-1], centres[4])
