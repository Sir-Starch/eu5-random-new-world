"""The far-Pacific side of the expanded canvas and the island groups it contains (read-only).

The expanded canvas of ``eu5_canvas`` keeps the Atlantic side it always had. This module adds
the other side of the New World: the Pacific from the far west of the map, through the
polynesian islands before the map seam, to the open water east of New Zealand. The shape is
made of round contours only, never of tag borders or column limits, because a continent
generated against a straight canvas edge would inherit a straight coast:

* water within ``REACH_PX`` (Euclidean) of the New World, minus ``GUARD_PX`` around every
  Old World land location and around the waters of the Old World continents;
* pockets and channels narrower than twice ``OPEN_PX`` are dropped, so nothing is generated
  between New Zealand and Australia or in the bays of the Oceanian island chains;
* the addition stops at a column where the existing canvas already covers every row, so it
  joins the Atlantic part without a visible edge, which stays exactly as it was.

Island groups of oceania and the ocean tags that end up wholly inside the canvas are not
holes of it: the canvas covers them and reports them as groups, so a continent can be
generated over them and ``eu5_islands`` can keep or move each group.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.topology import adjacency_pairs, euclidean_distance, label_components, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map

REFERENCE_WIDTH: Final[int] = 16384
STEP: Final[int] = 4
EIGHTHS: Final[int] = 8
REACH_PX: Final[int] = 5400
GUARD_PX: Final[int] = 160
OPEN_PX: Final[int] = 300
GROUP_PX: Final[int] = 32
COAST_ZONE_PX: Final[int] = 30_000
STRIP_COLUMNS: Final[int] = 1600
OLD_WORLD: Final[frozenset[str]] = frozenset({"asia", "europe", "africa"})
ISLAND_TAGS: Final[frozenset[str]] = frozenset(
    {"oceania", "atlantic_ocean_continent", "pacific_ocean_continent"}
)
NOT_LAND: Final[frozenset[CellClass]] = frozenset({CellClass.SEA, CellClass.LAKE})


class ExpansionError(ValueError):
    """The Pacific side cannot join the canvas that the Atlantic side defines."""


@dataclass(frozen=True, slots=True, eq=False)
class IslandGroup:
    """Island locations that stay or move together, with the sea zones of their ports."""

    locations: tuple[int, ...]
    zones: tuple[int, ...]


@dataclass(frozen=True, slots=True, eq=False)
class Expansion:
    """What the Pacific side adds to a canvas, in the rolled coordinates of its input."""

    canvas: NDArray[np.bool_]
    groups: tuple[IslandGroup, ...]


def scaled(pixels: int, width: int) -> int:
    """A distance of the installed 16,384-pixel map, on a map ``width`` pixels wide."""
    return max(1, pixels * width // REFERENCE_WIDTH)


def within(sources: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Pixels at most ``radius`` pixels (Euclidean) from a source pixel.

    Computed on blocks of ``STEP`` pixels, so a source counts for its whole block (up to
    three pixels of extra reach) and the contour is exact to a block. Sources are pooled with
    ``any``, so no island of a pixel or two is lost.
    """
    height, width = sources.shape
    rows, columns = -(-height // STEP), -(-width // STEP)
    padded = np.zeros((rows * STEP, columns * STEP), dtype=bool)
    padded[:height, :width] = sources
    pooled = padded.reshape(rows, STEP, columns, STEP).any(axis=(1, 3))
    del padded
    limit = radius // STEP
    near = euclidean_distance(pooled, limit + 1) <= EIGHTHS * limit
    return np.kron(near, np.ones((STEP, STEP), dtype=bool))[:height, :width]


def strip_islands(game_map: Eu5Map, width: int) -> NDArray[np.bool_]:
    """Oceanian land locations lying wholly in the columns before the map seam."""
    labels = game_map.labels
    land = np.array([kind not in NOT_LAND for kind in game_map.classes], dtype=bool)
    tagged = np.array([name == "oceania" for name in game_map.continents], dtype=bool)
    count = len(game_map.keys)
    total = np.bincount(labels.ravel(), minlength=count)
    edge = scaled(STRIP_COLUMNS, width)
    before = np.bincount(labels[:, :edge].ravel(), minlength=count)
    return land & tagged & (total > 0) & (before == total)


def _cut_column(canvas: NDArray[np.bool_], inside_new: NDArray[np.bool_]) -> int:
    """First column at or after the New World's median column that the canvas covers fully."""
    columns = np.flatnonzero(inside_new.any(axis=0))
    start = int(np.median(columns))
    full = np.flatnonzero(canvas.all(axis=0))
    after = full[full >= start]
    if after.size == 0:
        message = "The Atlantic canvas leaves no column to join the Pacific side"
        raise ExpansionError(message)
    return int(after[0])


def _holes(
    canvas: NDArray[np.bool_],
    rolled: NDArray[np.int32],
    land: NDArray[np.bool_],
    islandish: NDArray[np.bool_],
) -> tuple[NDArray[np.bool_], NDArray[np.int64]]:
    """Enclosed non-canvas parts that hold only island locations, and those locations."""
    parts = label_components((~canvas).astype(np.int32))
    outer = np.unique(np.concatenate([parts[0], parts[-1], parts[:, 0], parts[:, -1]]))
    rows, columns = np.nonzero(land[rolled] & ~canvas)
    part, label = parts[rows, columns], rolled[rows, columns]
    enclosed = ~np.isin(part, outer)
    part, label = part[enclosed], label[enclosed]
    if part.size == 0:
        return np.zeros(canvas.shape, dtype=bool), np.zeros(0, dtype=np.int64)
    pairs = np.unique(np.stack([part, label]), axis=1)
    holes = np.unique(pairs[0])
    other = np.unique(pairs[0][~islandish[pairs[1]]])
    fill = np.setdiff1d(holes, other)
    members = pairs[1][np.isin(pairs[0], fill)]
    return np.isin(parts, fill), np.unique(members).astype(np.int64)


def _groups(
    game_map: Eu5Map, rolled: NDArray[np.int32], pinned: NDArray[np.bool_], width: int
) -> tuple[IslandGroup, ...]:
    """Cluster the island locations by closeness and attach their coast zones.

    A coast zone is a small sea zone that touches an island of the group; the vanilla
    islands name theirs ``*_coast``, ``*_bay`` or ``*_point`` and none touches a high sea
    or an ocean zone [V-EXEC 1.4.6, all 113 islands before the seam]. Scripts refer to the
    coast zones, so they stay with their islands.
    """
    near = within(pinned[rolled], scaled(GROUP_PX, width))
    parts = label_components(near.astype(np.int32))
    rows, columns = np.nonzero(pinned[rolled])
    pairs = np.unique(np.stack([rolled[rows, columns], parts[rows, columns]]), axis=1)
    cluster = {int(label): int(part) for label, part in pairs.T.tolist()}
    if len(cluster) != int(np.count_nonzero(pinned)):
        message = "An island location lies in two island groups"
        raise ExpansionError(message)
    count = len(game_map.keys)
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    sizes = np.bincount(game_map.labels.ravel(), minlength=count)
    limit = COAST_ZONE_PX * width * width // (REFERENCE_WIDTH * REFERENCE_WIDTH)
    zones: dict[int, set[int]] = {}
    for first, second in unpack_pairs(adjacency_pairs(game_map.labels, wrap_x=True)):
        for island, zone in ((first, second), (second, first)):
            if island in cluster and sea[zone] and sizes[zone] <= limit:
                zones.setdefault(cluster[island], set()).add(zone)
    members: dict[int, list[int]] = {}
    for label, part in cluster.items():
        members.setdefault(part, []).append(label)
    return tuple(
        IslandGroup(tuple(sorted(labels)), tuple(sorted(zones.get(part, ()))))
        for part, labels in sorted(members.items(), key=lambda item: min(item[1]))
    )


def expansion(
    game_map: Eu5Map,
    rolled: NDArray[np.int32],
    canvas: NDArray[np.bool_],
    inside_new: NDArray[np.bool_],
) -> Expansion:
    """The canvas with the Pacific side added, and the island groups it covers."""
    height, width = rolled.shape
    classes = game_map.classes
    sea = np.array([kind is CellClass.SEA for kind in classes], dtype=bool)
    land = np.array([kind not in NOT_LAND for kind in classes], dtype=bool)
    new_world = np.array([name == "america" for name in game_map.continents], dtype=bool)
    old_water = np.array([name in OLD_WORLD for name in game_map.continents], dtype=bool) & sea
    islandish = np.array([name in ISLAND_TAGS for name in game_map.continents], dtype=bool)
    movable = strip_islands(game_map, width)
    other = ((~new_world & land & ~movable) | old_water)[rolled]
    free = ((sea & ~old_water & ~new_world) | movable)[rolled] & ~within(
        other, scaled(GUARD_PX, width)
    )
    del other
    cut = _cut_column(canvas, inside_new)
    reach = free & within(inside_new, scaled(REACH_PX, width))
    reach[:, cut:] = False
    del free
    open_px = scaled(OPEN_PX, width)
    base = canvas | inside_new | reach
    opened = within(~within(~base, open_px), open_px) & base
    del base
    joined = canvas | inside_new | (reach & opened)
    del reach, opened
    parts = label_components(joined.astype(np.int32))
    main = parts == np.bincount(parts[joined]).argmax()
    del parts
    joined = (joined & main) | inside_new
    del main
    filled, found = _holes(joined, rolled, land & ~new_world, islandish)
    joined |= filled
    pinned = movable.copy()
    pinned[found] = True
    del height
    return Expansion(joined, _groups(game_map, rolled, pinned, width) if pinned.any() else ())
