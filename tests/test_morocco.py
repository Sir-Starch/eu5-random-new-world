"""The African start keeps the Iberian conquests under the chosen owner."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rnw.eu5_morocco import (
    AFRICAN_HOLDINGS,
    COUNTRIES_BLOCK,
    COUNTRIES_FILE,
    IBERIAN_HOLDINGS,
    MoroccoError,
    MoroccoPolicy,
    algeciras,
    apply_morocco_start,
    plan_morocco,
)
from rnw.eu5_rewrite import owned_locations
from rnw.loc_keys import KeySpace
from rnw.pdx import parse

AFRICA = {f"loc_{i:03d}": (i + 5, 4) for i in range(110)}
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
    start = plan_morocco(AFRICA | {"at_wrap": (4, 998)}, ORIGINAL, 1000)
    assert start.policy is MoroccoPolicy.RESTORE
    assert len(start.africa) == AFRICAN_HOLDINGS
    assert "at_wrap" in start.africa
    assert start.capital == "loc_007"
    assert "loc_109" not in start.africa
    reverse = dict(reversed(tuple(AFRICA.items())))
    assert plan_morocco(reverse | {"at_wrap": (4, 998)}, ORIGINAL, 1000) == start


def test_reservation_requires_enough_land_for_the_exact_holdings() -> None:
    with pytest.raises(MoroccoError, match="requires 86 passable locations"):
        _ = plan_morocco({"tiny": (8, 4)}, ORIGINAL, 1000)


@pytest.mark.parametrize("policy", list(MoroccoPolicy))
def test_policy_has_one_iberian_owner_and_never_changes_its_population(
    policy: MoroccoPolicy,
) -> None:
    start = plan_morocco(AFRICA, ORIGINAL, 1000, policy)
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
    }[policy]
    country = countries.block(recipient)
    assert country is not None
    expected = {
        MoroccoPolicy.RESTORE: {*IBERIAN_HOLDINGS, *start.africa},
        MoroccoPolicy.EMIRATE: set(IBERIAN_HOLDINGS),
        MoroccoPolicy.CASTILE: {*IBERIAN_HOLDINGS, "toledo"},
    }[policy]
    assert owned_locations(country) == expected
    assert result.texts["06_pops.txt"] == texts["06_pops.txt"]
    assert countries.block("GRA") is not None
    if policy is MoroccoPolicy.RESTORE:
        assert "MOR" not in result.removed_ids
        assert f"capital = {start.capital}" in result.texts[COUNTRIES_FILE]
        assert "ruler = ruler_mor" in result.texts[COUNTRIES_FILE]
        assert f"birth = {start.capital}" in result.texts["05_characters.txt"]
    else:
        assert "MOR" in result.removed_ids
        assert "ruler_mor" in result.removed_ids
        assert "second = MOR" not in result.texts["12_diplomacy.txt"]


def test_a_forged_reservation_cannot_take_a_vanilla_holding() -> None:
    start = plan_morocco(AFRICA, ORIGINAL, 1000)
    bad = replace(start, africa=("ronda", *start.africa[1:]))
    with pytest.raises(MoroccoError, match="86 distinct new African holdings"):
        _ = apply_morocco_start(
            bad,
            {COUNTRIES_FILE: SETUP},
            {"fez"},
            {},
            location_replacements={},
            final_locations={*IBERIAN_HOLDINGS, *AFRICA},
            replacement_capitals={},
        )
