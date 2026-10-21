"""Covered previews and mod-list pictures, on synthetic maps."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw import pictures


def _map() -> np.ndarray:
    image = np.zeros((64, 128, 3), dtype=np.uint8)
    image[:, :] = (25, 45, 90)
    image[10:50, 70:110] = (70, 110, 60)
    return image


def test_covering_paints_only_the_canvas() -> None:
    """The canvas becomes terra incognita; the rest of the map stays as it was."""
    image = _map()
    rows, columns = np.nonzero(np.zeros((64, 128), dtype=bool) | (np.arange(128) < 40))
    covered = pictures.cover(image, rows, columns)
    assert np.all(covered[:, :40] == pictures.TERRA_INCOGNITA)
    assert np.array_equal(covered[:, 40:], image[:, 40:])
    assert pictures.center_column(covered) in range(18, 22)


def test_the_thumbnail_is_a_square_around_the_new_world_and_wraps_the_map() -> None:
    """Centred on the covered columns, the square takes columns from both map edges."""
    image = _map()
    rows, columns = np.nonzero(np.ones((64, 128), dtype=bool) & (np.arange(128) < 8))
    covered = pictures.cover(image, rows, columns)
    square = pictures.thumbnail(covered, pictures.center_column(covered))
    assert square.shape == (pictures.SIZE, pictures.SIZE, 3)
    middle = square[pictures.SIZE // 2, pictures.SIZE // 2]
    assert tuple(middle) == pictures.TERRA_INCOGNITA
    again = pictures.thumbnail(covered, pictures.center_column(covered))
    assert np.array_equal(square, again)
