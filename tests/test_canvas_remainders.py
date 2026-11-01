"""A zone that the canvas cuts along its length leaves a needle, which the canvas takes whole."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.eu5_canvas import MIN_REMAINDER_PX, MIN_THICKNESS_PX, select_canvas
from rnw.model import CellClass

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map

BAND = 8


def _map(zone_width: int) -> Eu5Map:
    """America as a block, a sea zone beside it ``zone_width`` columns wide, far water, Africa."""
    labels = np.full((400, 900), 3, dtype=np.int32)
    labels[50:350, 100:140] = 1
    labels[50:350, 140 : 140 + zone_width] = 2
    labels[40:350, 800:850] = 0
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("old", "new", "strip", "far"),
                labels=labels,
                continents=(
                    "africa",
                    "america",
                    "pacific_ocean_continent",
                    "pacific_ocean_continent",
                ),
                classes=(CellClass.LAND, CellClass.LAND, CellClass.SEA, CellClass.SEA),
                ambiguous=np.array([False, False, False, False]),
            ),
        ),
    )


def test_a_needle_left_of_a_zone_is_taken_whole() -> None:
    game = _map(BAND + 14)  # 14 columns remain, about 300 rows tall: 4,200 px, 13 px thick
    left = int(np.count_nonzero(game.labels == 2)) - BAND * 300
    assert MIN_REMAINDER_PX < left < 2 * MIN_REMAINDER_PX
    canvas = select_canvas(game, BAND)
    assert canvas.removed[2]
    assert not canvas.trimmed[2]


def test_a_strip_thinner_than_a_core_of_vanillas_zones_is_taken_whole() -> None:
    game = _map(BAND + 26)  # 26 columns remain: 7,800 px, about 24 px thick (20 px passed once)
    assert MIN_THICKNESS_PX > 24
    canvas = select_canvas(game, BAND)
    assert canvas.removed[2]
    assert not canvas.trimmed[2]


def test_a_thick_remainder_stays_a_trimmed_zone_of_its_own() -> None:
    game = _map(BAND + 60)  # 60 columns remain: 18,000 px, about 55 px thick
    assert MIN_THICKNESS_PX < 55
    canvas = select_canvas(game, BAND)
    assert canvas.trimmed[2]
    assert not canvas.removed[2]
