"""Planar river serialization preserves continuous geography across a world seam."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_rivers import RiverRasterError, _fragment, encode_rivers  # pyright: ignore[reportPrivateUsage]
from rnw.rivers import (
    BODY,
    JOIN,
    NONE,
    SOURCE,
    Rivers,
    flow_classes,
    generate_rivers,
    network_problems,
)
from tests.test_rivers import _valley  # pyright: ignore[reportPrivateUsage]

WIDTHS = (4, 5, 11, 15)


def _validate(codes: np.ndarray, water: np.ndarray, seam: int) -> None:
    # Independent consumer: put the crop at its final world positions, then parse
    # planar components just as the loader does. Boundary terminals are permitted.
    placed = np.roll(codes, -seam, axis=1)
    assert np.all(placed[:, -1] >= 16)
    wet = np.roll(water, -seam, axis=1).copy()
    wet[:, (0, -1)] = True
    role = np.where(placed < 16, BODY, NONE).astype(np.int8)
    role[placed == 0] = SOURCE
    role[placed == 1] = JOIN
    assert not any(network_problems(role, wet).values())


def _fork() -> Rivers:
    role = np.full((30, 48), NONE, dtype=np.int8)
    role[20, 2:45] = BODY
    role[20, 2] = SOURCE
    role[6:20, 22] = BODY
    role[19, 22] = JOIN
    flow = np.zeros(role.shape, dtype=np.int64)
    flow[role != NONE] = 100
    return Rivers(role=role, flow=flow, stats={})


@pytest.mark.parametrize("seam", range(1, 48))
def test_every_cut_of_a_fork_serializes_valid_pieces(seam: int) -> None:
    """Cuts through a source, junction or tributary keep the whole renderable line."""
    rivers = _fork()
    original = rivers.role.copy()
    classes = np.where(original != NONE, 2, -1).astype(np.int8)
    codes, stats = encode_rivers(rivers, classes, WIDTHS, seam=seam)
    water = np.zeros(original.shape, dtype=bool)
    water[:, 45:] = True
    _validate(codes, water, seam)
    assert np.array_equal(rivers.role, original)
    assert np.count_nonzero(codes < 16) + stats["isolated_points"] + stats[
        "boundary_pixels"
    ] == np.count_nonzero(original != NONE)
    assert np.all(codes[(codes < 16) & (codes > 1)] == 11)


@pytest.mark.parametrize("seed", [5, 11, 23])
def test_real_generated_trees_at_many_seam_positions(seed: int) -> None:
    """Meanders, multiple crossings, nested tributaries and their widths survive."""
    land, height, rain = _valley(220, 180)
    rivers = generate_rivers(land, height, rain, seed=seed)
    classes = flow_classes(rivers, (615, 239, 81, 65))
    assert not any(network_problems(rivers.role, ~land).values())
    crossings = 0
    for seam in range(1, land.shape[1], 3):
        codes, stats = encode_rivers(rivers, classes, WIDTHS, seam=seam)
        crossings += stats["cut_networks"]
        _validate(codes, ~land, seam)
        body = (codes > 1) & (codes < 16)
        assert np.array_equal(codes[body], np.array(WIDTHS, dtype=np.uint8)[classes[body]])
        assert np.count_nonzero(codes < 16) + stats["isolated_points"] + stats[
            "boundary_pixels"
        ] == np.count_nonzero(rivers.role != NONE)
    assert crossings > 0


def test_uncut_network_and_inputs_remain_exact() -> None:
    rivers = _fork()
    classes = np.where(rivers.role != NONE, 0, -1).astype(np.int8)
    codes, stats = encode_rivers(rivers, classes, WIDTHS, seam=47)
    expected = np.where(classes >= 0, 4, 255).astype(np.uint8)
    expected[rivers.role == SOURCE] = SOURCE
    expected[rivers.role == JOIN] = JOIN
    assert np.array_equal(codes, expected)
    assert stats == {"cut_networks": 0, "fragments": 0, "isolated_points": 0, "boundary_pixels": 0}


def test_one_pixel_fragment_is_counted_without_inventing_a_line() -> None:
    role = np.full((5, 12), NONE, dtype=np.int8)
    role[2, 2:10] = BODY
    role[2, 2] = SOURCE
    rivers = Rivers(role, np.ones(role.shape, dtype=np.int64), {})
    codes, stats = encode_rivers(
        rivers, np.where(role != NONE, 0, -1).astype(np.int8), WIDTHS, seam=3
    )
    assert codes[2, 2] == 255
    assert codes[2, 3] == SOURCE
    assert stats == {"cut_networks": 1, "fragments": 1, "isolated_points": 0, "boundary_pixels": 1}
    assert rivers.role[2, 2] == SOURCE


def test_invalid_continuous_network_fails_instead_of_dropping_a_river() -> None:
    rivers = _fork()
    rivers.role[20, 2] = BODY
    with pytest.raises(RiverRasterError, match="exactly one source"):
        _ = encode_rivers(
            rivers, np.where(rivers.role != NONE, 0, -1).astype(np.int8), WIDTHS, seam=12
        )


def test_boundary_fork_chooses_a_drawable_start_without_losing_pixels() -> None:
    role = np.full((7, 8), NONE, dtype=np.int8)
    points = {(3, 1), (3, 2), (3, 3), (3, 4), (2, 3)}
    for p in points:
        role[p] = BODY
    role[3, 1] = SOURCE
    rivers = Rivers(role, np.ones(role.shape, dtype=np.int64), {})
    codes = np.where(role != NONE, 4, 255).astype(np.uint8)
    _fragment(codes, rivers, dict.fromkeys(points, 0), dict.fromkeys(points, 0), -1)
    assert set(zip(*np.where(codes < 16), strict=True)) == points
    assert codes[3, 2] == JOIN
    assert codes[3, 1] != SOURCE
    assert np.count_nonzero(codes == SOURCE) == 1


def test_boundary_fork_without_any_drawable_start_still_fails() -> None:
    role = np.full((7, 8), NONE, dtype=np.int8)
    points = {(3, 2), (3, 3), (3, 4), (2, 3)}
    for p in points:
        role[p] = BODY
    role[3, 2] = SOURCE
    rivers = Rivers(role, np.ones(role.shape, dtype=np.int64), {})
    codes = np.where(role != NONE, 4, 255).astype(np.uint8)
    with pytest.raises(RiverRasterError, match="no room"):
        _fragment(codes, rivers, dict.fromkeys(points, 0), dict.fromkeys(points, 0), -1)
