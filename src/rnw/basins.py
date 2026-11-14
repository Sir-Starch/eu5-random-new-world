"""Basins graded along the drainage of the land (epoch 64, ``epoch.BASINS``).

A structural relief (``rnw.relief``) gives a continent its cordilleras, its hill country and the
slope its rivers follow, and its drainage is planned on it (``watersheds.plan_drainage``). Real
continents are then worn down by that drainage: a river grades its bed to the sea, steeply where
its catchment is small and ever more gently as it grows (the slope of a graded bed falls with the
square root of the catchment), and the great rivers spread broad, low plains far inland (the
Amazon, the Congo, the Mississippi, the Paraná, the Ganges, Mesopotamia), where a continent's
floodplains and marshes lie, while hill country keeps its hills on a lower base and the
cordilleras stand above it all.

On the coarse grid of each watershed domain's drainage tree, the square root of every cell's
catchment (in cells) is widened into a cone that falls by ``cone_slope`` a cell around the larger
rivers, so a river's plain is as wide as its basin is large. A graded bed rises from the coast up
the tree by the landmass's ``gradient`` over the widened root at every step. The base of the land
(its mean height over ``base_blur`` cells around) is lowered to that bed, less on high ground
(``mountains``), not at all where a drawing paints mountains and not on the hard old rock of the
shields, which a slow noise places on a share of each landmass; the lowering is smoothed over
``smoothing`` cells and added to the relief, so hills and valleys smaller than the base keep their
shape and a pixel as high as ``standing`` (a narrow range, the Wall) stands. How gently a
landmass's rivers fall and how much of it is shield are drawn for each landmass, so every
continent's basins lie at their own height. The plan is not changed: the export draws the same
rivers along it, and the larger rivers climb no more often than on the relief they were planned
on. Integer arithmetic.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, block_mean, box_blur, smoothstep, upsample, warped_noise
from rnw.relief import COAST_HEIGHT, HINT_HIGH, HINT_LOW, HINT_STEP
from rnw.rivers import STEP, accumulate, upstream_order
from rnw.rng import derive_seed
from rnw.topology import label_components
from rnw.watersheds import plan_spans

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.relief import ReliefHints
    from rnw.watersheds import DrainagePlan


@dataclass(frozen=True, slots=True)
class BasinSettings:
    """Height units, drainage cells (``rivers.STEP`` pixels) and square roots of catchments."""

    cone_slope: int  # permille of a root of the catchment lost per cell away from a river
    gradient: tuple[int, int]  # a landmass's graded fall per cell times the root, drawn between
    base: int  # the graded bed at the coast, above COAST_HEIGHT
    mountains: tuple[int, int]  # the base height over which the land is lowered less and then not
    standing: tuple[int, int]  # the height of a pixel over which it is lowered less and then not
    base_blur: int  # cells around a cell whose mean land height is its base
    smoothing: int  # cells the lowering is smoothed over
    shield_share: tuple[int, int]  # permille of a landmass of hard old rock, drawn between
    shield_period: int  # pixels of the noise that places the shields
    shield_edge: int  # noise units over which the rock softens at a shield's edge


BASINS: Final[BasinSettings] = BasinSettings(
    cone_slope=2000,
    gradient=(300, 1500),
    base=100,
    mountains=(12000, 16000),
    standing=(14000, 18000),
    base_blur=8,
    smoothing=3,
    shield_share=(0, 600),
    shield_period=2400,
    shield_edge=6000,
)
STRIP_ROWS: Final[int] = 512  # rows of the raster read or changed at a time (a multiple of STEP)
CONE_BLOCK: Final[int] = 4  # drainage cells a side of the blocks the cones are widened over
SQRT2_PERMILLE: Final[int] = 1414
PAINTED_RISE: Final[int] = 20000  # the bed under fully painted mountains rises this much
MOVES: Final[tuple[tuple[int, int, int], ...]] = (
    (1, 0, PERMILLE),
    (-1, 0, PERMILLE),
    (0, 1, PERMILLE),
    (0, -1, PERMILLE),
    (1, 1, SQRT2_PERMILLE),
    (1, -1, SQRT2_PERMILLE),
    (-1, 1, SQRT2_PERMILLE),
    (-1, -1, SQRT2_PERMILLE),
)


@dataclass(frozen=True, slots=True, eq=False)
class _Grid:
    """The plan's trees on one grid of drainage cells over the whole domain.

    The trees of the watershed domains (``watersheds.plan_spans``) have their own grids, each
    starting at its span's first column; every cell of a span is the cell of this grid that holds
    its centre, so the cells of the two sides of the seam are neighbours here and the slope can
    be limited across it. ``links`` is each cell's downstream cell (-1: none), ``over`` the land
    and lakes the trees drain, ``order`` the groups of ``rivers.upstream_order``."""

    over: NDArray[np.bool_]
    links: NDArray[np.int64]
    catchment: NDArray[np.int64]
    order: tuple[NDArray[np.int64], ...]
    between: tuple[int, ...]  # columns of cells between the spans, outside every tree


def _grid(rows: int, columns: int, plan: DrainagePlan) -> _Grid:
    shape = (-(-rows // STEP), -(-columns // STEP) + 1)
    over = np.zeros(shape, dtype=bool)
    links = np.full(shape[0] * shape[1], -1, dtype=np.int64)
    catchment = np.zeros(shape, dtype=np.int64)
    covered = np.zeros(shape[1], dtype=bool)
    for (left, right), parent in zip(plan_spans(columns, plan.seam), plan.parents, strict=True):
        width = -(-(right - left) // STEP)
        local = parent.astype(np.int64).reshape(shape[0], width)
        target = (left + np.arange(width, dtype=np.int64) * STEP + STEP // 2) // STEP
        covered[target] = True
        here = local >= 0
        over[:, target] = here
        index = np.arange(shape[0], dtype=np.int64)[:, np.newaxis] * shape[1] + target
        downstream = np.where(here, local, 0)
        moved = index.ravel()[downstream.ravel()].reshape(local.shape)
        links.reshape(shape)[:, target] = np.where(here, moved, -1)
        catchment[:, target] = accumulate(local, here.astype(np.int64).ravel()).reshape(local.shape)
    # A column of cells between the spans (at the seam) is land where land is beside it.
    between = tuple(
        int(column)
        for column in np.flatnonzero(~covered[1:-1]) + 1
        if covered[column - 1] and covered[column + 1]
    )
    for column in between:
        over[:, column] = over[:, column - 1] | over[:, column + 1]
    return _Grid(over, links, catchment, tuple(upstream_order(links)), between)


def _window(size: int, offset: int) -> slice:
    return slice(max(offset, 0), size + min(offset, 0))


def widened(
    catchment: NDArray[np.int64], over: NDArray[np.bool_], settings: BasinSettings
) -> NDArray[np.int64]:
    """The square root of each cell's catchment in permille, widened into a cone that falls by
    ``cone_slope`` a cell around every river over the land and lakes (on blocks of ``CONE_BLOCK``
    cells, each holding its largest root, interpolated back to the cells)."""
    roots = np.floor(np.sqrt(np.maximum(catchment, 0).astype(np.float64))).astype(np.int64)
    roots = np.where(over, roots * PERMILLE, 0)
    rows, columns = roots.shape
    pad = ((0, -rows % CONE_BLOCK), (0, -columns % CONE_BLOCK))
    blocks = (-(-rows // CONE_BLOCK), CONE_BLOCK, -(-columns // CONE_BLOCK), CONE_BLOCK)
    cone = np.pad(roots, pad).reshape(blocks).max(axis=(1, 3))
    land = np.pad(over, pad).reshape(blocks).any(axis=(1, 3))
    height, width = cone.shape
    while True:
        before = cone.copy()
        for down, right, length in MOVES:
            fall = settings.cone_slope * CONE_BLOCK * length // PERMILLE
            target = cone[_window(height, down), _window(width, right)]
            source = cone[_window(height, -down), _window(width, -right)]
            _ = np.maximum(target, source - fall, out=target)
            cone[~land] = 0
        if np.array_equal(cone, before):
            break
    half = CONE_BLOCK // 2
    padded = np.pad(cone, ((1, 2), (1, 2)), mode="edge")
    fine = upsample(padded, CONE_BLOCK, ((height + 1) * CONE_BLOCK, (width + 1) * CONE_BLOCK))
    fine = fine[half : half + rows, half : half + columns]
    return np.where(over, np.maximum(roots, fine), 0)


def _hint_cells(
    hints: ReliefHints | None, shape: tuple[int, int]
) -> tuple[NDArray[np.int64] | None, NDArray[np.int64] | None]:
    """The painted mountains and lowlands at the centre of each drainage cell, in permille."""
    if hints is None:
        return None, None
    rows = (np.arange(shape[0], dtype=np.int64) * STEP + STEP // 2) // HINT_STEP
    columns = (np.arange(shape[1], dtype=np.int64) * STEP + STEP // 2) // HINT_STEP
    out: list[NDArray[np.int64] | None] = []
    for painted in (hints.mountains, hints.lowlands):
        if not painted.any():
            out.append(None)
            continue
        sampled = painted[
            np.minimum(rows, painted.shape[0] - 1)[:, np.newaxis],
            np.minimum(columns, painted.shape[1] - 1)[np.newaxis, :],
        ].astype(np.int64)
        out.append(smoothstep(sampled, HINT_LOW, HINT_HIGH))
    return out[0], out[1]


def _landmass_draws(
    over: NDArray[np.bool_], seed: int, settings: BasinSettings
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The graded fall and the softness (permille) of every cell. Each landmass (numbered in raster
    order) draws its fall and the share of it that is hard old rock between the bounds of
    ``settings``; a slow noise places the hard rock on its highest values (``shield_period``),
    softening over ``shield_edge`` at the shields' edges."""
    parts = label_components(np.where(over, 1, 0).astype(np.int32))
    period = settings.shield_period // STEP
    noise = warped_noise(
        derive_seed(seed, "basin_shields"),
        over.shape,
        step=8,
        period=period,
        octaves=3,
        warp_px=period // 3,
    )
    fall = np.zeros(over.shape, dtype=np.int64)
    softness = np.full(over.shape, PERMILLE, dtype=np.int64)
    order = np.argsort(parts, axis=None, kind="stable")
    starts = np.searchsorted(parts.ravel()[order], np.arange(int(parts.max()) + 2))
    for part in range(1, int(parts.max()) + 1):
        cells = order[starts[part] : starts[part + 1]]
        key = derive_seed(seed, f"basin_{part}")
        low, high = settings.gradient
        fall.ravel()[cells] = low + key % (high - low + 1)
        low, high = settings.shield_share
        share = low + (key >> 24) % (high - low + 1)
        values = np.sort(noise.ravel()[cells])
        edge = int(values[min(values.size - 1, values.size * (PERMILLE - share) // PERMILLE)])
        if share == 0:
            edge = int(values[-1]) + settings.shield_edge
        hard = smoothstep(
            noise.ravel()[cells], edge - settings.shield_edge // 2, edge + settings.shield_edge // 2
        )
        softness.ravel()[cells] = PERMILLE - hard
    return fall, softness


def _graded_bed(
    grid: _Grid, cone: NDArray[np.int64], fall: NDArray[np.int64], base: int
) -> NDArray[np.int64]:
    """The height of the graded bed of every cell: ``base`` above the coast where the trees meet
    the water, rising by ``fall`` over the widened root at every step up a tree (a diagonal step
    the root of two longer), summed in thousandths."""
    columns = grid.over.shape[1]
    index = np.arange(grid.links.size, dtype=np.int64)
    links = grid.links
    diagonal = (
        (links >= 0) & (links // columns != index // columns) & (links % columns != index % columns)
    )
    length = np.where(diagonal, SQRT2_PERMILLE, PERMILLE)
    rise = fall.ravel() * length * PERMILLE // np.maximum(cone.ravel(), PERMILLE)
    bed = np.zeros(links.size, dtype=np.int64)
    for group in reversed(grid.order):
        bed[group] = bed[links[group]] + rise[group]
    return COAST_HEIGHT + base + bed.reshape(grid.over.shape) // PERMILLE


def _base_height(
    relief: NDArray[np.int32], land: NDArray[np.bool_], shape: tuple[int, int], radius: int
) -> NDArray[np.int64]:
    """The mean land height within ``radius`` cells of every drainage cell of the grid
    (``COAST_HEIGHT`` with no land so near), read a strip of rows at a time."""
    rows = int(land.shape[0])
    share = np.zeros(shape, dtype=np.int64)
    total = np.zeros(shape, dtype=np.int64)
    for first in range(0, rows, STRIP_ROWS):
        last = min(rows, first + STRIP_ROWS)
        block = slice(first // STEP, -(-last // STEP))
        on_land = land[first:last]
        here = block_mean(on_land.astype(np.int64) * PERMILLE, STEP)
        share[block, : here.shape[1]] = here
        total[block, : here.shape[1]] = block_mean(
            np.where(on_land, relief[first:last], 0).astype(np.int64), STEP
        )
    share = box_blur(share, radius)
    total = box_blur(total, radius)
    return np.where(share > 0, total * PERMILLE // np.maximum(share, 1), COAST_HEIGHT)


def basin_change(  # noqa: PLR0913 - the relief, land, plan, seed, drawing and settings.
    relief: NDArray[np.int32],
    land: NDArray[np.bool_],
    plan: DrainagePlan,
    *,
    seed: int,
    hints: ReliefHints | None = None,
    settings: BasinSettings = BASINS,
) -> NDArray[np.int64]:
    """The change of height (never positive) at the centre of every drainage cell of the domain
    (``_grid``): the base of the land lowered to the graded bed, smoothed."""
    rows, columns = (int(size) for size in land.shape)
    grid = _grid(rows, columns, plan)
    cone = widened(grid.catchment, grid.over, settings)
    fall, softness = _landmass_draws(grid.over, seed, settings)
    bed = _graded_bed(grid, cone, fall, settings.base)
    del cone, fall
    for column in grid.between:
        left, right = grid.over[:, column - 1], grid.over[:, column + 1]
        beside = np.where(left, bed[:, column - 1], bed[:, column + 1])
        both = (bed[:, column - 1] + bed[:, column + 1]) // 2
        bed[:, column] = np.where(left & right, both, beside)
    base = _base_height(relief, land, grid.over.shape, settings.base_blur)
    lowering = np.where(grid.over, np.maximum(base - bed, 0), 0) * softness // PERMILLE
    del softness
    lowering = lowering * (PERMILLE - smoothstep(base, *settings.mountains)) // PERMILLE
    del bed, base
    mountains, _ = _hint_cells(hints, grid.over.shape)
    if mountains is not None:
        lowering = lowering * (PERMILLE - mountains) // PERMILLE
    return -box_blur(lowering, settings.smoothing)


def shape_relief(  # noqa: PLR0913 - the relief, land, plan, seed, drawing and settings.
    relief: NDArray[np.int32],
    land: NDArray[np.bool_],
    plan: DrainagePlan,
    *,
    seed: int,
    hints: ReliefHints | None = None,
    settings: BasinSettings = BASINS,
) -> None:
    """Lower the land of ``relief`` in place by ``basin_change``, interpolated between the centres
    of the drainage cells, a strip of rows at a time: a pixel as high as ``standing`` less and
    then not at all (a narrow range or a wall stands), and land stays at least ``COAST_HEIGHT``."""
    rows, columns = (int(size) for size in land.shape)
    change = basin_change(relief, land, plan, seed=seed, hints=hints, settings=settings)
    # Sample k of the padded grid sits at pixel STEP * k - STEP // 2 on both axes; ``upsample``
    # reads two samples beyond the rows and columns it fills.
    padded = np.pad(change, ((1, 2), (1, 2)), mode="edge")
    del change
    width = (padded.shape[1] - 2) * STEP
    half = STEP // 2
    for first in range(0, rows, STRIP_ROWS):
        last = min(rows, first + STRIP_ROWS)
        low = (first + half) // STEP
        high = -(-(last + half) // STEP)
        window = upsample(padded[low : high + 2], STEP, ((high - low) * STEP, width))
        start = first + half - low * STEP
        part = window[start : start + last - first, half : half + columns]
        del window
        height = relief[first:last].astype(np.int64)
        part = part * (PERMILLE - smoothstep(height, *settings.standing)) // PERMILLE
        worn = np.maximum(height + part, COAST_HEIGHT)
        relief[first:last] = np.where(land[first:last], worn, height)
