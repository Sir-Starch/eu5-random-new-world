"""The shared canvas preserves land ownership and resolves overlapping coastal domains."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

from itertools import combinations
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.continent_domains import (
    CONTINENTS,
    Domain,
    _coastal_claim,  # pyright: ignore[reportPrivateUsage]
    _coastal_waters,  # pyright: ignore[reportPrivateUsage]
    plan_domains,
)
from rnw.eu5_biomes import EQUATOR_ROW, block_features, climate_grid, land_features, latitude_tenths
from rnw.eu5_canvas import CanvasError, select_canvas
from rnw.model import CellClass
from rnw.settings import PRESETS

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map
    from rnw.settings import NewWorldSettings


def test_a_water_pocket_inside_retained_land_is_outside_the_american_claim() -> None:
    marine = np.ones((9, 11), dtype=bool)
    marine[2:7, 2:7] = False
    marine[4, 4] = True
    footprint = np.zeros_like(marine)
    footprint[5, 9] = True
    claimed = marine | footprint
    protected = _coastal_claim(claimed, footprint, marine)
    assert not protected[4, 4]
    assert protected[0, 0]
    assert protected[5, 9]
    assert np.count_nonzero(claimed ^ protected) == 1


def _map() -> Eu5Map:
    labels = np.zeros((400, 800), dtype=np.int32)
    labels[40:350, 190:245] = 1
    labels[70:290, 620:724] = 2
    labels[45:70, 660:715] = 3
    labels[205:228, :42] = 4
    labels[205:228, -25:] = 4
    labels[270:325, 16:108] = 4
    labels[180:188, 695:703] = 5
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("ocean", "america", "africa", "asia", "oceania", "lake"),
                labels=labels,
                continents=(
                    "pacific_ocean_continent",
                    "america",
                    "africa",
                    "asia",
                    "oceania",
                    "africa",
                ),
                classes=(CellClass.SEA, *(CellClass.LAND for _ in range(4)), CellClass.LAKE),
                ambiguous=np.array([True, False, False, False, False, False]),
            ),
        ),
    )


def _settings(names: tuple[str, ...]) -> dict[str, NewWorldSettings]:
    return {name: PRESETS[CONTINENTS[name].preset].new_world for name in names}


def _in_world(
    domain: Domain, local: NDArray[np.bool_], shape: tuple[int, int]
) -> NDArray[np.bool_]:
    result = np.zeros(shape, dtype=bool)
    for crop, original in domain.spans():
        result[domain.rows, original] = local[:, crop]
    return result


SELECTIONS = tuple(
    names for size in range(1, len(CONTINENTS) + 1) for names in combinations(CONTINENTS, size)
)


@pytest.mark.parametrize("names", SELECTIONS)
def test_all_selections_cover_their_land_once(names: tuple[str, ...]) -> None:
    game = _map()
    labels = game.labels
    domains = plan_domains(game, _settings(names[::-1]))
    assert tuple(domain.continent.key for domain in domains) == names
    owners = np.full(labels.shape, -1, dtype=np.int8)
    for index, domain in enumerate(domains):
        mask = _in_world(domain, domain.mask, labels.shape)
        footprint = _in_world(domain, domain.footprint, labels.shape)
        member = np.array([tag == domain.continent.key for tag in game.continents], dtype=bool)
        assert np.array_equal(footprint, member[labels])
        assert not np.any(footprint & ~mask)
        assert np.all(owners[mask] == -1)
        assert not np.any(mask & (labels == 3))
        if names != ("america",):
            assert not np.any(mask & ~(member[labels] | (labels == 0)))
        owners[mask] = index


def test_original_african_land_interface_and_oceanian_wrap() -> None:
    game = _map()
    africa, oceania = plan_domains(game, _settings(("africa", "oceania")))
    assert africa.land_interface is not None
    interface = _in_world(africa, africa.land_interface, game.labels.shape)
    expected = np.zeros(game.labels.shape, dtype=bool)
    expected[70, 660:715] = True
    assert np.array_equal(interface, expected)
    assert oceania.land_interface is None
    assert oceania.seam is not None
    assert oceania.first_row > 0
    rows = slice(205 - oceania.first_row, 228 - oceania.first_row)
    assert np.all(oceania.footprint[rows, oceania.seam - 1 : oceania.seam + 1])


def test_america_only_uses_the_current_canvas() -> None:
    game = _map()
    selected = _settings(("america",))
    (domain,) = plan_domains(game, selected)
    expected = select_canvas(game, selected["america"].ocean_band_px, expanded=True)
    assert domain.legacy_canvas is not None
    assert np.array_equal(domain.mask, expected.mask)
    assert domain.spans() == tuple(expected.spans())
    assert [(group.locations, group.zones) for group in domain.legacy_canvas.groups] == [
        (group.locations, group.zones) for group in expected.groups
    ]
    assert np.array_equal(domain.legacy_canvas.removed, expected.removed)


def test_small_islands_do_not_claim_the_full_continental_band() -> None:
    footprint = np.zeros((48, 64), dtype=bool)
    footprint[10:20, 10:20] = True
    footprint[25:27, 40:42] = True
    seas = ~footprint
    seas[23, 13] = False  # A retained location in the large landmass's band.
    coastal = _coastal_waters(footprint, seas, reach=8, island_reach=3, continental_area=64)
    assert coastal[26, 12]
    assert coastal[29, 40]
    assert not coastal[30, 40]
    assert not coastal[23, 13]
    assert not np.any(coastal & footprint)


def test_continents_resolve_their_own_presets() -> None:
    selected = {
        "america": CONTINENTS["america"].geography("wall"),
        "africa": CONTINENTS["africa"].geography("archipelago"),
        "oceania": CONTINENTS["oceania"].geography("supercontinent"),
    }
    assert selected["america"] == PRESETS["wall"].new_world
    assert selected["africa"].land_permille == PRESETS["archipelago"].new_world.land_permille
    assert selected["oceania"].land_permille == PRESETS["supercontinent"].new_world.land_permille
    assert not selected["africa"].expand_oceans
    assert not selected["oceania"].expand_oceans


@pytest.mark.parametrize("name", ["wall", "omerika"])
def test_american_landforms_cannot_be_applied_to_other_continents(name: str) -> None:
    for key in ("africa", "oceania"):
        with pytest.raises(CanvasError, match="American options"):
            _ = CONTINENTS[key].geography(name)
        with pytest.raises(CanvasError, match="American options"):
            _ = plan_domains(_map(), {key: PRESETS[name].new_world})


@pytest.mark.parametrize("names", [(), ("asia",)])
def test_rejects_empty_and_unsupported_selections(names: tuple[str, ...]) -> None:
    selected = dict.fromkeys(names, PRESETS["continents"].new_world)
    with pytest.raises(CanvasError, match="Choose at least one supported continent"):
        _ = plan_domains(_map(), selected)


def test_window_climate_and_cell_size_votes_use_global_latitude() -> None:
    land = np.zeros((64, 64), dtype=bool)
    land[3:12, 5:25] = True
    heights = np.full(land.shape, 7000, dtype=np.int32)
    row0 = EQUATOR_ROW - 256
    grid = climate_grid(~land, heights, seasonal=True, row0=row0)
    points = np.array([[7, 12]], dtype=np.int64)
    cell = land_features(grid, points, np.array([7000], dtype=np.int64))
    assert cell[0, 0] == latitude_tenths(np.array([row0 + points[0, 0]]))[0]
    regional, local = block_features(land, heights, grid)
    legacy, base = block_features(land, heights, climate_grid(~land, heights, seasonal=True))
    assert np.array_equal(regional, legacy)
    assert np.all(local[:, 0] < base[:, 0])
