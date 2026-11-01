"""The window's settings: playable ranges, sliders, units, and the location budget."""

from __future__ import annotations

import pytest

from rnw.app import controls
from rnw.gui.text import STRINGS
from rnw.settings import PRESETS, RANGES, WORLD_TYPES, build_settings


def test_every_control_is_a_setting_inside_what_the_validator_accepts() -> None:
    """Each range lies inside the settings' own range and holds every world type's value."""
    for control in controls.CONTROLS:
        low, high = RANGES[control.field]
        assert low <= control.low < control.high <= high, control.key
        for preset in WORLD_TYPES:
            assert control.allows(control.default(preset)), (control.key, preset)
        assert f"control.{control.key}" in STRINGS
        assert f"control.{control.key}.about" in STRINGS
        assert f"unit.{control.unit}" in STRINGS
    assert {control.group for control in controls.CONTROLS} == set(controls.GROUPS)


def test_state_land_control_offers_a_sixty_percent_target() -> None:
    """The shared window control reaches the higher, still-validated land target."""
    control = controls.BY_KEY["natives.state_share_permille"]
    assert control.low == 30
    assert control.high == 600
    assert control.shown(control.high) == 60
    assert control.stored(60) == control.high


def test_peasant_mix_control_is_bounded_and_defaults_to_the_existing_output() -> None:
    """The all-land population-mix control spans 30 to 80%, with the former 60% default."""
    control = controls.BY_KEY["natives.peasant_peak_permille"]
    assert (control.low, control.default("continents"), control.high) == (300, 600, 800)
    assert (control.shown(control.low), control.shown(control.high)) == (30, 80)
    assert control.group == "peoples"


@pytest.mark.parametrize(
    "control", controls.CONTROLS, ids=[control.key for control in controls.CONTROLS]
)
def test_sliders_reach_both_ends_and_come_back_to_a_value(control: controls.Control) -> None:
    """A slider runs from the low to the high end; a value maps to a position and back."""
    assert control.value_at(0) == control.low
    assert control.value_at(controls.STEPS) == control.high
    middle = control.value_at(controls.STEPS // 2)
    assert control.low <= middle <= control.high
    assert abs(control.value_at(control.position(middle)) - middle) <= max(1, middle // 100)
    assert control.stored(control.shown(control.high) * 10) == control.high
    assert control.stored(control.shown(control.low) / 10 - 1) == control.low


def test_changes_go_into_a_settings_document_and_back() -> None:
    """Flat changes nest by section; a code's document splits into shown and other changes."""
    document = controls.nested({"new_world.land_permille": 300, "natives.tribe_locations": 8})
    assert document == {"new_world": {"land_permille": 300}, "natives": {"tribe_locations": 8}}
    assert controls.nested({}) is None
    shown, other = controls.flat({"new_world": {"land_permille": 300, "coast_margin_px": 9}})
    assert shown == {"new_world.land_permille": 300}
    assert other == {"new_world": {"coast_margin_px": 9}}


def test_every_world_type_fits_the_location_budget_and_small_locations_do_not() -> None:
    """The presets stay below the budget; much land in small locations goes over it."""
    for preset in WORLD_TYPES:
        assert controls.estimated_locations(PRESETS[preset]) < controls.LOCATION_BUDGET
    crowded = build_settings(
        "supercontinent", {"new_world": {"land_permille": 600, "location_px": 40}}
    )
    assert controls.estimated_locations(crowded) > controls.LOCATION_BUDGET


def test_wall_width_reaches_a_wall_that_takes_nearly_all_the_land() -> None:
    """Widths run from 4% to 44% of the canvas, and the default is the former maximum, 14%."""
    control = controls.BY_KEY["new_world.wall_width_permille"]
    assert (control.low, control.default("wall"), control.high) == (40, 140, 440)
    assert (control.shown(control.low), control.shown(control.high)) == (4, 44)
    assert RANGES["wall_width_permille"] == (40, 440)
    assert control.group == "wall"


def test_the_widest_wall_still_fits_the_location_budget() -> None:
    """The Wall's land counts inside the land share: the widest one at the default land fits."""
    widest = build_settings("wall", {"new_world": {"wall_width_permille": 440}})
    assert controls.estimated_locations(widest) < controls.LOCATION_BUDGET
    narrow = build_settings("wall", {"new_world": {"wall_width_permille": 40}})
    # More Wall than the land share asks for adds land; a narrow one adds none.
    assert controls.estimated_locations(widest) > controls.estimated_locations(narrow)
    assert controls.estimated_locations(narrow) == controls.estimated_locations(
        build_settings("wall", {"new_world": {"wall_width_permille": 100}})
    )
