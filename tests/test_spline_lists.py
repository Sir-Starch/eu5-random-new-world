"""Native tagged lists preserve records, point bits and the first structural error."""

# NumPy fixture arrays have broad scalar stubs.
# pyright: reportAny=false
from __future__ import annotations

import struct
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.splnet import POINT_FLAG, SplineNetwork, parse, serialize, strip_id
from tests.reference.spline_lists import parse as reference

if TYPE_CHECKING:
    from collections.abc import Callable


def _fixture(*, exceptional: bool = False) -> bytes:
    xy = np.array([[1.5, 2.5], [8.5, 4.5], [12.5, 9.5]], dtype=np.float32)
    if exceptional:
        xy = (
            np.array([0x80000000, 1, 0x7F800000, 0x7FC00011, 0, 0xFFC00003], dtype=np.uint32)
            .view(np.float32)
            .reshape(3, 2)
        )
    return serialize(
        SplineNetwork(
            anchors=np.array([1, 2, 3], dtype=np.int64),
            anchor_xy=xy,
            point_xy=np.array([[4.5, 4.5], [6.5, 3.5], [10.5, 7.5]], dtype=np.float32),
            segments=((1, POINT_FLAG + 4, POINT_FLAG + 5, 2), (3, POINT_FLAG + 6, 2)),
            strips={strip_id(1, 2): (0,), strip_id(2, 3): (1,), strip_id(1, 3): (0, 1)},
        )
    )


def _outcome(reader: Callable[[bytes], SplineNetwork], data: bytes) -> object:
    try:
        network = reader(data)
    except ValueError as error:
        return type(error), str(error)
    return (
        network.anchors.tobytes(),
        network.anchor_xy.tobytes(),
        network.point_xy.tobytes(),
        network.segments,
        tuple(network.strips.items()),
    )


@pytest.mark.parametrize("exceptional", [False, True])
def test_native_lists_keep_the_records_and_float_bits(*, exceptional: bool) -> None:
    data = _fixture(exceptional=exceptional)
    assert _outcome(parse, data) == _outcome(reference, data)
    assert serialize(parse(data)) == data


def test_every_truncation_has_the_original_first_error() -> None:
    data = _fixture()
    for stop in range(len(data)):
        cut = data[:stop]
        assert _outcome(parse, cut) == _outcome(reference, cut), stop


def test_mutated_tokens_counts_and_ids_keep_the_original_first_error() -> None:
    data = _fixture()
    for index in range(len(data)):
        for mask in (1, 255):
            changed = bytearray(data)
            changed[index] ^= mask
            modified = bytes(changed)
            assert _outcome(parse, modified) == _outcome(reference, modified), (index, mask)


@pytest.mark.parametrize("offset", [18, 24, 30])
@pytest.mark.parametrize("count", [-1, -2, 0, 2**31 - 1])
def test_untrusted_counts_do_not_allocate_from_declared_size(offset: int, count: int) -> None:
    data = bytearray(_fixture())
    struct.pack_into("<i", data, offset, count)
    raw = bytes(data)
    assert _outcome(parse, raw) == _outcome(reference, raw)


def test_lists_are_independent_during_concurrent_reads() -> None:
    data = _fixture()
    expected = _outcome(reference, data)
    with ThreadPoolExecutor(4) as pool:
        assert all(result == expected for result in pool.map(_parse_outcome, [data] * 64))


def _parse_outcome(data: bytes) -> object:
    return _outcome(parse, data)
