"""The Rust kernels equal their pure-Python references bit for bit (ADR 0005)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import (
    _native,
    eu5_objects,
    eu5_slots,
    eu5_terrain,
    fields,
    lzav,
    noise,
    rivers,
    terrain_tiles,
    topology,
)
from tests.reference import fields as reference_fields
from tests.reference import lzav as reference_lzav
from tests.reference import noise as reference_noise
from tests.reference import objects as reference_objects
from tests.reference import points as reference_points
from tests.reference import rivers as reference_rivers
from tests.reference import slots as reference_slots
from tests.reference import terrain as reference_terrain
from tests.reference import tiles as reference_tiles
from tests.reference import topology as reference_topology


def test_sea_voronoi_matches_brute_force_squared_distances() -> None:
    rng = np.random.default_rng(123)
    mask = rng.random((23, 31)) > 0.3
    seeds = np.full(mask.shape, -1, dtype=np.int32)
    positions = [(1, 2), (4, 25), (12, 16), (20, 3), (20, 28)]
    for label, (row, column) in enumerate(positions):
        seeds[row, column] = label
    expected = np.full(mask.shape, -1, dtype=np.int32)
    for row, column in zip(*np.nonzero(mask), strict=True):
        expected[row, column] = min(
            range(len(positions)),
            key=lambda label: (
                (int(row) - positions[label][0]) ** 2 + (int(column) - positions[label][1]) ** 2,
                label,
            ),
        )
    np.testing.assert_array_equal(_native.sea_voronoi(mask, seeds), expected)


def _streams() -> list[bytes]:
    generator = np.random.default_rng(7)
    noise = bytes(generator.integers(0, 256, 3000, dtype=np.uint8))
    runs = bytes(generator.integers(0, 3, 5000, dtype=np.uint8)) + bytes(40_000) + b"\x07" * 77
    shorts = [b"a", b"abcdefgh", bytes(range(20))]
    return [noise, runs, *shorts]


# Named ids: the streams as ids would be too long for a Windows environment variable.
@pytest.mark.parametrize("raw", _streams(), ids=["noise", "runs", "one", "eight", "twenty"])
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
    # The seed-positioned land fields start up to 2**24 pixels from the origin.
    (2**64 - 1, 2**24 - 1, 2**24 - 17, 67, 39, 4096),
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
@pytest.mark.parametrize("wrap_x", [False, True])
def test_step_distance_equals_the_reference(limit: int, *, octagonal: bool, wrap_x: bool) -> None:
    """Diamond and octagonal steps, limits below, at and far above the grid size."""
    for sources in _grids():
        native = topology.distance_from(sources, limit, octagonal=octagonal, wrap_x=wrap_x)
        expected = reference_topology.distance_from(
            sources, limit, octagonal=octagonal, wrap_x=wrap_x
        )
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


SHAPES = [(1, 1), (1, 9), (9, 1), (5, 7), (40, 3), (64, 100), (33, 47)]


def _values(shape: tuple[int, int]) -> np.ndarray:
    generator = np.random.default_rng(shape[0] * 1000 + shape[1])
    return generator.integers(-3_000_000, 3_000_000, shape, dtype=np.int64)


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("step", [1, 2, 3, 7, 16])
def test_upsample_equals_the_reference(shape: tuple[int, int], step: int) -> None:
    """Bilinear samples, including negative values that must floor, not truncate."""
    coarse = _values((shape[0] // step + 2, shape[1] // step + 2))
    native = fields.upsample(coarse, step, shape)
    assert native.shape == shape
    assert np.array_equal(native, reference_fields.upsample(coarse, step, shape))


def test_upsample_refuses_a_grid_that_is_too_small() -> None:
    """The native kernel checks what NumPy would turn into an index error."""
    with pytest.raises(ValueError, match="too small"):
        _ = fields.upsample(np.zeros((2, 2), dtype=np.int64), 4, (9, 9))


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("step", [1, 2, 3, 5, 8])
def test_block_mean_equals_the_reference(shape: tuple[int, int], step: int) -> None:
    """Partial blocks replicate the edge; negative sums floor."""
    values = _values(shape)
    native = fields.block_mean(values, step)
    assert np.array_equal(native, reference_fields.block_mean(values, step))


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("radius", [0, 1, 2, 5, 40])
def test_box_blur_equals_the_reference(shape: tuple[int, int], radius: int) -> None:
    """Radii smaller and much larger than the grid, signed values."""
    values = _values(shape)
    native = fields.box_blur(values, radius)
    assert np.array_equal(native, reference_fields.box_blur(values, radius))


def _pixel_classes(seed: int) -> tuple[eu5_objects.PixelClasses, np.ndarray]:
    generator = np.random.default_rng(seed)
    labels = generator.integers(0, 9, (13, 17), dtype=np.int32)
    materials = generator.integers(0, 40, (26, 34), dtype=np.uint8)
    classes = eu5_objects.PixelClasses(
        labels=labels,
        materials=materials,
        label_class=np.array([0, 1, 2, -1, 3, 1, 0, 2, 4], dtype=np.int64),
        label_coarse=np.array([0, 0, 1, 1, 2, 0, 0, 1, 2], dtype=np.int64),
        calibrate=np.array([True, True, False, True, True, False, True, True, True]),
    )
    return classes, generator.random((13, 17)) < 0.6


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_canvas_pixels_equal_the_reference(seed: int) -> None:
    """Raster order, merged slots and skipped class-less labels match."""
    classes, canvas = _pixel_classes(seed)
    native = eu5_objects.canvas_pixels(classes, canvas)
    expected = reference_objects.canvas_pixels(classes, canvas)
    for found, wanted in zip(native, expected, strict=True):
        assert found.dtype == np.uint32
        assert np.array_equal(found, wanted)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_pixel_counts_equal_the_reference(seed: int) -> None:
    """Counts per key over the masked labels match for both class tables."""
    classes, _ = _pixel_classes(seed)
    masked = eu5_objects.PixelClasses(
        classes.labels,
        classes.materials,
        classes.label_coarse,
        classes.label_coarse,
        classes.calibrate,
    )
    for table in (masked.label_class, classes.label_coarse):
        native = eu5_objects.pixel_counts(masked, table, 5, masked.calibrate)
        expected = reference_objects.pixel_counts(masked, table, 5, masked.calibrate)
        assert np.array_equal(native, expected)


def test_pixel_counts_refuse_a_label_without_a_class() -> None:
    """A masked label of class -1 would give a negative key, which bincount refuses."""
    classes, _ = _pixel_classes(1)
    with pytest.raises(ValueError, match="no class"):
        _ = eu5_objects.pixel_counts(classes, classes.label_class, 5, np.ones(9, dtype=np.bool_))


@pytest.mark.parametrize("seed", [4, 5])
def test_instance_sampling_equals_the_reference(seed: int) -> None:
    """Whole and fractional parts, donor choice and float positions match bit for bit."""
    classes, canvas = _pixel_classes(seed)
    pixels = eu5_objects.canvas_pixels(classes, canvas)
    generator = np.random.default_rng(seed)
    use_fine = generator.random(90) < 0.5
    fine = generator.integers(0, 3 << 24, 90, dtype=np.int64) * (generator.random(90) < 0.7)
    coarse = generator.integers(0, 2 << 24, 90, dtype=np.int64)
    donors = generator.random((7, 10), dtype=np.float32)
    native = eu5_objects.sample_instances(
        pixels, use_fine=use_fine, densities=(fine, coarse), source=donors, rows=13, key=seed + 99
    )
    rows, columns, fine_key, coarse_key = (array.astype(np.int64) for array in pixels)
    density = np.where(use_fine[fine_key], fine[fine_key], coarse[coarse_key])
    wanted = density > 0
    expected = reference_objects.sample_instances(
        rows[wanted],
        columns[wanted],
        density=density[wanted],
        source=donors,
        rows=13,
        key=seed + 99,
    )
    assert native.shape[1] == 10
    assert np.array_equal(native.view(np.uint32), expected.view(np.uint32))
    assert eu5_objects.sample_instances(
        pixels, use_fine=use_fine, densities=(fine, coarse), source=donors[:0], rows=13, key=1
    ).shape == (0, 10)


@pytest.mark.parametrize("wrap_x", [False, True])
def test_components_equal_the_reference(*, wrap_x: bool) -> None:
    """Numbering by first pixel, with and without the seam joining the edges."""
    generator = np.random.default_rng(21)
    grids = [
        generator.integers(0, k, shape, dtype=np.int32)
        for k, shape in (
            (2, (30, 41)),
            (5, (60, 17)),
            (3, (1, 30)),
            (3, (30, 1)),
            (1, (6, 6)),
            (9, (50, 50)),
        )
    ]
    blobs = np.zeros((40, 40), dtype=np.int32)
    blobs[5:20, 5:20] = 1
    blobs[10:30, 25:39] = 1
    blobs[:, 0] = 2
    blobs[:, -1] = 2
    grids.append(blobs)
    for labels in grids:
        native = topology.label_components(labels, wrap_x=wrap_x)
        assert native.dtype == np.int32
        assert np.array_equal(native, reference_topology.label_components(labels, wrap_x=wrap_x))
    empty = np.zeros((0, 4), dtype=np.int32)
    assert topology.label_components(empty).shape == (0, 4)


@pytest.mark.parametrize("shape", [(1, 1), (4, 9), (30, 41), (64, 64)])
@pytest.mark.parametrize("seed", [1, 2])
def test_drainage_equals_the_reference(shape: tuple[int, int], seed: int) -> None:
    """The flood order, ties by hashed noise and the accumulated rain match."""
    generator = np.random.default_rng(seed * 100 + shape[0])
    land = generator.random(shape) < 0.75
    height = generator.integers(-5, 400, shape, dtype=np.int64)
    height[::7] = 100  # flats make the tie-breaking noise matter
    rain = generator.integers(-3, 50, shape, dtype=np.int64)
    native = rivers.drainage(land, height, rain, key=seed + 1000)
    expected = reference_rivers.drainage(land, height, rain, key=seed + 1000)
    assert np.array_equal(native.parent, expected.parent)
    assert np.array_equal(native.flow, expected.flow)


@pytest.mark.parametrize(("seed", "limits"), [(8, (512, 64)), (9, (6, 3)), (10, (40, 5))])
def test_interior_points_equal_the_reference(seed: int, limits: tuple[int, int]) -> None:
    """Boundary and shore distances, the land score and its ties, empty cells at the origin."""
    generator = np.random.default_rng(seed)
    shape = (60, 77)
    labels = (
        fields.upsample(
            generator.integers(0, 14, (shape[0] // 11 + 2, shape[1] // 11 + 2)), 11, shape
        )
        % 14
    ).astype(np.int32)
    labels[labels == 7] = 8  # cell 7 has no pixel
    labels[:3, :9] = -1
    land = generator.random(14) < 0.6
    native = _native.interior_points(labels, land, *limits)
    assert np.array_equal(native, reference_points.interior_points(labels, land, *limits))
    assert native[7].tolist() == [0, 0]
    assert native.shape == (14, 2)
    with pytest.raises(ValueError, match="below the count"):
        _ = _native.interior_points(labels, land[:5], *limits)


def _slot_window(seed: int, shape: tuple[int, int]) -> tuple[np.ndarray, ...]:
    generator = np.random.default_rng(seed)
    count = 14
    labels = (
        fields.upsample(
            generator.integers(0, count, (shape[0] // 8 + 2, shape[1] // 8 + 2)), 8, shape
        )
        % count
    ).astype(np.int32)
    land_label = generator.random(count) < 0.6
    land = land_label[labels] & (generator.random(shape) < 0.97)
    rivers_mask = (generator.random(shape) < 0.01) & land
    return labels, land, rivers_mask, land_label


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("with_rivers", [False, True])
def test_slot_synthesis_equals_the_reference(seed: int, *, with_rivers: bool) -> None:
    """Coast, transition, river and border bands, variation levels and the remap match."""
    shape = (70 + seed * 9, 83 + seed * 5)
    labels, land, river_mask, land_label = _slot_window(seed, shape)
    generator = np.random.default_rng(seed + 50)
    count = land_label.size
    tables = eu5_slots.SlotTables(
        water=~land_label,
        coast_slot=generator.integers(0, 5, count, dtype=np.int64),
        topography=generator.integers(0, 4, count, dtype=np.int64),
        vegetation=generator.integers(0, 4, count, dtype=np.int64),
        climate=generator.integers(0, 3, count, dtype=np.int64),
        level_one=generator.integers(0, 500, count, dtype=np.int64),
        level_two=generator.integers(0, 400, count, dtype=np.int64),
        materials=generator.integers(0, 18, count, dtype=np.int64),
    )
    if not with_rivers:
        river_mask = np.zeros(shape, dtype=np.bool_)
    for origin in ((0, 0), (1234, 567)):
        native = eu5_slots.synthesize(labels, land, river_mask, tables, seed=seed, origin=origin)
        expected = reference_slots.synthesize(
            labels, land, river_mask, tables, seed=seed, origin=origin
        )
        assert native.dtype == np.uint8
        assert np.array_equal(native, expected)
        assert len(np.unique(native)) > 4
        for core in (
            (slice(5, 40), slice(7, 60)),
            (slice(0, 1), slice(0, shape[1])),
            (slice(20, shape[0]), slice(30, 31)),
        ):
            cropped = eu5_slots.synthesize(
                labels, land, river_mask, tables, seed=seed, origin=origin, core=core
            )
            assert np.array_equal(cropped, expected[core])


def test_lzav_encoder_equals_the_reference() -> None:
    """Run detection, the end-literal rule and short and long length forms match."""
    generator = np.random.default_rng(31)
    samples = [
        bytes(generator.integers(0, 256, 700, dtype=np.uint8)),
        bytes(5000),
        bytes([1, 2, 3, 4, 5, 6, 7, 8]) * 90 + b"tail-bytes-here",
        bytes(generator.integers(0, 4, 3000, dtype=np.uint8)) + bytes(40) + b"x" * 33,
        b"abcdefgh" * 4 + b"123456789",
        b"a",
        bytes(9),
        bytes(10),
        bytes(range(256)) * 3,
    ]
    for raw in samples:
        stream = lzav.encode(raw)
        assert stream == reference_lzav.encode(raw)
        assert lzav.decode(stream, len(raw)) == raw


@pytest.mark.parametrize(
    ("shape", "sample_bytes"), [((100, 90), 2), ((300, 200), 1), ((517, 129), 2)]
)
def test_layer_packing_equals_the_reference(shape: tuple[int, int], sample_bytes: int) -> None:
    """Flip, mip levels, edge-padded tiles, truncation to the sample type and offsets match."""
    generator = np.random.default_rng(shape[0])
    image = generator.integers(0, 70_000, shape, dtype=np.int64)
    image[: shape[0] // 2, : shape[1] // 2] = 4000  # long runs compress
    layer = terrain_tiles.LayerFormat(shape[1], shape[0], "<u2" if sample_bytes == 2 else "u1")
    native = terrain_tiles.write_layer(image, layer)
    assert native == reference_tiles.write_layer(image, layer)


@pytest.mark.parametrize("seed", [1, 2])
@pytest.mark.parametrize("origin", [(0, 0), (4096, 2048)])
def test_decal_heights_equal_the_reference(seed: int, origin: tuple[int, int]) -> None:
    """Land mask, canvas mask and heights match: coast smoothing, caps, crests and shelves."""
    generator = np.random.default_rng(seed)
    shape = (45, 61)
    codes = fields.upsample(
        generator.integers(-1, 2, (shape[0] // 6 + 2, shape[1] // 6 + 2)), 6, shape
    )
    codes = codes.astype(np.int8)
    codes[:5] = -1
    water = (
        fields.upsample(generator.integers(0, 2, (shape[0] // 9 + 2, shape[1] // 9 + 2)), 9, shape)
        > 0
    )
    relief = fields.upsample(
        generator.integers(-500, 30_000, (shape[0] // 5 + 2, shape[1] // 5 + 2)), 5, shape
    )
    native = eu5_terrain.decal_heights(codes, water, relief, seed=seed, origin=origin)
    land, canvas, inland, offshore = reference_terrain.land_and_distances(
        codes.astype(np.int64), water
    )
    expected = reference_terrain.heights(
        relief.astype(np.int64),
        land=land,
        inland=inland,
        offshore=offshore,
        seed=seed,
        origin=origin,
    )
    assert np.array_equal(native[0], land)
    assert np.array_equal(native[1], canvas)
    assert np.array_equal(native[2], expected)
    assert land.any()
    assert (~land).any()
    doubled = (shape[0] * 2, shape[1] * 2)
    for core in (
        (slice(10, 70), slice(12, 100)),
        (slice(0, 1), slice(0, doubled[1])),
        (slice(40, doubled[0]), slice(50, 51)),
    ):
        part = eu5_terrain.decal_heights(codes, water, relief, seed=seed, origin=origin, core=core)
        assert np.array_equal(part[0], land)
        assert np.array_equal(part[1], canvas[core])
        assert np.array_equal(part[2], expected[core])
