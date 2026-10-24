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
from rnw.parallel import band_rows
from rnw.progress import checkpoint
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
# The colour is blurred over a radius of BLUR pixels, so a strip reads that many rows past it.
BLUR: Final[int] = 2
# Rows per strip: the memory of one texture row (RGBA in eight-byte integers, a dozen
# arrays alive) bounds the strip by the free memory [V-EXEC C102].
STRIP_ROW_BYTES: Final[int] = 400
STRIP_FLOOR: Final[int] = 16
STRIP_CEILING: Final[int] = 512


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
    image: NDArray[np.uint8], distance: NDArray[np.uint8], reach: int, strip: int
) -> NDArray[np.int64]:
    """Mean RGBA per (latitude band, distance to land) from vanilla pixels.

    The sums are exact integers in float64 (below 2**53), so adding them strip by strip
    gives the same table as adding them at once.
    """
    rows = image.shape[0]
    bands = rows // BAND_ROWS
    size = bands * (reach + 1)
    counts = np.zeros(size, dtype=np.int64)
    sums = np.zeros((size, 4), dtype=np.float64)
    for first in range(0, rows, strip):
        last = min(rows, first + strip)
        latitude = np.minimum(np.arange(first, last, dtype=np.int64) // BAND_ROWS, bands - 1)
        key = (
            latitude[:, None] * (reach + 1)
            + np.minimum(distance[first:last], reach).astype(np.int64)
        ).ravel()
        counts += np.bincount(key, minlength=size)
        for channel in range(4):
            sums[:, channel] += np.bincount(
                key, weights=image[first:last, :, channel].ravel(), minlength=size
            )
    counts = np.maximum(1, counts)
    return (sums.astype(np.int64) // counts[:, None]).reshape(bands, reach + 1, 4)


def _synthesize(
    table: NDArray[np.int64], distance: NDArray[np.int64], reach: int, first_row: int
) -> NDArray[np.int64]:
    """Colour by latitude (linearly blended between bands) and distance to land.

    ``distance`` holds the rows from ``first_row`` of the image on.
    """
    rows = distance.shape[0]
    bands = table.shape[0]
    position = (
        np.arange(first_row, first_row + rows, dtype=np.int64) * 1000 - BAND_ROWS * 500
    ) // BAND_ROWS
    lower = np.minimum(np.maximum(position // 1000, 0), bands - 1)
    upper = np.minimum(lower + 1, bands - 1)
    weight = np.minimum(np.maximum(position - lower * 1000, 0), 1000)[:, None, None]
    d = np.minimum(distance, reach)
    first = table[lower[:, None], d]
    second = table[upper[:, None], d]
    return (first * (1000 - weight) + second * weight) // 1000


def _render(  # noqa: PLR0913 - a strip reads the image, both distances, the table and the noise.
    image: NDArray[np.uint8],
    distances: tuple[NDArray[np.uint8], NDArray[np.uint8]],
    touched: NDArray[np.bool_],
    table: NDArray[np.int64],
    *,
    first: int,
    last: int,
    reach: int,
    key: int,
) -> NDArray[np.uint8]:
    """New colours of rows ``first`` to ``last``; the blur reads ``BLUR`` rows past them."""
    rows, columns = touched.shape
    start, stop = max(0, first - BLUR), min(rows, last + BLUR)
    old_distance, new_distance = (d[start:stop].astype(np.int64) for d in distances)
    synthetic = _synthesize(table, new_distance, reach, start)
    for channel in range(4):
        synthetic[..., channel] = box_blur(synthetic[..., channel], BLUR)
    synthetic = synthetic[first - start : last - start]
    noise = fractal_noise(
        key, 0, first, columns, last - first, period=96, octaves=3, persistence_permille=500
    )
    synthetic[..., :3] += (noise * 6 // NOISE_SCALE)[..., None]
    calm = np.minimum(old_distance, new_distance)[first - start : last - start]
    keep = np.clip(calm - (reach - BLEND), 0, BLEND)[..., None]
    original = image[first:last].astype(np.int64)
    blended = (original * keep + synthetic * (BLEND - keep)) // BLEND
    return np.where(touched[first:last, :, None], blended, original).clip(0, 255).astype(np.uint8)


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
    image = _decode(data)
    old_water = _downsample(vanilla_water, factor, any_true=False)
    fresh_water = _downsample(new_water, factor, any_true=False)
    touched = _downsample(canvas, factor, any_true=True)
    # Distances are at most reach + 1 steps, which a byte holds.
    old_distance = distance_from(~old_water, reach + 1, octagonal=True).astype(np.uint8)
    new_distance = distance_from(~fresh_water, reach + 1, octagonal=True).astype(np.uint8)
    del old_water, fresh_water
    rows, columns = touched.shape
    strip = band_rows(
        columns * STRIP_ROW_BYTES, workers=1, floor=STRIP_FLOOR, ceiling=STRIP_CEILING
    )
    table = _profile_table(image, old_distance, reach, strip)
    key = derive_seed(seed, stream)
    result = np.empty_like(image)
    changed = np.zeros(touched.shape, dtype=bool)
    for first in range(0, rows, strip):
        checkpoint()
        last = min(rows, first + strip)
        result[first:last] = _render(
            image,
            (old_distance, new_distance),
            touched,
            table,
            first=first,
            last=last,
            reach=reach,
            key=key,
        )
        changed[first:last] = touched[first:last] & np.any(
            result[first:last] != image[first:last], axis=2
        )
    return rewrite(data, result, changed), int(np.count_nonzero(changed))


def _lakes(data: bytes, canvas: NDArray[np.bool_]) -> tuple[bytes, int]:
    """Drop lake mesh transforms (x, y, z, quaternion, scale) centred in the canvas."""
    if len(data) % LAKE_RECORD:
        message = "Lake mesh transforms do not contain complete 40-byte records"
        raise ValueError(message)
    rows, columns = canvas.shape
    kept: list[bytes] = []
    for offset in range(0, len(data), LAKE_RECORD):
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
