"""New World cells: seed-driven coasts, continuous identities and city points."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

from rnw import newworld
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.newworld import (
    LAND_KINDS,
    NewWorld,
    derive_world,
    generate_new_world,
    land_stage,
    open_sea,
    seal_pockets,
    stray_strait,
    unported_cells,
    wobble_borders,
)
from rnw.sea_corridors import corridor_paths, draw_corridors
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
    # A ramp of feature_px / 3 gave one outline (0.83); the water band along the canvas's boundary
    # leaves this small canvas less room (0.55 without it).
    assert np.mean(overlap) < 0.65
    assert not any(np.any(mask[:, 440:]) for mask in masks)


def test_continent_cells_continue_through_the_middle_of_the_canvas() -> None:
    """A canvas has no reserved artificial boundary through its generated land."""
    domain = np.ones((160, 400), dtype=bool)
    world = generate_new_world(domain, seed=3, settings=SMALL)
    mask = _land_mask(world)
    assert np.any(mask[:, 199] & mask[:, 200])
    assert np.any(world.labels[:, 199][mask[:, 199]] == world.labels[:, 200][mask[:, 199]])


def test_polar_contacts_are_narrow_large_and_impassable() -> None:
    """A continent may approach a pole, but cannot fill the whole map edge."""
    domain = np.ones((240, 480), dtype=bool)
    worlds = [generate_new_world(domain, seed=seed, settings=SMALL) for seed in range(8)]
    touching = 0
    for world in worlds:
        land = _land_mask(world)
        interior = [
            int(world.pixels[i])
            for i, kind in enumerate(world.classes)
            if kind in LAND_KINDS and 80 <= world.centroids[i, 0] < 160
        ]
        for row in (0, -1):
            assert np.count_nonzero(land[row]) <= 8 * SMALL.location_px
            ids = np.unique(world.labels[row][land[row]])
            touching += len(ids)
            for index in ids:
                assert world.classes[index] is CellClass.WASTELAND
                assert world.pixels[index] > 2 * np.median(interior)
    assert touching > 0


def test_a_small_canvas_lobe_has_no_reserved_land() -> None:
    """A narrow lobe can be all ocean, or hold seed-driven land."""
    domain = np.zeros((300, 600), dtype=bool)
    domain[20:280, 170:580] = True
    domain[100:200, 20:170] = True
    settings = replace(SMALL, feature_px=160, land_permille=300, coast_margin_px=4)
    areas: list[int] = []
    for seed in range(16):
        land, ocean, lakes, _ = land_stage(domain, seed, settings)
        assert np.array_equal(land | ocean | lakes, domain)
        assert land[:, 170:].any()
        areas.append(int(np.count_nonzero(land[:, :170])))
    assert min(areas) == 0
    assert max(areas) > 0
    assert len(set(areas)) > len(areas) // 2


def test_drawn_land_crosses_the_map_seam_without_a_channel() -> None:
    """A drawn continent is continuous even when its display crosses both map edges."""
    domain = np.ones((160, 400), dtype=bool)
    drawn = np.zeros(domain.shape, dtype=bool)
    drawn[30:130, 60:340] = True
    world = generate_new_world(domain, seed=3, settings=SMALL, drawn=drawn)
    assert np.all(_land_mask(world)[40:120, 190:210])


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


def test_sea_cells_follow_actual_routes_without_moving_the_coast() -> None:
    domain = np.ones((160, 192), dtype=bool)
    bands = np.zeros(domain.shape, dtype=bool)
    bands[35:55, :] = True
    bands[100:120, :] = True
    plain = generate_new_world(domain, seed=3, settings=SMALL)
    world = generate_new_world(domain, seed=3, settings=SMALL, sea_bands=bands)
    assert np.array_equal(_land_mask(world), _land_mask(plain))
    assert np.array_equal(world.elevation, plain.elevation)
    assert np.array_equal(world.labels[_land_mask(world)], plain.labels[_land_mask(plain)])
    ocean = np.array([k is CellClass.SEA for k in world.classes])[world.labels]
    for number, kind in enumerate(world.classes):
        if kind is CellClass.SEA:
            mask = world.labels == number
            assert np.unique(label_components(mask.astype(np.int32))[mask]).size == 1
    assert np.any(ocean)


def test_a_crossing_is_a_chain_of_ordinary_cells_not_a_band_cut_out_of_the_water() -> None:
    ocean = np.zeros((300, 500), dtype=np.bool_)
    ocean[10:-10, 10:-10] = True
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    spacing = 20
    paths = corridor_paths(ocean, bands, spacing)
    assert paths
    labels = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=5, spacing=spacing, smallest=40, bands=bands
    )
    assert np.array_equal(labels >= 0, ocean)
    line = draw_corridors(paths, ocean, 1)
    band = draw_corridors(paths, ocean, spacing)
    chain = np.unique(labels[line])
    assert chain.size >= 5  # about one cell per sea-cell width of the line
    for cell in chain.tolist():
        mask = labels == cell
        assert np.unique(label_components(mask.astype(np.int32))[mask]).size == 1
    # No border of the band's ruled edge: the cells of the chain reach beyond it, and no cell
    # outside the chain lies wholly within it.
    reaching = [cell for cell in chain.tolist() if np.any((labels == cell) & ~band)]
    assert len(reaching) >= chain.size - 2
    inside = [
        cell
        for cell in np.unique(labels[band]).tolist()
        if cell not in chain and not np.any((labels == cell) & ~band)
    ]
    assert not inside


def test_without_a_crossing_the_banded_partition_is_the_plain_one() -> None:
    ocean = np.ones((32, 45), dtype=np.bool_)
    ocean[12:20, 12:18] = False
    bands = np.zeros(ocean.shape, dtype=np.bool_)
    assert not corridor_paths(ocean, bands, 8)
    banded = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=11, spacing=8, smallest=4, bands=bands
    )
    plain = newworld._sea_cells(  # pyright: ignore[reportPrivateUsage]
        ocean, key=11, spacing=8, smallest=4, bands=None
    )
    assert np.array_equal(banded, plain)


def test_land_keeps_a_band_of_water_from_the_canvas_boundary() -> None:
    """No land within a share of the canvas's width of the join with the game's map."""
    domain = np.ones((300, 800), dtype=bool)
    domain[:, :100] = False
    domain[:60, 100:300] = False
    settings = replace(SMALL, feature_px=200, land_permille=350, coast_margin_px=4)
    pad = domain.shape[1] * newworld.EDGE_WATER_PERMILLE // 1000
    assert pad > settings.coast_margin_px
    outside = ~domain
    outside[:, [0, -1]] = True
    for seed in range(1, 4):
        land, _, _, _ = land_stage(domain, seed, settings)
        assert int(distance_from(outside, 4 * pad, octagonal=True)[land].min()) >= pad
        # the share of land of the canvas does not fall because of the band
        assert np.count_nonzero(land) * 1000 >= 0.85 * settings.land_permille * np.count_nonzero(
            domain
        )


def test_land_without_a_way_to_a_port_becomes_wasteland() -> None:
    """Land cells reach a port only through land: walled-in pockets turn into wasteland."""
    kinds = (
        CellClass.SEA,
        CellClass.LAND,  # coastal
        CellClass.LAND,  # joined to the coast through the previous cell
        CellClass.WASTELAND,
        CellClass.LAND,  # behind the wasteland
        CellClass.LAND,
        CellClass.LAKE,
        CellClass.LAND,  # only a lake on its far side
    )
    labels = np.arange(len(kinds), dtype=np.int32).reshape(1, -1)
    world = derive_world(labels, kinds, np.zeros((1, len(kinds)), dtype=np.int32))
    assert unported_cells(world) == [4, 5, 7]
    sealed = seal_pockets(world)
    assert sealed.classes[4:6] == (CellClass.WASTELAND, CellClass.WASTELAND)
    assert sealed.classes[7] is CellClass.WASTELAND
    assert sealed.classes[1:3] == (CellClass.LAND, CellClass.LAND)
    assert unported_cells(sealed) == []
    assert seal_pockets(sealed) is sealed


def _block(rows: slice, columns: slice, shape: tuple[int, int]) -> Footprint:
    grid = np.zeros(shape, dtype=bool)
    grid[rows, columns] = True
    found = np.nonzero(grid)
    return Footprint(found[0].astype(np.int32), found[1].astype(np.int32))


def test_island_groups_stay_or_move_and_are_holes_of_the_cells() -> None:
    """The land is made on the whole domain; each group then stands on ocean, not on land."""
    domain = np.ones((160, 400), dtype=bool)
    shape = (160, 400)
    groups = [
        _block(slice(60 + 30 * n, 64 + 30 * n), slice(40 + 90 * n, 52 + 90 * n), shape)
        for n in range(3)
    ]
    world = generate_new_world(domain, seed=3, settings=SMALL, groups=groups)
    assert world.moves.shape == (3, 2)
    land, _ocean, _lakes, _ = land_stage(domain, 3, SMALL)
    for group, (rows, columns) in zip(groups, world.moves.tolist(), strict=True):
        target = (group.rows + rows, group.columns + columns)
        assert (world.labels[target] == -1).all()
        assert not land[target].any()
    assert (world.labels == -1).sum() == sum(group.size for group in groups)
    again = generate_new_world(domain, seed=3, settings=SMALL, groups=groups)
    assert np.array_equal(world.labels, again.labels)
    assert np.array_equal(world.moves, again.moves)


def test_the_centre_control_moves_land_inward_and_keeps_its_share() -> None:
    domain = np.zeros((200, 600), dtype=bool)
    domain[20:180, 40:560] = True
    settings = replace(SMALL, feature_px=240, land_permille=300)
    depth = distance_from(~domain, 400, octagonal=True)
    means: list[float] = []
    shares: list[int] = []
    for centre in (0, 500, 1000):
        land, _ocean, _lakes, _ = land_stage(domain, 7, replace(settings, centre_permille=centre))
        means.append(float(depth[land].mean()))
        shares.append(int(np.count_nonzero(land)))
    assert means[0] < means[1] < means[2]
    assert max(shares) - min(shares) <= max(shares) // 20
    plain = land_stage(domain, 7, settings)[0]
    assert np.array_equal(plain, land_stage(domain, 7, replace(settings, centre_permille=0))[0])
