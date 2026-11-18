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

from rnw import _native
from rnw.eu5_biomes import (
    CLIMATE_STEP,
    SIZE_STEP,
    ClimateGrid,
    GroundField,
    block_features,
    block_ground_scores,
    cell_edges,
    cell_readings,
    cell_sizes,
    class_sizes,
    climate_grid,
)
from rnw.eu5_rivers import watershed_spans
from rnw.fields import PERMILLE, block_mean, warped_noise
from rnw.progress import checkpoint
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
from rnw.timing import measured
from rnw.topology import adjacency_pairs, label_components

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

    from rnw.eu5_biomes import SizeModel

# The share of river pixels, the largest by flow, that cells take as borders: vanilla has 302
# and 218 permille of its Old World's and Americas' river pixels on a location border, against
# 100 and 79 permille of all land pixels there [V-EXEC 2026-11-13, the audit of world gady3byywf].
BORDER_PERMILLE: Final[int] = 300


@measured
def domain_climate(
    land: NDArray[np.bool_],
    lakes: NDArray[np.bool_],
    height: NDArray[np.integer],
    *,
    row0: int = 0,
    outside_land: NDArray[np.bool_] | None = None,
) -> ClimateGrid:
    """Rainfall of each season and distance to the sea on a grid ``CLIMATE_STEP`` coarser than
    the domain. Its land, lakes and retained land are dry for the transport model.
    ``row0`` locates the first row on the game map to read its latitude."""
    sea = ~(land | lakes)
    if outside_land is not None:
        sea &= ~outside_land
    return climate_grid(sea, height, seasonal=True, row0=row0)


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


def _validate_outside_land(
    land: NDArray[np.bool_],
    lakes: NDArray[np.bool_],
    outside_land: NDArray[np.bool_] | None,
) -> None:
    if outside_land is not None and (
        outside_land.shape != land.shape or np.any(outside_land & (land | lakes))
    ):
        message = "Retained land must be outside the drainage domain's land and lakes"
        raise RiverGenerationError(message)


@measured
def plan_drainage(  # noqa: PLR0913 - the drainage plan reads the domain and its outside terrain.
    land: NDArray[np.bool_],
    height: NDArray[np.int32],
    *,
    lakes: NDArray[np.bool_],
    seam: int | None,
    seed: int,
    outside_land: NDArray[np.bool_] | None = None,
) -> DrainagePlan:
    """The drainage of the domain's relief in independent watershed domains split at ``seam``
    (the column the game's map starts at; None: no seam), as the export plans its rivers
    (``eu5_nw_export._river_basins``), each span with its own seed."""
    columns = int(land.shape[1])
    _validate_outside_land(land, lakes, outside_land)
    parents = tuple(
        route(
            land[:, left:right],
            height[:, left:right],
            seed=derive_seed(seed, f"river_basin_{left}"),
            lakes=lakes[:, left:right],
            outside_land=None if outside_land is None else outside_land[:, left:right],
        ).astype(np.int32)
        for left, right in plan_spans(columns, seam)
    )
    return DrainagePlan(seam=seam, parents=parents)


@measured
def domain_rivers(  # noqa: PLR0913 - drainage, waters and rain for each basin.
    land: NDArray[np.bool_],
    plan: DrainagePlan,
    *,
    lakes: NDArray[np.bool_],
    rain: NDArray[np.int64],
    seed: int,
    outside_land: NDArray[np.bool_] | None = None,
) -> Rivers:
    """The rivers of the domain along its drainage ``plan`` (``plan_drainage``), the flow being
    the domain's own ``rain`` (``domain_climate``), each span draining to genuine water.

    A plan that is not this domain's (another number of spans, or water where the domain has
    land) or a span with a bad outlet fails.
    """
    _validate_outside_land(land, lakes, outside_land)
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
        kept = None if outside_land is None else outside_land[:, left:right]
        target = Rivers(rivers.role[:, left:right], rivers.flow[:, left:right], {})
        found = planned_rivers(
            domain,
            parent,
            _span_rain(rain, (rows, right - left), left),
            seed=derive_seed(seed, f"river_basin_{left}"),
            output=target,
            lakes=lakes[:, left:right],
            outside_land=kept,
        )
        water = ~domain
        if kept is not None:
            water &= ~kept
        problems = outlet_problems(found.role, water)
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
# How fast the spacing of the final cells may grow with distance, in thousandths of a pixel per
# pixel: a location is then at most 1.5 times as wide as a neighbour one of its own widths away.
# Vanilla's neighbours differ by more than an octave in 100 and 109 permille of its Old World's
# and Americas' pairs of land locations and by more than two in 5; sized block by block, the
# generated ones did in 299 and 65 permille [V-EXEC 2026-11-15]. The cells' own targets differ
# as often as vanilla's (103 to 107 permille over an octave); graded at 300, the plan held 21 and
# the grown cells of eight worlds 69 and 2.9, the polar bands left out; at 500, with the inland
# cells kept within ``SIZE_BAND`` of their plan, 46 and the grown cells 87 and 3.0 [V-EXEC
# 2026-11-16, seeds 20261115, 42, 7, 1234, 99, 2026, 31337 and 555].
GRADATION: Final[int] = 500
# The first cells (``spacing_grid``) are graded more gently: a coastal cell whose plan is large
# reaches the high land behind the shore and is voted mountain, so the steeper the first cells'
# sizes change, the larger the coastal mountain blocks the final cells are planned on came out
# (against the coastal flatland of their pair: +0.005 of an octave at 300, +0.04 at 400, +0.09 at
# 500), and the final cells followed them [V-EXEC 2026-11-16, eight worlds as above].
FIRST_GRADATION: Final[int] = 300
# The land before a polar band widens toward it this many times more slowly than ``GRADATION``
# allows: at the full rate the spacing doubled within three blocks where the cells are small, and
# the pairs of cells beside the bands differed by more than two octaves in 40 to 50 permille of
# them (28 pooled), ten times as often as elsewhere; widening at half the rate, and never narrowed
# by the settlement noise (``_graded_grid``), in 5 [V-EXEC 2026-11-16].
APPROACH_SLOWER: Final[int] = 2
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
# The cells beside water (``river_cells``). A thrown seed lies anywhere in its square, and one by
# the sea grew a cell the sea cut: a coastal cell's size followed its seed's distance from the sea
# (rank correlation 0.77; seeds within 0.15 of their spacing of it grew 0.88 of an octave under
# their plan), and as the land rises from the shore the cells reaching inland took the hills' and
# the mountains' ground: on four worlds the coastal hills came out 0.30 of an octave larger than
# the coastal flatland beside them (standard error 0.04). The seed of each cell beside water
# therefore moves to the centre of the cell it grew (Lloyd's relaxation of the shore,
# ``RELAX_STEPS``), and the speed of each such cell is then corrected toward its planned share of
# the land it and its neighbours grew (``SHORE_FEEDBACK_STEPS``; by the square root of that share
# over its own area, within ``SHORE_GAIN_STEP`` a time and ``SHORE_GAIN_RANGE`` in all), so that
# it grows as large as planned beside the cells it borders. Pooled over the four worlds the coastal
# flatland is 0.015 of an octave smaller than the inland flatland beside it (its plan 0.012), the
# coastal hills 0.08 larger than the coastal flatland (0.02), wetlands 0.02 smaller (0.03),
# mountains 0.09 larger (0.04) and inland mountains 0.09 smaller (0.03); vanilla's lie from 0.10 to
# 0.17 smaller, 0.03 to 0.09 larger, 0.03 smaller to 0.10 larger, 0.05 smaller to 0.04 larger and
# 0.09 to 0.02 smaller. A seed sped by the root of the land's share of its square instead
# inflated the coastal cells (coastal flatland 0.05 larger than the inland), and so evened the
# coastal hills; moved twice, the second time after the last correction, 0.10 larger; corrected
# toward the share of all the land, the coastal cells grew into the next row (0.43 larger);
# every cell corrected, the neighbours of a grown cell differed by more than an octave in 38
# permille of the pairs, not 70; every seed moved, the land lay in a lattice of diamonds, the
# shape the four-neighbour growth gives regular seeds [V-EXEC 2026-11-15, seeds 20261115, 42, 7
# and 1234, grown cells]. A share of its own neighbourhood depends on whom a cell borders: a
# coastal mountain cell borders more inland cells, which the sea does not cut, than the coastal
# flatland beside it, and was given 0.055 of an octave more land for it; and the plan, read from
# blocks of first cells whose ground is the final cell's for three in five coastal mountains,
# carries little of vanilla's offsets on the coast (coastal mountains planned 0.02 larger than the
# coastal flatland beside them, their size 0.07 smaller): over eight worlds the coastal mountains
# came out 0.09 larger (standard error of the worlds' means 0.025). The final cells beside the sea
# are therefore corrected instead toward their planned square at the density of the inland cells
# round them (``SHORE_DENSITY_BLOCKS``), moved by vanilla's offset of their ground on the coast
# against its inland flatland (``eu5_biomes.coastal_offsets``, read on the cells as they grow).
# Unlike the share of all the land, which knew no offset, this plans the coast smaller than the
# inland round it, as vanilla's is. Pooled, with ``SIZE_BAND``, ``GRADATION`` and
# ``FIRST_GRADATION``: coastal mountains 0.03 larger than the coastal flatland beside them (0.03),
# coastal hills 0.04, inland mountains 0.05 smaller, coastal flatland 0.02 smaller than the inland
# (0.00 before; its plan's offset is diluted by the first cells and the blocks). Tried and worse
# for the coastal mountains: every seed sped toward the size its first cell was given (+0.17; the
# class of a coastal cell follows its extent, so the cells whose target came out large grew
# large), a third pass of cells (+0.11), four corrections (+0.08), no river walls (+0.10), the
# coastal offset of the cell's own ground instead of against the inland flatland (+0.05), the
# mean inland cell round it instead of its own plan (coastal flatland 0.07 larger) [V-EXEC
# 2026-11-16, seeds 20261115, 42, 7, 1234, 99, 2026, 31337 and 555, grown cells].
RELAX_STEPS: Final[int] = 1
SHORE_FEEDBACK_STEPS: Final[int] = 2
SHORE_GAIN_STEP: Final[tuple[int, int]] = (500, 2000)  # permille of a cell's speed, per growth
SHORE_GAIN_RANGE: Final[tuple[int, int]] = (250, 4000)  # permille of its spacing, in all
# The final cells beside the sea are corrected toward their planned square at the density of the
# inland cells whose seeds lie within this many ``DENSITY_STEP`` blocks of theirs (``river_cells``
# with ``coast``), not toward their share of their own neighbours.
SHORE_DENSITY_BLOCKS: Final[int] = 4
# An inland final cell that grew more than this (thousandths of an octave of area) off its planned
# square at that density is corrected back to the edge of the band, the others not: a slow seed
# among fast ones was hemmed in (the smaller cell of an inland pair over two octaves had a
# neighbour planned 0.73 of an octave larger, against 0.34 for all inland cells; its seed lay as
# far from the others as any), and those pairs grew 1.1 octaves apart beyond their plans.
# Corrected all the way, every cell evened the land (38 permille of the pairs over an octave);
# within the band the growth keeps its variety [V-EXEC 2026-11-16, eight worlds as above].
SIZE_BAND: Final[int] = 750
CENTRE_STRIP: Final[int] = 512  # rows of the grown cells read at a time
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


@measured
def grade_spacing(
    spacing: NDArray[np.int64], land: NDArray[np.bool_], step_permille: int
) -> NDArray[np.int64]:
    """The largest spacing at or below ``spacing`` that grows by at most ``step_permille`` from
    one block of ``land`` to the next (``step_permille`` times the square root of two to a
    diagonal one), as a mesh limits the growth of its elements: a small spacing narrows the
    large ones around it, a large one never widens the small. Blocks without land neither take
    nor pass a limit."""
    return _native.grade_spacing(
        np.ascontiguousarray(spacing), np.ascontiguousarray(land), step_permille, checkpoint
    )


@measured
def spacing_grid(  # noqa: PLR0913 - the land, sea, relief and climate, bands, model and spacing.
    land: NDArray[np.bool_],
    height: NDArray[np.integer],
    climate: ClimateGrid,
    *,
    sea: NDArray[np.bool_],
    polar_rows: int | tuple[int, int],
    sizes: SizeModel,
    ground: GroundField,
    spacing: int,
) -> NDArray[np.int64]:
    """Seed spacing of every ``DENSITY_STEP`` block, in permille of the uniform ``spacing``, read
    from the land alone: the first cells are grown on it (``cell_spacing_grid``).

    Each ``SIZE_STEP`` block of land takes the size of the vanilla locations of the class the
    vote will give it and of the ground its land votes (``ground``, ``block_ground_scores``), on
    the coast if it holds ``sea`` (``eu5_biomes.class_sizes``), graded and scaled as
    ``_graded_grid`` does at ``FIRST_GRADATION``. The ``polar_rows`` rows at either edge keep
    ``POLAR_SPACING``.
    """
    step = DENSITY_STEP
    share = _land_share(land)
    found, features = block_features(land, height, climate)
    coarse = np.zeros(found.shape, dtype=np.int64)
    if features.size:
        coastal = _blocks_holding(sea, found.shape)
        coarse[found] = class_sizes(
            sizes, features, block_ground_scores(ground, found), coastal[found]
        )
    ratio = SIZE_STEP // step
    shape = share.shape
    size = np.repeat(np.repeat(coarse, ratio, axis=0), ratio, axis=1)[: shape[0], : shape[1]]
    return _graded_grid(
        size, share, _polar(shape, polar_rows), spacing, None, gradation=FIRST_GRADATION
    )


@measured
def cell_spacing_grid(  # noqa: PLR0913 - the land's cells, relief, climate, sea, bands, model, key.
    cells: NDArray[np.int32],
    height: NDArray[np.integer],
    climate: ClimateGrid,
    *,
    sea: NDArray[np.bool_],
    polar_rows: int | tuple[int, int],
    sizes: SizeModel,
    ground: GroundField,
    key: int,
    spacing: int,
) -> NDArray[np.int64]:
    """Seed spacing of every ``DENSITY_STEP`` block, in permille of the uniform ``spacing``, read
    from first ``cells`` grown on ``spacing_grid``: every cell takes the size vanilla gives the
    class and the ground the final vote will give it (from the votes of its land, ``ground``),
    inland or by the ``sea`` (``eu5_biomes.cell_sizes``), a block the
    mean over its land, and the grid is graded and scaled (``_graded_grid``) with the
    settlement noise (``key``). The final cells then lie, by and large, where cells of their
    own class were sized.
    """
    count = int(cells.max()) + 1 if np.any(cells >= 0) else 0
    share = _land_share(cells >= 0)
    shape = share.shape
    size = np.zeros(shape, dtype=np.int64)
    if count:
        features, centred, votes, coastal = cell_readings(
            cells, count, height, climate, sea, ground=ground
        )
        target = cell_sizes(
            sizes, features, centred, votes, coastal, edges=cell_edges(cells, count)
        )
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
    return _graded_grid(size, share, polar, spacing, density, gradation=GRADATION)


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


def _polar(shape: tuple[int, int], polar_rows: int | tuple[int, int]) -> NDArray[np.bool_]:
    """The blocks of the north and south polar rows that intersect the domain."""
    polar = np.zeros(shape, dtype=bool)
    north, south = (polar_rows, polar_rows) if isinstance(polar_rows, int) else polar_rows
    polar[: -(-north // DENSITY_STEP)] = True
    if south:
        band = -(-south // DENSITY_STEP)
        polar[-band:] = True
    return polar


def _graded_grid(  # noqa: PLR0913 - the sizes, land, bands, spacing, density and gradation.
    size: NDArray[np.int64],
    share: NDArray[np.int64],
    polar: NDArray[np.bool_],
    spacing: int,
    density: NDArray[np.int64] | None,
    *,
    gradation: int,
) -> NDArray[np.int64]:
    """The spacing (permille of the uniform ``spacing``) of blocks whose cells should be ``size``
    (thousandths of an octave of area): within ``SPACING_RANGE``, graded (``grade_spacing``,
    ``gradation``; the polar blocks keep ``POLAR_SPACING`` ungraded, for their cells become the
    large wastelands of the map's edge, and the land before them widens toward them
    ``APPROACH_SLOWER`` times more slowly from half their area), then moved by the settlement
    ``density`` (thousandths of an octave of area), which is smooth and needs no grading and
    never narrows the land before the bands, and
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
    slope = gradation * DENSITY_STEP // max(1, spacing)
    wanted = int(weight.sum()) * PERMILLE
    # The land before a polar band widens toward it, its first blocks from half the area of the
    # band's cells, so they border cells that grow into them instead of ordinary ones and remain
    # the larger, for those touching the map's edge become its wastelands.
    gentle = slope // APPROACH_SLOWER
    approach = -grade_spacing(
        -np.where(polar & has_land, POLAR_SPACING * PERMILLE // 1414 + gentle, 0), has_land, gentle
    )

    def graded(shift: int) -> NDArray[np.int64]:
        free = np.clip(spacing_permille(exponent - shift), SPACING_RANGE[0], SPACING_RANGE[1])
        out = grade_spacing(np.maximum(free, approach), has_land & ~polar, slope)
        if moved is not None:
            out = np.clip(out * moved // PERMILLE, SPACING_RANGE[0], SPACING_RANGE[1])
            out = np.maximum(out, approach)
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


@measured
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


@measured
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
    return _native.throw_seeds(
        np.ascontiguousarray(xs),
        np.ascontiguousarray(ys),
        np.ascontiguousarray(radius),
        smallest,
        widest,
        columns,
        SEED_GAP,
        checkpoint,
    )


@measured
def river_cells(  # noqa: PLR0913 - the land, its walls, the seeds' spacing and the merge size.
    land: NDArray[np.bool_],
    walls: NDArray[np.bool_],
    *,
    key: int,
    spacing: int,
    grid: NDArray[np.int64],
    smallest: int,
    coast: Callable[[NDArray[np.int32], int], NDArray[np.int64]] | None = None,
) -> NDArray[np.int32]:
    """Land cells grown from ``spaced_sites`` that do not cross ``walls`` (the border rivers),
    whose pixels then join the cell beside them; cells under ``smallest`` pixels are merged.

    Each seed grows as fast as its spacing (``synth.grow_weighted``): grown at one pace, a seed
    of the sparse land gives half of the way to each seed of the dense land beside it, and the
    cells of the largest spacings came out at three quarters of their area [V-EXEC 2026-11-13].
    The cells are grown ``SHORE_FEEDBACK_STEPS`` times before the last growth: each time the speed
    of every cell beside water (``_shore_cells``) is corrected toward its planned share of the land
    it and its neighbours grew (``_shore_gains``), and the first ``RELAX_STEPS`` times its seed
    moves to the centre of the cell it grew (``_centre_pixels``). Given ``coast`` (each grown
    cell's size offset by the sea, in thousandths of an octave: ``eu5_biomes.coastal_offsets``),
    a shore cell is corrected instead toward its planned square at the density of the inland cells
    round it, moved by that offset, and an inland cell grown more than ``SIZE_BAND`` off its plan
    at that density back to the band's edge (``_density_gains``).
    """
    sites = spaced_sites(key, land, spacing, grid)
    passable = land & ~walls
    columns = int(land.shape[1])
    placed = np.flatnonzero(sites.ravel() >= 0)
    order = sites.ravel()[placed].astype(np.int64)
    flat = np.zeros(order.size, dtype=np.int64)
    flat[order] = placed  # the pixel of each seed, by its number
    del placed, order
    gain = np.full(flat.size, PERMILLE, dtype=np.int64)
    for step in range(max(RELAX_STEPS, SHORE_FEEDBACK_STEPS)):
        planned = _seed_spacing(flat, grid, columns)
        grown = grow_weighted(passable, sites, planned * gain // PERMILLE)
        shore = _shore_cells(grown, land, flat.size)
        if step < SHORE_FEEDBACK_STEPS:
            gain = (
                _shore_gains(grown, planned, gain, shore)
                if coast is None
                else _density_gains(
                    grown,
                    planned,
                    gain,
                    shore,
                    blocks=_seed_blocks(flat, columns),
                    shape=(int(grid.shape[0]), int(grid.shape[1])),
                    offsets=coast(grown, flat.size),
                )
            )
        if step < RELAX_STEPS:
            flat = np.where(shore, _centre_pixels(grown, flat), flat)
            sites = np.full(land.shape, -1, dtype=np.int32)
            sites.ravel()[flat] = np.arange(flat.size, dtype=np.int32)
        del grown
    grown = grow_weighted(passable, sites, _seed_spacing(flat, grid, columns) * gain // PERMILLE)
    del sites, passable
    return merge_small(grow_regions(land, grown), smallest)


def _seed_spacing(
    flat: NDArray[np.int64], grid: NDArray[np.int64], columns: int
) -> NDArray[np.int64]:
    """The spacing (``grid``) at each seed's raster position ``flat``."""
    rows, cells = np.divmod(flat, columns)
    return grid[rows // DENSITY_STEP, cells // DENSITY_STEP].astype(np.int64)


def _grown_areas(grown: NDArray[np.int32], count: int) -> NDArray[np.int64]:
    """The pixels of each of the ``count`` cells of ``grown``, ``CENTRE_STRIP`` rows at a time."""
    area = np.zeros(count, dtype=np.int64)
    for first in range(0, int(grown.shape[0]), CENTRE_STRIP):
        cell = grown[first : first + CENTRE_STRIP]
        area += np.bincount(cell[(cell >= 0) & (cell < count)], minlength=count)[:count]
    return area


def _shore_gains(
    grown: NDArray[np.int32],
    planned: NDArray[np.int64],
    gain: NDArray[np.int64],
    shore: NDArray[np.bool_],
) -> NDArray[np.int64]:
    """The speed factors (``gain``, permille) of the cells of ``grown``, those of the ``shore``
    cells corrected toward their planned share of the land they and the cells beside them grew:
    the land shared by the squares of their spacings (``planned``), each factor multiplied by the
    square root of that share over the cell's area (within ``SHORE_GAIN_STEP``) and kept within
    ``SHORE_GAIN_RANGE``."""
    area = _grown_areas(grown, int(planned.size))
    squares = planned * planned
    return _corrected(gain, _shares(grown, squares, area), area, shore)


def _seed_blocks(flat: NDArray[np.int64], columns: int) -> tuple[NDArray[np.int64], ...]:
    """The ``DENSITY_STEP`` block (row, column) of each seed's raster position ``flat``."""
    rows, cells = np.divmod(flat, columns)
    return rows // DENSITY_STEP, cells // DENSITY_STEP


def _block_box(values: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """The sum of ``values`` over the blocks within ``radius`` of each (a square), the columns
    wrapping round the world and the rows ending at its edges."""
    padded = np.pad(values, ((radius, radius), (0, 0)))
    if radius:
        padded = np.concatenate([padded[:, -radius:], padded, padded[:, :radius]], axis=1)
    total = np.pad(padded.cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
    side = 2 * radius + 1
    return total[side:, side:] - total[:-side, side:] - total[side:, :-side] + total[:-side, :-side]


def _density_gains(  # noqa: PLR0913 - the cells, their spacing and speed, the shore, seeds, offsets.
    grown: NDArray[np.int32],
    planned: NDArray[np.int64],
    gain: NDArray[np.int64],
    shore: NDArray[np.bool_],
    *,
    blocks: tuple[NDArray[np.int64], ...],
    shape: tuple[int, int],
    offsets: NDArray[np.int64],
) -> NDArray[np.int64]:
    """``_shore_gains`` with each ``shore`` cell corrected toward its planned square (``planned``)
    at the density of the inland cells round it: the land they grew over the squares of their
    spacings, summed over the cells whose seeds lie within ``SHORE_DENSITY_BLOCKS`` of the cell's
    seed's block (``blocks``, of a grid of ``shape`` blocks), moved by its ``offsets``
    (thousandths of an octave of area); a shore cell with no inland cell so near keeps its share of
    its neighbourhood. An inland cell grown more than ``SIZE_BAND`` off its planned square at that
    density is corrected to the edge of the band."""
    count = int(planned.size)
    area = _grown_areas(grown, count)
    squares = planned * planned
    inland = ~shore
    rows, columns = blocks
    land_sum = np.zeros(shape, dtype=np.int64)
    square_sum = np.zeros(shape, dtype=np.int64)
    np.add.at(land_sum, (rows[inland], columns[inland]), area[inland])
    np.add.at(square_sum, (rows[inland], columns[inland]), squares[inland])
    near_land = _block_box(land_sum, SHORE_DENSITY_BLOCKS)[rows, columns]
    near_squares = _block_box(square_sum, SHORE_DENSITY_BLOCKS)[rows, columns]
    moved = spacing_permille(np.floor_divide(offsets * SPACING_PARTS, PERMILLE))
    planned_here = squares * near_land // np.maximum(near_squares, 1)
    dense = planned_here * moved // PERMILLE
    band = spacing_permille(np.array([-SIZE_BAND, SIZE_BAND]) * SPACING_PARTS // PERMILLE)
    kept = np.clip(area, planned_here * band[0] // PERMILLE, planned_here * band[1] // PERMILLE)
    wanted = np.where(shore, np.where(near_squares > 0, dense, _shares(grown, squares, area)), kept)
    return _corrected(gain, wanted, area, np.ones(count, dtype=bool))


def _shares(
    grown: NDArray[np.int32], squares: NDArray[np.int64], area: NDArray[np.int64]
) -> NDArray[np.int64]:
    """Each cell's share of the land (``area``) it and the cells beside it in ``grown`` grew,
    shared by their ``squares``."""
    count = int(squares.size)
    pairs = adjacency_pairs(grown)
    low = pairs >> np.int64(32)
    high = pairs & np.int64((1 << 32) - 1)
    keep = (low >= 0) & (high >= 0) & (low < count) & (high < count)
    low, high = low[keep], high[keep]
    around, weight = area.copy(), squares.copy()
    np.add.at(around, low, area[high])
    np.add.at(around, high, area[low])
    np.add.at(weight, low, squares[high])
    np.add.at(weight, high, squares[low])
    return around * squares // np.maximum(weight, 1)


def _corrected(
    gain: NDArray[np.int64],
    wanted: NDArray[np.int64],
    area: NDArray[np.int64],
    shore: NDArray[np.bool_],
) -> NDArray[np.int64]:
    """``gain`` of the ``shore`` cells multiplied by the root of ``wanted`` over their ``area``
    (within ``SHORE_GAIN_STEP``) and kept within ``SHORE_GAIN_RANGE``."""
    correction = np.array(
        [
            math.isqrt(share * PERMILLE * PERMILLE // max(own, 1))
            for share, own in zip(wanted.tolist(), area.tolist(), strict=True)
        ],
        dtype=np.int64,
    )
    moved = gain * np.clip(correction, *SHORE_GAIN_STEP) // PERMILLE
    return np.where(shore, np.clip(moved, *SHORE_GAIN_RANGE), gain)


def _shore_cells(
    grown: NDArray[np.int32], land: NDArray[np.bool_], count: int
) -> NDArray[np.bool_]:
    """Whether each of the ``count`` cells of ``grown`` has a pixel beside water (outside
    ``land``)."""
    out = np.zeros(count, dtype=bool)
    rows = int(grown.shape[0])
    for first in range(0, rows, CENTRE_STRIP):
        top, bottom = max(0, first - 1), min(rows, first + CENTRE_STRIP + 1)
        water = ~land[top:bottom]
        beside = np.zeros_like(water)
        beside[1:] |= water[:-1]
        beside[:-1] |= water[1:]
        beside[:, 1:] |= water[:, :-1]
        beside[:, :-1] |= water[:, 1:]
        part = grown[top:bottom]
        inner = slice(first - top, first - top + min(CENTRE_STRIP, rows - first))
        labels = part[inner][beside[inner] & (part[inner] >= 0)]
        out[labels] = True
    return out


@measured
def _centre_pixels(grown: NDArray[np.int32], flat: NDArray[np.int64]) -> NDArray[np.int64]:
    """The raster position of the centre of each cell of ``grown`` (numbered as the seeds at
    ``flat``): the pixel of its mean row and column (floored) when the cell holds it, else the
    cell's pixel nearest to it, the first in raster order of equals. A seed that grew no cell
    keeps its pixel."""
    checkpoint()
    out = _native.centre_pixels(np.ascontiguousarray(grown), np.ascontiguousarray(flat))
    checkpoint()
    return out
