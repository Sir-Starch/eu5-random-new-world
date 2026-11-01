"""Plan continuous ocean corridors on the land-and-water raster before making sea cells.

A coarse water graph finds neighbouring shore stretches. Only crossings that improve
an existing water route are drawn; line-of-sight simplification makes their centre
lines straight where geography permits. The final corridor is clipped to water and
never changes the land mask.
"""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

from rnw.sea_policy import MAX_DETOUR

if TYPE_CHECKING:
    from numpy.typing import NDArray

AXIS = 1000
DIAGONAL = 1414
STRIP_ROWS = 1024


def _graph(water: NDArray[np.bool_]) -> dict[int, list[tuple[int, int]]]:
    height, width = water.shape
    links: dict[int, list[tuple[int, int]]] = {}
    for row, column in zip(*np.nonzero(water), strict=True):
        r, c = int(row), int(column)
        neighbours: list[tuple[int, int]] = []
        for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < height and 0 <= cc < width and water[rr, cc]):
                continue
            if dr and dc and not (water[r, cc] and water[rr, c]):
                continue
            neighbours.append((rr * width + cc, DIAGONAL if dr and dc else AXIS))
        links[r * width + c] = sorted(neighbours)
    return links


def _shore(water: NDArray[np.bool_]) -> NDArray[np.bool_]:
    padded = np.pad(water, 1)
    return water & (~padded[:-2, 1:-1] | ~padded[2:, 1:-1] | ~padded[1:-1, :-2] | ~padded[1:-1, 2:])


def _distance_to_allowed(
    links: dict[int, list[tuple[int, int]]], start: int, end: int, allowed: set[int], limit: int
) -> bool:
    best = {start: 0}
    queue = [(0, start)]
    while queue:
        distance, cell = heapq.heappop(queue)
        if distance != best[cell]:
            continue
        if cell == end:
            return True
        for other, length in links[cell]:
            candidate = distance + length
            if (
                other in allowed
                and candidate <= limit
                and candidate < best.get(other, candidate + 1)
            ):
                best[other] = candidate
                heapq.heappush(queue, (candidate, other))
    return False


def _pixel_line(a: tuple[int, int], b: tuple[int, int], ocean: NDArray[np.bool_]) -> bool:
    """A centre line must remain in water at full raster resolution."""
    r0, c0 = a
    r1, c1 = b
    steps = max(abs(r1 - r0), abs(c1 - c0))
    if steps == 0:
        return bool(ocean[r0, c0])
    previous = (r0, c0)
    for n in range(steps + 1):
        row = (r0 * (steps - n) + r1 * n) // steps
        col = (c0 * (steps - n) + c1 * n) // steps
        if not ocean[row, col]:
            return False
        if (
            row != previous[0]
            and col != previous[1]
            and not (ocean[row, previous[1]] or ocean[previous[0], col])
        ):
            return False
        previous = (row, col)
    return True


def _straighten(
    path: list[int], width: int, tile: int, ocean: NDArray[np.bool_]
) -> list[tuple[int, int]]:
    height, pixels_wide = ocean.shape
    points = [
        (
            min(height - 1, (cell // width) * tile + tile // 2),
            min(pixels_wide - 1, (cell % width) * tile + tile // 2),
        )
        for cell in path
    ]
    result = [points[0]]
    at = 0
    while at < len(points) - 1:
        end = len(points) - 1
        while end > at and not _pixel_line(points[at], points[end], ocean):
            end -= 1
        if end == at:
            return []
        result.append(points[end])
        at = end
    return result


def designed_corridors(  # noqa: C901, PLR0912, PLR0915 - shore diagram and route selection.
    ocean: NDArray[np.bool_],
    bands: NDArray[np.bool_],
    spacing: int,
    *,
    domain: NDArray[np.bool_] | None = None,
) -> NDArray[np.bool_]:
    """Return water-only, straightened crossing bands derived from the generated coasts."""
    tile = max(1, spacing // 2)
    height, width = ocean.shape
    rows = np.minimum(np.arange(tile // 2, height, tile, dtype=np.int64), height - 1)
    cols = np.minimum(np.arange(tile // 2, width, tile, dtype=np.int64), width - 1)
    if not len(rows) or not len(cols):
        return np.zeros(ocean.shape, dtype=bool)
    water = ocean[np.ix_(rows, cols)]
    if domain is None:
        shore = _shore(water)
    else:
        if domain.shape != ocean.shape:
            message = "Ocean route domain does not fit its water"
            raise ValueError(message)
        inside = domain[np.ix_(rows, cols)]
        land = np.pad(inside & ~water, 1)
        shore = water & (land[:-2, 1:-1] | land[2:, 1:-1] | land[1:-1, :-2] | land[1:-1, 2:])
        # Outside the replacement domain is not a coastline. Only inherited
        # currents entering there supply offshore route terminals.
        shore |= water & bands[np.ix_(rows, cols)] & _shore(inside)
    links = _graph(water)
    if not links or not np.any(shore):
        return np.zeros(ocean.shape, dtype=bool)
    grid_width = water.shape[1]
    coast = {int(r) * grid_width + int(c) for r, c in zip(*np.nonzero(shore), strict=True)}
    # Area divided by shoreline is a geographic width, not a fixed number of continents.
    spacing_cells = max(1, len(links) // len(coast))
    best: dict[int, tuple[int, tuple[int, int]]] = {}
    parents: dict[int, int] = {}
    queue: list[tuple[int, tuple[int, int], int]] = []
    for cell in sorted(coast):
        r, c = divmod(cell, grid_width)
        owner = (r // spacing_cells, c // spacing_cells)
        best[cell] = (0, owner)
        heapq.heappush(queue, (0, owner, cell))
    while queue:
        distance, owner, cell = heapq.heappop(queue)
        if best[cell] != (distance, owner):
            continue
        for other, length in links[cell]:
            candidate = (distance + length, owner)
            if other not in best or candidate < best[other]:
                best[other] = candidate
                parents[other] = cell
                heapq.heappush(queue, (*candidate, other))
    crossings: dict[tuple[tuple[int, int], tuple[int, int]], tuple[int, int, int]] = {}
    for cell, neighbours in links.items():
        if cell not in best:
            continue
        distance, owner = best[cell]
        for other, length in neighbours:
            if other not in best or best[other][1] == owner:
                continue
            other_distance, other_owner = best[other]
            pair = (min(owner, other_owner), max(owner, other_owner))
            candidate = (distance + length + other_distance, min(cell, other), max(cell, other))
            if candidate < crossings.get(pair, (1 << 62, 1 << 62, 1 << 62)):
                crossings[pair] = candidate
    allowed = set(coast)
    # Two typical sea-cell widths from shore are already navigable.
    frontier = set(coast)
    for _ in range((2 * spacing + tile - 1) // tile):
        frontier = {other for cell in frontier for other, _ in links[cell]} - allowed
        allowed.update(frontier)
    paths: list[list[tuple[int, int]]] = []
    for distance, first, second in sorted(crossings.values()):
        left, right = [first], [second]
        while left[-1] in parents:
            left.append(parents[left[-1]])
        while right[-1] in parents:
            right.append(parents[right[-1]])
        start, end = left[-1], right[-1]
        if _distance_to_allowed(links, start, end, allowed, MAX_DETOUR * distance):
            continue
        path = list(reversed(left)) + right
        straight = _straighten(path, grid_width, tile, ocean)
        if not straight:
            continue
        paths.append(straight)
        allowed.update(path)
    image = Image.new("1", (width, height))
    draw = ImageDraw.Draw(image)
    for path in paths:
        draw.line([(column, row) for row, column in path], fill=1, width=spacing)
    drawn = np.asarray(image)
    result = np.empty(ocean.shape, dtype=bool)
    for first in range(0, height, STRIP_ROWS):
        rows = slice(first, min(height, first + STRIP_ROWS))
        result[rows] = drawn[rows] & ocean[rows]
    return result
