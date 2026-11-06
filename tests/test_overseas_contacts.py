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
from rnw.eu5_overseas import overseas_flags, passable_contacts
from rnw.geography import Location
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


def _hierarchy() -> dict[str, Location]:
    def at(key: str, continent: str, subcontinent: str) -> Location:
        return Location(key, continent, subcontinent, "r", "a", "p")

    return {
        "rnw_sea": at("rnw_sea", "america", "north_america"),
        "closed_remainder": at("closed_remainder", "atlantic_ocean_continent", "n_atlantic"),
        "europe_sea": at("europe_sea", "europe", "western_europe"),
        "open_sea": at("open_sea", "pacific_ocean_continent", "n_pacific"),
        "rnw_land": at("rnw_land", "america", "south_america"),
    }


KEYS = ["rnw_sea", "closed_remainder", "europe_sea", "open_sea", "rnw_land"]


def test_flags_leave_out_ocean_impassable_exempt_and_unlisted_locations() -> None:
    flags = overseas_flags([*KEYS, "unlisted"], _hierarchy(), {"rnw_land"}, {"europe_sea"})
    assert flags.tolist() == [1, 0, 0, 0, 0, 0]
    assert overseas_flags(KEYS, _hierarchy(), set()).tolist() == [1, 0, 2, 0, 1]


def test_recoloured_remainder_hides_a_contact_only_from_the_held_labels() -> None:
    """A closed remainder that joins a European sea in the file touches America there."""
    held = np.array([[3, 0, 1, 1, 2, 3]], dtype=np.int32)
    written = np.array([[3, 0, 2, 2, 2, 3]], dtype=np.int32)
    flags = overseas_flags(KEYS, _hierarchy(), set())
    assert passable_contacts(held, flags) == []
    assert passable_contacts(written, flags) == [(0, 2)]
    assert (
        passable_contacts(written, overseas_flags(KEYS, _hierarchy(), set(), {"europe_sea"})) == []
    )


def test_contacts_are_found_across_rows_bands_and_the_wrap() -> None:
    flags = overseas_flags(KEYS, _hierarchy(), set())
    vertical = np.full((7, 3), 3, dtype=np.int32)
    vertical[4, 1], vertical[5, 1] = 0, 2
    assert passable_contacts(vertical, flags, band=2) == [(0, 2)]
    assert passable_contacts(vertical, flags, band=1) == [(0, 2)]
    wrapped = np.array([[2, 3, 3, 0], [3, 3, 3, 3]], dtype=np.int32)
    assert passable_contacts(wrapped, flags) == [(0, 2)]
    diagonal = np.array([[0, 3], [3, 2]], dtype=np.int32)
    assert passable_contacts(diagonal, flags) == []
    land_and_sea = np.array([[0, 4, 3]], dtype=np.int32)
    assert passable_contacts(land_and_sea, flags) == []
