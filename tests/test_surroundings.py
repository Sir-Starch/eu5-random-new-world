"""What surrounds a world's generated lands on the map (``rnw.app.surroundings``)."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import atlas as atlas_module
from rnw.app import surroundings
from rnw.eu5_atlas import build_atlas
from tests.fakes import synthetic_atlas, synthetic_world

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.atlas import Atlas

HEIGHT, WIDTH = 256, 512
# The kinds of the test map's pixels: kept sea and land, generated land and sea.
KEPT_SEA, KEPT, LAND, SEA = 0, 1, 2, 3


def _map(seed: int) -> NDArray[np.int8]:
    """A map of generated land and sea in a band of rows, kept land and sea around it."""
    rng = np.random.default_rng(seed)
    found = np.where(rng.random((HEIGHT, WIDTH)) < 0.3, KEPT, KEPT_SEA).astype(np.int8)
    found[64:200] = np.where(rng.random((136, WIDTH)) < 0.4, LAND, SEA)
    return found


def _preview(world: NDArray[np.int8]) -> NDArray[np.uint8]:
    colours = np.array(
        [
            (25, 45, 90),
            surroundings.KEPT_LAND,
            surroundings.GENERATED_DRY[0],
            surroundings.GENERATED_WET[0],
        ],
        dtype=np.uint8,
    )
    return colours[world[:: surroundings.PREVIEW_STEP, :: surroundings.PREVIEW_STEP]]


def _atlas(world: NDArray[np.int8], row: int, column: int, rows: int, columns: int) -> Atlas:
    """An atlas at a scale of 4 whose box starts at the map's ``row`` and ``column`` (columns
    wrap): location 0 is its land, location 1 its sea."""
    scale = 4
    picked = world[
        np.ix_(row + np.arange(rows) * scale, (column + np.arange(columns) * scale) % WIDTH)
    ]
    labels = np.select([picked == LAND, picked == SEA], [1, 2], 0).astype(np.int32)
    base = synthetic_atlas()
    kinds = np.full(base.cells, atlas_module.KINDS.index("sea"), dtype=np.uint8)
    kinds[0] = atlas_module.KINDS.index("land")
    return replace(base, scale=scale, labels=labels, kinds=kinds, origin=None)


@pytest.mark.parametrize(("row", "column"), [(64, 40), (68, 44), (60, 480)])
def test_an_old_atlas_is_placed_where_its_picture_shows_it(row: int, column: int) -> None:
    """Matched to the world's picture, the box lands on the map's row and on its column to the
    picture's eighth, across the map's seam too; the kept land under it is the picture's."""
    world = _map(7)
    preview = _preview(world)
    found = _atlas(world, row, column, 32, 64)
    origin = surroundings.match_origin(found, preview)
    assert origin is not None
    assert origin[0] == row
    assert origin[1] // surroundings.PREVIEW_STEP == column // surroundings.PREVIEW_STEP
    assert origin[2:] == (HEIGHT, WIDTH)
    kept = surroundings.kept_land(found, origin, preview)
    assert kept.shape == found.size
    assert not kept[found.labels > 0].any()


def test_a_recorded_place_is_used_as_it_is() -> None:
    world = _map(3)
    found = replace(_atlas(world, 64, 40, 32, 64), origin=(64, 40, HEIGHT, WIDTH))
    assert surroundings.placed(found, _preview(world)) == (64, 40, HEIGHT, WIDTH)


def test_a_box_that_fits_its_picture_in_many_places_is_not_placed() -> None:
    """All sea fits anywhere: the world is shown without its surroundings."""
    world = np.full((HEIGHT, WIDTH), SEA, dtype=np.int8)
    found = _atlas(world, 64, 40, 32, 64)
    assert surroundings.match_origin(found, _preview(world)) is None
    alone = surroundings.surroundings(found, _preview(world), {})
    assert alone.kept is None


def test_a_box_that_its_picture_does_not_show_is_not_placed() -> None:
    world = _map(5)
    other = _map(6)
    assert surroundings.match_origin(_atlas(world, 64, 40, 32, 64), _preview(other)) is None


def test_each_land_location_has_the_continent_of_its_region() -> None:
    found = synthetic_atlas()
    keys = tuple("sahel_region" if number % 2 else "alaska_region" for number in range(found.cells))
    found = replace(found, region_keys=keys)
    regions = {"sahel_region": "africa", "alaska_region": "america"}
    continent = surroundings.continents_of(found, regions)
    land = {atlas_module.KINDS.index("land"), atlas_module.KINDS.index("wasteland")}
    for number, kind in enumerate(found.kinds.tolist()):
        if kind not in land:
            assert continent[number] == -1
        else:
            name = regions[keys[number]]
            assert continent[number] == surroundings.CONTINENTS.index(name)
    assert (surroundings.continents_of(found, {}) == -1).all()


def test_the_atlas_records_where_its_box_lies_on_the_map() -> None:
    """The box's first row and its column on the map, the canvas's columns shifted and wrapped,
    are written and read back; an atlas without them reads as before."""
    world, plan, biomes, natives, mask = synthetic_world()
    built = build_atlas(
        world=world,
        plan=plan,
        biomes=biomes,
        natives=natives,
        mask=mask,
        step=1,
        margin=3,
        column_shift=70,
    )
    assert built.origin is not None
    height, width = mask.shape
    rows, _columns = np.nonzero(mask)
    assert built.origin[2:] == (height, width)
    assert built.origin[0] >= int(rows.min())
    assert 0 <= built.origin[1] < width
    document, picture = atlas_module.to_files(built)
    assert atlas_module.from_files(document, picture).origin == built.origin
    older = replace(built, origin=None)
    assert atlas_module.from_files(*atlas_module.to_files(older)).origin is None
