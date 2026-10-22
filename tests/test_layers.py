"""The parts of a world: rolls in the settings and the code, their seeds, and the continent key."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import cast

import pytest
from typer.testing import CliRunner

from rnw.app.worldcode import (
    WorldCode,
    WorldCodeError,
    decode,
    encode,
    format_of,
    new_code,
    rolled,
    with_new_seed,
)
from rnw.cli import app
from rnw.layers import PARTS, land_key, layer_seed, rolls_of
from rnw.settings import (
    PRESETS,
    ROLLS,
    RollSettings,
    SettingsError,
    build_settings,
    run_spec,
    spec_digest,
)


def test_rolls_are_not_written_while_they_are_zero_so_old_documents_do_not_change() -> None:
    """The settings document, and every digest of it, is what it was before rolls existed."""
    settings = PRESETS["continents"]
    assert settings.rolls == ROLLS
    assert "rolls" not in settings.to_json_data()
    before = spec_digest(run_spec(5, settings))
    assert (
        spec_digest(run_spec(5, build_settings("continents", {"rolls": {"peoples": 0}}))) == before
    )
    rolled_settings = build_settings("continents", {"rolls": {"peoples": 2}})
    assert cast("dict[str, object]", rolled_settings.to_json_data()["rolls"]) == {
        "resources": 0,
        "peoples": 2,
    }
    assert spec_digest(run_spec(5, rolled_settings)) != before
    again = build_settings("continents", dict(rolled_settings.to_json_data()))
    assert again == rolled_settings


def test_rolls_are_whole_numbers_in_a_range() -> None:
    """A negative, a huge or a non-number roll is refused."""
    for bad in (-1, 65_536, 1.5, "1", True):
        with pytest.raises(SettingsError):
            _ = build_settings("continents", {"rolls": {"peoples": bad}})
    with pytest.raises(SettingsError):
        _ = build_settings("continents", {"rolls": {"land": 1}})
    assert RollSettings() == ROLLS


def test_a_part_draws_from_the_worlds_own_seed_until_it_is_rolled() -> None:
    """Roll 0 is the seed itself (so older worlds are unchanged); later rolls differ, stably."""
    seed = 123456789
    assert layer_seed(seed, "peoples", 0) == seed
    assert layer_seed(seed, "resources", 0) == seed
    first, second = layer_seed(seed, "peoples", 1), layer_seed(seed, "peoples", 2)
    assert len({seed, first, second, layer_seed(seed, "resources", 1)}) == 4
    assert layer_seed(seed, "peoples", 1) == first
    assert layer_seed(seed + 1, "peoples", 1) != first
    with pytest.raises(ValueError, match="Unknown part"):
        _ = layer_seed(seed, "land", 1)
    with pytest.raises(ValueError, match="counts from 0"):
        _ = layer_seed(seed, "peoples", -1)
    assert rolls_of(build_settings("continents", {"rolls": {"resources": 3}})) == {
        "resources": 3,
        "peoples": 0,
    }


def test_the_land_key_ignores_the_peoples_and_the_resources_but_not_the_land() -> None:
    """Versions of one continent share a key; another seed or another land setting does not."""
    base = PRESETS["continents"]
    key = land_key(base, 7)
    assert key == land_key(build_settings("continents", {"rolls": {"peoples": 4}}), 7)
    assert key == land_key(build_settings("continents", {"natives": {"empire_permille": 0}}), 7)
    assert key == land_key(build_settings("continents", {"new_world": {"precious_permille": 5}}), 7)
    assert key != land_key(base, 8)
    assert key != land_key(build_settings("continents", {"new_world": {"land_permille": 555}}), 7)
    assert key != land_key(PRESETS["islands"], 7)


def test_codes_with_rolls_round_trip_in_the_compact_format() -> None:
    """Rolls are two more numbered fields: a few bytes, and an old code decodes as before."""
    plain = new_code("continents", 42)
    assert decode(encode(plain)) == plain
    version = rolled(rolled(plain, "peoples"), "peoples")
    assert version.changes == {"rolls": {"peoples": 2}}
    text = encode(version)
    assert format_of(text) == 2
    assert decode(text) == version
    assert len(encode(rolled(plain, "resources"))) <= len(encode(plain)) + 6
    mixed = rolled(version, "resources")
    assert decode(encode(mixed)).settings().rolls == RollSettings(resources=1, peoples=2)


def test_a_new_continent_keeps_the_settings_and_starts_the_rolls_again() -> None:
    """A new seed, the same changes, no rolls; asking for a part that does not exist is refused."""
    start = new_code("islands", 9, {"natives": {"empire_permille": 500}, "rolls": {"peoples": 3}})
    fresh = with_new_seed(start, 11)
    assert (fresh.preset, fresh.seed) == ("islands", 11)
    assert fresh.changes == {"natives": {"empire_permille": 500}}
    assert with_new_seed(rolled(new_code("islands", 9), "peoples")).changes is None
    assert with_new_seed(new_code("islands", 9)).seed != 9
    with pytest.raises(WorldCodeError, match="Unknown part"):
        _ = rolled(start, "land")
    top = replace(start, changes={"rolls": {"peoples": 65_535}})
    with pytest.raises(WorldCodeError):
        _ = rolled(top, "peoples")
    assert WorldCode("islands", 1, "0.9.22").changes is None
    assert set(PARTS) == {"peoples", "resources"}


def test_the_reroll_command_prints_the_code_of_a_version() -> None:
    """Peoples and resources are drawn again on the same land; land is a new seed."""
    runner = CliRunner()
    code = encode(new_code("continents", 77))
    peoples = runner.invoke(app, ["reroll", code, "--part", "peoples"])
    assert peoples.exit_code == 0, peoples.output
    printed = cast("dict[str, object]", json.loads(peoples.output))
    assert printed["seed"] == 77
    assert printed["rolls"] == {"resources": 0, "peoples": 1}
    land = runner.invoke(app, ["reroll", code, "--part", "land", "--seed", "5"])
    document = cast("dict[str, object]", json.loads(land.output))
    assert document["seed"] == 5
    assert document["rolls"] == {"resources": 0, "peoples": 0}
    bad = runner.invoke(app, ["reroll", code, "--part", "weather"])
    assert bad.exit_code == 2
