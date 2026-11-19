"""The installed game's Americas as the types the societies stage reads (ADR 0012).

A world that keeps the vanilla geography generates no land: the cells are the game's own
locations, the hierarchy is the game's, and the climate, vegetation, topography and resources
are those of the game's location templates. The societies stage (``rnw.eu5_history_build``)
reads a ``NewWorld`` (cell classes, contacts, sizes, centres), a ``Plan`` (the key and the
hierarchy of each cell), the ``CellBiomes`` of each cell and the river pixels of each cell; this
module makes those from the installation, and nothing else. It writes no file.

A cell is a vanilla location: of the ``america`` continent (land, wasteland, lakes) or a water
(sea zone or lake) that the canvas of the original ocean band takes in, as many of them as the
canvas holds a pixel of. Cells are numbered in the order of the map's own labels, so the same
installation always gives the same cells.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import CellBiomes
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_map import RIVER_WATER
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world

if TYPE_CHECKING:
    from collections.abc import Mapping

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.geography import Location

WATER: Final[frozenset[CellClass]] = frozenset({CellClass.SEA, CellClass.LAKE})


class VanillaWorldError(ValueError):
    """The installation has no Americas to keep."""


@dataclass(frozen=True, slots=True, eq=False)
class VanillaWorld:
    """The vanilla Americas on a canvas, in the types of a generated world.

    ``labels`` are cell numbers on the canvas's crop (-1 off the canvas); ``keep`` is the map's
    label of each cell, so ``world.classes[i]`` and ``plan.cells[i]`` are the game's location
    ``game_map.keys[keep[i]]``.
    """

    keep: tuple[int, ...]
    world: NewWorld
    plan: Plan
    biomes: CellBiomes
    river_pixels: NDArray[np.int64]


def cell_labels(game_map: Eu5Map, hierarchy: dict[str, Location], canvas: Canvas) -> list[int]:
    """The map labels that are cells: the Americas' locations and the waters the canvas holds."""
    crop = _crop(canvas, game_map.labels)
    present: list[int] = np.unique(crop[canvas.mask]).tolist()
    found: list[int] = []
    for label in present:
        key = game_map.keys[label]
        location = hierarchy.get(key)
        if game_map.classes[label] in WATER or (
            location is not None and location.continent == NEW_WORLD
        ):
            found.append(int(label))
    return found


def _crop[T: np.generic](canvas: Canvas, raster: NDArray[T]) -> NDArray[T]:
    """The canvas's window of a map-sized raster, in the canvas's coordinates."""
    return np.roll(raster, canvas.roll, axis=1)[:, canvas.col0 : canvas.col0 + canvas.mask.shape[1]]


def _installed_cell(game_map: Eu5Map, hierarchy: Mapping[str, Location], label: int) -> PlannedCell:
    key = game_map.keys[label]
    location = hierarchy.get(key)
    return PlannedCell(
        key=key,
        name=key,
        color=int(game_map.colors[label]),
        kind=game_map.classes[label],
        province=location.province if location else "",
        area=location.area if location else "",
        region=location.region if location else "",
        subcontinent=location.subcontinent if location else "",
        continent=location.continent if location else game_map.continents[label],
    )


def _installed_biomes(
    cells: list[PlannedCell], attributes: Mapping[str, dict[str, str]]
) -> CellBiomes:
    rows = [attributes.get(cell.key, {}) for cell in cells]
    return CellBiomes(
        climate=tuple(row.get("climate", "") for row in rows),
        vegetation=tuple(row.get("vegetation", "") for row in rows),
        topography=tuple(row.get("topography", "") for row in rows),
        raw_material=tuple(row.get("raw_material", "") for row in rows),
    )


def build(
    game_map: Eu5Map,
    hierarchy: dict[str, Location],
    attributes: dict[str, dict[str, str]],
    canvas: Canvas,
    *,
    height: NDArray[np.uint16] | None = None,
) -> VanillaWorld:
    """The vanilla Americas as a world, a plan, biomes and river pixels.

    ``attributes`` are the game's location templates (``eu5_biomes.template_attributes``) and
    ``height`` the game's heights as a map-sized raster (zero where not given: the societies do not
    read it, the atlas does).
    """
    keep = cell_labels(game_map, hierarchy, canvas)
    if not any(
        game_map.classes[label] is CellClass.LAND
        and hierarchy.get(game_map.keys[label]) is not None
        and hierarchy[game_map.keys[label]].continent == NEW_WORLD
        for label in keep
    ):
        message = "The installation has no land of the Americas on the canvas"
        raise VanillaWorldError(message)
    index = np.full(len(game_map.keys) + 1, -1, dtype=np.int32)
    index[keep] = np.arange(len(keep), dtype=np.int32)
    crop = _crop(canvas, game_map.labels)
    labels = np.where(canvas.mask, index[crop], -1).astype(np.int32)
    kinds = tuple(game_map.classes[label] for label in keep)
    elevation = (
        np.zeros(labels.shape, dtype=np.int32)
        if height is None
        else np.where(canvas.mask, _crop(canvas, height), 0).astype(np.int32)
    )
    world = derive_world(labels, kinds, elevation)
    cells = [_installed_cell(game_map, hierarchy, label) for label in keep]
    biomes = _installed_biomes(cells, attributes)
    flowing = canvas.mask & (_crop(canvas, game_map.rivers) < RIVER_WATER)
    river_pixels = np.bincount(labels[flowing & (labels >= 0)], minlength=len(keep)).astype(
        np.int64
    )
    return VanillaWorld(tuple(keep), world, Plan(cells=cells), biomes, river_pixels)


def with_real_americas(  # noqa: PLR0913 - the overlay derives the shared map from final inputs.
    game_map: Eu5Map,
    hierarchy: Mapping[str, Location],
    attributes: Mapping[str, dict[str, str]],
    *,
    final: NDArray[np.int32],
    generated: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    height: NDArray[np.uint16],
    rivers: NDArray[np.uint8],
) -> VanillaWorld:
    """Add unchanged American locations to the society graph, leaving the map plan alone."""
    vanilla_count = len(game_map.keys)
    count = len(plan.cells)
    present = np.bincount(final.ravel(), minlength=vanilla_count + count)
    bound = {cell.key: i for i, cell in enumerate(plan.cells)}
    keep = tuple(
        i
        for i, key in enumerate(game_map.keys)
        if present[i]
        and game_map.continents[i] == NEW_WORLD
        and key in hierarchy
        and key not in bound
    )
    if not any(game_map.classes[i] is CellClass.LAND for i in keep):
        message = "The composed map has no retained American land for the new societies"
        raise VanillaWorldError(message)
    table = np.full(vanilla_count + count, -1, dtype=np.int32)
    table[vanilla_count:] = np.arange(count, dtype=np.int32)
    table[list(keep)] = np.arange(count, count + len(keep), dtype=np.int32)
    for i, key in enumerate(game_map.keys):
        if present[i] and key in bound and game_map.classes[i] is CellClass.SEA:
            table[i] = bound[key]
    labels = np.empty_like(final)
    relief = np.empty_like(generated.elevation)
    flowing = np.zeros(count + len(keep) + 1, dtype=np.int64)
    for first in range(0, final.shape[0], 256):
        rows = slice(first, first + 256)
        current = labels[rows] = table[final[rows]]
        new = generated.labels[rows] >= 0
        relief[rows] = np.where(new, generated.elevation[rows], height[rows])
        water = np.where(new, rivers[rows], game_map.rivers[rows])
        active = current[(current >= 0) & (water < RIVER_WATER)]
        flowing += np.bincount(active, minlength=flowing.size)
    cells = [_installed_cell(game_map, hierarchy, i) for i in keep]
    original = _installed_biomes(cells, attributes)
    classes = generated.classes + tuple(cell.kind for cell in cells)
    world = derive_world(labels, classes, relief, wrap_x=True)
    return VanillaWorld(
        keep,
        world,
        replace(plan, cells=[*plan.cells, *cells]),
        CellBiomes(
            climate=biomes.climate + original.climate,
            vegetation=biomes.vegetation + original.vegetation,
            topography=biomes.topography + original.topography,
            raw_material=biomes.raw_material + original.raw_material,
        ),
        flowing[:-1],
    )
