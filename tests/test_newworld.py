"""New World cells: the seam strait and shore-aware city points (synthetic domains)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.model import CellClass
from rnw.newworld import SEAM_GAP_PX, derive_world, generate_new_world, open_channels, open_sea
from rnw.settings import NewWorldSettings
from rnw.topology import distance_from, label_components

SMALL = NewWorldSettings(
    land_permille=450,
    feature_px=96,
    octaves=3,
    persistence_permille=500,
    coast_margin_px=6,
    min_island_px=24,
    min_lake_px=8,
    max_lake_px=400,
    location_px=14,
    sea_zone_px=40,
    min_cell_px=30,
    min_sea_cell_px=60,
    wasteland_permille=90,
    province_size=6,
    ocean_band_px=32,
)


def test_seam_column_gets_a_strait() -> None:
    """No land lies within the seam gap; land remains on both sides."""
    domain = np.ones((160, 400), dtype=bool)
    world = generate_new_world(domain, seed=3, settings=SMALL, seam=200)
    land = np.array([kind in {CellClass.LAND, CellClass.WASTELAND} for kind in world.classes])
    mask = land[world.labels] & (world.labels >= 0)
    assert not np.any(mask[:, 200 - SEAM_GAP_PX : 200 + SEAM_GAP_PX])
    assert np.any(mask[:, :200])
    assert np.any(mask[:, 200:])
    plain = generate_new_world(domain, seed=3, settings=SMALL)
    assert not np.array_equal(plain.labels, world.labels)


def test_city_points_move_away_from_the_shore() -> None:
    """A coastal land cell's point sits farther inland than its middle; sea keeps the middle."""
    labels = np.zeros((41, 90), dtype=np.int32)
    labels[:, 10:50] = 1
    labels[:, 50:] = 2
    kinds = (CellClass.SEA, CellClass.LAND, CellClass.LAND)
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    row, column = world.interior[1].tolist()
    assert labels[row, column] == 1
    assert column > 32  # the cell's middle column is 29-30
    assert world.interior[0].tolist()[1] < 10


def test_enclosed_sea_gets_a_strait_to_the_open_sea() -> None:
    """Water ringing a protected hole that land encloses is joined to open water."""
    domain = np.ones((80, 120), dtype=bool)
    domain[36:44, 56:64] = False
    domain[0:3, 100:103] = False  # a protected corner must not seed the search
    land = np.ones((80, 120), dtype=bool)
    land[:6, :] = land[-6:, :] = False
    land[:, :6] = land[:, -6:] = False
    land[32:48, 52:68] = False
    land &= domain
    shore = distance_from(~domain, 6, octagonal=True) < 6
    open_shore = distance_from(open_sea(domain), 6, octagonal=True) < 6
    opened = open_channels(domain, land, shore=shore, open_shore=open_shore, width=6)
    water = domain & ~opened
    parts = label_components(water.astype(np.int32))
    assert parts[40, 54] == parts[2, 2]
    assert np.count_nonzero(land & ~opened) < 400
    assert np.array_equal(open_channels(domain, opened, shore=shore, open_shore=open_shore,
                                        width=6), opened)  # fmt: skip
