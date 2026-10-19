"""Start development: society terms, harbours, market villages (synthetic fixtures)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw.eu5_development import (
    FULL_CANDIDATES,
    RAY_DIRECTIONS,
    Development,
    DevelopmentCalibration,
    DevelopmentError,
    Site,
    build_development,
    building_lines,
    calibrate,
    development_lines,
    fit_full,
    harbour_values,
    hundredths_text,
    market_villages,
    shelter,
    society_term,
    society_terms,
    spearman_permille,
    template_harbours,
    to_hundredths,
    to_milli,
)
from rnw.eu5_natives import Country, NativeWorld
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import (
    BUILDINGS_FILE,
    DEVELOPMENT_FILE,
    HARBOR,
    SETUP_DIR,
    TEMPLATES,
    NewWorldExportError,
    verify_development,
)
from rnw.eu5_rewrite import drop_block_entries, insert_into_block
from rnw.geography import Location
from rnw.model import CellClass
from rnw.pdx import parse

RULES = """development = {
	base = -2
	coastal = 5
	city = 5
	town = 2
	forest = -2
	flatland = 1
	mesoamerica_region = 12
	plains_region = 5
	cahokia = 7
}
"""
FIELDS = "topography = flatland vegetation = forest climate = tropical"
TEMPLATE_TEXT = f"""a1 = {{ {FIELDS} natural_harbor_suitability = 0.25 }}
a2 = {{ {FIELDS} natural_harbor_suitability = -0.10 }}
a3 = {{ {FIELDS} movement_assistance = {{ x = 1 }} }}
a4 = {{ {FIELDS} natural_harbor_suitability = 0.00 }}
old = {{ {FIELDS} natural_harbor_suitability = 0.75 }}
"""
BUILDINGS = """locations = {
	a1 = { rank = city town_setup = x }
}
building_manager = {
	market_village = { tag = AAA level = 1 location = a2 }
	castle = { tag = OLD level = 1 location = old }
}
"""
COUNTRIES = """countries = {
	countries = {
		AAA = { own_control_core = { a2 } capital = a2 }
		BBB = { own_control_core = { a3 } capital = a3 }
		TTT = { type = pop add_pops_from_locations = { a4 } }
		OLD = { own_control_core = { old } capital = old }
	}
}
"""


def _location(key: str, region: str) -> Location:
    return Location(
        key=key,
        continent="america",
        subcontinent="sub",
        region=region,
        area=f"{key}_area",
        province=f"{key}_province",
    )


def _calibration() -> DevelopmentCalibration:
    american = {
        "a1": _location("a1", "mesoamerica_region"),
        "a2": _location("a2", "mesoamerica_region"),
        "a3": _location("a3", "other_region"),
        "a4": _location("a4", "other_region"),
    }
    return calibrate(
        rules_text=RULES,
        templates_text=TEMPLATE_TEXT,
        buildings_text=BUILDINGS,
        countries_text=COUNTRIES,
        american=american,
    )


def test_decimals_keep_sign_and_refuse_extra_places() -> None:
    """Hundredths round-trip, including vanilla's negative harbour values."""
    assert to_milli("-0.25") == -250
    assert to_milli("12") == 12_000
    assert to_hundredths("0.05") == 5
    assert to_hundredths("-0.10") == -10
    assert [hundredths_text(v) for v in (-10, 0, 5, 100, 75)] == [
        "-0.10",
        "0.00",
        "0.05",
        "1.00",
        "0.75",
    ]
    with pytest.raises(DevelopmentError):
        _ = to_hundredths("0.125")
    with pytest.raises(DevelopmentError):
        _ = to_milli("x")


def test_template_harbours_include_negatives_and_nested_blocks() -> None:
    """Templates with a currents block are still read; negative values are kept."""
    assert template_harbours(TEMPLATE_TEXT) == {"a1": 25, "a2": -10, "a4": 0, "old": 75}
    body = "{ topography = flatland natural_harbor_suitability = -0.10 }"
    assert HARBOR.sub("", body) == "{ topography = flatland }"


def test_calibration_reads_the_vanilla_american_setup() -> None:
    """Maximum keyed sum, harbour values, village share and class means come from the text."""
    calibration = _calibration()
    assert calibration.society_max == 12
    assert calibration.harbours == (-10, 0, 25)
    assert calibration.village_permille == 500
    means = dict(calibration.vanilla_means)
    # a1: -2 + 5 * 0.25 + city 5 + forest -2 + flatland 1 + keyed 12
    assert means["city"] == (1, 15_250)
    # a2: -2 - 0.5 - 2 + 1 + 12 = 8.5; a3: -3 clamps to 0
    assert means["capital"] == (2, 4_250)
    assert means["tribe"] == (1, 0)
    assert means["town"] == (0, 0)


def test_calibration_fails_without_american_land() -> None:
    """Missing data stops the build instead of falling back."""
    with pytest.raises(DevelopmentError):
        _ = calibrate(
            rules_text=RULES,
            templates_text=TEMPLATE_TEXT,
            buildings_text=BUILDINGS,
            countries_text=COUNTRIES,
            american={},
        )


def test_society_terms_follow_complexity() -> None:
    """Zero gives no entry, the saturation level and more the maximum, halves round up."""
    complexity = {"a": 0, "b": 1000, "c": 400, "d": 30, "e": 35, "f": 600, "g": 800}
    terms = society_terms(complexity, ["g", "f", "e", "d", "c", "b", "a"], 12, 800)
    assert terms == {"g": 12, "f": 9, "e": 1, "c": 6, "b": 12}
    assert list(terms) == ["g", "f", "e", "c", "b"]
    values = [
        society_terms({"x": level}, ["x"], 12, 800).get("x", 0) for level in range(0, 1001, 50)
    ]
    assert values == sorted(values)
    assert society_terms({"x": 500}, ["x"], 12, 1000) == {"x": 6}
    assert society_terms({"x": 500}, ["x"], 12, 500) == {"x": 12}


def _site(kind: str) -> Site:
    return Site(
        kind=kind, harbour=0, rank="", vegetation="forest", climate="", topography="", keyed=0
    )


def _flat_calibration(base: int) -> DevelopmentCalibration:
    return DevelopmentCalibration(
        society_max=12,
        harbours=(0,),
        village_permille=500,
        rules={"base": base, "forest": 0},
        vanilla_means={
            "capital": (1, 4000),
            "member": (1, 4000),
            "city": (0, 0),
            "town": (0, 0),
            "tribe": (0, 0),
            "unorganised": (0, 0),
        },
    )


def test_fit_full_lowers_the_term_where_land_already_develops() -> None:
    """The saturation brings state land to the vanilla mean on poor and rich land alike."""
    sites = [_site("capital"), _site("member"), _site("member"), _site("tribe")]
    levels = [500, 500, 500, 500]
    terms: list[int] = []
    for base in (-1000, 0):
        full = fit_full(_flat_calibration(base), sites, levels)
        assert full in FULL_CANDIDATES
        terms.append(society_term(500, 12, full))
    assert terms == [5, 4]
    assert fit_full(_flat_calibration(0), [_site("tribe")], [900]) == FULL_CANDIDATES[-1]
    assert fit_full(_flat_calibration(0), [], []) == FULL_CANDIDATES[-1]


def test_build_development_plans_terms_harbours_and_villages() -> None:
    """A tiny world gets terms on its state land, one harbour and one village."""
    cells = [
        ("g1", "forest", "tropical", "flatland"),
        ("g2", "forest", "tropical", "flatland"),
        ("g3", "forest", "tropical", "flatland"),
    ]
    development = build_development(
        calibration=_calibration(), natives=_natives(), cells=cells, scores={"g2": 10}
    )
    assert development.harbours == {"g2": 0}
    assert development.villages == (("QQA", "g1"),)
    assert set(development.terms) <= {"g1", "g2"}
    assert development.terms["g1"] >= development.terms.get("g2", 0)
    full = development.stats["society_full_permille"]
    assert isinstance(full, int)
    assert full in FULL_CANDIDATES
    assert development.stats["society_max"] == 12


def test_harbour_values_reproduce_the_vanilla_multiset() -> None:
    """As many ports as vanilla values give back every value; order follows shelter."""
    vanilla = [-10, 0, 0, 0, 25, 50]
    scores = {"p1": 40, "p2": 3, "p3": 3, "p4": 20, "p5": 1, "p6": 30}
    values = harbour_values(scores, vanilla)
    assert sorted(values.values()) == vanilla
    assert values["p5"] == -10
    assert values["p1"] == 50
    assert values["p2"] <= values["p3"]


def test_harbour_values_keep_the_zero_share_for_other_sizes() -> None:
    """Fewer or more ports than vanilla values keep the distribution within one value."""
    vanilla = [0] * 8 + [10, 20]
    for count in (3, 10, 25):
        values = harbour_values({f"p{i:02d}": i for i in range(count)}, vanilla)
        zeros = sum(1 for v in values.values() if v == 0)
        assert abs(zeros - 0.8 * count) <= 1
        ordered = [values[f"p{i:02d}"] for i in range(count)]
        assert ordered == sorted(ordered)


def test_ray_table_is_a_unit_circle() -> None:
    """Forty-eight integer directions of length about 1024, one per 7.5 degrees."""
    assert len(RAY_DIRECTIONS) == 48
    for dx, dy in RAY_DIRECTIONS:
        assert abs(dx * dx + dy * dy - 1024 * 1024) < 2200


def test_shelter_counts_rays_that_meet_land() -> None:
    """Open water scores 0, a straight coast about half, a pond 48; rays wrap the map."""
    water = np.ones((100, 200), dtype=bool)
    dock = np.array([[50, 100]], dtype=np.int64)
    assert shelter(water, dock).tolist() == [0]
    coast = water.copy()
    coast[:50, :] = False
    straight = int(shelter(coast, dock)[0])
    assert straight == 23
    bay = coast.copy()
    bay[50:, :90] = False
    bay[50:, 110:] = False
    assert int(shelter(bay, dock)[0]) > straight
    pond = np.zeros((100, 200), dtype=bool)
    pond[50, 100] = True
    assert shelter(pond, dock).tolist() == [48]
    strip = water.copy()
    strip[:, :10] = False
    edge = np.array([[50, 195]], dtype=np.int64)
    assert shelter(strip, edge).tolist() == [23]


def test_market_villages_take_the_most_complex_capitals() -> None:
    """A vanilla share, most complex first, ties by population then key."""
    states = [("AAA", "k1"), ("BBB", "k2"), ("CCC", "k3"), ("DDD", "k4")]
    complexity = {"k1": 300, "k2": 800, "k3": 800, "k4": 100}
    population = {"k1": 90, "k2": 10, "k3": 50, "k4": 70}
    assert market_villages(states, complexity, population, 500) == (("CCC", "k3"), ("BBB", "k2"))
    assert market_villages(states, complexity, population, 0) == ()
    assert market_villages(states, complexity, population, 250) == (("CCC", "k3"),)


def test_spearman_uses_average_ranks() -> None:
    """Perfect, inverse and tied rank correlations."""
    assert spearman_permille([1, 2, 3, 4], [10, 20, 30, 40]) == 1000
    assert spearman_permille([1, 2, 3, 4], [4, 3, 2, 1]) == -1000
    assert spearman_permille([1, 1, 1, 1], [1, 2, 3, 4]) == 0
    assert 0 < spearman_permille([1, 2, 2, 5], [1, 3, 2, 9]) < 1000


def test_generated_lines_parse_into_their_blocks() -> None:
    """Terms and villages insert into the vanilla blocks and parse back."""
    rules = insert_into_block(RULES, ("development",), development_lines({"loc_1": 7, "loc_2": 1}))
    block = parse(rules).block("development")
    assert block is not None
    assert block.first("loc_1") is not None
    assert block.first("loc_2") is not None
    assert block.first("base") is not None
    text = insert_into_block(
        BUILDINGS, ("building_manager",), building_lines([("QQA", "loc_1"), ("QQB", "loc_2")])
    )
    manager = parse(text).block("building_manager")
    assert manager is not None
    villages = [e.value for e in manager.find("market_village") if not isinstance(e.value, str)]
    assert len(villages) == 3
    assert development_lines({}) == ""
    assert building_lines([]) == ""


def test_drop_block_entries_keeps_every_other_byte() -> None:
    """Only the named keys leave the block; comments and spacing stay."""
    text = "# header\ndevelopment = {\n\tbase = -2 # keep\n\tmesoamerica_region = 12\n\tx = 1\n}\n"
    out = drop_block_entries(text, ("development",), {"mesoamerica_region", "absent"})
    assert out == "# header\ndevelopment = {\n\tbase = -2 # keep\n\tx = 1\n}\n"
    with pytest.raises(KeyError):
        _ = drop_block_entries(text, ("missing",), {"x"})


def _plan() -> Plan:
    def cell(key: str, kind: CellClass) -> PlannedCell:
        return PlannedCell(
            key=key,
            name=key,
            color=1,
            kind=kind,
            province="p",
            area="a",
            region="r",
            subcontinent="s",
            continent="america",
        )

    return Plan(
        cells=[
            cell("g1", CellClass.LAND),
            cell("g2", CellClass.LAND),
            cell("g3", CellClass.LAND),
            cell("sea", CellClass.SEA),
        ]
    )


def _country(tag: str, kind: str, members: tuple[str, ...], capital: str) -> Country:
    return Country(
        tag=tag,
        name="Xatlan",
        kind=kind,
        members=members,
        capital=capital,
        culture="c",
        religion="r",
        include="t",
        areas=("a",),
        color=(1, 2, 3),
        color2=(3, 2, 1),
    )


def _natives() -> NativeWorld:
    return NativeWorld(
        pops={},
        countries=(
            _country("QQA", "state", ("g1", "g2"), "g1"),
            _country("QQB", "tribe", ("g3",), "g3"),
        ),
        ranks={},
        markets=(),
        holy_sites={},
        names={},
        vassals=(),
        complexity={"g1": 900, "g2": 400, "g3": 0},
        population={"g1": 50, "g2": 20, "g3": 5},
        stats={},
    )


NEW_WORLD_KEYS = {"mesoamerica_region", "plains_region", "cahokia"}
DEVELOPMENT_PATH = f"{SETUP_DIR}/{DEVELOPMENT_FILE}".removeprefix("game/")
TEMPLATES_WITH_PORT = (
    TEMPLATE_TEXT + "g2 = { topography = flatland natural_harbor_suitability = 0.25 }\n"
)


def _outputs(
    terms: dict[str, int],
    templates: str,
    villages: list[tuple[str, str]],
    rules: str | None = None,
) -> dict[str, bytes]:
    base = rules or drop_block_entries(RULES, ("development",), NEW_WORLD_KEYS)
    dev = insert_into_block(base, ("development",), development_lines(terms))
    buildings = insert_into_block(BUILDINGS, ("building_manager",), building_lines(villages))
    return {
        DEVELOPMENT_PATH: dev.encode(),
        f"{SETUP_DIR}/{BUILDINGS_FILE}".removeprefix("game/"): buildings.encode(),
        TEMPLATES.removeprefix("game/"): templates.encode(),
    }


def _development(terms: dict[str, int] | None = None) -> Development:
    return Development(
        terms=terms or {"g1": 11, "g2": 5},
        harbours={"g2": 25},
        villages=(("QQA", "g1"),),
        stats={},
    )


def _verify(outputs: dict[str, bytes], development: Development) -> dict[str, object]:
    return verify_development(
        outputs, _plan(), _natives(), development, _calibration(), NEW_WORLD_KEYS
    )


def test_verification_accepts_the_planned_output() -> None:
    """Terms, the one harbour and the one village are found as planned."""
    outputs = _outputs({"g1": 11, "g2": 5}, TEMPLATES_WITH_PORT, [("QQA", "g1")])
    assert _verify(outputs, _development()) == {
        "development_entries": 2,
        "harbour_values": 1,
        "market_villages": 1,
    }


@pytest.mark.parametrize("case", ["kept", "duplicate", "sea", "high", "harbour", "village"])
def test_verification_rejects_broken_output(case: str) -> None:
    """Each broken record raises instead of being repaired."""
    terms = {"g1": 11, "g2": 5}
    templates = TEMPLATES_WITH_PORT
    villages = [("QQA", "g1")]
    development = _development()
    rules = None
    if case == "kept":
        rules = RULES
    if case == "sea":
        terms = {**terms, "sea": 2}
    if case == "high":
        terms = {"g1": 13, "g2": 5}
        development = _development(terms)
    if case == "harbour":
        templates += "g3 = { natural_harbor_suitability = 0.50 }\n"
    if case == "village":
        villages = [("QQA", "g2")]
    outputs = _outputs(terms, templates, villages, rules)
    if case == "duplicate":
        outputs[DEVELOPMENT_PATH] = outputs[DEVELOPMENT_PATH].replace(
            b"\tg1 = 11\n", b"\tg1 = 11\n\tg1 = 3\n"
        )
    with pytest.raises(NewWorldExportError):
        _ = _verify(outputs, development)
