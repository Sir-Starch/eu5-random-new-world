"""A remapped place retains the access that vanilla scripts rely on."""

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_remap import RemapAccess, RemapError, build_remap, remap_text
from rnw.model import CellClass


def _plan() -> Plan:
    return Plan(
        [
            PlannedCell(key, key, i + 1, kind, key + "_province", "a", "r", "s", "c")
            for i, (key, kind) in enumerate(
                (
                    ("inland", CellClass.LAND),
                    ("harbour", CellClass.LAND),
                    ("closed", CellClass.SEA),
                    ("lane", CellClass.SEA),
                )
            )
        ]
    )


def test_a_removed_port_maps_to_a_port_despite_a_closer_inland_cell() -> None:
    remap = build_remap(
        [("landfall", CellClass.LAND, 0, 0)],
        _plan(),
        np.array([[0, 0], [0, 10], [0, 1], [0, 20]], dtype=np.int64),
        {"old_province": ["landfall"]},
        access=RemapAccess(port_keys=frozenset({"landfall"}), port_cells=frozenset({1})),
    )
    assert remap == {"landfall": "harbour", "old_province": "harbour_province"}
    script = "waypoints = { landfall } on_arrive = { this = location:landfall }"
    rewritten, _ = remap_text(script, remap)
    assert "waypoints = { harbour }" in rewritten
    assert "this = location:harbour" in rewritten


def test_passable_water_cannot_be_rebound_to_a_closer_closed_ocean() -> None:
    remap = build_remap(
        [("current", CellClass.SEA, 0, 0), ("deep_basin", CellClass.SEA, 0, 0)],
        _plan(),
        np.array([[0, 20], [0, 30], [0, 0], [0, 10]], dtype=np.int64),
        {},
        access=RemapAccess(navigable_keys=frozenset({"current"}), closed_seas=frozenset({2})),
    )
    assert remap == {"current": "lane", "deep_basin": "closed"}


@pytest.mark.parametrize("kind", [CellClass.LAND, CellClass.SEA])
def test_missing_access_is_an_error_instead_of_an_incompatible_replacement(kind: CellClass) -> None:
    with pytest.raises(RemapError, match="preserves the geographic role"):
        _ = build_remap(
            [("required", kind, 0, 0)],
            _plan(),
            np.zeros((4, 2), dtype=np.int64),
            {},
            access=RemapAccess(
                port_keys=frozenset({"required"}) if kind is CellClass.LAND else frozenset(),
                navigable_keys=frozenset({"required"}) if kind is CellClass.SEA else frozenset(),
                closed_seas=frozenset({2, 3}),
            ),
        )
