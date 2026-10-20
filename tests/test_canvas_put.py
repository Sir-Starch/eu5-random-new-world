"""``Canvas.put`` writes crop rasters into the map like indexing by the mask's pixels did."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_canvas import Canvas


def _canvas(*, width: int, col0: int, roll: int, crop: int, seed: int) -> Canvas:
    generator = np.random.default_rng(seed)
    mask = generator.random((12, crop)) < 0.6
    return Canvas(
        roll=roll,
        col0=col0,
        mask=mask,
        shape=(12, width),
        removed=np.zeros(1, dtype=bool),
        trimmed=np.zeros(1, dtype=bool),
    )


@pytest.mark.parametrize(("col0", "roll"), [(10, 0), (3, 25), (0, 7), (20, 5), (11, 39)])
def test_put_equals_assignment_through_the_mask_indices(col0: int, roll: int) -> None:
    """Planes and colour channels, with and without a wrap over the map seam."""
    width, crop = 40, 22
    canvas = _canvas(width=width, col0=col0, roll=roll, crop=crop, seed=col0 + roll)
    values = np.random.default_rng(1).integers(0, 200, (12, crop), dtype=np.int32)
    colours = np.random.default_rng(2).integers(0, 255, (12, crop, 3), dtype=np.uint8)
    rows, columns = np.nonzero(canvas.mask)
    world = (columns + canvas.col0 - canvas.roll) % width
    expected = np.full((12, width), -7, dtype=np.int32)
    expected[rows, world] = values[rows, columns]
    expected_rgb = np.zeros((12, width, 3), dtype=np.uint8)
    expected_rgb[rows, world] = colours[rows, columns]
    target = np.full((12, width), -7, dtype=np.int32)
    canvas.put(target, values)
    target_rgb = np.zeros((12, width, 3), dtype=np.uint8)
    canvas.put(target_rgb, colours)
    assert np.array_equal(target, expected)
    assert np.array_equal(target_rgb, expected_rgb)
    assert sum(crop_span.stop - crop_span.start for crop_span, _ in canvas.spans()) == crop
