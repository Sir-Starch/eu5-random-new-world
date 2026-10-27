"""Closed-ocean identities join across a canvas; land and lanes can split them."""

# NumPy stubs type array construction as Any.
# pyright: reportAny=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.eu5_canvas import Canvas, OceanRemainder, remainder_runs
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_oceans import emitted_cells, plan_oceans
from rnw.geography import Location
from rnw.loc_keys import KeySpace
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.wording import reference

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map


def _map() -> Eu5Map:
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("old_ocean",),
                colors=np.array([0x123456]),
                classes=(CellClass.SEA,),
                continents=("pacific_ocean_continent",),
                ambiguous=np.array([True]),
                labels=np.zeros((10, 20), dtype=np.int32),
            ),
        ),
    )


def _canvas(*, remainders: bool = True) -> Canvas:
    parts = (
        tuple(
            OceanRemainder(0, remainder_runs(np.ones((10, 5), dtype=bool), 0, left), 50)
            for left in (0, 15)
        )
        if remainders
        else ()
    )
    return Canvas(
        0, 5, np.ones((10, 10), dtype=bool), (10, 20), np.array([False]), np.array([True]), parts
    )


def _plan(kinds: tuple[CellClass, ...]) -> Plan:
    return Plan(
        [
            PlannedCell(
                f"new_{n}",
                "name",
                0xAABB00 + n,
                kind,
                f"p{n}",
                "area",
                "region",
                "subcontinent",
                "pacific_ocean_continent",
            )
            for n, kind in enumerate(kinds)
        ]
    )


def _hierarchy() -> dict[str, Location]:
    return {
        "old_ocean": Location(
            "old_ocean", "pacific_ocean_continent", "subcontinent", "region", "area", "province"
        )
    }


def test_closed_water_rejoins_both_retained_halves_as_one_location() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    world = derive_world(labels, (CellClass.SEA,), labels.copy())
    plan = _plan(world.classes)
    oceans = plan_oceans(
        _map(), _canvas(), world, plan, _hierarchy(), frozenset({0}), KeySpace(set())
    )
    plan.oceans = oceans
    assert plan.cells[0].key == "old_ocean"
    assert plan.cells[0].color == 0x123456
    assert oceans.retained == {"old_ocean"}
    assert not oceans.patches
    assert not emitted_cells(plan)


def test_land_separates_named_ocean_without_recolouring_other_water() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[:, 4:6] = 1
    labels[:, 6:] = 2
    world = derive_world(labels, (CellClass.SEA, CellClass.LAND, CellClass.SEA), labels.copy())
    plan = _plan(world.classes)
    canvas = _canvas()
    oceans = plan_oceans(
        _map(), canvas, world, plan, _hierarchy(), frozenset({0, 2}), KeySpace(set())
    )
    plan.oceans = oceans
    assert plan.cells[0].key == "old_ocean"
    assert plan.cells[2].key.startswith("rnw_ocean_")
    assert plan.cells[0].name == plan.cells[2].name == reference("old_ocean")
    assert plan.cells[1].key == "new_1"
    image = np.zeros((10, 20, 3), dtype=np.uint8)
    oceans.paint(image, canvas)
    assert not np.any(image[:, :15])
    assert np.all(np.any(image[:, 15:] != 0, axis=2))
    assert len(emitted_cells(plan)) == 2


def test_closed_cells_connected_through_retained_water_emit_one_identity() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[4:6, :] = 1
    labels[6:] = 2
    world = derive_world(labels, (CellClass.SEA, CellClass.LAND, CellClass.SEA), labels.copy())
    plan = _plan(world.classes)
    oceans = plan_oceans(
        _map(), _canvas(), world, plan, _hierarchy(), frozenset({0, 2}), KeySpace(set())
    )
    assert plan.cells[0].key == plan.cells[2].key == "old_ocean"
    assert not oceans.patches


def test_ocean_consumed_by_land_has_no_reserved_location() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    world = derive_world(labels, (CellClass.LAND,), labels.copy())
    plan = _plan(world.classes)
    oceans = plan_oceans(
        _map(), _canvas(remainders=False), world, plan, _hierarchy(), frozenset(), KeySpace(set())
    )
    assert not oceans.retained
    assert not oceans.extra
    assert plan.cells[0].key == "new_0"


def test_a_lane_separates_closed_water_even_when_it_has_the_same_ocean_parent() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[:, 4:6] = 1
    labels[:, 6:] = 2
    world = derive_world(labels, (CellClass.SEA,) * 3, labels.copy())
    plan = _plan(world.classes)
    _ = plan_oceans(
        _map(), _canvas(), world, plan, _hierarchy(), frozenset({0, 2}), KeySpace(set())
    )
    assert plan.cells[0].key != plan.cells[2].key
    assert plan.cells[1].key == "new_1"


def test_a_tiny_remainder_joins_its_adjacent_navigable_sea() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[5, 0] = 1
    world = derive_world(labels, (CellClass.SEA, CellClass.SEA), labels.copy())
    original = _canvas()
    main = original.ocean_parts[1]
    tiny = OceanRemainder(0, np.array([[5, 4, 5]], dtype=np.int64), 1)
    canvas = Canvas(
        original.roll,
        original.col0,
        original.mask,
        original.shape,
        original.removed,
        original.trimmed,
        (main, tiny),
    )
    plan = _plan(world.classes)
    oceans = plan_oceans(_map(), canvas, world, plan, _hierarchy(), frozenset({0}), KeySpace(set()))
    assert oceans.retained == {"old_ocean"}
    assert not oceans.extra
    assert [(part.pixels, color) for part, color in oceans.patches] == [(1, plan.cells[1].color)]
    assert oceans.stats["ocean_fragments_absorbed"] == 1


def test_tiny_remainder_cannot_join_water_across_land() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[5, 0] = 1
    world = derive_world(labels, (CellClass.SEA, CellClass.LAND), labels.copy())
    original = _canvas()
    tiny = OceanRemainder(0, np.array([[5, 4, 5]], dtype=np.int64), 1)
    canvas = Canvas(
        original.roll,
        original.col0,
        original.mask,
        original.shape,
        original.removed,
        original.trimmed,
        (original.ocean_parts[1], tiny),
    )
    plan = _plan(world.classes)
    oceans = plan_oceans(_map(), canvas, world, plan, _hierarchy(), frozenset({0}), KeySpace(set()))
    assert len(oceans.extra) == 1
    assert oceans.stats["ocean_fragments_absorbed"] == 0


def test_tiny_remainder_can_join_retained_vanilla_sea() -> None:
    labels = np.zeros((10, 10), dtype=np.int32)
    labels[5, 0] = 1
    world = derive_world(labels, (CellClass.SEA, CellClass.LAND), labels.copy())
    game = _map()
    old_labels = game.labels.copy()
    old_labels[5, 3] = 1
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("old_ocean", "nearby_sea"),
                colors=np.array([0x123456, 0x654321]),
                classes=(CellClass.SEA, CellClass.SEA),
                continents=("pacific_ocean_continent",) * 2,
                ambiguous=np.array([True, False]),
                labels=old_labels,
            ),
        ),
    )
    original = _canvas()
    tiny = OceanRemainder(0, np.array([[5, 4, 5]], dtype=np.int64), 1)
    canvas = Canvas(
        original.roll,
        original.col0,
        original.mask,
        original.shape,
        original.removed,
        original.trimmed,
        (original.ocean_parts[1], tiny),
    )
    plan = _plan(world.classes)
    oceans = plan_oceans(game, canvas, world, plan, _hierarchy(), frozenset({0}), KeySpace(set()))
    assert [(part.pixels, color) for part, color in oceans.patches] == [(1, 0x654321)]
