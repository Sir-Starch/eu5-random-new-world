"""Pure-Python priority-flood drainage: the specification of the Rust kernel.

Moved from ``rnw.rivers`` when it became native (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rivers import Drainage
from rnw.rng import hash_grid

if TYPE_CHECKING:
    from numpy.typing import NDArray

NOISE_BITS: Final[int] = 16


def drainage(
    land: NDArray[np.bool_], height: NDArray[np.int64], rain: NDArray[np.int64], key: int
) -> Drainage:
    """Priority flood from all water over 8-neighbours; rain accumulated downstream.

    ``land``, ``height`` and ``rain`` are coarse grids. Equal filled heights are taken
    in hashed-noise order, so drainage across flats wanders instead of running straight.
    """
    rows, columns = int(land.shape[0]), int(land.shape[1])
    width = columns + 2
    size = (rows + 2) * width
    padded = np.zeros((rows + 2, width), dtype=bool)
    padded[1:-1, 1:-1] = land
    level = np.zeros((rows + 2, width), dtype=np.int64)
    level[1:-1, 1:-1] = np.maximum(height, 0)
    grid_r, grid_c = np.indices((rows + 2, width), dtype=np.int64)
    noise = (hash_grid(key, grid_c, grid_r) >> np.uint64(64 - NOISE_BITS)).astype(np.int64)
    border = np.ones((rows + 2, width), dtype=bool)
    border[1:-1, 1:-1] = False
    is_land: list[bool] = padded.ravel().tolist()
    levels: list[int] = level.ravel().tolist()
    ties: list[int] = noise.ravel().tolist()
    closed = bytearray(border.ravel().tobytes())
    index_bits = size.bit_length()
    shift = index_bits + NOISE_BITS
    mask = (1 << index_bits) - 1
    parent = [-1] * size
    filled = [0] * size
    offsets = (-width - 1, -width, -width + 1, -1, 1, width - 1, width, width + 1)
    seeds: list[int] = np.flatnonzero(~padded.ravel() & ~border.ravel()).tolist()
    heap = [(ties[index] << index_bits) | index for index in seeds]
    for item in heap:
        closed[item & mask] = 1
    heapq.heapify(heap)
    order: list[int] = []
    while heap:
        index = heapq.heappop(heap) & mask
        base = filled[index]
        if is_land[index]:
            order.append(index)
        for offset in offsets:
            other = index + offset
            if closed[other] or not is_land[other]:
                continue
            closed[other] = 1
            parent[other] = index
            value = max(levels[other], base)
            filled[other] = value
            heapq.heappush(heap, (value << shift) | (ties[other] << index_bits) | other)
    rain_padded = np.zeros((rows + 2, width), dtype=np.int64)
    rain_padded[1:-1, 1:-1] = np.maximum(rain, 0)
    flow: list[int] = rain_padded.ravel().tolist()
    for index in reversed(order):
        flow[parent[index]] += flow[index]
    inner = ((grid_r[1:-1, 1:-1]) * width + grid_c[1:-1, 1:-1]).ravel()
    up = np.array(parent, dtype=np.int64)[inner]
    up_r, up_c = np.divmod(np.maximum(up, 0), width)
    return Drainage(
        parent=np.where(up >= 0, (up_r - 1) * columns + (up_c - 1), -1),
        flow=np.array(flow, dtype=np.int64)[inner],
    )
