"""New World cells: seed-driven coasts, the seam strait and city points (synthetic domains)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

from rnw.model import CellClass
from rnw.newworld import (
    LAND_KINDS,
    SEAM_GAP_PX,
    NewWorld,
    derive_world,
    generate_new_world,
    open_sea,
    stray_strait,
    wobble_borders,
)
from rnw.settings import NewWorldSettings
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

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


def _land_mask(world: NewWorld) -> NDArray[np.bool_]:
    land = np.array([kind in LAND_KINDS for kind in world.classes] + [False])
    return land[world.labels]


def test_land_outline_changes_with_the_seed() -> None:
    """Seeds place different coasts in one domain; a thin arm of the domain stays sea."""
    settings = replace(SMALL, feature_px=240, octaves=5, land_permille=400, coast_margin_px=4)
    domain = np.zeros((300, 600), dtype=bool)
    domain[20:280, 20:400] = True
    domain[140:170, 400:590] = True
    masks = [
        _land_mask(generate_new_world(domain, seed=seed, settings=settings)) for seed in range(1, 5)
    ]
    overlap = [np.count_nonzero(a & b) / np.count_nonzero(a | b) for a, b in combinations(masks, 2)]
    assert np.mean(overlap) < 0.55  # a ramp of feature_px / 3 gave one outline (0.83)
    assert not any(np.any(mask[:, 440:]) for mask in masks)


def test_seam_column_gets_a_strait() -> None:
    """No land lies within the seam gap; land remains on both sides."""
    domain = np.ones((160, 400), dtype=bool)
    world = generate_new_world(domain, seed=3, settings=SMALL, seam=200)
    mask = _land_mask(world)
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


def test_enclosed_sea_gets_a_path_to_the_open_sea() -> None:
    """Water ringing a protected hole that land encloses gets a path to open water."""
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
    path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
    assert path is not None
    assert 20 <= np.count_nonzero(path) <= 30
    water = domain & ~(land & ~path)
    parts = label_components(water.astype(np.int32))
    assert parts[40, 54] == parts[2, 2]
    land[44:75, 58:62] = False
    assert stray_strait(domain, land, shore=shore, open_shore=open_shore) is None


def test_islet_inside_land_keeps_a_strait() -> None:
    """Land generated around a protected islet leaves its sea joined to open water."""
    settings = replace(SMALL, land_permille=700)
    domain = np.ones((240, 240), dtype=bool)
    domain[116:124, 116:124] = False
    world = generate_new_world(domain, seed=5, settings=settings)
    mask = _land_mask(world)
    water = (world.labels >= 0) & ~mask
    parts = label_components(np.where(water, 1, 0).astype(np.int32))
    assert np.count_nonzero(mask) > mask.size // 3  # the islet sits inside a landmass
    ring = parts[112:128, 112:128][water[112:128, 112:128]]
    edge = parts[0, :][water[0, :]]
    assert np.intersect1d(ring, edge).size


def test_a_vanishing_cell_does_not_undo_the_wobble() -> None:
    """A one-pixel cell lost to the displacement is restored; other borders still bend.

    Before generator 0.9.1 one such cell made the whole world keep straight borders.
    """
    labels = np.zeros((160, 240), dtype=np.int32)
    labels[:, 120:] = 1
    labels[80, 119] = 2
    kinds = [CellClass.LAND] * 3
    moved = wobble_borders(labels, kinds, 2)  # seed 2 displaces the one-pixel cell away
    assert not np.array_equal(moved, labels)
    assert int(np.count_nonzero(moved == 2)) == 1
    parts = label_components(moved)
    for cell in range(3):
        assert np.unique(parts[moved == cell]).size == 1
