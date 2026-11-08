"""Choose the replaceable New World canvas on the EU5 map (read-only).

The original canvas follows ``america`` with an ocean distance band. Optional expansion
adds a fixed longitudinal ocean sector and retains the northern extension. Both protect
other continents and their waters. Expanded closed-ocean remainders are recorded as row
runs for the connected final identities planned by ``eu5_oceans``; their fragments no
longer veto the entire ocean's inclusion.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_pacific import REFERENCE_WIDTH, IslandGroup, expansion
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

NEW_WORLD: Final[str] = "america"
OCEANS: Final[frozenset[str]] = frozenset({"atlantic_ocean_continent", "pacific_ocean_continent"})
OPENED: Final[frozenset[str]] = frozenset(
    {"oceania", "indian_ocean_continent", "antarctic_ocean_continent"}
)
GUARD_PX: Final[int] = 96
MIN_REMAINDER_PX: Final[int] = 3000
# A remainder thinner than this is a strip of a zone that the canvas cut along its length,
# a long needle or a bent bolt among the generated waters that touches many neighbours; the
# canvas takes it whole. Vanilla's zones are 50-80 px thick at their cores, so a remainder this
# thin is less than two thirds of the thinnest core. (The 20 px of the first rule left the bolts
# of 22-25 px: twelve zones of the installed map, 0.1 % of the canvas's area.)
MIN_THICKNESS_PX: Final[int] = 30
EXPANDED_BAND_PX: Final[int] = 1600
OCEAN_SECTOR: Final[tuple[int, int]] = (1600, 6500)


class CanvasError(ValueError):
    """The canvas cannot be placed without crossing the map seam."""


@dataclass(frozen=True, slots=True, eq=False)
class OceanRemainder:
    """One connected closed-ocean remainder, as (row, left, right) rolled runs."""

    source: int
    runs: NDArray[np.int64]
    pixels: int


def remainder_runs(mask: NDArray[np.bool_], top: int, left: int) -> NDArray[np.int64]:
    """Encode a bounded component by row, without retaining another large raster."""
    found: list[tuple[int, int, int]] = []
    for row in range(mask.shape[0]):
        ends = np.flatnonzero(np.diff(np.pad(mask[row], 1).astype(np.int8)))
        found.extend(
            (top + row, left + start, left + stop)
            for start, stop in zip(ends[::2].tolist(), ends[1::2].tolist(), strict=True)
        )
    return np.asarray(found, dtype=np.int64).reshape(-1, 3)


@dataclass(frozen=True, slots=True, eq=False)
class Canvas:
    """Canvas in rolled coordinates: world column = (column + col0 - roll) mod width."""

    roll: int
    col0: int
    mask: NDArray[np.bool_]
    shape: tuple[int, int]
    removed: NDArray[np.bool_]
    trimmed: NDArray[np.bool_]
    ocean_parts: tuple[OceanRemainder, ...] = ()
    groups: tuple[IslandGroup, ...] = ()
    footprints: tuple[Footprint, ...] = ()
    moves: tuple[tuple[int, int], ...] = ()
    opened: NDArray[np.bool_] | None = None
    expanded: bool = False
    # Where the installed game's own Americas lie on the canvas (land and lakes of the New World's
    # continent): the template of Omerika (``rnw.omerika``). Read from the map, never shipped.
    template: NDArray[np.bool_] | None = None

    def rolled(self, labels: NDArray[np.int32], rows: slice | None = None) -> NDArray[np.int32]:
        """Rows of the map's ``labels`` in rolled coordinates (the map is not kept rolled)."""
        return np.roll(labels if rows is None else labels[rows], self.roll, axis=1)

    def world_column(self, column: NDArray[np.int64] | int) -> NDArray[np.int64] | int:
        """Map a crop column back to the unrolled map column."""
        return (column + self.col0 - self.roll) % self.shape[1]

    def spans(self) -> list[tuple[slice, slice]]:
        """Pairs of (crop columns, map columns) that cover the canvas: two if it wraps the seam."""
        width, crop_width = self.shape[1], int(self.mask.shape[1])
        start = (self.col0 - self.roll) % width
        first = min(crop_width, width - start)
        pairs = [(slice(0, first), slice(start, start + first))]
        if first < crop_width:
            pairs.append((slice(first, crop_width), slice(0, crop_width - first)))
        return pairs

    def put(self, target: NDArray[np.generic], values: NDArray[np.generic]) -> None:
        """Write the crop-sized ``values`` into the map-sized ``target`` where the mask holds.

        Equal to assigning through the indices of the mask's pixels and their map columns,
        without building those indices (two eight-byte numbers for each of 38 million pixels).
        """
        for crop, world in self.spans():
            keep = self.mask[:, crop]
            keep = keep.reshape(keep.shape + (1,) * (values.ndim - 2))
            np.copyto(target[:, world], values[:, crop], where=keep)


def moved_pixels(canvas: Canvas) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Rows and map columns of the pixels where the moved island groups now stand."""
    rows: list[NDArray[np.int64]] = []
    columns: list[NDArray[np.int64]] = []
    for footprint, (down, across) in zip(canvas.footprints, canvas.moves, strict=False):
        if down or across:
            rows.append(footprint.rows.astype(np.int64) + down)
            columns.append(
                np.asarray(canvas.world_column(footprint.columns.astype(np.int64) + across))
            )
    if not rows:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    return np.concatenate(rows), np.concatenate(columns)


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


def remainder_boxes(
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


def _thickness(mask: NDArray[np.bool_]) -> float:
    """Twice the area over the perimeter, in pixels: the width of a strip of ``mask``."""
    padded = np.pad(mask, 1)
    inner = padded[1:-1, 1:-1]
    perimeter = sum(
        int(np.count_nonzero(inner & ~view))
        for view in (padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:])
    )
    return 2.0 * int(np.count_nonzero(mask)) / max(perimeter, 1)


def _crop_labels(game_map: Eu5Map, canvas: Canvas) -> NDArray[np.int32]:
    crop = np.empty(canvas.mask.shape, dtype=np.int32)
    for columns, world in canvas.spans():
        crop[:, columns] = game_map.labels[:, world]
    return crop


def _account(
    rolled: NDArray[np.int32], canvas: NDArray[np.bool_], count: int
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    """The locations the canvas replaces whole, and those it only trims."""
    inside = np.bincount(rolled[canvas].ravel(), minlength=count)
    total = np.bincount(rolled.ravel(), minlength=count)
    removed = (inside == total) & (total > 0)
    return removed, (inside > 0) & ~removed


def _footprints(
    crop: NDArray[np.int32], mask: NDArray[np.bool_], groups: tuple[IslandGroup, ...], count: int
) -> tuple[Footprint, ...]:
    """The canvas pixels of each group: its locations and its coast zones, in crop coordinates."""
    if not groups:
        return ()
    owner = np.full(count, -1, dtype=np.int32)
    for number, group in enumerate(groups):
        owner[list(group.zones)] = number
    for number, group in enumerate(groups):
        owner[list(group.locations)] = number
    grid = owner[crop]
    grid[~mask] = -1
    rows, columns = np.nonzero(grid >= 0)
    who = grid[rows, columns]
    order = np.argsort(who, kind="stable")
    rows, columns, who = rows[order], columns[order], who[order]
    bounds = np.searchsorted(who, np.arange(len(groups) + 1))
    return tuple(
        Footprint(
            rows[bounds[number] : bounds[number + 1]].astype(np.int32),
            columns[bounds[number] : bounds[number + 1]].astype(np.int32),
        )
        for number in range(len(groups))
    )


def place_islands(
    game_map: Eu5Map, canvas: Canvas, moves: Sequence[tuple[int, int]] | None = None
) -> Canvas:
    """The canvas with its island groups where they stand or have moved to.

    ``select_canvas`` covers the groups, so a continent may be generated over them. Here each
    group (its locations and its coast zones) becomes a hole of the mask at its final place, so
    its vanilla pixels survive there; ``moves`` is the translation of each group (none: they
    all stay). The old place of a group that moved stays in the mask, to be generated. The
    replaced and trimmed locations are counted again on the map as it is then, a group's
    pixels at their new place and nothing else of it.
    """
    if not canvas.groups and not canvas.expanded:
        return canvas
    shifts = tuple(moves) if moves is not None else ((0, 0),) * len(canvas.groups)
    count = len(game_map.keys)
    crop = _crop_labels(game_map, canvas)
    mask = canvas.mask.copy()
    member = np.zeros(count, dtype=bool)
    lost = np.zeros(count, dtype=np.int64)
    after = crop.copy()
    for group, footprint, (rows, columns) in zip(
        canvas.groups, canvas.footprints, shifts, strict=True
    ):
        member[list(group.locations)] = True
        member[list(group.zones)] = True
        target = (footprint.rows + rows, footprint.columns + columns)
        lost += np.bincount(crop[target], minlength=count)
        after[target] = crop[footprint.rows, footprint.columns]
        mask[target] = False
    inside = np.bincount(after[mask].ravel(), minlength=count)
    total = np.bincount(game_map.labels.ravel(), minlength=count)
    removed = (inside == total - np.where(member, 0, lost)) & (total > 0) & ~member
    trimmed = (inside > 0) & ~removed & ~member
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    tagged = np.array([name in OPENED for name in game_map.continents], dtype=bool)
    return replace(
        canvas,
        mask=mask,
        removed=removed,
        trimmed=trimmed,
        moves=shifts,
        opened=(removed | trimmed) & sea & tagged,
    )


def open_map(game_map: Eu5Map, canvas: Canvas) -> Eu5Map:
    """The map with the open waters the canvas took over counted as ocean, as the rest are.

    The Pacific side covers sea zones that the installed game files give to oceania or to the
    southern oceans; the generated world replaces or trims them as it does an ocean's.
    """
    if canvas.opened is None or not canvas.opened.any():
        return game_map
    continents = tuple(
        "pacific_ocean_continent" if opened else name
        for name, opened in zip(game_map.continents, canvas.opened.tolist(), strict=True)
    )
    return replace(game_map, continents=continents)


def _sector(rolled: NDArray[np.int32], roll: int, water: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """A fixed longitudinal sector of ``water``, east of Hawaii and west of the African waters.

    Coordinates are fractions of the installed map, not a shipped raster. The old band
    supplies Alaska's northern extension; the sector supplies southern width independently of
    America's coast. All protected waters keep their guard.
    """
    columns = (np.arange(rolled.shape[1], dtype=np.int64) - roll) % rolled.shape[1]
    inside = (columns * REFERENCE_WIDTH >= OCEAN_SECTOR[0] * rolled.shape[1]) & (
        columns * REFERENCE_WIDTH < OCEAN_SECTOR[1] * rolled.shape[1]
    )
    return water & inside[np.newaxis, :]


def _expand(
    game_map: Eu5Map, rolled: NDArray[np.int32], canvas: NDArray[np.bool_]
) -> tuple[NDArray[np.bool_], tuple[IslandGroup, ...]]:
    """The canvas with the Pacific side, and the island groups that it covers."""
    new_world = np.array([name == NEW_WORLD for name in game_map.continents], dtype=bool)
    added = expansion(game_map, rolled, canvas, new_world[rolled])
    return added.canvas, added.groups


def select_canvas(game_map: Eu5Map, band_px: int, *, expanded: bool = False) -> Canvas:
    """Return the canvas for ``band_px`` of ocean around the New World."""
    count = len(game_map.keys)
    groups: tuple[IslandGroup, ...] = ()
    continents = np.array(game_map.continents, dtype=object)
    new_world = continents == NEW_WORLD
    ocean = np.isin(continents, list(OCEANS))
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    roll = _roll_for(new_world[game_map.labels].any(axis=0))
    rolled = np.roll(game_map.labels, roll, axis=1)
    inside_new = new_world[rolled]
    band = max(1, EXPANDED_BAND_PX * rolled.shape[1] // REFERENCE_WIDTH) if expanded else band_px
    near_new = distance_from(inside_new, band + 1, octagonal=True) <= band
    other = ~new_world & ~ocean
    near_other = distance_from(other[rolled], GUARD_PX + 1) <= GUARD_PX
    canvas = inside_new | ((ocean & sea)[rolled] & near_new & ~near_other)
    if expanded:
        water = (ocean & sea)[rolled] & ~near_other
        canvas, groups = _expand(game_map, rolled, canvas | _sector(rolled, roll, water))
    zones = np.unique(rolled[canvas & ~inside_new])
    boxes = remainder_boxes(rolled, canvas, zones, count)
    ocean_parts: list[OceanRemainder] = []
    for zone in zones.tolist():
        if zone not in boxes:
            continue
        window = boxes[zone]
        part = (rolled[window] == zone) & ~canvas[window]
        # Closed-ocean remainders are partitioned into connected identities by the
        # ocean planner. Their geometry no longer vetoes the generation domain.
        if expanded and game_map.ambiguous[zone]:
            components = label_components(
                part.astype(np.int32), wrap_x=part.shape[1] == rolled.shape[1]
            )
            sizes = np.bincount(components[part])
            ocean_parts.extend(
                OceanRemainder(
                    zone,
                    remainder_runs(
                        part & (components == component), window[0].start, window[1].start
                    ),
                    int(sizes[component]),
                )
                for component in sorted(
                    np.flatnonzero(sizes).tolist(), key=lambda n: (-sizes[n], n)
                )
            )
            continue
        components = label_components(part.astype(np.int32))
        sizes = np.bincount(components[part])
        keep = int(np.argmax(sizes))
        others = np.delete(sizes, keep)
        if int(sizes[keep]) < MIN_REMAINDER_PX or _thickness(components == keep) < MIN_THICKNESS_PX:
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
    removed, trimmed = _account(rolled, canvas, count)
    col0, col1 = int(used[0]), int(used[-1]) + 1
    americas = new_world & ~sea
    return Canvas(
        roll=roll,
        col0=col0,
        mask=np.ascontiguousarray(canvas[:, col0:col1]),
        shape=(int(rolled.shape[0]), int(rolled.shape[1])),
        removed=removed,
        trimmed=trimmed,
        ocean_parts=tuple(ocean_parts),
        groups=groups,
        footprints=_footprints(rolled[:, col0:col1], canvas[:, col0:col1], groups, count),
        expanded=expanded,
        template=np.ascontiguousarray(americas[rolled[:, col0:col1]]),
    )
