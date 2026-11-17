"""Geographic role mapping before batched exact nearest-neighbour queries."""

# pyright: reportAny=false
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_remap import FAMILY, GeographicRemap, RemapAccess, RemapError

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_newworld import Plan
    from rnw.model import CellClass


def build_remap(  # noqa: PLR0913 - geographic levels share their location bindings.
    removed: list[tuple[str, CellClass, int, int]],
    plan: Plan,
    centres: NDArray[np.int64],
    provinces: dict[str, list[str]],
    *,
    access: RemapAccess,
    areas: dict[str, list[str]] | None = None,
) -> GeographicRemap:
    """Map removed location (and province) keys to generated keys.

    ``removed`` holds (key, class, row, column) in the same coordinates as ``centres``,
    which gives each generated cell's centre. ``provinces`` lists each removed province's
    locations in definition order. Removed ports require a generated port, and
    passable water requires passable water. These are geographic roles shared by
    every script reference, including expedition waypoints and their callbacks.
    """
    remap: dict[str, str] = {}
    by_family: dict[frozenset[CellClass], NDArray[np.int64]] = {}
    for family in set(FAMILY.values()):
        members = [i for i, cell in enumerate(plan.cells) if cell.kind in family]
        by_family[family] = np.array(members, dtype=np.int64)
    for key, kind, row, column in removed:
        pool = by_family[FAMILY[kind]]
        if key in access.port_keys:
            pool = np.array([i for i in pool.tolist() if i in access.port_cells], dtype=np.int64)
        elif key in access.navigable_keys:
            pool = np.array(
                [i for i in pool.tolist() if i not in access.closed_seas], dtype=np.int64
            )
        if not pool.size:
            message = f"No generated replacement preserves the geographic role of {key}"
            raise RemapError(message)
        delta = centres[pool] - np.array([row, column], dtype=np.int64)
        best = int(pool[int(np.argmin((delta * delta).sum(axis=1)))])
        remap[key] = plan.cells[best].key
    province_of = {cell.key: cell.province for cell in plan.cells}
    province_remap: dict[str, str] = {}
    for province, keys in provinces.items():
        for key in keys:
            if key in remap:
                province_remap[province] = province_of[remap[key]]
                break
    area_of = {cell.key: cell.area for cell in plan.cells}
    area_remap: dict[str, str] = {}
    for area, members in (areas or {}).items():
        destinations = Counter(area_of[remap[key]] for key in members if key in remap)
        if not destinations:
            message = f"No generated replacement for removed area {area}"
            raise RemapError(message)
        area_remap[area] = min(destinations, key=lambda name: (-destinations[name], name))
    return GeographicRemap(remap, province_remap, area_remap)
