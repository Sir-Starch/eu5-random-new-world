"""Generate a complete New World inside an arbitrary domain mask (T3, game-independent).

The domain is the set of pixels that may be replaced. A ring of ocean is kept along its
border so generated seas meet the surrounding (protected) ocean, and a strait along an
optional seam column where the map wraps: EU5 does not stitch terrain across the wrap,
so land there shows a crack [V-GAME owner observation, 1.4.1]. Land carries a
continuous relief field (``relief.py``); the highest cells become wastelands. Everything
is integer arithmetic driven by named SplitMix64 streams, so equal inputs give equal
outputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw import _native
from rnw.fields import warped_noise
from rnw.model import CellClass
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.relief import generate_relief
from rnw.rng import derive_seed
from rnw.synth import grow_regions, merge_small, renumber, seed_sites
from rnw.topology import adjacency_pairs, distance_from, label_components, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

PERMILLE: Final[int] = 1000
WOBBLE_PX: Final[int] = 16
WOBBLE_PERIOD: Final[int] = 48
WOBBLE_PASSES: Final[int] = 64
WOBBLE_REPAIRS: Final[int] = 16
STRIP_ROWS: Final[int] = 1024
INTERIOR_LIMIT: Final[int] = 512
SHORE_LIMIT: Final[int] = 64
# Land keeps clear of the domain edge and of a SEAM_GAP_PX strait at the wrap. Elevation
# falls over a ramp of EDGE_RAMP_MARGINS coast margins whose start moves inland by up to
# EDGE_SHIFT_RAMPS ramps of warped noise with a period of EDGE_SHIFT_PERIOD_PERMILLE of the
# ramp, so coasts neither trace the canvas
# nor run as a straight canal along the seam. The ramp does not grow with the feature size:
# a wide ramp leaves only the canvas core for the land budget, and every seed then fills
# the same outline [V-EXEC C64].
SEAM_GAP_PX: Final[int] = 24
EDGE_RAMP_MARGINS: Final[int] = 4
EDGE_SHIFT_RAMPS: Final[int] = 2
EDGE_SHIFT_PERIOD_PERMILLE: Final[int] = 2500
MAX_STRAITS: Final[int] = 16
OUTSIDE: Final[int] = 2
LAND_KINDS: Final[frozenset[CellClass]] = frozenset(
    {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
)


@dataclass(frozen=True, slots=True, eq=False)
class NewWorld:
    """Generated cells for one domain; arrays are in domain-crop coordinates."""

    labels: NDArray[np.int32]
    classes: tuple[CellClass, ...]
    elevation: NDArray[np.int32]
    pixels: NDArray[np.int64]
    centroids: NDArray[np.int64]
    interior: NDArray[np.int64]
    mean_elevation: NDArray[np.int64]
    spread: NDArray[np.int64]
    edges: tuple[tuple[int, int], ...]


def _field(  # noqa: PLR0913 - a field is defined by its stream, shape and octaves.
    seed: int,
    stream: str,
    *,
    shape: tuple[int, int],
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[np.int32]:
    """Fractal noise for the whole crop, computed in row strips to bound memory."""
    height, width = shape
    key = derive_seed(seed, stream)
    out = np.empty(shape, dtype=np.int32)
    for row in range(0, height, STRIP_ROWS):
        rows = min(STRIP_ROWS, height - row)
        out[row : row + rows] = fractal_noise(
            key,
            0,
            row,
            width,
            rows,
            period=period,
            octaves=octaves,
            persistence_permille=persistence_permille,
        )
    return out


def _seam_gap(columns: NDArray[np.int64], seam: int) -> NDArray[np.int64]:
    """Distance in pixels to the seam between columns ``seam - 1`` and ``seam``."""
    return np.where(columns >= seam, columns - seam, seam - 1 - columns)


def _land(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings, seam: int | None
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Return land, ocean, lake masks and the shaped elevation."""
    margin = settings.coast_margin_px
    ramp = EDGE_RAMP_MARGINS * margin
    shift_px = EDGE_SHIFT_RAMPS * ramp
    shift_period = max(8, ramp * EDGE_SHIFT_PERIOD_PERMILLE // PERMILLE)
    sources = ~domain
    sources[[0, -1], :] = True
    sources[:, [0, -1]] = True
    guard = sources.copy()
    strait = np.zeros(domain.shape, dtype=bool)
    if seam is not None and 0 < seam < domain.shape[1]:
        columns = np.arange(domain.shape[1], dtype=np.int64)
        strait |= (_seam_gap(columns, seam) < SEAM_GAP_PX)[np.newaxis, :]
        guard |= strait
    relief = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
    )
    wobble = _field(
        seed,
        "new_world_edge",
        shape=domain.shape,
        period=max(8, ramp // 2),
        octaves=3,
        persistence_permille=500,
    )
    shift = warped_noise(
        derive_seed(seed, "new_world_edge_shift"),
        (int(domain.shape[0]), int(domain.shape[1])),
        step=8,
        period=shift_period,
        octaves=4,
        warp_px=shift_period // 4,
    )
    # Warped noise mostly stays within +-0.4 of NOISE_SCALE; stretch it over the shift.
    inland = shift_px * np.clip(NOISE_SCALE // 2 + shift * 5 // 4, 0, NOISE_SCALE) // NOISE_SCALE
    offset = wobble.astype(np.int64) * ramp // (3 * NOISE_SCALE) - inland
    open_shore = distance_from(open_sea(domain), margin, octagonal=True) < margin
    open_shore |= strait & ~(distance_from(sources, margin, octagonal=True) < margin)
    # A sea cut off from open water (around a protected islet) gets a strait: its shortest
    # path to open water joins the guard and the coasts are drawn again, so the strait has
    # the same ragged shores as every other coast instead of a straight canal [V-EXEC C64].
    land, shore, elevation = _coasts(domain, guard, relief, offset, ramp=ramp, settings=settings)
    for _ in range(MAX_STRAITS):
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        guard |= path
        land, shore, elevation = _coasts(
            domain, guard, relief, offset, ramp=ramp, settings=settings
        )
    parts = label_components(land.astype(np.int32))
    land &= np.bincount(parts.ravel())[parts] >= settings.min_island_px
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    ocean_parts = np.unique(parts[water & shore])
    ocean = water & np.isin(parts, ocean_parts)
    enclosed = water & ~ocean
    size = np.bincount(parts.ravel())[parts]
    small = enclosed & ((size < settings.min_lake_px) | (size > settings.max_lake_px))
    return land | small, ocean, enclosed & ~small, elevation


def _coasts(  # noqa: PLR0913 - the coast model needs the guard, both fields and the ramp.
    domain: NDArray[np.bool_],
    guard: NDArray[np.bool_],
    relief: NDArray[np.int32],
    offset: NDArray[np.int64],
    *,
    ramp: int,
    settings: NewWorldSettings,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Lower the relief over a ramp from the guard and keep the land budget.

    Returns land, shore (no land within a coast margin of the guard) and the elevation.
    """
    # The cap must exceed every reach, or the wobble would dent the interior too.
    edge = distance_from(guard, ramp - int(offset.min()) + 2, octagonal=True)
    reach = edge.astype(np.int64) + offset
    penalty = (ramp - reach) * NOISE_SCALE * 3 // ramp
    # No land in slivers of the domain too thin to hold a full ramp.
    opened = distance_from(edge >= ramp, ramp + 1, octagonal=True) <= ramp
    penalty = np.where(opened, penalty, 3 * NOISE_SCALE)
    shore = edge < settings.coast_margin_px
    elevation = (relief - np.maximum(0, penalty)).astype(np.int32)
    interior = domain & ~shore
    values = elevation[interior]
    keep = values.size * settings.land_permille // PERMILLE
    threshold = np.partition(values, values.size - keep)[values.size - keep]
    return interior & (elevation >= threshold), shore, elevation


def open_sea(domain: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Pixels outside the domain that reach the raster border, and the border itself.

    Holes in the domain (protected islands or seas inside it) are not open sea.
    """
    outside = ~domain
    parts = label_components(outside.astype(np.int32))
    border = np.zeros(domain.shape, dtype=bool)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    reaching = np.unique(parts[border & outside])
    return border | (outside & np.isin(parts, reaching))


def _path(
    start: NDArray[np.bool_], target: NDArray[np.bool_], passable: NDArray[np.bool_]
) -> NDArray[np.bool_]:
    """Shortest 4-connected path over ``passable`` pixels from ``start`` to ``target``.

    Breadth-first; ties go to the lowest-index neighbour. Empty if unreachable.
    """
    height, width = start.shape
    previous = np.full(start.size, -1, dtype=np.int32)
    seen = start.ravel() | ~passable.ravel()
    goal = target.ravel()
    frontier = np.flatnonzero(start.ravel())
    end = -1
    while frontier.size and end < 0:
        column = frontier % width
        origins = [
            frontier[frontier >= width],
            frontier[frontier < (height - 1) * width],
            frontier[column != 0],
            frontier[column != width - 1],
        ]
        source = np.concatenate(origins)
        reached = np.concatenate(
            [origins[0] - width, origins[1] + width, origins[2] - 1, origins[3] + 1]
        )
        fresh = ~seen[reached]
        source, reached = source[fresh], reached[fresh]
        order = np.lexsort((source, reached))
        source, reached = source[order], reached[order]
        first = np.concatenate([[True], reached[1:] != reached[:-1]]) if reached.size else reached
        source, reached = source[first], reached[first]
        previous[reached] = source
        seen[reached] = True
        hits = reached[goal[reached]]
        end = int(hits.min()) if hits.size else -1
        frontier = reached
    path = np.zeros(start.size, dtype=bool)
    node = end
    while node >= 0:
        path[node] = True
        node = int(previous[node])
    return path.reshape(height, width)


def stray_strait(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    *,
    shore: NDArray[np.bool_],
    open_shore: NDArray[np.bool_],
) -> NDArray[np.bool_] | None:
    """Shortest path from a sea that land cuts off from open water to open water.

    Water around a hole in the domain (a protected island or sea) counts as sea, so no sea
    zone and no protected coast may be cut off. None when every sea that touches ``shore``
    reaches ``open_shore``, or when no path through the domain exists.
    """
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    open_parts = np.unique(parts[water & open_shore])
    stray = np.setdiff1d(np.unique(parts[water & shore]), open_parts)
    if not stray.size:
        return None
    path = _path(water & (parts == stray[0]), water & np.isin(parts, open_parts), domain)
    return path if np.any(path) else None


def _weighted(
    owner: NDArray[np.int32], weights: NDArray[np.int64] | NDArray[np.int32], count: int
) -> NDArray[np.int64]:
    """Exact per-cell integer sums (float64 is exact below 2**53)."""
    sums = cast("NDArray[np.float64]", np.bincount(owner, weights=weights, minlength=count))
    return sums.astype(np.int64)


def _interior_points(
    labels: NDArray[np.int32], count: int, land: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Per cell, the first pixel (raster order) with the best interior score.

    Water cells take the pixel farthest from the cell boundary. Land cells (``land`` per
    cell) hold city models, which are square and can reach past a near shore, so their
    score is ``min(2 * d_border, d_shore)`` in octagonal distance, ties going to the
    larger ``d_border``: the point moves inland until it is twice as far from water as
    from the cell's other borders.
    """
    padded = np.pad(labels, 1, constant_values=-1)
    center = padded[1:-1, 1:-1]
    boundary = (
        (padded[:-2, 1:-1] != center)
        | (padded[2:, 1:-1] != center)
        | (padded[1:-1, :-2] != center)
        | (padded[1:-1, 2:] != center)
    )
    del padded, center
    is_land = np.concatenate([land, [False]])[labels]
    distance = distance_from(boundary, INTERIOR_LIMIT).astype(np.int64)
    border = distance_from(boundary, INTERIOR_LIMIT, octagonal=True).astype(np.int64)
    shore = distance_from(~is_land, SHORE_LIMIT, octagonal=True).astype(np.int64)
    score = np.where(is_land, np.minimum(2 * border, shore), distance)
    tie = np.where(is_land, border, 0)
    del distance, border, shore, boundary, is_land
    return _native.best_points(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(score, dtype=np.int64),
        np.ascontiguousarray(tie, dtype=np.int64),
        count,
    )


def _absorb_orphans(
    labels: NDArray[np.int32], orphan: NDArray[np.bool_], kind: NDArray[np.int64]
) -> NDArray[np.bool_]:
    """Give orphan pixels the label of a non-orphan 4-neighbour of the same class.

    Works inwards from the edges of orphan patches, N, W, E, S first, touching only
    orphan pixels; returns the pixels that found no such neighbour.
    """
    height, width = labels.shape
    flat = labels.reshape(-1)
    is_orphan = orphan.reshape(-1).copy()
    pending = np.flatnonzero(is_orphan)
    for _ in range(WOBBLE_PASSES):
        if not pending.size:
            break
        for offset in (-width, -1, 1, width):
            column = pending % width
            if offset == -width:
                inside = pending >= width
            elif offset == width:
                inside = pending < (height - 1) * width
            elif offset == -1:
                inside = column != 0
            else:
                inside = column != width - 1
            here = pending[inside & is_orphan[pending]]
            there = here + offset
            ok = (
                ~is_orphan[there]
                & (flat[there] >= 0)
                & (kind[np.maximum(flat[there], 0)] == kind[np.maximum(flat[here], 0)])
            )
            flat[here[ok]] = flat[there[ok]]
            is_orphan[here[ok]] = False
        pending = pending[is_orphan[pending]]
    return is_orphan.reshape(height, width)


def wobble_borders(
    labels: NDArray[np.int32], kinds: list[CellClass], seed: int
) -> NDArray[np.int32]:
    """Bend straight cell borders into curves; classes, coasts and cell count are kept.

    Each pixel takes the label found a smooth noise displacement away when that pixel
    has the same class. Pieces cut off from their cell's largest part are absorbed by a
    neighbouring cell of the same class. A cell that would vanish or split gets its
    original pixels back, and so do the pixels it took, until every cell is one piece;
    one bad cell no longer undoes the wobble of the whole world (C71).
    """
    shape = (int(labels.shape[0]), int(labels.shape[1]))
    kind = np.array([list(CellClass).index(value) for value in kinds], dtype=np.int64)
    offsets = [
        warped_noise(
            derive_seed(seed, stream), shape, step=4, period=WOBBLE_PERIOD, octaves=3, warp_px=0
        )
        * WOBBLE_PX
        // NOISE_SCALE
        for stream in ("nw_wobble_rows", "nw_wobble_columns")
    ]
    rows = np.clip(np.arange(shape[0])[:, np.newaxis] + offsets[0], 0, shape[0] - 1)
    columns = np.clip(np.arange(shape[1])[np.newaxis, :] + offsets[1], 0, shape[1] - 1)
    source = labels[rows, columns]
    del rows, columns, offsets
    valid = (labels >= 0) & (source >= 0)
    same = valid & (kind[np.maximum(source, 0)] == kind[np.maximum(labels, 0)])
    moved = np.where(same, source, labels).astype(np.int32)
    del source, same, valid
    counts = np.bincount(moved[moved >= 0], minlength=len(kinds))
    vanished = np.flatnonzero(counts == 0)
    if vanished.size:
        restore = np.isin(labels, vanished)
        moved[restore] = labels[restore]
    parts = label_components(moved)
    owner = np.full(int(parts.max()) + 1, -1, dtype=np.int64)
    owner[parts.ravel()] = moved.ravel()
    sizes = np.bincount(parts.ravel())
    best = np.full(len(kinds), -1, dtype=np.int64)
    order = np.lexsort((np.arange(sizes.size), -sizes))
    for part in order.tolist():
        cell = int(owner[part])
        if cell >= 0 and best[cell] < 0:
            best[cell] = part
    if np.any(best < 0):
        return labels
    keep = np.zeros(sizes.size, dtype=bool)
    keep[best] = True
    orphan = (moved >= 0) & ~keep[parts]
    del parts
    left = _absorb_orphans(moved, orphan, kind)
    moved[left] = labels[left]
    for _ in range(WOBBLE_REPAIRS):
        check = label_components(moved)
        pieces = np.zeros(int(check.max()) + 1, dtype=np.int64) - 1
        pieces[check.ravel()] = moved.ravel()
        per_cell = np.bincount(pieces[pieces >= 0], minlength=len(kinds))
        bad = np.flatnonzero(per_cell != 1)
        if not bad.size:
            return moved
        revert = np.isin(labels, bad) | np.isin(moved, bad)
        moved[revert] = labels[revert]
    return labels


def generate_new_world(
    domain: NDArray[np.bool_], *, seed: int, settings: NewWorldSettings, seam: int | None = None
) -> NewWorld:
    """Fill ``domain`` with generated land, sea and lake cells.

    ``seam`` is the crop column where the world map wraps (cells left of it continue at
    the right map edge); a strait keeps land away from it.
    """
    land, ocean, lakes, _ = _land(domain, seed, settings, seam)
    land_cells = merge_small(
        grow_regions(
            land, seed_sites(derive_seed(seed, "nw_land_sites"), land, settings.location_px)
        ),
        settings.min_cell_px,
    )
    sea_cells = merge_small(
        grow_regions(
            ocean, seed_sites(derive_seed(seed, "nw_sea_sites"), ocean, settings.sea_zone_px)
        ),
        settings.min_sea_cell_px,
    )
    lake_parts = label_components(np.where(lakes, 1, 0).astype(np.int32))
    lake_cells = np.where(lakes, lake_parts, -1).astype(np.int32)
    labels = np.full(domain.shape, -1, dtype=np.int32)
    kinds: list[CellClass] = []
    for kind, part in (
        (CellClass.LAND, land_cells),
        (CellClass.SEA, sea_cells),
        (CellClass.LAKE, lake_cells),
    ):
        numbered = renumber(part)
        present = int(numbered.max()) + 1 if np.any(numbered >= 0) else 0
        labels[numbered >= 0] = numbered[numbered >= 0] + len(kinds)
        kinds.extend([kind] * present)
    labels = wobble_borders(labels, kinds, seed)
    relief = generate_relief(land, seed=seed)
    count = len(kinds)
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    owner = flat[inside]
    pixels = np.bincount(owner, minlength=count).astype(np.int64)
    mean_relief = _weighted(owner, relief.ravel()[inside], count) // np.maximum(1, pixels)
    land_ids = [index for index, kind in enumerate(kinds) if kind is CellClass.LAND]
    wasteland = len(land_ids) * settings.wasteland_permille // PERMILLE
    ranked = sorted(land_ids, key=lambda index: (-int(mean_relief[index]), index))
    for index in ranked[:wasteland]:
        kinds[index] = CellClass.WASTELAND
    return derive_world(labels, tuple(kinds), relief)


def derive_world(
    labels: NDArray[np.int32], kinds: tuple[CellClass, ...], elevation: NDArray[np.int32]
) -> NewWorld:
    """Compute sizes, centres, interior points and contacts for a labelled world."""
    count = len(kinds)
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    owner = flat[inside]
    width = labels.shape[1]
    pixels = np.bincount(owner, minlength=count).astype(np.int64)
    rows = _weighted(owner, inside // width, count)
    columns = _weighted(owner, inside % width, count)
    values = elevation.ravel()[inside].astype(np.int64)
    mean_elevation = _weighted(owner, values, count) // np.maximum(1, pixels)
    square = _weighted(owner, values * values, count) // np.maximum(1, pixels)
    variance = np.maximum(0, square - mean_elevation * mean_elevation)
    spread = np.floor(np.sqrt(variance.astype(np.float64))).astype(np.int64)
    centroids = np.stack([rows // np.maximum(1, pixels), columns // np.maximum(1, pixels)], axis=1)
    edges = tuple(
        (first, second)
        for first, second in unpack_pairs(adjacency_pairs(labels))
        if first >= 0 and second >= 0
    )
    return NewWorld(
        labels=labels,
        classes=kinds,
        elevation=elevation,
        pixels=pixels,
        centroids=centroids,
        interior=_interior_points(
            labels, count, np.array([kind in LAND_KINDS for kind in kinds], dtype=bool)
        ),
        mean_elevation=mean_elevation,
        spread=spread,
        edges=edges,
    )


def unported_cells(world: NewWorld) -> list[int]:
    """Land cells that reach no coast without crossing wasteland, lakes or the sea.

    EU5 logs a location as "isolated from all ports by impassable terrain" when walling
    wasteland leaves it no way to a port [V-GAME 1.4.2, C95]; every coastal land cell has
    a port, so the cells to find are the land components that touch no sea cell.
    """
    parent = list(range(len(world.classes)))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    coastal: set[int] = set()
    for first, second in world.edges:
        kinds = (world.classes[first], world.classes[second])
        if kinds == (CellClass.LAND, CellClass.LAND):
            parent[find(first)] = find(second)
        elif kinds == (CellClass.LAND, CellClass.SEA):
            coastal.add(find(first))
        elif kinds == (CellClass.SEA, CellClass.LAND):
            coastal.add(find(second))
    reached = {find(item) for item in coastal}
    return [
        index
        for index, kind in enumerate(world.classes)
        if kind is CellClass.LAND and find(index) not in reached
    ]


def seal_pockets(world: NewWorld) -> NewWorld:
    """``world`` with its unported land turned into wasteland (mountains no port reaches)."""
    cells = unported_cells(world)
    if not cells:
        return world
    kinds = list(world.classes)
    for index in cells:
        kinds[index] = CellClass.WASTELAND
    return replace(world, classes=tuple(kinds))


def split_at_column(world: NewWorld, column: int) -> NewWorld:
    """Split every cell that crosses ``column`` so no cell spans it.

    Used for a map seam: each side's 4-connected parts become separate cells (the
    largest part keeps the original index), so every cell stays connected.
    """
    labels = world.labels.copy()
    kinds = list(world.classes)
    if not 0 < column < labels.shape[1]:
        return world
    left = labels[:, column - 1]
    right = labels[:, column]
    crossing = np.unique(left[(left == right) & (left >= 0)])
    for cell in cast("list[int]", crossing.tolist()):
        rows, columns = np.nonzero(labels == cell)
        top, bottom = int(rows.min()), int(rows.max()) + 1
        start, end = int(columns.min()), int(columns.max()) + 1
        window = labels[top:bottom, start:end]
        mine = window == cell
        side = np.zeros(mine.shape, dtype=np.int32)
        side[:, max(0, column - start) :] = 1
        parts = label_components(np.where(mine, side, -1).astype(np.int32))
        ids = np.unique(parts[mine])
        sizes = [int(np.count_nonzero(parts[mine] == part)) for part in ids.tolist()]
        keep = ids[int(np.argmax(sizes))]
        for part in ids.tolist():
            if part == keep:
                continue
            window[mine & (parts == part)] = len(kinds)
            kinds.append(world.classes[cell])
    return derive_world(labels, tuple(kinds), world.elevation)
