"""River references: priority-flood drainage (the Rust kernel's specification) and the
whole-raster valley carving, network checks and coarse statistics that the strip versions
of ``rnw.rivers`` must equal.

Moved from ``rnw.rivers`` (docs/adr/0005-native-core.md).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, block_mean, smoothstep
from rnw.rivers import BODY, JOIN, NONE, SOURCE, STEP, Drainage
from rnw.rng import hash_grid
from rnw.topology import euclidean_distance, label_components, nearest_label

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


def carve_valleys(
    relief: NDArray[np.int64],
    classes: NDArray[np.int8],
    *,
    depths: tuple[int, ...],
    radius_px: int,
    floor: int,
) -> NDArray[np.int64]:
    """Lower ``relief`` around river pixels: ``depths[class]`` at the river, easing to
    nothing at ``radius_px``; land never drops below ``floor``. Water (0) is kept."""
    river = classes >= 0
    if not np.any(river):
        return relief
    distance = euclidean_distance(river, radius_px)
    nearest = nearest_label(classes.astype(np.int32), river, radius_px + 1)
    depth = np.array(depths, dtype=np.int64)[np.maximum(nearest, 0)]
    ease = PERMILLE - smoothstep(distance, 0, radius_px * 8)
    carve = np.where(nearest >= 0, depth * ease // PERMILLE, 0)
    land = relief > 0
    return np.where(land, np.maximum(relief - carve, np.minimum(relief, floor)), relief)


def network_problems(role: NDArray[np.int8], water: NDArray[np.bool_]) -> dict[str, int]:
    """Violations of the river raster rules (all zero for a valid network).

    Sources have one river neighbour, joins two, other pixels two (or one at a free
    end, or three beside exactly one join); no 2x2 blocks; each connected network has
    exactly one source and at least one end at or in water.
    """
    river = role != NONE
    padded = np.pad(river, 1)
    degree = (
        padded[:-2, 1:-1].astype(np.int64) + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    )
    join = np.pad(role == JOIN, 1)
    joins = join[:-2, 1:-1].astype(np.int64) + join[2:, 1:-1] + join[1:-1, :-2] + join[1:-1, 2:]
    wet = np.pad(water, 1)
    near_water = wet[:-2, 1:-1] | wet[2:, 1:-1] | wet[1:-1, :-2] | wet[1:-1, 2:] | water
    body = role == BODY
    ends = body & (degree == 1)
    components = label_components(np.where(river, 1, 0).astype(np.int32))
    size = int(components.max()) + 1
    networks = np.unique(components[river])
    sources = np.bincount(components[role == SOURCE], minlength=size)[networks]
    mouths = np.bincount(components[ends & near_water], minlength=size)[networks]
    return {
        "bad_sources": int(np.count_nonzero((role == SOURCE) & (degree != 1))),
        "bad_joins": int(np.count_nonzero((role == JOIN) & (degree != 2))),
        "bad_body": int(np.count_nonzero(body & ((degree == 0) | (degree > 3)))),
        "bad_confluences": int(np.count_nonzero(body & (degree == 3) & (joins != 1))),
        "blocks": int(
            np.count_nonzero(river[:-1, :-1] & river[1:, :-1] & river[:-1, 1:] & river[1:, 1:])
        ),
        "networks_without_one_source": int(np.count_nonzero(sources != 1)),
        "networks_without_mouth": int(np.count_nonzero(mouths == 0)),
    }


def coarse_land_and_height(
    land: NDArray[np.bool_], height: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Land share (permille) and weighted land height of every STEP x STEP block."""
    count = block_mean(land.astype(np.int64) * PERMILLE, STEP)
    weight = block_mean(np.where(land, height, 0), STEP)
    return count, weight
