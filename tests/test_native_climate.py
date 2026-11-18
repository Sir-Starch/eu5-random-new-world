"""Integer wind transport keeps the original scans, including wrap, poles and overflow."""

# NumPy scalar and indexing stubs are broad.
# pyright: reportAny=false, reportPrivateUsage=false
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw import _native, climate
from rnw.eu5_biomes import RAIN, SEASONAL
from rnw.progress import Cancelled, Progress, active
from tests.reference import climate as reference


@pytest.mark.parametrize("shape", [(1, 1), (1, 23), (31, 1), (19, 37), (131, 17)])
@pytest.mark.parametrize("strip", [1, 7, 128])
def test_wind_strips_equal_both_original_climate_models(
    shape: tuple[int, int], strip: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(climate, "WIND_STRIP", strip)
    rng = np.random.default_rng(7341)
    height = rng.integers(0, 65000, shape, dtype=np.int64)
    latitude = rng.integers(0, 1000, shape[0], dtype=np.int64)
    for density in (0.0, 0.4, 1.0):
        sea = rng.random(shape) < density
        for equator in (-5, shape[0] // 2, shape[0] + 5):
            found = climate.seasonal_rainfall(sea, height, latitude, equator, SEASONAL)
            expected = reference.seasonal_rainfall(sea, height, latitude, equator, SEASONAL)
            assert all(np.array_equal(a, b) for a, b in zip(found, expected, strict=True))
        assert np.array_equal(
            climate.rainfall(sea, height, latitude, RAIN),
            reference.rainfall(sea, height, latitude, RAIN),
        )


@pytest.mark.parametrize("rates", [(1, 1, 1), (3, 7, 11), (-3, -5, -7), (0, 0, 0)])
def test_wind_arithmetic_keeps_signed_int64_wrapping_and_floor_division(
    rates: tuple[int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(climate, "WIND_STRIP", 3)
    rng = np.random.default_rng(9001)
    shape = (7, 11)
    sea = rng.random(shape) < 0.4

    def integers(dims: tuple[int, ...]) -> np.ndarray:
        return rng.integers(-(2**63), 2**63 - 1, dims, dtype=np.int64)

    height = integers(shape)
    effective = np.zeros((2, shape[0]), dtype=np.int64)
    fast, slow = climate._Sea(sea, effective, SEASONAL), reference._Sea(sea, effective, SEASONAL)
    for name in ("capacity", "cold", "warm"):
        values = integers((2, shape[0]))
        setattr(fast, name, values)
        setattr(slow, name, values)
    # Even overlapping flags keep the original east-current precedence.
    for name in ("off_west", "off_east"):
        flags = rng.random(shape) < 0.7
        setattr(fast, name, flags)
        setattr(slow, name, flags)
    efficiency, west, east, inflow = (integers((2, shape[0])) for _ in range(4))
    total = integers((2, *shape))
    expected = total.copy()
    settings = replace(SEASONAL, decay_px=rates[0], recharge_px=rates[1], lift_units=rates[2])
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        climate._zonal(
            fast, height, efficiency, weights=(west, east), settings=settings, total=total
        )
        reference._zonal(
            slow, height, efficiency, weights=(west, east), settings=settings, total=expected
        )
        assert np.array_equal(total, expected)
        climate._inflow(
            fast, height, efficiency, weight=inflow, equator=3, settings=settings, total=total
        )
        reference._inflow(
            slow, height, efficiency, weight=inflow, equator=3, settings=settings, total=expected
        )
        assert np.array_equal(total, expected)
        settings_old = replace(RAIN, decay_px=rates[0], recharge_px=rates[1], lift_units=rates[2])
        assert np.array_equal(
            climate._scan(sea, height, settings_old), reference._scan(sea, height, settings_old)
        )


@pytest.mark.parametrize("limit", [0, 1, 17, 1000])
def test_sea_runs_keep_seam_laps_and_strided_input(limit: int) -> None:
    sea = np.array([[True, True, False, True], [True] * 4, [False] * 4])[:, ::-1]
    assert np.array_equal(climate._sea_run(sea, limit), reference._sea_run(sea, limit))


def test_cancellation_is_observed_after_a_completed_native_strip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(climate, "WIND_STRIP", 1)
    job = Progress()
    original = _native.climate_scan
    calls: list[int] = []

    def scan(
        sea: np.ndarray, height: np.ndarray, rates: tuple[int, int, int], laps: int
    ) -> np.ndarray:
        found = original(sea, height, rates, laps)
        calls.append(sea.shape[0])
        job.cancel()
        return found

    monkeypatch.setattr(_native, "climate_scan", scan)
    with active(job), pytest.raises(Cancelled):
        _ = climate._scan(np.zeros((4, 9), dtype=bool), np.zeros((4, 9), dtype=np.int64), RAIN)
    assert calls == [1]
