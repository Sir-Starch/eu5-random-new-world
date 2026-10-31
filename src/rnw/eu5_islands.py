"""The vanilla map with its moved island groups where they now stand (EU5 1.4.6).

``eu5_canvas.place_islands`` decides where each island group stands. This module moves the
vanilla data that names a place: the location colours and labels, the rivers and the points
(locators and ports) of the locations and coast zones of every group that moved. A group's
pixels are copied to their new place and its points shifted with them; the old place is left
as it was, because it lies inside the canvas and is generated over.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_canvas import moved_pixels
from rnw.eu5_map import MapPoint

if TYPE_CHECKING:
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map


def shifts(game_map: Eu5Map, canvas: Canvas) -> dict[str, tuple[int, int]]:
    """Rows and columns by which each moved location and coast zone has moved, by key."""
    found: dict[str, tuple[int, int]] = {}
    for group, move in zip(canvas.groups, canvas.moves, strict=False):
        if move != (0, 0):
            for label in (*group.locations, *group.zones):
                found[game_map.keys[label]] = move
    return found


def relocate_map(game_map: Eu5Map, canvas: Canvas) -> Eu5Map:
    """``game_map`` with each moved group's pixels and points at their new place."""
    moved = shifts(game_map, canvas)
    if not moved:
        return game_map
    width = int(game_map.labels.shape[1])
    labels = game_map.labels.copy()
    rgb = game_map.rgb.copy()
    rivers = game_map.rivers.copy()
    for footprint, (down, across) in zip(canvas.footprints, canvas.moves, strict=False):
        if not (down or across):
            continue
        rows = footprint.rows.astype(np.int64)
        old = np.asarray(canvas.world_column(footprint.columns.astype(np.int64)))
        new = np.asarray(canvas.world_column(footprint.columns.astype(np.int64) + across))
        labels[rows + down, new] = game_map.labels[rows, old]
        rgb[rows + down, new] = game_map.rgb[rows, old]
        rivers[rows + down, new] = game_map.rivers[rows, old]
    points = tuple(
        MapPoint(
            point.source,
            point.key,
            (point.x + moved[point.key][1]) % width,
            point.y + moved[point.key][0],
        )
        if point.key in moved
        else point
        for point in game_map.points
    )
    return replace(game_map, labels=labels, rgb=rgb, rivers=rivers, points=points)


def stamp_codes(
    codes: np.ndarray[tuple[int, ...], np.dtype[np.int8]],
    game_map: Eu5Map,
    canvas: Canvas,
    water: int,
    land: int,
) -> None:
    """Mark the pixels where moved groups stand as ground to build: water for coast zones."""
    rows, columns = moved_pixels(canvas)
    if rows.size == 0:
        return
    sea = np.array([kind.value in {"sea", "lake"} for kind in game_map.classes], dtype=bool)
    codes[rows, columns] = np.where(sea[game_map.labels[rows, columns]], water, land)
