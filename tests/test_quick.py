"""Quick settings: levels over the controls, for every world type."""

from __future__ import annotations

from rnw.app import controls, quick
from rnw.gui.text import STRINGS
from rnw.settings import REGIONAL_PRESETS, WORLD_TYPES, RegionalSettings, build_settings


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


def test_many_states_requests_a_substantially_higher_land_share() -> None:
    """The quick choice reaches 44% on the default presets, inside the new control range."""
    states = quick.BY_NAME["states"]
    for preset in WORLD_TYPES:
        many = states.level("many").values(preset)["natives.state_share_permille"]
        assert many == 440
        assert controls.BY_KEY["natives.state_share_permille"].allows(many)


def _region(key: str, preset: str, overrides: dict[str, object] | None = None) -> RegionalSettings:
    """One continent's resolved settings of type ``preset``, as the window resolves them."""
    document: dict[str, object] = {"preset": preset, **(overrides or {})}
    return build_settings("continents", {"continents": {key: document}}).continents.regions[0]


def _held(region: RegionalSettings, setting: quick.Quick) -> dict[str, int]:
    return {
        key: controls.region_value(controls.REGION_BY_KEY[key], region) for key in setting.touched()
    }


def test_every_continent_starts_on_an_answer_of_each_question() -> None:
    """A continent's own defaults (Oceania's state share is 24, Africa's 443) are a level: the
    questions are not America's numbers, and a default continent never reads as custom. The
    questions that scale a value start on "normal"; the fixed ones (empires, turbulence) on
    whichever level holds the type's own value."""
    scaled = {"land", "peoples", "states", "wealth"}
    for key in REGIONAL_PRESETS:
        for preset in controls.REGION_TYPES:
            defaults = _region(key, preset)
            for setting in quick.QUICK:
                level = setting.current(preset, _held(defaults, setting), defaults)
                assert level is not None, (key, preset, setting.name)
                if setting.name in scaled:
                    assert level == "normal", (key, preset, setting.name)


def test_every_answer_of_every_continent_is_distinct_and_playable() -> None:
    """After the clamping to the continent's ranges no two levels coincide, each is read back
    and every value is one the continent's sliders allow (the state share goes down to 1)."""
    for key in REGIONAL_PRESETS:
        for preset in controls.REGION_TYPES:
            defaults = _region(key, preset)
            for setting in quick.QUICK:
                mixes = [
                    tuple(sorted(level.values(preset, defaults).items()))
                    for level in setting.levels
                ]
                assert len(set(mixes)) == len(mixes), (key, preset, setting.name)
                for level in setting.levels:
                    values = level.values(preset, defaults)
                    assert all(
                        controls.REGION_BY_KEY[name].allows(number)
                        for name, number in values.items()
                    )
                    held = {**_held(defaults, setting), **values}
                    assert setting.current(preset, held, defaults) == level.name


def test_a_continents_states_start_from_its_own_share() -> None:
    """Oceania keeps 24 for "normal" (not America's 30 floor), Africa's levels grow from 443."""
    oceania = _region("oceania", "archipelago")
    states = quick.BY_NAME["states"]
    shares = {
        level.name: level.values("archipelago", oceania)["natives.state_share_permille"]
        for level in states.levels
    }
    assert shares == {"few": 12, "normal": 24, "many": 96}
    africa = _region("africa", "supercontinent")
    shares = {
        level.name: level.values("supercontinent", africa)["natives.state_share_permille"]
        for level in states.levels
    }
    assert shares["few"] < 443 == shares["normal"] < shares["many"]
    assert shares["many"] == controls.REGION_BY_KEY["natives.state_share_permille"].high


def test_no_answer_of_a_continent_makes_a_world_the_engine_cannot_take() -> None:
    """Each answer on each continent, with America and the other continent left alone, stays
    under the location budget."""
    for key in REGIONAL_PRESETS:
        for preset in controls.REGION_TYPES:
            defaults = _region(key, preset)
            for setting in quick.QUICK:
                for level in setting.levels:
                    sections: dict[str, dict[str, int]] = {"new_world": {}, "natives": {}}
                    for name, number in level.values(preset, defaults).items():
                        control = controls.REGION_BY_KEY[name]
                        sections[control.section][control.field] = number
                    settings = build_settings(
                        "continents",
                        {"continents": {"america": False, key: {"preset": preset, **sections}}},
                    )
                    assert controls.estimated_locations(settings) < controls.LOCATION_BUDGET, (
                        key,
                        preset,
                        setting.name,
                        level.name,
                    )
