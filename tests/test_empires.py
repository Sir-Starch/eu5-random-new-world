"""Great empires with causes and weaknesses (synthetic fixtures)."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pytest

from rnw.eu5_empires import (
    FEAR,
    IRRITATED,
    OPINION_TYPES,
    PREY,
    TYRANT,
    EmpireCalibration,
    EmpireError,
    american_rank,
    defined_biases,
    empire_calibration,
    empire_opinions,
    empire_roads,
    extraordinary_report,
    highest_level,
    largest_states,
    median,
    opinion_knowledge,
    opinion_lines,
    rank_levels,
    road_density,
    road_lines,
    road_targets,
    share,
    travel_steps,
    unlinked,
    written_discoveries,
    written_ranks,
)
from rnw.eu5_natives import (
    Country,
    NativeWorld,
    VanillaNatives,
    country_records,
    discover_opinion_partners,
)
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import (
    COUNTRIES_FILE,
    SETUP_DIR,
    NewWorldExportError,
    verify_empires,
)
from rnw.eu5_rewrite import insert_into_block
from rnw.model import CellClass
from rnw.newworld import NewWorld
from rnw.pdx import Block, parse
from rnw.societies import STATE, STEP_COST, LandGraph

SETUP = """countries = {
\tcountries = {
\t\tAAA = { own_control_core = { a1 } include = "plain" country_rank = rank_duchy }
\t\tBBB = { own_control_core = { b1 } include = "adv" country_rank = rank_county }
\t\tCCC = { own_control_core = { old1 } include = "old" starting_technology_level = 3
\t\t\tcountry_rank = rank_empire }
\t\tDDD = { type = pop add_pops_from_locations = { a1 } country_rank = rank_kingdom }
\t\tEEE = { own_control_core = { a1 old1 } include = "adv" country_rank = rank_kingdom }
\t}
}
"""
AMERICAN = {"a1", "b1"}
RANKS = [
    "rank_empire = { level = 4 }\nrank_kingdom = { level = 3 }\n",
    "rank_duchy = { level = 2 }\nrank_county = { level = 1 }\n",
    "# only a comment\n",
]
LEVELS = {"plain": 0, "adv": 2, "old": 3}
BIASES = [
    "opinion_threatens_conquest = { value = -50 }\nopinion_prey_to_conquest = { value = -25 }\n",
    "opinion_tyrant_overlord = { value = -50 }\nopinion_irritated = { value = -10 }\nother = { }\n",
]
ROADS = "road_network = {\n\ta1 = b1\n}\n"
LOW_SETUP = (
    "countries = { countries = { AAA = { own_control_core = { a1 } country_rank = rank_duchy } } }"
)


def _calibration(**changes: object) -> EmpireCalibration:
    found = empire_calibration(
        levels=LEVELS,
        state_levels=(0, 1, 2),
        setup_text=SETUP,
        rank_texts=RANKS,
        roads_text=ROADS,
        bias_texts=BIASES,
        american=AMERICAN,
        pops={},
        cultures={},
    )
    return replace(found, **changes)


def test_the_level_is_the_lower_of_the_highest_and_one_above_the_americas() -> None:
    """``min(T, S + 1)``: T from a template or an entry, S from the American states."""
    assert highest_level(LEVELS, SETUP) == 3
    assert highest_level({"a": 1}, SETUP) == 3
    assert highest_level({"a": 1}, "countries = { countries = { X = { } } }") == 1
    assert _calibration().level == 3
    assert (
        empire_calibration(
            levels={"a": 2},
            state_levels=(0, 2),
            setup_text=SETUP,
            rank_texts=RANKS,
            roads_text=ROADS,
            bias_texts=BIASES,
            american=AMERICAN,
            pops={},
            cultures={},
        ).level
        == 3
    )
    low = empire_calibration(
        levels={"a": 3},
        state_levels=(0, 0),
        setup_text=LOW_SETUP,
        rank_texts=RANKS,
        roads_text=ROADS,
        bias_texts=BIASES,
        american=AMERICAN,
        pops={},
        cultures={},
    )
    assert low.level == 1
    with pytest.raises(EmpireError):
        _ = highest_level({}, "countries = { countries = { X = { } } }")


def test_the_rank_is_the_highest_an_american_landed_country_starts_with() -> None:
    """Old World, pop and mixed countries do not count; no rank or an unknown one fails."""
    ranks = rank_levels(RANKS)
    assert ranks == {"rank_empire": 4, "rank_kingdom": 3, "rank_duchy": 2, "rank_county": 1}
    assert american_rank(SETUP, ranks, AMERICAN) == "rank_duchy"
    assert american_rank(SETUP, ranks, {"b1"}) == "rank_county"
    with pytest.raises(EmpireError):
        _ = american_rank(SETUP, ranks, {"nowhere"})
    with pytest.raises(EmpireError):
        _ = american_rank(SETUP, {"rank_county": 1}, AMERICAN)


def test_a_missing_opinion_type_fails() -> None:
    """All four opinion types must be biases."""
    assert set(OPINION_TYPES) <= defined_biases(BIASES)
    for missing in OPINION_TYPES:
        texts = [text.replace(missing, "renamed") for text in BIASES]
        with pytest.raises(EmpireError, match=missing):
            _ = empire_calibration(
                levels=LEVELS,
                state_levels=(0, 1, 2),
                setup_text=SETUP,
                rank_texts=RANKS,
                roads_text=ROADS,
                bias_texts=texts,
                american=AMERICAN,
                pops={},
                cultures={},
            )
    with pytest.raises(EmpireError):
        _ = empire_calibration(
            levels=LEVELS,
            state_levels=(),
            setup_text=SETUP,
            rank_texts=RANKS,
            roads_text=ROADS,
            bias_texts=BIASES,
            american=AMERICAN,
            pops={},
            cultures={},
        )


def test_the_road_bound_is_the_ninetieth_percentile_of_pairs_per_owned_location() -> None:
    """A pair counts for the owner of its first location; only countries with roads count."""
    setup = (
        "countries = { countries = {\n"
        "X = { own_control_core = { x1 x2 } }\n"
        "Y = { own_control_core = { y1 } }\n"
        "Z = { own_control_core = { z1 z2 z3 z4 } }\n"
        "W = { own_control_core = { w1 w2 w3 w4 w5 } }\n"
        "P = { type = pop add_pops_from_locations = { p1 } }\n"
        "} }\n"
    )
    roads = (
        "road_network = {\nx1 = x2\ny1 = x1\nz1 = z2\nz2 = z3\nz3 = z4\nunknown = x1\np1 = x1\n}\n"
    )
    assert road_density(setup, roads) == 1000  # X 500, Z 750, Y 1000 (W has none)
    with pytest.raises(EmpireError):
        _ = road_density(setup, "road_network = {\n}\n")


def test_the_largest_vanilla_states_are_counted_by_locations() -> None:
    """The comparison states come by locations, then tag, with their foreign pops."""
    setup = (
        "countries = { countries = {\n"
        "AAA = { own_control_core = { a1 a2 } }\n"
        "BBB = { own_control_core = { b1 a3 } }\n"
        "CCC = { own_control_core = { c1 } }\n"
        "} }\n"
    )
    pops = {
        "a1": [("peasants", 300, "maya", "r")],
        "a2": [("peasants", 100, "other", "r")],
        "c1": [("peasants", 10, "x", "r")],
    }
    found = largest_states(
        setup, {"a1", "a2", "a3", "b1", "c1"}, pops, {"AAA": "maya", "BBB": "none", "CCC": "x"}
    )
    assert [(state.tag, state.locations) for state in found] == [("AAA", 2), ("BBB", 2), ("CCC", 1)]
    assert [state.foreign_culture_permille for state in found] == [250, 0, 0]


def test_road_targets_are_vassal_capitals_ranked_places_and_the_biggest_of_each_area() -> None:
    """The capital is left out, only the empire's own locations count, and ties break by key."""
    keys = [f"k{n}" for n in range(8)]
    targets = road_targets(
        capital=0,
        vassal_capitals=[7],
        members=[0, 1, 2, 3, 4],
        ranked=[0, 2, 6],
        markets=[3, 5],
        areas=["x", "x", "x", "y", "y", "z", "z", "z"],
        population=[9, 5, 5, 4, 8, 7, 7, 7],
        keys=keys,
    )
    # vassal capital 7; ranked 2 and market 3 of the empire; area x: 0 (the capital, left out)
    # and area y: 4 (most populous). 6 and 5 are not the empire's.
    assert targets == (2, 3, 4, 7)
    tie = road_targets(
        capital=0,
        vassal_capitals=[],
        members=[1, 2, 0],
        ranked=[],
        markets=[],
        areas=["x", "x", "x"],
        population=[1, 5, 5],
        keys=["k0", "k2", "k1"],
    )
    assert tie == (2,)  # nodes 1 and 2 tie in population; key k1 (node 2) is lower than k2


def _graph(count: int, edges: list[tuple[int, int]]) -> LandGraph:
    zero = np.zeros(count, dtype=np.int64)
    return LandGraph(
        capacity=zero,
        potential=zero,
        cost=np.full(count, STEP_COST, dtype=np.int64),
        edges=np.array(edges, dtype=np.int64).reshape(-1, 2),
        links=np.zeros((0, 2), dtype=np.int64),
    )


def test_roads_run_through_the_empire_and_its_vassals_and_leave_islands_unlinked() -> None:
    """A target on another island, or beyond a foreign state, is reported unlinked."""
    graph = _graph(7, [(0, 1), (1, 2), (2, 3), (4, 5), (3, 6)])
    roads = empire_roads(graph, capital=0, members=[0, 1], vassal_members=[2], targets=[2, 3, 5])
    assert roads == ((0, 1), (1, 2))
    assert unlinked(roads, 0, [2, 3, 5]) == (3, 5)
    assert unlinked(roads, 0, [0, 1]) == ()


def test_travel_steps_and_report_helpers() -> None:
    """Steps are whole steps from the capital; the median is the upper one."""
    graph = _graph(4, [(0, 1), (1, 2)])
    assert travel_steps(graph, {0, 1, 2}, 0, [1, 2, 3]) == [1, 2]
    assert median([3, 1, 2]) == 2
    assert median([1, 2, 3, 4]) == 3
    assert median([]) == 0
    assert share(1, 3) == 333
    assert share(1, 0) == 0


def test_neighbours_fear_the_empire_and_vassals_resent_it_once_each() -> None:
    """Contact gives the fear pair, vassalage the resentment pair, a vassal is never feared."""
    found = empire_opinions("EMP", ["NBB", "NBA", "VAS", "EMP", "NBA"], ["VAS", "VAB", "VAS"])
    assert found == (
        ("NBA", "EMP", FEAR),
        ("EMP", "NBA", PREY),
        ("NBB", "EMP", FEAR),
        ("EMP", "NBB", PREY),
        ("VAB", "EMP", TYRANT),
        ("EMP", "VAB", IRRITATED),
        ("VAS", "EMP", TYRANT),
        ("EMP", "VAS", IRRITATED),
    )
    assert len(set(found)) == len(found)
    assert empire_opinions("EMP", [], []) == ()


def test_generated_lines_parse_into_their_blocks() -> None:
    """Road pairs are sorted once by key; opinions parse as records; nothing gives no text."""
    roads = road_lines([("b", "a"), ("a", "b"), ("c", "d")])
    text = insert_into_block("road_network = {\n\tz = y\n}\n", ("road_network",), roads)
    block = parse(text).block("road_network")
    assert block is not None
    assert [(entry.key, entry.value) for entry in block.entries] == [
        ("z", "y"),
        ("a", "b"),
        ("c", "d"),
    ]
    lines = opinion_lines([("A", "B", FEAR)])
    setup = insert_into_block("diplomacy_manager = {\n}\n", ("diplomacy_manager",), lines)
    manager = parse(setup).block("diplomacy_manager")
    assert manager is not None
    [opinion] = list(manager.find("opinion"))
    assert isinstance(opinion.value, Block)
    assert {e.key: e.value for e in opinion.value.entries} == {
        "first": "A",
        "second": "B",
        "type": FEAR,
    }
    assert road_lines([]) == ""
    assert opinion_lines([]) == ""


def _country(tag: str, members: tuple[str, ...], **changes: object) -> Country:
    base = Country(
        tag=tag,
        name="Xatlan",
        kind=STATE,
        members=members,
        capital=members[0],
        culture="c",
        religion="r",
        include="t",
        areas=("a",),
        color=(1, 2, 3),
        color2=(3, 2, 1),
        level=0,
    )
    return replace(base, **changes)


def test_records_write_the_level_and_the_rank_of_an_empire_only() -> None:
    """The rank follows the level; an ordinary state writes none; the text parses."""
    empire = _country("EMP", ("g0",), great=True, level=3, rank="rank_duchy", include="adv")
    plain = _country("ORD", ("g1",))
    text = "countries = {\n\tcountries = {\n" + country_records((empire, plain)) + "\t}\n}\n"
    record = parse(text).block("countries", "countries", "EMP")
    assert record is not None
    keys = [entry.key for entry in record.entries]
    assert keys.index("country_rank") == keys.index("starting_technology_level") + 1
    assert written_ranks(text, {"EMP", "ORD"}) == {"EMP": ["rank_duchy"], "ORD": []}


KEYS = ("g0", "g1", "g2", "g3", "g4", "g5")
EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (2, 4))
PLANNED_ROADS = (("g0", "g1"), ("g1", "g2"), ("g2", "g3"))
PLANNED_OPINIONS = (
    ("NBR", "EMP", FEAR),
    ("EMP", "NBR", PREY),
    ("VAS", "EMP", TYRANT),
    ("EMP", "VAS", IRRITATED),
)
ORIGINAL_ROADS = "road_network = {\n\told_a = old_b\n}\n"
ORIGINAL_OPINIONS = (
    "diplomacy_manager = {\n"
    "\topinion = { first = OLD second = NEW type = border_aggression }\n"
    "\topinion = { first = GON second = OLD type = opinion_angry }\n"
    "}\n"
)


def _plan(*, area_per_location: bool = False) -> Plan:
    def cell(key: str, kind: CellClass) -> PlannedCell:
        return PlannedCell(
            key=key,
            name=key,
            color=1,
            kind=kind,
            province="p",
            area=key if area_per_location else "a",
            region="r",
            subcontinent="s",
            continent="america",
        )

    return Plan(cells=[cell(key, CellClass.LAND) for key in KEYS])


def _world() -> NewWorld:
    zero = np.zeros(len(KEYS), dtype=np.int64)
    return NewWorld(
        labels=np.zeros((1, 1), dtype=np.int32),
        classes=(CellClass.LAND,) * len(KEYS),
        elevation=np.zeros((1, 1), dtype=np.int32),
        pixels=zero,
        centroids=np.zeros((len(KEYS), 2), dtype=np.int64),
        interior=np.zeros((len(KEYS), 2), dtype=np.int64),
        mean_elevation=zero,
        spread=zero,
        edges=EDGES,
    )


def _countries() -> tuple[Country, ...]:
    return (
        _country("EMP", ("g0", "g1", "g2"), great=True, level=3, rank="rank_duchy", include="adv"),
        _country("VAS", ("g3",)),
        _country("NBR", ("g4",)),
        _country("FAR", ("g5",)),
    )


def _natives(
    countries: tuple[Country, ...] | None = None,
    roads: tuple[tuple[str, str], ...] = PLANNED_ROADS,
    opinions: tuple[tuple[str, str, str], ...] = PLANNED_OPINIONS,
) -> NativeWorld:
    return NativeWorld(
        pops={},
        countries=countries or _countries(),
        ranks={},
        markets=(),
        holy_sites={},
        names={},
        vassals=(("EMP", "VAS"),),
        complexity={},
        population={},
        stats={},
        roads=roads,
        opinions=opinions,
    )


def _vanilla() -> VanillaNatives:
    return VanillaNatives(
        density={},
        population_per_location=0,
        cultures={},
        religions={},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
        empire=EmpireCalibration(
            level=3, rank="rank_duchy", road_permille=1000, opinions=OPINION_TYPES
        ),
    )


def _outputs(
    natives: NativeWorld, *, extra_roads: str = "", extra_opinions: str = ""
) -> dict[str, bytes]:
    countries = "countries = {\n\tcountries = {\n" + country_records(natives.countries) + "\t}\n}\n"
    roads = insert_into_block(ORIGINAL_ROADS, ("road_network",), road_lines(natives.roads))
    gone = "\topinion = { first = GON second = OLD type = opinion_angry }\n"
    kept = ORIGINAL_OPINIONS.replace(gone, "")
    opinions = insert_into_block(kept, ("diplomacy_manager",), opinion_lines(natives.opinions))
    if extra_roads:
        roads = roads.replace("\n}\n", "\n" + extra_roads + "}\n")
    if extra_opinions:
        opinions = opinions.replace("\n}\n", "\n" + extra_opinions + "}\n")
    return {
        f"{SETUP_DIR}/{COUNTRIES_FILE}".removeprefix("game/"): countries.encode(),
        f"{SETUP_DIR}/09_roads.txt".removeprefix("game/"): roads.encode(),
        f"{SETUP_DIR}/18_opinions.txt".removeprefix("game/"): opinions.encode(),
    }


def _verify(
    outputs: dict[str, bytes], natives: NativeWorld, *, area_per_location: bool = False
) -> dict[str, object]:
    return verify_empires(
        outputs,
        natives,
        _plan(area_per_location=area_per_location),
        _world(),
        _vanilla(),
        {"09_roads.txt": ORIGINAL_ROADS, "18_opinions.txt": ORIGINAL_OPINIONS},
        {"GON"},
    )


def test_verification_accepts_the_planned_empire() -> None:
    """Roads, opinions, level and rank are as planned and the Old World is vanilla's."""
    natives = _natives()
    assert _verify(_outputs(natives), natives) == {
        "empire_countries": 1,
        "empire_road_pairs": 3,
        "empire_opinions": 4,
    }


@dataclass(frozen=True, slots=True)
class _Broken:
    """One way to break the output, and the complaint it must draw."""

    message: str
    roads: tuple[tuple[str, str], ...] = PLANNED_ROADS
    opinions: tuple[tuple[str, str, str], ...] = PLANNED_OPINIONS
    state_rank: str = ""
    empire_level: int = 3
    extra_roads: str = ""
    extra_opinions: str = ""
    edit: tuple[str, bytes, bytes] | None = None


REPEATED = "\topinion = { first = NBR second = EMP type = opinion_threatens_conquest }\n"
BROKEN = {
    "out_of_contact": _Broken("not a contact", roads=(*PLANNED_ROADS, ("g0", "g3"))),
    "outside_the_empire": _Broken("not a contact", roads=(*PLANNED_ROADS, ("g4", "g5"))),
    "repeated_pair": _Broken("road pairs are repeated", extra_roads="\tg1 = g0\n"),
    "disconnected": _Broken("not connected", roads=(("g0", "g1"), ("g2", "g3"))),
    "unrelated_opinion": _Broken(
        "unrelated states", opinions=(*PLANNED_OPINIONS, ("FAR", "EMP", FEAR))
    ),
    "repeated_opinion": _Broken("opinions are repeated", extra_opinions=REPEATED),
    "rank_on_a_state": _Broken("writes the ranks", state_rank="rank_duchy"),
    "wrong_level": _Broken("does not write level", empire_level=2),
    "changed_road": _Broken(
        "Old World roads", edit=("09_roads.txt", b"old_a = old_b", b"old_a = old_c")
    ),
    "changed_opinion": _Broken(
        "Old World opinions",
        edit=("18_opinions.txt", b"first = OLD second = NEW", b"first = OLD second = XYZ"),
    ),
}


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_verification_rejects_each_broken_record(case: str) -> None:
    """Each broken record raises, for its own reason, instead of being repaired."""
    broken = BROKEN[case]
    first, vassal, *rest = _countries()
    countries = (
        replace(first, level=broken.empire_level),
        replace(vassal, rank=broken.state_rank),
        *rest,
    )
    natives = _natives(countries, broken.roads, broken.opinions)
    outputs = _outputs(
        natives, extra_roads=broken.extra_roads, extra_opinions=broken.extra_opinions
    )
    if broken.edit is not None:
        name, old, new = broken.edit
        path = f"main_menu/setup/1337/{name}"
        outputs[path] = outputs[path].replace(old, new)
    with pytest.raises(NewWorldExportError, match=broken.message):
        _ = _verify(outputs, natives)


def test_opinion_holders_discover_the_areas_of_their_partners_capitals() -> None:
    """Each holder names the capital area of each partner once; a country without opinions none."""
    capitals = {"EMP": "g0", "NBR": "g4", "VAS": "g3", "FAR": "g5"}
    assert opinion_knowledge(PLANNED_OPINIONS, capitals) == {
        "NBR": frozenset({"g0"}),
        "EMP": frozenset({"g4", "g3"}),
        "VAS": frozenset({"g0"}),
    }
    assert opinion_knowledge((), capitals) == {}
    with pytest.raises(KeyError):
        _ = opinion_knowledge((("NBR", "NOBODY", FEAR),), capitals)


def _unaware_countries() -> tuple[Country, ...]:
    """Each country knows its own areas only, as a generated one does without opinions."""
    return tuple(replace(country, areas=country.members) for country in _countries())


def test_discovering_adds_the_missing_areas_and_leaves_the_rest_as_it_is() -> None:
    """The three holders gain their partners' capital areas, sorted and once; FAR is untouched."""
    countries = _unaware_countries()
    capitals = {country.tag: country.capital for country in countries}
    found = {
        country.tag: country.areas
        for country in discover_opinion_partners(countries, PLANNED_OPINIONS, capitals)
    }
    assert found == {
        "EMP": ("g0", "g1", "g2", "g3", "g4"),
        "VAS": ("g0", "g3"),
        "NBR": ("g0", "g4"),
        "FAR": ("g5",),
    }
    assert discover_opinion_partners(countries, (), capitals) == countries


def test_written_records_name_the_capital_and_the_discovered_areas() -> None:
    """The record's ``capital`` and the words of ``discovered_areas`` are read back."""
    countries = _unaware_countries()
    text = "countries = {\n\tcountries = {\n" + country_records(countries) + "\t}\n}\n"
    found = written_discoveries(text, {"EMP", "FAR", "NOBODY"})
    assert found == {
        "EMP": ("g0", frozenset({"g0", "g1", "g2"})),
        "FAR": ("g5", frozenset({"g5"})),
    }


def test_verification_accepts_opinions_whose_holders_discovered_the_capitals() -> None:
    """With an area per location, discovering is what makes the planned opinions acceptable."""
    countries = _unaware_countries()
    capitals = {country.tag: country.capital for country in countries}
    aware = discover_opinion_partners(countries, PLANNED_OPINIONS, capitals)
    natives = _natives(aware)
    assert _verify(_outputs(natives), natives, area_per_location=True)["empire_opinions"] == 4


@pytest.mark.parametrize(("holder", "partner"), [("NBR", "EMP"), ("EMP", "NBR"), ("VAS", "EMP")])
def test_verification_refuses_a_holder_that_has_not_discovered_the_capital(
    holder: str, partner: str
) -> None:
    """The game warns of a bias toward an undiscovered capital (C170): it is refused, not mended."""
    countries = _unaware_countries()
    capitals = {country.tag: country.capital for country in countries}
    aware = discover_opinion_partners(countries, PLANNED_OPINIONS, capitals)
    capital_area = capitals[partner]
    forgetful = tuple(
        replace(c, areas=tuple(a for a in c.areas if a != capital_area)) if c.tag == holder else c
        for c in aware
    )
    natives = _natives(forgetful)
    with pytest.raises(NewWorldExportError, match=f"{holder} holds .* of {partner} without"):
        _ = _verify(_outputs(natives), natives, area_per_location=True)


def test_an_opinion_the_plan_lacks_is_refused() -> None:
    """Written opinions that the plan does not hold, or that it holds and the text lacks."""
    natives = _natives()
    outputs = _outputs(replace(natives, opinions=PLANNED_OPINIONS[:3]))
    with pytest.raises(NewWorldExportError, match="differ from the plan"):
        _ = _verify(outputs, natives)


def test_a_world_without_empires_needs_no_lines() -> None:
    """Without a great empire nothing is written and the Old World files stay vanilla's."""
    countries = tuple(replace(c, great=False, level=0, rank="") for c in _countries())
    natives = replace(_natives(countries, (), ()), vassals=())
    assert _verify(_outputs(natives), natives) == {
        "empire_countries": 0,
        "empire_road_pairs": 0,
        "empire_opinions": 0,
    }


def test_an_unchanged_file_is_vanillas_and_needs_no_output() -> None:
    """A world without empires leaves the roads file as it is, so it is not among the outputs."""
    countries = tuple(replace(c, great=False, level=0, rank="") for c in _countries())
    natives = replace(_natives(countries, (), ()), vassals=())
    outputs = _outputs(natives)
    del outputs["main_menu/setup/1337/09_roads.txt"]
    assert _verify(outputs, natives)["empire_road_pairs"] == 0


def test_the_report_lists_the_calibration_and_the_vanilla_comparison() -> None:
    """The section names the calibration, one record per empire and the vanilla states."""
    report = extraordinary_report(
        _vanilla().empire or EmpireCalibration(0, "", 0, ()), [{"tag": "EMP"}]
    )
    assert report["calibration"] == {
        "level": 3,
        "rank": "rank_duchy",
        "opinion_types": list(OPINION_TYPES),
        "road_bound_permille": 1000,
    }
    assert report["empires"] == [{"tag": "EMP"}]
    assert report["vanilla_largest_states"] == []
