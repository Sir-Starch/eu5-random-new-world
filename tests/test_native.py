"""The Rust kernels equal their pure-Python references bit for bit (ADR 0005)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import fields, lzav, noise, topology
from tests.reference import lzav as reference_lzav
from tests.reference import noise as reference_noise
from tests.reference import topology as reference_topology


def _streams() -> list[bytes]:
    generator = np.random.default_rng(7)
    noise = bytes(generator.integers(0, 256, 3000, dtype=np.uint8))
    runs = bytes(generator.integers(0, 3, 5000, dtype=np.uint8)) + bytes(40_000) + b"\x07" * 77
    shorts = [b"a", b"abcdefgh", bytes(range(20))]
    return [noise, runs, *shorts]


@pytest.mark.parametrize("raw", _streams())
def test_lzav_decoder_equals_the_reference(raw: bytes) -> None:
    """Literal-only and run-length streams decode to the original in both decoders."""
    for stream in (lzav.encode(raw), lzav.encode_literals(raw)):
        size = (
            max(len(raw), lzav.LITERALS_AT_END) if stream == lzav.encode_literals(raw) else len(raw)
        )
        assert lzav.decode(stream, size) == reference_lzav.decode(stream, size)


def test_lzav_decoder_refuses_what_the_reference_refuses() -> None:
    """Wrong formats, wrong sizes and references before the data fail in both."""
    raw = bytes(300)
    stream = lzav.encode(raw)
    for data, size in ((b"\x25\x00", 0), (stream, len(raw) + 1), (stream[:-5], len(raw))):
        with pytest.raises(ValueError):  # noqa: PT011 - both raise a ValueError subclass
            _ = lzav.decode(data, size)
        with pytest.raises((ValueError, IndexError)):
            _ = reference_lzav.decode(data, size)
    assert lzav.LzavError.__mro__[1] is ValueError


WINDOWS = [
    (1, 0, 0, 1, 1, 2),
    (0xDEADBEEF, 0, 0, 64, 48, 16),
    (2**64 - 1, 5, 10, 35, 20, 16),
    (12345, 1000, 2000, 257, 131, 7),
    (99, 3, 4, 100, 3, 1000),
]


@pytest.mark.parametrize("window", WINDOWS)
def test_value_noise_equals_the_reference(window: tuple[int, int, int, int, int, int]) -> None:
    """One octave over a window, including origins off the lattice and huge keys."""
    key, x0, y0, width, height, period = window
    native = noise.value_noise(key, x0, y0, width, height, period=period)
    expected = reference_noise.value_noise(key, x0, y0, width, height, period=period)
    assert native.dtype == np.int64
    assert np.array_equal(native, expected)


@pytest.mark.parametrize("window", WINDOWS)
@pytest.mark.parametrize(("octaves", "persistence"), [(1, 500), (3, 500), (6, 650), (8, 300)])
def test_fractal_noise_equals_the_reference(
    window: tuple[int, int, int, int, int, int], octaves: int, persistence: int
) -> None:
    """Octaves, halving periods (down to the floor of 2) and weights match."""
    key, x0, y0, width, height, period = window
    args = (key, x0, y0, width, height)
    native = noise.fractal_noise(
        *args, period=period, octaves=octaves, persistence_permille=persistence
    )
    expected = reference_noise.fractal_noise(
        *args, period=period, octaves=octaves, persistence_permille=persistence
    )
    assert np.array_equal(native, expected)


def test_noise_windows_refuse_what_the_reference_refuses() -> None:
    """Negative origins and empty windows raise the same error."""
    for call in (noise.value_noise, reference_noise.value_noise):
        for args in ((1, -1, 0, 4, 4), (1, 0, 0, 0, 4), (1, 0, 0, 4, 0)):
            with pytest.raises(ValueError, match="non-negative origin"):
                _ = call(*args, period=4)
        with pytest.raises(ValueError, match="non-negative origin"):
            _ = call(1, 0, 0, 4, 4, period=0)


def _points(count: int, span: int) -> tuple[np.ndarray, np.ndarray]:
    generator = np.random.default_rng(3)
    return (
        generator.integers(-span, span, count, dtype=np.int64),
        generator.integers(-span, span, count, dtype=np.int64),
    )


@pytest.mark.parametrize("span", [50, 100_000, 5_000_000])
def test_noise_at_points_equals_the_reference(span: int) -> None:
    """Negative coordinates floor, shapes survive, huge coordinates wrap alike."""
    xs, ys = _points(4000, span)
    for period in (2, 16, 33, 4096):
        native = fields.value_noise_at(7, xs, ys, period)
        assert np.array_equal(native, reference_noise.value_noise_at(7, xs, ys, period))
    grid_x, grid_y = xs[:3000].reshape(30, 100), ys[:3000].reshape(30, 100)
    for octaves in (1, 2, 5, 7):
        native = fields.fractal_at(
            0xABCDEF, grid_x, grid_y, period=24, octaves=octaves, persistence_permille=500
        )
        expected = reference_noise.fractal_at(
            0xABCDEF, grid_x, grid_y, period=24, octaves=octaves, persistence_permille=500
        )
        assert native.shape == grid_x.shape
        assert np.array_equal(native, expected)


def test_noise_at_accepts_non_contiguous_input() -> None:
    """Broadcast views, as warped_noise passes them, give the reference's values."""
    ys = (np.arange(9, dtype=np.int64) * 16)[:, np.newaxis]
    xs = (np.arange(13, dtype=np.int64) * 16)[np.newaxis, :]
    ys, xs = np.broadcast_arrays(ys, xs)
    native = fields.fractal_at(5, xs, ys, period=32, octaves=3, persistence_permille=500)
    expected = reference_noise.fractal_at(5, xs, ys, period=32, octaves=3, persistence_permille=500)
    assert np.array_equal(native, expected)


def _grids() -> list[np.ndarray]:
    generator = np.random.default_rng(11)
    grids = [
        np.zeros((7, 9), dtype=np.bool_),
        np.ones((4, 4), dtype=np.bool_),
        np.array([[True]]),
        np.array([[False, False, True, False, False]]),
        np.array([[False], [True], [False], [False]]),
    ]
    for shape, density in (((60, 80), 0.01), ((33, 100), 0.002), ((120, 45), 0.2)):
        grids.append(generator.random(shape) < density)
    blob = np.zeros((90, 90), dtype=np.bool_)
    blob[30:60, 20:50] = True
    blob[70, 80] = True
    grids.append(blob)
    return grids


@pytest.mark.parametrize("limit", [0, 1, 2, 3, 9, 40, 500])
@pytest.mark.parametrize("octagonal", [False, True])
def test_step_distance_equals_the_reference(limit: int, *, octagonal: bool) -> None:
    """Diamond and octagonal steps, limits below, at and far above the grid size."""
    for sources in _grids():
        native = topology.distance_from(sources, limit, octagonal=octagonal)
        expected = reference_topology.distance_from(sources, limit, octagonal=octagonal)
        assert native.dtype == np.int32
        assert np.array_equal(native, expected)


@pytest.mark.parametrize("limit", [0, 1, 2, 5, 17, 200])
def test_euclidean_distance_equals_the_reference(limit: int) -> None:
    """Exact distances in eighths, including capping at the limit."""
    for sources in _grids():
        native = topology.euclidean_distance(sources, limit)
        assert native.dtype == np.int64
        assert np.array_equal(native, reference_topology.euclidean_distance(sources, limit))


def test_euclidean_distance_refuses_a_limit_the_squares_cannot_hold() -> None:
    """The native kernel keeps squares in 32 bits and says so instead of wrapping."""
    with pytest.raises(ValueError, match="limit is too large"):
        _ = topology.euclidean_distance(np.ones((2, 2), dtype=np.bool_), 70_000)


@pytest.mark.parametrize("limit", [0, 1, 3, 25, 400])
def test_label_spreading_equals_the_reference(limit: int) -> None:
    """Ties between labels resolve by the lowest-index neighbour in both."""
    generator = np.random.default_rng(5)
    for sources in _grids():
        labels = generator.integers(0, 6, sources.shape, dtype=np.int32)
        native = topology.nearest_label(labels, sources, limit)
        assert native.dtype == np.int32
        assert np.array_equal(native, reference_topology.nearest_label(labels, sources, limit))
