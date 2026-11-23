"""EU5 river encoding is lossless and refuses channels at the display divide."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_rivers import (
    RiverRasterError,
    encode_rivers,
    sourceless_rivers,
    watershed_spans,
)
from rnw.rivers import BODY, JOIN, NONE, SOURCE, Rivers

WIDTHS = (4, 5, 11, 15)


def _fork() -> Rivers:
    role = np.full((30, 48), NONE, dtype=np.int8)
    role[20, 2:45] = BODY
    role[20, 2] = SOURCE
    role[6:20, 22] = BODY
    role[19, 22] = JOIN
    flow = np.zeros(role.shape, dtype=np.int64)
    flow[role != NONE] = 100
    return Rivers(role=role, flow=flow, stats={})


@pytest.mark.parametrize("seam", [0, 1, 47, 48, 60])
def test_uncut_network_and_inputs_remain_exact(seam: int) -> None:
    rivers = _fork()
    original = rivers.role.copy()
    classes = np.where(original != NONE, 2, -1).astype(np.int8)
    codes, stats = encode_rivers(rivers, classes, WIDTHS, seam=seam)
    expected = np.where(classes >= 0, 11, 255).astype(np.uint8)
    expected[original == SOURCE] = SOURCE
    expected[original == JOIN] = JOIN
    assert np.array_equal(codes, expected)
    assert np.array_equal(rivers.role, original)
    assert not any(stats.values())


@pytest.mark.parametrize("seam", range(2, 46))
def test_crossing_or_touching_the_closed_boundary_fails_without_cutting(seam: int) -> None:
    rivers = _fork()
    original = rivers.role.copy()
    with pytest.raises(RiverRasterError, match="closed watershed boundary"):
        _ = encode_rivers(
            rivers, np.where(original != NONE, 0, -1).astype(np.int8), WIDTHS, seam=seam
        )
    assert np.array_equal(rivers.role, original)


def test_width_classes_must_describe_the_same_network() -> None:
    rivers = _fork()
    classes = np.where(rivers.role != NONE, 0, -1).astype(np.int8)
    classes[20, 10] = -1
    with pytest.raises(RiverRasterError, match="exactly the planned"):
        _ = encode_rivers(rivers, classes, WIDTHS, seam=47)


@pytest.mark.parametrize(
    ("seam", "expected"),
    [(0, ((1, 12),)), (1, ((2, 12),)), (5, ((0, 4), (6, 12))), (12, ((0, 11),)), (20, ((0, 12),))],
)
def test_domain_bounds_close_only_world_edge_channel_samples(
    seam: int, expected: tuple[tuple[int, int], ...]
) -> None:
    assert watershed_spans(12, seam) == expected


def test_a_channel_cut_from_its_source_is_found_whole() -> None:
    """A vanilla river whose headwaters were replaced leaves a remainder the loader cannot walk."""
    sea, land = 254, 255
    rivers = np.full((12, 20), land, dtype=np.uint8)
    rivers[1:11, 2] = 4  # reaches the first and last rows' neighbours, with its source
    rivers[1, 2] = 0
    rivers[5, 6:10] = 4  # a remainder: no source
    rivers[6, 9] = 2
    rivers[0:12, 15] = 4  # runs through the first and last rows: not judged
    rivers[3, 12] = sea
    found = sourceless_rivers(rivers, classes=16)
    assert found.sum() == 5
    assert found[5, 6:10].all()
    assert found[6, 9]
    assert not found[:, 2].any()
    assert not found[:, 15].any()
