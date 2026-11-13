"""Rivers of a generated domain, drawn before its cells (epoch 64, ``epoch.RIVERS_FIRST``).

Vanilla lays a large share of its rivers on location borders and sizes its locations by what
the land is: small in wet, warm lowlands and on the coasts, large in deserts, on dry steppes and
in the cold [V-EXEC, ``docs/terrain-biomes.md``]. Cells grown from a uniform scatter of seeds
before any river exists can do neither. So the domain's own rainfall (``domain_climate``: the
zonal-wind model of ``rnw.climate`` on the domain, everything outside its land and lakes being
sea) drains its relief first (``domain_rivers``), in the same independent watershed domains as
the export's rivers; the cells are then grown with the larger rivers as walls and seeds spaced
by the size vanilla gives the class the climate vote will choose (``spacing_grid``, from the
game's own locations: ``eu5_biomes.SizeModel``). The export draws the same rivers again from the
same inputs, so the borders it gets are the rivers it writes. Integer arithmetic and square
roots of exact integers.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import (
    CLIMATE_STEP,
    SIZE_STEP,
    ClimateGrid,
    block_features,
    class_sizes,
    climate_grid,
)
from rnw.eu5_rivers import watershed_spans
from rnw.fields import PERMILLE, block_mean
from rnw.rivers import (
    NONE,
    STEP,
    RiverGenerationError,
    Rivers,
    flow_classes,
    generate_rivers,
    outlet_problems,
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
    """Rainfall and distance to the sea on a grid ``CLIMATE_STEP`` coarser than the domain, with
    all but its land and lakes taken as sea. The domain's rows are the game map's (latitudes)."""
    return climate_grid(~(land | lakes), height)


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


def domain_rivers(  # noqa: PLR0913 - the land, relief, lakes, rain, seam and seed.
    land: NDArray[np.bool_],
    height: NDArray[np.int32],
    *,
    lakes: NDArray[np.bool_],
    rain: NDArray[np.int64],
    seam: int | None,
    seed: int,
) -> Rivers:
    """The rivers of the domain in independent watershed domains split at ``seam`` (the column
    the game's map starts at; None: no seam), each draining to genuine water.

    The same planning as the export's (``eu5_nw_export._river_basins``) with the domain's own
    ``rain`` (``domain_climate``); a span that cannot drain or has a bad outlet fails.
    """
    rows, columns = (int(size) for size in land.shape)
    spans = ((0, columns),) if seam is None else watershed_spans(columns, seam)
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
    for left, right in spans:
        domain = land[:, left:right]
        target = Rivers(rivers.role[:, left:right], rivers.flow[:, left:right], {})
        found = generate_rivers(
            domain,
            height[:, left:right],
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
# Spacing levels are eighths of an octave of the uniform spacing (a quarter octave of a cell's
# area); ``SPACING[k - SPACING_LOW]`` is level k in permille, from 0.59 to 3.36 times the spacing.
SPACING_LOW: Final[int] = -6
SPACING: Final[tuple[int, ...]] = (
    595, 648, 707, 771, 841, 917, 1000, 1091, 1189, 1297, 1414, 1542, 1682, 1834,
    2000, 2181, 2378, 2594, 2828, 3084, 3364,
)  # fmt: skip
POLAR_SPACING: Final[int] = 3000  # permille of the spacing in the polar bands, as before


def spacing_grid(
    land: NDArray[np.bool_],
    height: NDArray[np.integer],
    climate: ClimateGrid,
    *,
    polar_rows: int,
    sizes: SizeModel,
) -> NDArray[np.int64]:
    """Seed spacing of every ``DENSITY_STEP`` block, in permille of the uniform spacing.

    Each ``SIZE_STEP`` block of land takes the size of the vanilla locations of the class the
    vote will give it (``eu5_biomes.class_sizes``), quantized to the levels of ``SPACING`` and
    shifted as a whole so that the land outside the polar bands expects as many cells as the
    uniform spacing gives it. The sizes are not smoothed: vanilla's change from one class to the
    next. The ``polar_rows`` rows at either edge keep ``POLAR_SPACING``.
    """
    step = DENSITY_STEP
    rows, columns = (int(size) for size in land.shape)
    shape = (-(-rows // step), -(-columns // step))
    share = np.empty(shape, dtype=np.int64)
    strip = step * 32
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        blocks = slice(first // step, -(-window.stop // step))
        share[blocks] = block_mean(land[window].astype(np.int64) * PERMILLE, step)
    found, features = block_features(land, height, climate)
    coarse = np.zeros(found.shape, dtype=np.int64)
    if features.size:
        coarse[found] = class_sizes(sizes, features)
    ratio = SIZE_STEP // step
    size = np.repeat(np.repeat(coarse, ratio, axis=0), ratio, axis=1)[: shape[0], : shape[1]]
    level = np.floor_divide(size + 125, 250)
    polar = np.zeros(shape, dtype=bool)
    band = -(-polar_rows // step) if polar_rows else 0
    if band:
        polar[:band] = True
        polar[-band:] = True
    weight = np.where(polar, 0, share)
    # Expected cells of a block at level k are its land over 2^(k / 4); pick the shift that keeps
    # their sum nearest the uniform spacing's (exact integers, no logarithms).
    wanted = int(weight.sum()) * PERMILLE
    best: tuple[int, int] = (1 << 62, 0)
    for shift in range(-24, 25):
        shifted = np.clip(level - shift, SPACING_LOW, SPACING_LOW + len(SPACING) - 1)
        spacing = np.array(SPACING, dtype=np.int64)[shifted - SPACING_LOW]
        expected = int((weight * PERMILLE * PERMILLE * PERMILLE // (spacing * spacing)).sum())
        best = min(best, (abs(expected - wanted), shift))
    shifted = np.clip(level - best[1], SPACING_LOW, SPACING_LOW + len(SPACING) - 1)
    out = np.array(SPACING, dtype=np.int64)[shifted - SPACING_LOW]
    return np.where(polar, POLAR_SPACING, out)


def variable_sites(
    key: int, mask: NDArray[np.bool_], spacing: int, grid: NDArray[np.int64]
) -> NDArray[np.int32]:
    """Jittered-grid seeds inside ``mask`` whose spacing follows ``grid`` (``spacing_grid``).

    Each level of the grid has a jittered grid of its own spacing, kept in the blocks of that
    level; every component of the mask gets at least one seed. Seeds are numbered in raster order.
    """
    rows, columns = (int(size) for size in mask.shape)
    found: list[NDArray[np.int64]] = []
    for level in np.unique(grid).tolist():
        size = max(1, spacing * int(level) // PERMILLE)
        gx = np.arange(-(-columns // size), dtype=np.int64)
        gy = np.arange(-(-rows // size), dtype=np.int64)
        hashed = hash_grid(derive_seed(key, f"level_{level}"), gx[np.newaxis, :], gy[:, np.newaxis])
        sx = gx[np.newaxis, :] * size + (hashed & np.uint64(0xFFFF)).astype(np.int64) % size
        sy = (
            gy[:, np.newaxis] * size
            + ((hashed >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64) % size
        )
        inside = (sx < columns) & (sy < rows)
        sx, sy = sx[inside], sy[inside]
        keep = mask[sy, sx] & (grid[sy // DENSITY_STEP, sx // DENSITY_STEP] == level)
        found.append(sy[keep] * columns + sx[keep])
    flat = np.unique(np.concatenate(found)) if found else np.zeros(0, dtype=np.int64)
    components = label_components(mask.astype(np.int32))
    covered = np.zeros(int(components.max()) + 1, dtype=bool)
    covered[components.ravel()[flat]] = True
    firsts = first_pixels(components)
    extra = firsts[mask.ravel()[firsts] & ~covered[components.ravel()[firsts]]]
    ordered = np.unique(np.concatenate([flat, extra]))
    seeds = np.full(mask.size, -1, dtype=np.int32)
    seeds[ordered] = np.arange(ordered.size, dtype=np.int32)
    return seeds.reshape(mask.shape)


def river_cells(  # noqa: PLR0913 - the land, its walls, the seeds' spacing and the merge size.
    land: NDArray[np.bool_],
    walls: NDArray[np.bool_],
    *,
    key: int,
    spacing: int,
    grid: NDArray[np.int64],
    smallest: int,
) -> NDArray[np.int32]:
    """Land cells grown from ``variable_sites`` that do not cross ``walls`` (the border rivers),
    whose pixels then join the cell beside them; cells under ``smallest`` pixels are merged.

    Each seed grows as fast as its spacing (``synth.grow_weighted``): grown at one pace, a seed
    of the sparse land gives half of the way to each seed of the dense land beside it, and the
    cells of the largest spacings came out at three quarters of their area [V-EXEC 2026-11-13].
    """
    sites = variable_sites(key, land, spacing, grid)
    rows, columns = np.nonzero(sites >= 0)
    speed = np.zeros(int(sites.max()) + 1 if rows.size else 0, dtype=np.int64)
    speed[sites[rows, columns]] = grid[rows // DENSITY_STEP, columns // DENSITY_STEP]
    del rows, columns
    grown = grow_weighted(land & ~walls, sites, speed)
    del sites
    return merge_small(grow_regions(land, grown), smallest)
