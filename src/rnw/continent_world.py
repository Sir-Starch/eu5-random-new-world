"""Compose compact regional geography for one pass of world-scale generation."""

# NumPy stubs type boolean indexing, shapes and reductions as Any.
# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.continent_domains import ocean_speck_limit
from rnw.eu5_canvas import Canvas, CanvasError, OceanRemainder, remainder_boxes, remainder_runs
from rnw.islands import Footprint, carve
from rnw.model import CellClass
from rnw.newworld import (
    NewWorld,
)
from rnw.progress import checkpoint
from rnw.topology import adjacency_pairs, label_components, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

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
    expected = domain.mask
    if domain.footprints:
        expected = carve(expected, domain.footprints, tuple(map(tuple, world.moves.tolist())))
    for local, original in domain.spans():
        for first in range(0, domain.mask.shape[0], BAND_ROWS):
            checkpoint()
            stop = min(first + BAND_ROWS, domain.mask.shape[0])
            rows = slice(first + domain.first_row, stop + domain.first_row)
            own = world.labels[first:stop, local]
            mask = own >= 0
            target = labels[rows, original]
            if np.any(mask & (target >= 0)) or np.any(mask != expected[first:stop, local]):
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


def relocated_canvas(game_map: Eu5Map, canvas: Canvas) -> Canvas:
    """Count retained and replaced locations at their final installed coordinates."""
    counted = _canvas(game_map, canvas.mask)
    return replace(
        counted,
        removed=counted.removed if canvas.drowned is None else counted.removed | canvas.drowned,
        groups=canvas.groups,
        footprints=canvas.footprints,
        moves=canvas.moves,
        enclosed_ocean=canvas.enclosed_ocean,
        drowned=canvas.drowned,
    )


def absorb_ocean_specks(game_map: Eu5Map, canvas: Canvas) -> tuple[Eu5Map, Canvas]:
    """Assign an isolated old ocean speck to the retained land enclosing it."""
    height, width = canvas.shape
    paints: list[tuple[OceanRemainder, int]] = []
    labels = game_map.labels
    for part in canvas.ocean_parts:
        if part.pixels >= ocean_speck_limit(width) or not game_map.ambiguous[part.source]:
            continue
        banks: set[int] = set()
        for row, left, right in part.runs.tolist():
            banks.add(int(labels[row, (left - 1) % width]))
            banks.add(int(labels[row, right % width]))
            if row > 0:
                banks.update(labels[row - 1, left:right].tolist())
            if row + 1 < height:
                banks.update(labels[row + 1, left:right].tolist())
        banks.discard(part.source)
        if len(banks) == 1:
            (bank,) = banks
            if game_map.classes[bank] in {CellClass.LAND, CellClass.WASTELAND}:
                paints.append((part, bank))
    if not paints:
        return game_map, canvas
    labels = labels.copy()
    rgb = game_map.rgb.copy()
    for part, bank in paints:
        color = int(game_map.colors[bank])
        for row, left, right in part.runs.tolist():
            labels[row, left:right] = bank
            rgb[row, left:right] = (color >> 16, (color >> 8) & 255, color & 255)
    edits = tuple((part, int(game_map.colors[bank])) for part, bank in paints)
    return replace(game_map, labels=labels, rgb=rgb), replace(canvas, enclosed_ocean=edits)


def _around(cell: int, width: int, height: int) -> tuple[int, ...]:
    """The flat positions of a pixel's four neighbours, round the seam and not past the poles."""
    row, column = divmod(cell, width)
    return (
        *((cell - width,) if row else ()),
        *((cell + width,) if row + 1 < height else ()),
        row * width + (column + 1) % width,
        row * width + (column - 1) % width,
    )


def _pieces(flat: NDArray[np.int64], width: int, height: int, limit: int) -> list[list[int]]:
    """The connected pieces of the flat pixel positions; ``limit`` pixels in one are too many."""
    pending = set(flat.tolist())
    pieces: list[list[int]] = []
    while pending:
        stack = [pending.pop()]
        piece: list[int] = []
        while stack:
            cell = stack.pop()
            piece.append(cell)
            for other in _around(cell, width, height):
                if other in pending:
                    pending.discard(other)
                    stack.append(other)
        if len(piece) >= limit:
            message = "A fragment of replaced land is too large to give to the water round it"
            raise CanvasError(message)
        pieces.append(sorted(piece))
    return pieces


def _bank(piece: list[int], labels: NDArray[np.int32], retained: NDArray[np.bool_]) -> int:
    """The retained location that touches a piece along most of its edge."""
    height, width = labels.shape
    inside = set(piece)
    touching: dict[int, int] = {}
    for cell in piece:
        for other in _around(cell, width, height):
            if other not in inside:
                bank = int(labels[other // width, other % width])
                if retained[bank]:
                    touching[bank] = touching.get(bank, 0) + 1
    if not touching:
        message = "A fragment of replaced land touches no retained location"
        raise CanvasError(message)
    return max(touching, key=lambda index: (touching[index], -index))


def _piece_runs(rows: NDArray[np.int64], columns: NDArray[np.int64]) -> NDArray[np.int64]:
    """A piece as (row, left, right) runs; its positions are sorted by row, then column."""
    runs: list[tuple[int, int, int]] = []
    for row in np.unique(rows).tolist():
        here = columns[rows == row]
        edges = np.flatnonzero(np.diff(here) != 1) + 1
        runs.extend((row, int(run[0]), int(run[-1]) + 1) for run in np.split(here, edges))
    return np.asarray(runs, dtype=np.int64).reshape(-1, 3)


def absorb_land_fragments(
    game_map: Eu5Map, canvas: Canvas, generated: Collection[str]
) -> tuple[Eu5Map, Canvas]:
    """Give the small pieces of replaced land that lie among retained water to that water.

    The plan leaves out of every canvas a small piece of replaced land that no canvas reaches
    (``continent_domains._rejoin_fragments``, ``_without_islets``): an islet's stray pixels, or a
    small island, in a retained sea zone. The location is removed whole, so the piece takes the
    colour of the retained location that surrounds it the most, and the recolouring is recorded
    among the ocean identities' patches, the only changes allowed outside the canvas. A location
    that has no pixel left is recorded as drowned: removed from the map without a canvas.
    """
    labels = game_map.labels
    height, width = labels.shape
    if canvas.mask.shape != labels.shape:
        message = "The composed canvas must cover the whole map"
        raise CanvasError(message)
    kinds = zip(game_map.continents, game_map.classes, strict=True)
    replaced = np.fromiter(
        (name in generated and kind not in {CellClass.SEA, CellClass.LAKE} for name, kind in kinds),
        dtype=bool,
    )
    found: list[NDArray[np.int64]] = []
    for first in range(0, height, BAND_ROWS):
        checkpoint()
        rows = slice(first, first + BAND_ROWS)
        row, column = np.nonzero(replaced[labels[rows]] & ~canvas.mask[rows])
        found.append((row + first) * width + column)
    flat = np.concatenate(found) if found else np.zeros(0, dtype=np.int64)
    if not flat.size:
        return game_map, canvas
    limit = ocean_speck_limit(width)
    if flat.size > limit * 64:
        message = "Replaced land lies outside the generated canvases"
        raise CanvasError(message)
    retained = np.fromiter(
        (
            name not in generated and kind is not CellClass.LAKE
            for name, kind in zip(game_map.continents, game_map.classes, strict=True)
        ),
        dtype=bool,
    )
    count = len(game_map.keys)
    lost = np.bincount(labels[flat // width, flat % width], minlength=count)
    total = np.zeros(count, dtype=np.int64)
    for first in range(0, height, BAND_ROWS):
        total += np.bincount(labels[first : first + BAND_ROWS].ravel(), minlength=count)
    labels, rgb = labels.copy(), game_map.rgb.copy()
    edits: list[tuple[OceanRemainder, int]] = []
    for piece in _pieces(flat, width, height, limit):
        bank = _bank(piece, labels, retained)
        colour = int(game_map.colors[bank])
        rows, columns = np.divmod(np.asarray(piece, dtype=np.int64), width)
        labels[rows, columns] = bank
        rgb[rows, columns] = (colour >> 16, (colour >> 8) & 255, colour & 255)
        edits.append((OceanRemainder(bank, _piece_runs(rows, columns), len(piece)), colour))
    return (
        replace(game_map, labels=labels, rgb=rgb),
        replace(
            canvas,
            enclosed_ocean=(*canvas.enclosed_ocean, *edits),
            drowned=(lost > 0) & (lost == total),
        ),
    )


def _island_placements(canvas: Canvas, regions: Sequence[WorldRegion]) -> Canvas:
    footprints: list[Footprint] = []
    moves: list[tuple[int, int]] = []
    for region in regions:
        domain = region.domain
        for footprint, (down, across) in zip(domain.footprints, region.world.moves, strict=True):
            footprints.append(
                Footprint(
                    footprint.rows + domain.first_row,
                    (footprint.columns + domain.first_column) % domain.map_width,
                )
            )
            moves.append((int(down), int(across)))
    return replace(
        canvas,
        groups=tuple(group for region in regions for group in region.domain.groups),
        footprints=tuple(footprints),
        moves=tuple(moves),
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
    plans = [r.world.planned for r in regions]
    if any(part is None for part in plans) and not all(part is None for part in plans):
        message = "Some continents keep the area planned for their cells and some do not"
        raise CanvasError(message)
    planned = (
        None
        if any(part is None for part in plans)
        else np.concatenate([part for part in plans if part is not None])[order]
    )
    return ComposedWorld(
        _island_placements(_canvas(game_map, labels >= 0), regions),
        NewWorld(
            labels=labels,
            classes=ordered,
            elevation=elevation,
            pixels=pixels,
            centroids=centres,
            interior=points,
            mean_elevation=mean,
            spread=spread,
            planned=planned,
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
