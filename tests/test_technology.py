"""Technology levels and regional families of the native states (synthetic fixtures)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.eu5_empires import OPINION_TYPES, EmpireCalibration
from rnw.eu5_natives import (
    Country,
    Culture,
    NativesError,
    NativeWorld,
    VanillaNatives,
    _Cells,  # pyright: ignore[reportPrivateUsage]
    _include,  # pyright: ignore[reportPrivateUsage]
    _state_levels,  # pyright: ignore[reportPrivateUsage]
    _technology,  # pyright: ignore[reportPrivateUsage]
    country_records,
    homeland,
)
from rnw.eu5_nw_export import COUNTRIES_FILE, SETUP_DIR, NewWorldExportError, verify_technology
from rnw.eu5_technology import (
    FAMILIES,
    FAMILY_WEIGHT,
    MESOAMERICA,
    NORTH_AMERICA,
    SOUTH_AMERICA,
    Families,
    TechnologyError,
    agreement_permille,
    families,
    family_shares,
    histogram,
    homeland_distance,
    majority,
    plain,
    quantile_levels,
    state_levels,
    technology_report,
    template_for_level,
    vanilla_state_levels,
    without_families,
)
from rnw.pdx import Block, parse
from rnw.societies import STATE, TRIBE, Polity, Societies

TRIGGERS = """is_capital_mesoamerica = {
\tcapital ?= {
\t\tOR = {
\t\t\tregion = region:meso_region
\t\t\tAND = {
\t\t\t\tarea = area:odd_area
\t\t\t}
\t\t}
\t}
}
is_capital_in_south_america_or_carribean = {
\tcapital ?= {
\t\tOR = {
\t\t\tregion = region:south_region
\t\t\tregion = region:island_region
\t\t}
\t}
}
"""
REGIONS = {"meso_region", "south_region", "island_region", "north_region", "odd_region"}
AREAS = {"odd_area", "plain_area"}


def test_families_read_both_triggers_to_any_depth() -> None:
    """A listed region or area decides; an area of an unlisted region is still Mesoamerican."""
    found = families(TRIGGERS, REGIONS, AREAS)
    assert found.of("meso_region", "plain_area") == MESOAMERICA
    assert found.of("odd_region", "odd_area") == MESOAMERICA
    assert found.of("south_region", "plain_area") == SOUTH_AMERICA
    assert found.of("island_region", "plain_area") == SOUTH_AMERICA
    assert found.of("north_region", "plain_area") == NORTH_AMERICA
    assert found.of("north_region", "no_such_area") == NORTH_AMERICA


@pytest.mark.parametrize("case", ["missing", "empty", "unknown_region", "unknown_area"])
def test_families_fail_loudly(case: str) -> None:
    """A missing trigger, an empty one and a key outside the Americas each stop the build."""
    text = TRIGGERS
    if case == "missing":
        text = TRIGGERS.split("is_capital_in_south", maxsplit=1)[0]
    if case == "empty":
        text = TRIGGERS.replace("region = region:south_region", "").replace(
            "region = region:island_region", ""
        )
    if case == "unknown_region":
        text = TRIGGERS.replace("island_region", "old_world_region")
    if case == "unknown_area":
        text = TRIGGERS.replace("area:odd_area", "area:old_world_area")
    with pytest.raises(TechnologyError):
        _ = families(text, REGIONS, AREAS)


LEVELS = {"plain": 0, "advanced": 2, "nested": 2}
SETUP = """countries = {
\tcountries = {
\t\tAAA = { own_control_core = { a1 a2 } include = "plain" starting_technology_level = 1 }
\t\tBBB = { own_control_core = { b1 } include = "advanced" }
\t\tCCC = { own_control_core = { c1 } include = "plain" include = "nested" }
\t\tDDD = { own_control_core = { d1 } include = "silent" }
\t\tEEE = { own_control_core = { old1 } include = "advanced" }
\t\tFFF = { own_control_core = { a1 old1 } include = "advanced" }
\t\tGGG = { type = pop add_pops_from_locations = { a1 } include = "advanced" }
\t}
}
"""
AMERICAN = {"a1", "a2", "b1", "c1", "d1"}


def test_calibration_takes_own_levels_then_includes_and_skips_the_rest() -> None:
    """An own level beats its template, includes give their highest, and only landed
    American countries with a level count."""
    assert vanilla_state_levels(SETUP, LEVELS, AMERICAN) == (1, 2, 2)


def test_calibration_fails_without_any_level() -> None:
    """No American landed country with a level stops the build."""
    with pytest.raises(TechnologyError):
        _ = vanilla_state_levels(SETUP, LEVELS, {"d1"})


def test_quantiles_reproduce_the_vanilla_multiset() -> None:
    """As many states as vanilla levels give exactly the vanilla levels, in rising order."""
    vanilla = [0, 0, 1, 1, 1, 2]
    assert quantile_levels(len(vanilla), vanilla) == vanilla
    assert quantile_levels(0, vanilla) == []
    assert quantile_levels(0, []) == []
    with pytest.raises(TechnologyError):
        _ = quantile_levels(3, [])


@pytest.mark.parametrize("count", [1, 2, 3, 7, 40, 131])
def test_quantile_levels_rise_and_keep_the_shares(count: int) -> None:
    """Levels never fall and each level keeps about its vanilla share on any world size."""
    vanilla = [0] * 11 + [1] * 17 + [2] * 191
    levels = quantile_levels(count, vanilla)
    assert levels == sorted(levels)
    assert set(levels) <= {0, 1, 2}
    if count >= len(vanilla) // 10:
        for level, share in ((0, 11), (1, 17), (2, 191)):
            assert abs(levels.count(level) * len(vanilla) - share * count) <= len(vanilla)


def test_states_rise_by_complexity_then_population_then_tag() -> None:
    """Ties break by population and then by tag, and the result keeps the order given."""
    order = [(5, 10, "B"), (5, 10, "A"), (1, 99, "Z"), (5, 3, "C")]
    assert state_levels(order, [0, 1, 2, 2]) == [2, 2, 0, 1]


TEMPLATE_LEVELS = {"own": 1, "tribal": 0, "high": 2, "adv": 2, "adv_no_coast": 2, "def": 0}


@pytest.mark.parametrize(
    ("own", "level", "expected"),
    [
        ("own", 1, "own"),
        ("own", 2, "own"),
        ("own", 3, "adv"),
        ("own", 0, "def"),
        ("tribal", 1, "tribal"),
        ("tribal", 2, "adv"),
        ("high", 1, "def"),
        ("", 2, "adv"),
        ("", 1, "def"),
    ],
)
def test_a_template_stays_within_one_level_of_its_state(
    own: str, level: int, expected: str
) -> None:
    """The own template serves its level and the one above; else advanced or default by level."""
    found = template_for_level(own, level, TEMPLATE_LEVELS, advanced="adv", default="def")
    assert found == expected


def _vanilla(**changes: object) -> VanillaNatives:
    culture = {
        "tribal": Culture("f", (), 1, "tribal", "tribe_t", "", ""),
        "advanced": Culture("f", (), 1, "adv", "", "", ""),
        "none": Culture("f", (), 1, "", "", "", ""),
    }
    base = VanillaNatives(
        density={},
        population_per_location=0,
        cultures=culture,
        religions={},
        templates=frozenset({"tribal", "tribe_t", "adv", "adv_no_coast", "amerindian_monarchy"}),
        reserved_tags=frozenset(),
        holy_sites=(),
        levels={"tribal": 0, "adv": 2, "adv_no_coast": 2, "amerindian_monarchy": 0},
        overlord_level=2,
        state_levels=(0, 1, 2, 2),
    )
    return replace(base, **changes)


def test_the_template_follows_the_level_in_both_directions() -> None:
    """A level-2 state of a tribal culture takes the advanced template, a level-1 state of an
    advanced culture the default one, and coast variants still apply."""
    vanilla = replace(_vanilla(), levels={**_vanilla().levels, "amerindian_monarchy": 0})
    advanced = "amerindian_advanced_monarchy_not_nahuatl"
    vanilla = replace(
        vanilla,
        templates=vanilla.templates | {advanced},
        levels={**vanilla.levels, advanced: 2},
    )
    assert _include(vanilla, "tribal", level=2, coastal=True) == advanced
    assert _include(vanilla, "tribal", level=1, coastal=True) == "tribal"
    assert _include(vanilla, "advanced", level=1, coastal=True) == "amerindian_monarchy"
    assert _include(vanilla, "advanced", level=2, coastal=True) == "adv"
    assert _include(vanilla, "advanced", level=2, coastal=False) == "adv_no_coast"
    assert _include(vanilla, "none", level=0, coastal=True) == "amerindian_monarchy"
    assert _include(vanilla, "none", level=2, coastal=True) == advanced
    assert _include(vanilla, "tribal", level=None, coastal=True) == "tribe_t"
    assert _include(vanilla, "none", level=None, coastal=True) == "amerindian_tribe"


def _country(tag: str, kind: str = STATE, **changes: object) -> Country:
    base = Country(
        tag=tag,
        name="Xatlan",
        kind=kind,
        members=(f"loc_{tag}",),
        capital=f"loc_{tag}",
        culture="c",
        religion="r",
        include="t0",
        areas=("area_one",),
        color=(1, 2, 3),
        color2=(3, 2, 1),
    )
    return replace(base, **changes)


def test_country_records_write_the_level_after_the_includes() -> None:
    """A state writes its level right after its include; a tribe writes none."""
    state = _country("QQA", level=2, include="adv")
    tribe = _country("QQB", TRIBE)
    text = "countries = {\n\tcountries = {\n" + country_records((state, tribe)) + "\t}\n}\n"
    record = parse(text).block("countries", "countries", "QQA")
    assert record is not None
    keys = [entry.key for entry in record.entries]
    assert keys.index("starting_technology_level") == keys.index("include") + 1
    level = record.first("starting_technology_level")
    assert level is not None
    assert level.value == "2"
    other = parse(text).block("countries", "countries", "QQB")
    assert other is not None
    assert other.first("starting_technology_level") is None
    assert isinstance(other.first("include"), object)


def test_family_helpers() -> None:
    """Shares are permille times the weight, the plain vector drops them, the majority wins."""
    members = [MESOAMERICA, NORTH_AMERICA, NORTH_AMERICA, NORTH_AMERICA]
    shares = family_shares(members, [1, 1, 1, 1])
    assert shares == [FAMILY_WEIGHT * 250, 0, FAMILY_WEIGHT * 750]
    vector = (1, 2, 3, *shares)
    assert plain(vector) == (1, 2, 3)
    assert without_families(vector) == (1, 2, 3, 0, 0, 0)
    assert majority(members, [5, 1, 1, 1]) == MESOAMERICA
    assert majority(members, [1, 1, 1, 1]) == NORTH_AMERICA
    assert majority([], []) == ""
    assert len(shares) == len(FAMILIES)


def test_the_distance_leaves_the_family_entries_out() -> None:
    """The mean L1 distance is weighted by the zones' population and ignores the families."""
    zones = [((10, 20, 1, 2, 3), 100), ((0, 0, 9, 9, 9), 300)]
    homelands = {"a": (12, 20, 9, 9, 9), "b": (3, 3, 0, 0, 0)}
    assert homeland_distance(zones, ["a", "b"], homelands) == (100 * 2 + 300 * 6) // 400
    assert homeland_distance([], [], homelands) == 0


def test_report_helpers() -> None:
    """Histograms are sorted with ``none`` for no level; the report names its numbers."""
    assert histogram([2, 0, 2, None]) == {"0": 1, "2": 2, "none": 1}
    assert agreement_permille(1, 3) == 333
    assert agreement_permille(0, 0) == 0
    report = technology_report(
        states=[("QQB", 2), ("QQA", 0)],
        vanilla=(0, 2, 2),
        tribes=[None, 0],
        replaced=1,
        agreement={"states": 500},
        distance={"with_families": 3},
        vassals=2,
    )
    assert report["state_levels"] == {"0": 1, "2": 1}
    assert report["tags_at_level"] == {"0": ["QQA"], "2": ["QQB"]}
    assert report["tribe_template_levels"] == {"0": 1, "none": 1}
    assert report["vassals"] == 2


def _societies(polities: tuple[Polity, ...], complexity: list[int]) -> Societies:
    count = len(complexity)
    return Societies(
        complexity=np.array(complexity, dtype=np.int64),
        population=np.array([1000 + 10 * node for node in range(count)], dtype=np.int64),
        peasants=np.zeros(count, dtype=np.int64),
        religion=np.zeros(count, dtype=np.int64),
        culture=np.zeros(count, dtype=np.int64),
        hearths=(),
        polities=polities,
        ranks={},
        markets=(),
    )


def test_states_take_levels_by_complexity_and_an_empire_the_highest() -> None:
    """Ordinary states take the vanilla quantiles; empires the top level; tribes none."""
    polities = (
        Polity(STATE, (0,), 0, 0),
        Polity(STATE, (1,), 1, 0),
        Polity(STATE, (2,), 2, 0),
        Polity(STATE, (3,), 3, 0, great=True),
        Polity(TRIBE, (4,), 4, 0),
    )
    societies = _societies(polities, [300, 100, 700, 900, 50])
    tags = ["TAA", "TBB", "TCC", "TDD", "TEE"]
    empire = EmpireCalibration(
        level=3, rank="rank_duchy", road_permille=1000, opinions=OPINION_TYPES
    )
    assert _state_levels(societies, tags, _vanilla(empire=empire)) == {0: 2, 1: 0, 2: 2, 3: 3}
    with pytest.raises(NativesError, match="No empire calibration"):
        _ = _state_levels(societies, tags, _vanilla())
    with pytest.raises(NativesError, match="No vanilla state levels"):
        _ = _state_levels(societies, tags, _vanilla(state_levels=(), empire=empire))


def test_the_report_counts_agreement_replaced_templates_and_distances() -> None:
    """Families agree where the culture's vanilla family is the family of the land."""
    open_land = homeland([""], [""], [""], [0], [False], [False], [1], [NORTH_AMERICA])
    state_land = homeland([""], [""], [""], [0], [False], [True], [1], [NORTH_AMERICA])
    cultures = {
        "north": Culture("f", open_land, 1, "own", "", "", "", family=NORTH_AMERICA),
        "south": Culture("f", state_land, 1, "", "", "", "", family=SOUTH_AMERICA),
    }
    vanilla = replace(_vanilla(), cultures=cultures, levels={"own": 0, "adv": 2})
    polities = (Polity(STATE, (0,), 0, 0), Polity(STATE, (1,), 1, 1), Polity(TRIBE, (2,), 2, 1))
    societies = replace(
        _societies(polities, [100, 800, 0]),
        population=np.array([100, 300, 600], dtype=np.int64),
        culture=np.array([0, 1, 1], dtype=np.int64),
    )
    cells = _Cells(
        cells=[0, 1, 2],
        climate=["", "", ""],
        vegetation=["", "", ""],
        topography=["", "", ""],
        latitude=[0, 0, 0],
        coastal=[False] * 3,
        seas=[[], [], []],
        family=[NORTH_AMERICA, NORTH_AMERICA, SOUTH_AMERICA],
    )
    countries = (
        _country("QQA", culture="north", capital="a", include="adv", level=2),
        _country("QQB", culture="south", capital="b", include="adv", level=2),
        _country("QQC", TRIBE, culture="south", capital="c", include="tribal"),
    )
    report = _technology(
        societies,
        cells,
        vanilla,
        countries,
        keys=["a", "b", "c"],
        state=np.array([True, True, False]),
        cultures=["north", "south"],
        plain_cultures=["south", "south"],
        vassals=0,
    )
    assert report["family_agreement_permille"] == {"states": 500, "tribes": 1000, "population": 700}
    assert report["templates_replaced"] == 1
    assert report["state_levels"] == {"2": 2}
    assert report["tribe_template_levels"] == {"none": 1}
    # zone 0 (100 people) is state land, zone 1 (900) a third state land: only the state share
    # differs from the cultures' homelands, so the distances are 2000 and 2 * 333 against 2000
    assert report["homeland_distance"] == {"with_families": 1400, "without_families": 1200}


OVERLORD = 2
PATH = f"{SETUP_DIR}/{COUNTRIES_FILE}".removeprefix("game/")


def _world(
    countries: tuple[Country, ...], vassals: tuple[tuple[str, str], ...] = ()
) -> NativeWorld:
    return NativeWorld(
        pops={},
        countries=countries,
        ranks={},
        markets=(),
        holy_sites={},
        names={},
        vassals=vassals,
        complexity={f"loc_{c.tag}": 100 * number for number, c in enumerate(countries)},
        population={f"loc_{c.tag}": 50 for c in countries},
        stats={},
    )


def _verified(countries: tuple[Country, ...], vassals: tuple[tuple[str, str], ...] = ()) -> object:
    text = "countries = {\n\tcountries = {\n" + country_records(countries) + "\t}\n}\n"
    vanilla = _vanilla(levels={"t0": 0, "t1": 1, "t2": 2, "tt": 0}, overlord_level=OVERLORD)
    return verify_technology({PATH: text.encode()}, _world(countries, vassals), vanilla)


def _good() -> tuple[Country, ...]:
    return (
        _country("QQA", level=0, include="t0"),
        _country("QQB", level=2, include="t2"),
        _country("QQC", level=2, include="t1"),
        _country("QQT", TRIBE, include="tt"),
    )


def test_verification_accepts_levels_that_fit() -> None:
    """Levels rise with complexity, templates fit, the lord can lead."""
    assert _verified(_good(), (("QQB", "QQC"),)) == {
        "technology_levels_written": 3,
        "technology_vassal_lords": 1,
    }


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "outside",
        "tribe",
        "template_above",
        "template_below",
        "falling",
        "weak_lord_level",
        "weak_lord_template",
    ],
)
def test_verification_rejects_each_broken_record(case: str) -> None:
    """A missing level, a level outside the vanilla set, a level on a tribe, a template above
    or two below the level, a fall along the complexity and a weak lord all raise."""
    first, second, third, tribe = _good()
    vassals = (("QQB", "QQC"),)
    if case == "missing":
        second = replace(second, level=None)
    if case == "outside":
        second = replace(second, level=3)
    if case == "tribe":
        tribe = replace(tribe, level=1)
    if case == "template_above":
        first = replace(first, include="t1")
    if case == "template_below":
        second = replace(second, include="t0")
    if case == "falling":
        first = replace(first, level=2, include="t2")
        second = replace(second, level=1, include="t1")
        third = replace(third, level=1, include="t1")
    if case == "weak_lord_level":
        second = replace(second, level=1, include="t1")
        third = replace(third, level=1, include="t1")
    if case == "weak_lord_template":
        second = replace(second, include="t1")
    with pytest.raises(NewWorldExportError):
        _ = _verified((first, second, third, tribe), vassals)


def test_an_empire_is_left_out_of_the_ordering() -> None:
    """A great empire may be less complex than a state of a lower level."""
    first, second, third, tribe = _good()
    empire = replace(first, great=True, level=2, include="t2")
    assert _verified((empire, replace(second, level=1, include="t1"), third, tribe))


def test_an_empire_may_write_the_calibrated_level_above_the_vanilla_ones() -> None:
    """Level 3 is no vanilla American state level but the empire's, one above its template."""
    first, second, third, tribe = _good()
    empire = replace(first, great=True, level=3, include="t2")
    calibrated = EmpireCalibration(
        level=3, rank="rank_duchy", road_permille=1000, opinions=OPINION_TYPES
    )
    text = "countries = {\n\tcountries = {\n" + country_records((empire, second, third, tribe))
    text += "\t}\n}\n"
    countries = (empire, second, third, tribe)
    vanilla = _vanilla(
        levels={"t0": 0, "t1": 1, "t2": 2, "tt": 0}, overlord_level=OVERLORD, empire=calibrated
    )
    assert verify_technology({PATH: text.encode()}, _world(countries), vanilla)
    with pytest.raises(NewWorldExportError):
        _ = verify_technology(
            {PATH: text.encode()}, _world(countries), replace(vanilla, empire=None)
        )
    ordinary = replace(second, level=3, include="t2")
    broken = "countries = {\n\tcountries = {\n" + country_records((first, ordinary, third, tribe))
    with pytest.raises(NewWorldExportError):
        _ = verify_technology(
            {PATH: (broken + "\t}\n}\n").encode()},
            _world((first, ordinary, third, tribe)),
            vanilla,
        )


def test_parsed_blocks_stay_blocks() -> None:
    """The fixture text parses into country blocks."""
    text = "countries = {\n\tcountries = {\n" + country_records(_good()) + "\t}\n}\n"
    holder = parse(text).block("countries", "countries")
    assert holder is not None
    assert all(isinstance(entry.value, Block) for entry in holder.entries)


def test_families_dataclass_is_frozen() -> None:
    """The families cannot change after they are read."""
    found = Families({"a": MESOAMERICA}, {})
    with pytest.raises(AttributeError):
        found.by_region = {}  # pyright: ignore[reportAttributeAccessIssue]
