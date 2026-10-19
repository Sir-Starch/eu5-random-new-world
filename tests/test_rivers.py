"""Drainage, river networks, size classes and valleys (synthetic terrain)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.rivers import (
    BODY,
    JOIN,
    NONE,
    SOURCE,
    STEP,
    Rivers,
    carve_valleys,
    drainage,
    flow_classes,
    generate_rivers,
    network_problems,
    streams,
)


def _valley(rows: int = 360, columns: int = 280) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Land rising from a sea along the top edge, with a valley down the middle."""
    r, c = np.indices((rows, columns))
    land = r >= 12
    height = np.where(land, 6000 + r * 25 + np.abs(c - columns // 2) * 18, 0)
    rain = np.full((-(-rows // STEP), -(-columns // STEP)), 1000, dtype=np.int64)
    return land, height.astype(np.int64), rain


def test_drainage_reaches_water_from_every_land_cell() -> None:
    """Following downstream links from any land cell ends in water; flow sums rain."""
    land = np.zeros((12, 12), dtype=bool)
    land[2:10, 2:10] = True
    height = np.where(land, 100, 0).astype(np.int64)
    height[5, 5] = 50  # a pit is crossed, not a sink
    tree = drainage(land, height, np.where(land, 1, 0).astype(np.int64), 3)
    for start in np.flatnonzero(land.ravel()).tolist():
        cell, steps = start, 0
        while land.ravel()[cell]:
            cell = int(tree.parent[cell])
            steps += 1
            assert steps < land.size
    outlets = tree.parent[land.ravel()]
    drained = tree.flow[np.unique(outlets[~land.ravel()[outlets]])].sum()
    assert drained == land.sum()


def test_streams_form_a_tree_from_mouths_upstream() -> None:
    """Main streams leave into water; each tributary leaves into an earlier stream."""
    land, height, rain = _valley()
    coarse = land[::STEP, ::STEP]
    tree = drainage(coarse, height[::STEP, ::STEP], np.where(coarse, rain, 0), 5)
    found = streams(tree, 3000, 2)
    assert found
    assert any(stream.parent >= 0 for stream in found)
    owner = {cell: number for number, stream in enumerate(found) for cell in stream.cells}
    for number, stream in enumerate(found):
        assert tree.flow[stream.cells[0]] >= tree.flow[stream.cells[-1]]
        if stream.parent < 0:
            assert not coarse.ravel()[stream.outlet]
        else:
            assert stream.parent < number
            assert owner[stream.outlet] == stream.parent


def test_generated_network_obeys_the_raster_rules() -> None:
    """Rivers in a valley: valid topology, sources and joins, deterministic."""
    land, height, rain = _valley()
    rivers = generate_rivers(land, height, rain, seed=11)
    assert np.array_equal(rivers.role, generate_rivers(land, height, rain, seed=11).role)
    assert not any(network_problems(rivers.role, ~land).values())
    assert np.count_nonzero(rivers.role == SOURCE) >= 1
    assert np.count_nonzero(rivers.role == BODY) > 30
    assert np.all(land[rivers.role == JOIN])
    on_water = (rivers.role != NONE) & ~land
    assert np.count_nonzero(on_water) <= 3 * np.count_nonzero(rivers.role == SOURCE)


def test_network_problems_flag_broken_rasters() -> None:
    """A 2x2 block, a network without a source and a sourceless loop are reported."""
    role = np.full((8, 8), NONE, dtype=np.int8)
    water = np.zeros((8, 8), dtype=bool)
    water[:, 0] = True
    role[3, 1:5] = BODY
    problems = network_problems(role, water)
    assert problems["networks_without_one_source"] == 1
    role[3, 4] = SOURCE
    assert not any(network_problems(role, water).values())
    role[4, 1:3] = BODY
    assert network_problems(role, water)["blocks"] == 1


def test_flow_classes_follow_quantiles_and_valleys_are_carved() -> None:
    """Classes split river pixels by flow; valleys sink rivers but keep the floor."""
    role = np.full((5, 40), NONE, dtype=np.int8)
    role[2, :] = BODY
    flow = np.zeros((5, 40), dtype=np.int64)
    flow[2, :] = np.arange(40)
    classes = flow_classes(Rivers(role=role, flow=flow, stats={}), (500, 250, 250))
    assert classes[2].tolist() == [0] * 20 + [1] * 10 + [2] * 10
    relief = np.full((5, 40), 7000, dtype=np.int64)
    relief[:, 0] = 0
    carved = carve_valleys(relief, classes, depths=(100, 200, 2000), radius_px=2, floor=6000)
    assert carved[2, 5] == 6900
    assert carved[2, 35] == 6000
    assert carved[0, 5] > carved[1, 5] > carved[2, 5]
    assert carved[2, 0] == 0
