"""A vanished discovery area does not retire an otherwise retained country."""

from __future__ import annotations

import pytest

from rnw.eu5_remap import remap_text
from rnw.eu5_rewrite import prune_setup
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
