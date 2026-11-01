"""Water crossings are planned as continuous geometry before sea cells are made."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import sea_corridors
from rnw.sea_corridors import clear_of_corridors, corridor_paths, corridor_sites, draw_corridors
from rnw.topology import label_components

if TYPE_CHECKING:
    import pytest
    from numpy.typing import NDArray


def designed_corridors(
    ocean: NDArray[np.bool_],
    bands: NDArray[np.bool_],
    spacing: int,
    *,
    domain: NDArray[np.bool_] | None = None,
) -> NDArray[np.bool_]:
    """The band of every corridor, one sea-cell width wide."""
    return draw_corridors(corridor_paths(ocean, bands, spacing, domain=domain), ocean, spacing)


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


def test_a_crossing_never_paints_land_and_does_not_mutate_source_currents() -> None:
    ocean = np.ones((400, 700), dtype=np.bool_)
    ocean[130:270, 300:400] = False
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    bands[20:40] = ocean[20:40]
    before = bands.copy()
    result = designed_corridors(ocean, bands, 20)
    assert not np.any(result & ~ocean)
    assert np.array_equal(bands, before)


def test_an_interior_old_current_fragment_does_not_define_a_new_route() -> None:
    ocean = np.ones((300, 500), dtype=np.bool_)
    ocean[10:-10, :10] = False
    ocean[10:-10, -10:] = False
    domain = np.ones(ocean.shape, dtype=np.bool_)
    empty = np.zeros(ocean.shape, dtype=np.bool_)
    old = empty.copy()
    old[90:130, 160:260] = True
    assert np.array_equal(
        designed_corridors(ocean, empty, 20, domain=domain),
        designed_corridors(ocean, old, 20, domain=domain),
    )


def test_a_replacement_boundary_is_not_an_invented_coast() -> None:
    ocean = np.ones((120, 200), dtype=np.bool_)
    empty = np.zeros(ocean.shape, dtype=np.bool_)
    assert not np.any(designed_corridors(ocean, empty, 20, domain=ocean))


def test_corridor_clipping_is_independent_of_strip_size(monkeypatch: pytest.MonkeyPatch) -> None:
    ocean = np.ones((300, 500), dtype=np.bool_)
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    expected = designed_corridors(ocean, bands, 20)
    monkeypatch.setattr(sea_corridors, "STRIP_ROWS", 7)
    assert np.array_equal(expected, designed_corridors(ocean, bands, 20))


def test_a_crossing_has_a_site_every_sea_cell_width_along_its_line() -> None:
    ocean = np.zeros((300, 500), dtype=np.bool_)
    ocean[10:-10, 10:-10] = True
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    paths = corridor_paths(ocean, bands, 20)
    rows, columns = corridor_sites(paths, ocean, 20, 5)
    assert rows.size >= 8
    assert np.all(ocean[rows, columns])
    assert not np.any(clear_of_corridors(rows, columns, paths, 4.0))
    ordered = np.argsort(rows)
    gaps = np.hypot(np.diff(rows[ordered]), np.diff(columns[ordered]))
    assert np.all((gaps > 10) & (gaps < 30))
    again = corridor_sites(paths, ocean, 20, 5)
    assert np.array_equal(rows, again[0])
    assert np.array_equal(columns, again[1])
    other = corridor_sites(paths, ocean, 20, 6)
    assert not (np.array_equal(rows, other[0]) and np.array_equal(columns, other[1]))


def test_sites_keep_clear_of_a_crossing_only_within_the_radius() -> None:
    path = [(10, 10), (10, 110)]
    rows = np.array([10, 18, 31, 10, 10, 60], dtype=np.int64)
    columns = np.array([60, 60, 60, 5, 125, 60], dtype=np.int64)
    clear = clear_of_corridors(rows, columns, [path], 20.0)
    # on the line, 8 px off, 21 px off, past the start (5 px) and past the end (15 px), far
    assert clear.tolist() == [False, False, True, False, False, True]
