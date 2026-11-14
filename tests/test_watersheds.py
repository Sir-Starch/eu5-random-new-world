"""Epoch 64: cordilleras, rivers before cells, seeds spaced by the land, rough hills, open vote."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import epoch, eu5_nw_export, newworld, relief, watersheds
from rnw.eu5_biomes import (
    CHUNK,
    NEIGHBOURS,
    OCTAVE_PARTS,
    SIZE_STEP,
    TOPOGRAPHIES,
    block_relief,
    calibrated_weights,
    cell_ruggedness,
    chosen_pairs,
    class_sizes,
    ground_ranks,
    integer_cube_root,
    latitude_tenths,
    nearest_others,
    octave_parts,
    prior_weights,
    rain_root,
    size_model,
    vote_grounds,
)
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_nw_export import NewWorldExportError
from rnw.fields import upsample
from rnw.model import CellClass
from rnw.newworld import NewWorld, generate_new_world
from rnw.relief import HILL_STEP, cell_roughness
from rnw.rivers import RiverGenerationError
from rnw.settings import NewWorldSettings
from rnw.synth import grow_regions, grow_weighted
from rnw.topology import label_components
from tests.fakes import SIZES

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.eu5_biomes import ClimateGrid
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map

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


def _fixed(value: int) -> Callable[..., int]:
    def answer(*_arguments: object, **_options: object) -> int:
        return value

    return answer


def _land(seed: int, shape: tuple[int, int]) -> np.ndarray:
    generator = np.random.default_rng(seed)
    coarse = generator.integers(0, 1000, (shape[0] // 60 + 2, shape[1] // 60 + 2))
    land = upsample(coarse, 60, shape) > 430
    land[:6] = False
    land[-6:] = False
    land[:, :6] = False
    land[:, -6:] = False
    return land


@pytest.mark.parametrize("window", [1, 200, 600])
def test_cordilleras_are_the_same_for_any_strip_height(
    monkeypatch: pytest.MonkeyPatch, window: int
) -> None:
    land = _land(5, (420, 380))
    whole = relief.generate_relief(land, seed=5, margins=True)
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, window)))
    monkeypatch.setattr(relief, "worker_count", _fixed(3))
    assert np.array_equal(relief.generate_relief(land, seed=5, margins=True), whole)
    assert not np.array_equal(whole, relief.generate_relief(land, seed=5))
    assert np.all(whole[~land] == 0)
    assert int(whole[land].min()) >= relief.COAST_HEIGHT


def test_a_plane_has_no_roughness_and_a_large_cell_reads_as_rough_as_a_small_one() -> None:
    rows, columns = np.mgrid[0:96, 0:120]
    labels = np.where(columns < 30, 0, 1).astype(np.int32)  # a small cell beside a large one
    plane = (6000 + rows * 40 + columns * 25).astype(np.int32)
    # A checkerboard of squares HILL_STEP wide: the height bends by four times 300 both ways.
    squares = np.where((rows // HILL_STEP + columns // HILL_STEP) % 2 == 0, 300, -300)
    assert cell_roughness(labels, plane, 2).tolist() == [0, 0]
    assert cell_roughness(labels, plane + squares.astype(np.int32), 2).tolist() == [1200, 1200]
    # A pixel is read along the directions whose ends are land, and only if one is.
    labels[:, 60:] = -1
    assert cell_roughness(labels, plane + squares.astype(np.int32), 2).tolist() == [1200, 1200]


def test_integer_cube_roots_and_prior_weights_are_exact() -> None:
    for value in (0, 1, 7, 8, 26, 27, 10**12, 10**12 + 1, 3**60 - 1, 3**60):
        root = integer_cube_root(value)
        assert root**3 <= value < (root + 1) ** 3
    weights = prior_weights(np.array([0, 0, 0, 1, 2, 2], dtype=np.int64), 4)
    assert weights[3] == 0
    assert weights[1] > weights[2] > weights[0]


def test_seeds_follow_the_spacing_and_reach_every_island() -> None:
    mask = np.zeros((256, 256), dtype=bool)
    mask[8:248, 8:248] = True
    mask[250:253, 250:253] = True  # a speck too small for any grid seed
    mask[248:250, :] = False
    grid = np.full((8, 8), 1000, dtype=np.int64)
    grid[:, 4:] = 2000
    sites = watersheds.variable_sites(17, mask, 16, grid)
    again = watersheds.variable_sites(17, mask, 16, grid)
    assert np.array_equal(sites, again)
    rows, columns = np.nonzero(sites >= 0)
    assert np.all(mask[rows, columns])
    dense = int(np.count_nonzero(columns < 128))
    sparse = int(np.count_nonzero(columns >= 128))
    assert dense > 3 * sparse
    parts = label_components(mask.astype(np.int32))
    assert set(np.unique(parts[mask]).tolist()) <= set(parts[rows, columns].tolist())
    assert sorted(sites[rows, columns].tolist()) == list(range(rows.size))


def test_cells_grow_up_to_the_walls_and_take_their_pixels() -> None:
    land = np.ones((120, 120), dtype=bool)
    walls = np.zeros_like(land)
    walls[:, 60] = True
    grid = np.full((4, 4), 1000, dtype=np.int64)
    cells = watersheds.river_cells(land, walls, key=3, spacing=30, grid=grid, smallest=10)
    assert np.all(cells >= 0)
    left, right = set(cells[:, :60].ravel().tolist()), set(cells[:, 61:].ravel().tolist())
    assert not left & right
    # Every wall pixel belongs to a cell of one side and touches a cell of the other.
    assert np.all((cells[:, 60] != cells[:, 59]) | (cells[:, 60] != cells[:, 61]))
    assert np.array_equal(grow_regions(land, cells), cells)


def test_seeds_grow_at_their_own_speed() -> None:
    mask = np.ones((3, 31), dtype=bool)
    seeds = np.full(mask.shape, -1, dtype=np.int32)
    seeds[1, 0] = 0
    seeds[1, 30] = 1
    equal = grow_weighted(mask, seeds, np.array([5, 5], dtype=np.int64))
    assert np.array_equal(equal, grow_regions(mask, seeds))
    # The first seed is twice as fast, so it reaches twice as far before they meet.
    fast = grow_weighted(mask, seeds, np.array([2, 1], dtype=np.int64))
    assert np.flatnonzero(fast[1] == 0).max() == 20  # they meet at round 20; the west claims first
    assert np.all(fast >= 0)


def test_the_spacing_keeps_the_number_of_cells() -> None:
    land = _land(9, (640, 640))
    height = relief.generate_relief(land, seed=9)
    climate = watersheds.domain_climate(land, np.zeros_like(land), height)
    grid = watersheds.spacing_grid(land, height, climate, polar_rows=0, sizes=SIZES)
    share = land[::32, ::32]
    spacing = grid[: share.shape[0], : share.shape[1]][share]
    expected = int((1_000_000 * 1000 // (spacing * spacing)).sum())
    assert abs(expected - int(share.sum()) * 1000) * 10 <= int(share.sum()) * 1000
    assert set(np.unique(grid).tolist()) <= set(watersheds.SPACING)


def test_rivers_come_first_from_epoch_64_only() -> None:
    domain = np.ones((240, 320), dtype=bool)
    older = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST - 1, sizes=SIZES
    )
    other_seam = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST - 1, seam=100, sizes=SIZES
    )
    assert np.array_equal(older.labels, other_seam.labels)
    world = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST, sizes=SIZES
    )
    again = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST, sizes=SIZES
    )
    assert np.array_equal(world.labels, again.labels)
    assert not np.array_equal(world.labels, older.labels)

    def land(made: NewWorld) -> np.ndarray:
        kinds = [kind in (CellClass.LAND, CellClass.WASTELAND) for kind in made.classes]
        return np.array([*kinds, False])[made.labels]

    assert np.array_equal(land(world), land(older))


def test_octave_parts_are_exact() -> None:
    assert octave_parts(2, 1) == OCTAVE_PARTS
    assert octave_parts(1, 2) == -OCTAVE_PARTS
    assert octave_parts(704, 704) == 0
    assert octave_parts(705, 704) == 0
    assert octave_parts(703, 704) == -1
    assert octave_parts(3, 2) == 37  # 64 log2(1.5) = 37.4
    assert octave_parts(3 * 512, 512) == 101  # 64 log2(3) = 101.4
    assert octave_parts(1 << 20, 1) == 20 * OCTAVE_PARTS


def test_class_sizes_take_the_size_of_the_class_the_vote_chooses() -> None:
    def blocks(rows: list[tuple[int, int, int, int]]) -> np.ndarray:
        # The seasons' features, as the synthetic model reads them (``tests.fakes``).
        table = np.array(rows, dtype=np.int64)
        summer, winter = rain_root(table[:, 1] * 2 // 3), rain_root(table[:, 1] // 3)
        return np.stack([table[:, 0], summer, table[:, 2], table[:, 3], winter], axis=1)

    dry = blocks([(100, 80, 7000, 50), (500, 120, 8000, 150)])
    wet = blocks([(100, 900, 7000, 50), (500, 700, 8000, 150)])
    flat = np.zeros((2, 2), dtype=np.int64)
    assert class_sizes(SIZES, dry, flat).tolist() == [1000, 1000]
    assert class_sizes(SIZES, wet, flat).tolist() == [-1000, -1000]
    both = np.concatenate([wet, dry])
    assert np.array_equal(
        class_sizes(SIZES, both, np.zeros((4, 2), dtype=np.int64)), [-1000] * 2 + [1000] * 2
    )
    # The block whose readings rank like vanilla's mountains is the one mountain the shares allow,
    # and mountains are 500 smaller.
    model = replace(
        SIZES,
        shares=np.array([1, 0, 0, 0, 1]),
        offsets=np.array([-500, 0, 0, 0, 0]),
        ground_table=np.repeat(np.array([[0] * 5, [500] * 5], dtype=np.int64), NEIGHBOURS, axis=0),
        grounds=np.repeat(np.array([4, 0], dtype=np.int64), NEIGHBOURS),
    )
    assert class_sizes(model, dry, flat).tolist() == [1000, 500]


def test_the_size_model_reads_locations_through_their_blocks() -> None:
    step = SIZE_STEP
    labels = np.zeros((2 * step, 2 * step), dtype=np.int32)  # "old" fills the top two blocks
    labels[step:, :step] = 3  # cultivated: the vote does not learn from it, so neither does this
    labels[step:, step : step + step // 4] = 1
    labels[step:, step + step // 4 :] = 2
    labels[0, 0] = 4  # a wasteland pixel
    namespace = SimpleNamespace(
        keys=("old", "west", "east", "fields", "waste"),
        classes=(CellClass.LAND,) * 4 + (CellClass.WASTELAND,),
        continents=("europe", NEW_WORLD, NEW_WORLD, "europe", "europe"),
        labels=labels,
    )
    game_map = cast("Eu5Map", cast("object", namespace))
    templates = {
        "old": {"climate": "arid", "vegetation": "desert", "topography": "flatland"},
        "west": {"climate": "oceanic", "vegetation": "forest", "topography": "hills"},
        "east": {"climate": "oceanic", "vegetation": "forest", "topography": "mountains"},
        "fields": {"climate": "oceanic", "vegetation": "farmland", "topography": "plateau"},
        "waste": {"climate": "arid", "vegetation": "desert", "topography": "mountains"},
    }
    height = np.full(labels.shape, 7000, dtype=np.uint16)
    height[step:, step:] = 9000
    model = size_model(game_map, templates, height)
    # The Old World's one passable location is its median; the Americas' lower median is the
    # smaller of their two, the larger is three times as large.
    assert model.size.tolist() == [0, 0, octave_parts(3, 1)]
    assert model.pairs.tolist() == [0, 1, 1]
    assert model.climate_of.tolist() == [0, 1]
    # Both of the Americas' locations lie in one block and read its features.
    centres = np.array([step // 2, step + step // 2, step + step // 2], dtype=np.int64)
    assert model.features[:, 0].tolist() == latitude_tenths(centres).tolist()
    assert model.features[:, 2].tolist() == [7000, 9000, 9000]
    assert np.array_equal(model.features[1], model.features[2])
    assert model.digest() == size_model(game_map, templates, height).digest()
    # Read without itself, each of the Americas' two forests is given the other's size; the
    # mountain lies 101/64 octave above that, the hill as far below. The shares are the Old
    # World's passable locations, the field among them.
    step_up = octave_parts(3, 1) * 1000 // OCTAVE_PARTS
    assert model.offsets.tolist() == [step_up, 0, -step_up, 0, 0]
    assert model.shares.tolist() == [0, 1, 0, 0, 1]
    assert model.dry.tolist() == [True, False]
    # The ground vote learns from the Old World's passable locations, the field among them, each
    # reading ranked among them: alike in height, the two rank by their order.
    assert model.grounds.tolist() == [TOPOGRAPHIES.index("flatland"), TOPOGRAPHIES.index("plateau")]
    assert model.ground_table[:, 0].tolist() == [0, 500]


def _chosen_without_self(train: np.ndarray, classes: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """How often each pair is chosen when every row is read by its nearest other rows."""
    rank = np.arange(NEIGHBOURS, 0, -1, dtype=np.int64)
    scores = np.zeros((train.shape[0], weights.size), dtype=np.int64)
    for row in range(train.shape[0]):
        distance = ((train - train[row]) ** 2).sum(axis=1)
        distance[row] = np.iinfo(np.int64).max
        order: np.ndarray = np.lexsort((np.arange(int(train.shape[0]), dtype=np.int64), distance))
        nearest = order[:NEIGHBOURS]
        np.add.at(scores[row], classes[nearest], rank)
    climate_of = np.arange(weights.size, dtype=np.int64)
    return np.bincount(chosen_pairs(scores * weights, climate_of), minlength=weights.size)


def test_calibrated_weights_give_a_rare_class_its_share() -> None:
    # A class whose share of the neighbourhood rises from none to 60 % along the row: a plurality
    # names it only where it holds more than half, a third of the rows it holds.
    places = np.arange(1000, dtype=np.int64)
    classes = ((places * 7919) % 1000 < places * 6 // 10).astype(np.int64)
    train = np.stack([places * 10, np.zeros_like(places)], axis=1)
    held = np.bincount(classes, minlength=2)
    plain = _chosen_without_self(train, classes, np.array([1, 1], dtype=np.int64))
    assert plain[1] * 3 < held[1] * 2
    weights = calibrated_weights(train, classes, np.array([0, 1], dtype=np.int64))
    chosen = _chosen_without_self(train, classes, weights)
    assert abs(int(chosen[1]) - int(held[1])) * 10 <= int(held[1])
    assert np.array_equal(weights, calibrated_weights(train, classes, np.array([0, 1])))


def test_a_row_never_votes_for_itself() -> None:
    train = np.zeros((CHUNK + 40, 2), dtype=np.int64)  # all alike: every tie goes by index
    train[CHUNK:, 0] = 5
    for start in (0, CHUNK):
        nearest = nearest_others(train, start, NEIGHBOURS)
        own = np.arange(start, start + int(nearest.shape[0]), dtype=np.int64)[:, np.newaxis]
        assert nearest.shape == (min(CHUNK, train.shape[0] - start), NEIGHBOURS)
        assert not np.any(nearest == own)
    # A pair no row holds weighs nothing; one row alone still gets a weight.
    weights = calibrated_weights(train, np.array([0] * (CHUNK + 39) + [2]), np.array([0, 1, 2]))
    assert weights[1] == 0
    assert weights[0] > 0
    assert weights[2] > 0


def test_the_ground_is_voted_by_vanilla_locations_alike_in_rank() -> None:
    #           mean height, ruggedness, roughness, rain, distance to the sea
    query = np.array(
        [
            [9000, 900, 80, 100, 100],  # high and broken
            [8800, 10, 20, 150, 300],  # high and smooth, far from the sea
            [6000, 20, 10, 900, 5],  # low, wet, at the sea
            [7000, 30, 30, 500, 50],
        ],
        dtype=np.int64,
    )
    ranks = ground_ranks(query)
    assert ranks[:, 0].tolist() == [750, 500, 0, 250]
    intended = ["mountains", "plateau", "wetlands", "flatland"]
    model = replace(
        SIZES,
        ground_table=np.repeat(ranks, NEIGHBOURS, axis=0),
        grounds=np.repeat([TOPOGRAPHIES.index(name) for name in intended], NEIGHBOURS),
    )
    shares = np.array([1, 1, 0, 1, 1], dtype=np.int64)
    wet = np.zeros(4, dtype=bool)

    def names(voted: np.ndarray) -> list[str]:
        return [TOPOGRAPHIES[kind] for kind in voted.tolist()]

    assert names(vote_grounds(model, query, wet, shares)) == intended
    # Only the order of the readings counts, not their scale.
    assert names(vote_grounds(model, query * 10, wet, shares)) == intended
    # A dry row is never wetland: the wetland share goes to the first other free row.
    dry = np.array([False, False, True, False])
    assert names(vote_grounds(model, query, dry, shares)) == [
        "mountains",
        "plateau",
        "flatland",
        "wetlands",
    ]


def test_block_relief_reads_the_spread_and_the_bend_of_each_block() -> None:
    rows, columns = np.mgrid[0:SIZE_STEP, 0 : 2 * SIZE_STEP]
    height = np.full(rows.shape, 7000, dtype=np.int32)
    right = columns >= SIZE_STEP
    squares = np.where((rows // HILL_STEP + columns // HILL_STEP) % 2 == 0, 300, -300)
    height[right] += squares[right].astype(np.int32)
    land = np.ones(rows.shape, dtype=bool)
    found = np.ones((1, 2), dtype=bool)
    relief = block_relief(land, height, found)
    assert relief[:, 0].tolist() == [0, 300]
    assert 0 < relief[0, 1] < relief[1, 1] <= 1200


def test_a_cell_is_as_rugged_as_its_ground_whatever_its_size() -> None:
    rows, columns = np.mgrid[0:SIZE_STEP, 0 : 5 * SIZE_STEP]
    squares = np.where((rows // HILL_STEP + columns // HILL_STEP) % 2 == 0, 300, -300)
    height = (7000 + squares + 10 * columns).astype(np.int32)  # broken ground on a slope
    labels = np.where(columns < SIZE_STEP, 0, 1).astype(np.int32)  # a small cell, a large one
    labels[:, 4 * SIZE_STEP :] = 2  # a block of water
    rugged = cell_ruggedness(labels, height, 2)
    assert rugged[0] == rugged[1] > 300
    # Vanilla's land is not its first labels: a mask of its land pixels reads the same.
    assert np.array_equal(cell_ruggedness(labels, height, 2, labels < 2), rugged)
    rough = cell_roughness(labels, height, 2)
    assert np.array_equal(cell_roughness(labels, height, 2, labels < 2), rough)
    # Their own spreads differ: the large cell spans thrice the slope.
    own = [int(height[labels == cell].std()) for cell in (0, 1)]
    assert own[1] > 3 * own[0] // 2


def test_the_world_keeps_its_drainage_plan_and_a_foreign_plan_is_refused() -> None:
    domain = np.ones((240, 320), dtype=bool)
    world = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST, seam=100, sizes=SIZES
    )
    plan = world.drainage
    assert plan is not None
    assert plan.seam == 100
    assert len(plan.parents) == len(watersheds.plan_spans(320, 100))
    older = generate_new_world(
        domain, seed=3, settings=SMALL, algorithm=epoch.RIVERS_FIRST - 1, sizes=SIZES
    )
    assert older.drainage is None
    for carried, roll in ((None, 100), (plan, 101)):
        canvas = cast(
            "Canvas", cast("object", SimpleNamespace(roll=roll, col0=0, shape=(240, 320)))
        )
        with pytest.raises(NewWorldExportError, match="no drainage plan split at this map's seam"):
            _ = eu5_nw_export._rivers(  # pyright: ignore[reportPrivateUsage]
                replace(world, drainage=carried),
                canvas,
                cast("ClimateGrid", cast("object", None)),
                3,
                algorithm=epoch.RIVERS_FIRST,
            )
    land = np.zeros((240, 320), dtype=bool)
    land[40:200, 60:260] = True
    lakes = np.zeros_like(land)
    whole = watersheds.plan_drainage(
        land, np.where(land, 7000, 0).astype(np.int32), lakes=lakes, seam=None, seed=5
    )
    rain = np.full((60, 80), 800, dtype=np.int64)
    rivers = watersheds.domain_rivers(land, whole, lakes=lakes, rain=rain, seed=5)
    assert rivers.stats["watershed_domains"] == 1
    split = replace(whole, seam=100)
    with pytest.raises(RiverGenerationError, match="number of spans"):
        _ = watersheds.domain_rivers(land, split, lakes=lakes, rain=rain, seed=5)


def test_the_cells_grow_along_the_rivers_of_the_worn_relief() -> None:
    land = _land(4, (240, 320))
    lakes = np.zeros_like(land)
    planned = relief.generate_relief(land, seed=4, lakes=lakes, margins=True)
    worn = planned.copy()
    _, walls, plan = newworld._river_cells(  # pyright: ignore[reportPrivateUsage]
        land, lakes, worn, seed=4, settings=SMALL, seam=100, sizes=SIZES, algorithm=epoch.BASINS
    )
    assert not np.array_equal(worn, planned)
    before = watersheds.plan_drainage(land, planned, lakes=lakes, seam=100, seed=4)
    assert all(np.array_equal(a, b) for a, b in zip(plan.parents, before.parents, strict=True))
    # The export draws the rivers again with the rain of the world's (worn) elevation.
    rain = watersheds.domain_climate(land, lakes, worn).rain
    rivers = watersheds.domain_rivers(land, plan, lakes=lakes, rain=rain, seed=4)
    assert np.array_equal(walls, watersheds.border_rivers(rivers))
    older = planned.copy()
    _ = newworld._river_cells(  # pyright: ignore[reportPrivateUsage]
        land, lakes, older, seed=4, settings=SMALL, seam=100, sizes=SIZES,
        algorithm=epoch.BASINS - 1,
    )  # fmt: skip
    assert np.array_equal(older, planned)
