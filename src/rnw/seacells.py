"""Rectangular open-sea cells and a local partition for shores, straits and ocean crossings.

Start with a balanced rectangular grid. Whole tiles in unconstrained water stay as drawn.
The rest is divided along shore bands and into separate narrows by a geodesic partition.
The sites of designed crossings keep their places. Compact islands contribute to the actual
land mask and port graph. The shape of the offshore grid is independent of their positions.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.progress import checkpoint
from rnw.sea_corridors import CLEAR_PERMILLE, clear_of_corridors, corridor_paths, corridor_sites
from rnw.synth import jittered_sites
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

# One coarse pixel is this share of a typical cell's side: a cell is about twenty of them wide.
COARSE_DIVISOR: Final[int] = 20
MIN_COARSE: Final[int] = 2
# The width of a band along the coast and the number of bands before the open sea, in permille
# of the typical cell's side and in bands.
BAND_PERMILLE: Final[int] = 1000
BANDS: Final[int] = 2
# The coastal band alone is this wide (permille of the typical cell's side): its cells lie along the
# coast longer than they are wide, so that there are fewer of them to serve with the ports of the
# land beside them.
COAST_PERMILLE: Final[int] = 700
# Water that no disk of this radius (permille of the typical cell's side) fits in, and that joins
# two wider waters, is a strait.
NECK_PERMILLE: Final[int] = 300
# A cell above this many typical cells is divided, one below this is given to its neighbours
# (permille of the typical area).
SPLIT_PERMILLE: Final[int] = 1500
DROP_PERMILLE: Final[int] = 500
PERMILLE: Final[int] = 1000
# A compact obstruction can lie inside one tile, leaving most of it navigable. Both bounds
# matter: a thin island longer than a tile is a coast, as is bulky land within the span.
ISLAND_SPAN_PERMILLE: Final[int] = 1250
ISLAND_AREA_PERMILLE: Final[int] = 450
# The relaxation: rounds that may divide and remove cells, then rounds that only centre them.
SETTLING_ROUNDS: Final[int] = 14
CENTRING_ROUNDS: Final[int] = 4
EIGHTH: Final[int] = 8
# A strait joins at least this many wide waters.
JOINS: Final[int] = 2
# How many coarse pixels each way the full raster looks for the cells that may own a pixel.
REACH: Final[int] = 3


def coarse_step(spacing: int) -> int:
    """The side of a coarse pixel, in pixels, for cells of ``spacing``."""
    return max(MIN_COARSE, spacing // COARSE_DIVISOR)


@dataclass(frozen=True, slots=True, eq=False)
class Layout:
    """The water on the coarse raster: its weight, its flags and its regions.

    ``depth`` is the distance of every coarse pixel from land in eighths of a coarse pixel, ``band``
    the width of a band in the same unit, and ``neck`` the water of the straits.
    """

    step: int
    mass: NDArray[np.int64]
    water: NDArray[np.bool_]
    region: NDArray[np.int32]
    depth: NDArray[np.int32]
    neck: NDArray[np.bool_]
    band: int


def _mass(flags: NDArray[np.bool_], step: int) -> NDArray[np.int64]:
    """The flagged pixels in every ``step`` x ``step`` block of the raster."""
    height, width = flags.shape
    rows, columns = -(-height // step), -(-width // step)
    out = np.zeros((rows, columns), dtype=np.int64)
    for first in range(0, rows, 256):
        stop = min(rows, first + 256)
        block = flags[first * step : min(height, stop * step)]
        padded = np.zeros(((stop - first) * step, columns * step), dtype=np.bool_)
        padded[: block.shape[0], : block.shape[1]] = block
        out[first:stop] = padded.reshape(stop - first, step, columns, step).sum(axis=(1, 3))
    return out


def _necks(water: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Water that no disk of ``radius`` coarse pixels fits in, that joins two wider waters."""
    limit = EIGHTH * (radius + 2)
    inside = water & (euclidean_distance(~water, limit) >= EIGHTH * radius)
    reached = euclidean_distance(inside, limit) <= EIGHTH * radius
    wide = water & reached
    thin = water & ~wide
    if not thin.any():
        return thin
    broad = label_components(np.where(wide, 1, 0).astype(np.int32))
    narrow = label_components(np.where(thin, 1, 0).astype(np.int32))
    wide_count = int(broad.max()) + 1
    pairs: set[int] = set()
    for here, there in (
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
        ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
        ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
    ):
        mine, other = narrow[here], broad[there]
        touches = thin[here] & wide[there]
        pairs.update(
            np.unique(mine[touches].astype(np.int64) * wide_count + other[touches]).tolist()
        )
    joined: dict[int, set[int]] = {}
    for pair in pairs:
        joined.setdefault(pair // wide_count, set()).add(pair % wide_count)
    necks = {key for key, group in joined.items() if len(group) >= JOINS}
    # A longer route may connect the mouths elsewhere, as in an archipelago or between
    # an island and the mainland. Identify such mouths on a bounded local window.
    candidates = sorted(joined.keys() - necks)
    if candidates:
        rows, columns = np.nonzero(thin)
        ids = narrow[rows, columns]
        order = np.argsort(ids, kind="stable")
        sorted_ids = ids[order]
        first = np.searchsorted(sorted_ids, candidates)
        past = np.searchsorted(sorted_ids, candidates, side="right")
        for key, start, stop in zip(candidates, first, past, strict=True):
            points = order[start:stop]
            if _local_mouths(wide, narrow, key, rows[points], columns[points], radius):
                necks.add(key)
    neck_ids = np.array(sorted(necks), dtype=np.int64)
    return thin & np.isin(narrow, neck_ids)


def _local_mouths(  # noqa: PLR0913, PLR0917 - the shape and the scale of the passage.
    wide: NDArray[np.bool_],
    narrow: NDArray[np.int32],
    key: int,
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    radius: int,
) -> bool:
    """Test for two substantial mouths within a few sea widths of the same narrow passage."""
    collar = 2 * radius
    if max(np.ptp(rows), np.ptp(columns)) > 8 * radius:
        return False
    window = (
        slice(max(0, int(rows.min()) - collar), int(rows.max()) + collar + 1),
        slice(max(0, int(columns.min()) - collar), int(columns.max()) + collar + 1),
    )
    water = wide[window]
    parts = label_components(water.astype(np.int32))
    cut = narrow[window] == key
    contact = np.zeros_like(cut)
    contact[:-1] |= cut[1:]
    contact[1:] |= cut[:-1]
    contact[:, :-1] |= cut[:, 1:]
    contact[:, 1:] |= cut[:, :-1]
    mouths = np.unique(parts[contact & water])
    areas = np.bincount(parts.ravel())
    return int((areas[mouths] >= radius**2).sum()) >= JOINS


def _compact_islands(solid: NDArray[np.int64], step: int, spacing: int) -> NDArray[np.bool_]:
    """Find land whose footprint can sit within a tile without imposing a row of coastal cells."""
    land = solid > 0
    parts = label_components(land.astype(np.int32))
    count = int(parts.max()) + 1
    rows, columns = np.nonzero(land)
    owner = parts[rows, columns]
    area = np.bincount(owner, weights=solid[rows, columns], minlength=count)
    low = np.full((2, count), max(land.shape), dtype=np.int64)
    high = np.zeros_like(low)
    for axis, coords in enumerate((rows, columns)):
        np.minimum.at(low[axis], owner, coords)
        np.maximum.at(high[axis], owner, coords)
    span = (high - low + 1).max(axis=0)
    small = (
        (area > 0)
        & (area * PERMILLE <= spacing**2 * ISLAND_AREA_PERMILLE)
        & (span * step * PERMILLE <= spacing * ISLAND_SPAN_PERMILLE)
    )
    return land & small[parts]


def layout(ocean: NDArray[np.bool_], spacing: int) -> Layout:
    """The coarse raster of ``ocean`` and its regions: the bands along the coast and the straits.

    Whatever is not ocean is the shore the bands follow: the land, the lakes and the edge of the
    generated domain, where the cells lie along the edge as they lie along a coast. Distances and
    the coarse partition can run across a small island. The true water mask still excludes it
    when the full-resolution cells are drawn.
    """
    step = coarse_step(spacing)
    mass = _mass(ocean, step)
    solid = _mass(~ocean, step)
    covered = _compact_islands(solid, step, spacing)
    water = (mass > 0) | covered
    land = (2 * solid >= step * step) & ~covered
    band = EIGHTH * max(1, round(BAND_PERMILLE * spacing / (PERMILLE * step)))
    coast = EIGHTH * max(1, round(COAST_PERMILLE * spacing / (PERMILLE * step)))
    reached = euclidean_distance(land, band * (BANDS + 1))
    # The distance is counted in bands: the coastal band is ``coast`` wide, the others ``band``.
    depth = np.where(reached < coast, reached * band // coast, reached - coast + band)
    ring = np.minimum(depth // band, BANDS)
    neck = _necks(mass > 0, max(1, round(NECK_PERMILLE * spacing / (PERMILLE * step))))
    code = np.where(water, ring + 1, 0)
    code[neck & water] = BANDS + 2
    region = label_components(code.astype(np.int32))
    return Layout(
        step, mass + np.where(covered, solid, 0), water, region, depth.astype(np.int32), neck, band
    )


def _geodesic(
    flags: Layout, rows: NDArray[np.int64], columns: NDArray[np.int64]
) -> tuple[NDArray[np.int32], NDArray[np.uint32]]:
    sites = np.ascontiguousarray(np.stack((rows, columns), axis=1))
    checkpoint()
    label, cost = _native.sea_geodesic(
        np.ascontiguousarray(flags.water),
        np.ascontiguousarray(flags.region),
        sites,
        np.zeros(len(rows), dtype=np.uint32),
    )
    checkpoint()
    return label, cost


def _unserved(
    flags: Layout, rows: NDArray[np.int64], columns: NDArray[np.int64]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """The sites with one added, where a region has none, at the first pixel of the region."""
    width = flags.water.shape[1]
    sea = np.flatnonzero(flags.water.ravel())
    region_of = flags.region.ravel()[sea]
    held = np.zeros(int(flags.region.max()) + 1, dtype=bool)
    held[flags.region[rows, columns]] = True
    wanted, first = np.unique(region_of, return_index=True)
    missing = first[~held[wanted]]
    spots = sea[missing]
    return (
        np.concatenate((rows, spots // width)),
        np.concatenate((columns, spots % width)),
    )


def _sums(owner: NDArray[np.intp], values: NDArray[np.float64], count: int) -> NDArray[np.float64]:
    """The sum of ``values`` of each of ``count`` owners."""
    return np.asarray(np.bincount(owner, weights=values, minlength=count), dtype=np.float64)


def relax(
    flags: Layout,
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    pinned: int,
    typical: float,
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int32]]:
    """The sites of ``rows`` / ``columns`` (coarse pixels) moved to the middle of their cells and
    the cells divided or given away until they are of one size; the first ``pinned`` sites stay
    where they are. ``typical`` is the area of a cell in pixels.

    Returns the final sites and the coarse partition made from them.
    """
    water = flags.water
    width = water.shape[1]
    sea = np.flatnonzero(water.ravel())
    if not sea.size:
        return rows, columns, np.full(water.shape, -1, dtype=np.int32)
    sea_rows, sea_columns = sea // width, sea % width
    weights = flags.mass.ravel()[sea].astype(np.float64)
    rows, columns = _unserved(flags, rows, columns)
    total = SETTLING_ROUNDS + CENTRING_ROUNDS
    label = np.zeros(water.shape, dtype=np.int32)
    for step in range(total):
        label, cost = _geodesic(flags, rows, columns)
        count = len(rows)
        owner = label.ravel()[sea]
        reached = owner >= 0
        area = np.bincount(owner[reached], weights=weights[reached], minlength=count)
        if step == total - 1:
            break
        held: NDArray[np.intp] = owner[reached].astype(np.intp)
        row_weights: NDArray[np.float64] = (weights * sea_rows)[reached]
        column_weights: NDArray[np.float64] = (weights * sea_columns)[reached]
        mean_row = _sums(held, row_weights, count)
        mean_column = _sums(held, column_weights, count)
        safe = np.maximum(area, 1.0)
        centres = np.ascontiguousarray(np.stack((mean_row / safe, mean_column / safe), axis=1))
        near, far = _native.sea_extremes(label, cost, centres)
        free = np.arange(count) >= pinned
        new_rows, new_columns = rows.copy(), columns.copy()
        moved = free & (near >= 0)
        new_rows[moved], new_columns[moved] = near[moved] // width, near[moved] % width
        keep = np.ones(count, dtype=bool)
        added_rows: list[int] = []
        added_columns: list[int] = []
        if step < SETTLING_ROUNDS:
            home = flags.region[rows, columns]
            alone = np.bincount(home, minlength=int(flags.region.max()) + 1)
            for cell in range(count):
                size = area[cell] * PERMILLE
                if size > SPLIT_PERMILLE * typical and far[cell] >= 0:
                    # A cell that keeps its site (a crossing's) is divided too: the new one is free.
                    added_rows.append(int(far[cell] // width))
                    added_columns.append(int(far[cell] % width))
                elif free[cell] and size < DROP_PERMILLE * typical and alone[home[cell]] > 1:
                    keep[cell] = False
                    alone[home[cell]] -= 1
        rows = np.concatenate((new_rows[keep], np.asarray(added_rows, dtype=np.int64)))
        columns = np.concatenate((new_columns[keep], np.asarray(added_columns, dtype=np.int64)))
        pinned = int(keep[:pinned].sum())
    return rows, columns, label


def _grid(
    flags: Layout,
    spacing: int,
    pinned_rows: NDArray[np.int64],
    pinned_columns: NDArray[np.int64],
) -> NDArray[np.int32]:
    """Give each whole tile in deep water its grid number, and give other water to the local cut."""
    sides: list[NDArray[np.int64]] = []
    for size in flags.water.shape:
        count = max(1, (size * flags.step + spacing // 2) // spacing)
        sides.append(np.arange(count + 1, dtype=np.int64) * size // count)
    rows, columns = sides
    open_water = flags.water & ~flags.neck & (flags.depth >= flags.band * BANDS)
    open_water[pinned_rows, pinned_columns] = False
    complete = np.logical_and.reduceat(open_water, rows[:-1], axis=0)
    complete = np.logical_and.reduceat(complete, columns[:-1], axis=1)
    tiles = np.full(complete.shape, -1, dtype=np.int32)
    tiles[complete] = np.arange(int(complete.sum()), dtype=np.int32)
    return np.repeat(np.repeat(tiles, np.diff(rows), axis=0), np.diff(columns), axis=1)


def partition(
    ocean: NDArray[np.bool_],
    key: int,
    *,
    spacing: int,
    bands: NDArray[np.bool_] | None = None,
    domain: NDArray[np.bool_] | None = None,
) -> NDArray[np.int32]:
    """Lay out the offshore grid and solve the water along its coasts at the original resolution."""
    flags = layout(ocean, spacing)
    rows, columns = jittered_sites(key, ocean.shape, spacing)
    pinned_rows = np.empty(0, dtype=np.int64)
    pinned_columns = np.empty(0, dtype=np.int64)
    if bands is not None:
        if bands.shape != ocean.shape:
            message = "Current bands do not fit the world"
            raise ValueError(message)
        paths = corridor_paths(ocean, bands, spacing, domain=domain)
        clear = clear_of_corridors(rows, columns, paths, spacing * CLEAR_PERMILLE / PERMILLE)
        pinned_rows, pinned_columns = corridor_sites(paths, ocean, spacing, key)
        rows, columns = rows[clear], columns[clear]
    return _draw(
        ocean,
        flags,
        rows,
        columns,
        pinned_rows=pinned_rows,
        pinned_columns=pinned_columns,
        spacing=spacing,
    )


def _draw(  # noqa: PLR0913 - the mesh, size and two sets of coordinates.
    ocean: NDArray[np.bool_],
    flags: Layout,
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    *,
    pinned_rows: NDArray[np.int64],
    pinned_columns: NDArray[np.int64],
    spacing: int,
) -> NDArray[np.int32]:
    step = flags.step
    tiles = _grid(flags, spacing, pinned_rows // step, pinned_columns // step)
    water = flags.water & (tiles < 0)
    bands = np.where(water, np.minimum(flags.depth // flags.band, BANDS) + 1, 0)
    bands[flags.neck & water] = BANDS + 2
    adaptive = replace(flags, water=water, region=label_components(bands.astype(np.int32)))
    valid = water[rows // step, columns // step]
    pinned = len(pinned_rows)
    rows = np.concatenate((pinned_rows, rows[valid]))
    columns = np.concatenate((pinned_columns, columns[valid]))
    final_rows, final_columns, coarse = relax(
        adaptive,
        (rows // step).astype(np.int64),
        (columns // step).astype(np.int64),
        pinned,
        float(spacing * spacing),
    )
    sites = np.stack((final_rows * step + step // 2, final_columns * step + step // 2), axis=1)
    sites[:pinned] = np.stack((rows[:pinned], columns[:pinned]), axis=1)
    # Values below -1 mark finished grid tiles in the native rasteriser.
    locked = tiles >= 0
    coarse[locked] = -2 - tiles[locked]
    home = np.minimum(flags.depth[final_rows, final_columns] // flags.band, BANDS).astype(np.int32)
    home[flags.neck[final_rows, final_columns]] = -1
    checkpoint()
    labels = _native.sea_refine(
        np.ascontiguousarray(ocean),
        np.ascontiguousarray(coarse),
        step,
        REACH,
        np.ascontiguousarray(sites.astype(np.int64)),
        np.ascontiguousarray(flags.depth),
        flags.band,
        BANDS,
        np.ascontiguousarray(home),
    )
    checkpoint()
    return labels
