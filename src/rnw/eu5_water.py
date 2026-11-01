"""Water visuals for a generated New World: water colour, coastal foam and lake meshes.

Vanilla textures paint shallow water and foam along the old coastlines and lake meshes
sit at the old lakes [V-GAME C45]. Inside the canvas the colour and foam are rebuilt
from vanilla statistics (keeping vanilla pixels where both maps are open ocean), and lake
meshes over the canvas are dropped.

A pixel is the colour of the open water around it plus the shelf of the nearest coast.
The open water is the vanilla colour of pixels far from any old land, smoothed and filled
across the old continents. The shelf is the mean difference between vanilla pixels and
that background by latitude band and distance to land. A table of absolute colours
would paint every new island with the average of all coasts, a disc whose edge shows
wherever the local sea is lighter or darker than the average [V-GAME/V-LOCAL C461].
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

    from rnw.eu5_islands import Moved

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
STRIP_ROW_BYTES: Final[int] = 480
STRIP_FLOOR: Final[int] = 16
STRIP_CEILING: Final[int] = 512
# The open-water background is a grid of cells GRID pixels wide, each the mean of its pixels at
# least ``reach`` from old land. A cell with fewer than GRID_MIN such pixels takes the mean
# of the larger block it belongs to; the grid is then smoothed SMOOTH times.
GRID: Final[int] = 32
GRID_MIN: Final[int] = GRID * GRID // 8
SMOOTH: Final[int] = 3


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


def _open_water_cells(
    image: NDArray[np.uint8], distance: NDArray[np.uint8], reach: int, strip: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Colour sums and pixel counts per ``GRID`` cell of the pixels ``reach`` or more from land.

    Cells past the image edge hold only the pixels inside it. The sums are exact integers,
    so adding them block row by block row gives the same cells as adding them at once.
    """
    rows, columns = distance.shape
    cells = (-(-rows // GRID), -(-columns // GRID))
    sums = np.zeros((*cells, 4), dtype=np.int64)
    counts = np.zeros(cells, dtype=np.int64)
    step = max(1, strip // GRID) * GRID
    for first in range(0, rows, step):
        last = min(rows, first + step)
        block_rows = -(-(last - first) // GRID)
        shape = (block_rows * GRID, cells[1] * GRID)
        far = np.zeros(shape, dtype=bool)
        far[: last - first, :columns] = distance[first:last] >= reach
        top = first // GRID
        counts[top : top + block_rows] = far.reshape(block_rows, GRID, cells[1], GRID).sum(
            axis=(1, 3), dtype=np.int64
        )
        for channel in range(4):
            values = np.zeros(shape, dtype=np.int64)
            values[: last - first, :columns] = image[first:last, :, channel]
            values[~far] = 0
            sums[top : top + block_rows, :, channel] = values.reshape(
                block_rows, GRID, cells[1], GRID
            ).sum(axis=(1, 3), dtype=np.int64)
    return sums, counts


def _background_grid(sums: NDArray[np.int64], counts: NDArray[np.int64]) -> NDArray[np.int64]:
    """Open-water colour per cell: the cell's own mean, else that of the nearest larger block.

    A cell with fewer than ``GRID_MIN`` pixels is empty (land, coast or shelf). Blocks of
    2x2 cells, then 4x4 and so on pool their sums, and an empty cell takes the mean of the
    smallest block that has any; the result is smoothed ``SMOOTH`` times (a 1-2-1 filter,
    wrapping across the seam) so cell edges do not show. Integer throughout.
    """
    own = counts >= GRID_MIN
    levels = [(np.where(own[..., None], sums, 0), np.where(own, counts, 0))]
    while levels[-1][1].shape != (1, 1):
        total, count = levels[-1]
        rows, columns = count.shape
        total = np.pad(total, ((0, rows % 2), (0, columns % 2), (0, 0)))
        count = np.pad(count, ((0, rows % 2), (0, columns % 2)))
        half = (count.shape[0] // 2, count.shape[1] // 2)
        levels.append(
            (
                total.reshape(half[0], 2, half[1], 2, 4).sum(axis=(1, 3)),
                count.reshape(half[0], 2, half[1], 2).sum(axis=(1, 3)),
            )
        )
    total, count = levels[-1]
    if not count[0, 0]:
        message = "The water texture has no open water far enough from land to take its colour"
        raise ValueError(message)
    grid = total // count[..., None]
    for total, count in reversed(levels[:-1]):
        parent = np.repeat(np.repeat(grid, 2, axis=0), 2, axis=1)[
            : count.shape[0], : count.shape[1]
        ]
        grid = np.where((count > 0)[..., None], total // np.maximum(count, 1)[..., None], parent)
    for _ in range(SMOOTH):
        grid = (np.roll(grid, 1, axis=1) + 2 * grid + np.roll(grid, -1, axis=1)) // 4
        above = np.concatenate([grid[:1], grid[:-1]])
        below = np.concatenate([grid[1:], grid[-1:]])
        grid = (above + 2 * grid + below) // 4
    return grid


def _background(grid: NDArray[np.int64], first: int, last: int, columns: int) -> NDArray[np.int64]:
    """Bilinear open-water colour of rows ``first`` to ``last``; columns wrap at the seam.

    Cell centres sit half a cell in; weights are in 1/(2 GRID), so every step is exact.
    """
    height, width = grid.shape[:2]
    span = 2 * GRID
    y = 2 * np.arange(first, last, dtype=np.int64) + 1 - GRID
    row, fy = y // span, (y % span)[:, None, None]
    x = 2 * np.arange(columns, dtype=np.int64) + 1 - GRID
    column, fx = x // span, (x % span)[None, :, None]
    vertical = (
        grid[np.clip(row, 0, height - 1)] * (span - fy) + grid[np.clip(row + 1, 0, height - 1)] * fy
    )
    return (vertical[:, column % width] * (span - fx) + vertical[:, (column + 1) % width] * fx) // (
        span * span
    )


def _profile_table(
    image: NDArray[np.uint8],
    distance: NDArray[np.uint8],
    grid: NDArray[np.int64],
    reach: int,
    strip: int,
) -> NDArray[np.int64]:
    """Mean RGBA offset from the open-water background per (latitude band, distance to land).

    The sums are exact integers in float64 (below 2**53), so adding them strip by strip
    gives the same table as adding them at once.
    """
    rows, columns = distance.shape
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
        offset = image[first:last].astype(np.int64) - _background(grid, first, last, columns)
        for channel in range(4):
            sums[:, channel] += np.bincount(
                key, weights=offset[..., channel].ravel(), minlength=size
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


def _render(  # noqa: PLR0913 - a strip reads the image, both distances, the shelf, the sea and the noise.
    image: NDArray[np.uint8],
    distances: tuple[NDArray[np.uint8], NDArray[np.uint8]],
    touched: NDArray[np.bool_],
    colors: tuple[NDArray[np.int64], NDArray[np.int64]],
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
    table, grid = colors
    synthetic = _synthesize(table, new_distance, reach, start) + _background(
        grid, start, stop, columns
    )
    for channel in range(4):
        padded = np.pad(synthetic[..., channel], ((0, 0), (BLUR, BLUR)), mode="wrap")
        synthetic[..., channel] = box_blur(padded, BLUR)[:, BLUR:-BLUR]
    synthetic = synthetic[first - start : last - start]
    noise = fractal_noise(
        key, 0, first, columns, last - first, period=96, octaves=3, persistence_permille=500
    )
    other = fractal_noise(
        key,
        columns,
        first,
        columns,
        last - first,
        period=96,
        octaves=3,
        persistence_permille=500,
    )
    position = np.arange(columns, dtype=np.int64) * 1000 // columns
    weight = position * position * (3000 - 2 * position) // 1_000_000
    # At either map edge the same section of noise is sampled. Smooth endpoint
    # weights also preserve its slope, rather than resetting the texture at x=0.
    noise = (other * (1000 - weight) + noise * weight) // 1000
    synthetic[..., :3] += (noise * 6 // NOISE_SCALE)[..., None]
    calm = np.minimum(old_distance, new_distance)[first - start : last - start]
    keep = np.clip(calm - (reach - BLEND), 0, BLEND)[..., None]
    original = image[first:last].astype(np.int64)
    blended = (original * keep + synthetic * (BLEND - keep)) // BLEND
    return np.where(touched[first:last, :, None], blended, original).clip(0, 255).astype(np.uint8)


def carry_pixels(
    image: NDArray[np.uint8], moved: Moved | None, factor: int
) -> NDArray[np.bool_] | None:
    """Copy the texture pixels of the moved island groups to their new places, in ``image``.

    A texture pixel is ``factor`` location pixels wide. Returns the pixels written, or None.
    """
    if moved is None:
        return None
    rows, columns = image.shape[:2]
    old = (moved.rows // factor, moved.columns // factor)
    new = (moved.new_rows // factor, moved.new_columns // factor)
    ok = (new[0] < rows) & (new[1] < columns) & (old[0] < rows) & (old[1] < columns)
    source = image[old[0][ok], old[1][ok]].copy()
    image[new[0][ok], new[1][ok]] = source
    placed = np.zeros((rows, columns), dtype=bool)
    placed[new[0][ok], new[1][ok]] = True
    return placed


def _rebuild(  # noqa: PLR0913 - one texture needs masks at its own scale and the seed.
    data: bytes,
    *,
    factor: int,
    reach: int,
    masks: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]],
    seed: int,
    stream: str,
    moved: Moved | None = None,
) -> tuple[bytes, int]:
    vanilla_water, new_water, canvas = masks
    image = _decode(data)
    old_water = _downsample(vanilla_water, factor, any_true=False)
    fresh_water = _downsample(new_water, factor, any_true=False)
    touched = _downsample(canvas, factor, any_true=True)
    # Distances are at most reach + 1 steps, which a byte holds.
    old_distance = distance_from(~old_water, reach + 1, octagonal=True, wrap_x=True).astype(
        np.uint8
    )
    new_distance = distance_from(~fresh_water, reach + 1, octagonal=True, wrap_x=True).astype(
        np.uint8
    )
    # A removed coast affects colour and foam outside its location-colour mask.
    # Rebuild precisely the original water whose distance to land changed; retained
    # shores and the shared open ocean keep their original pixels. This is the input
    # footprint of the coast field, not a correction of an already written texture.
    affected = (
        distance_from(old_distance != new_distance, BLUR + 1, octagonal=True, wrap_x=True) <= BLUR
    )
    touched |= old_water & fresh_water & affected
    del old_water, fresh_water
    rows, columns = touched.shape
    strip = band_rows(
        columns * STRIP_ROW_BYTES, workers=1, floor=STRIP_FLOOR, ceiling=STRIP_CEILING
    )
    # The sea and the shelf are read from the vanilla pixels, before a moved island's
    # texture is copied over open water.
    grid = _background_grid(*_open_water_cells(image, old_distance, reach, strip))
    table = _profile_table(image, old_distance, grid, reach, strip)
    placed = carry_pixels(image, moved, factor)
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
            (table, grid),
            first=first,
            last=last,
            reach=reach,
            key=key,
        )
        changed[first:last] = touched[first:last] & np.any(
            result[first:last] != image[first:last], axis=2
        )
    if placed is not None:
        result[placed] = image[placed]
        changed |= placed
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


def water_outputs(  # noqa: PLR0913, PLR0917 - the textures need the masks, the seed and the moved groups.
    game_dir: Path,
    vanilla_water: NDArray[np.bool_],
    new_water: NDArray[np.bool_],
    canvas: NDArray[np.bool_],
    seed: int,
    moved: Moved | None = None,
) -> tuple[dict[str, bytes], dict[str, int]]:
    """Mod copies of the water colour map, foam map and lake mesh list.

    The colour and foam of a moved island group (``moved``) go with it.
    """
    root = game_dir / "game/in_game"
    masks = (vanilla_water, new_water, canvas)
    color, color_px = _rebuild(
        (root / WATER_COLOR).read_bytes(),
        factor=2,
        reach=COLOR_REACH,
        masks=masks,
        seed=seed,
        stream="water_color",
        moved=moved,
    )
    foam, foam_px = _rebuild(
        (root / FOAM).read_bytes(),
        factor=4,
        reach=FOAM_REACH,
        masks=masks,
        seed=seed,
        stream="water_foam",
        moved=moved,
    )
    lakes, dropped = _lakes((root / LAKES).read_bytes(), canvas)
    outputs = {f"in_game/{WATER_COLOR}": color, f"in_game/{FOAM}": foam, f"in_game/{LAKES}": lakes}
    return outputs, {"water_color_px": color_px, "foam_px": foam_px, "lake_meshes_dropped": dropped}
