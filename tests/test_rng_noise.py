"""The RNG and noise are explicitly specified and platform independent."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.noise import fractal_noise, value_noise
from rnw.rng import SeedRangeError, SplitMix64, derive_seed, hash_grid, hash_point


def test_splitmix64_matches_reference_vectors() -> None:
    """Seed 1234567 matches Rosetta Code's SplitMix64 task; seed 0 is a regression vector."""
    reference = SplitMix64(1234567)
    assert [reference.next_u64() for _ in range(5)] == [
        6457827717110365317,
        3203168211198807973,
        9817491932198370423,
        4593380528125082431,
        16408922859458223821,
    ]
    zero = SplitMix64(0)
    assert [zero.next_u64() for _ in range(3)] == [
        0xE220A8397B1DCDAF,
        0x6E789E6AA1B965F4,
        0x06C45D188009454F,
    ]


def test_bounded_draws_are_in_range_and_repeatable() -> None:
    """Rejection sampling stays in range and depends only on the seed."""
    first = SplitMix64(9)
    second = SplitMix64(9)
    draws = [first.below(7) for _ in range(200)]
    assert draws == [second.below(7) for _ in range(200)]
    assert set(draws) == set(range(7))


def test_streams_and_seed_range() -> None:
    """Named streams are distinct and seeds must be unsigned 64-bit."""
    assert derive_seed(1, "a") == derive_seed(1, "a")
    assert derive_seed(1, "a") != derive_seed(1, "b")
    assert derive_seed(1, "a") != derive_seed(2, "a")
    with pytest.raises(SeedRangeError):
        _ = SplitMix64(1 << 64)
    with pytest.raises(SeedRangeError):
        _ = derive_seed(-1, "a")


def test_vectorized_hash_equals_python_reference() -> None:
    """NumPy wrapping arithmetic equals exact 64-bit Python arithmetic."""
    xs = np.array([0, 1, 4095, 1 << 40], dtype=np.int64)
    ys = np.array([0, 7, 8191, 3], dtype=np.int64)
    key = 0xFEED_FACE_CAFE_BEEF
    values = hash_grid(key, xs, ys).tolist()
    assert values == [hash_point(key, x, y) for x, y in zip(xs.tolist(), ys.tolist(), strict=True)]


def test_noise_window_equals_crop_of_larger_field() -> None:
    """A field for a sub-window has exactly the pixels of the larger field."""
    big = fractal_noise(5, 0, 0, 64, 48, period=16, octaves=3, persistence_permille=500)
    small = fractal_noise(5, 5, 10, 35, 20, period=16, octaves=3, persistence_permille=500)
    assert np.array_equal(big[10:30, 5:40], small)
    assert int(big.min()) >= -32768
    assert int(big.max()) <= 32767


def test_noise_depends_on_key_and_is_smooth() -> None:
    """Different keys differ; neighbouring pixels change by bounded steps."""
    first = value_noise(1, 0, 0, 32, 32, period=8)
    assert not np.array_equal(first, value_noise(2, 0, 0, 32, 32, period=8))
    assert int(np.abs(np.diff(first, axis=1)).max()) < 32768


@pytest.mark.parametrize("period", [1600, 3600, 4096])
def test_continent_noise_resolves_pixels_instead_of_large_stair_steps(period: int) -> None:
    """The cubic interpolant's derivative bounds pixel changes at continent scale.

    Its largest slope is 1.5 times the corner difference / period. Four units
    allow integer rounding of fractions and final samples. The old 8-bit
    fractions exceeded this bound by repeatedly holding then jumping.
    """
    field = value_noise(1234, 1000, 2000, 1600, 3, period=period)
    bound = int(np.ceil(1.5 * 65535 / period)) + 4
    assert int(np.abs(np.diff(field, axis=1)).max()) <= bound
    assert np.count_nonzero(np.diff(field[0]) == 0) < field.shape[1] // 4
