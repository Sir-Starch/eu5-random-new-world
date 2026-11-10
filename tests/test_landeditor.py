"""The editor's presets, decoration, checks and imports, on a synthetic area."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import landeditor
from rnw.landarea import EDITOR_STEP, TEMPLATE_STEP, LandArea
from rnw.landeditor import usable_area
from rnw.landmask import (
    HIGHLANDS,
    LAKE,
    LAND,
    LOWLANDS,
    MOUNTAINS,
    SEA,
    LandMask,
    from_kinds,
)
from rnw.settings import PRESETS

SETTINGS = PRESETS["continents"].new_world


def _area() -> LandArea:
    """A canvas of 1920 by 2400 pixels: a wide area with the Americas and an island group in it."""
    area = np.zeros((480, 600), dtype=np.bool_)
    area[20:-20, 20:-20] = True
    americas = np.zeros_like(area)
    americas[180:380, 60:160] = True
    islands = np.zeros_like(area)
    islands[100:112, 300:312] = True
    return LandArea((480 * TEMPLATE_STEP, 600 * TEMPLATE_STEP), area, americas, islands).at(
        EDITOR_STEP
    )


def test_every_preset_fills_its_share_of_the_usable_area_and_keeps_off_the_edge() -> None:
    area = _area()
    assert area.picture_shape == (240, 300)
    usable = usable_area(area.area.copy(), 6)
    for name in landeditor.PRESETS:
        kinds = landeditor.make_preset(name, area, 7, margin=6)
        assert kinds.shape == area.picture_shape
        assert set(np.unique(kinds).tolist()) <= {SEA, LAND}
        land = kinds == LAND
        assert not (land & ~usable).any(), name
        share = land.sum() * 1000 // usable.sum()
        wanted = landeditor.SHARES[name]
        assert wanted * 0.5 < share < wanted * 1.4, (name, share)
        assert np.array_equal(kinds, landeditor.make_preset(name, area, 7, margin=6))
        assert not np.array_equal(kinds, landeditor.make_preset(name, area, 8, margin=6)), name


def test_a_preset_that_does_not_exist_or_has_no_room_is_refused() -> None:
    area = _area()
    with pytest.raises(ValueError, match="no preset"):
        _ = landeditor.make_preset("pangaea", area, 1)
    nothing = LandArea(area.shape, np.zeros_like(area.area), area.americas, area.islands)
    with pytest.raises(ValueError, match="No area is left"):
        _ = landeditor.make_preset(landeditor.SUPERCONTINENT, nothing, 1)


def test_the_installed_americas_are_a_land_to_start_from() -> None:
    area = _area()
    kinds = landeditor.americas(area)
    assert np.array_equal(kinds == LAND, area.americas & area.area)


def test_decoration_adds_ground_to_plain_land_and_keeps_what_was_painted() -> None:
    area = _area()
    base = landeditor.make_preset(landeditor.SUPERCONTINENT, area, 3)
    base[60:70, 100:110] = LOWLANDS
    base[40:44, 120:130] = LAKE
    done = landeditor.decorate(base, 11, lowlands=True)
    changed = done != base
    assert (base[changed] == LAND).all()
    assert np.array_equal(done[base != LAND], base[base != LAND])
    for kind in (MOUNTAINS, HIGHLANDS, LOWLANDS, LAKE):
        assert (done == kind).sum() > (base == kind).sum(), kind
    again = landeditor.decorate(base, 11, lowlands=True)
    assert np.array_equal(done, again)
    assert not np.array_equal(done, landeditor.decorate(base, 12, lowlands=True))
    lakes = (done == LAKE) & (base != LAKE)
    ring = landeditor._dilate(lakes, 2) & ~lakes  # pyright: ignore[reportPrivateUsage]
    assert (done[ring] != SEA).all()
    only = landeditor.decorate(base, 11, mountains=False, highlands=False, lakes=False)
    assert not (only == MOUNTAINS).any()
    assert not (only == HIGHLANDS).any()
    sea = np.zeros(area.picture_shape, dtype=np.uint8)
    assert np.array_equal(landeditor.decorate(sea, 1), sea)


def test_the_check_reports_what_the_generator_will_do() -> None:
    area = _area()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[60:180, 70:200] = LAND
    found = landeditor.check(kinds, area, SETTINGS)
    assert found.refusal == landeditor.NOTHING
    assert found.kept_percent == 100
    assert found.specks == 0
    assert found.outside_permille == 0
    assert found.open_lakes == ()
    assert found.land_permille == (120 * 130) * 1000 // kinds.size
    kinds[100:104, 100:104] = LAKE
    kinds[70:72, 210:212] = LAND
    found = landeditor.check(kinds, area, SETTINGS)
    assert found.lakes == 16
    assert found.specks >= 1
    assert found.open_lakes == ()
    assert found.refusal == landeditor.NOTHING


def test_land_outside_the_area_or_in_its_margin_is_counted_and_refused_when_it_is_most() -> None:
    area = _area()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[60:180, 70:200] = LAND
    kinds[5:30, 5:12] = LAND
    found = landeditor.check(kinds, area, SETTINGS)
    assert found.outside_permille > 0
    assert found.refusal == landeditor.NOTHING
    edge = np.zeros(area.picture_shape, dtype=np.uint8)
    edge[3:16, 3:290] = LAND
    found = landeditor.check(edge, area, SETTINGS)
    assert found.refusal == landeditor.OUTSIDE
    assert found.kept_percent < 50


def test_a_picture_with_too_little_or_too_much_land_has_no_world() -> None:
    area = _area()
    empty = np.zeros(area.picture_shape, dtype=np.uint8)
    assert landeditor.check(empty, area, SETTINGS).refusal == landeditor.NO_LAND
    full = np.full(area.picture_shape, LAND, dtype=np.uint8)
    assert landeditor.check(full, area, SETTINGS).refusal == landeditor.NO_LAND


def test_a_lake_that_opens_to_the_sea_is_found_where_it_is() -> None:
    area = _area()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[60:180, 70:200] = LAND
    kinds[100:110, 60:90] = LAKE
    found = landeditor.check(kinds, area, SETTINGS)
    assert found.refusal == landeditor.OPEN_LAKE
    ((column, row),) = found.open_lakes
    assert 60 <= column < 90
    assert 100 <= row < 110


def test_island_groups_that_new_land_reaches_are_counted() -> None:
    area = _area()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[60:180, 70:200] = LAND
    assert landeditor.check(kinds, area, SETTINGS).islands_touched == 0
    kinds[50:70, 148:170] = LAND
    kinds[40:70, 148:152] = LAND
    assert landeditor.check(kinds, area, SETTINGS).islands_touched == 1


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="none of the"):
        _ = landeditor.check(np.full(_area().picture_shape, 9, np.uint8), _area(), SETTINGS)


def _mask(shape: tuple[int, int]) -> LandMask:
    kinds = np.zeros(shape, dtype=np.uint8)
    kinds[shape[0] // 4 : 3 * shape[0] // 4, shape[1] // 4 : 3 * shape[1] // 4] = LAND
    kinds[shape[0] // 2, shape[1] // 2] = MOUNTAINS
    return from_kinds(kinds)


def test_a_picture_is_laid_on_the_sheet_by_its_proportions() -> None:
    sheet = (240, 300)
    exact, how = landeditor.to_editor(_mask(sheet), sheet)
    assert how == "exact"
    assert exact.shape == sheet
    stretched, how = landeditor.to_editor(_mask((480, 600)), sheet)
    assert how == "stretched"
    assert stretched.shape == sheet
    assert stretched[120, 150] in {LAND, MOUNTAINS}
    near, how = landeditor.to_editor(_mask((300, 300)), sheet)
    assert how == "centered"
    assert near.shape == sheet
    assert not near[:, :30].any()
    assert not near[:, -30:].any()
    assert near[120, 150] in {LAND, MOUNTAINS}
    plain, how = landeditor.to_editor(
        from_kinds(np.where(_mask(sheet).land, LAND, SEA).astype(np.uint8)), sheet
    )
    assert how == "exact"
    assert plain.max() == LAND


def test_a_sketch_becomes_kinds() -> None:
    picture = np.zeros((4, 5, 3), dtype=np.uint8)
    picture[:] = (30, 58, 110)
    picture[1, 1] = (110, 160, 80)
    picture[2, 2] = (70, 120, 190)
    kinds = landeditor.from_sketch(picture, lake=(70, 120, 190), land=(110, 160, 80))
    assert kinds[1, 1] == LAND
    assert kinds[2, 2] == LAKE
    assert kinds[0, 0] == SEA
