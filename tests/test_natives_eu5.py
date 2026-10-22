"""EU5 native start state: matching, tags, colours and setup text (synthetic fixtures)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_biomes import CellBiomes
from rnw.eu5_natives import (
    COUNTRY_NAME,
    OPERATORS,
    Country,
    Culture,
    NativesError,
    PlaceNamer,
    VanillaNatives,
    _include,  # pyright: ignore[reportPrivateUsage]
    country_definitions,
    country_names,
    country_records,
    diaspora,
    homeland,
    hsv_rgb,
    land_graph,
    map_colors,
    match_homelands,
    new_tags,
    overlord_level,
    template_governments,
    template_levels,
    vanilla_colors,
    vassal_lines,
    vassal_pairs,
)
from rnw.eu5_nw_export import referenced_words
from rnw.eu5_rewrite import insert_into_block, prune_setup
from rnw.eu5_technology import FAMILIES, MESOAMERICA, NORTH_AMERICA, plain
from rnw.loc_keys import KeySpace, key_hashes
from rnw.model import CellClass
from rnw.names import MarkovNames, name_key
from rnw.newworld import NewWorld
from rnw.pdx import parse
from rnw.societies import STATE, TRIBE, Polity, Societies

if TYPE_CHECKING:
    from pathlib import Path


def _country(tag: str, kind: str) -> Country:
    return Country(
        tag=tag,
        name="Xatlan",
        kind=kind,
        members=("loc_a", "loc_b"),
        capital="loc_a",
        culture="test_culture",
        religion="test_religion",
        include="test_template",
        areas=("area_one",),
        color=(10, 20, 30),
        color2=(200, 100, 0),
    )


def test_homeland_weights_climate_states_and_families() -> None:
    """Shares are pop-weighted permille; climate, state share and the families count double."""
    vector = homeland(
        ["tropical", "arid"],
        ["jungle", "desert"],
        ["hills", "flatland"],
        [100, -300],
        [True, False],
        [True, False],
        [3, 1],
        [MESOAMERICA, NORTH_AMERICA],
    )
    climates = vector[:11]
    assert sum(climates) == 2 * 1000
    states, latitude, coast, *family = vector[-6:]
    assert states == 2 * 750
    assert latitude == (3 * 100 + 300) // 4 // 2
    assert coast == 750 // 2
    assert family == [2 * 750, 0, 2 * 250]
    assert len(vector) == 11 + 7 + 5 + 3 + len(FAMILIES)


def test_a_zone_follows_the_family_of_its_land_over_a_better_climate() -> None:
    """A Mesoamerican zone takes the Mesoamerican culture unless the climate gap is larger."""

    def vector(climates: list[str], members: list[str]) -> tuple[int, ...]:
        count = len(climates)
        return homeland(
            climates,
            ["jungle"] * count,
            ["hills"] * count,
            [100] * count,
            [True] * count,
            [False] * count,
            [1] * count,
            members,
        )

    here = vector(["tropical"] * 2, [MESOAMERICA] * 2)
    candidates = [
        ("northern", vector(["tropical"] * 2, [NORTH_AMERICA] * 2)),
        ("southern", vector(["tropical", "subtropical"], [MESOAMERICA] * 2)),
    ]
    # the climate alone fits the northern culture better; the family decides for the other
    plain_candidates = [(name, plain(found)) for name, found in candidates]
    assert match_homelands([(plain(here), 1)], plain_candidates, key=1) == ["northern"]
    assert match_homelands([(here, 1)], candidates, key=1) == ["southern"]


def test_match_prefers_own_pool_and_unused_candidates() -> None:
    """Zones take unused candidates of their pool and reuse only a much better fit."""
    zones = [((0, 0), 30), ((0, 0), 20), ((1000, 1000), 10)]
    candidates = [("near", (0, 0)), ("also_near", (100, 0)), ("far", (5000, 5000))]
    chosen = match_homelands(zones, candidates, key=1)
    assert sorted(chosen[:2]) == ["also_near", "near"]
    assert chosen[2] in {"near", "also_near"}
    pooled = match_homelands(zones, candidates, key=1, preferred=[[2], [2], [0]])
    assert pooled == ["far", "far", "near"]


def test_tags_are_fresh_three_letter_words() -> None:
    """Generated tags avoid reserved words and keyword-like operators."""
    reserved = frozenset({"ABC", "XYZ"}) | OPERATORS
    tags = new_tags(500, reserved, seed=9, keys=KeySpace(set()))
    assert len(set(tags)) == 500
    assert all(len(tag) == 3 and tag.isalpha() and tag.isupper() for tag in tags)
    assert not set(tags) & reserved
    assert tags == new_tags(500, reserved, seed=9, keys=KeySpace(set()))


def test_tags_skip_taken_localization_hashes() -> None:
    """A tag is skipped when the hash of its name or adjective key is already taken."""
    first = new_tags(2, frozenset(), seed=9, keys=KeySpace(set()))
    taken = key_hashes([f"{first[0]}_ADJ"])
    tags = new_tags(2, frozenset(), seed=9, keys=KeySpace(taken))
    assert first[0] not in tags
    assert tags[0] == first[1]


def test_hsv_primaries() -> None:
    """Integer HSV maps hue sectors to the expected channels."""
    assert hsv_rgb(0, 1000, 1000) == (255, 0, 0)
    assert hsv_rgb(120, 1000, 1000) == (0, 255, 0)
    assert hsv_rgb(240, 1000, 1000) == (0, 0, 255)
    assert hsv_rgb(60, 1000, 1000) == (255, 255, 0)
    assert hsv_rgb(200, 0, 500) == (127, 127, 127)


TEMPLATES = {
    "typed": "government = {\n\ttype = monarchy\n}\n",
    "nested": 'include = "typed"\ngovernment = {\n\truler = random\n}\n',
    "open": "starting_technology_level = 2\ngovernment = {\n\tparliament = { }\n}\n",
    "orphan": "government = {\n}\n",
    "loop_a": 'include = "loop_b"\n',
    "loop_b": 'include = "loop_a"\n',
    "monarch": "government = {\n\ttype = monarchy\n\their_selection = tribal_oldest_male\n}\n",
}
OPEN_USERS = """countries = {
\tcountries = {
\t\tAAA = {
\t\t\tinclude = "open"
\t\t\tgovernment = { type = republic heir_selection = oligarchic_elective ruler = x }
\t\t}
\t\tBBB = {
\t\t\tinclude = "open"
\t\t\tgovernment = { type = republic heir_selection = oligarchic_elective }
\t\t}
\t\tCCC = {
\t\t\tinclude = "open"
\t\t\tgovernment = { type = monarchy }
\t\t}
\t\tDDD = {
\t\t\tinclude = "orphan"
\t\t\tgovernment = { ruler = random }
\t\t}
\t\tEEE = {
\t\t\tinclude = "monarch"
\t\t\tgovernment = { type = monarchy heir_selection = cognatic_primogeniture }
\t\t}
\t\tFFF = {
\t\t\tinclude = "nested"
\t\t}
\t}
}
"""


def test_template_governments_follow_their_vanilla_users() -> None:
    """A template takes what its vanilla users write most; it needs a type from somewhere."""
    governments = template_governments(TEMPLATES, OPEN_USERS)
    assert governments == {
        "typed": (),
        "nested": (),
        "open": (("type", "republic"), ("heir_selection", "oligarchic_elective")),
        "monarch": (("type", "monarchy"), ("heir_selection", "cognatic_primogeniture")),
    }


def test_country_records_add_the_template_government() -> None:
    """A country with an open template writes the completed government fields."""
    country = replace(
        _country("QQA", "state"),
        include="open",
        government=(("type", "republic"), ("heir_selection", "oligarchic_elective")),
    )
    text = "countries = {\n\tcountries = {\n" + country_records((country,)) + "\t}\n}\n"
    government = parse(text).block("countries", "countries", "QQA", "government")
    assert government is not None
    assert [(entry.key, entry.value) for entry in government.entries] == [
        ("type", "republic"),
        ("heir_selection", "oligarchic_elective"),
        ("ruler", "random"),
    ]


def test_country_texts_parse_and_name_every_tag() -> None:
    """Records, definitions and names parse and agree for states and tribes."""
    countries = (_country("QQA", "state"), _country("QQB", "tribe"))
    setup = "countries = {\n\tcountries = {\n\tOLD = {\n\t}\n\t}\n}\n"
    text = insert_into_block(setup, ("countries", "countries"), country_records(countries))
    holder = parse(text).block("countries", "countries")
    assert holder is not None
    records = {entry.key: entry.value for entry in holder.entries}
    assert set(records) == {"OLD", "QQA", "QQB"}
    state = parse(text).block("countries", "countries", "QQA")
    tribe = parse(text).block("countries", "countries", "QQB")
    assert state is not None
    assert tribe is not None
    assert state.first("capital") is not None
    assert tribe.first("type") is not None
    assert tribe.first("capital") is None
    core = state.block("own_control_core")
    assert core is not None
    assert [word.value for word in core.words()] == ["loc_a", "loc_b"]
    definitions = parse(country_definitions(countries).decode("utf-8-sig"))
    assert {entry.key for entry in definitions.entries} == {"QQA", "QQB"}
    assert country_names(countries) == {
        "QQA": "Xatlan",
        "QQA_ADJ": "Xatlan",
        "QQB": "Xatlan",
        "QQB_ADJ": "Xatlan",
    }


def test_prune_setup_writes_generated_pops() -> None:
    """Generated locations get their pop lines; removed ones disappear."""
    texts = {"06_pops.txt": "locations={\ngone = {\n\tdefine_pop = { type = peasants }\n}\n}\n"}
    pops = {"new_a": ["\tdefine_pop = { type = tribesmen size = 1.000 }"], "new_b": []}
    result = prune_setup(texts, {"gone"}, pops)
    holder = parse(result.texts["06_pops.txt"]).block("locations")
    assert holder is not None
    assert [entry.key for entry in holder.entries] == ["new_a", "new_b"]
    first = holder.block("new_a")
    assert first is not None
    assert len(list(first.find("define_pop"))) == 1


def test_named_colour_values_are_not_location_references() -> None:
    """A colour that spells a key is not a reference; a key on the left side is."""
    path = "in_game/map_data/named_locations/00_default.txt"
    text = "rnw_loc_00001 = dabaca\ndabaca = 123456 # dabaca\n"
    assert referenced_words(path, text) == {"rnw_loc_00001", "dabaca"}
    assert referenced_words(path, "rnw_loc_00001 = dabaca\n") == {"rnw_loc_00001"}
    assert "dabaca" in referenced_words("in_game/common/x.txt", "a = dabaca\n")


def test_land_graph_links_shores_and_scores_farming() -> None:
    """Sea coasts count as coastal, lakes only link shores; poles cannot farm."""
    classes = (CellClass.LAND, CellClass.LAND, CellClass.LAKE, CellClass.LAND, CellClass.SEA)
    small = np.zeros(5, dtype=np.int64)
    world = NewWorld(
        labels=np.zeros((1, 1), dtype=np.int32),
        classes=classes,
        elevation=np.zeros((1, 1), dtype=np.int32),
        pixels=np.full(5, 1000, dtype=np.int64),
        centroids=np.array([[4839, 0], [4839, 10], [4839, 20], [200, 30], [200, 40]]),
        interior=np.zeros((5, 2), dtype=np.int64),
        mean_elevation=small,
        spread=small,
        edges=((0, 1), (1, 2), (2, 3), (3, 4)),
    )
    biomes = CellBiomes(
        climate=("tropical", "tropical", "", "arctic", ""),
        vegetation=("grasslands", "jungle", "", "sparse", ""),
        topography=("flatland", "mountains", "", "flatland", ""),
        raw_material=("", "", "", "", ""),
    )
    vanilla = VanillaNatives(
        density={"tropical": 5000, "arctic": 300},
        population_per_location=0,
        cultures={},
        religions={},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
    )
    graph, cells = land_graph(world, biomes, small, vanilla)
    assert cells.cells == [0, 1, 3]
    assert graph.edges.tolist() == [[0, 1]]
    assert graph.links.tolist() == [[1, 2]]
    assert cells.coastal == [False, False, True]
    assert cells.seas == [[], [], [4]]
    assert graph.potential[0] == 900  # tropical grassland plain
    assert graph.potential[2] == 0  # far beyond 65 degrees
    assert graph.capacity[0] == 5000  # 1000 px at 5 per 1000 px
    assert graph.cost[1] > graph.cost[0]


def test_markov_names_are_new_unique_and_seeded() -> None:
    """Draws repeat for a seed, never copy the corpus and never repeat each other."""
    corpus = [
        f"{a}{b}{c}"
        for a in ("Tla", "Xo", "Cua")
        for b in ("ca", "chi", "te")
        for c in ("pan", "tlan", "co")
    ]
    first = MarkovNames(corpus, 3, "test", set())
    names = [first.next() for _ in range(40)]
    again = MarkovNames(corpus, 3, "test", set())
    assert names == [again.next() for _ in range(40)]
    assert len({name_key(name) for name in names}) == len(names)
    assert not {name_key(name) for name in names} & {name_key(name) for name in corpus}
    assert name_key("Caxitlán") == name_key("caxitlan")


def test_place_namer_backs_off_to_larger_corpora() -> None:
    """A culture with few names borrows its religion's corpus; unknown ones use all."""
    places = tuple((f"Ka{i:02d}lan", "big_culture") for i in range(50))
    places += (("Xolo", "small_culture"),)
    culture = Culture("faith", (), 1, "", "", "", "")
    vanilla = VanillaNatives(
        density={},
        population_per_location=0,
        cultures={"big_culture": culture, "small_culture": culture},
        religions={},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
        places=places,
        languages={"big_culture": ("big_language", ""), "small_culture": ("small_language", "")},
        reserved_names=frozenset(),
    )
    namer = PlaceNamer(vanilla, seed=1)
    drawn = [namer.name("small_culture") for _ in range(5)] + [namer.name("unknown")]
    assert len({name_key(name) for name in drawn}) == len(drawn)
    assert all(name_key(name) not in {name_key(p) for p, _ in places} for name in drawn)


def test_vassal_lines_parse_as_dependencies() -> None:
    """Vassal pairs become dependency records inside the diplomacy manager."""
    text = insert_into_block(
        "diplomacy_manager = {\n}\n", ("diplomacy_manager",), vassal_lines((("QQA", "QQB"),))
    )
    holder = parse(text).block("diplomacy_manager")
    assert holder is not None
    record = holder.block("dependency")
    assert record is not None
    fields = {entry.key: entry.value for entry in record.entries}
    assert fields == {"first": "QQA", "second": "QQB", "subject_type": "vassal"}
    assert vassal_lines(()) == ""


def test_map_colours_avoid_vanilla_colours_and_each_other() -> None:
    """No generated colour repeats a taken one, even when its best draw would."""
    plain = map_colors([set(), {0}, {0, 1}], 7, frozenset())
    first = {color for color, _ in plain}
    assert len(first) == 3
    taken = frozenset({plain[0][0], plain[2][0]})
    moved = map_colors([set(), {0}, {0, 1}], 7, taken)
    chosen = [color for color, _ in moved]
    assert not set(chosen) & taken
    assert len(set(chosen)) == 3
    assert map_colors([set(), {0}, {0, 1}], 7, taken) == moved


def test_vanilla_colours_resolve_named_and_inline_definitions(tmp_path: Path) -> None:
    """Every country's colour counts, whether it names a map colour or spells one."""
    named = tmp_path / "game/main_menu/common/named_colors/02_map.txt"
    named.parent.mkdir(parents=True)
    colors = "colors = {\n\tmap_a = rgb { 10 20 30 }\n\tmap_b = hsv360 { 0 100 100 }\n"
    _ = named.write_text(colors + "\tmap_c = rgb { 1 2 }\n}\n", encoding="utf-8")
    countries = tmp_path / "game/in_game/setup/countries"
    countries.mkdir(parents=True)
    definitions = [
        "AAA = {\n\tcolor = map_a\n\tcolor2 = rgb { 9 9 9 }\n}\n",
        "BBB = {\n\tcolor = rgb { 40 50 60 }\n}\n",
        "CCC = {\n\tcolor = map_b\n}\nDDD = {\n\tcolor = map_c\n}\n",
    ]
    _ = (countries / "x.txt").write_text("".join(definitions), encoding="utf-8")
    assert vanilla_colors(tmp_path) == {(10, 20, 30), (40, 50, 60), (255, 0, 0)}


def test_diaspora_gives_every_unused_culture_and_religion_a_small_pop() -> None:
    """Unused cultures and religions get one small pop in the zone that fits them best."""

    def culture(religion: str, vector: tuple[int, ...]) -> Culture:
        return Culture(religion, vector, 1, "", "", "", "")

    zero = np.zeros(3, dtype=np.int64)
    societies = Societies(
        complexity=zero,
        population=np.array([1000, 2000, 0], dtype=np.int64),
        peasants=zero,
        religion=np.array([0, 1, 1], dtype=np.int64),
        culture=np.array([0, 1, 1], dtype=np.int64),
        hearths=(),
        polities=(),
        ranks={},
        markets=(),
    )
    west, east = (1000, 0, 0), (0, 1000, 0)
    vanilla = VanillaNatives(
        density={},
        population_per_location=0,
        cultures={
            "c0": culture("r0", west),
            "c1": culture("r1", east),
            "cx": culture("rx", east),
            "cy": culture("r0", west),
        },
        religions={"r0": (west, 1), "r1": (east, 1), "rx": (east, 1), "rz": (west, 1)},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
    )
    rows = diaspora(
        societies,
        ["k0", "k1", "k2"],
        zones=[(west, 1000), (east, 2000)],
        state=np.array([False, True, False]),
        religions=["r0", "r1"],
        cultures=["c0", "c1"],
        vanilla=vanilla,
        seed=1,
    )
    assert sorted(rows) == ["k0", "k1"]
    assert rows["k0"] == [
        "\tdefine_pop = {\ttype = tribesmen\tsize = 0.050\tculture = cy\treligion = r0 }",
        "\tdefine_pop = {\ttype = tribesmen\tsize = 0.050\tculture = c0\treligion = rz }",
    ]
    assert rows["k1"] == [
        "\tdefine_pop = {\ttype = peasants\tsize = 0.050\tculture = cx\treligion = rx }"
    ]


def test_country_name_pattern_reads_names_and_adjectives() -> None:
    """Vanilla country names, with or without a version number, are told from adjectives."""
    text = ' WNA: "Wanga"\n WNA_ADJ: "Wangan"\n FOO:0 "Bar"\n'
    assert COUNTRY_NAME.findall(text) == [("WNA", "Wanga"), ("WNA_ADJ", "Wangan"), ("FOO", "Bar")]


LEVELS = {
    "plain": "starting_technology_level = 0\ngovernment = { type = monarchy }\n",
    "advanced": "starting_technology_level = 2\n",
    "nested": 'include = "advanced"\ninclude = "missing"\n',
    "silent": "government = { type = tribe }\n",
    "loop_a": 'include = "loop_b"\n',
    "loop_b": 'include = "loop_a"\n',
}


def test_template_levels_follow_includes() -> None:
    """A template has the level it sets or its includes set; none is no level."""
    assert template_levels(LEVELS) == {"plain": 0, "advanced": 2, "nested": 2}


def test_overlord_level_is_the_lowest_of_the_vanilla_lords() -> None:
    """Lords without a known level do not count; no lord with one stops the build."""
    setup = (
        "countries = { countries = {\n"
        'AAA = { include = "advanced" include = "silent" }\n'
        'BBB = { include = "nested" }\n'
        'CCC = { include = "silent" }\n'
        'DDD = { include = "plain" }\n}\n}\n'
    )
    levels = template_levels(LEVELS)
    diplomacy = (
        "dependency = { first = AAA second = XXX subject_type = vassal }\n"
        "dependency = { first = BBB second = XXX subject_type = vassal }\n"
        "dependency = { first = CCC second = XXX subject_type = vassal }\n"
        "dependency = { first = DDD second = XXX subject_type = tributary }\n"
    )
    assert overlord_level(setup, diplomacy, levels) == 2
    with pytest.raises(NativesError):
        _ = overlord_level(setup, "", levels)


def test_overlords_come_from_able_states_only() -> None:
    """The biggest able state leads; a bigger unable neighbour can only follow."""
    polities = (
        Polity(STATE, (0,), 0, 0),
        Polity(STATE, (1,), 1, 0),
        Polity(STATE, (2,), 2, 0),
        Polity(TRIBE, (3,), 3, 0),
    )
    societies = Societies(
        complexity=np.zeros(4, dtype=np.int64),
        population=np.array([9000, 5000, 1000, 100], dtype=np.int64),
        peasants=np.zeros(4, dtype=np.int64),
        religion=np.zeros(4, dtype=np.int64),
        culture=np.zeros(4, dtype=np.int64),
        hearths=(),
        polities=polities,
        ranks={},
        markets=(),
    )
    near: list[set[int]] = [{1, 2}, {0, 2}, {0, 1}, set()]
    assert vassal_pairs(societies, ["x"], near, {1, 2}) == [(1, 2)]
    # state 1 is more than a third of state 0, so only state 2 can follow it
    assert vassal_pairs(societies, ["x"], near, {0, 1, 2}) == [(0, 2)]
    assert vassal_pairs(societies, ["x"], near, set()) == []


def test_a_great_empire_takes_a_template_that_can_lead_vassals() -> None:
    """Its culture's template stays if it has the level a lord needs, else the advanced one."""
    lord = Culture("faith", (), 1, "tier_two", "", "", "")
    weak = Culture("faith", (), 1, "tier_zero", "", "", "")
    vanilla = VanillaNatives(
        density={},
        population_per_location=0,
        cultures={"lord": lord, "weak": weak},
        religions={},
        templates=frozenset({"tier_two", "tier_zero", "amerindian_advanced_monarchy_not_nahuatl"}),
        reserved_tags=frozenset(),
        holy_sites=(),
        levels={"tier_two": 2, "tier_zero": 0, "amerindian_advanced_monarchy_not_nahuatl": 2},
        overlord_level=2,
    )
    advanced = "amerindian_advanced_monarchy_not_nahuatl"
    assert _include(vanilla, "lord", level=2, coastal=True, empire=True) == "tier_two"
    assert _include(vanilla, "weak", level=1, coastal=True) == "tier_zero"
    assert _include(vanilla, "weak", level=1, coastal=True, empire=True) == advanced
    assert _include(vanilla, "nobody", level=2, coastal=True, empire=True) == advanced
