"""Connected, compatible impassable land is one indivisible location.

Physical samples stay separate for relief, climate and drainage. The administrative
graph contracts them before partitioning, so a province cannot cut a wasteland in
two. Compatibility includes every biome attribute: merging never paints a different
climate, vegetation or topography over part of a location.
"""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rnw.model import CellClass

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np
    from numpy.typing import NDArray

    from rnw.newworld import NewWorld


@dataclass(frozen=True, slots=True, eq=False)
class LocationUnits:
    """A representative per physical cell, with the contracted graph's centres."""

    owner: tuple[int, ...]
    members: tuple[tuple[int, ...], ...]
    centres: NDArray[np.int64]
    edges: tuple[tuple[int, int], ...]


def location_units(world: NewWorld, attributes: Sequence[tuple[str, ...]]) -> LocationUnits:
    """Union only touching wastelands with identical attributes; ties by lowest cell."""
    count = len(world.classes)
    if len(attributes) != count:
        message = "Every physical cell needs a compatibility signature"
        raise ValueError(message)
    parent = list(range(count))

    def root(cell: int) -> int:
        while parent[cell] != cell:
            parent[cell] = parent[parent[cell]]
            cell = parent[cell]
        return cell

    for first, second in world.edges:
        if (
            world.classes[first] is CellClass.WASTELAND
            and world.classes[second] is CellClass.WASTELAND
            and attributes[first] == attributes[second]
        ):
            a, b = root(first), root(second)
            parent[max(a, b)] = min(a, b)
    owner = tuple(root(cell) for cell in range(count))
    members: list[list[int]] = [[] for _ in range(count)]
    for cell, unit in enumerate(owner):
        members[unit].append(cell)
    centres = world.centroids.copy()
    for unit, cells in enumerate(members):
        if len(cells) > 1:
            weights = world.pixels[cells]
            centres[unit] = (world.centroids[cells] * weights[:, None]).sum(axis=0) // weights.sum()
    edges = tuple(
        sorted(
            {
                (min(owner[a], owner[b]), max(owner[a], owner[b]))
                for a, b in world.edges
                if owner[a] != owner[b]
            }
        )
    )
    return LocationUnits(owner, tuple(tuple(cells) for cells in members), centres, edges)
