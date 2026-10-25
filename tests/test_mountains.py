"""Mountain detail is continuous across bands and independent of location identities."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_mountains import Mountain, MountainRelief, mountain_relief
from rnw.terrain_tiles import LayerFormat

if TYPE_CHECKING:
    from numpy.typing import NDArray


def ridge() -> NDArray[np.uint16]:
    rows, columns = np.indices((64, 64))
    return (np.maximum(0, 30 - np.abs(columns - 32) - np.abs(rows - 32) // 3) * 1900).astype(
        np.uint16
    )


def test_a_rotated_range_samples_identically_in_arbitrary_bands_and_columns() -> None:
    field = MountainRelief((ridge(),), (Mountain(70, 100, 90, 0, 1), Mountain(120, 125, 90, 0, 0)))
    whole = field.sample((10, 20), (160, 190))
    assert int(whole.max()) > 8000
    assert np.all(whole >= 0)
    rows = np.concatenate(
        [field.sample((10, top), (min(17, 180 - top), 190)) for top in range(20, 180, 17)]
    )
    columns = np.concatenate(
        [field.sample((left, 20), (160, min(23, 200 - left))) for left in range(10, 200, 23)],
        axis=1,
    )
    assert np.array_equal(whole, rows)
    assert np.array_equal(whole, columns)
    assert np.count_nonzero(whole[:, :8]) == 0
    assert np.array_equal(field.sources[0], ridge())


@dataclass
class Sources:
    size: int = 1024

    def layer(self, decal: str, kind: str) -> tuple[LayerFormat, NDArray[np.uint16]]:
        del decal, kind
        a = np.zeros((self.size, self.size), dtype=np.uint16)
        a[self.size // 4 : 3 * self.size // 4, self.size // 4 : 3 * self.size // 4] = 40000
        return LayerFormat(self.size, self.size, "<u2"), a


def test_placement_follows_relief_with_stable_seed_and_refuses_changed_sources() -> None:
    elevation = np.zeros((160, 240), dtype=np.int32)
    elevation[35:125, 30:210] = 22000
    first = mountain_relief(Sources(), elevation, seed=73, column0=0)
    assert first.placements
    assert first.placements == mountain_relief(Sources(), elevation, seed=73, column0=0).placements
    assert first.placements != mountain_relief(Sources(), elevation, seed=74, column0=0).placements
    assert all(elevation[s.row // 2, s.column // 2] >= 14000 for s in first.placements)
    assert not mountain_relief(Sources(), elevation * 0, seed=73, column0=0).placements
    with pytest.raises(ValueError, match="1024"):
        _ = mountain_relief(Sources(64), elevation, seed=73, column0=0)
