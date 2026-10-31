"""The expanded canvas keeps its Atlantic sector, adds a Pacific side and covers island groups."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.eu5_canvas import open_map, select_canvas, settle_islands
from rnw.eu5_map import Eu5Map
from rnw.eu5_pacific import within
from rnw.model import CellClass

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _map(*, shift: int = 0) -> Eu5Map:
    labels = np.full((400, 800), 2, dtype=np.int32)
    labels[30:130, 160 + shift : 220 + shift] = 1
    labels[130:360, 200 + shift : 220 + shift] = 1
    labels[40:350, 620:710] = 0
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("old", "new", "ocean"),
                labels=labels,
                continents=("africa", "america", "pacific_ocean_continent"),
                classes=(CellClass.LAND, CellClass.LAND, CellClass.SEA),
                ambiguous=np.array([False, False, True]),
            ),
        ),
    )


def _mask(game: Eu5Map, *, expanded: bool) -> NDArray[np.bool_]:
    canvas = select_canvas(game, 8, expanded=expanded)
    target = np.zeros(game.labels.shape, dtype=bool)
    canvas.put(target, np.ones(canvas.mask.shape, dtype=bool))
    return target


def test_expansion_supplies_southern_width_and_preserves_protected_pixels() -> None:
    game = _map()
    old = _mask(game, expanded=False)
    wide = _mask(game, expanded=True)
    assert not old[300, 100]
    assert wide[300, 100]
    assert not np.any(wide[game.labels == 0])
    assert np.all(wide[game.labels == 1])
    assert np.count_nonzero(wide) > 2 * np.count_nonzero(old)


def test_sector_does_not_move_with_the_original_american_coast() -> None:
    # The Pacific side lies on the other side of the map seam; the sector and the band stay.
    east = slice(260, 600)
    assert np.array_equal(
        _mask(_map(), expanded=True)[:, east], _mask(_map(shift=15), expanded=True)[:, east]
    )
    assert not np.array_equal(_mask(_map(), expanded=False), _mask(_map(shift=15), expanded=False))


def _pacific() -> Eu5Map:
    """America, an Old World block with a bay, and an island with its coast and a high sea."""
    labels = np.full((400, 800), 2, dtype=np.int32)  # pacific ocean
    labels[40:350, 200:240] = 1  # america
    labels[40:350, 700:760] = 0  # the Old World, east
    labels[100:150, 90:140] = 0  # Old World land in the Pacific, a bay between its two parts
    labels[180:230, 90:140] = 0
    labels[200:204, 20:26] = 3  # an island before the seam...
    labels[198:206, 18:28] = np.where(labels[198:206, 18:28] == 3, 3, 4)  # ...and its coast zone
    labels[300:340, 10:60] = 5  # a high sea of oceania
    return Eu5Map(
        keys=("old", "new", "ocean", "isle", "isle_coast", "high_sea"),
        colors=np.zeros(6, dtype=np.int64),
        classes=(
            CellClass.LAND,
            CellClass.LAND,
            CellClass.SEA,
            CellClass.LAND,
            CellClass.SEA,
            CellClass.SEA,
        ),
        ambiguous=np.array([False, False, True, False, False, False]),
        continents=(
            "africa",
            "america",
            "pacific_ocean_continent",
            "oceania",
            "oceania",
            "oceania",
        ),
        rgb=np.zeros((*labels.shape, 3), dtype=np.uint8),
        labels=labels,
        rivers=np.zeros(labels.shape, dtype=np.uint8),
        locations_chunks=(),
        rivers_chunks=(),
        points=(),
        inputs=(),
    )


def test_the_pacific_side_covers_an_island_group_and_settling_leaves_it_in_place() -> None:
    game = _pacific()
    canvas = select_canvas(game, 8, expanded=True)
    assert [(group.locations, group.zones) for group in canvas.groups] == [((3,), (4,))]
    covered = np.zeros(game.labels.shape, dtype=bool)
    canvas.put(covered, np.ones(canvas.mask.shape, dtype=bool))
    assert covered[200:204, 20:26].all()
    assert canvas.removed[3]
    settled = settle_islands(game, canvas)
    kept = np.zeros(game.labels.shape, dtype=bool)
    settled.put(kept, np.ones(settled.mask.shape, dtype=bool))
    assert not kept[game.labels == 3].any()
    assert not kept[game.labels == 4].any()
    assert kept[200, 40]
    assert not settled.removed[3]
    assert not settled.removed[4]
    assert not settled.trimmed[4]


def test_the_pacific_side_keeps_a_buffer_round_old_world_land_and_drops_narrow_bays() -> None:
    game = _pacific()
    canvas = select_canvas(game, 8, expanded=True)
    mask = np.zeros(game.labels.shape, dtype=bool)
    canvas.put(mask, np.ones(canvas.mask.shape, dtype=bool))
    assert not mask[game.labels == 0].any()
    land = game.labels == 0
    assert not within(land, 6)[mask].any()
    assert mask[170, 20]
    assert not mask[158:172, 104:124].any()
    assert mask[:, 0].any()


def test_open_map_counts_the_taken_oceanian_waters_as_ocean() -> None:
    game = _pacific()
    canvas = settle_islands(game, select_canvas(game, 8, expanded=True))
    assert canvas.removed[5]
    opened = open_map(game, canvas)
    assert opened.continents[5] == "pacific_ocean_continent"
    assert opened.continents[3:5] == ("oceania", "oceania")
    assert game.continents[5] == "oceania"
