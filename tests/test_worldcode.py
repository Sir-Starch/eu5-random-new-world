"""World codes: round trip, forgiving input, damage detection, version promise."""

from __future__ import annotations

from dataclasses import fields

import pytest

from rnw import __version__, epoch
from rnw.app import worldcode
from rnw.app.worldcode import WorldCode, WorldCodeError, decode, encode, new_code, reproduces
from rnw.settings import NativeSettings, NewWorldSettings


def test_a_default_world_is_a_short_code_that_round_trips() -> None:
    """Preset, seed and generator survive, and a default world needs 28 characters."""
    code = new_code("continents", 319218363)
    text = encode(code)
    assert text.startswith("RNW1-")
    assert len(text.replace("-", "")) == len("RNW1") + 28
    assert decode(text) == code
    assert code.generator == __version__


def test_ocean_mode_is_explicit_and_older_codes_keep_the_original_canvas() -> None:
    original = WorldCode("continents", 42, "0.11.99")
    assert decode(encode(original)).settings().new_world.expand_oceans == 0
    assert new_code("continents", 42).settings().new_world.expand_oceans == 1
    narrow = new_code("continents", 42, {"new_world": {"expand_oceans": 0}})
    assert decode(encode(narrow)).settings().new_world.expand_oceans == 0
    assert worldcode.with_new_seed(original, 43).settings().new_world.expand_oceans == 0
    assert worldcode.rolled(original, "resources").settings().new_world.expand_oceans == 0


def test_changed_settings_travel_with_the_code() -> None:
    """A change of a setting is part of the code; the decoded settings apply it."""
    changes: dict[str, object] = {"new_world": {"land_permille": 500}}
    code = new_code("archipelago", 7, changes)
    again = decode(encode(code))
    assert again == code
    assert again.settings().new_world.land_permille == 500
    assert again.settings().preset == "archipelago"
    assert len(encode(code)) > len(encode(new_code("archipelago", 7)))


def test_reading_forgives_case_spacing_and_look_alike_letters() -> None:
    """Lower case, spaces, line breaks and O/I/L for 0/1 read as the code was written."""
    code = new_code("continents", 0x1F0F0F0F0F0F0F01)
    text = encode(code)
    sloppy = text.lower().replace("-", " \n")
    assert decode(sloppy) == code
    folded = text.replace("0", "O").replace("1", "l")
    assert decode(folded) == code


def test_a_typing_mistake_is_found_by_the_check() -> None:
    """Changing, dropping or adding one character is refused, never read as another world."""
    text = encode(new_code("continents", 123456789))
    body = text.replace("-", "")[4:]
    others = [c for c in worldcode.ALPHABET if c != body[5]]
    broken = [body[:5] + others[0] + body[6:], body[:-1], body + "0"]
    for variant in broken:
        with pytest.raises(WorldCodeError):
            _ = decode("RNW1-" + variant)
    with pytest.raises(WorldCodeError, match="starts with"):
        _ = decode("ABC-" + body)
    with pytest.raises(WorldCodeError, match="characters"):
        _ = decode("RNW1-UUUU-U")


def test_unknown_presets_seeds_and_settings_are_refused_when_a_code_is_made() -> None:
    """Bad input never becomes a code."""
    with pytest.raises(WorldCodeError, match="Unknown preset"):
        _ = new_code("flat")
    with pytest.raises(WorldCodeError):
        _ = new_code("continents", -1)
    with pytest.raises(WorldCodeError):
        _ = new_code("continents", 1, {"new_world": {"land_permille": 5000}})
    with pytest.raises(WorldCodeError):
        _ = encode(WorldCode("continents", 1, "9999.0.0"))


def test_only_a_release_of_the_same_epoch_promises_the_same_world() -> None:
    """A code from before the epochs, or from another epoch, decodes but is not promised."""
    older = WorldCode("continents", 5, "0.1.2")
    assert decode(encode(older)).generator == "0.1.2"
    assert not reproduces(older)
    assert reproduces(new_code("continents", 5))
    first = ".".join(str(part) for part in epoch.ALGORITHM_SINCE[0])
    assert reproduces(WorldCode("continents", 5, first)) == (epoch.CURRENT == 1)
    assert not reproduces(WorldCode("continents", 5, "0.9.19"))


def test_random_seeds_differ_and_fit_64_bits() -> None:
    """The default seed is random and valid."""
    seeds = {worldcode.random_seed() for _ in range(20)}
    assert len(seeds) == 20
    assert all(0 <= seed < 1 << 64 for seed in seeds)


def test_changes_of_listed_fields_pack_into_a_short_compact_code() -> None:
    """Format 2 writes a number and a value per change; other changes keep format 1 JSON."""
    changes: dict[str, object] = {
        "new_world": {"land_permille": 600, "feature_px": 4000, "precious_permille": 3000},
        "natives": {"state_spread_permille": 450, "population_permille": 2500},
    }
    code = new_code("supercontinent", 42, changes)
    text = encode(code)
    assert decode(text) == code
    assert len(text) < 70
    assert worldcode.format_of(text) == worldcode.COMPACT
    other: dict[str, object] = {"coast": {"passes": 12}}
    legacy = new_code("continents", 42, other)
    assert worldcode.format_of(encode(legacy)) == worldcode.FORMAT
    assert decode(encode(legacy)) == legacy


def test_every_setting_of_the_new_world_and_its_peoples_has_a_field_number() -> None:
    """The append-only list names every field a world code can change."""
    names = [f"new_world.{item.name}" for item in fields(NewWorldSettings)]
    names += [f"natives.{item.name}" for item in fields(NativeSettings)]
    assert set(names) <= set(worldcode.CHANGE_FIELDS)
    assert len(set(worldcode.CHANGE_FIELDS)) == len(worldcode.CHANGE_FIELDS)
    assert len(worldcode.CHANGE_FIELDS) < 256
