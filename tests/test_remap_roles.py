"""A remapped place retains the access that vanilla scripts rely on."""

from __future__ import annotations

from dataclasses import replace

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


def test_a_dropped_area_uses_the_area_of_its_geographic_replacements() -> None:
    plan = _plan()
    plan.cells = [replace(cell, area=cell.key + "_area") for cell in plan.cells]
    remap = build_remap(
        [("old_sea", CellClass.SEA, 0, 0)],
        plan,
        np.array([[0, 20], [0, 30], [0, 0], [0, 10]], dtype=np.int64),
        {},
        access=RemapAccess(navigable_keys=frozenset({"old_sea"}), closed_seas=frozenset({2})),
        areas={"lost_area": ["old_sea"]},
    )
    assert remap["lost_area"] == "lane_area"
    script = (
        "area = lost_area trigger = { has_discovered_area = area:lost_area } "
        "areas = { lost_area kept_area lane_area } "
        "discovered_areas = { lost_area lane_area }"
    )
    rewritten, _ = remap_text(script, remap)
    assert "lost_area" not in rewritten
    assert "area = lane_area" in rewritten
    assert "area:lane_area" in rewritten
    assert "areas = {  kept_area lane_area }" in rewritten
    assert "discovered_areas = {  lane_area }" in rewritten


def test_identical_location_and_province_names_keep_their_own_bindings() -> None:
    plan = _plan()
    plan.cells = [replace(cell, area=cell.key + "_area") for cell in plan.cells]
    remap = build_remap(
        [("shared", CellClass.SEA, 0, 0)],
        plan,
        np.array([[0, 20], [0, 30], [0, 0], [0, 10]], dtype=np.int64),
        {"shared": ["shared"]},
        access=RemapAccess(navigable_keys=frozenset({"shared"}), closed_seas=frozenset({2})),
        areas={"lost_area": ["shared"]},
    )
    assert remap["shared"] == "lane"
    assert remap.areas["lost_area"] == "lane_area"
    script = (
        "location = shared waypoints = { shared } "
        "location:shared province:shared province_definition:shared "
        "provinces = { shared } area:lost_area"
    )
    rewritten, _ = remap_text(script, remap)
    assert "location = lane" in rewritten
    assert "waypoints = { lane }" in rewritten
    assert "location:lane " in rewritten
    assert "province:lane_province" in rewritten
    assert "province_definition:lane_province" in rewritten
    assert "provinces = { lane_province }" in rewritten
    assert "area:lane_area" in rewritten


def test_identical_area_and_province_names_use_the_scope() -> None:
    plan = _plan()
    plan.cells = [replace(cell, area=cell.key + "_area") for cell in plan.cells]
    remap = build_remap(
        [("old_sea", CellClass.SEA, 0, 0)],
        plan,
        np.array([[0, 20], [0, 30], [0, 0], [0, 10]], dtype=np.int64),
        {"shared": ["old_sea"]},
        access=RemapAccess(),
        areas={"shared": ["old_sea"]},
    )
    rewritten, _ = remap_text("province:shared area:shared", remap)
    assert rewritten == "province:closed_province area:closed_area"


def test_a_dropped_area_without_any_compatible_location_is_an_error() -> None:
    with pytest.raises(RemapError, match="removed area lost_area"):
        _ = build_remap(
            [],
            _plan(),
            np.zeros((4, 2), dtype=np.int64),
            {},
            access=RemapAccess(),
            areas={"lost_area": ["absent"]},
        )
