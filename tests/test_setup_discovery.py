"""A vanished discovery area does not retire an otherwise retained country."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_nw_export import (
    _discovery_outputs,  # pyright: ignore[reportPrivateUsage]
    _setup_paths,  # pyright: ignore[reportPrivateUsage]
)
from rnw.eu5_remap import GeographicRemap, remap_discoveries, remap_text
from rnw.eu5_rewrite import prune_regional_setup, prune_setup, retain_country_territory
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path


def test_regional_start_reads_dlc_town_rights_at_their_mounted_path(tmp_path: Path) -> None:
    name = "25_city_rights.txt"
    relative = f"main_menu/setup/1337/{name}"
    source = tmp_path / "game/dlc/example" / relative
    source.parent.mkdir(parents=True)
    town_rights = "townrights_manager = { old_city = city_rights kept_city = city_rights }"
    _ = source.write_text(town_rights, encoding="utf-8")
    assert name not in _setup_paths(tmp_path, regional=False)
    assert _setup_paths(tmp_path, regional=True) == {name: source}
    result = prune_setup(
        {name: source.read_text(encoding="utf-8")}, {"old_city"}, {}, regional=True
    )
    holder = parse(result.texts[name]).block("townrights_manager")
    assert holder is not None
    assert [entry.key for entry in holder.entries] == ["kept_city"]


def test_discoveries_bind_the_same_provinces_in_templates_and_country_records(
    tmp_path: Path,
) -> None:
    relative = "main_menu/setup/templates/expl_crossing.txt"
    source = tmp_path / "game" / relative
    source.parent.mkdir(parents=True)
    template = (
        "discovered_areas = { old_key kept_area }\n"
        "discovered_provinces = { old_key same_target kept_province }\n"
        "discovered_regions = { old_key }\n"
    )
    _ = source.write_text(template, encoding="utf-8-sig")
    bindings = GeographicRemap(
        {"old_key": "new_location"},
        {"old_key": "new_province", "same_target": "new_province"},
        {"old_key": "new_area"},
    )
    outputs = _discovery_outputs(tmp_path, bindings)
    assert set(outputs) == {relative}
    assert outputs[relative].startswith(b"\xef\xbb\xbf")
    rewritten = outputs[relative].decode("utf-8-sig")
    holder = parse(rewritten)
    for field, words in (
        ("discovered_areas", ["new_area", "kept_area"]),
        ("discovered_provinces", ["new_province", "kept_province"]),
        ("discovered_regions", ["old_key"]),
    ):
        block = holder.block(field)
        assert block is not None
        assert [word.value for word in block.words()] == words
    assert (
        remap_discoveries(f"countries = {{ countries = {{ KEEP = {{ {template} }} }} }}", bindings)
        == f"countries = {{ countries = {{ KEEP = {{ {rewritten} }} }} }}"
    )


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


def test_retired_saint_does_not_retire_the_religion_or_its_other_members() -> None:
    texts = {
        "05_characters.txt": """character_db = {
            old_saint = { birth = gone_city }
            kept_saint = { birth = kept_city }
        }""",
        "06_pops.txt": """locations = {
            kept_city = { define_pop = { religion = shared_faith } }
        }""",
        "13_religion.txt": """religion_manager = {
            shared_faith = {
                saint = { character = old_saint }
                saint = { character = kept_saint }
                timed_modifier = { modifier = kept_modifier }
            }
        }
        building_manager = { cardinal = { location = gone_city } }""",
    }
    result = prune_setup(texts, {"gone_city"}, {}, regional=True)
    assert result.texts["06_pops.txt"] == texts["06_pops.txt"]
    assert "old_saint" in result.removed_ids
    assert "shared_faith" not in result.removed_ids
    assert "old_saint" not in result.texts["13_religion.txt"]
    religion = parse(result.texts["13_religion.txt"]).block("religion_manager", "shared_faith")
    assert religion is not None
    assert religion.block("saint") is not None
    assert religion.block("timed_modifier") is not None
    assert "kept_saint" in result.texts["13_religion.txt"]
    assert "gone_city" not in result.texts["13_religion.txt"]


def test_regional_setup_preserves_a_mixed_country_and_its_ruler() -> None:
    texts = {
        "04_dynasties.txt": "dynasty_manager = { house = { name = house home = old_city } }",
        "05_characters.txt": """character_db = {
            past = { tag = EXT birth = old_city }
            monarch = {
                tag = MIX birth = old_city dynasty = house father = past spouse = partner
            }
            partner = { tag = OUT birth = retained_town spouse = monarch }
        }""",
        "10_countries.txt": """countries = { countries = {
            MIX = {
                capital = old_city
                own_control_conquered = { old_city new_capital }
                government = { ruler = monarch }
            }
            EXT = { capital = old_town own_core = { old_town } }
            OUT = { capital = retained_town own_core = { retained_town } }
        } }""",
    }
    result = prune_regional_setup(
        texts,
        {"old_city", "old_town"},
        {},
        location_replacements={"old_city": "new_city"},
        final_locations={"new_city", "new_capital", "retained_town"},
        replacement_capitals={"MIX": "new_capital"},
    )
    assert result.removed_ids == {"old_city", "old_town", "past", "EXT"}
    countries = parse(result.texts["10_countries.txt"]).block("countries", "countries")
    assert countries is not None
    assert countries.block("OUT") is not None
    mix = countries.block("MIX")
    assert mix is not None
    assert (capital := mix.first("capital")) is not None
    assert capital.value == "new_capital"
    assert (owned := mix.block("own_control_conquered")) is not None
    assert [word.value for word in owned.words()] == ["new_capital"]
    chars = parse(result.texts["05_characters.txt"]).block("character_db")
    assert chars is not None
    assert chars.block("past") is None
    monarch = chars.block("monarch")
    assert monarch is not None
    assert (birth := monarch.first("birth")) is not None
    assert birth.value == "new_city"
    assert monarch.first("father") is None
    assert monarch.first("spouse") is not None
    assert "home = new_city" in result.texts["04_dynasties.txt"]


@pytest.mark.parametrize("replacement", [{}, {"old_city": "old_city"}, {"old_city": "unknown"}])
def test_regional_setup_requires_an_existing_destination_for_personal_places(
    replacement: dict[str, str],
) -> None:
    texts = {
        "04_dynasties.txt": "dynasty_manager = { house = { home = old_city } }",
        "10_countries.txt": "countries = { countries = { } }",
    }
    with pytest.raises(ValueError, match="house needs a replacement for home old_city"):
        _ = prune_regional_setup(
            texts,
            {"old_city"},
            {},
            location_replacements=replacement,
            final_locations={"new_city"},
            replacement_capitals={},
        )


def test_regional_pruning_does_not_use_statement_types_or_advisory_rows_as_ids() -> None:
    sources = {
        "10_countries.txt": (
            "countries = { countries = {"
            "  OUT = { type = army capital = kept_city }"
            "  EXT = { capital = gone_city }"
            "} }"
        ),
        "25_area_preferences.txt": (
            "countries = { countries = { OUT = { preference = gone_city } } }"
        ),
        "27_armies.txt": (
            "unit_manager = { army = { tag = EXT } } unit_manager = { army = { tag = OUT } }"
        ),
    }
    result = prune_setup(sources, {"gone_city"}, {}, regional=True)
    assert result.removed_ids == {"gone_city", "EXT"}
    assert "OUT = {" in result.texts["10_countries.txt"]
    assert "OUT = {" not in result.texts["25_area_preferences.txt"]
    assert "army = { tag = OUT }" in result.texts["27_armies.txt"]


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
