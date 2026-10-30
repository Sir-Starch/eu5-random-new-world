"""Generate a complete New World inside an arbitrary domain mask (T3, game-independent).

The domain is the set of pixels that may be replaced. Ocean margins protect the surrounding
Old World and the longitudinal canvas borders; land may reach the polar map edges. The map wrap is
inside this continuous crop and imposes no coast or land budget. Land carries a
continuous relief field (``relief.py``); the highest cells become wastelands. Everything
is integer arithmetic driven by named SplitMix64 streams, so equal inputs give equal
outputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native, wall
from rnw.fields import warped_noise
from rnw.landmask import LandMaskError
from rnw.model import CellClass
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.parallel import Stages, stage_workers
from rnw.progress import checkpoint
from rnw.relief import generate_relief
from rnw.rng import SplitMix64, derive_seed
from rnw.sea_corridors import designed_corridors
from rnw.straits import pinch
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
FIELD_ORIGIN_LIMIT: Final[int] = 1 << 24
INTERIOR_LIMIT: Final[int] = 512
SHORE_LIMIT: Final[int] = 64
# Land keeps clear of the domain edge. Elevation
# falls over a ramp of EDGE_RAMP_MARGINS coast margins whose start moves inland by up to
# EDGE_SHIFT_RAMPS ramps of warped noise with a period of EDGE_SHIFT_PERIOD_PERMILLE of the
# ramp, so coasts neither trace the canvas
# nor run as a straight canal along a strait axis. The ramp does not grow with the feature size:
# a wide ramp leaves only the canvas core for the land budget, and every seed then fills
# the same outline [V-EXEC C64].
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
    """Fractal noise on a seed-positioned lattice, in memory-bounded row strips.

    A fixed lattice gives the same pixels high variance in every world: its nodes
    vary much more than the spaces between them. In a narrow part of the canvas
    (such as the old Alaska) that favours the same island outline. Draw the phase
    across many periods so no position in the canvas owns a lattice node, and
    changing feature size does not keep sampling the same few nodes. The origin
    belongs to the whole field, including both sides of the map seam, not a strip
    or a connected part of the domain. Coordinates stay well inside integer limits.
    """
    height, width = shape
    key = derive_seed(seed, stream)
    origin = SplitMix64(derive_seed(seed, stream, "origin"))
    x0, y0 = origin.below(FIELD_ORIGIN_LIMIT), origin.below(FIELD_ORIGIN_LIMIT)
    out = np.empty(shape, dtype=np.int32)
    for row in range(0, height, STRIP_ROWS):
        rows = min(STRIP_ROWS, height - row)
        out[row : row + rows] = fractal_noise(
            key,
            x0,
            y0 + row,
            width,
            rows,
            period=period,
            octaves=octaves,
            persistence_permille=persistence_permille,
        )
    return out


def _edge_offset(
    seed: int,
    wobble: NDArray[np.int32],
    *,
    ramp: int,
    shift_px: int,
    shift_period: int,
) -> NDArray[np.int32]:
    """Where the coast ramp starts, per pixel: wobble minus the inland shift.

    The shift noise is built in strips of ``STRIP_ROWS`` rows (a multiple of the noise
    step); the offset is a few ramps wide, so a 32-bit raster holds it.
    """
    height, width = (int(size) for size in wobble.shape)
    key = derive_seed(seed, "new_world_edge_shift")
    offset = np.empty((height, width), dtype=np.int32)
    for first in range(0, height, STRIP_ROWS):
        rows = min(STRIP_ROWS, height - first)
        shift = warped_noise(
            key,
            (rows, width),
            step=8,
            period=shift_period,
            octaves=4,
            warp_px=shift_period // 4,
            row0=first,
        )
        # Warped noise mostly stays within +-0.4 of NOISE_SCALE; stretch it over the shift.
        inland = (
            shift_px * np.clip(NOISE_SCALE // 2 + shift * 5 // 4, 0, NOISE_SCALE) // NOISE_SCALE
        )
        offset[first : first + rows] = (
            wobble[first : first + rows].astype(np.int64) * ramp // (3 * NOISE_SCALE) - inland
        )
    return offset


PERCENT: Final[int] = 100
# Of the land a drawing asks for inside the area, the least that must stay after the margin.
MIN_KEPT_PERCENT: Final[int] = 50


def land_stage(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Return land, ocean, lake masks and the shaped elevation."""
    if settings.landform:
        return _wall_land(domain, seed, settings)
    relief = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
    )
    return _natural_land(domain, seed, settings, relief)


def _natural_land(
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    relief: NDArray[np.int32],
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Construct natural coasts from a density field, preserving the requested land budget."""
    margin = settings.coast_margin_px
    ramp = EDGE_RAMP_MARGINS * margin
    shift_px = EDGE_SHIFT_RAMPS * ramp
    shift_period = max(8, ramp * EDGE_SHIFT_PERIOD_PERMILLE // PERMILLE)
    guard = ~domain
    guard[:, [0, -1]] = True
    wobble = _field(
        seed,
        "new_world_edge",
        shape=domain.shape,
        period=max(8, ramp // 2),
        octaves=3,
        persistence_permille=500,
    )
    offset = _edge_offset(seed, wobble, ramp=ramp, shift_px=shift_px, shift_period=shift_period)
    del wobble
    open_shore = distance_from(open_sea(domain), margin, octagonal=True) < margin
    # A sea cut off from open water (around a protected islet) gets a strait: its shortest
    # path to open water joins the guard and the coasts are drawn again, so the strait has
    # the same ragged shores as every other coast instead of a straight canal [V-EXEC C64].
    land, shore, elevation = _coasts(domain, guard, relief, offset, ramp=ramp, settings=settings)
    for _ in range(MAX_STRAITS):
        checkpoint()
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        guard |= path
        land, shore, elevation = _coasts(
            domain, guard, relief, offset, ramp=ramp, settings=settings
        )
    del relief, offset, guard, open_shore
    land &= _large_parts(land, settings.min_island_px)
    return (*_classify(domain, land, shore, settings), elevation)


def _wall_land(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Build the barrier and seed both continental placement and local coasts beside it.

    Splitting the canvas leaves broad northern and southern pockets. Local coast
    noise alone scatters land through each pocket, repeating that composition even
    on different seeds. A longer wavelength lets whole regions become ocean or
    continent; the original field supplies bays, peninsulas and islands. Both
    scales follow feature size, with one sea level for all the side land.
    """
    centre, half = wall.geometry(domain, settings)
    sides = domain.copy()
    gap = half + max(2 * settings.coast_margin_px, settings.sea_zone_px)
    sides[:, max(0, centre - gap) : centre + gap + 1] = False
    relief = _field(
        seed,
        "wall_continents",
        shape=domain.shape,
        period=4 * settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
    )
    detail = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
    )
    relief *= 2
    relief += detail
    relief //= 3
    del detail
    land, _, _, elevation = _natural_land(sides, seed, settings, relief)
    land |= wall.coast(domain, seed, settings)
    return (*_classify(domain, land, _off_limits(domain, settings), settings), elevation)


def _classify(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    settings: NewWorldSettings,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
    """Split the water of ``domain`` into ocean and lakes; small lakes fill with land.

    Returns land, ocean and lake masks. Water that reaches the shore is ocean; water enclosed
    by land is a lake unless it is smaller than ``min_lake_px`` or larger than ``max_lake_px``.
    """
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32, copy=False)
    parts = label_components(coded)
    del coded
    water = domain & ~land
    sizes = np.bincount(parts.ravel())
    ocean_part = np.zeros(sizes.size, dtype=bool)
    ocean_part[np.unique(parts[water & shore])] = True
    ocean = water & ocean_part[parts]
    enclosed = water & ~ocean
    outside_range = (sizes < settings.min_lake_px) | (sizes > settings.max_lake_px)
    small = enclosed & outside_range[parts]
    return land | small, ocean, enclosed & ~small


def _land_from_mask(
    domain: NDArray[np.bool_],
    drawn: NDArray[np.bool_],
    settings: NewWorldSettings,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
    """Land, ocean and lakes of a land that is drawn, not generated (``rnw.landmask``).

    The land keeps off the canvas's edge, as generated land does (the coast margin from what
    lies outside the domain and the border); specks under
    ``min_island_px`` go. A drawing that loses most of its land to that is refused, since it
    asks for land where the New World cannot be.
    """
    margin = settings.coast_margin_px
    guard = ~domain
    guard[:, [0, -1]] = True
    shore = distance_from(guard, margin, octagonal=True) < margin
    del guard
    wanted = drawn & domain
    land = wanted & ~shore
    asked, kept = int(np.count_nonzero(wanted)), int(np.count_nonzero(land))
    if not asked or kept * PERCENT < asked * MIN_KEPT_PERCENT:
        share = kept * PERCENT // max(1, asked)
        message = (
            f"Most of the land drawn lies where the New World cannot be: {share} % of it is "
            f"inside the area and away from its edge ({margin} pixels of coast margin). "
            "Draw the continents well inside the picture and inside the area"
        )
        raise LandMaskError(message)
    land &= _large_parts(land, settings.min_island_px)
    open_shore = distance_from(open_sea(domain), margin, octagonal=True) < margin
    for _ in range(MAX_STRAITS):
        checkpoint()
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        # A sea that the drawing cuts off from open water gets a strait, a coast margin wide,
        # as generated land does (C64): no sea zone may be left without a way to the sea.
        land &= distance_from(path, margin, octagonal=True) >= margin
        land &= _large_parts(land, settings.min_island_px)
    if not land.any():
        message = (
            f"No land is left once parts under {settings.min_island_px} pixels are taken out: "
            "draw larger continents"
        )
        raise LandMaskError(message)
    return _classify(domain, land, shore, settings)


def _off_limits(domain: NDArray[np.bool_], settings: NewWorldSettings) -> NDArray[np.bool_]:
    """Pixels where no land may be added after the coasts are drawn: a coast margin from what
    lies outside the domain and from the longitudinal borders."""
    guard = ~domain
    guard[:, [0, -1]] = True
    return distance_from(guard, settings.coast_margin_px, octagonal=True) < settings.coast_margin_px


def _large_parts(mask: NDArray[np.bool_], minimum: int) -> NDArray[np.bool_]:
    """Pixels of ``mask`` that sit in a 4-connected part of the labelling of at least ``minimum``.

    The labelling is of the mask as a 0/1 raster, so the parts are land and water alike;
    callers intersect the result with the side they mean.
    """
    parts = label_components(mask.astype(np.int32))
    return (np.bincount(parts.ravel()) >= minimum)[parts]


def _coasts(  # noqa: PLR0913 - the coast model needs the guard, both fields and the ramp.
    domain: NDArray[np.bool_],
    guard: NDArray[np.bool_],
    relief: NDArray[np.int32],
    offset: NDArray[np.int32],
    *,
    ramp: int,
    settings: NewWorldSettings,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Lower the relief over a ramp from the guard and keep the land budget.

    Returns land, shore (no land within a coast margin of the guard) and the elevation.
    The per-pixel arithmetic runs in strips; only the two distance fields are whole-raster.
    """
    # The cap must exceed every reach, or the wobble would dent the interior too.
    edge = distance_from(guard, ramp - int(offset.min()) + 2, octagonal=True)
    # No land in slivers of the domain too thin to hold a full ramp.
    opened = distance_from(edge >= ramp, ramp + 1, octagonal=True) <= ramp
    shore = edge < settings.coast_margin_px
    height, width = (int(size) for size in edge.shape)
    elevation = np.empty((height, width), dtype=np.int32)
    for first in range(0, height, STRIP_ROWS):
        rows = slice(first, min(height, first + STRIP_ROWS))
        reach = edge[rows].astype(np.int64) + offset[rows]
        penalty = (ramp - reach) * NOISE_SCALE * 3 // ramp
        penalty = np.where(opened[rows], penalty, 3 * NOISE_SCALE)
        elevation[rows] = (relief[rows] - np.maximum(0, penalty)).astype(np.int32)
    del edge, opened
    interior = domain & ~shore
    threshold = _threshold(elevation, interior, settings.land_permille)
    return interior & (elevation >= threshold), shore, elevation


def _threshold(values: NDArray[np.int32], mask: NDArray[np.bool_], permille: int) -> int:
    """The value that ``permille`` of the masked values (rounded down) reach or pass.

    Equal to ``np.partition(values[mask], n - keep)[n - keep]`` with ``keep = n * permille
    // 1000``, found by counting the values instead of copying and partitioning them.
    """
    height = int(values.shape[0])
    lows: list[int] = []
    highs: list[int] = []
    for first in range(0, height, STRIP_ROWS):
        strip = values[first : first + STRIP_ROWS][mask[first : first + STRIP_ROWS]]
        if strip.size:
            lows.append(int(strip.min()))
            highs.append(int(strip.max()))
    if not lows:
        message = "no pixel can hold land"
        raise ValueError(message)
    low, high = min(lows), max(highs)
    counts = np.zeros(high - low + 1, dtype=np.int64)
    for first in range(0, height, STRIP_ROWS):
        strip = values[first : first + STRIP_ROWS][mask[first : first + STRIP_ROWS]]
        counts += np.bincount(strip.astype(np.int64) - low, minlength=counts.size)
    total = int(counts.sum())
    keep = total * permille // PERMILLE
    if keep < 1:
        message = f"a land share of {permille} permille keeps no pixel of {total}"
        raise ValueError(message)
    return low + int(np.searchsorted(np.cumsum(counts), total - keep, side="right"))


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


def _interior_points(
    labels: NDArray[np.int32], count: int, land: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Per cell, the first pixel (raster order) with the best interior score.

    Water cells take the pixel farthest from the cell boundary. Land cells (``land`` per
    cell) hold city models, which are square and can reach past a near shore, so their
    score is ``min(2 * d_border, d_shore)`` in octagonal distance, ties going to the
    larger ``d_border``: the point moves inland until it is twice as far from water as
    from the cell's other borders. The kernel is Rust (ADR 0005), its NumPy specification
    is ``tests/reference/points.py``.
    """
    del count
    return _native.interior_points(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(land, dtype=np.bool_),
        INTERIOR_LIMIT,
        SHORE_LIMIT,
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
    labels: NDArray[np.int32], kinds: list[CellClass], seed: int, *, fixed_sea: bool = False
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
    if fixed_sea:
        sea_kind = list(CellClass).index(CellClass.SEA)
        for start in range(0, shape[0], STRIP_ROWS):
            rows = slice(start, min(shape[0], start + STRIP_ROWS))
            same[rows] &= kind[np.maximum(labels[rows], 0)] != sea_kind
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


def _cells(mask: NDArray[np.bool_], *, key: int, spacing: int, smallest: int) -> NDArray[np.int32]:
    """Cells of about ``spacing`` pixels grown inside ``mask``, none under ``smallest`` pixels."""
    return merge_small(grow_regions(mask, seed_sites(key, mask, spacing)), smallest)


def _sea_cells(  # noqa: PLR0913 - partition inputs and the physical replacement domain.
    ocean: NDArray[np.bool_],
    *,
    key: int,
    spacing: int,
    smallest: int,
    bands: NDArray[np.bool_] | None,
    domain: NDArray[np.bool_] | None = None,
) -> NDArray[np.int32]:
    """Partition actual ocean routes separately from ordinary water."""

    def sea_part(mask: NDArray[np.bool_]) -> NDArray[np.int32]:
        sites = seed_sites(key, mask, spacing)
        nearest = _native.sea_voronoi(np.ascontiguousarray(mask), sites)
        # A coast or a current band may cut a Voronoi cell into separate pieces.
        # They are distinct cells before small connected pieces are merged.
        parts = label_components(nearest)
        return merge_small(np.where(mask, parts, -1).astype(np.int32), smallest)

    if bands is None:
        return sea_part(ocean)
    if bands.shape != ocean.shape:
        message = "Current bands do not fit the world"
        raise ValueError(message)
    result = np.full(ocean.shape, -1, dtype=np.int32)
    corridors = designed_corridors(ocean, bands, spacing, domain=domain)
    offset = 0
    for category in ("crossing", "open"):
        mask = np.empty(ocean.shape, dtype=np.bool_)
        present = False
        for start in range(0, len(ocean), STRIP_ROWS):
            rows = slice(start, min(len(ocean), start + STRIP_ROWS))
            if category == "crossing":
                mask[rows] = corridors[rows]
            else:
                mask[rows] = ocean[rows] & ~corridors[rows]
            present = present or bool(np.any(mask[rows]))
        if not present:
            continue
        part = renumber(sea_part(mask))
        maximum = -1
        for start in range(0, len(ocean), STRIP_ROWS):
            rows = slice(start, min(len(ocean), start + STRIP_ROWS))
            result[rows][mask[rows]] = part[rows][mask[rows]] + offset
            maximum = max(maximum, int(part[rows].max()))
        offset += maximum + 1
    return result


def generate_new_world(
    domain: NDArray[np.bool_],
    *,
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None = None,
    sea_bands: NDArray[np.bool_] | None = None,
) -> NewWorld:
    """Fill ``domain`` with generated land, sea and lake cells.

    With ``drawn`` (a land mask fitted to the domain, ``rnw.landmask``) the land is the
    drawing's and the generator makes the rest on it.

    Cells belong to this continuous canvas. Projecting it across the game's raster
    boundary must retain each cell's identity on both sides, just as vanilla does.

    The land cells, the sea cells and the relief depend only on the masks, so they are
    built beside each other when the machine has the cores and the memory for it.
    """
    if drawn is None:
        land, ocean, lakes, _ = land_stage(domain, seed, settings)
    else:
        if settings.landform:
            message = "The Wall cannot be combined with a drawn land mask"
            raise LandMaskError(message)
        land, ocean, lakes = _land_from_mask(domain, drawn, settings)
    land, ocean, _ = pinch(land, ocean, _off_limits(domain, settings))
    with Stages(stage_workers()) as stages:
        land_job = stages.submit(
            "land cells",
            partial(
                _cells,
                land,
                key=derive_seed(seed, "nw_land_sites"),
                spacing=settings.location_px,
                smallest=settings.min_cell_px,
            ),
        )
        sea_job = stages.submit(
            "sea cells",
            partial(
                _sea_cells,
                ocean,
                key=derive_seed(seed, "nw_sea_sites"),
                spacing=settings.sea_zone_px,
                smallest=settings.min_sea_cell_px,
                bands=sea_bands,
                domain=domain,
            ),
        )
        relief_job = stages.submit("relief", partial(generate_relief, land, seed=seed))
        lake_cells = np.where(lakes, label_components(np.where(lakes, 1, 0).astype(np.int32)), -1)
        land_cells, sea_cells, relief = land_job.result(), sea_job.result(), relief_job.result()
    if settings.landform:
        wall.add_relief(relief, land, domain, seed, settings)
    del ocean, lakes, land
    labels = np.full(domain.shape, -1, dtype=np.int32)
    kinds: list[CellClass] = []
    for kind, part in (
        (CellClass.LAND, land_cells),
        (CellClass.SEA, sea_cells),
        (CellClass.LAKE, lake_cells.astype(np.int32)),
    ):
        numbered = renumber(part)
        present = int(numbered.max()) + 1 if np.any(numbered >= 0) else 0
        labels[numbered >= 0] = numbered[numbered >= 0] + len(kinds)
        kinds.extend([kind] * present)
        del numbered
    del land_cells, sea_cells, lake_cells
    labels = wobble_borders(labels, kinds, seed, fixed_sea=sea_bands is not None)
    count = len(kinds)
    pixels, _, _, total, _ = _cell_sums(labels, relief, count)
    mean_relief = total // np.maximum(1, pixels)
    land_ids = [index for index, kind in enumerate(kinds) if kind is CellClass.LAND]
    wasteland = len(land_ids) * settings.wasteland_permille // PERMILLE
    ranked = sorted(land_ids, key=lambda index: (-int(mean_relief[index]), index))
    for index in ranked[:wasteland]:
        kinds[index] = CellClass.WASTELAND
    if settings.landform:
        # Polar end locations are impassable, while the shelves remain playable.
        polar = np.unique(labels[[0, -1], :])
        for index in polar.tolist():
            if index >= 0 and kinds[index] is CellClass.LAND:
                kinds[index] = CellClass.WASTELAND
        centre, _ = wall.geometry(domain, settings)
        if (
            not settings.wall_allow_gaps
            and not np.isin(
                labels[:, centre], [i for i, kind in enumerate(kinds) if kind in LAND_KINDS]
            ).all()
        ):
            message = "The Wall lost its continuous land barrier during cell construction"
            raise ValueError(message)
    return derive_world(labels, tuple(kinds), relief)


def _cell_sums(
    labels: NDArray[np.int32], elevation: NDArray[np.int32], count: int
) -> tuple[NDArray[np.int64], ...]:
    """Pixels, row sum, column sum, elevation sum and elevation square sum per cell.

    The sums are exact integers in float64 (below 2**53), added strip by strip, so the
    result does not depend on the strip height.
    """
    rows, width = (int(size) for size in labels.shape)
    totals = np.zeros((5, count), dtype=np.float64)
    columns_of = np.arange(width, dtype=np.int64)
    for first in range(0, rows, STRIP_ROWS):
        last = min(rows, first + STRIP_ROWS)
        strip = labels[first:last]
        inside = strip >= 0
        owner = strip[inside]
        row_index = np.broadcast_to(
            np.arange(first, last, dtype=np.int64)[:, np.newaxis], strip.shape
        )
        column_index = np.broadcast_to(columns_of[np.newaxis, :], strip.shape)
        values = elevation[first:last][inside].astype(np.int64)
        totals[0] += np.bincount(owner, minlength=count)
        for slot, weights in enumerate(
            (row_index[inside], column_index[inside], values, values * values), start=1
        ):
            totals[slot] += np.bincount(owner, weights=weights, minlength=count)
    return tuple(total.astype(np.int64) for total in totals)


def derive_world(
    labels: NDArray[np.int32], kinds: tuple[CellClass, ...], elevation: NDArray[np.int32]
) -> NewWorld:
    """Compute sizes, centres, interior points and contacts for a labelled world."""
    count = len(kinds)
    pixels, rows, columns, total, square_total = _cell_sums(labels, elevation, count)
    mean_elevation = total // np.maximum(1, pixels)
    square = square_total // np.maximum(1, pixels)
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
