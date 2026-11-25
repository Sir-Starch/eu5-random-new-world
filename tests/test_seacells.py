"""Compact sea cells (epoch 64, ``epoch.COMPACT_SEAS``): water divided into even, compact pieces."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import epoch, newworld, seacells
from rnw.model import CellClass
from rnw.ports import ForeignCoast, served, settle_seas
from rnw.synth import jittered_sites
from rnw.topology import label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

SPACING = 60
TYPICAL = SPACING * SPACING


def _partition(ocean: NDArray[np.bool_], key: int = 5) -> NDArray[np.int32]:
    return seacells.partition(ocean, key, spacing=SPACING)


def _sea_with_a_shore() -> NDArray[np.bool_]:
    """Open sea of 600 x 720 pixels under a coast that runs along its north edge."""
    ocean = np.ones((600, 720), dtype=np.bool_)
    ocean[:90] = False
    ocean[90:140, 200:330] = False
    return ocean


def test_the_switch_is_part_of_the_epoch_table() -> None:
    assert epoch.SWITCHES["COMPACT_SEAS"] == epoch.COMPACT_SEAS == 64


def test_every_water_pixel_is_in_a_cell_and_no_land_is() -> None:
    ocean = _sea_with_a_shore()
    labels = _partition(ocean)
    assert np.array_equal(labels >= 0, ocean)


def test_cells_are_of_one_size() -> None:
    ocean = _sea_with_a_shore()
    labels = _partition(ocean)
    parts = np.where(ocean, label_components(labels), -1).astype(np.int32)
    areas = np.bincount(parts[parts >= 0])
    areas = areas[areas > 0]
    assert len(areas) > 60
    assert np.percentile(areas, 10) >= 0.5 * TYPICAL
    assert np.percentile(areas, 90) <= 1.6 * TYPICAL
    assert int(areas.max()) <= 2 * TYPICAL


def test_the_cells_along_a_coast_lie_in_a_row_that_follows_it() -> None:
    """The coastal band is a row of cells that touch the shore, the next row none of it."""
    ocean = _sea_with_a_shore()
    labels = _partition(ocean)
    shore = np.zeros_like(ocean)
    shore[1:] |= ~ocean[:-1] & ocean[1:]
    row = set(np.unique(labels[shore & (np.arange(600)[:, None] == 90)]).tolist())
    # Every pixel of the straight stretch of the shore is in one of a handful of cells in a row
    # (the coast is 720 pixels long, a cell is a good deal narrower than that).
    assert 4 <= len(row) <= 14
    far = labels[300:400, 300:400]
    assert not (set(np.unique(far).tolist()) & row)


def test_a_strait_is_a_cell_of_its_own_and_no_cell_reaches_through_it() -> None:
    ocean = np.zeros((260, 600), dtype=np.bool_)
    ocean[20:240, 20:280] = True
    ocean[20:240, 320:580] = True
    ocean[120:134, 280:320] = True  # a strait fourteen pixels wide
    labels = _partition(ocean)
    west = set(np.unique(labels[20:240, 20:270]).tolist())
    east = set(np.unique(labels[20:240, 330:580]).tolist())
    strait = set(np.unique(labels[121:133, 285:315]).tolist())
    assert not west & east
    assert not strait & (west | east)


def test_a_strait_is_detected_even_when_the_mouths_have_another_route() -> None:
    ocean = np.zeros((320, 600), dtype=np.bool_)
    ocean[20:300, 20:280] = True
    ocean[20:300, 320:580] = True
    ocean[20:100, 280:320] = True
    ocean[200:214, 280:320] = True
    flags = seacells.layout(ocean, SPACING)
    assert flags.neck[207 // flags.step, 300 // flags.step]
    assert not flags.neck[55 // flags.step, 300 // flags.step]


def test_no_cell_reaches_through_a_strait_after_the_small_pieces_are_folded() -> None:
    """The whole cut of the export (``newworld._sea_cells``, with its smallest cell and the
    folding of slivers) keeps the water on either side of a narrow strait in cells of its own."""
    ocean = np.zeros((260, 600), dtype=np.bool_)
    ocean[20:240, 20:280] = True
    ocean[20:240, 320:580] = True
    ocean[120:134, 280:320] = True
    for smallest in (500, 2000):
        labels = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
            ocean,
            key=5,
            spacing=SPACING,
            smallest=smallest,
            bands=None,
            algorithm=epoch.COMPACT_SEAS,
        )
        west = set(np.unique(labels[20:240, 20:270]).tolist())
        east = set(np.unique(labels[20:240, 330:580]).tolist())
        assert not west & east, smallest
        assert np.array_equal(labels >= 0, ocean)


def test_open_sea_uses_rectangles_even_with_an_off_centre_island() -> None:
    ocean = np.ones((420, 480), dtype=np.bool_)
    rows, columns = np.ogrid[:420, :480]
    ocean &= (rows - 140) ** 2 + (columns - 144) ** 2 > 11**2
    empty_sea = _partition(np.ones_like(ocean))
    labels = _partition(ocean)
    assert np.array_equal(labels[ocean], empty_sea[ocean])
    assert (labels[~ocean] == -1).all()
    cell = labels[120, 120]
    assert np.array_equal(labels == cell, ocean & (rows // 60 == 2) & (columns // 60 == 2))


def test_a_small_island_is_no_shore_for_the_bands() -> None:
    """A small island does not affect the surrounding water's depth bands."""
    ocean = np.ones((420, 480), dtype=np.bool_)
    rows, columns = np.ogrid[:420, :480]
    ocean &= (rows - 210) ** 2 + (columns - 240) ** 2 > 14**2
    flags = seacells.layout(ocean, SPACING)
    step = flags.step
    assert flags.water[210 // step, 240 // step]
    assert np.array_equal(flags.depth, seacells.layout(np.ones_like(ocean), SPACING).depth)


def test_a_cluster_shares_one_grid_cell_and_each_island_can_have_a_port() -> None:
    rows, columns = np.ogrid[:240, :300]
    dry = np.full((240, 300), -1, dtype=np.int32)
    for land, (row, column) in enumerate(((132, 132), (141, 153), (158, 137), (161, 159))):
        dry[(rows - row) ** 2 + (columns - column) ** 2 <= 5**2] = land
    ocean = dry < 0
    cut = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=5, spacing=SPACING, smallest=500, bands=None, algorithm=epoch.COMPACT_SEAS
    )
    labels = np.where(ocean, cut + 4, dry).astype(np.int32)
    classes = (CellClass.LAND,) * 4 + (CellClass.SEA,) * (int(cut.max()) + 1)
    world = newworld.derive_world(labels, classes, np.zeros_like(labels))
    settled = settle_seas(world, dissolve=True)
    ports = served(settled.world, ForeignCoast())
    assert ports.unserved == ()
    assert set(ports.port) == set(range(4))
    assert len(set(ports.port.values())) == 1
    assert settled.merged == 0
    sea = ports.port[0]
    assert np.array_equal(
        settled.world.labels == sea, ocean & (rows // 60 == 2) & (columns // 60 == 2)
    )


def test_a_large_island_is_a_shore_the_cells_follow() -> None:
    ocean = np.ones((520, 560), dtype=np.bool_)
    ocean[160:360, 160:400] = False
    flags = seacells.layout(ocean, SPACING)
    assert not flags.water[250 // flags.step, 250 // flags.step]
    labels = _partition(ocean)
    rows, columns = np.ogrid[:520, :560]
    shore = ocean & (
        (np.abs(rows - 159.5) <= 3) & (columns >= 157) & (columns <= 402)
        | (np.abs(rows - 360.5) <= 3) & (columns >= 157) & (columns <= 402)
        | (np.abs(columns - 159.5) <= 3) & (rows >= 157) & (rows <= 362)
        | (np.abs(columns - 400.5) <= 3) & (rows >= 157) & (rows <= 362)
    )
    # The island is 900 pixels round, so a row of cells of a side of about sixty pixels follows it.
    assert np.unique(labels[shore]).size >= 8


def test_a_four_location_island_can_cross_an_ordinary_grid_edge() -> None:
    dry = np.full((360, 420), -1, dtype=np.int32)
    dry[137:149, 154:187] = 0
    dry[137:149, 187:219] = 1
    dry[149:160, 154:187] = 2
    dry[149:160, 187:219] = 3
    ocean = dry < 0
    labels = _partition(ocean)
    empty = _partition(np.ones_like(ocean))
    assert np.array_equal(labels[ocean], empty[ocean])
    world = newworld.derive_world(
        np.where(ocean, labels + 4, dry).astype(np.int32),
        (CellClass.LAND,) * 4 + (CellClass.SEA,) * (int(labels.max()) + 1),
        np.zeros_like(labels),
    )
    settled = settle_seas(world, dissolve=True)
    ports = served(settled.world, ForeignCoast())
    assert settled.world is world
    assert not ports.unserved
    assert len(set(ports.port.values())) == 2


def test_the_same_water_is_divided_the_same_way_twice() -> None:
    ocean = _sea_with_a_shore()
    assert np.array_equal(_partition(ocean), _partition(ocean))


def test_pinned_sites_keep_their_place() -> None:
    ocean = np.ones((300, 420), dtype=np.bool_)
    rows, columns = jittered_sites(5, ocean.shape, SPACING)
    pin_rows = np.array([150, 150], dtype=np.int64)
    pin_columns = np.array([100, 300], dtype=np.int64)
    labels = seacells._draw(  # pyright: ignore[reportPrivateUsage]
        ocean,
        seacells.layout(ocean, SPACING),
        rows,
        columns,
        pinned_rows=pin_rows,
        pinned_columns=pin_columns,
        spacing=SPACING,
    )
    assert labels[150, 100] == 0
    assert labels[150, 300] == 1


def test_the_previous_epoch_still_divides_the_sea_with_straight_distance() -> None:
    """The old way (nearest site in a straight line) is kept for the epochs before 64."""
    ocean = np.ones((200, 260), dtype=np.bool_)
    ocean[:, 100:130] = False
    ocean[90:110, 100:130] = True
    old = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=9, spacing=40, smallest=30, bands=None, algorithm=epoch.COMPACT_SEAS - 1
    )
    new = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=9, spacing=40, smallest=30, bands=None, algorithm=epoch.COMPACT_SEAS
    )
    current = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=9, spacing=40, smallest=30, bands=None
    )
    assert np.array_equal(new, current)
    assert not np.array_equal(old, new)
    assert np.array_equal(old >= 0, ocean)
    assert np.array_equal(new >= 0, ocean)
