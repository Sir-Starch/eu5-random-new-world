"""The files of the stories and unions: starts, payload copies, formables, texts (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.content import (
    RIVER_CENTRE,
    SACRED_CENTRE,
    Absence,
    ContentPlan,
    Facts,
    Opportunity,
    Place,
    Start,
    State,
    Union,
)
from rnw.eu5_story import (
    LOCALIZATION,
    MODIFIERS_FILE,
    PRIVILEGES_FILE,
    START_FILE,
    UNION_FILE,
    StoryError,
    build,
    facts_of,
    modifier_block,
    payload,
)
from rnw.pdx import Block, parse
from rnw.stories import LOCATION, STATIC, STORIES, Modifier, Source

if TYPE_CHECKING:
    from pathlib import Path

SOURCES = {
    "chk_funding_woodhenge_restoration": ("country", True, "monthly_gold_expense = 2"),
    "chk_protection_against_flooding": ("location", False, "local_life_expectancy = 1"),
    "chk_outer_cahokia_protected_flooding": ("location", False, "local_monthly_prosperity = 0.04"),
    "chk_restricted_construction": ("country", False, "monthly_gold_income = 4"),
    "chk_river_water_polluted": ("location", False, "local_life_expectancy = -5"),
    "chk_outer_cahokia_growth": ("location", False, "local_population_growth = 0.03"),
    "chk_exodus_of_cahokia": (
        "country",
        False,
        "monthly_gold_income = 6.5 monthly_prestige = -0.25",
    ),
}
BUILDING = """great_temple_of_tenochtitlan = {
\tmax_levels = 7
\tmodifier = {
\t\tlocal_clergy_estate_power = 0.2
\t\tlocal_cultural_tradition = 0.1
\t}
}
"""
PRIVILEGE = """hurin_qusqu_privilege = {
\testate = clergy_estate
\tpotential = { religion = religion:inti }
\tcountry_modifier = {
\t\ttolerance_own = 0.1
\t\tglobal_clergy_estate_power = 0.3
\t}
}
"""


def _decay(decaying: bool) -> str:  # noqa: FBT001 - a flag of a table row
    return " decaying = yes" if decaying else ""


def _static(name: str, category: str, decaying: bool, effect: str) -> str:  # noqa: FBT001
    data = f"game_data = {{ category = {category}{_decay(decaying)} }}"
    return f"{name} = {{\n\t{data}\n\t{effect}\n}}\n"


def _install(root: Path, *, drop: str = "") -> Path:
    game = root / "game"
    statics = "".join(
        _static(name, category, decaying, effect)
        for name, (category, decaying, effect) in SOURCES.items()
        if name != drop
    )
    for relative, text in {
        "main_menu/common/static_modifiers/country.txt": statics,
        "in_game/common/building_types/event_only_buildings.txt": BUILDING,
        "in_game/common/estate_privileges/clergy_estate.txt": PRIVILEGE,
    }.items():
        path = game / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
    return root


def _plan() -> ContentPlan:
    start = Start(1350, 1395, 3)
    return ContentPlan(
        (
            Opportunity(RIVER_CENTRE, "ABC", "loc_a", start),
            Opportunity(SACRED_CENTRE, "DEF", "loc_b", Start(1360, 1405, 2)),
        ),
        (Union(0, ("loc_a", "loc_c"), ("loc_a",), ("ABC", "DEF"), "loc_a"),),
        (),
    )


def _build(root: Path, plan: ContentPlan | None = None) -> dict[str, bytes]:
    return build(
        root,
        plan or _plan(),
        names={"loc_a": "Alto", "loc_b": "Brava"},
        tags=["XYZ"],
        languages=("english", "turkish"),
        seed=5,
        taken=frozenset({(1, 2, 3)}),
    ).files


def test_a_payload_is_copied_with_its_category_and_decay(tmp_path: Path) -> None:
    """The mod's modifier has its own name and the effect lines of the vanilla one."""
    root = _install(tmp_path)
    copied = payload(root, Source(STATIC, "chk_funding_woodhenge_restoration"))
    assert copied.decaying
    assert copied.category == "country"
    modifier = Modifier(
        "rnw_x", "country", Source(STATIC, "chk_funding_woodhenge_restoration"), "X", "x"
    )
    text = modifier_block(modifier, copied)
    assert text.startswith(
        "rnw_x = {\n\tgame_data = {\n\t\tcategory = country\n\t\tdecaying = yes\n\t}\n"
    )
    assert "\tmonthly_gold_expense = 2\n}" in text
    assert "woodhenge" not in text


def test_a_source_that_is_gone_or_of_another_kind_stops_the_export(tmp_path: Path) -> None:
    """Nothing is substituted: a missing source, an empty one or a category clash is an error."""
    root = _install(tmp_path, drop="chk_exodus_of_cahokia")
    with pytest.raises(StoryError, match="chk_exodus_of_cahokia is gone"):
        _ = payload(root, Source(STATIC, "chk_exodus_of_cahokia"))
    with pytest.raises(StoryError, match="has no nothing"):
        _ = payload(root, Source("building", "great_temple_of_tenochtitlan", "nothing"))
    copied = payload(root, Source(STATIC, "chk_protection_against_flooding"))
    wrong = Modifier(
        "rnw_y", "country", Source(STATIC, "chk_protection_against_flooding"), "Y", "y"
    )
    with pytest.raises(StoryError, match="is country but its source is location"):
        _ = modifier_block(wrong, copied)


def test_a_world_gets_the_events_of_the_families_that_have_a_bearer(tmp_path: Path) -> None:
    """Static events and modifiers for each family present, a start event per bearer."""
    files = _build(_install(tmp_path))
    assert "in_game/events/rnw_river.txt" in files
    assert "in_game/events/rnw_sacred.txt" in files
    start = files[START_FILE].decode("utf-8-sig")
    assert "tag = ABC" in start
    assert "owns = location:loc_a" in start
    assert "set_variable = { name = rnw_river_centre value = location:loc_a }" in start
    assert "from = 1350.1.1" in start
    assert "monthly_chance = 3" in start
    assert "trigger_event_non_silently = { id = rnw_sacred.1 }" in start
    ids = [e.key for e in parse(start).entries if e.key and isinstance(e.value, Block)]
    assert ids == ["rnw_story.1001", "rnw_story.1002"]
    modifiers = files[MODIFIERS_FILE].decode("utf-8-sig")
    assert "rnw_river_embankments" in modifiers
    assert "rnw_sacred_endowment" in modifiers
    assert "local_clergy_estate_power = 0.2" in modifiers
    privilege = files[PRIVILEGES_FILE].decode("utf-8-sig")
    assert "has_variable = rnw_sacred_privilege_open" in privilege
    assert "global_clergy_estate_power = 0.3" in privilege
    assert "religion" not in privilege


def test_a_family_without_a_bearer_leaves_no_event_behind(tmp_path: Path) -> None:
    """No bearer, no events of that family (they would be orphans), no modifier, no privilege."""
    only_river = ContentPlan(
        (Opportunity(RIVER_CENTRE, "ABC", "loc_a", Start(1350, 1395, 3)),),
        (),
        (Absence(SACRED_CENTRE, "none"),),
    )
    files = _build(_install(tmp_path), only_river)
    assert "in_game/events/rnw_sacred.txt" not in files
    assert PRIVILEGES_FILE not in files
    assert "rnw_sacred" not in files[MODIFIERS_FILE].decode("utf-8-sig")
    empty = _build(_install(tmp_path), ContentPlan((), (), ()))
    assert empty == {}


def test_a_union_is_a_formable_of_a_tag_the_game_does_not_define(tmp_path: Path) -> None:
    """The formable, flag, coat of arms, colour and names that the vanilla ADU has."""
    files = _build(_install(tmp_path))
    formable = files[UNION_FILE].decode("utf-8-sig")
    block = parse(formable).block("rnw_union_1_f")
    assert block is not None
    assert block.first("tag") is not None
    assert "tag = XYZ" in formable
    assert "adjective = XYZ_ADJ" in formable
    assert "color = map_XYZ" in formable
    assert "tag = ABC" in formable
    locations = block.block("locations")
    assert locations is not None
    assert [w.value for w in locations.words()] == ["loc_a", "loc_c"]
    assert "XYZ = {" in files["main_menu/common/flag_definitions/rnw_union.txt"].decode("utf-8-sig")
    assert "map_XYZ = rgb" in files["main_menu/common/named_colors/rnw_union.txt"].decode(
        "utf-8-sig"
    )
    arms = files["main_menu/common/coat_of_arms/coat_of_arms/rnw_union.txt"].decode("utf-8-sig")
    assert 'pattern = "pattern_solid.dds"' in arms
    english = files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"].decode("utf-8-sig")
    assert ' XYZ: "Alto Union"' in english
    assert ' XYZ_ADJ: "Alto"' in english


def test_the_texts_are_written_in_every_language_the_same(tmp_path: Path) -> None:
    """Until L1 translates them, each language carries the English text."""
    files = _build(_install(tmp_path))
    english = files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"]
    turkish = files[f"{LOCALIZATION}/turkish/rnw_story_l_turkish.yml"]
    assert english.decode("utf-8-sig").replace("l_english:", "l_x:") == turkish.decode(
        "utf-8-sig"
    ).replace("l_turkish:", "l_x:")
    assert b"rnw_river.1.title" in english
    assert len(STORIES) == 2


def test_facts_come_from_the_parts_of_a_world() -> None:
    """Owners follow the states' members; holy places and links outside the world drop out."""
    facts = facts_of(
        keys=["a", "b", "c"],
        population={"a": 5, "b": 0, "c": 3},
        ranks={"a": "city"},
        religion={"a": "r1", "c": "r2"},
        river={"a": 2},
        states=[("AAA", ("a", "b"), "a", "r1"), ("BBB", ("c",), "c", "r2")],
        holy=["a", "z"],
        links=[("a", "b"), ("a", "c"), ("c", "z")],
    )
    assert set(facts.places) == {"a", "c"}
    assert facts.places["a"] == Place("a", 5, 2, "city", "r1", "AAA")
    assert facts.places["c"].owner == "BBB"
    assert facts.states["AAA"] == State("AAA", "a", "r1")
    assert facts.holy == {"a"}
    assert facts.links == {("a", "c")}
    assert isinstance(facts, Facts)
    assert LOCATION == "location"
