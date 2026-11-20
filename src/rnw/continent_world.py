"""Compose compact regional geography for one pass of world-scale generation."""

# NumPy stubs type boolean indexing, shapes and reductions as Any.
# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_canvas import Canvas, CanvasError, OceanRemainder, remainder_boxes, remainder_runs
from rnw.model import CellClass
from rnw.newworld import (
    NewWorld,
    _sea_cells,  # pyright: ignore[reportPrivateUsage]
    derive_world,
)
from rnw.progress import checkpoint
from rnw.rng import derive_seed
from rnw.synth import renumber
from rnw.topology import adjacency_pairs, label_components, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from rnw.continent_domains import Domain
    from rnw.eu5_map import Eu5Map
    from rnw.land_contact import ContactBlend

BAND_ROWS: Final[int] = 256
CELL_ORDER: Final[dict[CellClass, int]] = {
    CellClass.LAND: 0,
    CellClass.WASTELAND: 0,
    CellClass.NON_OWNABLE: 0,
    CellClass.SEA: 1,
    CellClass.LAKE: 2,
}


@dataclass(frozen=True, slots=True, eq=False)
class WorldRegion:
    """A completed physical domain at its original local origin."""

    domain: Domain
    world: NewWorld
    contact: ContactBlend | None = None


@dataclass(frozen=True, slots=True, eq=False)
class ComposedWorld:
    """One map and a translation from every physical regional location number."""

    canvas: Canvas
    world: NewWorld
    cell_ids: dict[str, NDArray[np.int32]]


def _place(
    region: WorldRegion,
    cells: NDArray[np.int32],
    labels: NDArray[np.int32],
    elevation: NDArray[np.int32],
) -> None:
    domain, world = region.domain, region.world
    if world.labels.shape != domain.mask.shape:
        message = f"Generated cells do not fit {domain.continent.key}"
        raise CanvasError(message)
    table = np.append(cells, np.int32(-1)).astype(np.int32, copy=False)
    for local, original in domain.spans():
        for first in range(0, domain.mask.shape[0], BAND_ROWS):
            checkpoint()
            stop = min(first + BAND_ROWS, domain.mask.shape[0])
            rows = slice(first + domain.first_row, stop + domain.first_row)
            own = world.labels[first:stop, local]
            mask = own >= 0
            target = labels[rows, original]
            if np.any(mask & (target >= 0)) or np.any(mask != domain.mask[first:stop, local]):
                message = f"The composed footprint conflicts at {domain.continent.key}"
                raise CanvasError(message)
            np.copyto(target, table[own], where=mask)
            np.copyto(elevation[rows, original], world.elevation[first:stop, local], where=mask)


def _canvas(game_map: Eu5Map, mask: NDArray[np.bool_]) -> Canvas:
    original = game_map.labels
    count = len(game_map.keys)
    inside = np.zeros(count, dtype=np.int64)
    outside = np.zeros(count, dtype=np.int64)
    for first in range(0, original.shape[0], BAND_ROWS):
        checkpoint()
        rows = slice(first, first + BAND_ROWS)
        found = original[rows]
        total = np.bincount(found.ravel(), minlength=count)
        covered = np.bincount(found[mask[rows]], minlength=count)
        inside += covered
        outside += total - covered
    trimmed = (inside > 0) & (outside > 0)
    return Canvas(
        roll=0,
        col0=0,
        mask=mask,
        shape=original.shape,
        removed=(inside > 0) & (outside == 0),
        trimmed=trimmed,
        ocean_parts=_remainders(game_map, mask, trimmed),
    )


def _remainders(
    game_map: Eu5Map, mask: NDArray[np.bool_], trimmed: NDArray[np.bool_]
) -> tuple[OceanRemainder, ...]:
    labels = game_map.labels
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    zones = np.flatnonzero(trimmed & sea).astype(np.int32)
    parts: list[OceanRemainder] = []
    for zone, window in remainder_boxes(labels, mask, zones, len(game_map.keys)).items():
        rest = (labels[window] == zone) & ~mask[window]
        components = label_components(
            rest.astype(np.int32), wrap_x=rest.shape[1] == labels.shape[1]
        )
        sizes = np.bincount(components[rest])
        found = np.flatnonzero(sizes).tolist()
        if len(found) == 1 and not game_map.ambiguous[zone]:
            continue
        parts.extend(
            OceanRemainder(
                zone,
                remainder_runs(components == part, window[0].start, window[1].start),
                int(sizes[part]),
            )
            for part in sorted(found, key=lambda index: (-sizes[index], index))
        )
    return tuple(parts)


def compose_regions(
    game_map: Eu5Map,
    regions: Sequence[WorldRegion],
    *,
    southern_passage: int = 0,
    seed: int = 0,
) -> ComposedWorld:
    """Assemble the final physical footprints, preserving wrap and local cell measurements."""
    names = [r.domain.continent.key for r in regions]
    if not names or len(set(names)) != len(names):
        message = "Compose each selected continent exactly once"
        raise CanvasError(message)
    rows, columns = game_map.labels.shape
    labels = np.full((rows, columns), -1, dtype=np.int32)
    elevation = np.zeros((rows, columns), dtype=np.int32)
    kinds = tuple(kind for r in regions for kind in r.world.classes)
    order = sorted(range(len(kinds)), key=lambda index: CELL_ORDER[kinds[index]])
    numbers = np.empty(len(kinds), dtype=np.int32)
    numbers[order] = np.arange(len(kinds), dtype=np.int32)
    cell_ids: dict[str, NDArray[np.int32]] = {}
    centroids: list[NDArray[np.int64]] = []
    interior: list[NDArray[np.int64]] = []
    start = 0
    for name, region in zip(names, regions, strict=True):
        domain, local = region.domain, region.world
        stop = start + len(local.classes)
        cell_ids[name] = numbers[start:stop]
        _place(region, cell_ids[name], labels, elevation)
        centres = local.centroids.copy()
        points = local.interior.copy()
        for coordinates in (centres, points):
            coordinates[:, 0] += domain.first_row
            coordinates[:, 1] = (coordinates[:, 1] + domain.first_column) % columns
        centroids.append(centres)
        interior.append(points)
        start = stop
    ordered = tuple(kinds[index] for index in order)
    pixels = np.concatenate([r.world.pixels for r in regions])[order]
    centres = np.concatenate(centroids)[order]
    points = np.concatenate(interior)[order]
    mean = np.concatenate([r.world.mean_elevation for r in regions])[order]
    spread = np.concatenate([r.world.spread for r in regions])[order]
    if southern_passage:
        south = _southern_water(game_map, labels, southern_passage, seed=seed)
        ordered += south.classes
        pixels = np.concatenate((pixels, south.pixels))
        shift = (rows - southern_passage, 0)
        centres = np.concatenate((centres, south.centroids + shift))
        points = np.concatenate((points, south.interior + shift))
        mean = np.concatenate((mean, south.mean_elevation))
        spread = np.concatenate((spread, south.spread))
    return ComposedWorld(
        _canvas(game_map, labels >= 0),
        NewWorld(
            labels=labels,
            classes=ordered,
            elevation=elevation,
            pixels=pixels,
            centroids=centres,
            interior=points,
            mean_elevation=mean,
            spread=spread,
            barrier=np.concatenate(
                [cell_ids[r.domain.continent.key][r.world.barrier] for r in regions]
            ).astype(np.int64),
            edges=tuple(
                (a, b) for a, b in unpack_pairs(adjacency_pairs(labels, wrap_x=True)) if a >= 0
            ),
            wrap_x=True,
        ),
        cell_ids,
    )


def _southern_water(game: Eu5Map, labels: NDArray[np.int32], reach: int, *, seed: int) -> NewWorld:
    """Partition the southern link through retained closed ocean at normal sea-cell scale."""
    known = np.array([kind is CellClass.SEA for kind in game.classes], dtype=bool)
    target = labels[-reach:]
    closed = (known & game.ambiguous)[game.labels[-reach:]] & (target < 0)
    spacing = max(3, 120 * labels.shape[1] // 16_384)
    generated = (
        _sea_cells(
            closed,
            key=derive_seed(seed, "southern_passage"),
            spacing=spacing,
            smallest=max(1, spacing**2 // 7),
            domain=closed,
            bands=None,
        )
        if closed.any()
        else np.full(closed.shape, -1, dtype=np.int32)
    )
    generated = renumber(generated)
    south = derive_world(
        generated, (CellClass.SEA,) * (int(generated.max()) + 1), np.zeros_like(generated)
    )
    if closed.any():
        target[closed] = generated[closed] + int(labels.max()) + 1
    return south
