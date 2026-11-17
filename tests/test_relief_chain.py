"""The native chain retains NumPy's signed arithmetic and blurred slope."""

# pyright: reportAny=false
from __future__ import annotations

import numpy as np
import pytest

from rnw import _native, relief
from rnw.noise import NOISE_SCALE
from tests.reference.relief_chain import chain


@pytest.mark.parametrize("shape", [(1, 1), (1, 65), (65, 1), (5, 7), (83, 127)])
@pytest.mark.parametrize("extreme", [False, True])
def test_chain_matches_original_arithmetic(shape: tuple[int, int], *, extreme: bool) -> None:
    rng = np.random.default_rng(835)
    fields = [rng.integers(-32768, 32768, shape[::-1], dtype=np.int64).T for _ in range(3)]
    if extreme:
        for field in fields:
            field.flat[::3] = np.iinfo(np.int64).min
            field.flat[1::3] = np.iinfo(np.int64).max
    axis, wander, width = fields
    for core, flank in [(1, 1), (83, 260), (130, 390)]:
        with np.errstate(invalid="ignore", over="ignore"):
            expected = chain(axis, wander, width, core, flank)
        actual = _native.relief_chain(
            np.ascontiguousarray(axis),
            np.ascontiguousarray(wander),
            np.ascontiguousarray(width),
            (
                relief.SLOPE_REACH,
                relief.SLOPE_BLUR,
                relief.SLOPE_FLOOR,
                *relief.SLOPE_FADE,
                relief.AXIS_WANDER,
                NOISE_SCALE,
                core,
                flank,
            ),
        )
        assert np.array_equal(actual, expected)


def test_ridge_accumulator_owns_its_state_and_finishes_once() -> None:
    ridges = _native.RidgeAccumulator(2, 3, NOISE_SCALE, relief.RIDGE_GAIN)
    noise = np.full((2, 3), 1000, dtype=np.int64)
    ridges.add(noise, 1000)
    noise[:] = 0
    result = ridges.finish(1000)
    expected = (NOISE_SCALE - 1000) ** 2 // NOISE_SCALE * 1000 // NOISE_SCALE
    assert np.all(result == expected)
    with pytest.raises(ValueError, match="finished"):
        ridges.add(noise, 1000)
    with pytest.raises(ValueError, match="finished"):
        _ = ridges.finish(1000)
