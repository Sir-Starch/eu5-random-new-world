"""Omerika keeps the Americas' general shape, and the two great landmasses stay joined."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import omerika
from rnw.app import controls
from rnw.app.worldcode import WorldCode, decode, encode
from rnw.newworld import land_stage
from rnw.settings import (
    PRESETS,
    WORLD_TYPES,
    NewWorldSettings,
    SettingsError,
    build_settings,
    run_spec,
)
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from numpy.typing import NDArray

HEIGHT, WIDTH = 2100, 2000


def _americas() -> NDArray[np.bool_]:
    """A synthetic two-continent canvas: a northern and a southern disc joined by a thin neck."""
    ys, xs = np.mgrid[:HEIGHT, :WIDTH]
    north = (ys - 520) ** 2 + (xs - 800) ** 2 < 470**2
    south = (ys - 1560) ** 2 + (xs - 1050) ** 2 < 420**2
    neck = np.zeros((HEIGHT, WIDTH), dtype=bool)
    for y in range(520, 1560):
        centre = 800 + (1050 - 800) * (y - 520) // 1040
        neck[y, centre - 30 : centre + 30] = True
    return north | south | neck


@pytest.fixture(scope="module")
def americas() -> NDArray[np.bool_]:
    return _americas()


@pytest.fixture(scope="module")
def settings() -> NewWorldSettings:
    return PRESETS["omerika"].new_world


def test_omerika_is_a_world_type_whose_land_follows_a_template() -> None:
    assert "omerika" in WORLD_TYPES
    assert PRESETS["omerika"].new_world.template_permille > 0
    for other in WORLD_TYPES:
        if other != "omerika":
            assert PRESETS[other].new_world.template_permille == 0


def test_a_world_without_a_template_keeps_the_settings_document_it_had() -> None:
    document = cast("dict[str, dict[str, int]]", PRESETS["continents"].to_json_data())
    assert "template_permille" not in document["new_world"]
    shaped = cast("dict[str, dict[str, int]]", PRESETS["omerika"].to_json_data())
    assert shaped["new_world"]["template_permille"] == 500
    assert run_spec(1, PRESETS["continents"]) == run_spec(1, build_settings("continents", {}))


def test_the_template_cannot_be_combined_with_a_drawn_land_or_the_wall() -> None:
    with pytest.raises(SettingsError, match="drawn land mask"):
        _ = build_settings("omerika", {"mask": {"id": 5}})
    with pytest.raises(SettingsError, match="Wall"):
        _ = build_settings("omerika", {"new_world": {"landform": 1}})


def test_a_world_code_carries_omerika_and_its_likeness() -> None:
    code = WorldCode("omerika", 42, "1.2.0", {"new_world": {"template_permille": 350}})
    again = decode(encode(code))
    assert again.preset == "omerika"
    assert again.settings().new_world.template_permille == 350


def test_the_likeness_control_is_an_omerika_control_inside_the_validator_range() -> None:
    control = controls.BY_KEY["new_world.template_permille"]
    assert control.group == "omerika"
    assert control.allows(control.default("omerika"))
    assert controls.estimated_locations(PRESETS["omerika"]) <= controls.LOCATION_BUDGET


def test_the_template_is_prepared_the_same_way_every_time_and_by_seed(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    first = omerika.prepare(americas, 7, settings)
    again = omerika.prepare(americas, 7, settings)
    other = omerika.prepare(americas, 8, settings)
    assert np.array_equal(first.field, again.field)
    assert first.route == again.route
    assert not np.array_equal(first.field, other.field)


def test_the_template_finds_a_route_through_the_neck_between_the_two_great_landmasses(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    template = omerika.prepare(americas, 7, settings)
    assert template.route
    rows = np.array([row for row, _ in template.route]) * omerika.ROUTE_STEP
    # It runs from the middle of one disc to the middle of the other, through the neck.
    assert int(rows.min()) < 800
    assert int(rows.max()) > 1300
    # The route is a chain of neighbouring cells.
    assert all(
        abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1
        for a, b in zip(template.route, template.route[1:], strict=False)
    )
    # What the land must keep joined is the neck, not the stretch of the route inside a continent.
    assert 0 < len(template.joint[0]) < len(template.route)
    assert set((template.joint[0] // omerika.ROUTE_STEP).tolist()) <= {
        row for row, _ in template.route
    }


def test_the_field_is_land_inside_the_template_and_sea_far_from_it(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    template = omerika.prepare(americas, 7, settings)
    relief = np.zeros((HEIGHT, WIDTH), dtype=np.int32)
    omerika.add_to(relief, template)
    # The warp moves the template by at most the weakest likeness's amplitude, so the discs' own
    # centres, far inside them, stay land and the far corner stays sea.
    assert relief[520, 800] > 0
    assert relief[1560, 1050] > 0
    assert relief[HEIGHT - 5, 5] < 0


def test_a_template_of_another_canvas_is_refused(settings: NewWorldSettings) -> None:
    with pytest.raises(omerika.OmerikaError, match="template"):
        _ = land_stage(np.ones((200, 300), dtype=bool), 1, settings, None)
    with pytest.raises(omerika.OmerikaError, match="template"):
        _ = land_stage(
            np.ones((200, 300), dtype=bool), 1, settings, np.ones((100, 100), dtype=bool)
        )


@pytest.mark.parametrize("seed", [1, 2, 3, 42])
def test_the_land_resembles_the_template_and_joins_its_two_landmasses(
    seed: int, americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    domain = np.ones((HEIGHT, WIDTH), dtype=bool)
    land, ocean, lakes, _ = land_stage(domain.copy(), seed, settings, americas)
    template = omerika.prepare(americas, seed, settings)
    # Both great landmasses lie in one landmass of the generated land (land_stage checks it too).
    omerika.check_joined(land, template)
    # The land lies mostly where the template says: its overlap is far above chance.
    overlap = int((land & americas).sum())
    assert overlap * 100 > 55 * int(land.sum())
    # It is not the template: the coast is the generator's own.
    assert not np.array_equal(land, americas)
    assert not (ocean & land).any()
    assert not (lakes & land).any()


def test_the_likeness_decides_how_near_the_land_is_to_the_template(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    domain = np.ones((HEIGHT, WIDTH), dtype=bool)
    shares: list[int] = []
    for likeness in (350, 900):
        shape = replace(settings, template_permille=likeness, land_permille=330)
        land = land_stage(domain.copy(), 5, shape, americas)[0]
        shares.append(int((land & americas).sum()) * 1000 // int(land.sum()))
    assert shares[1] > shares[0]


def test_land_that_splits_the_great_landmasses_is_refused(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    template = omerika.prepare(americas, 7, settings)
    cut = americas.copy()
    cut[1020:1080, :] = False
    omerika.check_joined(americas, template)
    with pytest.raises(omerika.OmerikaError, match="does not join"):
        omerika.check_joined(cut, template)
    with pytest.raises(omerika.OmerikaError, match="sea"):
        omerika.check_joined(np.zeros_like(americas), template)


def test_a_template_with_one_landmass_has_nothing_to_join(settings: NewWorldSettings) -> None:
    ys, xs = np.mgrid[:HEIGHT, :WIDTH]
    one = (ys - 800) ** 2 + (xs - 1000) ** 2 < 500**2
    template = omerika.prepare(one, 7, settings)
    with pytest.raises(omerika.OmerikaError, match="fewer than two"):
        omerika.check_joined(one, template)


def test_the_thin_parts_of_the_land_have_a_centre_line_and_the_thick_ones_none() -> None:
    land = np.zeros((300, 400), dtype=bool)
    land[100:200, 220:380] = True  # a broad continent, 400 x 640 px
    land[145:155, 20:220] = True  # a cape 40 px wide and 800 px long, reaching west
    inside = euclidean_distance(~land, 40).astype(np.int64)
    line = omerika._skeleton(  # pyright: ignore[reportPrivateUsage]
        land, inside
    )
    cape = line[145:155, 40:200]
    assert int(cape.sum()) >= 120  # the cape's whole length is a line
    assert not line[110:190, 260:340].any()  # the heart of the continent is not
    assert not (line & ~land).any()


def test_below_the_least_likeness_no_promise_is_made_to_join_the_great_landmasses(
    americas: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    loose = replace(settings, template_permille=omerika.JOIN_MIN_PERMILLE - 1)
    template = omerika.prepare(americas, 7, loose)
    assert not template.promised
    assert not template.route
    # Nothing is asked of any land then: even one without a neck passes.
    omerika.check_joined(np.zeros_like(americas), template)
    assert omerika.prepare(americas, 7, replace(settings, template_permille=500)).promised
