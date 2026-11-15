"""Rivers of a generated domain, drawn before its cells (epoch 64, ``epoch.RIVERS_FIRST``).

Vanilla lays a large share of its rivers on location borders and sizes its locations by what
the land is: small in wet, warm lowlands and on the coasts, large in deserts, on dry steppes and
in the cold [V-EXEC, ``docs/terrain-biomes.md``]. Cells grown from a uniform scatter of seeds
before any river exists can do neither. So the domain's own rainfall (``domain_climate``: the
zonal-wind model of ``rnw.climate`` on the domain, everything outside its land and lakes being
sea) runs down the drainage of its relief (``plan_drainage``, ``domain_rivers``), in the same
independent watershed domains as the export's rivers; the cells are then grown with the larger
rivers as walls and seeds spaced by the size vanilla gives the class the climate vote will choose
(``spacing_grid``, from the game's own locations: ``eu5_biomes.SizeModel``). The world keeps its
drainage plan (``newworld.NewWorld.drainage``) and the export draws the same rivers again along
it, so the borders it gets are the rivers it writes. Integer arithmetic and square roots of
exact integers.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import (
    CLIMATE_STEP,
    GROUND_BLUR,
    SIZE_STEP,
    ClimateGrid,
    block_features,
    block_relief,
    cell_readings,
    cell_sizes,
    class_sizes,
    climate_grid,
)
from rnw.eu5_rivers import watershed_spans
from rnw.fields import PERMILLE, block_mean, warped_noise
from rnw.rivers import (
    NONE,
    STEP,
    RiverGenerationError,
    Rivers,
    flow_classes,
    outlet_problems,
    planned_rivers,
    route,
)
from rnw.rng import derive_seed, hash_grid
from rnw.synth import first_pixels, grow_regions, grow_weighted, merge_small
from rnw.topology import label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_biomes import SizeModel

# The share of river pixels, the largest by flow, that cells take as borders: vanilla has 302
# and 218 permille of its Old World's and Americas' river pixels on a location border, against
# 100 and 79 permille of all land pixels there [V-EXEC 2026-11-13, the audit of world gady3byywf].
BORDER_PERMILLE: Final[int] = 300


def domain_climate(
    land: NDArray[np.bool_], lakes: NDArray[np.bool_], height: NDArray[np.integer]
) -> ClimateGrid:
    """Rainfall of each season and distance to the sea on a grid ``CLIMATE_STEP`` coarser than
    the domain, with all but its land and lakes taken as sea. The domain's rows are the game
    map's (latitudes)."""
    return climate_grid(~(land | lakes), height, seasonal=True)


def _span_rain(rain: NDArray[np.int64], shape: tuple[int, int], left: int) -> NDArray[np.int64]:
    """The rain at the centres of the river grid of a span that starts at column ``left``."""
    rows, columns = shape
    centre_rows = np.arange(-(-rows // STEP), dtype=np.int64) * STEP + STEP // 2
    centre_columns = left + np.minimum(
        np.arange(-(-columns // STEP), dtype=np.int64) * STEP + STEP // 2, columns - 1
    )
    grid_rows = np.clip(centre_rows // CLIMATE_STEP, 0, rain.shape[0] - 1)
    grid_columns = np.clip(centre_columns // CLIMATE_STEP, 0, rain.shape[1] - 1)
    return rain[grid_rows[:, np.newaxis], grid_columns[np.newaxis, :]]


@dataclass(frozen=True, slots=True, eq=False)
class DrainagePlan:
    """How a domain's land drains, decided on its relief before anything is raised on it.

    One drainage tree (``rivers.route``) per independent watershed domain of the seam
    (``eu5_rivers.watershed_spans``; ``seam`` None: one domain), each the downstream coarse cell
    of every coarse cell of its span in raster order, -1 for water. The rivers are drawn along it
    (``domain_rivers``) when the cells are grown and again when the world is written.
    """

    seam: int | None
    parents: tuple[NDArray[np.int32], ...]


def plan_spans(columns: int, seam: int | None) -> tuple[tuple[int, int], ...]:
    """The column spans of a plan's trees: ``eu5_rivers.watershed_spans``, one without a seam."""
    return ((0, columns),) if seam is None else watershed_spans(columns, seam)


def plan_drainage(
    land: NDArray[np.bool_],
    height: NDArray[np.int32],
    *,
    lakes: NDArray[np.bool_],
    seam: int | None,
    seed: int,
) -> DrainagePlan:
    """The drainage of the domain's relief in independent watershed domains split at ``seam``
    (the column the game's map starts at; None: no seam), as the export plans its rivers
    (``eu5_nw_export._river_basins``), each span with its own seed."""
    columns = int(land.shape[1])
    parents = tuple(
        route(
            land[:, left:right],
            height[:, left:right],
            seed=derive_seed(seed, f"river_basin_{left}"),
            lakes=lakes[:, left:right],
        ).astype(np.int32)
        for left, right in plan_spans(columns, seam)
    )
    return DrainagePlan(seam=seam, parents=parents)


def domain_rivers(
    land: NDArray[np.bool_],
    plan: DrainagePlan,
    *,
    lakes: NDArray[np.bool_],
    rain: NDArray[np.int64],
    seed: int,
) -> Rivers:
    """The rivers of the domain along its drainage ``plan`` (``plan_drainage``), the flow being
    the domain's own ``rain`` (``domain_climate``), each span draining to genuine water.

    A plan that is not this domain's (another number of spans, or water where the domain has
    land) or a span with a bad outlet fails.
    """
    rows, columns = (int(size) for size in land.shape)
    seam = plan.seam
    spans = plan_spans(columns, seam)
    if len(spans) != len(plan.parents):
        message = "The drainage plan is not this domain's: it has another number of spans"
        raise RiverGenerationError(message)
    rivers = Rivers(
        np.empty(land.shape, dtype=np.int8),
        np.empty(land.shape, dtype=np.int64),
        dict.fromkeys(("streams", "mouths", "joins", "dropped", "pixels"), 0),
    )
    if seam is not None:
        for column in (seam - 1, seam):
            if 0 <= column < columns:
                rivers.role[:, column] = NONE
                rivers.flow[:, column] = 0
    thresholds: list[int] = []
    for (left, right), parent in zip(spans, plan.parents, strict=True):
        domain = land[:, left:right]
        target = Rivers(rivers.role[:, left:right], rivers.flow[:, left:right], {})
        found = planned_rivers(
            domain,
            parent,
            _span_rain(rain, (rows, right - left), left),
            seed=derive_seed(seed, f"river_basin_{left}"),
            output=target,
            lakes=lakes[:, left:right],
        )
        problems = outlet_problems(found.role, ~domain)
        if any(problems.values()):
            message = f"river basin {left}:{right} has invalid outlets: {problems}"
            raise RiverGenerationError(message)
        thresholds.append(found.stats["threshold"])
        for key, value in found.stats.items():
            if key != "threshold":
                rivers.stats[key] = rivers.stats.get(key, 0) + value
    rivers.stats.update(
        watershed_domains=len(spans),
        outlets_checked=rivers.stats["mouths"],
        threshold_min=min(thresholds, default=0),
        threshold_max=max(thresholds, default=0),
    )
    return rivers


def border_rivers(rivers: Rivers) -> NDArray[np.bool_]:
    """The river pixels that cells take as borders: the ``BORDER_PERMILLE`` largest by flow."""
    return flow_classes(rivers, (PERMILLE - BORDER_PERMILLE, BORDER_PERMILLE)) == 1


# Seed spacing by the land (``spacing_grid``): every ``eu5_biomes.SIZE_STEP`` block of land takes
# the size of vanilla's locations where vanilla's land is like it and of the class the climate
# vote will choose there (``eu5_biomes.class_sizes``).
DENSITY_STEP: Final[int] = 32  # pixels per block of the spacing grid; a multiple of CLIMATE_STEP
POLAR_SPACING: Final[int] = 3000  # permille of the spacing in the polar bands, as before
# The narrowest and widest spacing of the land outside them, permille of the uniform spacing:
# 2^(-3/4) and 2^(7/4), a cell from 0.35 to 11 times the uniform area, as before.
SPACING_RANGE: Final[tuple[int, int]] = (595, 3364)
# How fast the spacing may grow with distance, in thousandths of a pixel per pixel: a location
# is then at most 1.3 times as wide as a neighbour one of its own widths away, so neighbouring
# locations differ by at most 0.76 of an octave in area before their seeds are drawn. Vanilla's
# neighbours differ by more than an octave in 100 and 109 permille of its Old World's and
# Americas' pairs of land locations and by more than two in 5; sized block by block, the
# generated ones did in 299 and 65 permille [V-EXEC 2026-11-15].
GRADATION: Final[int] = 300
# Settlement that the land's class does not explain: vanilla's locations lie off the size their
# class gives them by 0.74 and 0.87 of an octave (standard deviations, Old World and Americas),
# and that remainder is shared by neighbours (correlation 0.51 and 0.58) and fades over 300 to
# 600 pixels [V-EXEC 2026-11-15]. A smooth noise of this period and spread (thousandths of an
# octave of area, after the gradation, which it is too smooth to need) gives each world regions
# of denser and sparser settlement of its own.
DENSITY_PERIOD: Final[int] = 800
DENSITY_SPREAD: Final[int] = 650
# Seeds keep this share (permille) of the mean of their spacings apart; it gives as many seeds as
# the spacing expects (``spaced_sites``).
SEED_GAP: Final[int] = 758
# Candidate seeds per square of the local spacing, as the side of a lattice (3: nine).
SEED_CANDIDATES: Final[int] = 3
SPACING_PARTS: Final[int] = 64  # spacing exponents are 64ths of an octave
SHIFT_OCTAVES: Final[int] = 6  # the whole spacing is scaled by at most this many octaves
_FIXED: Final[int] = 20  # binary places of ``_ROOTS`` and ``_POWERS``


def _powers() -> tuple[int, ...]:
    """2^(k / SPACING_PARTS) for k below SPACING_PARTS in ``_FIXED`` binary places, from exact
    integer square roots (no floating point)."""
    roots = [2 << _FIXED]
    while len(roots) < SPACING_PARTS.bit_length():
        roots.append(math.isqrt(roots[-1] << _FIXED))
    out: list[int] = []
    for part in range(SPACING_PARTS):
        value = 1 << _FIXED
        for bit, root in enumerate(roots[1:], start=1):
            if part >> (SPACING_PARTS.bit_length() - 1 - bit) & 1:
                value = value * root >> _FIXED
        out.append(value)
    return tuple(out)


_POWERS: Final[tuple[int, ...]] = _powers()


def spacing_permille(exponent: NDArray[np.int64]) -> NDArray[np.int64]:
    """PERMILLE * 2^(exponent / SPACING_PARTS), floored; integers."""
    whole = np.floor_divide(exponent, SPACING_PARTS)
    part = exponent - whole * SPACING_PARTS
    value = np.array(_POWERS, dtype=np.int64)[part] * PERMILLE
    up, down = np.maximum(whole, 0), np.maximum(-whole, 0)
    return (value << up) >> (_FIXED + down)


def grade_spacing(
    spacing: NDArray[np.int64], land: NDArray[np.bool_], step_permille: int
) -> NDArray[np.int64]:
    """The largest spacing at or below ``spacing`` that grows by at most ``step_permille`` from
    one block of ``land`` to the next (``step_permille`` times the square root of two to a
    diagonal one), as a mesh limits the growth of its elements: a small spacing narrows the
    large ones around it, a large one never widens the small. Blocks without land neither take
    nor pass a limit."""
    big = np.int64(1) << 40
    graded = np.where(land, spacing, big)
    straight, diagonal = step_permille, step_permille * 1414 // 1000
    while True:
        padded = np.pad(graded, 1, constant_values=big)
        limit = np.minimum.reduce(
            [
                padded[:-2, 1:-1] + straight,
                padded[2:, 1:-1] + straight,
                padded[1:-1, :-2] + straight,
                padded[1:-1, 2:] + straight,
                padded[:-2, :-2] + diagonal,
                padded[:-2, 2:] + diagonal,
                padded[2:, :-2] + diagonal,
                padded[2:, 2:] + diagonal,
            ]
        )
        lowered = np.minimum(graded, np.where(land, limit, big))
        if np.array_equal(lowered, graded):
            return np.where(land, graded, spacing)
        graded = lowered


def spacing_grid(  # noqa: PLR0913 - the land, sea, relief and climate, bands, model and spacing.
    land: NDArray[np.bool_],
    height: NDArray[np.integer],
    climate: ClimateGrid,
    *,
    sea: NDArray[np.bool_],
    polar_rows: int,
    sizes: SizeModel,
    spacing: int,
) -> NDArray[np.int64]:
    """Seed spacing of every ``DENSITY_STEP`` block, in permille of the uniform ``spacing``, read
    from the land alone: the first cells are grown on it (``cell_spacing_grid``).

    Each ``SIZE_STEP`` block of land takes the size of the vanilla locations of the class the
    vote will give it and of the ground its relief makes it, on the coast if it holds ``sea``
    (``eu5_biomes.class_sizes``), graded and scaled as ``_graded_grid`` does. The
    ``polar_rows`` rows at either edge keep ``POLAR_SPACING``.
    """
    step = DENSITY_STEP
    share = _land_share(land)
    found, features = block_features(land, height, climate)
    coarse = np.zeros(found.shape, dtype=np.int64)
    if features.size:
        relief = block_relief(land, height, found, blur=GROUND_BLUR)
        coastal = _blocks_holding(sea, found.shape)
        coarse[found] = class_sizes(sizes, features, relief, coastal[found])
    ratio = SIZE_STEP // step
    shape = share.shape
    size = np.repeat(np.repeat(coarse, ratio, axis=0), ratio, axis=1)[: shape[0], : shape[1]]
    return _graded_grid(size, share, _polar(shape, polar_rows), spacing, None)


def cell_spacing_grid(  # noqa: PLR0913 - the land's cells, relief, climate, sea, bands, model, key.
    cells: NDArray[np.int32],
    height: NDArray[np.integer],
    climate: ClimateGrid,
    *,
    sea: NDArray[np.bool_],
    polar_rows: int,
    sizes: SizeModel,
    key: int,
    spacing: int,
) -> NDArray[np.int64]:
    """Seed spacing of every ``DENSITY_STEP`` block, in permille of the uniform ``spacing``, read
    from first ``cells`` grown on ``spacing_grid``: every cell takes the size vanilla gives the
    class and the ground the final vote will give it, inland or by the ``sea``
    (``eu5_biomes.cell_sizes``), a block the
    mean over its land, and the grid is graded and scaled (``_graded_grid``) with the
    settlement noise (``key``). The final cells then lie, by and large, where cells of their
    own class were sized.
    """
    count = int(cells.max()) + 1 if np.any(cells >= 0) else 0
    share = _land_share(cells >= 0)
    shape = share.shape
    size = np.zeros(shape, dtype=np.int64)
    if count:
        features, centred, readings, coastal = cell_readings(cells, count, height, climate, sea)
        target = cell_sizes(sizes, features, centred, readings, coastal)
        step = DENSITY_STEP
        area = step * step
        rows = int(cells.shape[0])
        strip = step * 32
        for first in range(0, rows, strip):
            window = slice(first, min(rows, first + strip))
            blocks = slice(first // step, -(-window.stop // step))
            cell = cells[window]
            on_land = cell >= 0
            # Means scaled by a block's area are sums: the target summed over its land pixels,
            # over the land pixels counted the same way, is the mean exactly.
            total = block_mean(np.where(on_land, target[np.maximum(cell, 0)], 0) * area, step)
            pixels = block_mean(on_land.astype(np.int64) * area, step)
            size[blocks] = np.floor_divide(total, np.maximum(pixels, 1))
    polar = _polar(shape, polar_rows)
    density = _density(key, shape, (share > 0) & ~polar)
    return _graded_grid(size, share, polar, spacing, density)


def _blocks_holding(mask: NDArray[np.bool_], shape: tuple[int, ...]) -> NDArray[np.bool_]:
    """The ``SIZE_STEP`` blocks (``shape`` of them) that hold a pixel of ``mask``."""
    step = SIZE_STEP
    rows = int(mask.shape[0])
    found = np.zeros((int(shape[0]), int(shape[1])), dtype=bool)
    strip = step * 16
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        blocks = slice(first // step, -(-window.stop // step))
        found[blocks] = block_mean(mask[window].astype(np.int64) * step * step, step) > 0
    return found


def _land_share(land: NDArray[np.bool_]) -> NDArray[np.int64]:
    """The land of every ``DENSITY_STEP`` block, permille, a strip at a time."""
    step = DENSITY_STEP
    rows, columns = (int(size) for size in land.shape)
    share = np.empty((-(-rows // step), -(-columns // step)), dtype=np.int64)
    strip = step * 32
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        blocks = slice(first // step, -(-window.stop // step))
        share[blocks] = block_mean(land[window].astype(np.int64) * PERMILLE, step)
    return share


def _polar(shape: tuple[int, int], polar_rows: int) -> NDArray[np.bool_]:
    """The blocks of the ``polar_rows`` rows at either edge."""
    polar = np.zeros(shape, dtype=bool)
    band = -(-polar_rows // DENSITY_STEP) if polar_rows else 0
    if band:
        polar[:band] = True
        polar[-band:] = True
    return polar


def _graded_grid(
    size: NDArray[np.int64],
    share: NDArray[np.int64],
    polar: NDArray[np.bool_],
    spacing: int,
    density: NDArray[np.int64] | None,
) -> NDArray[np.int64]:
    """The spacing (permille of the uniform ``spacing``) of blocks whose cells should be ``size``
    (thousandths of an octave of area): within ``SPACING_RANGE``, graded (``grade_spacing``,
    ``GRADATION``; the polar blocks keep ``POLAR_SPACING`` ungraded, for their cells become the
    large wastelands of the map's edge, and the land before them widens toward them at the same
    rate from half their area), then moved by the settlement
    ``density`` (thousandths of an octave of area), which is smooth and needs no grading, and
    scaled as a whole, in 64ths of an octave, so that the land outside the polar bands expects
    as many cells as the uniform spacing gives it. Vanilla's own sizes change between classes
    over a location or two, not at once: neighbouring locations differ by more than an octave
    in a tenth of their pairs [V-EXEC 2026-11-15].
    """
    has_land = share > 0
    weight = np.where(polar, 0, share)
    # Thousandths of an octave of area to 64ths of an octave of spacing (half the octaves).
    exponent = np.floor_divide(size * (SPACING_PARTS // 2), PERMILLE)
    moved = (
        None
        if density is None
        else spacing_permille(np.floor_divide(density * (SPACING_PARTS // 2), PERMILLE))
    )
    slope = GRADATION * DENSITY_STEP // max(1, spacing)
    wanted = int(weight.sum()) * PERMILLE
    # The land before a polar band widens toward it at the same rate, from half the area of the
    # band's cells, so they border cells that grow into them instead of ordinary ones and remain
    # the larger, for those touching the map's edge become its wastelands.
    approach = -grade_spacing(
        -np.where(polar & has_land, POLAR_SPACING * PERMILLE // 1414, 0), has_land, slope
    )

    def graded(shift: int) -> NDArray[np.int64]:
        free = np.clip(spacing_permille(exponent - shift), SPACING_RANGE[0], SPACING_RANGE[1])
        out = grade_spacing(np.maximum(free, approach), has_land & ~polar, slope)
        if moved is not None:
            out = np.clip(out * moved // PERMILLE, SPACING_RANGE[0], SPACING_RANGE[1])
        # A block without land holds no seed; it keeps the uniform spacing.
        return np.where(has_land, np.where(polar, POLAR_SPACING, out), PERMILLE)

    def expected(grid: NDArray[np.int64]) -> int:
        return int((weight * PERMILLE * PERMILLE * PERMILLE // (grid * grid)).sum())

    # A larger shift narrows the spacing, so the expected cells grow with it: the smallest shift
    # that expects at least as many cells as wanted, or the one before it, whichever is nearer.
    low, high = -SHIFT_OCTAVES * SPACING_PARTS, SHIFT_OCTAVES * SPACING_PARTS
    while high - low > 1:
        middle = (low + high) // 2
        if expected(graded(middle)) < wanted:
            low = middle
        else:
            high = middle
    best = min((abs(expected(graded(shift)) - wanted), shift) for shift in (low, high))
    return graded(best[1])


def _density(key: int, shape: tuple[int, int], land: NDArray[np.bool_]) -> NDArray[np.int64]:
    """The settlement noise (``DENSITY_PERIOD``, ``DENSITY_SPREAD``) of every block, in
    thousandths of an octave of area: centred and scaled to its spread over the ``land`` blocks."""
    noise = warped_noise(
        key, shape, step=1, period=max(2, DENSITY_PERIOD // DENSITY_STEP), octaves=2, warp_px=0
    )[: shape[0], : shape[1]]
    values = noise[land]
    if values.size == 0:
        return np.zeros(shape, dtype=np.int64)
    count = int(values.size)
    mean = int(values.sum()) // count
    variance = int((values * values).sum()) // count - mean * mean
    spread = max(1, math.isqrt(max(variance, 0)))
    return (noise - mean) * DENSITY_SPREAD // spread


def spaced_sites(
    key: int, mask: NDArray[np.bool_], spacing: int, grid: NDArray[np.int64]
) -> NDArray[np.int32]:
    """Seeds inside ``mask`` whose spacing follows ``grid`` (``spacing_grid``), none nearer to
    another than ``SEED_GAP`` of the mean of their spacings.

    Candidates (``_seed_candidates``) are taken in an order hashed from ``key``, each kept unless
    a kept one lies too near (dart throwing, ``_throw_seeds``). Seeds drawn from a jittered grid
    per spacing level could lie a sixth of the spacing apart, and the cell grown between two such
    seeds was a sliver among large ones [V-EXEC 2026-11-15]. Every component of the mask gets at
    least one seed. Seeds are numbered in raster order. Integers.
    """
    columns = int(mask.shape[1])
    if not mask.any():
        return np.full(mask.shape, -1, dtype=np.int32)
    blocks = block_mean(mask.astype(np.int64) * DENSITY_STEP * DENSITY_STEP, DENSITY_STEP) > 0
    present = grid[: blocks.shape[0], : blocks.shape[1]][blocks]
    smallest = max(1, spacing * int(present.min()) // PERMILLE)
    widest = max(1, spacing * int(present.max()) // PERMILLE)
    xs, ys, radius, order = _seed_candidates(key, mask, spacing, grid, smallest)
    flat = _throw_seeds(
        xs[order], ys[order], radius[order], smallest=smallest, widest=widest, columns=columns
    )
    components = label_components(mask.astype(np.int32))
    covered = np.zeros(int(components.max()) + 1, dtype=bool)
    covered[components.ravel()[flat]] = True
    firsts = first_pixels(components)
    extra = firsts[mask.ravel()[firsts] & ~covered[components.ravel()[firsts]]]
    ordered = np.unique(np.concatenate([flat, extra]))
    seeds = np.full(mask.size, -1, dtype=np.int32)
    seeds[ordered] = np.arange(ordered.size, dtype=np.int32)
    return seeds.reshape(mask.shape)


def _seed_candidates(
    key: int, mask: NDArray[np.bool_], spacing: int, grid: NDArray[np.int64], smallest: int
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """Candidate seeds: a jittered lattice of a third of the ``smallest`` spacing (pixels) inside
    ``mask``, thinned to about ``SEED_CANDIDATES`` squared per square of the local spacing, with
    their columns, rows, local spacings (pixels) and the hashed order they are tried in."""
    rows, columns = (int(size) for size in mask.shape)
    lattice = max(1, smallest // SEED_CANDIDATES)
    gx = np.arange(-(-columns // lattice), dtype=np.int64)
    gy = np.arange(-(-rows // lattice), dtype=np.int64)
    hashed = hash_grid(key, gx[np.newaxis, :], gy[:, np.newaxis])
    sx = gx[np.newaxis, :] * lattice + (hashed & np.uint64(0xFFFF)).astype(np.int64) % lattice
    sy = (
        gy[:, np.newaxis] * lattice
        + ((hashed >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64) % lattice
    )
    inside = (sx < columns) & (sy < rows)
    sx, sy, hashed = sx[inside], sy[inside], hashed[inside]
    keep = mask[sy, sx]
    sx, sy, hashed = sx[keep], sy[keep], hashed[keep]
    radius = np.maximum(1, spacing * grid[sy // DENSITY_STEP, sx // DENSITY_STEP] // PERMILLE)
    # Keep a candidate with a chance of (SEED_CANDIDATES * lattice / radius)^2, read from 16 bits
    # of its hash: where the spacing is wide the lattice is thinned.
    chance = ((hashed >> np.uint64(32)) & np.uint64(0xFFFF)).astype(np.int64)
    side = SEED_CANDIDATES * lattice
    kept = chance * radius * radius < (side * side) << 16
    sx, sy, hashed, radius = sx[kept], sy[kept], hashed[kept], radius[kept]
    order = np.lexsort((sy * columns + sx, (hashed >> np.uint64(48)).astype(np.int64)))
    return sx, sy, radius, order


def _throw_seeds(  # noqa: PLR0913 - the candidates, their spacings, the extremes and the width.
    xs: NDArray[np.int64],
    ys: NDArray[np.int64],
    radius: NDArray[np.int64],
    *,
    smallest: int,
    widest: int,
    columns: int,
) -> NDArray[np.int64]:
    """The raster positions of the candidates kept in turn: a candidate is dropped when a kept
    one lies nearer than ``SEED_GAP`` of the mean of their spacings (all in pixels). Kept seeds
    are filed in buckets of the ``smallest`` spacing, and a candidate looks as far as the
    ``widest`` spacing could reach."""
    buckets: dict[tuple[int, int], list[int]] = {}
    kept_x: list[int] = []
    kept_y: list[int] = []
    kept_r: list[int] = []
    gap = SEED_GAP * SEED_GAP
    scale = 4 * PERMILLE * PERMILLE
    for x, y, r in zip(xs.tolist(), ys.tolist(), radius.tolist(), strict=True):
        reach = -(-SEED_GAP * (r + widest) // (2 * PERMILLE * smallest))
        bx, by = x // smallest, y // smallest
        clear = True
        for cy in range(by - reach, by + reach + 1):
            for cx in range(bx - reach, bx + reach + 1):
                for j in buckets.get((cx, cy), ()):
                    dx, dy, both = x - kept_x[j], y - kept_y[j], r + kept_r[j]
                    if scale * (dx * dx + dy * dy) < gap * both * both:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                break
        if clear:
            buckets.setdefault((bx, by), []).append(len(kept_x))
            kept_x.append(x)
            kept_y.append(y)
            kept_r.append(r)
    return np.array(kept_y, dtype=np.int64) * columns + np.array(kept_x, dtype=np.int64)


def river_cells(  # noqa: PLR0913 - the land, its walls, the seeds' spacing and the merge size.
    land: NDArray[np.bool_],
    walls: NDArray[np.bool_],
    *,
    key: int,
    spacing: int,
    grid: NDArray[np.int64],
    smallest: int,
) -> NDArray[np.int32]:
    """Land cells grown from ``spaced_sites`` that do not cross ``walls`` (the border rivers),
    whose pixels then join the cell beside them; cells under ``smallest`` pixels are merged.

    Each seed grows as fast as its spacing (``synth.grow_weighted``): grown at one pace, a seed
    of the sparse land gives half of the way to each seed of the dense land beside it, and the
    cells of the largest spacings came out at three quarters of their area [V-EXEC 2026-11-13].
    """
    sites = spaced_sites(key, land, spacing, grid)
    rows, columns = np.nonzero(sites >= 0)
    speed = np.zeros(int(sites.max()) + 1 if rows.size else 0, dtype=np.int64)
    speed[sites[rows, columns]] = grid[rows // DENSITY_STEP, columns // DENSITY_STEP]
    del rows, columns
    grown = grow_weighted(land & ~walls, sites, speed)
    del sites
    return merge_small(grow_regions(land, grown), smallest)
