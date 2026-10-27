"""The game's records for sea leagues, confederations, fractured realms and sacred centres."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pytest

from rnw.archetypes import (
    FRACTURED_REALM,
    HIGHLAND_CONFEDERATION,
    SACRED_CENTRE,
    SEA_LEAGUE,
)
from rnw.eu5_archetypes import (
    ArchetypeCalibration,
    ArchetypeError,
    Bonds,
    Expected,
    alliance_lines,
    american_includes,
    archetype_calibration,
    archetype_problems,
    archetype_report,
    confederation_calibration,
    confederation_lines,
    currency_lines,
    government_fields,
    merge_knowledge,
    named_organizations,
    partner_knowledge,
    republic_template,
    rival_lines,
    slider_targets,
    theocracy_government,
    written_confederations,
    written_countries,
    written_pairs,
)
from rnw.eu5_natives import Country, country_records, discover_areas
from rnw.eu5_rewrite import insert_into_block
from rnw.pdx import parse

if TYPE_CHECKING:
    from collections.abc import Callable

AMERICAN = {"a1", "a2", "a3", "a4", "a5", "a6"}
SETUP = """countries = {
\tcountries = {
\t\tTLX = { own_control_core = { a1 } include = "republic_t" include = "expl_x"
\t\t\tgovernment = { type = republic heir_selection = oligarchic_elective ruler = tlx } }
\t\tMON = { own_control_core = { a2 } include = "monarchy_t"
\t\t\tgovernment = { type = monarchy heir_selection = cognatic ruler = random } }
\t\tKKA = { own_control_core = { a3 } include = "tribe_t" starting_technology_level = 0
\t\t\tcurrency_data = { gold = 100 stability = 33 tribal_cohesion = 90 } }
\t\tONO = { own_control_core = { a4 } include = "tribe_t" starting_technology_level = 0
\t\t\tcurrency_data = { gold = 100 stability = 33 tribal_cohesion = 90 } }
\t\tPOP = { type = pop add_pops_from_locations = { a5 } include = "pop_t" }
\t\tTIB = { own_control_core = { old1 } government = { type = theocracy
\t\t\their_selection = theocratic_elective } }
\t\tVNA = { own_control_core = { old2 } government = { type = theocracy
\t\t\their_selection = theocratic_elective } }
\t\tOLD = { own_control_core = { old3 } government = { type = theocracy } }
\t}
}
"""
TEMPLATES = {
    "republic_t": "government = { type = republic land_vs_naval = -70 }",
    "monarchy_t": "government = { land_vs_naval = -90 spiritualist_vs_humanist = -60 }",
    "tribe_t": (
        "government = { land_vs_naval = 60 spiritualist_vs_humanist = -90"
        " traditionalist_vs_innovative = -70 }"
    ),
    "pop_t": "government = { traditionalist_vs_innovative = -90 }",
    "old_t": "government = { land_vs_naval = 100 }",
}
GOVERNMENTS = {
    "republic_t": (("type", "republic"), ("heir_selection", "oligarchic_elective")),
    "monarchy_t": (("type", "monarchy"),),
}
LEVELS = {"republic_t": 2, "monarchy_t": 1}
GOVERNMENT_TYPES = ["theocracy = { heir_selection = theocratic_elective heir_selection = other }"]
VALUES = [
    "land_vs_naval = { }\nspiritualist_vs_humanist = { }\ntraditionalist_vs_innovative = { }\n"
]
IO_TYPES = ["tribal_confederation = { }\nother = { }\n"]
ORGANIZATIONS = """international_organization_manager = {
\tadd_international_organization = {
\t\ttype = tribal_confederation
\t\tcreation_date = 1142.1.1
\t\tmembers = { KKA ONO }
\t}
\tadd_international_organization = {
\t\ttype = tribal_confederation
\t\tcreation_date = 1337.1.1
\t\tmembers = { AFR SDQ }
\t}
}
"""
DIPLOMACY = (
    "diplomacy_manager = {\n"
    "\tscripted_mutual = { first = THO second = CWM type = alliance }\n"
    "\tscripted_mutual = { first = GON second = CWM type = alliance }\n"
    "\tdependency = { first = ENG second = WLS subject_type = vassal }\n"
    "}\n"
)
RIVALS = (
    "diplomacy_manager = {\n"
    "\trival = { first = FRA second = ENG }\n"
    "\trival = { first = GON second = FRA }\n"
    "}\n"
)


POPS = {"a3": [("tribesmen", 2000, "c", "r")], "a4": [("tribesmen", 1000, "c", "r")]}


def _calibration(**changes: object) -> ArchetypeCalibration:
    found = archetype_calibration(
        setup_text=SETUP,
        diplomacy_text=DIPLOMACY,
        rivals_text=RIVALS,
        io_text=ORGANIZATIONS,
        american=AMERICAN,
        governments=GOVERNMENTS,
        levels=LEVELS,
        templates=TEMPLATES,
        government_texts=GOVERNMENT_TYPES,
        value_texts=VALUES,
        io_type_texts=IO_TYPES,
        pops=POPS,
        year="1337",
    )
    return replace(found, **changes)


def test_the_calibration_reads_the_republic_the_theocracy_and_the_confederates() -> None:
    found = _calibration()
    assert found.republic_include == "republic_t"
    assert found.republic_government == GOVERNMENTS["republic_t"]
    assert found.republic_level == 2
    assert found.theocracy == (("type", "theocracy"), ("heir_selection", "theocratic_elective"))
    assert found.confederation_date == "1337.1.1"
    assert found.cohesion == (("gold", 100), ("stability", 33), ("tribal_cohesion", 90))
    assert (found.alliances, found.rivals, found.confederations) == (2, 2, 1)
    assert found.confederate_density == 1500


def test_the_positions_are_the_american_extremes_in_the_direction_of_each_kind() -> None:
    found = _calibration()
    assert dict(found.sliders[SEA_LEAGUE]) == {"land_vs_naval": 60}
    assert dict(found.sliders[SACRED_CENTRE]) == {
        "spiritualist_vs_humanist": -90,
        "traditionalist_vs_innovative": -90,
    }


def test_templates_of_american_countries_landed_or_pop_are_the_ones_that_count() -> None:
    assert american_includes(SETUP, AMERICAN) == {"republic_t", "monarchy_t", "tribe_t", "pop_t"}
    assert american_includes(SETUP, {"a1"}) == {"republic_t"}


def test_an_axis_the_game_lacks_or_no_template_sets_fails() -> None:
    used = ["republic_t", "monarchy_t", "tribe_t", "pop_t"]
    with pytest.raises(ArchetypeError, match="land_vs_naval is not defined"):
        _ = slider_targets(TEMPLATES, used, ["spiritualist_vs_humanist = { }"])
    with pytest.raises(ArchetypeError, match="sets land_vs_naval"):
        _ = slider_targets({}, used, VALUES)
    with pytest.raises(ArchetypeError, match="out of range"):
        _ = slider_targets({"x": "government = { land_vs_naval = 160 }"}, ["x"], VALUES)


def test_a_republic_needs_one_template_that_gives_the_government() -> None:
    assert republic_template(SETUP, AMERICAN, GOVERNMENTS, LEVELS) == (
        "republic_t",
        GOVERNMENTS["republic_t"],
        2,
    )
    with pytest.raises(ArchetypeError, match="0 templates"):
        _ = republic_template(SETUP, {"a2"}, GOVERNMENTS, LEVELS)
    with pytest.raises(ArchetypeError, match="gives no republic government"):
        _ = republic_template(SETUP, AMERICAN, {"republic_t": ()}, LEVELS)
    two = SETUP.replace(
        'include = "monarchy_t"\n\t\t\tgovernment = { type = monarchy',
        'include = "tribe_t"\n\t\t\tgovernment = { type = republic',
    )
    with pytest.raises(ArchetypeError, match="2 templates"):
        _ = republic_template(two, AMERICAN, GOVERNMENTS, LEVELS)


def test_a_theocracy_takes_the_heir_selection_vanilla_writes_if_the_type_allows_it() -> None:
    assert theocracy_government(SETUP, GOVERNMENT_TYPES) == (
        ("type", "theocracy"),
        ("heir_selection", "theocratic_elective"),
    )
    with pytest.raises(ArchetypeError, match="does not allow"):
        _ = theocracy_government(SETUP, ["theocracy = { heir_selection = other }"])
    with pytest.raises(ArchetypeError, match="writes a heir selection"):
        _ = theocracy_government("countries = { countries = { } }", GOVERNMENT_TYPES)


def test_a_confederation_needs_a_defined_type_american_members_and_cohesion() -> None:
    found = confederation_calibration(ORGANIZATIONS, SETUP, AMERICAN, IO_TYPES, POPS)
    assert found == ((("gold", 100), ("stability", 33), ("tribal_cohesion", 90)), 1, 1500)
    with pytest.raises(ArchetypeError, match="is defined"):
        _ = confederation_calibration(ORGANIZATIONS, SETUP, AMERICAN, ["other = { }"], POPS)
    with pytest.raises(ArchetypeError, match="No American"):
        _ = confederation_calibration(ORGANIZATIONS, SETUP, {"a2"}, IO_TYPES, POPS)
    plain = SETUP.replace("tribal_cohesion = 90", "x = 1")
    with pytest.raises(ArchetypeError, match="tribal_cohesion"):
        _ = confederation_calibration(ORGANIZATIONS, plain, AMERICAN, IO_TYPES, POPS)


def test_vanilla_without_an_alliance_or_a_rival_fails_the_calibration() -> None:
    kwargs: dict[str, object] = {
        "setup_text": SETUP,
        "diplomacy_text": "diplomacy_manager = { }",
        "rivals_text": RIVALS,
        "io_text": ORGANIZATIONS,
        "american": AMERICAN,
        "governments": GOVERNMENTS,
        "levels": LEVELS,
        "templates": TEMPLATES,
        "government_texts": GOVERNMENT_TYPES,
        "value_texts": VALUES,
        "io_type_texts": IO_TYPES,
        "pops": POPS,
        "year": "1337",
    }
    with pytest.raises(ArchetypeError, match="no alliance or no rival"):
        _ = archetype_calibration(**kwargs)  # pyright: ignore[reportArgumentType]


def test_government_fields_replace_the_same_keys_and_add_the_positions() -> None:
    base = (("type", "monarchy"), ("heir_selection", "cognatic"))
    assert government_fields(base, (("type", "theocracy"),), (("land_vs_naval", 60),)) == (
        ("heir_selection", "cognatic"),
        ("type", "theocracy"),
        ("land_vs_naval", "60"),
    )
    assert government_fields(base, (), ()) == base


def test_partners_discover_each_others_capital_areas() -> None:
    capitals = {"AAA": "a", "BBB": "b", "CCC": "c"}
    pairs = [("AAA", "BBB"), ("BBB", "AAA"), ("AAA", "CCC")]
    known = partner_knowledge(pairs, capitals)
    assert known == {"AAA": frozenset({"b", "c"}), "BBB": frozenset({"a"})}
    assert merge_knowledge(known, {"BBB": frozenset({"c"}), "CCC": frozenset({"a"})}) == {
        "AAA": frozenset({"b", "c"}),
        "BBB": frozenset({"a", "c"}),
        "CCC": frozenset({"a"}),
    }
    with pytest.raises(KeyError):
        _ = partner_knowledge([("AAA", "NOBODY")], capitals)


def test_generated_lines_parse_into_their_blocks_and_none_is_nothing() -> None:
    assert alliance_lines([]) == rival_lines([]) == confederation_lines("1337.1.1", []) == ""
    diplomacy = insert_into_block(
        DIPLOMACY, ("diplomacy_manager",), alliance_lines([("AAA", "BBB"), ("BBB", "CCC")])
    )
    assert written_pairs(diplomacy, "scripted_mutual", "alliance")[-2:] == [
        ("AAA", "BBB"),
        ("BBB", "CCC"),
    ]
    rivals = insert_into_block(RIVALS, ("diplomacy_manager",), rival_lines([("AAA", "BBB")]))
    assert written_pairs(rivals, "rival")[-1] == ("AAA", "BBB")
    organizations = insert_into_block(
        ORGANIZATIONS,
        ("international_organization_manager",),
        confederation_lines("1337.1.1", [("AAA", "BBB", "CCC")]),
    )
    assert written_confederations(organizations)[-1] == (
        "tribal_confederation",
        "1337.1.1",
        ("AAA", "BBB", "CCC"),
    )
    assert named_organizations(organizations, {"BBB", "AFR"}) == [
        "tribal_confederation",
        "tribal_confederation",
    ]
    assert parse(currency_lines((("gold", 100),)))  # a block of its own


def test_the_report_lists_the_calibration_the_options_and_the_groups() -> None:
    report = archetype_report(_calibration(), {SEA_LEAGUE: 2}, [{"kind": SEA_LEAGUE}])
    assert report["options"] == {SEA_LEAGUE: 2}
    assert report["groups"] == [{"kind": SEA_LEAGUE}]
    calibration = report["calibration"]
    assert isinstance(calibration, dict)
    assert calibration["republic_template"] == "republic_t"
    assert calibration["vanilla_confederations"] == 1


# A world of four groups, checked on the text the records and lines make.
ROSTER: dict[str, tuple[str, str]] = {
    "LGA": (SEA_LEAGUE, "state"),
    "LGB": (SEA_LEAGUE, "state"),
    "LGC": (SEA_LEAGUE, "state"),
    "CNA": (HIGHLAND_CONFEDERATION, "tribe"),
    "CNB": (HIGHLAND_CONFEDERATION, "tribe"),
    "CNC": (HIGHLAND_CONFEDERATION, "tribe"),
    "RLA": (FRACTURED_REALM, "state"),
    "RLB": (FRACTURED_REALM, "state"),
    "RLC": (FRACTURED_REALM, "state"),
    "SCA": (SACRED_CENTRE, "state"),
    "SCB": (SACRED_CENTRE, "state"),
    "SCC": (SACRED_CENTRE, "state"),
    "PLN": ("", "state"),
}


def _country(tag: str, calibration: ArchetypeCalibration) -> Country:
    kind, role = ROSTER[tag]
    base = Country(
        tag=tag,
        name=tag,
        kind=role,
        members=(f"x{tag}",),
        capital=f"x{tag}",
        culture="c",
        religion="r",
        include="monarchy_t" if role == "state" else "tribe_t",
        areas=(f"x{tag}",),
        color=(1, 2, 3),
        color2=(3, 2, 1),
        government=(("type", "monarchy"),) if role == "state" else (("type", "tribe"),),
        level=2 if role == "state" else None,
        archetype=kind,
    )
    if kind == SEA_LEAGUE:
        return replace(
            base,
            include=calibration.republic_include,
            government=government_fields(
                calibration.republic_government, (), calibration.sliders[SEA_LEAGUE]
            ),
        )
    if kind == HIGHLAND_CONFEDERATION:
        return replace(base, landed=True, currency=calibration.cohesion)
    if tag == "SCA":
        return replace(
            base,
            include="",
            government=government_fields(
                base.government, calibration.theocracy, calibration.sliders[SACRED_CENTRE]
            ),
        )
    return base


GROUPS = (
    (SEA_LEAGUE, ("LGA", "LGB", "LGC")),
    (HIGHLAND_CONFEDERATION, ("CNA", "CNB", "CNC")),
    (FRACTURED_REALM, ("RLA", "RLB", "RLC")),
    (SACRED_CENTRE, ("SCA", "SCB", "SCC")),
)
BONDS = Bonds(
    groups=GROUPS,
    alliances=(("LGA", "LGB"), ("LGB", "LGC"), ("LGA", "LGC")),
    rivals=(
        ("RLA", "RLB"),
        ("RLB", "RLA"),
        ("RLA", "RLC"),
        ("RLC", "RLA"),
        ("SCA", "SCB"),
        ("SCB", "SCA"),
        ("SCA", "SCC"),
        ("SCC", "SCA"),
    ),
    confederations=(("CNA", "CNB", "CNC"),),
)


@dataclass(slots=True)
class _World:
    """The plan, the written texts and the vanilla ones, for the checks and for breaking them."""

    calibration: ArchetypeCalibration
    countries: list[Country]
    bonds: Bonds
    texts: dict[str, str]
    originals: dict[str, str]
    free: dict[str, bool]

    def expected(self) -> dict[str, Expected]:
        return {
            c.tag: Expected(
                tag=c.tag,
                state=c.kind == "state",
                landed=c.landed,
                include=c.include,
                government=c.government,
                currency=c.currency,
                members=c.members,
                capital=c.capital,
                archetype=c.archetype,
                free=self.free[c.tag],
            )
            for c in self.countries
        }

    def problems(self) -> list[str]:
        return archetype_problems(
            texts=self.texts,
            originals=self.originals,
            countries=self.expected(),
            bonds=self.bonds,
            calibration=self.calibration,
            capital_areas={c.tag: c.capital for c in self.countries},
            gone={"GON"},
        )


def _written(countries: list[Country], bonds: Bonds, calibration: ArchetypeCalibration) -> _World:
    capitals = {c.tag: c.capital for c in countries}
    aware = discover_areas(countries, partner_knowledge(bonds.knowledge(), capitals))
    originals = {
        "10_countries.txt": "countries = { countries = { } }",
        "12_diplomacy.txt": DIPLOMACY,
        "15_international_organizations.txt": ORGANIZATIONS,
        "20_rivals.txt": RIVALS,
    }
    texts = {
        "10_countries.txt": "countries = {\n\tcountries = {\n"
        + country_records(aware)
        + "\t}\n}\n",
        "12_diplomacy.txt": insert_into_block(
            DIPLOMACY.replace(
                "\tscripted_mutual = { first = GON second = CWM type = alliance }\n", ""
            ),
            ("diplomacy_manager",),
            alliance_lines(bonds.alliances),
        ),
        "15_international_organizations.txt": insert_into_block(
            ORGANIZATIONS,
            ("international_organization_manager",),
            confederation_lines(calibration.confederation_date, bonds.confederations),
        ),
        "20_rivals.txt": insert_into_block(
            RIVALS.replace("\trival = { first = GON second = FRA }\n", ""),
            ("diplomacy_manager",),
            rival_lines(bonds.rivals),
        ),
    }
    free = dict.fromkeys(capitals, True)
    return _World(calibration, list(aware), bonds, texts, originals, free)


def _world() -> _World:
    calibration = _calibration()
    countries = [_country(tag, calibration) for tag in ROSTER]
    return _written(countries, BONDS, calibration)


def test_the_planned_groups_and_their_records_have_no_problems() -> None:
    world = _world()
    assert world.problems() == []
    record = written_countries(world.texts["10_countries.txt"], {"CNA", "LGA", "PLN"})
    assert record["CNA"].owned == ("xCNA",)
    assert not record["CNA"].pop
    assert record["CNA"].currency == world.calibration.cohesion
    assert record["LGA"].government["land_vs_naval"] == "60"
    assert record["PLN"].government["type"] == "monarchy"


def test_sacred_centre_rejects_an_inherited_monarchy_template() -> None:
    world = _world()
    countries = [replace(c, include="monarchy_t") if c.tag == "SCA" else c for c in world.countries]
    problems = _written(countries, world.bonds, world.calibration).problems()
    assert any("sacred centre" in problem for problem in problems)


def test_a_tribe_that_is_not_landed_holds_pops_without_owning_a_location() -> None:
    world = _world()
    calibration = world.calibration
    countries = [
        replace(c, landed=False, currency=()) if c.tag == "CNA" else c for c in world.countries
    ]
    bonds = replace(
        BONDS,
        groups=tuple((k, t) for k, t in GROUPS if k != HIGHLAND_CONFEDERATION),
        confederations=(),
    )
    countries = [replace(c, archetype="") if c.tag.startswith("CN") else c for c in countries]
    assert _written(countries, bonds, calibration).problems() == []
    record = written_countries(
        _written(countries, bonds, calibration).texts["10_countries.txt"], {"CNA"}
    )
    assert record["CNA"].pop
    assert record["CNA"].owned == ()


@dataclass(frozen=True, slots=True)
class _Break:
    """A way to break the written setup, and the complaint it has to draw."""

    complaint: str
    mutate: Callable[[_World], None]


def _edit(name: str, old: str, new: str) -> Callable[[_World], None]:
    def mutate(world: _World) -> None:
        assert old in world.texts[name]
        world.texts[name] = world.texts[name].replace(old, new, 1)

    return mutate


def _bind(world: _World) -> None:
    world.free["LGA"] = False


def _stray_alliance(world: _World) -> None:
    world.bonds = replace(world.bonds, alliances=(*world.bonds.alliances, ("LGA", "RLA")))


def _unreturned_rivalry(world: _World) -> None:
    world.bonds = replace(world.bonds, rivals=world.bonds.rivals[:-1])


def _unknown_member(world: _World) -> None:
    world.bonds = replace(world.bonds, groups=(*GROUPS, (SEA_LEAGUE, ("LGA", "NOBODY", "LGB"))))


def _forget(world: _World) -> None:
    """LGA does not discover the area of its ally LGB."""
    countries = [
        replace(c, areas=tuple(a for a in c.areas if a != "xLGB")) if c.tag == "LGA" else c
        for c in world.countries
    ]
    world.texts["10_countries.txt"] = (
        "countries = {\n\tcountries = {\n" + country_records(tuple(countries)) + "\t}\n}\n"
    )


ALLIED = "first = LGB second = LGC type = alliance }"
BREAKS = {
    "template": _Break(
        "does not write its template",
        _edit("10_countries.txt", 'include = "republic_t"', 'include = "monarchy_t"'),
    ),
    "position": _Break(
        "writes the government",
        _edit("10_countries.txt", "land_vs_naval = 60", "land_vs_naval = 0"),
    ),
    "theocracy": _Break(
        "writes the government", _edit("10_countries.txt", "type = theocracy", "type = monarchy")
    ),
    "currency": _Break(
        "writes the currency",
        _edit("10_countries.txt", "tribal_cohesion = 90", "tribal_cohesion = 10"),
    ),
    "ownership": _Break(
        "own its locations",
        _edit(
            "10_countries.txt",
            "own_control_core = {\n\t\t\txCNA",
            "add_pops_from_locations = {\n\t\t\txCNA",
        ),
    ),
    "missing_alliance": _Break(
        "12_diplomacy.txt repeats or lacks",
        _edit("12_diplomacy.txt", "first = LGA second = LGB", "first = LGA second = LGC"),
    ),
    "repeated_alliance": _Break(
        "12_diplomacy.txt repeats or lacks",
        _edit(
            "12_diplomacy.txt",
            ALLIED,
            f"{ALLIED}\n\tscripted_mutual = {{ first = LGC second = LGB type = alliance }}",
        ),
    ),
    "old_alliance": _Break(
        "Old World records of 12_diplomacy.txt",
        _edit("12_diplomacy.txt", "first = THO", "first = TRY"),
    ),
    "missing_rivalry": _Break(
        "20_rivals.txt repeats or lacks",
        _edit("20_rivals.txt", "first = SCA second = SCC", "first = SCA second = SCB"),
    ),
    "old_rivalry": _Break(
        "Old World records of 20_rivals.txt", _edit("20_rivals.txt", "first = FRA", "first = FRX")
    ),
    "missing_confederation": _Break(
        "organizations repeat or lack",
        _edit(
            "15_international_organizations.txt",
            "members = { CNA CNB CNC }",
            "members = { CNA CNB }",
        ),
    ),
    "undiscovered": _Break("without discovering", _forget),
    "bound": _Break("bound country", _bind),
    "stray_alliance": _Break("does not join a sea league", _stray_alliance),
    "unreturned": _Break("is not returned", _unreturned_rivalry),
    "unknown_member": _Break("repeats or lacks a country", _unknown_member),
}


@pytest.mark.parametrize("case", sorted(BREAKS))
def test_each_broken_record_is_found_and_not_mended(case: str) -> None:
    world = _world()
    BREAKS[case].mutate(world)
    problems = world.problems()
    assert any(BREAKS[case].complaint in problem for problem in problems), problems
