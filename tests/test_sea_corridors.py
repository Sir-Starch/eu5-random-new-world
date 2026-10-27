"""Water crossings are planned as continuous geometry before sea cells are made."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import sea_corridors
from rnw.sea_corridors import corridor_axes, designed_corridors
from rnw.topology import label_components

if TYPE_CHECKING:
    import pytest


def test_a_wide_ocean_gets_a_straight_crossing_without_changing_land() -> None:
    ocean = np.zeros((300, 500), dtype=np.bool_)
    ocean[10:-10, 10:-10] = True
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    original = ocean.copy()
    result = designed_corridors(ocean, bands, 20)
    assert np.array_equal(ocean, original)
    assert np.any(result)
    assert not np.any(result & ~ocean)
    rows, columns = np.nonzero(result)
    assert rows.max() - rows.min() > 5 * (columns.max() - columns.min())
    parts = label_components(result.astype(np.int32))
    assert np.unique(parts[result]).size == 1
    assert np.array_equal(result, designed_corridors(ocean, bands, 20))


def test_a_crossing_never_paints_land_or_the_existing_current() -> None:
    ocean = np.ones((400, 700), dtype=np.bool_)
    ocean[130:270, 300:400] = False
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    bands[20:40] = ocean[20:40]
    result = designed_corridors(ocean, bands, 20)
    assert not np.any(result & ~ocean)
    assert not np.any(result & bands)


def test_corridor_clipping_is_independent_of_strip_size(monkeypatch: pytest.MonkeyPatch) -> None:
    ocean = np.ones((300, 500), dtype=np.bool_)
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    expected = designed_corridors(ocean, bands, 20)
    monkeypatch.setattr(sea_corridors, "STRIP_ROWS", 7)
    assert np.array_equal(expected, designed_corridors(ocean, bands, 20))


def test_straight_band_gives_each_cell_the_same_geographic_axis() -> None:
    mask = np.zeros((80, 200), dtype=np.bool_)
    mask[35:45, 20:180] = True
    labels = np.zeros(mask.shape, dtype=np.int32)
    labels[:, 100:] = 1
    axes = corridor_axes(mask, labels, {0, 1}, 16, 2)
    assert set(axes) == {0, 1}
    assert axes[0] == axes[1]
    _, east, north = axes[0]
    assert east > 0
    assert north == 0


def test_a_round_junction_does_not_invent_a_single_current_axis() -> None:
    mask = np.zeros((80, 80), dtype=np.bool_)
    mask[20:60, 20:60] = True
    assert not corridor_axes(mask, np.zeros(mask.shape, dtype=np.int32), {0}, 16, 1)


def test_an_elongated_t_junction_does_not_force_its_sideways_arm() -> None:
    mask = np.zeros((200, 300), dtype=np.bool_)
    mask[95:105, 20:280] = True
    mask[50:100, 145:155] = True
    assert not corridor_axes(mask, np.zeros(mask.shape, dtype=np.int32), {0}, 20, 1)
