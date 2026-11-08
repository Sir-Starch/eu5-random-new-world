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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import CellBiomes
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_map import RIVER_WATER
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world

if TYPE_CHECKING:
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
    empty: dict[str, str] = {}
    cells: list[PlannedCell] = []
    for label in keep:
        key = game_map.keys[label]
        location = hierarchy.get(key)
        cells.append(
            PlannedCell(
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
        )
    biomes = CellBiomes(
        climate=tuple(attributes.get(cell.key, empty).get("climate", "") for cell in cells),
        vegetation=tuple(attributes.get(cell.key, empty).get("vegetation", "") for cell in cells),
        topography=tuple(attributes.get(cell.key, empty).get("topography", "") for cell in cells),
        raw_material=tuple(
            attributes.get(cell.key, empty).get("raw_material", "") for cell in cells
        ),
    )
    flowing = canvas.mask & (_crop(canvas, game_map.rivers) < RIVER_WATER)
    river_pixels = np.bincount(labels[flowing & (labels >= 0)], minlength=len(keep)).astype(
        np.int64
    )
    return VanillaWorld(tuple(keep), world, Plan(cells=cells), biomes, river_pixels)
