"""Raster topology helpers and the deterministic PNG writer."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

from rnw.png import COLOR_PALETTE, COLOR_RGB, encode_png, read_chunks
from rnw.topology import (
    adjacency_lengths,
    adjacency_pairs,
    component_counts,
    label_components,
    unpack_pairs,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_components_count_split_labels_and_wrap() -> None:
    """A label split by another is two parts unless the world wraps horizontally."""
    labels = np.array([[1, 0, 1], [1, 0, 1]], dtype=np.int32)
    assert component_counts(labels).tolist() == [1, 2]
    assert component_counts(labels, wrap_x=True).tolist() == [1, 1]
    assert label_components(labels).tolist() == [[0, 1, 2], [0, 1, 2]]


def test_components_use_four_connectivity() -> None:
    """Diagonal contact does not connect a label."""
    labels = np.array([[1, 0], [0, 1]], dtype=np.int32)
    assert component_counts(labels).tolist() == [2, 2]


def test_adjacency_lengths_count_the_touching_pixels_of_each_pair() -> None:
    labels = np.array([[0, 0, 1], [0, 2, 1]], dtype=np.int32)
    pairs, lengths = adjacency_lengths(labels)
    assert dict(zip(unpack_pairs(pairs), lengths.tolist(), strict=True)) == {
        (0, 1): 1,
        (0, 2): 2,
        (1, 2): 1,
    }
    assert np.array_equal(pairs, adjacency_pairs(labels))


def test_adjacency_pairs_optionally_include_corners() -> None:
    """Only the corner contact distinguishes 4- and 8-neighbour pairs."""
    labels = np.array([[0, 1], [2, 3]], dtype=np.int32)
    assert unpack_pairs(adjacency_pairs(labels)) == [(0, 1), (0, 2), (1, 3), (2, 3)]
    assert unpack_pairs(adjacency_pairs(labels, diagonal=True)) == [
        (0, 1),
        (0, 2),
        (0, 3),
        (1, 2),
        (1, 3),
        (2, 3),
    ]


def test_png_round_trips_through_pillow_in_both_modes() -> None:
    """Stored and zlib encodings decode to the same RGB pixels."""
    pixels = np.arange(5 * 7 * 3, dtype=np.uint8).reshape(5, 7, 3)
    for mode in ("stored", "zlib"):
        data = encode_png(pixels, color_type=COLOR_RGB, compression=mode)
        with Image.open(io.BytesIO(data)) as image:
            assert np.array_equal(np.asarray(image), pixels)


def test_stored_png_bytes_are_fixed_by_specification() -> None:
    """Uncompressed output has no dependency on the zlib build: a golden digest."""
    pixels = np.arange(4 * 3 * 3, dtype=np.uint8).reshape(4, 3, 3)
    data = encode_png(pixels, color_type=COLOR_RGB, compression="stored")
    assert (
        hashlib.sha256(data).hexdigest()
        == "36c72194a28d7afe0dc587ff63f6f40347b3a978556afdee2f4e13670c3561c5"
    )


def test_palette_chunks_are_preserved(tmp_path: Path) -> None:
    """A palette copied from a source image is written before IDAT and read back."""
    palette = bytes(range(256)) * 3
    pixels = np.array([[0, 254], [255, 4]], dtype=np.uint8)
    path = tmp_path / "rivers.png"
    _ = path.write_bytes(
        encode_png(
            pixels,
            color_type=COLOR_PALETTE,
            compression="zlib",
            extra_chunks=((b"PLTE", palette),),
        )
    )
    assert read_chunks(path) == ((b"PLTE", palette),)
    with Image.open(path) as image:
        assert image.mode == "P"
        assert np.array_equal(np.asarray(image), pixels)
