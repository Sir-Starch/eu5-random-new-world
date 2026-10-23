"""The hook probe of N2: anchors, files and script syntax (synthetic)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from rnw import eu5_probe
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from pathlib import Path

DEFINITIONS = """europe = {
\twestern_europe = { r = { central_switzerland_area = { p = { bern interlaken } } } }
}
oceania = {
\taustralasia = { r = { southeastern_australia_area = { dharug_province = { dharug eora } } } }
}
"""
COUNTRIES = """countries = { countries = {
\tBRN = { own_control_core = { bern interlaken } country_rank = rank_county capital = bern }
} }
"""
CHARTER = (
    "form_colonial_nation = { effect = { order_by = best_capital_for_colony\n"
    "cc_setup_new_town = yes create_location_country_from_province_definition = {\n"
    "hidden_effect = { setup_colonial_nation = yes } add_truce_with = { } } } }\n"
)
README = "# " + " ".join(eu5_probe.FORMABLE_KEYS) + "\n"
COAT_OF_ARMS = 'x = { pattern = "pattern_solid.dds" texture = "ce_checky_15_points.dds" }\n'
FILES = {
    "in_game/map_data/definitions.txt": DEFINITIONS,
    "main_menu/setup/1337/10_countries.txt": COUNTRIES,
    "in_game/common/formable_countries/readme.txt": README,
    "main_menu/common/coat_of_arms/coat_of_arms/pre_scripted_countries.txt": COAT_OF_ARMS,
    "in_game/common/on_action/_hardcoded.txt": "on_game_start = { effect = { } }\n",
    "in_game/common/on_action/country_yearly.txt": (
        "yearly_country_pulse = { on_actions = { x } }\n"
    ),
    "in_game/common/decisions/canal_construction.txt": (
        "x = { decision_category = infrastructure_decisions ai_will_do = { value = 1 } }\n"
    ),
    "in_game/common/scripted_effects/e.txt": (
        "e = { create_country_from_location = { set_capital = x make_subject_of = { } } }\n"
        "cc_setup_new_town = { }\nsetup_colonial_nation = { }\n"
    ),
    "in_game/common/colonial_charter_goals/form_colonial_nation.txt": CHARTER,
    "in_game/common/subject_types/colonial_nation.txt": (
        "colonial_nation = { is_colonial_subject = yes }\n"
    ),
    "main_menu/localization/english/a_l_english.yml": 'l_english:\n a: "A"\n',
    "main_menu/localization/turkish/a_l_turkish.yml": 'l_turkish:\n a: "A"\n',
}


def _install(root: Path, overrides: dict[str, str] | None = None) -> Path:
    for relative, text in {**FILES, **(overrides or {})}.items():
        path = root / "game" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
    return root


def test_the_probe_is_built_from_anchors_that_hold(tmp_path: Path) -> None:
    """A conforming installation gives every file, each script reads, texts in every language."""
    files = eu5_probe.build(_install(tmp_path))
    eu5_probe.check(files)
    assert ".metadata/metadata.json" in files
    assert "main_menu/localization/turkish/rnw_probe_l_turkish.yml" in files
    formable = files["in_game/common/formable_countries/rnw_probe.txt"].decode("utf-8-sig")
    assert "tag = ZQP" in formable
    assert "area = area:central_switzerland_area" in files[
        "in_game/common/scripted_country_names/rnw_probe.txt"
    ].decode("utf-8-sig")
    for path, data in files.items():
        if path.endswith(".txt"):
            assert parse(data.decode("utf-8-sig")).entries, path


@pytest.mark.parametrize(
    ("override", "problem"),
    [
        ({"in_game/events/x.txt": "x = { tag = ZQP }\n"}, "already used by the game"),
        ({"in_game/common/formable_countries/readme.txt": "# level\n"}, "no longer documents"),
        (
            {"main_menu/setup/1337/10_countries.txt": COUNTRIES.replace("interlaken", "elsewhere")},
            "no longer starts with",
        ),
        (
            {
                "main_menu/setup/1337/10_countries.txt": COUNTRIES.replace(
                    "rank_county", "rank_duchy"
                )
            },
            "no longer a county",
        ),
        (
            {"in_game/common/subject_types/colonial_nation.txt": "x = { }\n"},
            "colonial_nation.txt no longer holds",
        ),
        (
            {"in_game/common/scripted_effects/e.txt": "e = { }\n"},
            "no scripted effect uses create_country_from_location",
        ),
        (
            {
                "in_game/common/scripted_effects/e.txt": (
                    "e = { create_country_from_location = { set_capital = x\n"
                    "make_subject_of = { } } }\nsetup_colonial_nation = { }\n"
                )
            },
            "no scripted effect defines cc_setup_new_town",
        ),
        (
            {
                "in_game/common/colonial_charter_goals/form_colonial_nation.txt": CHARTER.replace(
                    "add_truce_with", "x"
                )
            },
            "form_colonial_nation.txt no longer holds add_truce_with",
        ),
        (
            {
                "main_menu/setup/1337/10_countries.txt": COUNTRIES.replace(
                    "bern interlaken", "bern interlaken eora"
                )
            },
            "eora of dharug_province is held by a country",
        ),
        (
            {
                "in_game/map_data/definitions.txt": DEFINITIONS.replace(
                    "dharug_province", "x_province"
                )
            },
            "the province dharug_province is not in the installation",
        ),
    ],
)
def test_an_anchor_that_has_moved_stops_the_build(
    tmp_path: Path, override: dict[str, str], problem: str
) -> None:
    """The probe is never built on a guess: a changed installation is refused with the reason."""
    root = _install(tmp_path, override)
    assert any(problem in found for found in eu5_probe.anchor_problems(root))
    with pytest.raises(eu5_probe.ProbeError, match="cannot be built"):
        _ = eu5_probe.build(root)


def test_the_probe_runs_a_story_start_in_miniature(tmp_path: Path) -> None:
    """A hidden window, a variable holding a location and a delayed event, all in the first year."""
    files = eu5_probe.build(_install(tmp_path))
    events = files["in_game/events/rnw_probe.txt"].decode("utf-8-sig")
    block = parse(events).block("rnw_probe.3")
    assert block is not None
    window = block.block("dynamic_historical_event")
    assert window is not None
    assert window.first("tag") is not None
    assert "hidden = yes" in events
    assert "monthly_chance = 100" in events
    assert "value = location:bern" in events
    assert "trigger_event_non_silently = { id = rnw_probe.5 months = { 1 2 } }" in events
    assert "remove_variable = rnw_probe_centre" in events


def _options(block: Block) -> list[Block]:
    return [
        entry.value
        for entry in block.entries
        if entry.key == "option" and isinstance(entry.value, Block)
    ]


def _scripts(files: dict[str, bytes]) -> dict[str, str]:
    return {path: data.decode("utf-8-sig") for path, data in files.items() if path.endswith(".txt")}


def test_the_probe_uses_only_effects_the_game_has(tmp_path: Path) -> None:
    """``trigger_event`` is no effect of the game (``Unknown effect trigger_event``, 1.4.4, 036)."""
    for path, text in _scripts(eu5_probe.build(_install(tmp_path))).items():
        assert not re.search(r"\btrigger_event\s*=", text), path


def test_the_start_hook_adds_to_the_game_start_and_does_not_replace_it(tmp_path: Path) -> None:
    """A second ``effect`` of ``on_game_start`` wins over the game's (036): hook an on_action."""
    files = eu5_probe.build(_install(tmp_path))
    root = parse(files["in_game/common/on_action/rnw_probe.txt"].decode("utf-8-sig"))
    start = root.block("on_game_start")
    assert start is not None
    assert start.first("effect") is None
    hooked = start.block("on_actions")
    assert hooked is not None
    assert [word.value for word in hooked.words()] == [eu5_probe.START_ACTION]
    action = root.block(eu5_probe.START_ACTION)
    assert action is not None
    assert action.first("effect") is not None


def test_what_the_probe_shows_is_named_by_the_keys_the_game_looks_up(tmp_path: Path) -> None:
    """Decisions by ``<id>.title`` and ``<id>.desc``, a formable by ``<id>`` and ``<id>_desc``,
    events by title, description and option; any other key shows as itself (036)."""
    files = eu5_probe.build(_install(tmp_path))
    scripts = _scripts(files)
    text = files["main_menu/localization/english/rnw_probe_l_english.yml"].decode("utf-8-sig")
    keys = set(re.findall(r"^ ([\w.]+):", text, re.MULTILINE))
    for entry in parse(scripts["in_game/common/decisions/rnw_probe.txt"]).entries:
        assert {f"{entry.key}.title", f"{entry.key}.desc"} <= keys
        assert isinstance(entry.value, Block)
        for option in _options(entry.value):
            name = option.first("name")
            assert name is not None
            assert name.value in keys
    assert {eu5_probe.FORMABLE, f"{eu5_probe.FORMABLE}_desc"} <= keys
    for entry in parse(scripts["in_game/events/rnw_probe.txt"]).entries:
        if not isinstance(entry.value, Block) or entry.value.first("title") is None:
            continue
        assert f"{entry.key}.title" in keys
        assert f"{entry.key}.desc" in keys
        for option in _options(entry.value):
            name = option.first("name")
            assert name is not None
            assert name.value in keys, name.value


def test_the_decision_shows_the_name_of_the_subject_it_makes(tmp_path: Path) -> None:
    """The name the game gives the new subject (H2) is read in an event, not looked up."""
    files = eu5_probe.build(_install(tmp_path))
    decisions = files["in_game/common/decisions/rnw_probe.txt"].decode("utf-8-sig")
    # a plain vassal kept its location's name (037); the game's colonies are colonial nations, and
    # the effect is hidden because its tooltip asks the capital of a country not yet made
    assert "type = subject_type:colonial_nation" in decisions
    assert "hidden_effect" in decisions
    assert "save_scope_as = rnw_probe_colony" in decisions
    assert "trigger_event_non_silently = { id = rnw_probe.6 }" in decisions
    texts = files["main_menu/localization/english/rnw_probe_l_english.yml"].decode("utf-8-sig")
    assert "[rnw_probe_colony.GetName]" in texts


def test_two_subjects_are_made_two_ways_and_each_has_a_scripted_name(tmp_path: Path) -> None:
    """Interlaken by the effect that makes a country from a location, an overseas province by the
    effect of the game's colonial charter (C207, C210, C218): one scripted name for each."""
    files = eu5_probe.build(_install(tmp_path))
    names = parse(files["in_game/common/scripted_country_names/rnw_probe.txt"].decode("utf-8-sig"))
    assert [entry.key for entry in names.entries] == [
        eu5_probe.SCRIPTED_NAME,
        eu5_probe.OVERSEAS_NAME,
    ]
    texts = files["in_game/common/scripted_country_names/rnw_probe.txt"].decode("utf-8-sig")
    assert "area = area:central_switzerland_area" in texts
    assert "area = area:southeastern_australia_area" in texts
    decisions = files["in_game/common/decisions/rnw_probe.txt"].decode("utf-8-sig")
    assert "create_country_from_location" in decisions
    colonize = decisions[decisions.index("rnw_probe_colonize = {") :]
    colonize = colonize[: colonize.index("rnw_probe_read_state = {")]
    # the charter goal's effect, with the scopes it is given and its helpers read
    for line in (
        "save_scope_as = owner",
        "province_definition:dharug_province = {",
        "save_scope_as = target",
        "order_by = best_capital_for_colony",
        "save_scope_as = new_town",
        "change_location_rank = location_rank:town",
        "cc_setup_new_town = yes",
        "create_location_country_from_province_definition = {",
        "subject_type = subject_type:colonial_nation",
        "from = scope:owner",
        "capital = scope:new_town",
        "hidden_effect = { setup_colonial_nation = yes }",
        "add_truce_with = {",
        "trigger_event_non_silently = { id = rnw_probe.7 }",
    ):
        assert line in colonize, line
    assert "hidden_effect" in colonize
    assert "NOT = { has_variable = rnw_probe_colonized }" in colonize


def test_the_overseas_event_finds_the_subject_by_where_its_capital_is(tmp_path: Path) -> None:
    """The hidden effect cannot save the new country, so the event looks for it."""
    files = eu5_probe.build(_install(tmp_path))
    events = parse(files["in_game/events/rnw_probe.txt"].decode("utf-8-sig"))
    block = events.block("rnw_probe.7")
    assert block is not None
    script = files["in_game/events/rnw_probe.txt"].decode("utf-8-sig")
    assert "random_subject = {" in script
    assert "capital.area = area:southeastern_australia_area" in script
    assert "save_scope_as = rnw_probe_overseas" in script
    assert len(_options(block)) == 2
    texts = files["main_menu/localization/english/rnw_probe_l_english.yml"].decode("utf-8-sig")
    assert "[rnw_probe_overseas.GetName]" in texts
    assert 'rnw_probe_overseas_scripted_country_name: "Probe Overseas"' in texts
    assert '"version": "0.4.0"' in files[".metadata/metadata.json"].decode("utf-8-sig")
