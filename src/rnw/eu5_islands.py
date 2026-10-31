"""The vanilla map with its moved island groups where they now stand (EU5 1.4.6).

``eu5_canvas.place_islands`` decides where each island group stands. This module moves the
vanilla data that names a place: the location colours and labels, the rivers and the points
(locators and ports) of the locations and coast zones of every group that moved, and describes
the moved pixels (``Moved``) for the layers that are read elsewhere: decal heights and materials
(``eu5_terrain``), mountain stamps, vegetation instances (``eu5_objects``) and water colour and
foam (``eu5_water``). A group's pixels are copied to their new place and its points shifted with
them; the old place is left as it was, because it lies inside the canvas and is generated over.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_map import MapPoint

if TYPE_CHECKING:
    from numpy.typing import NDArray

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


@dataclass(frozen=True, slots=True, eq=False)
class Moved:
    """The location pixels of the moved island groups: each old pixel and where it went.

    The pixel at (``rows[i]``, ``columns[i]``) now stands at (``rows[i] + down[i]``,
    ``(columns[i] + across[i]) % width``). ``order`` sorts the old pixels by their raster index.
    """

    rows: NDArray[np.int64]
    columns: NDArray[np.int64]
    down: NDArray[np.int64]
    across: NDArray[np.int64]
    width: int
    index: NDArray[np.int64]

    @property
    def new_rows(self) -> NDArray[np.int64]:
        """Rows of the pixels at their new places."""
        return self.rows + self.down

    @property
    def new_columns(self) -> NDArray[np.int64]:
        """Map columns of the pixels at their new places."""
        return (self.columns + self.across) % self.width

    def find(
        self, rows: NDArray[np.int64], columns: NDArray[np.int64]
    ) -> tuple[NDArray[np.bool_], NDArray[np.int64], NDArray[np.int64]]:
        """Which of the pixels (rows, columns) were moved, and by how many rows and columns."""
        wanted = rows * self.width + columns
        place = np.minimum(np.searchsorted(self.index, wanted), self.index.size - 1)
        found = self.index[place] == wanted
        return found, np.where(found, self.down[place], 0), np.where(found, self.across[place], 0)


def moved_pixels_of(canvas: Canvas) -> Moved | None:
    """The pixels of the groups that moved, None when none did."""
    rows: list[NDArray[np.int64]] = []
    columns: list[NDArray[np.int64]] = []
    down: list[NDArray[np.int64]] = []
    across: list[NDArray[np.int64]] = []
    for footprint, (step, side) in zip(canvas.footprints, canvas.moves, strict=False):
        if step or side:
            rows.append(footprint.rows.astype(np.int64))
            columns.append(np.asarray(canvas.world_column(footprint.columns.astype(np.int64))))
            down.append(np.full(footprint.size, step, dtype=np.int64))
            across.append(np.full(footprint.size, side, dtype=np.int64))
    if not rows:
        return None
    width = canvas.shape[1]
    all_rows, all_columns = np.concatenate(rows), np.concatenate(columns)
    order = np.argsort(all_rows * width + all_columns, kind="stable")
    return Moved(
        all_rows[order],
        all_columns[order],
        np.concatenate(down)[order],
        np.concatenate(across)[order],
        width,
        (all_rows * width + all_columns)[order],
    )
