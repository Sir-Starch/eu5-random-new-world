"""Generate a complete New World inside an arbitrary domain mask (T3, game-independent).

The domain is the set of pixels that may be replaced. A ring of ocean is kept along its
border so generated seas meet the surrounding (protected) ocean. Everything is integer
arithmetic driven by named SplitMix64 streams, so equal inputs give equal outputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw.model import CellClass
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.synth import grow_regions, merge_small, renumber, seed_sites
from rnw.topology import adjacency_pairs, distance_from, label_components, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

PERMILLE: Final[int] = 1000
STRIP_ROWS: Final[int] = 1024
INTERIOR_LIMIT: Final[int] = 512
OUTSIDE: Final[int] = 2


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


def _land(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Return land, ocean, lake masks and the shaped elevation."""
    margin = settings.coast_margin_px
    ramp = max(4 * margin, settings.feature_px // 3)
    sources = ~domain
    sources[[0, -1], :] = True
    sources[:, [0, -1]] = True
    edge = distance_from(sources, ramp + 1, octagonal=True)
    elevation = _field(
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
    reach = edge.astype(np.int64) + wobble.astype(np.int64) * ramp // (3 * NOISE_SCALE)
    penalty = (ramp - reach) * NOISE_SCALE * 3 // ramp
    elevation = (elevation - np.maximum(0, penalty)).astype(np.int32)
    interior = domain & (edge >= margin)
    values = elevation[interior]
    keep = values.size * settings.land_permille // PERMILLE
    threshold = np.partition(values, values.size - keep)[values.size - keep]
    land = interior & (elevation >= threshold)
    parts = label_components(land.astype(np.int32))
    land &= np.bincount(parts.ravel())[parts] >= settings.min_island_px
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    ocean_parts = np.unique(parts[water & (edge < margin)])
    ocean = water & np.isin(parts, ocean_parts)
    enclosed = water & ~ocean
    size = np.bincount(parts.ravel())[parts]
    small = enclosed & ((size < settings.min_lake_px) | (size > settings.max_lake_px))
    return land | small, ocean, enclosed & ~small, elevation


def _weighted(
    owner: NDArray[np.int32], weights: NDArray[np.int64] | NDArray[np.int32], count: int
) -> NDArray[np.int64]:
    """Exact per-cell integer sums (float64 is exact below 2**53)."""
    sums = cast("NDArray[np.float64]", np.bincount(owner, weights=weights, minlength=count))
    return sums.astype(np.int64)


def _interior_points(labels: NDArray[np.int32], count: int) -> NDArray[np.int64]:
    """Per cell, the first pixel (raster order) farthest from the cell's boundary."""
    height, width = labels.shape
    padded = np.pad(labels, 1, constant_values=-1)
    center = padded[1:-1, 1:-1]
    boundary = (
        (padded[:-2, 1:-1] != center)
        | (padded[2:, 1:-1] != center)
        | (padded[1:-1, :-2] != center)
        | (padded[1:-1, 2:] != center)
    )
    distance = distance_from(boundary, INTERIOR_LIMIT).ravel()
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    order = inside[np.lexsort((inside, -distance[inside].astype(np.int64), flat[inside]))]
    owners = flat[order]
    first = np.flatnonzero(np.concatenate([[True], owners[1:] != owners[:-1]]))
    points = np.zeros((count, 2), dtype=np.int64)
    points[owners[first]] = np.stack([order[first] // width, order[first] % width], axis=1)
    _ = height
    return points


def generate_new_world(
    domain: NDArray[np.bool_], *, seed: int, settings: NewWorldSettings
) -> NewWorld:
    """Fill ``domain`` with generated land, sea and lake cells."""
    land, ocean, lakes, elevation = _land(domain, seed, settings)
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
    count = len(kinds)
    flat = labels.ravel()
    inside = np.flatnonzero(flat >= 0)
    owner = flat[inside]
    pixels = np.bincount(owner, minlength=count).astype(np.int64)
    mean_elevation = _weighted(owner, elevation.ravel()[inside], count) // np.maximum(1, pixels)
    land_ids = [index for index, kind in enumerate(kinds) if kind is CellClass.LAND]
    wasteland = len(land_ids) * settings.wasteland_permille // PERMILLE
    if wasteland:
        ridges = NOISE_SCALE - np.abs(
            _field(
                seed,
                "new_world_ridges",
                shape=domain.shape,
                period=max(8, settings.feature_px // 3),
                octaves=4,
                persistence_permille=550,
            )
        ).astype(np.int64)
        ridge = np.bincount(owner, weights=ridges.ravel()[inside], minlength=count)
        mean_ridge = (ridge // np.maximum(1, pixels)).astype(np.int64)
        score = mean_ridge * 2 + mean_elevation
        ranked = sorted(land_ids, key=lambda index: (-int(score[index]), index))
        for index in ranked[:wasteland]:
            kinds[index] = CellClass.WASTELAND
    return derive_world(labels, tuple(kinds), elevation)


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
    mean_elevation = _weighted(owner, elevation.ravel()[inside], count) // np.maximum(1, pixels)
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
        interior=_interior_points(labels, count),
        mean_elevation=mean_elevation,
        edges=edges,
    )


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
