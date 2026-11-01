"""Plan continuous ocean corridors on the land-and-water raster before making sea cells.

A coarse water graph finds neighbouring shore stretches. Only crossings that improve
an existing water route are drawn; line-of-sight simplification makes their centre
lines straight where geography permits. The corridor never changes the land mask.

A corridor is made of ordinary sea cells: ``corridor_sites`` puts one cell's site every
sea-cell width along its centre line, the ordinary sites keep clear of the line, and one
Voronoi partition of the water then gives the chain of cells the same irregular borders as
every other cell. ``draw_corridors`` is the band of a corridor, for the pixels it covers.
"""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

import heapq
from itertools import pairwise
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image, ImageDraw

from rnw.rng import hash_point
from rnw.sea_policy import MAX_DETOUR

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

AXIS = 1000
DIAGONAL = 1414
STRIP_ROWS = 1024
# The ordinary sites keep this far from a corridor's centre line (permille of the sea-cell
# width), so the chain's cells are about as wide as any other cell. A site of the chain moves
# along the line by at most the first share and across it by at most the second.
CLEAR_PERMILLE: Final[int] = 750
ALONG_PERMILLE: Final[int] = 170
ACROSS_PERMILLE: Final[int] = 120
PERMILLE: Final[int] = 1000
Path = list[tuple[int, int]]


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


def corridor_paths(  # noqa: C901, PLR0912, PLR0915 - shore diagram and route selection.
    ocean: NDArray[np.bool_],
    bands: NDArray[np.bool_],
    spacing: int,
    *,
    domain: NDArray[np.bool_] | None = None,
) -> list[Path]:
    """The straightened centre lines of the crossings that the generated coasts call for.

    Each is a list of (row, column) vertices, every segment of which lies in water at full
    raster resolution.
    """
    tile = max(1, spacing // 2)
    height, width = ocean.shape
    rows = np.minimum(np.arange(tile // 2, height, tile, dtype=np.int64), height - 1)
    cols = np.minimum(np.arange(tile // 2, width, tile, dtype=np.int64), width - 1)
    if not len(rows) or not len(cols):
        return []
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
        return []
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
    paths: list[Path] = []
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
    return paths


def draw_corridors(
    paths: Sequence[Path], ocean: NDArray[np.bool_], width_px: int
) -> NDArray[np.bool_]:
    """The water of ``ocean`` within ``width_px`` of the centre lines ``paths``."""
    height, width = ocean.shape
    image = Image.new("1", (width, height))
    draw = ImageDraw.Draw(image)
    for path in paths:
        draw.line([(column, row) for row, column in path], fill=1, width=width_px)
    drawn = np.asarray(image)
    result = np.empty(ocean.shape, dtype=bool)
    for first in range(0, height, STRIP_ROWS):
        rows = slice(first, min(height, first + STRIP_ROWS))
        result[rows] = drawn[rows] & ocean[rows]
    return result


def corridor_sites(
    paths: Sequence[Path], ocean: NDArray[np.bool_], spacing: int, key: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Rows and columns of the sites of the cells that make up each corridor.

    A path is cut into as many equal stretches as fit a sea-cell width, and each stretch gets
    one site near its middle, moved a little along the line and across it. A site that the
    move would put on land stays on the line, which lies in water.
    """
    found: list[tuple[int, int]] = []
    for number, path in enumerate(paths):
        lengths = [float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in pairwise(path)]
        total = sum(lengths)
        if total <= 0:
            continue
        count = max(1, round(total / spacing))
        along_px = spacing * ALONG_PERMILLE / PERMILLE
        across_px = spacing * ACROSS_PERMILLE / PERMILLE
        for station in range(count):
            moved = hash_point(key, number, station)
            shift = ((moved & 0xFFFF) / 0xFFFF * 2 - 1) * along_px
            side = (((moved >> 16) & 0xFFFF) / 0xFFFF * 2 - 1) * across_px
            at = min(total, max(0.0, (station + 0.5) * total / count + shift))
            row, column = _point_at(path, lengths, at, side)
            row = min(max(row, 0), ocean.shape[0] - 1)
            column = min(max(column, 0), ocean.shape[1] - 1)
            if not ocean[row, column]:
                row, column = _point_at(path, lengths, at, 0.0)
            if ocean[row, column]:
                found.append((row, column))
    if not found:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    rows, columns = zip(*found, strict=True)
    return np.asarray(rows, dtype=np.int64), np.asarray(columns, dtype=np.int64)


def _point_at(path: Path, lengths: list[float], at: float, side: float) -> tuple[int, int]:
    """The point ``at`` pixels along ``path``, moved ``side`` pixels to the left of its heading.

    ``at`` beyond the end of the path gives the path's last point (moved aside like the rest).
    """
    segments = list(zip(pairwise(path), lengths, strict=True))
    for number, ((first, second), length) in enumerate(segments):
        if at > length and number < len(segments) - 1:
            at -= length
            continue
        share = min(1.0, at / length) if length else 0.0
        row = first[0] + (second[0] - first[0]) * share
        column = first[1] + (second[1] - first[1]) * share
        if length:
            row -= side * (second[1] - first[1]) / length
            column += side * (second[0] - first[0]) / length
        return round(row), round(column)
    return path[-1]


def clear_of_corridors(
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    paths: Sequence[Path],
    radius: float,
) -> NDArray[np.bool_]:
    """Which of the points lie farther than ``radius`` pixels from every path."""
    clear = np.ones(rows.shape, dtype=np.bool_)
    for path in paths:
        for first, second in pairwise(path):
            low_row, high_row = min(first[0], second[0]) - radius, max(first[0], second[0]) + radius
            low_col, high_col = (
                min(first[1], second[1]) - radius,
                max(first[1], second[1]) + radius,
            )
            near = np.flatnonzero(
                clear & (rows >= low_row) & (rows <= high_row)
                & (columns >= low_col) & (columns <= high_col)
            )  # fmt: skip
            if not near.size:
                continue
            step = np.array([second[0] - first[0], second[1] - first[1]], dtype=np.float64)
            square = float(step @ step)
            offset = np.stack([rows[near] - first[0], columns[near] - first[1]], axis=1).astype(
                np.float64
            )
            share = np.clip(offset @ step / square, 0.0, 1.0) if square else np.zeros(near.size)
            gap = offset - share[:, np.newaxis] * step
            clear[near[np.hypot(gap[:, 0], gap[:, 1]) <= radius]] = False
    return clear
