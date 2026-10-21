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
