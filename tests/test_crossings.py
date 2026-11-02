"""Real mouths, coastal shortcuts, parallel duplicates and diagonal drawing coordinates."""

# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.crossings import pixels, sections
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.straits import narrow_gaps
from rnw.topology import label_components
from tests.block_worlds import block_world
from tests.crossing_worlds import hourglass


@pytest.mark.parametrize("width", [1, 8, 17, 36])
def test_a_real_flared_mouth_with_a_long_walk_around_it_has_one_crossing(width: int) -> None:
    world = hourglass(width)
    found = sections(world)
    assert len(found) == 1
    assert found[0].squared == (width + 1) ** 2


def test_a_wider_mouth_is_outside_the_crossing_reach() -> None:
    assert sections(hourglass(37)) == []


def test_three_distinct_mouths_remain_three() -> None:
    found = sections(hourglass(8, (200, 400, 600), height=800))
    assert len(found) == 3
    assert sorted((s.start[0] + s.stop[0]) // 2 for s in found) == [200, 400, 600]


def test_a_long_uniform_channel_does_not_receive_crossings_at_its_location_borders() -> None:
    assert sections(block_world(["AAA1BBB"] * 20, block=30)) == []


def test_a_vanilla_width_link_gets_one_link_per_landmass_pair_not_one_per_location() -> None:
    bands = [f"{a * 3}1{b * 3}" for a, b in zip("ACEGI", "BDFHJ", strict=True)]
    world = block_world([row for row in bands for _ in range(6)], block=8)
    assert len(sections(world)) == 1


def test_a_short_coastal_detour_is_not_a_strait() -> None:
    assert sections(block_world(["AAA1BBB", "AAA1BBB", "AAACBBB", "2222222"], block=8)) == []


def test_neighbouring_location_pairs_do_not_draw_parallel_lines_at_one_mouth() -> None:
    world = hourglass(8)
    land = np.array([kind is CellClass.LAND for kind in world.classes])
    water = ~land[world.labels]
    assert len(narrow_gaps(world.labels, water, land, 36)) > 1
    assert len(sections(world)) == 1


def test_a_diagonal_throat_uses_a_short_diagonal_water_only_section() -> None:
    rows, cols = np.indices((240, 240))
    labels = ((rows // 30) * 8 + cols // 30).astype(np.int32)
    along, across = rows - cols, rows + cols - 240
    water = (abs(across) <= np.minimum(100, 8 + abs(along) // 2)) & (abs(along) <= 140)
    labels[water] = 64
    # A diagonal cut can split one square grid cell into two disconnected shores.
    # As in real generation, give each connected fragment its own identity.
    labels = label_components(labels)
    wet = np.zeros(int(labels.max()) + 1, dtype=bool)
    wet[labels.ravel()] = water.ravel()
    kinds = tuple(CellClass.SEA if value else CellClass.LAND for value in wet.tolist())
    world = derive_world(labels, kinds, np.zeros_like(labels))
    found = sections(world)
    assert len(found) == 1
    item = found[0]
    assert item.start[0] != item.stop[0]
    assert item.start[1] != item.stop[1]
    assert item.squared < 14**2
    assert all(world.labels[p] == item.through for p in pixels(item.start, item.stop)[1:-1])


def test_section_selection_is_independent_of_edge_iteration_order() -> None:
    world = hourglass()
    assert sections(world) == sections(replace(world, edges=tuple(reversed(world.edges))))
