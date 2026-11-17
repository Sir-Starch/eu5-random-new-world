"""Native cell kernels retain the pre-optimization algorithm, including ties."""

# pyright: reportAny=false
from __future__ import annotations

import numpy as np
import pytest

from rnw import _native, synth, watersheds
from rnw.progress import Cancelled, Progress, active
from tests.reference import cells as reference


@pytest.mark.parametrize("shape", [(0, 0), (1, 1), (1, 31), (31, 1), (32, 47)])
@pytest.mark.parametrize("weighted", [False, True])
def test_frontier_growth_equals_reference(shape: tuple[int, int], *, weighted: bool) -> None:
    rng = np.random.default_rng(3456)
    for _ in range(12):
        # A transposed input also proves wrappers preserve row-major semantics.
        mask = (rng.integers(0, 5, shape[::-1]) > 0).T
        seeds = np.full(shape[::-1], -7, dtype=np.int32).T
        sites = np.flatnonzero(rng.integers(0, 25, mask.size) == 0)
        seeds.flat[sites] = np.arange(sites.size, dtype=np.int32)
        speeds = rng.integers(1, 130, sites.size, dtype=np.int64)
        before = seeds.copy()
        if weighted:
            actual = synth.grow_weighted(mask, seeds, speeds)
            expected = reference.grow_weighted(mask, seeds, speeds)
        else:
            actual = synth.grow_regions(mask, seeds)
            expected = reference.grow_regions(mask, seeds)
        assert np.array_equal(actual, expected)
        assert np.array_equal(seeds, before)


@pytest.mark.parametrize("step", [0, 1, 72, 1000])
def test_spacing_relaxation_equals_reference(step: int) -> None:
    rng = np.random.default_rng(271828)
    for shape in [(0, 0), (1, 18), (18, 1), (27, 41)]:
        for _ in range(5):
            spacing = rng.integers(-10000, 20000, shape[::-1], dtype=np.int64).T
            land = (rng.integers(0, 6, shape[::-1]) > 0).T
            assert np.array_equal(
                watersheds.grade_spacing(spacing, land, step),
                reference.grade_spacing(spacing, land, step),
            )


@pytest.mark.parametrize("smallest", [1, 7, 40])
def test_greedy_seed_order_and_distance_equal_reference(smallest: int) -> None:
    rng = np.random.default_rng(161803)
    for size in (0, 1, 500):
        xs, ys = rng.integers(-50, 500, (2, size), dtype=np.int64)
        radius = rng.integers(smallest, smallest * 5, size, dtype=np.int64)
        keywords = {"smallest": smallest, "widest": smallest * 5, "columns": 500}
        assert np.array_equal(
            watersheds._throw_seeds(xs, ys, radius, **keywords),  # pyright: ignore[reportPrivateUsage]
            reference.throw_seeds(xs, ys, radius, **keywords),
        )


def test_native_growth_and_relaxation_are_cancellable() -> None:
    progress = Progress()
    progress.cancel()
    shape = (20, 20)
    with active(progress), pytest.raises(Cancelled):
        _ = synth.grow_regions(np.ones(shape, dtype=bool), np.zeros(shape, dtype=np.int32))
    with active(progress), pytest.raises(Cancelled):
        _ = watersheds.grade_spacing(np.ones(shape, dtype=np.int64), np.ones(shape, bool), 1)


def test_native_growth_rejects_invalid_speed_and_shapes() -> None:
    mask = np.ones((2, 3), dtype=bool)
    seeds = np.zeros(mask.shape, dtype=np.int32)
    with pytest.raises(ValueError, match="positive speed"):
        _ = synth.grow_weighted(mask, seeds, np.array([0], dtype=np.int64))
    with pytest.raises(ValueError, match="shapes"):
        _ = _native.grow_labels(mask, seeds.T.copy(), None, lambda: None)


def test_native_cell_centres_keep_empty_cells_and_first_distance_ties() -> None:
    rng = np.random.default_rng(123)
    for shape in [(1, 30), (30, 1), (71, 63)]:
        for _ in range(8):
            labels = rng.integers(-1, 19, shape, dtype=np.int32)
            seeds = np.arange(20, dtype=np.int64)
            assert np.array_equal(
                watersheds._centre_pixels(labels, seeds),  # pyright: ignore[reportPrivateUsage]
                reference.centre_pixels(labels, seeds),
            )
    ring = np.array([[0, 0, 0], [0, -1, 0], [0, 0, 0]], dtype=np.int32)
    assert watersheds._centre_pixels(ring, np.array([8], dtype=np.int64))[0] == 1  # pyright: ignore[reportPrivateUsage]


def test_small_cell_merges_keep_border_counts_and_label_order() -> None:
    rng = np.random.default_rng(2468)
    for shape in [(1, 31), (31, 1), (53, 71)]:
        for minimum in (0, 2, 50, 10000):
            labels = rng.integers(-1, 17, shape, dtype=np.int32)
            assert np.array_equal(
                synth.merge_small(labels, minimum), reference.merge_small(labels, minimum)
            )


def test_block_feature_sums_match_reference_for_partial_strips_and_negative_values() -> None:
    from rnw import eu5_biomes  # noqa: PLC0415

    rng = np.random.default_rng(987)
    for step in (1, 7, 32):
        for shape in [(1, 1), (19, 15), (67, 41)]:
            labels = rng.integers(-3, 17, shape[::-1], dtype=np.int32).T
            blocks = (-(-shape[0] // step), -(-shape[1] // step))
            table = rng.integers(-20000, 20000, (blocks[0] * blocks[1], 9), dtype=np.int64)
            actual = eu5_biomes._location_sums(labels, table, blocks, 19, step=step)  # pyright: ignore[reportPrivateUsage]
            expected = reference.location_sums(labels, table, blocks, 19, step=step)
            assert all(np.array_equal(a, b) for a, b in zip(actual, expected, strict=True))


@pytest.mark.parametrize("shape", [(1, 1), (5, 40), (48, 17)])
def test_native_bend_preserves_halos_and_masked_endpoints(shape: tuple[int, int]) -> None:
    from rnw import relief  # noqa: PLC0415

    rng = np.random.default_rng(4242)
    land = rng.integers(0, 5, shape) > 0
    height = rng.integers(-10000, 50000, shape, dtype=np.int64)
    for strip in (1, 7, 48):
        for start in range(0, shape[0], strip):
            stop = min(shape[0], start + strip)
            low, high = max(0, start - 8), min(shape[0], stop + 8)
            assert np.array_equal(
                relief.strip_bend(land[low:high], height[low:high], start, stop, shape[0]),
                reference.strip_bend(land[low:high], height[low:high], start, stop, shape[0]),
            )


@pytest.mark.parametrize("radius", [0, 1, 3, 8, 17])
def test_fused_land_blur_preserves_each_rounding_step(radius: int) -> None:
    from rnw.relief import land_blur  # noqa: PLC0415

    rng = np.random.default_rng(123456)
    for shape in [(1, 1), (1, 49), (49, 1), (57, 61)]:
        land = (rng.integers(0, 3, shape[::-1]) > 0).T
        height = rng.integers(-50000, 50000, shape[::-1], dtype=np.int64).T
        assert np.array_equal(
            land_blur(land, height, radius), reference.land_blur(land, height, radius)
        )


@pytest.mark.parametrize("blur", [0, 1, 8])
def test_native_block_relief_preserves_spread_and_bend(blur: int) -> None:
    from rnw import eu5_biomes  # noqa: PLC0415

    rng = np.random.default_rng(987654)
    for shape in [(13, 17), (130, 145), (1031, 71)]:
        land = rng.integers(0, 5, shape) > 0
        height = rng.integers(-10000, 50000, shape, dtype=np.int64)
        step = eu5_biomes.SIZE_STEP
        found = rng.integers(0, 3, (-(-shape[0] // step), -(-shape[1] // step))) > 0
        expected = reference.block_relief(land, height, found, blur=blur)
        actual = eu5_biomes.block_relief(land, height, found, blur=blur)
        assert np.array_equal(actual, expected)
        spread_only = eu5_biomes.block_relief(land, height, found, blur=blur, rough=False)
        assert np.array_equal(spread_only[:, 0], expected[:, 0])


def test_native_renumber_retains_first_appearance_and_all_negative_sentinels() -> None:
    rng = np.random.default_rng(567890)
    for shape in [(0, 0), (1, 41), (41, 1), (63, 17)]:
        for _ in range(8):
            labels = rng.integers(-9, 27, shape[::-1], dtype=np.int32).T
            assert np.array_equal(synth.renumber(labels), reference.renumber(labels))


def test_native_inline_instance_text_matches_python_float_formatting() -> None:
    rng = np.random.default_rng(192837)
    # Arbitrary float32 bit patterns exercise large/small values, signed zero, NaN and infinity.
    samples = rng.integers(0, 1 << 32, (1000, 17), dtype=np.uint32).view(np.float32)
    samples[0, :8] = [0.0, -0.0, np.inf, -np.inf, np.nan, 0.0078125, -0.0078125, 1.2345675]
    for values in (samples, np.empty((0, 16), np.float32), np.empty((3, 0), np.float32)):
        expected = "".join(
            " ".join(f"{float(v):.6f}" for v in row) + "\n" for row in values.tolist()
        )
        assert _native.format_instances(values) == expected


def test_native_coastal_contacts_keep_every_land_pixel_and_repeated_contact() -> None:
    rng = np.random.default_rng(123789)
    land = np.array([True, True, False, False, False])
    sea = np.array([False, False, True, True, False])
    for shape in [(1, 1), (1, 37), (37, 1), (53, 71)]:
        labels = rng.integers(-1, 5, shape, dtype=np.int32)
        expected: list[tuple[int, int, int]] = []
        for y in range(shape[0]):
            for x in range(shape[1]):
                for dy, dx in ((0, 1), (1, 0)):
                    if y + dy >= shape[0] or x + dx >= shape[1]:
                        continue
                    a, b = int(labels[y, x]), int(labels[y + dy, x + dx])
                    if a >= 0 and b >= 0:
                        if land[a] and sea[b]:
                            expected.append((a, b, y * shape[1] + x))
                        if sea[a] and land[b]:
                            expected.append((b, a, (y + dy) * shape[1] + x + dx))
        actual = _native.coastal_pixels(labels, land, sea)
        assert sorted(tuple(row) for row in actual.tolist()) == sorted(expected)


def test_fused_mountain_height_and_slot_rules_equal_numpy() -> None:
    from rnw.eu5_mountains import CAP, FULL, LOW  # noqa: PLC0415
    from rnw.eu5_slots import slot_remap  # noqa: PLC0415

    rng = np.random.default_rng(369258)
    shape = (67, 41)
    heights = rng.integers(-1000, 65000, shape, dtype=np.int64)
    inside = rng.integers(0, 3, shape) > 0
    detail = rng.integers(-500, 500, shape, dtype=np.int64)
    laid = rng.integers(0, 256, shape, dtype=np.uint8)
    reach = rng.integers(0, 13, shape, dtype=np.int32)
    stamped = np.where(inside & (heights >= LOW), laid, 255)
    gain = np.clip((heights - LOW) * 1000 // (FULL - LOW), 0, 1000)
    raised = heights + np.where(inside, detail * gain // 1000 * reach // 12, 0)
    expected = np.minimum(raised, np.maximum(heights, CAP))
    actual, slots = _native.blend_mountains(
        heights, inside, detail, laid, reach, (LOW, FULL, CAP), 255
    )
    assert np.array_equal(actual, expected)
    assert np.array_equal(slots, stamped)
    labels = rng.integers(-2, 19, shape, dtype=np.int32)
    materials = rng.integers(-1, 20, 19, dtype=np.int64)
    original = rng.integers(0, 16, shape, dtype=np.uint8)
    count = np.clip(materials[labels], 0, 16)
    remapped = slot_remap()[count, np.minimum(stamped, 15)]
    shown = (stamped != 255) & (remapped >= 10)
    expected_slots = np.where(shown, np.minimum(original, remapped), original).astype(np.uint8)
    actual_slots = _native.stamp_slots(original, stamped, labels, materials, slot_remap().ravel())
    assert np.array_equal(actual_slots, expected_slots)


@pytest.mark.parametrize("dtype", [np.int16, np.int32, np.int64, np.uint32, np.uint64])
def test_first_component_pixels_keep_value_order_for_dense_sparse_and_extreme_ids(
    dtype: type[np.integer],
) -> None:
    rng = np.random.default_rng(43210)
    for values in (
        np.array([], dtype=dtype),
        rng.integers(0, 17, (23, 31)).astype(dtype).T,
        np.array(
            [np.iinfo(dtype).max, 1, np.iinfo(dtype).max, 0, np.iinfo(dtype).min], dtype=dtype
        ),
    ):
        _, expected = np.unique(values.ravel(), return_index=True)
        assert np.array_equal(synth.first_pixels(values), expected)


def test_growth_checks_cancellation_after_starting_native_work() -> None:
    # The slow frontier cannot advance yet and stays pending after the first batch.
    # No large fixture or timing-dependent background cancellation is needed.
    mask = np.array([[True, True, False, True]])
    seeds = np.array([[0, -1, -1, 1]], dtype=np.int32)
    speeds = np.array([1, np.iinfo(np.int64).max], dtype=np.int64)
    calls = 0

    def stop() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise Cancelled

    with pytest.raises(Cancelled):
        _ = _native.grow_labels(mask, seeds, speeds, stop)
    assert calls == 2
    assert seeds.tolist() == [[0, -1, -1, 1]]
