"""The files of the stories and unions: starts, payload copies, formables, texts (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.colonial_names import GROUPS_DIR, LANGUAGES_DIR, NAMES_FILE, TRADITIONS
from rnw.content import (
    EMPIRE_PERIPHERY,
    GREAT_ALLIANCE,
    HARVEST,
    RIVER_CENTRE,
    RIVER_UNION,
    ROUTE_MARKET,
    SACRED_CENTRE,
    Absence,
    ContentPlan,
    Facts,
    Formation,
    Opportunity,
    Place,
    Start,
    State,
)
from rnw.eu5_formation import (
    ARMS_FILE,
    COLORS_FILE,
    EMBLEM_DIR,
    FLAGS_FILE,
    FORMABLES_FILE,
    PATTERN_DIR,
)
from rnw.eu5_story import (
    LOCALIZATION,
    MODIFIERS_FILE,
    PRIVILEGES_FILE,
    START_FILE,
    StoryError,
    build,
    facts_of,
    modifier_block,
    payload,
)
from rnw.pdx import Block, parse
from rnw.stories import STORIES
from rnw.storymodel import LOCATION, PULSE_FILE, STATIC, Modifier, Source

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
    "consolidated_trade_modifier": ("country", True, "selling_efficiency = 0.1"),
    "iro_strong_tribal_unity": ("country", False, "global_defensive = 0.15"),
    "seal_of_hansa_modifier": ("country", False, "monthly_diplomats = 0.1"),
    "pue_unification_of_the_ancestral_puebloans": ("country", False, "monthly_prestige = 0.25"),
    "lat_a_distinct_latin_bureaucracy": ("country", True, "global_monthly_control = 0.005"),
}
RANKS = (
    "rank_county = { level = 1 }\nrank_duchy = { level = 2 }\n"
    "rank_kingdom = { level = 3 }\nrank_empire = { level = 4 }\n"
)
PICTURES = (
    "ce_checky_15_points.dds",
    "ce_mountain.dds",
    "ce_anchor_shield.dds",
    "ce_rosette_06.dds",
    "ce_star_08.dds",
)
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


def _sources() -> dict[str, tuple[str, bool, str]]:
    """A synthetic vanilla source for every static modifier any story or formable copies."""
    found = dict(SOURCES)
    for story in STORIES:
        for modifier in story.modifiers:
            if modifier.source.kind == STATIC:
                _ = found.setdefault(modifier.source.name, (modifier.category, False, "x = 1"))
    return found


def _install(root: Path, *, drop: str = "", ranks: str = RANKS) -> Path:
    game = root / "game"
    for directory, names in ((EMBLEM_DIR, PICTURES), (PATTERN_DIR, ("pattern_solid.dds",))):
        for name in names:
            picture = root / directory / name
            picture.parent.mkdir(parents=True, exist_ok=True)
            _ = picture.write_bytes(b"DDS ")
    statics = "".join(
        _static(name, category, decaying, effect)
        for name, (category, decaying, effect) in _sources().items()
        if name != drop
    )
    for relative, text in {
        "main_menu/common/static_modifiers/country.txt": statics,
        "in_game/common/building_types/event_only_buildings.txt": BUILDING,
        "in_game/common/estate_privileges/clergy_estate.txt": PRIVILEGE,
        "in_game/common/country_ranks/00_default.txt": ranks,
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
        (Formation(RIVER_UNION, 0, ("loc_a", "loc_c"), ("loc_a",), ("ABC", "DEF"), "loc_a"),),
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
    # a world with no bearer at all still has the stories that find theirs in play
    empty = _build(_install(tmp_path), ContentPlan((), (), ()))
    pulse = {story.namespace for story in STORIES if story.pulse is not None}
    assert {path for path in empty if path.startswith("in_game/events/")} == {
        f"in_game/events/{namespace}.txt" for namespace in pulse
    }
    assert START_FILE not in empty
    assert PULSE_FILE in empty


def test_a_union_is_a_formable_of_a_tag_the_game_does_not_define(tmp_path: Path) -> None:
    """The formable, flag, coat of arms, colour and names that the vanilla ADU has."""
    files = _build(_install(tmp_path))
    formable = files[FORMABLES_FILE].decode("utf-8-sig")
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
    assert "XYZ = {" in files[FLAGS_FILE].decode("utf-8-sig")
    assert "map_XYZ = rgb" in files[COLORS_FILE].decode("utf-8-sig")
    arms = files[ARMS_FILE].decode("utf-8-sig")
    assert 'pattern = "pattern_solid.dds"' in arms
    english = files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"].decode("utf-8-sig")
    assert ' XYZ: "Alto Union"' in english
    assert ' XYZ_ADJ: "Alto"' in english
    # the formables list names a formable by its own key and describes it by ``<key>_desc``
    # (``rnw_union_2_f`` showed as a bare key and was logged as missing, EU5 1.4.4, 036)
    for entry in parse(formable).entries:
        if entry.key is not None:
            assert f" {entry.key}: " in english, entry.key
            assert f" {entry.key}_desc: " in english, entry.key
    assert ' rnw_union_1_f: "$XYZ$"' in english


def test_the_texts_are_written_in_every_language_the_same(tmp_path: Path) -> None:
    """Until L1 translates them, each language carries the English text."""
    files = _build(_install(tmp_path))
    english = files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"]
    turkish = files[f"{LOCALIZATION}/turkish/rnw_story_l_turkish.yml"]
    assert english.decode("utf-8-sig").replace("l_english:", "l_x:") == turkish.decode(
        "utf-8-sig"
    ).replace("l_turkish:", "l_x:")
    assert b"rnw_river.1.title" in english
    assert len(STORIES) == len({story.family for story in STORIES}) == 8


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


def _everything() -> ContentPlan:
    """An opportunity for each story family, with a second place where the family has one."""
    spec = (
        (RIVER_CENTRE, "AAA", "loc_a", ""),
        (SACRED_CENTRE, "BBB", "loc_b", ""),
        (HARVEST, "CCC", "loc_c", ""),
        (ROUTE_MARKET, "DDD", "loc_d", "loc_e"),
        (GREAT_ALLIANCE, "EEE", "loc_f", "loc_g"),
        (EMPIRE_PERIPHERY, "FFF", "loc_h", "loc_i"),
    )
    return ContentPlan(
        tuple(
            Opportunity(family, tag, centre, Start(1350 + number, 1395 + number, 3), other)
            for number, (family, tag, centre, other) in enumerate(spec)
        ),
        (),
        (),
    )


def _starts_by_tag(start: str) -> dict[str, str]:
    """The text of each start event by the tag of the bearer it is bound to."""
    found: dict[str, str] = {}
    for entry in parse(start).entries:
        if entry.key and isinstance(entry.value, Block):
            window = entry.value.block("dynamic_historical_event")
            tag = window.first("tag") if window is not None else None
            assert tag is not None
            found[str(tag.value)] = start[entry.start : entry.end]
    return found


def test_every_story_family_is_written_with_its_own_start(tmp_path: Path) -> None:
    """One events file per family, and a start that binds the places the family is about."""
    files = _build(_install(tmp_path), _everything())
    for story in STORIES:  # the planned families and the ones that find their bearers in play
        assert f"in_game/events/{story.namespace}.txt" in files, story.family
    starts = _starts_by_tag(files[START_FILE].decode("utf-8-sig"))
    assert set(starts) == {"AAA", "BBB", "CCC", "DDD", "EEE", "FFF"}
    route = starts["DDD"]
    assert "name = rnw_route_from value = location:loc_d" in route
    assert "name = rnw_route_to value = location:loc_e" in route
    assert route.count("owns = ") == 2  # a route's bearer holds both ends
    alliance = starts["EEE"]
    assert "name = rnw_alliance_seat value = location:loc_g" in alliance
    assert alliance.count("owns = ") == 1  # the partner's capital is not the bearer's
    assert "name = rnw_alliance_home value = location:loc_f" in alliance
    harvest = starts["CCC"]
    assert "rnw_harvest_centre value = location:loc_c" in harvest
    assert harvest.count("set_variable") == 1


def test_every_modifier_of_every_story_is_written_once_in_the_modifiers_file(
    tmp_path: Path,
) -> None:
    """The names are unique across the families, and each has its text in every language."""
    files = _build(_install(tmp_path), _everything())
    modifiers = parse(files[MODIFIERS_FILE].decode("utf-8-sig"))
    written = [entry.key for entry in modifiers.entries if entry.key]
    wanted = [modifier.name for story in STORIES for modifier in story.modifiers]
    assert sorted(written) == sorted(wanted)
    assert len(written) == len(set(written))
    english = files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"].decode("utf-8-sig")
    for name in wanted:
        assert f" STATIC_MODIFIER_NAME_{name}: " in english
        assert f" STATIC_MODIFIER_DESC_{name}: " in english


def test_colonial_names_are_written_for_the_regions_a_world_has(tmp_path: Path) -> None:
    """One scripted name per tradition and region, with its texts in every language."""
    root = _install(tmp_path)
    for directory, keys in (
        (LANGUAGES_DIR, ("spanish_language", "portuguese_language", "english_language")),
        (LANGUAGES_DIR, ("french_language",)),
        (GROUPS_DIR, ("netherlandish_group",)),
    ):
        path = root / directory / f"{keys[0]}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("".join(f"{key} = {{ }}\n" for key in keys))
    plan = ContentPlan((), (), ())
    made = build(
        root,
        plan,
        names={},
        tags=[],
        languages=("english", "turkish"),
        seed=5,
        taken=frozenset(),
        regions={"north_region": "Ingari"},
    )
    assert NAMES_FILE in made.files
    assert made.stats["colonial_names"] == len(TRADITIONS)
    english = made.files[f"{LOCALIZATION}/english/rnw_story_l_english.yml"].decode("utf-8-sig")
    assert ' rnw_english_north_region_scripted_country_name: "New Ingari"' in english
    none = build(
        root,
        plan,
        names={},
        tags=[],
        languages=("english",),
        seed=5,
        taken=frozenset(),
    )
    assert NAMES_FILE not in none.files
    assert none.stats["colonial_names"] == 0


def test_every_hidden_event_is_written_as_the_games_own_hidden_events_are(tmp_path: Path) -> None:
    """The engine logs an event without a title even when it is hidden (EU5 1.4.4, sitting 038):
    the game's hidden events carry ``title = empty_text``, ``desc = empty_text`` and an outcome."""
    files = _build(_install(tmp_path), _everything())
    scripts = [files[START_FILE], *(files[f"in_game/events/{s.namespace}.txt"] for s in STORIES)]
    hidden = 0
    for data in scripts:
        for entry in parse(data.decode("utf-8-sig")).entries:
            block = entry.value
            if not isinstance(block, Block) or block.first("hidden") is None:
                continue
            hidden += 1
            for key, wanted in (
                ("title", "empty_text"),
                ("desc", "empty_text"),
                ("outcome", "neutral"),
            ):
                found = block.first(key)
                assert found is not None, f"{entry.key} has no {key}"
                assert found.value == wanted, entry.key
    assert hidden >= 6 + len(STORIES) * 1  # the starts, the cleanups and the pulse starts
