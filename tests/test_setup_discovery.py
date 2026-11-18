"""A vanished discovery area does not retire an otherwise retained country."""

from __future__ import annotations

import pytest

from rnw.eu5_remap import remap_text
from rnw.eu5_rewrite import prune_setup, retain_country_territory
from rnw.pdx import parse


@pytest.mark.parametrize("remaining", ["kept_area", ""])
def test_a_country_keeps_its_setup_when_only_a_discovery_area_vanishes(remaining: str) -> None:
    text = (
        "countries = { countries = {\n"
        "AAA = {\n capital = kept_city\n government = { type = monarchy }\n"
        f" discovered_areas = {{ gone_area {remaining} }}\n"
        "}\n} }\n"
    )
    rebound, _ = remap_text(text, {"gone_area": "new_area"})
    result = prune_setup({"10_countries.txt": rebound}, {"gone_area"}, {})
    countries = parse(result.texts["10_countries.txt"]).block("countries", "countries")
    assert countries is not None
    country = countries.block("AAA")
    assert country is not None
    assert country.first("capital") is not None
    assert country.block("government") is not None
    discoveries = country.block("discovered_areas")
    assert discoveries is not None
    assert [word.value for word in discoveries.words()] == [
        "new_area",
        *([remaining] if remaining else []),
    ]
    assert "AAA" not in result.removed_ids
    assert result.deleted["10_countries.txt"] == 0


def test_a_removed_capital_still_retires_the_country_and_its_dependents() -> None:
    texts = {
        "10_countries.txt": (
            "countries = { countries = {\n"
            "AAA = { capital = gone_city discovered_areas = { gone_area } }\n"
            "BBB = { capital = kept_city }\n} }\n"
        ),
        "12_diplomacy.txt": "diplomacy = {\n dependency = { first = BBB second = AAA }\n}\n",
    }
    sources = {name: remap_text(text, {"gone_area": "new_area"})[0] for name, text in texts.items()}
    result = prune_setup(sources, {"gone_city", "gone_area"}, {})
    assert "AAA" in result.removed_ids
    assert "AAA" not in result.texts["10_countries.txt"]
    assert "BBB" in result.texts["10_countries.txt"]
    assert "dependency" not in result.texts["12_diplomacy.txt"]


def test_a_country_retired_in_a_later_pass_does_not_keep_nested_word_edits() -> None:
    texts = {
        "10_countries.txt": (
            "countries = { countries = {\n"
            "AAA = { capital = kept_city ruler = actor discovered_areas = { gone_area } }\n"
            "} }\n"
        ),
        "characters.txt": "characters = {\n actor = { birth_location = gone_city }\n}\n",
    }
    sources = {name: remap_text(text, {"gone_area": "new_area"})[0] for name, text in texts.items()}
    result = prune_setup(sources, {"gone_city", "gone_area"}, {})
    assert {"actor", "AAA"} <= result.removed_ids
    assert "AAA" not in result.texts["10_countries.txt"]


MIXED_COUNTRIES = """countries = { countries = {
    MIX = {
        capital = gone_city # Seat of government
        own_control_core = { gone_city }
        own_control_integrated = { old_strip kept_city kept_country }
        own_control_conquered = { held_border }
        control = { gone_town }
        government = { type = monarchy }
    }
    END = { capital = gone_city own_control_core = { gone_city } }
    ADJ = { capital = other_city own_control_core = { other_city }
            our_cores_conquered_by_others = { gone_city } }
} }
"""
REMOVED_LOCATIONS = {"gone_city", "old_strip", "gone_town"}


def test_keep_cross_border_ownership_and_reseat_its_capital_before_pruning() -> None:
    countries = retain_country_territory(MIXED_COUNTRIES, REMOVED_LOCATIONS, {"MIX": "kept_city"})
    result = prune_setup({"10_countries.txt": countries}, REMOVED_LOCATIONS, {})
    assert "END" in result.removed_ids
    assert {"MIX", "ADJ"}.isdisjoint(result.removed_ids)
    rewritten = result.texts["10_countries.txt"]
    assert "capital = kept_city # Seat of government" in rewritten
    holder = parse(rewritten).block("countries", "countries")
    assert holder is not None
    kept = holder.block("MIX")
    assert kept is not None
    assert kept.block("own_control_core") is None
    assert kept.block("control") is None
    lands = kept.block("own_control_integrated")
    assert lands is not None
    assert [word.value for word in lands.words()] == ["kept_city", "kept_country"]
    assert kept.block("own_control_conquered") is not None
    assert kept.block("government") is not None


@pytest.mark.parametrize("new_capital", ["gone_city", "other_city"])
def test_reject_a_replacement_capital_outside_surviving_holdings(new_capital: str) -> None:
    with pytest.raises(ValueError, match="MIX needs a replacement capital"):
        _ = retain_country_territory(MIXED_COUNTRIES, REMOVED_LOCATIONS, {"MIX": new_capital})


def test_remove_an_organization_that_loses_its_last_member_in_a_later_pass() -> None:
    texts = {
        "15_international_organizations.txt": (
            "international_organizations = {\n"
            "add_international_organization = { members = { AAA BBB } }\n"
            "add_international_organization = { members = { CCC } }\n}\n"
        ),
        "10_countries.txt": (
            "countries = { countries = {\n"
            "BBB = { capital = replaced_city }\n"
            "CCC = { capital = retained_city }\n} }\n"
        ),
    }
    result = prune_setup(texts, {"AAA", "replaced_city"}, {})
    organizations = result.texts["15_international_organizations.txt"]
    assert "members = { CCC }" in organizations
    assert "AAA" not in organizations
    assert "BBB" not in organizations
