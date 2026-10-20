"""Choose the replaceable New World canvas on the EU5 map (read-only).

The canvas is every pixel of the ``america`` continent plus ocean-continent sea pixels
within ``band_px`` of it, minus a guard zone around every other continent so that no
Old World location gains or loses a contact. Ocean zones cut by the band keep their key
and their largest remaining part; their other fragments join the canvas.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

NEW_WORLD: Final[str] = "america"
OCEANS: Final[frozenset[str]] = frozenset({"atlantic_ocean_continent", "pacific_ocean_continent"})
GUARD_PX: Final[int] = 96
MIN_REMAINDER_PX: Final[int] = 3000


class CanvasError(ValueError):
    """The canvas cannot be placed without crossing the map seam."""


@dataclass(frozen=True, slots=True, eq=False)
class Canvas:
    """Canvas in rolled coordinates: world column = (column + col0 - roll) mod width."""

    roll: int
    col0: int
    mask: NDArray[np.bool_]
    rolled: NDArray[np.int32]
    removed: NDArray[np.bool_]
    trimmed: NDArray[np.bool_]

    def world_column(self, column: NDArray[np.int64] | int) -> NDArray[np.int64] | int:
        """Map a crop column back to the unrolled map column."""
        width = int(self.rolled.shape[1])
        return (column + self.col0 - self.roll) % width


def _roll_for(columns_used: NDArray[np.bool_]) -> int:
    """Roll that moves the centre of the widest unused column run to column 0."""
    width = columns_used.size
    doubled = np.concatenate([columns_used, columns_used])
    best_start, best_length, start = 0, 0, -1
    for index, used in enumerate(doubled.tolist()):
        if not used and start < 0:
            start = index
        if (used or index == doubled.size - 1) and start >= 0:
            length = index - start
            if length > best_length and start < width:
                best_start, best_length = start, length
            start = -1
    centre = (best_start + best_length // 2) % width
    return (width - centre) % width


def _drop_landlocked(canvas: NDArray[np.bool_], sea: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Keep only canvas parts that touch a sea pixel outside the canvas.

    A part enclosed by other land could only hold orphan seas, so its vanilla locations
    are left untouched instead.
    """
    open_sea = sea & ~canvas
    touching = np.zeros(canvas.shape, dtype=bool)
    touching[1:] |= open_sea[:-1]
    touching[:-1] |= open_sea[1:]
    touching[:, 1:] |= open_sea[:, :-1]
    touching[:, :-1] |= open_sea[:, 1:]
    parts = label_components(np.where(canvas, 1, 0).astype(np.int32))
    good = np.zeros(int(parts.max()) + 1, dtype=bool)
    good[np.unique(parts[canvas & touching])] = True
    return canvas & good[parts]


def _remainder_boxes(
    rolled: NDArray[np.int32], canvas: NDArray[np.bool_], zones: NDArray[np.int32], count: int
) -> dict[int, tuple[slice, slice]]:
    """Bounding box of the part of each zone that the canvas leaves, for zones with one.

    A zone's remainder does not change while other zones are processed, since the
    canvas only changes on the pixels of the zone being processed.
    """
    chosen = np.zeros(count, dtype=bool)
    chosen[zones] = True
    rest = chosen[rolled] & ~canvas
    low = np.full((2, count), np.iinfo(np.int64).max, dtype=np.int64)
    high = np.full((2, count), -1, dtype=np.int64)
    for axis, view in enumerate((rest, rest.T)):
        first, second = np.nonzero(view)  # ascending in the first coordinate
        owner = rolled[(first, second) if axis == 0 else (second, first)]
        low[axis, owner[::-1]] = first[::-1]
        high[axis, owner] = first
    return {
        int(zone): (slice(int(low[0, zone]), int(high[0, zone]) + 1),
                    slice(int(low[1, zone]), int(high[1, zone]) + 1))
        for zone in zones.tolist()
        if high[0, zone] >= 0
    }  # fmt: skip


def select_canvas(game_map: Eu5Map, band_px: int) -> Canvas:
    """Return the canvas for ``band_px`` of ocean around the New World."""
    count = len(game_map.keys)
    continents = np.array(game_map.continents, dtype=object)
    new_world = continents == NEW_WORLD
    ocean = np.isin(continents, list(OCEANS))
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    roll = _roll_for(new_world[game_map.labels].any(axis=0))
    rolled = np.roll(game_map.labels, roll, axis=1)
    inside_new = new_world[rolled]
    near_new = distance_from(inside_new, band_px + 1, octagonal=True) <= band_px
    other = ~new_world & ~ocean
    near_other = distance_from(other[rolled], GUARD_PX + 1) <= GUARD_PX
    canvas = inside_new | ((ocean & sea)[rolled] & near_new & ~near_other)
    zones = np.unique(rolled[canvas & ~inside_new])
    boxes = _remainder_boxes(rolled, canvas, zones, count)
    for zone in zones.tolist():
        if zone not in boxes:
            continue
        window = boxes[zone]
        part = (rolled[window] == zone) & ~canvas[window]
        components = label_components(part.astype(np.int32))
        sizes = np.bincount(components[part])
        keep = int(np.argmax(sizes))
        others = np.delete(sizes, keep)
        if int(sizes[keep]) < MIN_REMAINDER_PX:
            canvas[window] |= part
        elif others.size and int(others.max()) >= MIN_REMAINDER_PX:
            canvas &= rolled != zone
        else:
            canvas[window] |= part & (components != keep)
    canvas = _drop_landlocked(canvas, sea[rolled])
    used = np.flatnonzero(canvas.any(axis=0))
    if used[0] == 0 or used[-1] == canvas.shape[1] - 1:
        message = "New World canvas crosses the map seam; reduce band_px"
        raise CanvasError(message)
    inside = np.bincount(rolled[canvas].ravel(), minlength=count)
    total = np.bincount(rolled.ravel(), minlength=count)
    removed = (inside == total) & (total > 0)
    trimmed = (inside > 0) & ~removed
    col0, col1 = int(used[0]), int(used[-1]) + 1
    return Canvas(
        roll=roll,
        col0=col0,
        mask=np.ascontiguousarray(canvas[:, col0:col1]),
        rolled=rolled,
        removed=removed,
        trimmed=trimmed,
    )
