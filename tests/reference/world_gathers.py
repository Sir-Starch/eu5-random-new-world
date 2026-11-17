"""Original rolled raster reads, before row-major gathers (epoch/output unchanged)."""

# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_seas import PERMILLE, STRIP_ROWS
from rnw.lanes import Course
from rnw.model import CellClass
from rnw.seas import Topography
from rnw.topology import LOW_BITS, PAIR_SHIFT, adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_seas import VanillaWater
    from rnw.newworld import NewWorld


def outside_contacts(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, offset: int
) -> set[tuple[int, int]]:
    """(vanilla label, generated cell) pairs that touch across the canvas edge."""
    height, width = canvas.shape
    stop = canvas.col0 + int(canvas.mask.shape[1]) + 1
    columns = np.arange(canvas.col0 - 1, stop, dtype=np.int64) % width
    contacts: set[tuple[int, int]] = set()
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS + 1))
        generated = np.pad(world.labels[rows], ((0, 0), (1, 1)), constant_values=-1)
        combined = np.where(
            generated >= 0,
            generated + offset,
            canvas.rolled(game_map.labels, rows)[:, columns],
        ).astype(np.int32)
        pairs = adjacency_pairs(combined)
        low, high = pairs >> PAIR_SHIFT, pairs & LOW_BITS
        across = pairs[(low < offset) & (high >= offset)]
        contacts.update((low, high - offset) for low, high in unpack_pairs(across))
    return contacts


def courses_over(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, vanilla: Mapping[str, VanillaWater]
) -> dict[int, Course]:
    """Where the currents of the game's deep zones that the canvas replaced ran over ``world``.

    For every generated cell, the share of its pixels (permille) that lay in such a zone, and the
    mean of their currents over those pixels.
    """
    count = len(game_map.keys)
    lane = np.zeros(count + 1, dtype=bool)
    east = np.zeros(count + 1, dtype=np.int64)
    north = np.zeros(count + 1, dtype=np.int64)
    for label, key in enumerate(game_map.keys):
        water = vanilla.get(key)
        if (
            canvas.removed[label]
            and water is not None
            and water.topography == Topography.DEEP_OCEAN
            and water.current is not None
        ):
            lane[label] = True
            east[label], north[label] = water.current
    cells = len(world.classes)
    area = np.zeros(cells, dtype=np.int64)
    east_sum = np.zeros(cells, dtype=np.float64)
    north_sum = np.zeros(cells, dtype=np.float64)
    height, crop = world.labels.shape
    columns = (np.arange(crop, dtype=np.int64) + canvas.col0) % canvas.shape[1]
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS))
        old = canvas.rolled(game_map.labels, rows)[:, columns]
        generated = world.labels[rows]
        on = lane[old] & (generated >= 0)
        found, were = generated[on], old[on]
        area += np.bincount(found, minlength=cells)
        east_sum += np.bincount(found, weights=east[were], minlength=cells)
        north_sum += np.bincount(found, weights=north[were], minlength=cells)
    courses: dict[int, Course] = {}
    for cell in np.flatnonzero(area).tolist():
        if world.classes[cell] is CellClass.SEA:
            courses[cell] = Course(
                int(PERMILLE * area[cell] // max(1, int(world.pixels[cell]))),
                (
                    round(float(east_sum[cell]) / int(area[cell])),
                    round(float(north_sum[cell]) / int(area[cell])),
                ),
            )
    return courses


def current_bands(
    game_map: Eu5Map, canvas: Canvas, vanilla: Mapping[str, VanillaWater]
) -> np.ndarray[tuple[int, ...], np.dtype[np.bool_]]:
    """The replaced vanilla current footprints, in the generation canvas's coordinates."""
    lane = np.zeros(len(game_map.keys) + 1, dtype=np.bool_)
    for label, key in enumerate(game_map.keys):
        water = vanilla.get(key)
        if (
            canvas.removed[label]
            and water is not None
            and water.topography == Topography.DEEP_OCEAN
            and water.current is not None
        ):
            lane[label] = True
    height, crop = canvas.mask.shape
    columns = (np.arange(crop, dtype=np.int64) + canvas.col0) % canvas.shape[1]
    bands = np.empty((height, crop), dtype=np.bool_)
    for start in range(0, height, STRIP_ROWS):
        rows = slice(start, min(height, start + STRIP_ROWS))
        bands[rows] = lane[canvas.rolled(game_map.labels, rows)[:, columns]] & canvas.mask[rows]
    return bands
