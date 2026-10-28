"""The export checks the written setup of the extraordinary societies (R7d)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw.archetypes import HIGHLAND_CONFEDERATION, SEA_LEAGUE
from rnw.eu5_archetypes import (
    ArchetypeCalibration,
    TheocracyInstitutions,
    alliance_lines,
    confederation_lines,
    rival_lines,
)
from rnw.eu5_natives import Country, NativeWorld, VanillaNatives, country_records
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import COUNTRIES_FILE, SETUP_DIR, NewWorldExportError, verify_archetypes
from rnw.eu5_rewrite import insert_into_block
from rnw.model import CellClass

COHESION = (("gold", 100), ("stability", 33), ("tribal_cohesion", 90))
CALIBRATION = ArchetypeCalibration(
    republic_include="republic_t",
    republic_government=(("type", "republic"), ("heir_selection", "oligarchic_elective")),
    republic_level=2,
    theocracy=(("type", "theocracy"), ("heir_selection", "theocratic_elective")),
    theocracy_institutions=TheocracyInstitutions(
        (("marriage_law", "monogamous_marriage"), ("heir_religion_law", "heir_special_succession")),
        "assembly",
        ("catholic",),
    ),
    confederation_date="1337.1.1",
    cohesion=COHESION,
    confederate_density=0,
    sliders={SEA_LEAGUE: (("land_vs_naval", 60),)},
    alliances=1,
    rivals=1,
    confederations=1,
)
KEYS = ("g0", "g1", "g2", "g3", "g4", "g5", "g6")
ORIGINALS = {
    "12_diplomacy.txt": (
        "diplomacy_manager = {\n\tscripted_mutual = { first = A second = B type = alliance }\n}\n"
    ),
    "15_international_organizations.txt": "international_organization_manager = {\n}\n",
    "20_rivals.txt": "diplomacy_manager = {\n\trival = { first = A second = B }\n}\n",
}


def _plan() -> Plan:
    return Plan(
        cells=[
            PlannedCell(
                key=key,
                name=key,
                color=1,
                kind=CellClass.LAND,
                province="p",
                area=key,
                region="r",
                subcontinent="s",
                continent="america",
            )
            for key in KEYS
        ]
    )


def _country(tag: str, where: str, **changes: object) -> Country:
    base = Country(
        tag=tag,
        name=tag,
        kind="state",
        members=(where,),
        capital=where,
        culture="c",
        religion="r",
        include="monarchy_t",
        areas=(where,),
        color=(1, 2, 3),
        color2=(3, 2, 1),
        government=(("type", "monarchy"),),
        level=2,
    )
    return replace(base, **changes)


def _countries() -> tuple[Country, ...]:
    government = (*CALIBRATION.republic_government, ("land_vs_naval", "60"))
    league = {"include": "republic_t", "government": government, "archetype": SEA_LEAGUE}
    tribe = {
        "kind": "tribe",
        "level": None,
        "landed": True,
        "currency": COHESION,
        "archetype": HIGHLAND_CONFEDERATION,
    }
    league_places = {
        "LGA": ("g0", ("g1", "g2")),
        "LGB": ("g1", ("g0", "g2")),
        "LGC": ("g2", ("g0", "g1")),
    }
    countries = [
        _country(tag, where, areas=(where, *known), **league)
        for tag, (where, known) in league_places.items()
    ]
    confederates = {
        "CNA": ("g3", ("g4", "g5")),
        "CNB": ("g4", ("g3", "g5")),
        "CNC": ("g5", ("g3", "g4")),
    }
    countries += [
        _country(tag, where, areas=(where, *known), **tribe)
        for tag, (where, known) in confederates.items()
    ]
    countries.append(_country("PLN", "g6"))
    return tuple(countries)


def _natives(countries: tuple[Country, ...] | None = None, **changes: object) -> NativeWorld:
    groups = [
        {"kind": SEA_LEAGUE, "tags": ["LGA", "LGB", "LGC"]},
        {"kind": HIGHLAND_CONFEDERATION, "tags": ["CNA", "CNB", "CNC"]},
    ]
    natives = NativeWorld(
        pops={},
        countries=countries or _countries(),
        ranks={},
        markets=(),
        holy_sites={},
        names={},
        vassals=(),
        complexity={},
        population={},
        stats={},
        alliances=(("LGA", "LGB"), ("LGB", "LGC"), ("LGA", "LGC")),
        confederations=(("CNA", "CNB", "CNC"),),
        confederation_date="1337.1.1",
        archetypes={"groups": groups},
    )
    return replace(natives, **changes)


def _vanilla(calibration: ArchetypeCalibration | None = CALIBRATION) -> VanillaNatives:
    return VanillaNatives(
        density={},
        population_per_location=0,
        cultures={},
        religions={},
        templates=frozenset(),
        reserved_tags=frozenset(),
        holy_sites=(),
        archetypes=calibration,
    )


def _outputs(natives: NativeWorld, *, skip: tuple[str, ...] = ()) -> dict[str, bytes]:
    countries = "countries = {\n\tcountries = {\n" + country_records(natives.countries) + "\t}\n}\n"
    files = {
        COUNTRIES_FILE: countries,
        "12_diplomacy.txt": insert_into_block(
            ORIGINALS["12_diplomacy.txt"], ("diplomacy_manager",), alliance_lines(natives.alliances)
        ),
        "15_international_organizations.txt": insert_into_block(
            ORIGINALS["15_international_organizations.txt"],
            ("international_organization_manager",),
            confederation_lines(natives.confederation_date, natives.confederations),
        ),
        "20_rivals.txt": insert_into_block(
            ORIGINALS["20_rivals.txt"], ("diplomacy_manager",), rival_lines(natives.rivals)
        ),
    }
    return {
        f"{SETUP_DIR}/{name}".removeprefix("game/"): text.encode()
        for name, text in files.items()
        if name not in skip
    }


def _verify(outputs: dict[str, bytes], natives: NativeWorld, vanilla: VanillaNatives | None = None):  # noqa: ANN202
    return verify_archetypes(
        outputs, natives, _plan(), vanilla or _vanilla(), ORIGINALS | {COUNTRIES_FILE: ""}, set()
    )


def test_verification_accepts_the_planned_league_and_confederation() -> None:
    natives = _natives()
    assert _verify(_outputs(natives), natives) == {
        "archetype_groups": 2,
        "archetype_alliances": 3,
        "archetype_rivalries": 0,
        "archetype_confederations": 1,
    }


def test_a_world_without_groups_needs_no_lines_and_leaves_the_files_vanillas() -> None:
    plain = tuple(
        replace(
            c,
            kind="state",
            level=2,
            archetype="",
            landed=False,
            currency=(),
            include="monarchy_t",
            government=(("type", "monarchy"),),
        )
        for c in _countries()
    )
    natives = _natives(plain, alliances=(), confederations=(), archetypes={"groups": []})
    unchanged = tuple(ORIGINALS)
    result = _verify(_outputs(natives, skip=unchanged), natives)
    assert result["archetype_groups"] == 0


def test_a_group_without_a_calibration_is_refused() -> None:
    natives = _natives()
    with pytest.raises(NewWorldExportError, match="No archetype calibration"):
        _ = _verify(_outputs(natives), natives, _vanilla(None))


def test_a_missing_alliance_a_missing_organization_and_a_wrong_record_are_refused() -> None:
    natives = _natives()
    lacking = replace(natives, alliances=natives.alliances[:2])
    with pytest.raises(NewWorldExportError, match=r"12_diplomacy\.txt repeats or lacks"):
        _ = _verify(_outputs(lacking), natives)
    with pytest.raises(NewWorldExportError, match="organizations repeat or lack"):
        _ = _verify(_outputs(replace(natives, confederations=())), natives)
    outputs = _outputs(natives)
    path = "main_menu/setup/1337/10_countries.txt"
    outputs[path] = outputs[path].replace(b"land_vs_naval = 60", b"land_vs_naval = 10")
    with pytest.raises(NewWorldExportError, match="writes the government"):
        _ = _verify(outputs, natives)
