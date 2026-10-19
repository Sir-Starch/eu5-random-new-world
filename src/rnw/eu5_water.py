"""Water visuals for a generated New World: water colour, coastal foam and lake meshes.

Vanilla textures paint shallow water and foam along the old coastlines and lake meshes
sit at the old lakes [V-GAME C45]. Inside the canvas the colour and foam are rebuilt
from vanilla statistics by latitude and distance to the new coast (keeping vanilla
pixels where both maps are open ocean), and lake meshes over the canvas are dropped.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
import struct
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image

from rnw.dds import rewrite
from rnw.fields import box_blur
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.topology import distance_from

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

WATER_COLOR: Final[str] = "gfx/map/water/watercolor_rgb_waterspec_a.dds"
FOAM: Final[str] = "gfx/map/water/foam_map.dds"
LAKES: Final[str] = "gfx/map/map_objects/lakes.bin"
LAKE_RECORD: Final[int] = 40
COLOR_REACH: Final[int] = 64
FOAM_REACH: Final[int] = 16
BAND_ROWS: Final[int] = 64
BLEND: Final[int] = 16


def _downsample(mask: NDArray[np.bool_], factor: int, *, any_true: bool) -> NDArray[np.bool_]:
    rows, columns = mask.shape[0] // factor, mask.shape[1] // factor
    blocks = mask[: rows * factor, : columns * factor].reshape(rows, factor, columns, factor)
    if any_true:
        return blocks.any(axis=(1, 3))
    return blocks[:, 0, :, 0]


def _decode(data: bytes) -> NDArray[np.uint8]:
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(io.BytesIO(data)) as image:
            return np.array(image.convert("RGBA"), dtype=np.uint8)
    finally:
        Image.MAX_IMAGE_PIXELS = previous


def _profile_table(
    image: NDArray[np.int64], distance: NDArray[np.int64], reach: int
) -> NDArray[np.int64]:
    """Mean RGBA per (latitude band, distance to land) from vanilla pixels."""
    bands = image.shape[0] // BAND_ROWS
    band = np.minimum(np.arange(image.shape[0], dtype=np.int64) // BAND_ROWS, bands - 1)[:, None]
    key = (band * (reach + 1) + np.minimum(distance, reach)).ravel()
    size = bands * (reach + 1)
    counts = np.maximum(1, np.bincount(key, minlength=size))
    table = np.zeros((size, 4), dtype=np.int64)
    for channel in range(4):
        sums = np.bincount(key, weights=image[..., channel].ravel(), minlength=size)
        table[:, channel] = sums.astype(np.int64) // counts
    return table.reshape(bands, reach + 1, 4)


def _synthesize(
    table: NDArray[np.int64], distance: NDArray[np.int64], reach: int
) -> NDArray[np.int64]:
    """Colour by latitude (linearly blended between bands) and distance to land."""
    rows = distance.shape[0]
    bands = table.shape[0]
    position = (np.arange(rows, dtype=np.int64) * 1000 - BAND_ROWS * 500) // BAND_ROWS
    lower = np.minimum(np.maximum(position // 1000, 0), bands - 1)
    upper = np.minimum(lower + 1, bands - 1)
    weight = np.minimum(np.maximum(position - lower * 1000, 0), 1000)[:, None, None]
    d = np.minimum(distance, reach)
    first = table[lower[:, None], d]
    second = table[upper[:, None], d]
    return (first * (1000 - weight) + second * weight) // 1000


def _rebuild(  # noqa: PLR0913 - one texture needs masks at its own scale and the seed.
    data: bytes,
    *,
    factor: int,
    reach: int,
    masks: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]],
    seed: int,
    stream: str,
) -> tuple[bytes, int]:
    vanilla_water, new_water, canvas = masks
    image = _decode(data).astype(np.int64)
    old_water = _downsample(vanilla_water, factor, any_true=False)
    fresh_water = _downsample(new_water, factor, any_true=False)
    touched = _downsample(canvas, factor, any_true=True)
    old_distance = distance_from(~old_water, reach + 1, octagonal=True).astype(np.int64)
    new_distance = distance_from(~fresh_water, reach + 1, octagonal=True).astype(np.int64)
    table = _profile_table(image, old_distance, reach)
    synthetic = _synthesize(table, new_distance, reach)
    for channel in range(4):
        synthetic[..., channel] = box_blur(synthetic[..., channel], 2)
    rows, columns = touched.shape
    noise = fractal_noise(
        derive_seed(seed, stream),
        0,
        0,
        columns,
        rows,
        period=96,
        octaves=3,
        persistence_permille=500,
    )
    synthetic[..., :3] += (noise * 6 // NOISE_SCALE)[..., None]
    calm = np.minimum(old_distance, new_distance)
    keep = np.clip(calm - (reach - BLEND), 0, BLEND)[..., None]
    blended = (image * keep + synthetic * (BLEND - keep)) // BLEND
    result = np.where(touched[..., None], blended, image).clip(0, 255).astype(np.uint8)
    changed = touched & np.any(result != image, axis=2)
    return rewrite(data, result, changed), int(np.count_nonzero(changed))


def _lakes(data: bytes, canvas: NDArray[np.bool_]) -> tuple[bytes, int]:
    """Drop lake mesh transforms (x, y, z, quaternion, scale) centred in the canvas."""
    rows, columns = canvas.shape
    kept: list[bytes] = []
    for offset in range(0, len(data) - len(data) % LAKE_RECORD, LAKE_RECORD):
        x, _, z = struct.unpack_from("<3f", data, offset)
        row, column = rows - 1 - int(z), int(x)
        inside = 0 <= row < rows and 0 <= column < columns and bool(canvas[row, column])
        if not inside:
            kept.append(data[offset : offset + LAKE_RECORD])
    return b"".join(kept), len(data) // LAKE_RECORD - len(kept)


def water_outputs(
    game_dir: Path,
    vanilla_water: NDArray[np.bool_],
    new_water: NDArray[np.bool_],
    canvas: NDArray[np.bool_],
    seed: int,
) -> tuple[dict[str, bytes], dict[str, int]]:
    """Mod copies of the water colour map, foam map and lake mesh list."""
    root = game_dir / "game/in_game"
    masks = (vanilla_water, new_water, canvas)
    color, color_px = _rebuild(
        (root / WATER_COLOR).read_bytes(),
        factor=2,
        reach=COLOR_REACH,
        masks=masks,
        seed=seed,
        stream="water_color",
    )
    foam, foam_px = _rebuild(
        (root / FOAM).read_bytes(),
        factor=4,
        reach=FOAM_REACH,
        masks=masks,
        seed=seed,
        stream="water_foam",
    )
    lakes, dropped = _lakes((root / LAKES).read_bytes(), canvas)
    outputs = {f"in_game/{WATER_COLOR}": color, f"in_game/{FOAM}": foam, f"in_game/{LAKES}": lakes}
    return outputs, {"water_color_px": color_px, "foam_px": foam_px, "lake_meshes_dropped": dropped}
