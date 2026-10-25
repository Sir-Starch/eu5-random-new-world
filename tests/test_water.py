"""The strip-by-strip water rebuild equals the whole-image one for any strip height."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

from rnw import eu5_water
from rnw.fields import upsample
from tests.reference import water as reference_water
from tests.test_dds import _file  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Callable


def test_lake_transforms_keep_protected_records_and_reject_an_incomplete_record() -> None:
    inside = struct.pack("<10f", 3, 0, 7, 0, 0, 0, 1, 1, 1, 1)
    outside = struct.pack("<10f", 30, 0, 7, 0, 0, 0, 1, 1, 1, 1)
    mask = np.zeros((10, 10), dtype=bool)
    mask[2, 3] = True
    kept, removed = eu5_water._lakes(inside + outside, mask)  # pyright: ignore[reportPrivateUsage]
    assert kept == outside
    assert removed == 1
    with pytest.raises(ValueError, match="40-byte"):
        _ = eu5_water._lakes(outside + b"x", mask)  # pyright: ignore[reportPrivateUsage]


ROWS, COLUMNS = 300, 220


def _texture(rows: int, columns: int, seed: int) -> bytes:
    """A DXT5 file whose level 0 decodes to RGBA noise (the encoder is not under test)."""
    return _file(rows, columns, seed)


def _masks(seed: int, factor: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    generator = np.random.default_rng(seed)
    shape = (ROWS * factor, COLUMNS * factor)
    coarse = generator.integers(0, 1000, (shape[0] // 60 + 2, shape[1] // 60 + 2))
    vanilla = upsample(coarse, 60, shape) > 450
    fresh = upsample(coarse[::-1].copy(), 60, shape) > 450
    canvas = np.zeros(shape, dtype=bool)
    canvas[shape[0] // 5 : shape[0] * 4 // 5, shape[1] // 6 : shape[1] * 5 // 6] = True
    return vanilla, fresh, canvas


@pytest.mark.parametrize(("factor", "reach"), [(2, 12), (4, 6)])
@pytest.mark.parametrize("strip", [1, 7, 64, 10_000])
def test_strips_of_any_height_build_the_whole_image_texture(
    monkeypatch: pytest.MonkeyPatch, factor: int, reach: int, strip: int
) -> None:
    """The latitude table sums, the blur at strip edges and the noise rows all line up."""
    masks = _masks(factor, factor)
    data = _texture(ROWS, COLUMNS, factor)
    monkeypatch.setattr(eu5_water, "_decode", _decode_stub)
    monkeypatch.setattr(reference_water, "_decode", _decode_stub)
    monkeypatch.setattr(eu5_water, "band_rows", _fixed(strip))
    result = eu5_water._rebuild(  # pyright: ignore[reportPrivateUsage]
        data, factor=factor, reach=reach, masks=masks, seed=5, stream="water_color"
    )
    expected = reference_water.rebuild(
        data, factor=factor, reach=reach, masks=masks, seed=5, stream="water_color"
    )
    assert result == expected
    assert result[1] > 0


def _fixed(rows: int) -> Callable[..., int]:
    """A stand-in for ``band_rows`` that always answers ``rows``."""

    def answer(*_arguments: object, **_options: object) -> int:
        return rows

    return answer


def _decode_stub(raw: bytes) -> np.ndarray:
    return _decoded(raw, ROWS, COLUMNS)


def _decoded(raw: bytes, rows: int, columns: int) -> np.ndarray:
    """A deterministic smooth RGBA image standing in for the decoded DDS."""
    del raw
    generator = np.random.default_rng(rows)
    base = upsample(
        generator.integers(0, 256, (rows // 40 + 2, columns // 40 + 2)), 40, (rows, columns)
    )
    image = np.stack([base, 255 - base, (base * 3) % 256, np.full_like(base, 255)], axis=-1)
    return image.astype(np.uint8)


def test_the_decoder_reads_a_png_through_pillow() -> None:
    """``_decode`` keeps RGBA bytes (a PNG stands in for the DDS the game ships)."""
    buffer = io.BytesIO()
    Image.fromarray(np.arange(4 * 5 * 4, dtype=np.uint8).reshape(4, 5, 4), "RGBA").save(
        buffer, format="PNG"
    )
    assert eu5_water._decode(buffer.getvalue()).shape == (4, 5, 4)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("factor", [2, 4])
def test_removed_island_rebuilds_its_offshore_water_without_repainting_retained_shore(
    monkeypatch: pytest.MonkeyPatch, factor: int
) -> None:
    """An unchanged location's water can lose an old island's colour/foam footprint."""
    rows, columns = 128, 192
    old = np.ones((rows, columns), dtype=bool)
    old[40:70, 30:50] = False
    old[40:70, 135:155] = False
    fresh = old.copy()
    fresh[40:70, 30:50] = True
    mask = old != fresh
    rgba = np.full((rows, columns, 4), 100, dtype=np.uint8)
    rgba[..., 3] = 255
    # A synthetic shallow-water stripe extends outside the removed island's colour.
    rgba[39:71, 25:30, :3] = 220
    captured: list[np.ndarray] = []

    def decode(_data: bytes) -> np.ndarray:
        return rgba

    monkeypatch.setattr(eu5_water, "_decode", decode)

    def capture(_data: bytes, result: np.ndarray, _changed: np.ndarray) -> bytes:
        captured.append(result)
        return b"synthetic"

    monkeypatch.setattr(eu5_water, "rewrite", capture)

    def scale(array: np.ndarray) -> np.ndarray:
        return np.repeat(np.repeat(array, factor, axis=0), factor, axis=1)

    masks = (scale(old), scale(fresh), scale(mask))
    _ = eu5_water._rebuild(  # pyright: ignore[reportPrivateUsage]
        b"synthetic", factor=factor, reach=12, masks=masks, seed=3, stream="coast_test"
    )
    result = captured[0]
    assert np.any(result[40:70, 27:30, :3] != rgba[40:70, 27:30, :3])
    assert np.array_equal(result[:, 100:], rgba[:, 100:])
