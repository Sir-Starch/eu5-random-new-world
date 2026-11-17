"""The k-d tree fast path preserves the original NumPy partition's boundary choices."""

# pyright: reportAny=false, reportPrivateUsage=false
from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_biomes import _nearest
from tests.reference.nearest import nearest


@pytest.mark.parametrize("features", [1, 2, 5, 8])
@pytest.mark.parametrize("scale", [1, 3, 10000, 10**12])
def test_tree_neighbours_keep_every_partition_tie(features: int, scale: int) -> None:
    rng = np.random.default_rng(763)
    for count in [1, 2, 7, 31, 100, 317]:
        # Small scales deliberately give many duplicates and boundary ties.
        train = rng.integers(-scale, scale + 1, (count, features), dtype=np.int64)
        query = rng.integers(-scale, scale + 1, (51, features), dtype=np.int64)
        query[: min(20, count)] = train[: min(20, count)]
        for k in sorted({1, min(3, count), min(13, count), count}):
            for block in [query, query[:0], query[::2]]:
                assert np.array_equal(
                    _nearest(train[:, ::-1], block[:, ::-1], k),
                    nearest(train[:, ::-1], block[:, ::-1], k),
                )


def test_boundary_ties_do_not_depend_on_other_query_rows() -> None:
    rng = np.random.default_rng(726)
    train = rng.integers(-1, 2, (1537, 3), dtype=np.int64)
    query = rng.integers(-1, 2, (321, 3), dtype=np.int64)
    expected = nearest(train, query, 13)
    for chunk in [1, 7, 127, 321]:
        actual = np.concatenate(
            [_nearest(train, query[i : i + chunk], 13) for i in range(0, len(query), chunk)]
        )
        assert np.array_equal(actual, expected)
