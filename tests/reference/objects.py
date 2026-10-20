"""Pure NumPy pixel keys and instance sampling: the specification of the Rust kernels.

Moved from ``rnw.eu5_objects`` when they became native (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rng import hash_grid

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_objects import PixelClasses

RECORD_FLOATS: Final[int] = 10
SLOT_CLASSES: Final[int] = 18
NO_SLOT: Final[int] = 17
DENSITY_BITS: Final[int] = 24
CHUNK_ROWS: Final[int] = 1024


def _slot_class(materials: NDArray[np.uint8]) -> NDArray[np.int64]:
    slots = materials.astype(np.int64)
    return np.where(slots >= NO_SLOT, NO_SLOT, slots)


def _pixel_keys(
    classes: PixelClasses, table: NDArray[np.int64], row0: int, row1: int
) -> NDArray[np.int64]:
    """Key (class x slot) of every material pixel in even material rows ``row0:row1``."""
    labels = classes.labels[row0 // 2 : row1 // 2]
    expanded = np.repeat(np.repeat(table[labels], 2, axis=0), 2, axis=1)
    return expanded * SLOT_CLASSES + _slot_class(classes.materials[row0:row1])


def pixel_counts(
    classes: PixelClasses, table: NDArray[np.int64], keys: int, mask: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Material pixels per key among labels where ``mask`` is true."""
    counts = np.zeros(keys * SLOT_CLASSES, dtype=np.int64)
    rows = classes.materials.shape[0]
    for start in range(0, rows, CHUNK_ROWS):
        stop = min(rows, start + CHUNK_ROWS)
        key = _pixel_keys(classes, table, start, stop)
        labels = np.repeat(np.repeat(classes.labels[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        chosen = mask[labels]
        counts += np.bincount(key[chosen], minlength=counts.size)
    return counts


def sample_instances(  # noqa: PLR0913 - sampling needs pixels, densities, source records and seed.
    pixel_rows: NDArray[np.int64],
    pixel_columns: NDArray[np.int64],
    *,
    density: NDArray[np.int64],
    source: NDArray[np.float32],
    rows: int,
    key: int,
) -> NDArray[np.float32]:
    """Records for pixels with fixed-point densities (expected count = density)."""
    first = hash_grid(key, pixel_columns, pixel_rows)
    fraction = (first & np.uint64((1 << DENSITY_BITS) - 1)).astype(np.int64)
    count = (density + fraction) >> DENSITY_BITS
    picked = np.flatnonzero(count)
    if not picked.size or not source.size:
        return np.zeros((0, RECORD_FLOATS), dtype=np.float32)
    repeat = count[picked]
    index = np.repeat(picked, repeat)
    copy = np.arange(index.size, dtype=np.int64) - np.repeat(np.cumsum(repeat) - repeat, repeat)
    second = hash_grid(key ^ 0x5EED, pixel_columns[index] * 8 + copy, pixel_rows[index])
    dx = (second & np.uint64(0xFFFF)).astype(np.int64)
    dz = ((second >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64)
    donor = ((second >> np.uint64(32)) % np.uint64(source.shape[0])).astype(np.int64)
    out = source[donor].copy()
    out[:, 0] = ((pixel_columns[index] * 65536 + dx) / 131072.0).astype(np.float32)
    out[:, 1] = 0.0
    out[:, 2] = (rows - (pixel_rows[index] * 65536 + dz) / 131072.0).astype(np.float32)
    return out


def canvas_pixels(
    classes: PixelClasses, canvas: NDArray[np.bool_]
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """Row, column, fine key and coarse key of every material pixel of the canvas to fill."""
    rows = classes.labels.shape[0]
    canvas_rows: list[NDArray[np.int64]] = []
    canvas_columns: list[NDArray[np.int64]] = []
    fine_keys: list[NDArray[np.int64]] = []
    coarse_keys: list[NDArray[np.int64]] = []
    for start in range(0, rows * 2, CHUNK_ROWS):
        stop = min(rows * 2, start + CHUNK_ROWS)
        labels = np.repeat(np.repeat(classes.labels[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        inside = np.repeat(np.repeat(canvas[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        inside &= classes.label_class[labels] >= 0
        local_rows, local_columns = np.nonzero(inside)
        canvas_rows.append(local_rows + start)
        canvas_columns.append(local_columns)
        fine_keys.append(_pixel_keys(classes, classes.label_class, start, stop)[inside])
        coarse_keys.append(_pixel_keys(classes, classes.label_coarse, start, stop)[inside])
    return (
        np.concatenate(canvas_rows),
        np.concatenate(canvas_columns),
        np.concatenate(fine_keys),
        np.concatenate(coarse_keys),
    )
