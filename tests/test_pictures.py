"""Covered previews and mod-list pictures, on synthetic maps."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

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


def test_the_tag_is_red_in_the_middle_and_leaves_the_rest_alone() -> None:
    """Large red letters with a dark outline in the centre; the corners are untouched."""
    square = np.zeros((pictures.SIZE, pictures.SIZE, 3), dtype=np.uint8)
    square[:] = pictures.TERRA_INCOGNITA
    marked = pictures.tagged(square, "7K3Q")
    red = np.all(marked == pictures.TAG_COLOR, axis=2)
    dark = np.all(marked == pictures.TAG_OUTLINE, axis=2)
    assert red.any()
    assert dark.sum() > 0
    rows, columns = np.nonzero(red | dark)
    assert abs((rows.min() + rows.max()) / 2 - pictures.SIZE / 2) <= 2
    assert abs((columns.min() + columns.max()) / 2 - pictures.SIZE / 2) <= 2
    assert columns.max() - columns.min() < pictures.SIZE * 5 // 8 + 8
    assert np.array_equal(marked[:20], square[:20])
    assert np.array_equal(marked[:, :20], square[:, :20])
    assert np.array_equal(marked, pictures.tagged(square, "7K3Q"))
    assert not np.array_equal(marked, pictures.tagged(square, "7K3R"))
    assert np.array_equal(square, np.full_like(square, pictures.TERRA_INCOGNITA))


def test_a_picture_too_small_for_the_tag_is_refused() -> None:
    """Four letters need more than a thumbnail of a few pixels."""
    tiny = np.zeros((20, 20, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="too small"):
        _ = pictures.tagged(tiny, "7K3Q")
