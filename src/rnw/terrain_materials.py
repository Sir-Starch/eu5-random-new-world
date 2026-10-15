"""Material layers for generated land by transferring vanilla texture patches.

Generated inland is cut into noise-perturbed Voronoi patches (in absolute world
coordinates, so neighbouring decals agree). Each patch copies the material pattern of
vanilla inland at a horizontal offset (similar latitude) whose category matches:
lowland or highland. Beaches and shelves pick among the decal's typical coastal slots
with smooth noise. All choices are deterministic functions of the seed and position.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import SplitMix64, derive_seed, hash_grid, hash_point

if TYPE_CHECKING:
    from numpy.typing import NDArray

SITE: Final[int] = 80
WOBBLE: Final[int] = 24
TRIES: Final[int] = 40
SHIFT_MIN: Final[int] = 300
SHIFT_MAX: Final[int] = 5000
LATITUDE_SPREAD: Final[int] = 120
SAMPLE_GRID: Final[tuple[int, ...]] = (-24, -8, 8, 24)
ACCEPT: Final[int] = 14
NONE, LOWLAND, HIGHLAND = 0, 1, 2
NO_MATERIAL: Final[int] = 255


def site_field(
    seed: int, x0: int, y0: int, width: int, height: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Cell coordinates of the nearest jittered site for each location pixel."""
    key = derive_seed(seed, "material_sites")
    xs = np.arange(x0, x0 + width, dtype=np.int64)[np.newaxis, :]
    ys = np.arange(y0, y0 + height, dtype=np.int64)[:, np.newaxis]
    wobble_x = fractal_noise(
        derive_seed(seed, "material_wobble_x"),
        x0,
        y0,
        width,
        height,
        period=48,
        octaves=3,
        persistence_permille=500,
    )
    wobble_y = fractal_noise(
        derive_seed(seed, "material_wobble_y"),
        x0,
        y0,
        width,
        height,
        period=48,
        octaves=3,
        persistence_permille=500,
    )
    px = xs + wobble_x * WOBBLE // NOISE_SCALE
    py = ys + wobble_y * WOBBLE // NOISE_SCALE
    base_x = np.floor_divide(px, SITE)
    base_y = np.floor_divide(py, SITE)
    best = np.full((height, width), np.iinfo(np.int64).max, dtype=np.int64)
    cell_x = np.zeros((height, width), dtype=np.int64)
    cell_y = np.zeros((height, width), dtype=np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx = base_x + dx
            cy = base_y + dy
            jitter = hash_grid(key, cx, cy)
            sx = cx * SITE + (jitter & np.uint64(0xFFFF)).astype(np.int64) % SITE
            sy = cy * SITE + ((jitter >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64) % SITE
            distance = (px - sx) ** 2 + (py - sy) ** 2
            closer = distance < best
            best = np.where(closer, distance, best)
            cell_x = np.where(closer, cx, cell_x)
            cell_y = np.where(closer, cy, cell_y)
    return cell_x, cell_y


def site_offset(
    seed: int, cell_x: int, cell_y: int, category: int, categories: NDArray[np.int8]
) -> tuple[int, int]:
    """A deterministic offset whose source area is mostly ``category`` vanilla inland."""
    rows, columns = categories.shape
    jitter = hash_point(derive_seed(seed, "material_sites"), cell_x, cell_y)
    centre_x = cell_x * SITE + (jitter & 0xFFFF) % SITE
    centre_y = cell_y * SITE + ((jitter >> 16) & 0xFFFF) % SITE
    rng = SplitMix64(derive_seed(seed, "material_offset", str(cell_x), str(cell_y), str(category)))
    best = (0, 0)
    best_hits = -1
    for _ in range(TRIES):
        shift = SHIFT_MIN + rng.below(SHIFT_MAX - SHIFT_MIN)
        dx = shift if rng.below(2) else -shift
        dy = rng.below(2 * LATITUDE_SPREAD + 1) - LATITUDE_SPREAD
        hits = 0
        for oy in SAMPLE_GRID:
            row = min(rows - 1, max(0, centre_y + dy + oy))
            for ox in SAMPLE_GRID:
                column = (centre_x + dx + ox) % columns
                hits += int(categories[row, column] == category)
        if hits > best_hits:
            best, best_hits = (dx, dy), hits
        if hits >= ACCEPT:
            break
    return best


def coastal_palette(slots: NDArray[np.int64]) -> list[tuple[int, int]]:
    """Up to three most common slots with permille weights."""
    counts = np.bincount(slots[slots != NO_MATERIAL], minlength=256)[:255]
    top = np.argsort(-counts, kind="stable")[:3]
    total = int(counts[top].sum())
    if total == 0:
        return [(0, 1000)]
    return [(int(slot), int(counts[slot]) * 1000 // total) for slot in top.tolist() if counts[slot]]


def pick(palette: list[tuple[int, int]], noise: NDArray[np.int64]) -> NDArray[np.int64]:
    """Map noise in [-32768, 32767] to palette slots by cumulative weights."""
    share = (noise + NOISE_SCALE) * 1000 // (2 * NOISE_SCALE)
    out = np.full(noise.shape, palette[-1][0], dtype=np.int64)
    limit = 0
    assigned = np.zeros(noise.shape, dtype=bool)
    for slot, weight in palette:
        limit += weight
        here = ~assigned & (share < limit)
        out[here] = slot
        assigned |= here
    return out
