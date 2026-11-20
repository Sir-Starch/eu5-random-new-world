"""The shape of a land bridge between a continent and the land beside it.

A bridge is a ridge of land, not a corridor: its axis is the cheapest route over a noisy
landscape (so it bends where a river valley would), smoothed until no corner is left, and its
body swells and narrows along the axis with the same irregular edge as every other coast. This
module holds the integer geometry; ``newworld`` chooses the shore, the noise and what to keep.
"""

# pyright: reportAny=false

from __future__ import annotations

import heapq
from itertools import pairwise
from math import isqrt
from typing import TYPE_CHECKING, Final, NamedTuple

import numpy as np

from rnw.noise import NOISE_SCALE
from rnw.rng import mix64
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray


def _swept(dy: int, dx: int) -> tuple[tuple[int, int], ...]:
    """The blocks beside a move that it passes between: they must be free too, so that a route
    cannot slip through a diagonal gap or hop a wall one block thick."""
    tall, wide = abs(dy), abs(dx)
    if not (tall and wide):
        return ()
    if tall == wide == 1:
        return ((dy, 0), (0, dx))
    if tall > wide:
        return ((dy // tall, 0), (dy // tall, dx))
    if wide > tall:
        return ((0, dx // wide), (dy, dx // wide))
    return ()


# The 16 moves of a route (the four steps, the four diagonals and the eight knight moves) with
# their lengths in thousandths of a block and the blocks they pass between, so a route has no
# preferred direction to speak of.
_MOVES: Final[tuple[tuple[int, int, int, tuple[tuple[int, int], ...]], ...]] = tuple(
    (dy, dx, round(1000 * (dy * dy + dx * dx) ** 0.5), _swept(dy, dx))
    for dy, dx in (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
        (-2, -1),
        (-2, 1),
        (2, -1),
        (2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
    )
)
SMOOTHING_ROUNDS: Final[int] = 3
UNIT: Final[int] = 1000


class NoRouteError(ValueError):
    """No route joins the start to the goal over the passable blocks."""


def route(
    cost: NDArray[np.int32],
    passable: NDArray[np.bool_],
    start: tuple[int, int],
    goal: NDArray[np.bool_],
) -> list[tuple[int, int]]:
    """The cheapest route of block positions from ``start`` to any ``goal`` block.

    ``cost`` is the price of crossing one block, in thousandths of a block of plain ground (at
    least ``UNIT``); a route may cross only ``passable`` blocks. A* with the straight distance
    to the goal as its guide, so a route over open ground reads few blocks. Ties go to the
    lowest block index, so the result is the same on every platform.
    """
    height, width = (int(size) for size in cost.shape)
    if not passable[start] or not goal.any():
        raise NoRouteError
    # Eighths of a block to the nearest goal block, as thousandths of a block of plain ground.
    guide = (euclidean_distance(goal, 4 * (height + width)) * (UNIT // 8)).ravel()
    flat_cost = cost.astype(np.int64).ravel()
    free = passable.ravel()
    target = goal.ravel()
    begin = start[0] * width + start[1]
    best = {begin: 0}
    parent: dict[int, int] = {}
    queue = [(int(guide[begin]), begin)]
    done: set[int] = set()
    while queue:
        _, here = heapq.heappop(queue)
        if here in done:
            continue
        if target[here]:
            nodes = [here]
            while nodes[-1] in parent:
                nodes.append(parent[nodes[-1]])
            return [divmod(node, width) for node in reversed(nodes)]
        done.add(here)
        row, column = divmod(here, width)
        spent = best[here]
        for dy, dx, length, between in _MOVES:
            y, x = row + dy, column + dx
            if not (0 <= y < height and 0 <= x < width):
                continue
            there = y * width + x
            if not free[there] or there in done:
                continue
            if not all(free[(row + by) * width + column + bx] for by, bx in between):
                continue
            price = spent + length * (int(flat_cost[here]) + int(flat_cost[there])) // (2 * UNIT)
            if price < best.get(there, price + 1):
                best[there] = price
                parent[there] = here
                heapq.heappush(queue, (price + int(guide[there]), there))
    raise NoRouteError


class Winding(NamedTuple):
    """How a route is made to wind: a waypoint every ``spacing`` blocks, ``low`` to ``high``
    blocks to its side (drawn from ``key``)."""

    spacing: int
    low: int
    high: int
    key: int


def _waypoint(
    blocks: Sequence[tuple[int, int]],
    index: int,
    size: int,
    side: int,
    passable: NDArray[np.bool_],
) -> tuple[int, int] | None:
    """The point ``size`` blocks to ``side`` (1 left, -1 right) of ``blocks[index]``, across the
    route's direction there; the other side, then half and a quarter of the distance, when the
    first is not passable; None when none is."""
    (before_row, before_column), (after_row, after_column) = (
        blocks[max(0, index - 4)],
        blocks[min(len(blocks) - 1, index + 4)],
    )
    along_row, along_column = after_row - before_row, after_column - before_column
    length = max(1, isqrt(along_row * along_row + along_column * along_column))
    row, column = blocks[index]
    for reach in (size, size // 2, size // 4):
        for direction in (side, -side):
            point = (
                row - along_column * direction * reach // length,
                column + along_row * direction * reach // length,
            )
            if (
                reach > 0
                and 0 <= point[0] < passable.shape[0]
                and 0 <= point[1] < passable.shape[1]
                and passable[point]
            ):
                return point
    return None


def wind(
    blocks: Sequence[tuple[int, int]],
    cost: NDArray[np.int32],
    passable: NDArray[np.bool_],
    goal: NDArray[np.bool_],
    winding: Winding,
) -> list[tuple[int, int]]:
    """A route made to wind: ``blocks`` again, through points to either side of it in turn.

    A route of at least ``winding.spacing`` blocks gets a point every spacing blocks (at least
    two), taken on its side, to the left and to the right in turn, by ``winding.low`` to
    ``winding.high`` blocks, or by as much of it as is passable; the new route goes through them.
    A route shorter than a spacing stays as it is, and so does one that cannot go through its
    points.
    """
    spacing, low, high, key = winding
    if len(blocks) < spacing:
        return list(blocks)
    count = max(2, len(blocks) // spacing)
    points = [blocks[0]]
    for number in range(1, count + 1):
        size = low + mix64(key ^ (number * 0x9E3779B97F4A7C15)) % (high - low + 1)
        point = _waypoint(
            blocks,
            number * len(blocks) // (count + 1),
            size,
            1 if number % 2 else -1,
            passable,
        )
        if point is not None:
            points.append(point)
    longer: list[tuple[int, int]] = [blocks[0]]
    try:
        for start, stop in pairwise(points):
            here = np.zeros_like(goal)
            here[stop] = True
            longer.extend(route(cost, passable, start, here)[1:])
        longer.extend(route(cost, passable, points[-1], goal)[1:])
    except NoRouteError:
        return list(blocks)
    return longer


def smooth(
    points: Sequence[tuple[int, int]], rounds: int = SMOOTHING_ROUNDS
) -> list[tuple[int, int]]:
    """Cut the corners of a polyline ``rounds`` times (Chaikin), keeping both ends.

    Positions are carried in fractions of a pixel (``4**rounds`` to the pixel), so the result is
    exact integer arithmetic; the returned points are rounded to pixels.
    """
    scale = 4**rounds
    line = [(y * scale, x * scale) for y, x in points]
    for _ in range(rounds):
        cut = [line[0]]
        for (y0, x0), (y1, x1) in pairwise(line):
            cut.append(((3 * y0 + y1) // 4, (3 * x0 + x1) // 4))
            cut.append(((y0 + 3 * y1) // 4, (x0 + 3 * x1) // 4))
        cut.append(line[-1])
        line = cut
    return [((y + scale // 2) // scale, (x + scale // 2) // scale) for y, x in line]


def trace(points: Sequence[tuple[int, int]]) -> NDArray[np.int64]:
    """Every pixel of a polyline in order, as rows of (row, column, distance along it).

    The distance counts the larger of the two coordinate steps of each segment, which is the
    number of pixels the segment crosses; the segments are drawn by integer interpolation.
    """
    out: list[NDArray[np.int64]] = []
    travelled = 0
    for (y0, x0), (y1, x1) in pairwise(points):
        steps = max(abs(y1 - y0), abs(x1 - x0))
        if steps == 0:
            continue
        along = np.arange(steps, dtype=np.int64)
        rows = y0 + ((y1 - y0) * along * 2 + np.sign(y1 - y0) * steps) // (2 * steps)
        columns = x0 + ((x1 - x0) * along * 2 + np.sign(x1 - x0) * steps) // (2 * steps)
        out.append(np.stack([rows, columns, travelled + along], axis=1))
        travelled += steps
    last = points[-1]
    out.append(np.array([[last[0], last[1], travelled]], dtype=np.int64))
    return np.concatenate(out)


def lattice(key: int, length: int, period: int) -> NDArray[np.int64]:
    """Smooth one-dimensional noise along ``length`` pixels, in 0..``NOISE_SCALE``.

    Values are drawn at every ``period`` pixels and joined by smoothsteps.
    """
    nodes = length // period + 2
    values = np.array(
        [mix64(key ^ (index * 0x9E3779B97F4A7C15)) % NOISE_SCALE for index in range(nodes)]
    )
    position = np.arange(length + 1, dtype=np.int64)
    index, fraction = position // period, (position % period) * NOISE_SCALE // period
    blend = fraction * fraction * (3 * NOISE_SCALE - 2 * fraction) // (NOISE_SCALE * NOISE_SCALE)
    return (values[index] * (NOISE_SCALE - blend) + values[index + 1] * blend) // NOISE_SCALE


def swell(length: int, flare: int) -> NDArray[np.int64]:
    """How far from either end of a ``length``-pixel axis the body is flared: 0..``NOISE_SCALE``.

    ``NOISE_SCALE`` at an end, falling smoothly to zero ``flare`` pixels in.
    """
    position = np.arange(length + 1, dtype=np.int64)
    nearest = np.minimum(position, length - position)
    unit = np.clip(nearest, 0, flare) * NOISE_SCALE // max(1, flare)
    smooth_unit = unit * unit * (3 * NOISE_SCALE - 2 * unit) // (NOISE_SCALE * NOISE_SCALE)
    return NOISE_SCALE - smooth_unit


def paint(
    axis: NDArray[np.int64],
    radius: NDArray[np.int64],
    edge: NDArray[np.int32],
    *,
    roughness_permille: int,
    every: int,
) -> NDArray[np.bool_]:
    """The union of discs along an axis, their edge pushed in and out by ``edge``.

    The land lies in the shape of ``edge``. ``axis`` holds (row, column, distance) rows and
    ``radius`` the disc radius at each distance; a disc is painted at every ``every``-th pixel of
    the axis (and at its end). A pixel is land when its distance from a centre is below the
    radius times ``1 + roughness_permille * edge / 1000 / NOISE_SCALE``, where ``edge`` is a
    noise spanning ``NOISE_SCALE`` centred on zero (so ``roughness_permille`` is twice the share
    of the radius that the edge swings by). The same noise lies under every disc that reaches a
    pixel, so the discs do not show.
    """
    height, width = edge.shape
    out = np.zeros(edge.shape, dtype=bool)
    chosen = np.arange(0, len(axis), every)
    if chosen[-1] != len(axis) - 1:
        chosen = np.append(chosen, len(axis) - 1)
    for index in chosen:
        row, column, along = (int(value) for value in axis[index])
        reach = int(radius[along]) * (2000 + roughness_permille) // 2000 + 1
        rows = slice(max(0, row - reach), min(height, row + reach + 1))
        columns = slice(max(0, column - reach), min(width, column + reach + 1))
        if rows.start >= rows.stop or columns.start >= columns.stop:
            continue
        y = np.arange(rows.start, rows.stop, dtype=np.int64)[:, None] - row
        x = np.arange(columns.start, columns.stop, dtype=np.int64)[None, :] - column
        grown = NOISE_SCALE + roughness_permille * edge[rows, columns].astype(np.int64) // 1000
        out[rows, columns] |= (y * y + x * x) * NOISE_SCALE * NOISE_SCALE < (
            int(radius[along]) ** 2 * grown * grown
        )
    return out
