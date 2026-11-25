"""Restore the Mamluks before the new African societies claim territory."""

from __future__ import annotations

import pytest

from rnw.eu5_africa_start import (
    COUNTRIES_BLOCK,
    COUNTRIES_FILE,
    AfricanLand,
    AfricanStartError,
    damascus_sultanate,
    plan_mamluks,
    prepare_mamluk_start,
    verify_mamluk_start,
)
from rnw.eu5_rewrite import owned_locations, prune_regional_setup
from rnw.geography import Location
from rnw.history_model import Route
from rnw.loc_keys import KeySpace
from rnw.pdx import parse
from rnw.settings import MamlukPolicy

SETUP = """countries = { countries = {
    MAM = {
        capital = cairo
        own_control_core = { cairo alexandria }
        own_control_integrated = { giza damascus }
        own_control_conquered = { iskenderun }
        government = { ruler = mamluk_ruler heir_selection = mamluk_succesion }
    }
    MEC = { capital = mecca own_control_core = { mecca } }
} }
"""
OLD_AFRICA = {"cairo", "alexandria", "giza"}
ORIGINAL = {"cairo": (5, 90), "damascus": (5, 98), "iskenderun": (9, 99)}
AFRICA = {
    "wrapped": (5, 0),
    "nearest_to_cairo": (5, 92),
    "moroccan": (5, 96),
    "near_iskenderun": (8, 97),
    "distant": (30, 30),
}
LAND = AfricanLand(
    AFRICA, 100, (Route("nearest_to_cairo", "near_iskenderun"), Route("near_iskenderun", "wrapped"))
)


def test_restore_mamluk_capital_and_both_sides_of_the_start() -> None:
    countries = parse(SETUP).block(*COUNTRIES_BLOCK)
    assert countries is not None
    mamluks = countries.block("MAM")
    assert mamluks is not None
    start = plan_mamluks(LAND, ORIGINAL, mamluks, OLD_AFRICA, reserved={"moroccan"})
    assert start.core == ("nearest_to_cairo", "near_iskenderun")
    assert start.integrated == ("wrapped",)
    assert start.capital == "nearest_to_cairo"
    assert start.asia == {"damascus", "iskenderun"}
    assert start == plan_mamluks(
        AfricanLand(dict(reversed(tuple(AFRICA.items()))), 100, LAND.routes[::-1]),
        ORIGINAL,
        mamluks,
        OLD_AFRICA,
        reserved={"moroccan"},
    )
    final_locations = {*AFRICA, *start.asia, "mecca"}
    text = prepare_mamluk_start(start, SETUP, OLD_AFRICA, final_locations, None)
    result = prune_regional_setup(
        {
            COUNTRIES_FILE: text,
            "05_characters.txt": "character_db = { mamluk_ruler = { tag = MAM birth = cairo } }",
            "12_diplomacy.txt": (
                "diplomacy_manager = { dependency = { first = MAM second = MEC } }"
            ),
        },
        OLD_AFRICA,
        {},
        location_replacements={"cairo": start.capital},
        replacement_capitals={"MAM": start.capital},
        final_locations=final_locations,
    )
    final = result.texts[COUNTRIES_FILE]
    verify_mamluk_start(start, final, "MAM")
    assert "MAM" not in result.removed_ids
    assert "ruler = mamluk_ruler heir_selection = mamluk_succesion" in final
    assert "own_control_conquered = { iskenderun }" in final
    assert f"birth = {start.capital}" in result.texts["05_characters.txt"]
    assert "first = MAM second = MEC" in result.texts["12_diplomacy.txt"]
    written = parse(final).block(*COUNTRIES_BLOCK, "MAM")
    assert written is not None
    assert owned_locations(written) == {*start.asia, *start.africa}


def test_mamluk_reservation_cannot_take_moroccos_land() -> None:
    mamluks = parse(SETUP).block(*COUNTRIES_BLOCK, "MAM")
    assert mamluks is not None
    with pytest.raises(AfricanStartError, match="require 3 unreserved passable locations"):
        _ = plan_mamluks(
            LAND, ORIGINAL, mamluks, OLD_AFRICA, reserved={"moroccan", "wrapped", "distant"}
        )


def test_independent_damascus_takes_the_asian_holdings_only() -> None:
    mamluks = parse(SETUP).block(*COUNTRIES_BLOCK, "MAM")
    assert mamluks is not None
    start = plan_mamluks(
        AfricanLand({}, 100, ()), ORIGINAL, mamluks, OLD_AFRICA, policy=MamlukPolicy.DAMASCUS
    )
    assert start.africa == ()
    assert start.capital == "damascus"
    hierarchy = {
        key: Location(key, "asia", "middle_east", "levant", key, key) for key in start.asia
    }
    sultanate = damascus_sultanate(
        start, hierarchy, 17, frozenset({"MAM", "MEC"}), KeySpace(set()), frozenset()
    )
    assert sultanate.tag not in {"MAM", "MEC"}
    assert sultanate.culture == "levantine_culture"
    assert sultanate.religion == "sunni"
    locations = {*start.asia, "mecca", *AFRICA}
    text = prepare_mamluk_start(start, SETUP, OLD_AFRICA, locations, sultanate)
    result = prune_regional_setup(
        {
            COUNTRIES_FILE: text,
            "12_diplomacy.txt": "diplomacy_manager = { dependency = { first = MAM second = MEC } }",
        },
        OLD_AFRICA | {"MAM"},
        {},
        location_replacements={},
        replacement_capitals={},
        final_locations=locations,
    )
    final = result.texts[COUNTRIES_FILE]
    verify_mamluk_start(start, final, sultanate.tag)
    assert parse(final).block(*COUNTRIES_BLOCK, "MAM") is None
    assert parse(final).block(*COUNTRIES_BLOCK, "MEC") is not None
    assert "first = MAM" not in result.texts["12_diplomacy.txt"]
