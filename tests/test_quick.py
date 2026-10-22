"""Quick settings: levels over the controls, for every world type."""

from __future__ import annotations

from rnw.app import controls, quick
from rnw.gui.text import STRINGS
from rnw.settings import WORLD_TYPES, build_settings


def _defaults(preset: str) -> dict[str, int]:
    return {control.key: control.default(preset) for control in controls.CONTROLS}


def test_every_level_has_its_words_and_touches_real_controls() -> None:
    """Names and tooltips exist for every question and answer; the controls are the window's."""
    for setting in quick.QUICK:
        assert f"quick.{setting.name}" in STRINGS
        assert f"quick.{setting.name}.about" in STRINGS
        assert len(setting.levels) >= 3
        for level in setting.levels:
            assert f"quick.{setting.name}.{level.name}" in STRINGS
            assert level.parts
            assert all(part.key in controls.BY_KEY for part in level.parts)


def test_a_question_owns_its_controls() -> None:
    """No control is set by two questions, or one answer would undo another."""
    owner: dict[str, str] = {}
    for setting in quick.QUICK:
        for level in setting.levels:
            for part in level.parts:
                assert owner.setdefault(part.key, setting.name) == setting.name, part.key


def test_every_world_type_starts_on_an_answer_and_every_answer_can_be_told_apart() -> None:
    """The type's own values are one level of each question, and no two levels coincide."""
    for preset in WORLD_TYPES:
        for setting in quick.QUICK:
            assert setting.current(preset, _defaults(preset)) is not None, (preset, setting.name)
            mixes = [tuple(sorted(level.values(preset).items())) for level in setting.levels]
            assert len(set(mixes)) == len(mixes), (preset, setting.name)


def test_choosing_an_answer_is_read_back_and_custom_when_a_slider_moves() -> None:
    """The controls hold the level that was set; a value between levels is custom."""
    for preset in WORLD_TYPES:
        for setting in quick.QUICK:
            for level in setting.levels:
                values = {**_defaults(preset), **level.values(preset)}
                assert setting.current(preset, values) == level.name
                assert all(controls.BY_KEY[key].allows(number) for key, number in values.items())
    moved = {**_defaults("continents"), "natives.empire_permille": 333}
    assert quick.BY_NAME["empires"].current("continents", moved) is None


def test_no_answer_makes_a_world_the_engine_cannot_take() -> None:
    """Every level of every question, on every world type, stays under the location budget."""
    for preset in WORLD_TYPES:
        for setting in quick.QUICK:
            for level in setting.levels:
                changes = {
                    key: number
                    for key, number in level.values(preset).items()
                    if number != controls.BY_KEY[key].default(preset)
                }
                settings = build_settings(preset, controls.nested(changes))
                assert controls.estimated_locations(settings) < controls.LOCATION_BUDGET, (
                    preset,
                    setting.name,
                    level.name,
                )


def test_more_land_makes_larger_locations_and_never_fewer_empires_than_asked() -> None:
    """Much land grows the locations; the empire levels are the four of EU4's fantasy setting."""
    land = quick.BY_NAME["land"]
    for preset in WORLD_TYPES:
        little, normal, much = (
            land.level(name).values(preset) for name in ("little", "normal", "much")
        )
        assert little["new_world.land_permille"] < normal["new_world.land_permille"]
        assert normal["new_world.land_permille"] < much["new_world.land_permille"]
        assert much["new_world.location_px"] > controls.BY_KEY["new_world.location_px"].default(
            preset
        )
    empires = quick.BY_NAME["empires"]
    assert [level.name for level in empires.levels] == ["never", "seldom", "sometimes", "often"]
    chances = [level.values("continents")["natives.empire_permille"] for level in empires.levels]
    assert chances[0] == 0
    assert chances == sorted(chances)
