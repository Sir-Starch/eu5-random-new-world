"""Compact sea cells (epoch 64, ``epoch.COMPACT_SEAS``): water divided into even, compact pieces."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw import epoch, newworld, seacells
from rnw.model import CellClass
from rnw.ports import ForeignCoast, served, settle_seas
from rnw.synth import seed_sites
from rnw.topology import label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

SPACING = 60
TYPICAL = SPACING * SPACING


def _sites(ocean: NDArray[np.bool_], key: int = 5) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    rows, columns = np.nonzero(seed_sites(key, ocean, SPACING) >= 0)
    return rows.astype(np.int64), columns.astype(np.int64)


def _partition(ocean: NDArray[np.bool_], key: int = 5) -> NDArray[np.int32]:
    rows, columns = _sites(ocean, key)
    return seacells.partition(ocean, rows, columns, pinned=0, spacing=SPACING)


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


def test_a_small_island_lies_inside_one_cell() -> None:
    ocean = np.ones((420, 480), dtype=np.bool_)
    rows, columns = np.ogrid[:420, :480]
    for centre in ((100, 120), (230, 240), (330, 400)):
        ocean &= (rows - centre[0]) ** 2 + (columns - centre[1]) ** 2 > 14**2
    labels = _partition(ocean)
    for centre in ((100, 120), (230, 240), (330, 400)):
        near = (rows - centre[0]) ** 2 + (columns - centre[1]) ** 2 <= 17**2
        assert np.unique(labels[near & ocean]).size == 1, centre


def test_a_small_island_is_no_shore_for_the_bands() -> None:
    """The bands about an island that a cell holds are level, and the disk is not water to them."""
    ocean = np.ones((420, 480), dtype=np.bool_)
    rows, columns = np.ogrid[:420, :480]
    ocean &= (rows - 210) ** 2 + (columns - 240) ** 2 > 14**2
    flags = seacells.layout(ocean, SPACING)
    assert len(flags.islands) == 1
    row, column, reach, shore_radius = flags.islands[0].tolist()
    assert reach >= 14
    assert shore_radius < reach
    step = flags.step
    assert abs(row * step - 210) <= step
    assert abs(column * step - 240) <= step
    assert flags.discs[row, column] == 1
    assert not flags.water[row, column]
    assert flags.depth[flags.discs == 1].min() == flags.depth[flags.discs == 1].max()


def test_close_small_islands_keep_separate_coastal_cells_and_ports() -> None:
    rows, columns = np.ogrid[:240, :300]
    distances = ((rows - 120) ** 2 + (columns - 105) ** 2, (rows - 120) ** 2 + (columns - 135) ** 2)
    radii = (12, 10)
    first, second = (
        distance <= radius**2 for distance, radius in zip(distances, radii, strict=True)
    )
    ocean = ~(first | second)
    cut = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=5, spacing=SPACING, smallest=500, bands=None, algorithm=epoch.COMPACT_SEAS
    )
    labels = np.where(ocean, cut + 2, np.where(first, 0, 1)).astype(np.int32)
    classes = (CellClass.LAND,) * 2 + (CellClass.SEA,) * (int(cut.max()) + 1)
    world = newworld.derive_world(labels, classes, np.zeros_like(labels))
    settled = settle_seas(world, dissolve=True)
    ports = served(settled.world, ForeignCoast())
    assert ports.unserved == ()
    assert ports.port[0] != ports.port[1]
    assert settled.merged == 0
    for land, (distance, radius) in enumerate(zip(distances, radii, strict=True)):
        sea = ports.port[land]
        assert np.all(settled.world.labels[ocean & (distance <= (radius + 1) ** 2)] == sea)
        assert 0.5 * TYPICAL <= settled.world.pixels[sea] <= 1.5 * TYPICAL


def test_a_large_island_is_a_shore_the_cells_follow() -> None:
    ocean = np.ones((520, 560), dtype=np.bool_)
    ocean[160:360, 160:400] = False
    flags = seacells.layout(ocean, SPACING)
    assert len(flags.islands) == 0
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


def test_the_same_water_is_divided_the_same_way_twice() -> None:
    ocean = _sea_with_a_shore()
    assert np.array_equal(_partition(ocean), _partition(ocean))


def test_pinned_sites_keep_their_place() -> None:
    ocean = np.ones((300, 420), dtype=np.bool_)
    rows, columns = _sites(ocean)
    pin_rows = np.array([150, 150], dtype=np.int64)
    pin_columns = np.array([100, 300], dtype=np.int64)
    rows = np.concatenate((pin_rows, rows))
    columns = np.concatenate((pin_columns, columns))
    labels = seacells.partition(ocean, rows, columns, pinned=2, spacing=SPACING)
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
