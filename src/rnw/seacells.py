"""Compact sea cells: the water divided into pieces that a ship can cross, of one size and shape.

The sea of a generated world was divided by the nearest of a jittered grid of sites, in a straight
line. That is a land cell's way, and it makes a sea cell that is not what the game's own are:
water behind a spit of land belongs to the cell on the other side of it, a cell reaches through
a strait to the sea beyond, a cell is a long crescent round an island, and the sizes run from a
fifth of the spacing to three times it. The game's sea zones are the other thing: each is one
compact piece of water, the zones beside each other are of one size, the zones along a coast lie
in rows that follow it, and a strait is a zone of its own.

The water is therefore divided in three steps:

* **Regions.** The water is cut into bands of about one cell's width by its distance from land (the
  coastal band, the next, ... the open sea beyond the last) and a strait, a passage no wider than
  two ``NECK_PERMILLE`` of a cell, is a region of its own. No cell ever crosses the border of a
  region, so the cells of a band are a row along the coast, each next row is cut on its own (as
  the bricks of a wall are), and no cell reaches through a strait to the sea beyond it.
* **Cells.** The sites are relaxed on the **distance through the water** (``geodesic``), not the
  straight distance: a cell is the water nearer to its site than to any other by a way that stays
  in its region, so a spit or an island ends it. The sites move to the middle of their cells (a
  Lloyd step) and a cell that is too large is divided, one that is too small is given to its
  neighbours, until the sizes are even.
* **Islands.** A small island is no coast the bands follow: it lies inside a cell of its own, the
  disk of water about it (a cell's own port is all such a coast can give), as the game's halo
  around a small island is one zone, not a ring of crescents each of which would need a port. The
  other cells are made round the disk.
* **Borders.** The final raster follows the coarse one but with every border cut straight
  between two sites (``refine``), so that the cells are polygons with straight sides, not stairs.

Nothing here draws a random number: the sites are the jittered grid's (``synth.seed_sites``) and
the corridors' chains (``sea_corridors``), which keep their places.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.progress import checkpoint
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

# One coarse pixel is this share of a typical cell's side: a cell is about twenty of them wide.
COARSE_DIVISOR: Final[int] = 20
MIN_COARSE: Final[int] = 2
# The width of a band along the coast and the number of bands before the open sea, in permille
# of the typical cell's side and in bands.
BAND_PERMILLE: Final[int] = 1000
BANDS: Final[int] = 4
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
# An island that a disk of this radius (permille of the cell's side) holds lies in a cell of its
# own: the disk of water about it. The bands keep level about the island, and the disk reaches
# beyond its shore, by ISLAND_MARGIN_PERMILLE of the side; the water in the disk is at least
# ISLAND_WATER_PERMILLE of a typical cell, whatever the island's size. The sites of other cells keep
# ISLAND_CLEAR_PERMILLE of the side off the disk.
ISLAND_PERMILLE: Final[int] = 675
ISLAND_MARGIN_PERMILLE: Final[int] = 250
ISLAND_WATER_PERMILLE: Final[int] = 600
ISLAND_CLEAR_PERMILLE: Final[int] = 100
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
    the width of a band in the same unit, ``neck`` the water of the straits and ``islands`` the
    middles (coarse row, column) of the small islands the water lies round without a band.
    """

    step: int
    mass: NDArray[np.int64]
    water: NDArray[np.bool_]
    region: NDArray[np.int32]
    depth: NDArray[np.int32]
    neck: NDArray[np.bool_]
    band: int
    islands: NDArray[np.int64]
    discs: NDArray[np.int32]


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
    neck_ids = np.array(
        sorted(key for key, group in joined.items() if len(group) >= JOINS), dtype=np.int64
    )
    return thin & np.isin(narrow, neck_ids)


def _small_islands(
    land: NDArray[np.bool_], solid: NDArray[np.int64], step: int, limit: int
) -> tuple[NDArray[np.int32], NDArray[np.int64]]:
    """The islands of ``land`` that a disk of ``limit`` pixels holds: a map and their middles.

    ``solid`` is the land in every coarse pixel, in pixels. The map numbers the islands from 1 (0
    elsewhere); there is a row of the second array for each island, in the order of the numbers:
    the centre of mass (row, column in coarse pixels), the radius, in pixels, of the disk about it
    that holds the island, and its area in pixels.
    """
    parts = label_components(land.astype(np.int32))
    count = int(parts.max()) + 1
    rows, columns = np.nonzero(land)
    owner = parts[rows, columns]
    weight = solid[rows, columns].astype(np.float64)
    area = np.bincount(owner, weights=weight, minlength=count)
    mean_row = np.bincount(owner, weights=weight * rows, minlength=count) / np.maximum(area, 1.0)
    mean_column = np.bincount(owner, weights=weight * columns, minlength=count) / np.maximum(
        area, 1.0
    )
    # Half a coarse pixel more than the farthest pixel's middle: the pixel's own edge.
    reach = np.hypot(rows - mean_row[owner], columns - mean_column[owner]) + 0.5
    radius = np.zeros(count)
    np.maximum.at(radius, owner, reach)
    small = (area > 0) & (radius * step <= limit)
    chosen = np.flatnonzero(small)
    number = np.zeros(count, dtype=np.int32)
    number[chosen] = np.arange(1, len(chosen) + 1, dtype=np.int32)
    middles = np.stack(
        (
            np.rint(mean_row[chosen]),
            np.rint(mean_column[chosen]),
            np.ceil(radius[chosen] * step),
            area[chosen],
        ),
        axis=1,
    )
    return np.where(land, number[parts], 0).astype(np.int32), middles.astype(np.int64)


def layout(ocean: NDArray[np.bool_], spacing: int) -> Layout:
    """The coarse raster of ``ocean`` and its regions: the bands along the coast and the straits.

    Whatever is not ocean is the shore the bands follow: the land, the lakes and the edge of the
    generated domain, where the cells lie along the edge as they lie along a coast. A small island
    is no shore: the water is taken to cover it, the bands are level over the disk of water that is
    its cell, and that disk is no water for the cells of the rest.
    """
    step = coarse_step(spacing)
    mass = _mass(ocean, step)
    solid = _mass(~ocean, step)
    land = 2 * solid >= step * step
    covering, found = _small_islands(land, solid, step, ISLAND_PERMILLE * spacing // PERMILLE)
    covered = covering > 0
    water = (mass > 0) | covered
    land &= ~covered
    band = EIGHTH * max(1, round(BAND_PERMILLE * spacing / (PERMILLE * step)))
    coast = EIGHTH * max(1, round(COAST_PERMILLE * spacing / (PERMILLE * step)))
    reached = euclidean_distance(land, band * (BANDS + 1))
    # The distance is counted in bands: the coastal band is ``coast`` wide, the others ``band``.
    depth = np.where(reached < coast, reached * band // coast, reached - coast + band)
    # The disk of an island holds the island, a margin of water about it and water for a cell.
    needed = ISLAND_WATER_PERMILLE * spacing * spacing / PERMILLE + found[:, 3]
    reach = np.maximum(
        found[:, 2] + ISLAND_MARGIN_PERMILLE * spacing // PERMILLE, np.ceil(np.sqrt(needed / np.pi))
    ).astype(np.int64)
    islands = np.stack((found[:, 0], found[:, 1], reach), axis=1)
    discs = np.zeros(land.shape, dtype=np.int32)
    for index, (row, column, radius) in enumerate(islands.tolist()):
        span = radius // step + 1
        window = (
            slice(max(0, row - span), min(land.shape[0], row + span + 1)),
            slice(max(0, column - span), min(land.shape[1], column + span + 1)),
        )
        rows, columns = np.ogrid[window]
        inside = (rows - row) ** 2 + (columns - column) ** 2 <= (radius / step) ** 2
        inside &= discs[window] == 0
        # The bands run level over the disk, at the level of its middle (after the first disk's).
        depth[window][inside & water[window]] = depth[row, column]
        discs[window][inside] = index + 1
    ring = np.minimum(depth // band, BANDS)
    neck = _necks(water & ~covered, max(1, round(NECK_PERMILLE * spacing / (PERMILLE * step))))
    water &= discs == 0
    code = np.where(water, ring + 1, 0)
    code[neck & water] = BANDS + 2
    region = label_components(code.astype(np.int32))
    return Layout(
        step, mass, water, region, depth.astype(np.int32), neck & water, band, islands, discs
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


def partition(
    ocean: NDArray[np.bool_],
    rows: NDArray[np.int64],
    columns: NDArray[np.int64],
    *,
    pinned: int,
    spacing: int,
) -> NDArray[np.int32]:
    """The sea cells of ``ocean``, relaxed from the sites at ``rows`` / ``columns`` (the first
    ``pinned`` of which keep their place); -1 outside the water, cells numbered by site.

    A cell can be in several pieces where the coarse raster joined what the full one parts (the
    caller's ``label_components`` tells them apart).
    """
    flags = layout(ocean, spacing)
    step = flags.step
    middle_rows = flags.islands[:, 0] * step + step // 2
    middle_columns = flags.islands[:, 1] * step + step // 2
    reach = flags.islands[:, 2]
    free = np.arange(len(rows)) >= pinned
    if len(middle_rows):
        # The sites of other cells give way to the disk of an island's cell.
        clear = reach + ISLAND_CLEAR_PERMILLE * spacing // PERMILLE
        beside = (
            (rows[:, None] - middle_rows[None, :]) ** 2
            + (columns[:, None] - middle_columns[None, :]) ** 2
            < clear[None, :] ** 2
        ).any(axis=1)
        free &= ~beside
    chain = pinned
    rows = np.concatenate((rows[:pinned], middle_rows, rows[free]))
    columns = np.concatenate((columns[:pinned], middle_columns, columns[free]))
    pinned += len(middle_rows)
    final_rows, final_columns, coarse = relax(
        flags,
        (rows // step).astype(np.int64),
        (columns // step).astype(np.int64),
        pinned,
        float(spacing * spacing),
    )
    # An island's disk is its cell's, whatever the water round it gave the other cells.
    coarse = np.where(flags.discs > 0, chain + flags.discs - 1, coarse).astype(np.int32)
    sites = np.stack((final_rows * step + step // 2, final_columns * step + step // 2), axis=1)
    sites[:pinned] = np.stack((rows[:pinned], columns[:pinned]), axis=1)
    home = np.minimum(flags.depth[final_rows, final_columns] // flags.band, BANDS).astype(np.int32)
    home[flags.neck[final_rows, final_columns]] = -1
    claim = np.zeros(len(final_rows), dtype=np.int64)
    claim[chain : chain + len(reach)] = reach * reach
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
        np.ascontiguousarray(claim),
    )
    checkpoint()
    return labels
