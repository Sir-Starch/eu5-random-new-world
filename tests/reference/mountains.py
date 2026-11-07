"""Pure NumPy mountain stamps on a decal window: the specification of the Rust kernel.

Moved from ``rnw.eu5_mountains.MountainRelief`` when ``stamp`` became native
(docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_mountains import ROTATIONS, UNIT
from rnw.eu5_slots import NO_MATERIAL

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray

    from rnw.eu5_mountains import Mountain, MountainRelief


def _footprints(
    relief: MountainRelief, origin: tuple[int, int], shape: tuple[int, int]
) -> Iterator[tuple[Mountain, tuple[slice, slice], NDArray[np.int64], NDArray[np.int64]]]:
    """Each stamp that reaches a decal window: its placement, the slices of the window it
    covers and the coordinates in its source there (1/1024 pixels, as ``u`` and ``v``).
    """
    column0, row0 = origin
    rows, columns = shape
    bounds = relief.bounds
    near = np.nonzero(
        (bounds[:, 0] < row0 + rows)
        & (bounds[:, 1] >= row0)
        & (bounds[:, 2] < column0 + columns)
        & (bounds[:, 3] >= column0)
    )[0]
    for index in near.tolist():
        stamp = relief.placements[index]
        top = max(row0, int(bounds[index, 0]))
        bottom = min(row0 + rows, int(bounds[index, 1]) + 1)
        left = max(column0, int(bounds[index, 2]))
        right = min(column0 + columns, int(bounds[index, 3]) + 1)
        yy = np.arange(top, bottom, dtype=np.int64)[:, None] - stamp.row
        xx = np.arange(left, right, dtype=np.int64)[None, :] - stamp.column
        cosine, sine = ROTATIONS[stamp.rotation]
        height, width = relief.sources[stamp.source].shape
        u = (xx * cosine + yy * sine) * width // stamp.along + width * UNIT // 2
        v = (yy * cosine - xx * sine) * height // stamp.across + height * UNIT // 2
        window = (slice(top - row0, bottom - row0), slice(left - column0, right - column0))
        yield stamp, window, u, v


def stamp(
    relief: MountainRelief, origin: tuple[int, int], shape: tuple[int, int]
) -> tuple[NDArray[np.int64], NDArray[np.uint8]]:
    """Additive height and material slot of a decal window, stamp by stamp."""
    out = np.zeros(shape, dtype=np.int64)
    # Height times 256 plus the complement of the slot; negative where no slot is laid.
    best = np.full(shape, -1, dtype=np.int64)
    for placed, window, u, v in _footprints(relief, origin, shape):
        source = relief.sources[placed.source]
        height, width = source.shape
        # Source coordinates in 1/1024 pixels, bilinearly sampled with zero
        # outside. A small edge fade removes the source's nonzero boundary.
        ix, iy = u // UNIT, v // UNIT
        valid = (ix >= 0) & (ix < width - 1) & (iy >= 0) & (iy < height - 1)
        x, y = np.clip(ix, 0, width - 2), np.clip(iy, 0, height - 2)
        fx, fy = u % UNIT, v % UNIT
        a = source[y, x].astype(np.int64) * (UNIT - fx) + source[y, x + 1] * fx
        b = source[y + 1, x].astype(np.int64) * (UNIT - fx) + source[y + 1, x + 1] * fx
        value = (a * (UNIT - fy) + b * fy) // (UNIT * UNIT)
        edge = np.minimum(
            np.minimum(u, (width - 1) * UNIT - u), np.minimum(v, (height - 1) * UNIT - v)
        )
        fade = np.clip(edge * 32000 // (max(width, height) * UNIT), 0, 1000)
        value = np.where(valid, value * fade // 1000 * placed.strength // 1000, 0)
        if relief.materials:
            slots = relief.materials[placed.source]
            slot = slots[np.clip(iy, 0, slots.shape[0] - 1), np.clip(ix, 0, slots.shape[1] - 1)]
            laid = (ix >= 0) & (ix < slots.shape[1]) & (iy >= 0) & (iy < slots.shape[0])
            key = np.where(laid & (slot != NO_MATERIAL), value * 256 + 255 - slot, -1)
            target = best[window]
            _ = np.maximum(target, key, out=target)
        target = out[window]
        target += value
    return out, np.where(best >= 0, 255 - best % 256, NO_MATERIAL).astype(np.uint8)
