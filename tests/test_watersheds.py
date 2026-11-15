"""Epoch 64: cordilleras, rivers before cells, seeds spaced by the land, rough hills, open vote."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import epoch, eu5_biomes, eu5_nw_export, newworld, relief, watersheds
from rnw.eu5_biomes import (
    CHUNK,
    GROUND_STEP,
    NEIGHBOURS,
    OCTAVE_PARTS,
    SIZE_STEP,
    TOPOGRAPHIES,
    GroundField,
    block_relief,
    calibrated_weights,
    cell_ground_scores,
    cell_ruggedness,
    cell_sizes,
    choose_grounds,
    chosen_pairs,
    class_sizes,
    ground_field,
    integer_cube_root,
    latitude_tenths,
    matched_weights,
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
    sites = watersheds.spaced_sites(17, mask, 16, grid)
    again = watersheds.spaced_sites(17, mask, 16, grid)
    assert np.array_equal(sites, again)
    rows, columns = np.nonzero(sites >= 0)
    assert np.all(mask[rows, columns])
    dense = int(np.count_nonzero(columns < 128))
    sparse = int(np.count_nonzero(columns >= 128))
    assert dense > 3 * sparse
    parts = label_components(mask.astype(np.int32))
    assert set(np.unique(parts[mask]).tolist()) <= set(parts[rows, columns].tolist())
    assert sorted(sites[rows, columns].tolist()) == list(range(rows.size))
    # No two seeds of the square lie nearer than SEED_GAP of the mean of their spacings.
    square = rows < 248
    ys, xs = rows[square], columns[square]
    radius = 16 * grid[ys // watersheds.DENSITY_STEP, xs // watersheds.DENSITY_STEP] // 1000
    near = (ys[:, None] - ys[None, :]) ** 2 + (xs[:, None] - xs[None, :]) ** 2
    gap = watersheds.SEED_GAP * (radius[:, None] + radius[None, :])
    np.fill_diagonal(near, 1 << 40)
    assert np.all(4_000_000 * near >= gap * gap)


def test_spacing_powers_are_exact_integers() -> None:
    parts = watersheds.SPACING_PARTS
    exponents = np.arange(-2 * parts, 2 * parts + 1, dtype=np.int64)
    values = watersheds.spacing_permille(exponents)
    assert values[exponents == 0].tolist() == [1000]
    assert values[exponents == parts].tolist() == [2000]
    assert values[exponents == -parts].tolist() == [500]
    assert values[exponents == parts // 2].tolist() == [1414]  # 1000 sqrt(2), floored
    assert np.all(np.diff(values) > 0)
    real = 1000 * np.exp2(exponents / parts)
    assert np.all((values <= real + 1e-6) & (values > real - 2))


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


def test_a_cell_centre_is_its_own_pixel_nearest_its_mean() -> None:
    grown = np.full((600, 7), -1, dtype=np.int32)
    grown[0:3, 0:3] = 0  # a square holds its mean (1, 1)
    grown[13, :] = 1  # a cup: the mean (12, 3) lies in its hollow, the nearest pixel below it
    grown[10:13, 0] = 1
    grown[10:13, 6] = 1
    grown[20, [0, 6]] = 2  # two pixels as near to the mean (20, 3): the first in raster order
    grown[590:600, 2] = 3  # beyond the first strip of rows: the mean row 594
    grown[[500, 520], 4] = 5  # a tie across two strips keeps the earlier pixel
    flat = np.array([0, 13 * 7, 20 * 7, 590 * 7 + 2, 300 * 7, 520 * 7 + 4], dtype=np.int64)
    centres = watersheds._centre_pixels(grown, flat)  # pyright: ignore[reportPrivateUsage]
    # Cell 4 grew nothing and keeps its seed's pixel.
    assert centres.tolist() == [1 * 7 + 1, 13 * 7 + 3, 20 * 7, 594 * 7 + 2, 300 * 7, 500 * 7 + 4]


def test_shore_cells_touch_water_across_strips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(watersheds, "CENTRE_STRIP", 2)
    land = np.ones((7, 6), dtype=bool)
    land[2, 4:] = False  # water in the second strip, beside cell 1 in the first and cell 2
    land[:, 0] = False  # and beside cell 0
    grown = np.full(land.shape, -1, dtype=np.int32)
    grown[:, 1:3] = 0
    grown[:2, 3:] = 1
    grown[3:5, 3:] = 2
    grown[5:, 3:] = 3  # inland
    shore = watersheds._shore_cells(grown, land, 5)  # pyright: ignore[reportPrivateUsage]
    # Cell 4 grew nothing.
    assert shore.tolist() == [True, True, True, False, False]


def test_relaxed_cells_are_even_up_to_the_coast(monkeypatch: pytest.MonkeyPatch) -> None:
    land = np.zeros((256, 512), dtype=bool)
    land[:, 64:] = True
    walls = np.zeros_like(land)
    grid = np.full((8, 16), 1000, dtype=np.int64)
    steps = watersheds.RELAX_STEPS
    assert steps > 0

    def sizes(relax: int) -> tuple[float, float]:
        """The coastal cells' mean size over the inner ones' and the inner ones' spread."""
        monkeypatch.setattr(watersheds, "RELAX_STEPS", relax)
        cells = watersheds.river_cells(land, walls, key=5, spacing=32, grid=grid, smallest=10)
        pixels = np.bincount(cells[cells >= 0])
        coastal = np.unique(cells[:, 64])
        edges = np.unique(np.concatenate([cells[0], cells[-1], cells[:, -1], coastal]))
        inner = np.setdiff1d(np.flatnonzero(pixels), edges)
        ratio = float(pixels[coastal].mean() / pixels[inner].mean())
        return ratio, float(np.log2(pixels[inner]).std())

    thrown, relaxed = sizes(0), sizes(steps)
    assert relaxed[1] < thrown[1]
    assert abs(1 - relaxed[0]) < abs(1 - thrown[0])


def test_a_seed_by_the_sea_grows_faster() -> None:
    land = np.zeros((128, 256), dtype=bool)
    land[:, 128:] = True
    grid = np.full((4, 8), 1000, dtype=np.int64)
    table = watersheds._land_table(land)  # pyright: ignore[reportPrivateUsage]
    flat = np.array([64 * 256 + 130, 64 * 256 + 200], dtype=np.int64)
    speeds = watersheds._seed_speeds(flat, grid, table, 256)  # pyright: ignore[reportPrivateUsage]
    # Half of the shore seed's square is sea: it grows faster by about the root of two.
    assert speeds[1] == 1000
    assert 1300 < speeds[0] < 1450


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
    ground = ground_field(SIZES, land, height, climate)
    grid = watersheds.spacing_grid(
        land, height, climate, sea=~land, polar_rows=0, sizes=SIZES, ground=ground, spacing=32
    )
    _assert_spacing_keeps_the_cells(land, grid)
    # Neighbouring blocks of land differ by at most the gradation of a block.
    slope = watersheds.GRADATION * watersheds.DENSITY_STEP // 32
    has = _blocks_with_land(land)
    for first, second, both in (
        (grid[:, :-1], grid[:, 1:], has[:, :-1] & has[:, 1:]),
        (grid[:-1], grid[1:], has[:-1] & has[1:]),
    ):
        assert np.all(np.abs(first - second)[both] <= slope)


def test_cells_size_the_land_by_their_own_class() -> None:
    land = _land(9, (640, 640))
    height = relief.generate_relief(land, seed=9)
    climate = watersheds.domain_climate(land, np.zeros_like(land), height)
    walls = np.zeros_like(land)
    ground = ground_field(SIZES, land, height, climate)
    grid = watersheds.spacing_grid(
        land, height, climate, sea=~land, polar_rows=0, sizes=SIZES, ground=ground, spacing=32
    )
    first = watersheds.river_cells(land, walls, key=1, spacing=32, grid=grid, smallest=40)

    def sized(key: int) -> np.ndarray:
        return watersheds.cell_spacing_grid(
            first,
            height,
            climate,
            sea=~land,
            polar_rows=0,
            sizes=SIZES,
            ground=ground,
            key=key,
            spacing=32,
        )

    final = sized(5)
    assert np.array_equal(final, sized(5))
    assert not np.array_equal(final, sized(6))
    _assert_spacing_keeps_the_cells(land, final)


def _blocks_with_land(land: np.ndarray) -> np.ndarray:
    step = watersheds.DENSITY_STEP
    rows, columns = -(-land.shape[0] // step), -(-land.shape[1] // step)
    padded = np.zeros((rows * step, columns * step), dtype=bool)
    padded[: land.shape[0], : land.shape[1]] = land
    return padded.reshape(rows, step, columns, step).any(axis=(1, 3))


def _assert_spacing_keeps_the_cells(land: np.ndarray, grid: np.ndarray) -> None:
    share = land[::32, ::32]
    spacing = grid[: share.shape[0], : share.shape[1]][share]
    expected = int((1_000_000 * 1000 // (spacing * spacing)).sum())
    assert abs(expected - int(share.sum()) * 1000) * 10 <= int(share.sum()) * 1000
    low, high = watersheds.SPACING_RANGE
    assert np.all((spacing >= low) & (spacing <= high))


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
    flat = _votes(["flatland", "flatland"])
    inland = np.zeros(2, dtype=bool)
    assert class_sizes(SIZES, dry, flat, inland).tolist() == [1000, 1000]
    assert class_sizes(SIZES, wet, flat, inland).tolist() == [-1000, -1000]
    both = np.concatenate([wet, dry])
    assert np.array_equal(
        class_sizes(SIZES, both, _votes(["flatland"] * 4), np.zeros(4, dtype=bool)),
        [-1000] * 2 + [1000] * 2,
    )
    # The block whose land votes mountain takes the size of mountains: 500 smaller, 300 on the
    # coast.
    model = replace(
        SIZES,
        offsets=np.array([[-500, 0, 0, 0, 0], [-300, 0, 0, 0, 0]]),
        ground_weights=np.ones(len(TOPOGRAPHIES), dtype=np.int64),
    )
    voted = _votes(["flatland", "mountains"])
    assert class_sizes(model, dry, voted, inland).tolist() == [1000, 500]
    assert class_sizes(model, dry, voted, np.array([False, True])).tolist() == [1000, 700]


def _votes(names: list[str]) -> np.ndarray:
    """Ground votes (``eu5_biomes.ground_scores``) all for the named ground of each row."""
    votes = np.zeros((len(names), len(TOPOGRAPHIES)), dtype=np.int64)
    votes[np.arange(len(names)), [TOPOGRAPHIES.index(name) for name in names]] = 528
    return votes


def test_cells_take_the_ground_of_the_land_they_cover() -> None:
    """A cell's ground is that of the blocks of its land, whatever the cell's size."""
    step = GROUND_STEP
    scores = np.zeros((2 * 4, len(TOPOGRAPHIES)), dtype=np.int64)
    scores[[0, 1, 4, 5]] = _votes(["wetlands"])[0]  # the left half of the land votes wetland
    scores[[2, 3, 6, 7]] = _votes(["hills"])[0]
    pixels = np.full(8, step * step, dtype=np.int64)
    field = GroundField(shape=(2, 4), scores=scores, pixels=pixels)
    labels = np.full((2 * step, 4 * step), -1, dtype=np.int32)
    labels[:4, :4] = 0  # a small cell in the wetland
    labels[4:, : 2 * step] = 1  # a large one filling the rest of it
    labels[:, 2 * step : 3 * step + 4] = 2  # most of its land in the hills, a strip in the wetland
    labels[:, 3 * step + 4 :] = 3
    labels[0, 0] = 9  # beyond the cells counted
    votes = cell_ground_scores(labels, 4, field)
    assert votes[0, TOPOGRAPHIES.index("wetlands")] == 15 * 528
    model = replace(SIZES, ground_weights=np.ones(len(TOPOGRAPHIES), dtype=np.int64))
    chosen = choose_grounds(model, votes, np.zeros(4, dtype=bool))
    assert [TOPOGRAPHIES[kind] for kind in chosen.tolist()] == ["wetlands"] * 2 + ["hills"] * 2
    # A dry cell is never wetland.
    dry = choose_grounds(model, votes, np.array([True, False, False, False]))
    assert TOPOGRAPHIES[int(dry[0])] != "wetlands"


def test_cells_take_the_size_of_the_class_they_will_be_voted() -> None:
    def blocks(rows: list[tuple[int, int, int, int]]) -> np.ndarray:
        table = np.array(rows, dtype=np.int64)
        summer, winter = rain_root(table[:, 1] * 2 // 3), rain_root(table[:, 1] // 3)
        return np.stack([table[:, 0], summer, table[:, 2], table[:, 3], winter], axis=1)

    dry = blocks([(100, 80, 7000, 50), (500, 120, 8000, 150)])
    wet = blocks([(100, 900, 7000, 50), (500, 700, 8000, 150)])
    readings = _votes(["flatland", "flatland"])
    inland = np.zeros(2, dtype=bool)
    assert cell_sizes(SIZES, dry, dry, readings, inland).tolist() == [1000, 1000]
    assert cell_sizes(SIZES, wet, wet, readings, inland).tolist() == [-1000, -1000]
    # Its centre votes the class: dry land around a wet centre is sized as the wet class is.
    assert cell_sizes(SIZES, dry, wet, readings, inland).tolist() == [-1000, -1000]
    # A coastal cell moves by its ground's coastal offset.
    coast = replace(SIZES, offsets=np.array([[0] * 5, [0, 0, 0, 0, -400]]))
    assert cell_sizes(coast, dry, dry, readings, np.array([True, False])).tolist() == [600, 1000]


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
    model = size_model(game_map, templates, height, mainland=1)
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
    assert model.digest() == size_model(game_map, templates, height, mainland=1).digest()
    # Read without itself, each of the Americas' two forests is given the other's size; the
    # mountain lies 101/64 octave above that, the hill as far below.
    step_up = octave_parts(3, 1) * 1000 // OCTAVE_PARTS
    # No location touches the sea: the coastal offsets are none.
    assert model.offsets.tolist() == [[step_up, 0, -step_up, 0, 0], [0] * 5]
    # Landmasses of fewer locations than ``mainland`` size no class.
    assert size_model(game_map, templates, height, mainland=6).size.size == 0
    assert model.dry.tolist() == [True, False]
    # The ground vote learns from the blocks of the Old World's passable land, the field among
    # them, each given the ground of the location holding most of it: "old" fills the top half's
    # 32 blocks, the field the 16 below its left half.
    flat, plateau = TOPOGRAPHIES.index("flatland"), TOPOGRAPHIES.index("plateau")
    assert model.grounds.tolist() == [flat] * 32 + [plateau] * 16
    assert model.ground_table[:, 0].tolist() == [7000] * 48
    assert model.ground_weights.size == len(TOPOGRAPHIES)


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


def test_matched_weights_give_a_world_the_share_its_neighbours_hold() -> None:
    # Rows whose neighbours hold the second class from 20 % to 60 %: a plurality names it for a
    # quarter of the rows, though the neighbours hold 40 % of it.
    share = np.arange(200, dtype=np.int64) * 40 // 199 + 20
    scores = np.stack([(100 - share) * 5, share * 5], axis=1)
    climate_of = np.arange(2, dtype=np.int64)

    def choose(weighed: np.ndarray) -> np.ndarray:
        return chosen_pairs(weighed, climate_of)

    ones = np.ones(2, dtype=np.int64)
    held = int(share.sum()) * 200 // int((share + (100 - share)).sum())
    assert int(np.bincount(choose(scores), minlength=2)[1]) * 3 < held * 2
    weights = matched_weights(scores, ones, choose)
    found = np.bincount(choose(scores * weights), minlength=2)
    assert abs(int(found[1]) - held) <= 2
    assert np.array_equal(weights, matched_weights(scores, ones, choose))
    # Rows that are of one class each keep their choice; one row alone and a class that weighs
    # nothing are no trouble.
    pure = np.array([[160, 0], [0, 160], [160, 0]], dtype=np.int64)
    assert np.array_equal(choose(pure * matched_weights(pure, ones, choose)), [0, 1, 0])
    single = matched_weights(scores[:1], ones, choose)
    assert single.shape == (2,)
    assert matched_weights(scores, np.array([1, 0], dtype=np.int64), choose)[1] == 0


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


def test_the_ground_is_voted_by_vanilla_locations_alike_without_shares() -> None:
    #           mean height, ruggedness, roughness, distance to the sea
    table = np.array(
        [
            [16000, 3000, 900, 300],  # high and broken
            [12000, 300, 120, 400],  # high and smooth, far from the sea
            [6100, 60, 30, 10],  # low and smooth, at the sea
            [7600, 500, 300, 150],  # low and rough
            [7000, 150, 60, 200],
        ],
        dtype=np.int64,
    )
    intended = ["mountains", "plateau", "wetlands", "hills", "flatland"]
    grounds = np.repeat([TOPOGRAPHIES.index(name) for name in intended], NEIGHBOURS)
    model = replace(
        SIZES,
        ground_table=np.repeat(table, NEIGHBOURS, axis=0),
        grounds=grounds,
        ground_weights=np.ones(len(TOPOGRAPHIES), dtype=np.int64),
    )

    def names(query: np.ndarray, dry: np.ndarray | None = None) -> list[str]:
        found = np.zeros(len(query), dtype=bool) if dry is None else dry
        return [TOPOGRAPHIES[kind] for kind in vote_grounds(model, query, found).tolist()]

    assert names(table) == intended
    # The readings count as they are: a land of lowland marsh is all wetland, with no quota.
    marsh = np.repeat(table[2:3], 4, axis=0) + np.arange(4)[:, np.newaxis]
    assert names(marsh) == ["wetlands"] * 4
    # A dry row is never wetland, also with the weights matched to the rows voted.
    dry = np.array([False, False, True, False, False])
    assert names(table, dry)[2] != "wetlands"
    matched = vote_grounds(model, marsh, np.ones(len(marsh), dtype=bool), matched=True)
    assert TOPOGRAPHIES.index("wetlands") not in matched.tolist()
    assert vote_grounds(model, table, np.zeros(5, dtype=bool), matched=True).tolist() == [
        TOPOGRAPHIES.index(name) for name in intended
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
    _, walls, plan, _ = newworld._river_cells(  # pyright: ignore[reportPrivateUsage]
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


def test_blurred_readings_are_those_of_the_whole_map_in_any_strip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cells of 50 pixels a side over a land of several islands.
    blocks = np.arange(300)[:, np.newaxis] // 50 * 6 + np.arange(260)[np.newaxis, :] // 50
    labels = np.where(_land(6, (300, 260)), blocks, -1).astype(np.int32)
    count = int(labels.max()) + 1
    generator = np.random.default_rng(6)
    height = (7000 + generator.integers(0, 3000, labels.shape)).astype(np.int32)
    land = labels >= 0
    whole = relief.land_blur(land, height, 8)
    expected = (
        cell_roughness(labels, whole, count),
        cell_ruggedness(labels, whole, count),
    )
    monkeypatch.setattr(relief, "ROUGHNESS_ROWS", 40)
    monkeypatch.setattr(eu5_biomes, "RELIEF_ROWS", 40)
    found = (
        cell_roughness(labels, height, count, blur=8),
        cell_ruggedness(labels, height, count, blur=8),
    )
    assert all(np.array_equal(a, b) for a, b in zip(found, expected, strict=True))
