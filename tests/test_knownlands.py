"""The known lands: the library's pictures, and how one is laid on the editor's sheet."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import knownlands, landeditor
from rnw.gui import text
from rnw.landarea import EDITOR_STEP, TEMPLATE_STEP, LandArea
from rnw.landmask import IS_LAND, LAKE, LAND, MIN_LAND_PERMILLE, SEA
from rnw.settings import PRESETS
from rnw.topology import distance_from

SETTINGS = PRESETS["continents"].new_world
MARGIN = landeditor.margin_for(SETTINGS)
SPECK = max(1, SETTINGS.min_island_px // EDITOR_STEP**2)
IS_LAND_ARRAY = np.array(IS_LAND, dtype=np.bool_)
# A land that runs on to the edges of the usable area still leaves some sea.
MOST_PERMILLE = 880


def _area() -> LandArea:
    """A wide area with the Americas and an island group in it (the sheet is 300 by 240)."""
    area = np.zeros((480, 600), dtype=np.bool_)
    area[20:-20, 20:-20] = True
    americas = np.zeros_like(area)
    americas[180:380, 60:160] = True
    islands = np.zeros_like(area)
    islands[100:112, 300:312] = True
    return LandArea((480 * TEMPLATE_STEP, 600 * TEMPLATE_STEP), area, americas, islands).at(
        EDITOR_STEP
    )


def test_the_library_lists_its_lands_and_each_has_a_picture_and_a_name() -> None:
    ids = knownlands.land_ids()
    assert len(ids) == len(set(ids)) >= 4
    for land in knownlands.known_lands():
        assert land.source.startswith(("https://", "supplied by"))
        assert 50 <= land.share <= 500
        assert set(land.open) <= set(knownlands.SIDES)
        assert f"editor.land.{land.id}" in text.sources()
        assert knownlands.source_kinds(land.id).ndim == 2


def test_a_picture_holds_sea_land_and_enclosed_lakes_only() -> None:
    for land_id in knownlands.land_ids():
        kinds = knownlands.source_kinds(land_id)
        assert set(np.unique(kinds).tolist()) <= {SEA, LAND, LAKE}, land_id
        share = int(np.count_nonzero(kinds == LAND)) * 1000 // kinds.size
        assert 100 <= share <= 900, land_id
        lake = kinds == LAKE
        assert not (distance_from(kinds == SEA, 2) < 2)[lake].any(), (
            f"a lake opens to the sea: {land_id}"
        )
        assert not kinds[[0, -1], :].any() or land_id, land_id


def test_an_unknown_land_is_refused() -> None:
    with pytest.raises(ValueError, match="no known land"):
        _ = knownlands.source_kinds("pangaea")
    with pytest.raises(ValueError, match="no known land"):
        _ = knownlands.known_land("pangaea", _area(), margin=MARGIN, speck=SPECK)


@pytest.mark.parametrize("land_id", knownlands.land_ids())
def test_every_land_lies_on_the_sheet_as_the_generator_will_take_it(land_id: str) -> None:
    area = _area()
    kinds = knownlands.known_land(land_id, area, margin=MARGIN, speck=SPECK)
    assert kinds.shape == area.picture_shape
    found = landeditor.check(kinds, area, SETTINGS)
    assert found.refusal == landeditor.NOTHING, land_id
    assert found.kept_percent == 100
    assert found.specks == 0
    assert found.open_lakes == ()
    land = IS_LAND_ARRAY[kinds]
    assert land.sum() * 1000 // kinds.size >= MIN_LAND_PERMILLE
    assert not land[~landeditor.usable_area(area.area.copy(), MARGIN)].any()
    assert np.array_equal(kinds, knownlands.known_land(land_id, area, margin=MARGIN, speck=SPECK))


def test_a_land_fills_about_its_share_of_the_usable_area() -> None:
    area = _area()
    usable = landeditor.usable_area(area.area.copy(), MARGIN)
    for land in knownlands.known_lands():
        kinds = knownlands.known_land(land.id, area, margin=MARGIN, speck=SPECK)
        filled = int(np.count_nonzero(IS_LAND_ARRAY[kinds])) * 1000 // int(usable.sum())
        if land.open:
            # A land whose map is cut runs on to the edges, and so may fill much more.
            assert 0.3 * land.share <= filled <= MOST_PERMILLE, (land.id, filled)
        else:
            assert 0.3 * land.share <= filled <= 1.15 * land.share, (land.id, filled)


def test_a_land_too_big_for_the_room_is_shrunk_to_lie_inside() -> None:
    area = _area()
    kinds = knownlands.place(
        knownlands.source_kinds("tamriel"), area, 900, margin=MARGIN, speck=SPECK
    )
    assert landeditor.check(kinds, area, SETTINGS).kept_percent == 100


def test_lakes_the_sea_reaches_are_closed() -> None:
    kinds = np.full((20, 20), LAND, dtype=np.uint8)
    kinds[:, :4] = SEA
    kinds[8:12, 3:9] = LAKE  # touches the sea on the left
    kinds[2:5, 10:14] = LAKE  # enclosed
    closed = knownlands.close_lakes(kinds)
    assert not (closed[8:12, 3:9] == LAKE).any()
    assert (closed[2:5, 10:14] == LAKE).all()


def _cut_land() -> np.ndarray:
    """A picture of a land cut at the top and the bottom, with a coast on the left and the right."""
    kinds = np.zeros((60, 80), dtype=np.uint8)
    kinds[:, 10:70] = LAND
    kinds[20:40, :10] = LAND  # a cape on the left
    return kinds


def test_a_land_whose_map_is_cut_runs_to_the_edges_of_the_usable_area() -> None:
    area = _area()
    usable = landeditor.usable_area(area.area.copy(), MARGIN)
    rows = np.nonzero(usable.any(axis=1))[0]
    top, bottom = int(rows.min()), int(rows.max())
    shut = knownlands.place(_cut_land(), area, 150, margin=MARGIN, speck=SPECK)
    runs = knownlands.place(_cut_land(), area, 150, margin=MARGIN, speck=SPECK, open_sides="ns")
    for kinds in (shut, runs):
        assert landeditor.check(kinds, area, SETTINGS).kept_percent == 100
    shut_land, runs_land = IS_LAND_ARRAY[shut], IS_LAND_ARRAY[runs]
    assert not (shut_land[top].any() and shut_land[bottom].any())
    assert runs_land[top].any()
    assert runs_land[bottom].any()
    # It still has a coast on the sides where the map has one.
    columns = np.nonzero(runs_land.any(axis=0))[0]
    assert columns.min() > 0
    assert columns.max() < runs.shape[1] - 1


def test_a_cut_on_one_side_reaches_only_that_edge() -> None:
    area = _area()
    usable = landeditor.usable_area(area.area.copy(), MARGIN)
    rows = np.nonzero(usable.any(axis=1))[0]
    top, bottom = int(rows.min()), int(rows.max())
    kinds = knownlands.place(_cut_land(), area, 150, margin=MARGIN, speck=SPECK, open_sides="n")
    land = IS_LAND_ARRAY[kinds]
    assert land[top].any()
    assert not land[bottom].any()
