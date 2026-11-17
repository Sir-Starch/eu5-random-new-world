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
