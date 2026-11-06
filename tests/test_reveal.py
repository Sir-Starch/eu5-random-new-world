"""The optional reveal of the generated New World at the campaign start (W6)."""

from __future__ import annotations

import random
from typing import cast

import pytest

from rnw import eu5_nw_export, settings
from rnw.app import controls, random_types, worldcode
from rnw.eu5_reveal import (
    ACTION,
    DISCOVERED,
    HOOK,
    REVEAL_FILE,
    RevealError,
    files,
    new_world_areas,
    script,
    verify,
)
from rnw.pdx import parse
from rnw.settings import build_settings, run_spec, spec_digest

DEFINITIONS = """
europe = { western_europe = { iberia_region = {
    castile_area = { toledo_province = { toledo madrid } } } } }
atlantic_ocean_continent = { atlantic = { north_atlantic = { azores_sea_area = {
    azores_province = { azores_sea } } } } }
america = {
    north_america = {
        rnw_north_region = {
            rnw_b_area = { rnw_b_province = { rnw_one rnw_two } }
            rnw_a_area = { rnw_a_province = { rnw_three } }
            rnw_east_sea_area = { rnw_east_province = { rnw_east_sea } }
        }
    }
    south_america = { rnw_south_region = { rnw_c_area = { rnw_c_province = { rnw_four } } } }
}
"""
AREAS = ["rnw_a_area", "rnw_b_area", "rnw_c_area", "rnw_east_sea_area"]


def test_the_areas_are_those_under_the_new_worlds_continent_land_and_sea() -> None:
    assert new_world_areas(DEFINITIONS) == AREAS


def test_a_world_without_a_new_world_cannot_be_revealed() -> None:
    old = "europe = { w = { r_region = { a_area = { p_province = { one } } } } }"
    with pytest.raises(RevealError, match="no area"):
        _ = new_world_areas(old)


def test_the_start_is_hooked_like_the_games_own_modules_and_every_area_is_discovered() -> None:
    root = parse(script(AREAS))
    assert [entry.key for entry in root.entries] == [HOOK, ACTION]
    # A second `effect` on on_game_start would stop the game's own start (C200): only on_actions.
    hook = root.block(HOOK)
    assert hook is not None
    assert [entry.key for entry in hook.entries] == ["on_actions"]
    effect = root.block(ACTION, "effect")
    assert effect is not None
    assert [entry.key for entry in effect.entries] == ["set_global_variable", "every_country"]
    flag = effect.first("set_global_variable")
    assert flag is not None
    assert flag.value == DISCOVERED
    countries = effect.block("every_country")
    assert countries is not None
    assert [entry.value for entry in countries.entries] == [f"area:{area}" for area in AREAS]


def test_the_file_is_written_with_a_byte_order_mark_and_checks_against_the_definitions() -> None:
    written = files(DEFINITIONS)
    assert list(written) == [REVEAL_FILE]
    assert written[REVEAL_FILE].startswith(b"\xef\xbb\xbf")
    assert verify(written, DEFINITIONS) == {"reveal_areas": len(AREAS)}


DAMAGES: list[tuple[str, str, str]] = [
    # (what the file says, what it is changed to, what the check says)
    ("\t\t\tdiscover_area = area:rnw_c_area\n", "", "1 missing"),
    (
        "area:rnw_c_area\n",
        "area:rnw_c_area\n\t\t\tdiscover_area = area:toledo_area\n",
        "1 extra",
    ),
    (f"= {DISCOVERED}", "= something_else", "set the global"),
    (
        f"on_actions = {{ {ACTION} }}",
        f"on_actions = {{ {ACTION} }}\n\teffect = {{ }}",
        "on_actions only",
    ),
    ("\t\t\tdiscover_area = area:rnw_a_area", "\t\t\tadd_gold = 1", "only discover"),
    (f"\n{ACTION} = ", "\nother_action = ", "must define"),
]


@pytest.mark.parametrize(("old", "new", "reason"), DAMAGES)
def test_a_written_file_that_does_not_say_what_it_should_is_refused(
    old: str, new: str, reason: str
) -> None:
    text = script(AREAS)
    assert text.count(old) == 1
    broken = text.replace(old, new)
    with pytest.raises(RevealError, match=reason):
        _ = verify({REVEAL_FILE: broken.encode("utf-8-sig")}, DEFINITIONS)


def test_a_missing_file_is_refused() -> None:
    with pytest.raises(RevealError, match="not among the written files"):
        _ = verify({}, DEFINITIONS)


def test_the_export_adds_the_reveal_only_when_the_setting_is_on() -> None:
    mod_definitions = "in_game/map_data/definitions.txt"
    texts = {mod_definitions: DEFINITIONS.encode("utf-8-sig")}
    off = eu5_nw_export._add_reveal(texts, enabled=False)  # pyright: ignore[reportPrivateUsage]
    assert off == {}
    assert list(texts) == [mod_definitions]
    on = eu5_nw_export._add_reveal(texts, enabled=True)  # pyright: ignore[reportPrivateUsage]
    assert on == {"reveal": {"reveal_areas": len(AREAS)}}
    assert REVEAL_FILE in texts
    nothing = {mod_definitions: b"europe = { w = { r_region = { a_area = { p = { one } } } } }"}
    with pytest.raises(eu5_nw_export.NewWorldExportError, match="no area"):
        _ = eu5_nw_export._add_reveal(nothing, enabled=True)  # pyright: ignore[reportPrivateUsage]


def test_the_setting_is_off_by_default_and_leaves_default_documents_as_they_were() -> None:
    for preset in settings.PRESETS:
        assert build_settings(preset).new_world.reveal_at_start == 0
        document = build_settings(preset).to_json_data()
        assert "reveal_at_start" not in cast("dict[str, object]", document["new_world"])
    plain = run_spec(7, build_settings("continents"))
    revealed = run_spec(7, build_settings("continents", {"new_world": {"reveal_at_start": 1}}))
    assert spec_digest(plain) != spec_digest(revealed)
    section = cast("dict[str, dict[str, object]]", revealed["settings"])["new_world"]
    assert section["reveal_at_start"] == 1


def test_the_setting_accepts_only_zero_and_one() -> None:
    with pytest.raises(settings.SettingsError, match="reveal_at_start"):
        _ = build_settings("continents", {"new_world": {"reveal_at_start": 2}})


def test_the_setting_travels_in_the_world_code_and_default_codes_do_not_change() -> None:
    plain = worldcode.new_code("continents", 42)
    revealed = worldcode.new_code("continents", 42, {"new_world": {"reveal_at_start": 1}})
    assert worldcode.decode(worldcode.encode(plain)).settings().new_world.reveal_at_start == 0
    assert worldcode.decode(worldcode.encode(revealed)).settings().new_world.reveal_at_start == 1
    # A code names its changes by field number, and a number once given is never reused.
    assert worldcode.CHANGE_FIELDS[-1] == "new_world.reveal_at_start"
    assert worldcode.CHANGE_FIELDS[-2] == "natives.turbulence_permille"
    assert len(worldcode.encode(plain)) < len(worldcode.encode(revealed))
    assert worldcode.with_new_seed(revealed, 43).settings().new_world.reveal_at_start == 1


def test_the_reveal_is_a_checkbox_of_the_page_and_no_random_draw_turns_it_on() -> None:
    control = controls.BY_KEY["new_world.reveal_at_start"]
    assert (control.low, control.high, control.default("continents")) == (0, 1, 0)
    assert control not in controls.ADVANCED
    assert "reveal_at_start" in controls.PAGE_OPTIONS
    for seed in range(40):
        _, changes = random_types.draw(random_types.CHAOS, random.Random(seed))  # noqa: S311 - a test's draw, not a secret
        assert "new_world.reveal_at_start" not in changes
