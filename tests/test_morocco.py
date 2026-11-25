"""The African start keeps the Iberian conquests under the chosen owner."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw.eu5_africa_start import (
    AFRICAN_HOLDINGS,
    COUNTRIES_BLOCK,
    COUNTRIES_FILE,
    IBERIAN_HOLDINGS,
    AfricanLand,
    AfricanStartError,
    algeciras,
    apply_morocco_start,
    plan_morocco,
)
from rnw.eu5_rewrite import owned_locations
from rnw.history_model import Route
from rnw.loc_keys import KeySpace
from rnw.pdx import parse
from rnw.settings import MoroccoPolicy

AFRICA = {f"loc_{i:03d}": (i + 5, 4) for i in range(110)}
ROUTES = tuple(Route(f"loc_{i:03d}", f"loc_{i + 1:03d}") for i in range(109))
LAND = AfricanLand(AFRICA, 1000, ROUTES)
ORIGINAL = dict.fromkeys(IBERIAN_HOLDINGS, (4, 4)) | {"fez": (12, 4)}
SETUP = f"""countries = {{ countries = {{
    CAS = {{ capital = toledo own_control_core = {{ toledo }} }}
    GRA = {{ capital = granada own_control_core = {{ granada }} }}
    MOR = {{
        capital = fez
        own_control_core = {{ fez {" ".join(IBERIAN_HOLDINGS)} }}
        government = {{ type = monarchy ruler = ruler_mor }}
    }}
}}
}}
"""


def test_reservation_uses_passable_candidates_and_wraps_distance() -> None:
    points = AFRICA | {"at_wrap": (4, 998), "isolated": (4, 4)}
    routes = (*ROUTES, Route("at_wrap", "loc_000"))
    start = plan_morocco(AfricanLand(points, 1000, routes), ORIGINAL)
    assert start.policy is MoroccoPolicy.RESTORE
    assert len(start.africa) == AFRICAN_HOLDINGS
    assert "at_wrap" in start.africa
    assert "isolated" not in start.africa
    assert start.capital == "loc_007"
    assert "loc_109" not in start.africa
    reverse = AfricanLand(dict(reversed(tuple(points.items()))), 1000, routes[::-1])
    assert plan_morocco(reverse, ORIGINAL) == start


def test_reservation_grows_from_a_passable_iberian_border() -> None:
    grounded = replace(LAND, borders=(("loc_109", "gibraltar", 0), ("loc_000", "ronda", 1)))
    start = plan_morocco(grounded, ORIGINAL)
    assert start.africa[0] == "loc_109"
    assert set(start.africa) == {f"loc_{i:03d}" for i in range(24, 110)}


def test_reservation_requires_enough_land_for_the_exact_holdings() -> None:
    with pytest.raises(AfricanStartError, match="requires 86 passable locations"):
        _ = plan_morocco(AfricanLand({"tiny": (8, 4)}, 1000, ()), ORIGINAL)


@pytest.mark.parametrize("policy", list(MoroccoPolicy))
def test_policy_has_one_iberian_owner_and_never_changes_its_population(
    policy: MoroccoPolicy,
) -> None:
    start = plan_morocco(LAND, ORIGINAL, policy)
    if policy is MoroccoPolicy.RESTORE:
        start = replace(start, capital_province="province_of_morocco")
    emirate = algeciras(42, frozenset({"MOR", "CAS", "GRA"}), KeySpace(set()), frozenset())
    texts = {
        COUNTRIES_FILE: SETUP,
        "05_characters.txt": "character_db = { ruler_mor = { tag = MOR birth = fez } }",
        "06_pops.txt": "locations = { algeciras = { define_pop = { culture = andalusi } } }",
        "12_diplomacy.txt": "diplomacy_manager = { rival = { first = CAS second = MOR } }",
    }
    result = apply_morocco_start(
        start,
        texts,
        {"fez"},
        {},
        location_replacements={"fez": "loc_033"},
        final_locations={*ORIGINAL.keys() - {"fez"}, "granada", "toledo", *AFRICA},
        replacement_capitals={},
        emirate=emirate if policy is MoroccoPolicy.EMIRATE else None,
    )
    countries = parse(result.texts[COUNTRIES_FILE]).block(*COUNTRIES_BLOCK)
    assert countries is not None
    recipient = {
        MoroccoPolicy.RESTORE: "MOR",
        MoroccoPolicy.EMIRATE: emirate.tag,
        MoroccoPolicy.CASTILE: "CAS",
        MoroccoPolicy.GRANADA: "GRA",
    }[policy]
    country = countries.block(recipient)
    assert country is not None
    expected = {
        MoroccoPolicy.RESTORE: {*IBERIAN_HOLDINGS, *start.africa},
        MoroccoPolicy.EMIRATE: set(IBERIAN_HOLDINGS),
        MoroccoPolicy.CASTILE: {*IBERIAN_HOLDINGS, "toledo"},
        MoroccoPolicy.GRANADA: {*IBERIAN_HOLDINGS, "granada"},
    }[policy]
    assert owned_locations(country) == expected
    assert result.texts["06_pops.txt"] == texts["06_pops.txt"]
    assert countries.block("GRA") is not None
    if policy is MoroccoPolicy.GRANADA:
        assert (capital := country.first("capital")) is not None
        assert capital.value == "granada"
        assert (integrated := country.block("own_control_integrated")) is not None
        assert [word.value for word in integrated.words()] == list(IBERIAN_HOLDINGS)
    if policy is MoroccoPolicy.RESTORE:
        assert "MOR" not in result.removed_ids
        assert (castile := countries.block("CAS")) is not None
        assert (discoveries := castile.block("discovered_provinces")) is not None
        assert [word.value for word in discoveries.words()] == [start.capital_province]
        assert f"capital = {start.capital}" in result.texts[COUNTRIES_FILE]
        assert "ruler = ruler_mor" in result.texts[COUNTRIES_FILE]
        assert f"birth = {start.capital}" in result.texts["05_characters.txt"]
    else:
        assert "MOR" in result.removed_ids
        assert "ruler_mor" in result.removed_ids
        assert "second = MOR" not in result.texts["12_diplomacy.txt"]


def test_a_forged_reservation_cannot_take_a_vanilla_holding() -> None:
    start = plan_morocco(LAND, ORIGINAL)
    bad = replace(start, africa=("ronda", *start.africa[1:]))
    with pytest.raises(AfricanStartError, match="86 distinct new African holdings"):
        _ = apply_morocco_start(
            bad,
            {COUNTRIES_FILE: SETUP},
            {"fez"},
            {},
            location_replacements={},
            final_locations={*IBERIAN_HOLDINGS, *AFRICA},
            replacement_capitals={},
        )
