"""Procedural north-south barrier with a guaranteed bent land core and coastal relief.

No EU4 map data is used. The barrier follows a route from the north edge of the installed
EU5 canvas to the south edge: a straight line at the chosen position wherever its envelope
fits, and a smooth detour around the protected Old World pixels (islands and their guard
water) wherever it does not. Protected pixels are never annexed to make the barrier fit.
"""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from rnw.fields import SUBPIXEL, fractal_at, value_noise_at
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

PERMILLE = 1000
STRIP_ROWS = 256
# The land share the Wall itself is sized for. A smaller share thins the side land only:
# the barrier takes its land first and the continents beside it share what is left.
BASE_LAND_PERMILLE = 250


# Planning grid. The route is chosen on cells GRID pixels wide and CELL_ROWS rows high, so it
# changes by at most GRID / CELL_ROWS = 0.5 pixel per row, and then smoothed over SMOOTH_ROWS.
GRID = 16
CELL_ROWS = 32
SMOOTH_ROWS = 512
# The smoothing moves the route by under 64 pixels and the grid by under GRID, so the planner
# keeps this much water beyond the envelope.
CLEARANCE = 80
# A column belongs to the span of the position control when this share of its rows is open.
OPEN_PERMILLE = 900


@dataclass(frozen=True, slots=True, eq=False)
class Route:
    """The barrier's envelope: the column of its centre in every row, and its half-width."""

    centre: NDArray[np.int64]
    half: int


def half_width(width: int, settings: NewWorldSettings) -> int:
    """Half-width of the envelope on a canvas ``width`` pixels wide."""
    return max(4, width * settings.wall_width_permille // (2 * PERMILLE))


def _protected_before(rows: NDArray[np.bool_]) -> NDArray[np.int32]:
    """Per row, the protected pixels left of each column (the last entry counts them all)."""
    before = np.zeros((rows.shape[0], rows.shape[1] + 1), dtype=np.int32)
    _ = np.cumsum(~rows, axis=1, dtype=np.int32, out=before[:, 1:])
    return before


def _strip_rows() -> int:
    return CELL_ROWS * max(1, STRIP_ROWS // CELL_ROWS)


def _free_cells(domain: NDArray[np.bool_], pad: int, phase: int) -> NDArray[np.bool_]:
    """Cells (row block, grid column) whose envelope fits and has room to be rounded off.

    The envelope (``pad`` pixels each side) must lie on the canvas; the planner's extra
    clearance must hold no protected pixel. Smoothing is an average of columns on the canvas,
    so the canvas edge itself needs no clearance. Grid column ``n`` is canvas column
    ``n * GRID + phase``, so a target keeps its exact column.
    """
    height, width = domain.shape
    columns = np.arange(width // GRID + 1, dtype=np.int64) * GRID + phase
    inside = (columns - pad >= 0) & (columns + pad < width)
    reach = pad + GRID + CLEARANCE
    low = np.clip(columns - reach, 0, width - 1)
    high = np.clip(columns + reach, 0, width - 1)
    cells = np.empty((-(-height // CELL_ROWS), len(columns)), dtype=bool)
    step = _strip_rows()
    for first in range(0, height, step):
        checkpoint()
        rows = domain[first : first + step]
        before = _protected_before(rows)
        free = ((before[:, high + 1] - before[:, low]) == 0) & inside
        blocks = np.arange(0, len(rows), CELL_ROWS)
        cells[first // CELL_ROWS : first // CELL_ROWS + len(blocks)] = np.logical_and.reduceat(
            free, blocks, axis=0
        )
    return cells


def _span(domain: NDArray[np.bool_], pad: int) -> tuple[int, int]:
    """Westmost and eastmost centre of the position control: the longest open band of columns."""
    height = domain.shape[0]
    shut = height - np.count_nonzero(domain, axis=0)
    ends = np.flatnonzero(
        np.diff(np.pad(shut * PERMILLE <= height * (PERMILLE - OPEN_PERMILLE), 1).astype(np.int8))
    )
    runs = [(int(a), int(b)) for a, b in zip(ends[::2], ends[1::2], strict=True)]
    fits = [(a + pad, b - pad - 1) for a, b in runs if b - a > 2 * pad]
    if not fits:
        message = "The Wall needs a continuous north-south canvas route wide enough for its width"
        raise ValueError(message)
    return max(fits, key=lambda run: run[1] - run[0])


def _plan(cells: NDArray[np.bool_], target: int) -> NDArray[np.int64]:
    """The grid column of a route through the open cells that stays as near ``target`` as it can.

    A route moves at most one cell sideways per row of cells. A backward pass finds the cells
    from which the south edge can still be reached, so the forward pass starts to avoid an
    obstacle early enough and returns to the target as soon as the obstacle is behind it.
    """
    count = len(cells)
    viable = np.zeros_like(cells)
    viable[-1] = cells[-1]
    for block in range(count - 2, -1, -1):
        near = viable[block + 1].copy()
        near[1:] |= viable[block + 1, :-1]
        near[:-1] |= viable[block + 1, 1:]
        viable[block] = cells[block] & near
    if not viable[0].any():
        message = "The Wall needs a continuous north-south canvas route wide enough for its width"
        raise ValueError(message)
    route = np.zeros(count, dtype=np.int64)
    for block in range(count):
        first = 0 if block == 0 else max(0, int(route[block - 1]) - 1)
        last = cells.shape[1] if block == 0 else min(cells.shape[1], int(route[block - 1]) + 2)
        choices = first + np.flatnonzero(viable[block, first:last])
        route[block] = choices[np.argmin(np.abs(choices - target))]
    return route


def _smooth(route: NDArray[np.int64], phase: int, height: int) -> NDArray[np.int64]:
    """Straight segments between the cell centres, rounded off by a moving average."""
    nodes = route * GRID + phase
    if len(nodes) == 1:
        return np.full(height, nodes[0], dtype=np.int64)
    rows = np.arange(height, dtype=np.int64) - CELL_ROWS // 2
    left = np.clip(rows // CELL_ROWS, 0, len(nodes) - 2)
    along = np.clip(rows - left * CELL_ROWS, 0, CELL_ROWS)
    line = nodes[left] + (nodes[left + 1] - nodes[left]) * along // CELL_ROWS
    radius = SMOOTH_ROWS // 2
    total = np.concatenate(([0], np.cumsum(np.pad(line, radius, mode="edge"))))
    return (total[2 * radius + 1 :] - total[: -2 * radius - 1]) // (2 * radius + 1)


def route(domain: NDArray[np.bool_], settings: NewWorldSettings) -> Route:
    """Choose the envelope's route: straight at the chosen position, around protected pixels.

    The position control spans the longest band of columns that is mostly open, west to
    east. The route is a straight line there unless the envelope (with the coast margin)
    would touch a protected pixel: then it detours around the obstacle, and around the whole
    group of islands that leave no room between them, by the shortest smooth way. A canvas
    with no way from the north edge to the south edge is rejected.
    """
    height, width = domain.shape
    half = half_width(width, settings)
    pad = half + settings.coast_margin_px
    west, east = _span(domain, pad)
    target = west + (east - west) * settings.wall_position_permille // PERMILLE
    cells = _free_cells(domain, pad, target % GRID)
    centre = _smooth(_plan(cells, target // GRID), target % GRID, height)
    step = _strip_rows()
    for first in range(0, height, step):
        rows = slice(first, min(height, first + step))
        low, high = centre[rows] - pad, centre[rows] + pad
        before = _protected_before(domain[rows])
        index = np.arange(len(low))
        shut = (low < 0) | (high >= width)
        if (
            shut.any()
            or (before[index, np.clip(high, 0, width - 1) + 1] != before[index, low]).any()
        ):
            message = "The Wall's route would cross protected pixels"
            raise ValueError(message)
    return Route(centre, half)


def core(
    height: int, seed: int, centre: NDArray[np.int64] | int, half: int, settings: NewWorldSettings
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Per-row centre column and half-width of the land that the barrier must always keep.

    The centre drifts and the width swells and narrows along the whole length, so a
    forced core is a bent, broad ridge of land rather than a ruler-straight strip. Both
    stay inside the envelope with room for the coastal jitter that `coast` adds; the width
    never falls below three tenths of the envelope's half-width, so the rows overlap. ``centre``
    is the route of the envelope (or one column, for a straight one).
    """
    ys = np.arange(height, dtype=np.int64)
    period = max(8, settings.feature_px)
    drift = value_noise_at(derive_seed(seed, "wall_core_drift"), ys * 0, ys, period)
    swell = value_noise_at(derive_seed(seed, "wall_core_swell"), ys * 0, ys, max(8, period // 2))
    middle = centre + drift * (3 * half) // (10 * NOISE_SCALE)
    reach = 3 * half // 10 + (swell + NOISE_SCALE) * half // (10 * NOISE_SCALE)
    return middle, reach


def spine(domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> NDArray[np.int64]:
    """The column of the guaranteed land core in every row."""
    course = route(domain, settings)
    return core(domain.shape[0], seed, course.centre, course.half, settings)[0]


def keep_clear(sides: NDArray[np.bool_], course: Route, gap: int) -> None:
    """Clear ``gap`` pixels either side of the route's centre, in every row, in place."""
    columns = np.arange(sides.shape[1], dtype=np.int64)[None, :]
    for first in range(0, len(sides), _strip_rows()):
        checkpoint()
        rows = slice(first, min(len(sides), first + _strip_rows()))
        sides[rows] &= np.abs(columns - course.centre[rows, None]) > gap


def coast(domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> NDArray[np.bool_]:
    """Threshold one continuous density field inside the continental envelope along its route.

    Land share shifts sea level, feature size and octaves set the scale of bays and
    islands, and coastal irregularity controls their strength. A low-density saddle
    can become a strait when continuity is not required; no passages are placed.
    """
    course = route(domain, settings)
    centre, half = course.centre, course.half
    height, _ = domain.shape
    middle, reach = core(height, seed, centre, half, settings)
    result = np.zeros(domain.shape, dtype=bool)
    key = derive_seed(seed, "wall_density")
    for first in range(0, height, STRIP_ROWS):
        checkpoint()
        ys = np.arange(first, min(height, first + STRIP_ROWS), dtype=np.int64)[:, None]
        left, right = int((centre[ys] - half).min()), int((centre[ys] + half).max()) + 1
        xs = np.arange(left, right, dtype=np.int64)[None, :]
        xx, yy = np.broadcast_arrays(xs * SUBPIXEL, ys * SUBPIXEL)
        noise = fractal_at(
            key,
            xx,
            yy,
            period=max(8, settings.feature_px // 3),
            octaves=settings.octaves,
            persistence_permille=settings.persistence_permille,
        )
        # A broad longitudinal field shares the same seed and controls. Its saddles
        # can cross the full envelope; finer octaves form coastal islets and bays.
        profile = fractal_at(
            key,
            yy * 0,
            yy,
            period=max(8, settings.feature_px),
            octaves=settings.octaves,
            persistence_permille=settings.persistence_permille,
        )
        across = np.abs(xs - centre[ys])
        # Coastal noise fades over the envelope's outer quarter, so a coast eases toward its
        # edge instead of being cut off along a straight vertical line there.
        fade = np.clip((half - across) * 4 * PERMILLE // half, 0, PERMILLE)
        density = (
            1600
            - across * 3000 // half
            + (max(settings.land_permille, BASE_LAND_PERMILLE) - BASE_LAND_PERMILLE) * 3
            + (noise * 3 + profile * 3)
            * settings.wall_coast_permille
            * fade
            // (NOISE_SCALE * PERMILLE)
        )
        # The core's edge is ragged like any coast, within an eighth of the envelope.
        edge = np.clip(noise * half // (8 * NOISE_SCALE), -(half // 8), half // 8)
        kept = np.abs(xs - middle[ys]) <= reach[ys] + edge
        polar = (ys < settings.coast_margin_px) | (ys >= height - settings.coast_margin_px)
        solid = ((density > 0) | (kept & (polar | (settings.wall_allow_gaps == 0)))) & (
            across <= half
        )
        result[first : first + len(ys), left:right] = solid
    return result


def add_relief(
    elevation: NDArray[np.int32],
    land: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
) -> None:
    """Raise a meandering longitudinal spine while leaving habitable coastal shelves."""
    course = route(domain, settings)
    half = course.half
    middle = core(len(domain), seed, course.centre, half, settings)[0]
    xs = np.arange(domain.shape[1], dtype=np.int64)[None, :]
    for first in range(0, len(domain), STRIP_ROWS):
        checkpoint()
        rows = slice(first, min(len(domain), first + STRIP_ROWS))
        ys = np.arange(rows.start, rows.stop, dtype=np.int64)[:, None]
        noise = value_noise_at(derive_seed(seed, "wall_spine"), ys * 0, ys, max(8, half))
        ridge = middle[rows][:, None] + noise * half // (8 * NOISE_SCALE)
        strength = np.maximum(0, half // 2 - np.abs(xs - ridge))
        lift = strength * 18000 * settings.wall_ridge_permille // (max(1, half // 2) * PERMILLE)
        elevation[rows] += np.where(land[rows], lift, 0).astype(np.int32)
