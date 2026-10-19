"""EU5 native start state: matching, tags, colours and setup text (synthetic fixtures)."""

from __future__ import annotations

import numpy as np

from rnw.eu5_biomes import CellBiomes
from rnw.eu5_natives import (
    OPERATORS,
    Country,
    VanillaNatives,
    country_definitions,
    country_names,
    country_records,
    homeland,
    hsv_rgb,
    land_graph,
    match_homelands,
    new_tags,
)
from rnw.eu5_nw_export import referenced_words
from rnw.eu5_rewrite import insert_into_block, prune_setup
from rnw.model import CellClass
from rnw.newworld import NewWorld
from rnw.pdx import parse


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


def test_homeland_weights_climate_and_states() -> None:
    """Shares are pop-weighted permille; climate and state share count double."""
    vector = homeland(
        ["tropical", "arid"],
        ["jungle", "desert"],
        ["hills", "flatland"],
        [100, -300],
        [True, False],
        [True, False],
        [3, 1],
    )
    climates = vector[:11]
    assert sum(climates) == 2 * 1000
    assert vector[-3] == 2 * 750
    assert vector[-2] == (3 * 100 + 300) // 4 // 2
    assert vector[-1] == 750 // 2


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
    tags = new_tags(500, reserved, seed=9)
    assert len(set(tags)) == 500
    assert all(len(tag) == 3 and tag.isalpha() and tag.isupper() for tag in tags)
    assert not set(tags) & reserved
    assert tags == new_tags(500, reserved, seed=9)


def test_hsv_primaries() -> None:
    """Integer HSV maps hue sectors to the expected channels."""
    assert hsv_rgb(0, 1000, 1000) == (255, 0, 0)
    assert hsv_rgb(120, 1000, 1000) == (0, 255, 0)
    assert hsv_rgb(240, 1000, 1000) == (0, 0, 255)
    assert hsv_rgb(60, 1000, 1000) == (255, 255, 0)
    assert hsv_rgb(200, 0, 500) == (127, 127, 127)


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
