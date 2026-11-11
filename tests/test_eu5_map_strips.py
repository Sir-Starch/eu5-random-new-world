"""Whole-map passes over the location raster work in strips and give the whole-map answer."""

from __future__ import annotations

import numpy as np
import pytest

from rnw import parallel
from rnw.eu5_map import (
    COLOR_SPACE,
    STRIP_ROWS,
    UndeclaredColorError,
    differing_pixels,
    labels_from_rgb,
)

HEIGHT = 2 * STRIP_ROWS + 37  # two whole strips and a short last one
WIDTH = 41


def _raster(seed: int, count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A random RGB raster of ``count`` declared colours, those colours, and the labels drawn."""
    rng = np.random.default_rng(seed)
    colors = rng.choice(COLOR_SPACE, size=count, replace=False).astype(np.int64)
    labels = rng.integers(0, count, size=(HEIGHT, WIDTH))
    packed = colors[labels]
    rgb = np.stack([(packed >> 16) & 255, (packed >> 8) & 255, packed & 255], axis=-1)
    return rgb.astype(np.uint8), colors, labels.astype(np.int32)


def test_labels_from_rgb_returns_the_declared_index_of_every_pixel() -> None:
    """The strips join without a seam: every pixel, in every strip, carries its colour's index."""
    rgb, colors, labels = _raster(1, 300)
    result = labels_from_rgb(rgb, colors)
    assert result.dtype == np.int32
    assert np.array_equal(result, labels)


def test_labels_from_rgb_counts_the_undeclared_pixels_of_every_strip() -> None:
    """An undeclared colour is refused with the count over the whole raster, not one strip."""
    rgb, colors, _ = _raster(2, 50)
    stray = 0xABCDEF
    assert not np.isin(stray, colors)
    for row in (3, STRIP_ROWS + 5, HEIGHT - 1):
        rgb[row, 7] = (stray >> 16, (stray >> 8) & 255, stray & 255)
    with pytest.raises(UndeclaredColorError) as raised:
        _ = labels_from_rgb(rgb, colors)
    assert raised.value.pixels == 3


def test_differing_pixels_matches_a_whole_raster_comparison() -> None:
    """A change in any one channel, in any strip, marks its pixel and no other."""
    left, _, _ = _raster(3, 40)
    right = left.copy()
    for row, column, channel in (
        (0, 0, 0),
        (STRIP_ROWS - 1, 5, 1),
        (STRIP_ROWS, 6, 2),
        (HEIGHT - 1, 40, 0),
    ):
        right[row, column, channel] ^= 1
    expected = np.not_equal(left, right).any(axis=2)
    result = differing_pixels(left, right)
    assert result.dtype == np.bool_
    assert int(np.count_nonzero(result)) == 4
    assert np.array_equal(result, expected)


def test_every_stage_returns_the_memory_its_arenas_hold(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stage that ends, with one worker or several, hands its freed heap back once."""
    released: list[int] = []
    monkeypatch.setattr(parallel, "release_free_memory", lambda: released.append(1))
    for workers in (1, 3):
        released.clear()
        with parallel.Stages(workers) as stages:
            futures = [
                stages.submit(f"stage {index}", lambda index=index: index) for index in range(3)
            ]
        assert [future.result() for future in futures] == [0, 1, 2]
        assert len(released) == 3


def test_a_stage_that_fails_still_returns_the_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """The release does not depend on the stage succeeding."""
    released: list[int] = []
    monkeypatch.setattr(parallel, "release_free_memory", lambda: released.append(1))

    def broken() -> None:
        message = "stage failed"
        raise RuntimeError(message)

    with parallel.Stages(1) as stages:
        future = stages.submit("broken", broken)
    with pytest.raises(RuntimeError, match="stage failed"):
        future.result()
    assert released == [1]


def test_releasing_free_memory_is_harmless_anywhere() -> None:
    """It returns nothing and changes no data, with the C library call or without it."""
    data = np.arange(1000, dtype=np.int32)
    parallel.release_free_memory()
    assert int(data.sum()) == 499500
