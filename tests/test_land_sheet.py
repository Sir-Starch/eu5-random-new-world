"""The classic window's land sheet: the tools, the rules of terrain and the undo."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.gui.land_sheet import (
    HIGHLANDS,
    KINDS,
    LAKE,
    LAND,
    MOUNTAINS,
    SEA,
    SHOWN,
    Rule,
    Sheet,
)
from rnw.landmask import KIND_COLORS


def test_a_dab_is_round_and_stays_on_the_sheet() -> None:
    sheet = Sheet(20, 20)
    sheet.stamp(10, 10, 1, LAND)
    assert sheet.counts()[LAND] == 1
    sheet.stamp(10, 10, 7, LAND)
    shape = sheet.kinds[7:14, 7:14] == LAND
    assert shape[3, 0]
    assert shape[3, 6]
    assert shape[0, 3]
    assert shape[6, 3]
    assert not shape[0, 0]
    assert not shape[6, 6]
    edge = Sheet(10, 10)
    edge.stamp(0, 0, 5, LAND)
    assert edge.get(2, 0) == LAND
    assert edge.get(-1, 0) == SEA
    assert edge.counts()[LAND] == int((edge.kinds == LAND).sum())
    Sheet(10, 10).stamp(-30, 4, 5, LAND)  # wholly outside: nothing, no error


def test_a_stroke_leaves_no_gaps_whatever_its_size() -> None:
    for size in (1, 4, 9):
        sheet = Sheet(120, 60)
        sheet.stroke(5, 5, 110, 50, size, LAND)
        columns = np.flatnonzero((sheet.kinds == LAND).any(axis=0))
        assert columns.min() <= 5
        assert columns.max() >= 110
        assert np.array_equal(columns, np.arange(columns.min(), columns.max() + 1))


def test_terrain_is_painted_on_ground_only_when_the_rule_says_so() -> None:
    sheet = Sheet(12, 12)
    sheet.rectangle(2, 2, 5, 5, 1, LAND)
    sheet.stamp(5, 5, 5, MOUNTAINS)
    assert sheet.get(4, 4) == MOUNTAINS
    assert sheet.get(7, 7) == SEA  # the sea took none of it
    _ = sheet.fill(0, 0, LAKE)
    assert sheet.get(0, 0) == LAKE
    sheet.stamp(0, 0, 3, HIGHLANDS)
    assert sheet.get(0, 0) == LAKE  # nor did a lake
    loose = Rule(terrain_on_ground=False)
    sheet.stamp(0, 0, 3, HIGHLANDS, loose)
    assert sheet.get(0, 0) == HIGHLANDS
    sheet.stamp(0, 0, 3, SEA)
    assert sheet.get(0, 0) == SEA  # the eraser paints over anything


def test_a_rectangle_and_an_ellipse_are_filled_or_outlines() -> None:
    sheet = Sheet(40, 30)
    sheet.rectangle(20, 10, 5, 3, 1, LAND)  # corners in any order
    assert (sheet.kinds[3:11, 5:21] == LAND).all()
    assert sheet.counts()[LAND] == 8 * 16
    outline = Sheet(40, 30)
    outline.rectangle(5, 3, 20, 10, 2, LAND, Rule(filled=False))
    assert outline.get(5, 3) == LAND
    assert outline.get(12, 6) == SEA
    disc = Sheet(40, 30)
    disc.ellipse(5, 5, 25, 15, 1, LAND)
    assert disc.get(15, 10) == LAND
    assert disc.get(5, 5) == SEA  # the corner of the box is outside it
    ring = Sheet(40, 30)
    ring.ellipse(5, 5, 25, 15, 3, LAND, Rule(filled=False))
    assert ring.get(15, 10) == SEA
    assert ring.get(5, 10) == LAND
    assert 0 < ring.counts()[LAND] < disc.counts()[LAND]
    tiny = Sheet(10, 10)
    tiny.ellipse(4, 4, 4, 4, 1, LAND)
    assert tiny.counts()[LAND] == 1


def test_a_fill_takes_the_stretch_of_equal_pixels_and_nothing_across_a_wall() -> None:
    sheet = Sheet(20, 10)
    sheet.rectangle(10, 0, 10, 9, 1, LAND)  # a wall splits the sea in two
    painted = sheet.fill(2, 4, LAKE)
    assert painted == 10 * 10
    assert (sheet.kinds[:, :10] == LAKE).all()
    assert (sheet.kinds[:, 11:] == SEA).all()
    assert sheet.fill(2, 4, LAKE) == 0  # nothing to change
    assert sheet.fill(-1, 4, LAKE) == 0
    box = sheet.take_dirty()
    assert box is not None
    assert (box.x0, box.y0, box.x1, box.y1) == (0, 0, 10, 9)


def test_a_change_is_one_step_of_the_undo_and_can_be_redone() -> None:
    sheet = Sheet(30, 30)
    assert not sheet.can_undo
    sheet.begin()
    assert sheet.drawing
    sheet.stroke(2, 2, 25, 25, 3, LAND)
    assert sheet.commit()
    after = sheet.kinds.copy()
    assert not sheet.drawing
    assert sheet.can_undo
    assert sheet.undo()
    assert sheet.empty
    assert sheet.can_redo
    assert sheet.redo()
    assert np.array_equal(sheet.kinds, after)
    assert not sheet.redo()
    sheet.begin()
    assert not sheet.commit()  # nothing drawn: no step
    sheet.begin()
    sheet.stamp(28, 4, 3, MOUNTAINS)  # not on ground, so nothing
    assert not sheet.commit()
    assert sheet.undo()
    assert not sheet.undo()


def test_a_shape_in_the_making_is_redrawn_from_its_start_and_can_be_dropped() -> None:
    sheet = Sheet(30, 30)
    sheet.begin()
    sheet.rectangle(2, 2, 10, 10, 1, LAND)
    sheet.restore()
    assert sheet.empty
    sheet.rectangle(2, 2, 20, 20, 1, LAND)
    assert sheet.counts()[LAND] == 19 * 19
    sheet.cancel()
    assert sheet.empty
    assert not sheet.drawing
    assert not sheet.can_undo


def test_a_new_change_ends_the_redo_and_the_undo_is_bounded() -> None:
    sheet = Sheet(10, 10)
    for step in range(100):
        sheet.begin()
        sheet.stamp(step % 10, step // 10, 1, LAND)
        assert sheet.commit()
    undone = 0
    while sheet.undo():
        undone += 1
    assert undone == 80  # MAX_UNDO
    assert sheet.redo()
    sheet.begin()
    sheet.stamp(5, 5, 1, LAKE)
    assert sheet.commit()
    assert not sheet.can_redo


def test_a_picture_replaces_the_sheet_as_one_step_and_only_its_size_fits() -> None:
    sheet = Sheet(10, 6)
    picture = np.full((6, 10), LAND, dtype=np.uint8)
    assert sheet.replace(picture)
    assert not sheet.replace(picture)
    box = sheet.take_dirty()
    assert box is not None
    assert (box.x1, box.y1) == (9, 5)
    assert sheet.clear()
    assert sheet.empty
    assert sheet.undo()
    assert (sheet.kinds == LAND).all()
    with pytest.raises(ValueError, match="size"):
        _ = sheet.replace(np.zeros((3, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="size"):
        _ = Sheet(4, 4, np.zeros((3, 3), dtype=np.uint8))


def test_the_sheet_reports_what_changed_for_the_canvas() -> None:
    sheet = Sheet(40, 40)
    assert sheet.take_dirty() is None
    sheet.stamp(10, 10, 3, LAND)
    sheet.stamp(30, 20, 3, LAND)
    box = sheet.take_dirty()
    assert box is not None
    assert (box.x0, box.y0, box.x1, box.y1) == (9, 9, 31, 21)
    assert sheet.take_dirty() is None
    assert sheet.counts()[SEA] + sheet.counts()[LAND] == 1600


def test_the_editor_shows_what_the_generator_reads() -> None:
    assert len(SHOWN) == KINDS == len(KIND_COLORS)
    assert SHOWN[SEA][3] == 0  # the sea lets the area under it show
    assert all(SHOWN[kind][3] > 200 for kind in range(1, KINDS))
