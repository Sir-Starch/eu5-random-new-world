"""The optional ocean sector has fixed width and protects the installed Old World."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.eu5_canvas import select_canvas
from rnw.model import CellClass

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map


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
    assert np.array_equal(_mask(_map(), expanded=True), _mask(_map(shift=15), expanded=True))
    assert not np.array_equal(_mask(_map(), expanded=False), _mask(_map(shift=15), expanded=False))
