"""Colonial overseas eligibility depends on passable final-map contacts."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.eu5_nw_export import (
    NewWorldExportError,
    _check_overseas_contacts,  # pyright: ignore[reportPrivateUsage]
)
from rnw.model import CellClass
from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan


@pytest.mark.parametrize("subcontinent", ["north_america", "south_america"])
def test_passable_greenland_sea_border_blocks_overseas(subcontinent: str) -> None:
    game_map = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("greenland_high_sea", "baffin_bay"),
                classes=(CellClass.SEA, CellClass.WASTELAND),
                continents=("europe", "europe"),
            ),
        ),
    )
    plan = cast(
        "Plan",
        cast(
            "object",
            SimpleNamespace(
                cells=[
                    SimpleNamespace(
                        key="rnw_sea",
                        kind=CellClass.SEA,
                        continent="america",
                        subcontinent=subcontinent,
                    ),
                    SimpleNamespace(
                        key="rnw_ocean", kind=CellClass.SEA, continent="atlantic_ocean_continent"
                    ),
                ]
            ),
        ),
    )
    # First and last columns touch through horizontal world wrap.
    raster = np.array([[0, 3, 1, 2]], dtype=np.int32)
    contacts = set(unpack_pairs(adjacency_pairs(raster, wrap_x=True)))
    with pytest.raises(NewWorldExportError, match="greenland_high_sea / rnw_sea"):
        _check_overseas_contacts(game_map, plan, set(), contacts)
    _check_overseas_contacts(game_map, plan, {0}, contacts)
    _check_overseas_contacts(game_map, plan, set(), {(1, 2), (0, 3), (2, 3)})
