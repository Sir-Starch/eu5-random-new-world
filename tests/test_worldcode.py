"""World codes: round trip, forgiving input, damage detection, version promise."""

from __future__ import annotations

import pytest

from rnw import __version__
from rnw.app import worldcode
from rnw.app.worldcode import WorldCode, WorldCodeError, decode, encode, new_code, reproduces


def test_a_default_world_is_a_short_code_that_round_trips() -> None:
    """Preset, seed and generator survive, and a default world needs 28 characters."""
    code = new_code("continents", 319218363)
    text = encode(code)
    assert text.startswith("RNW1-")
    assert len(text.replace("-", "")) == len("RNW1") + 28
    assert decode(text) == code
    assert code.generator == __version__


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


def test_only_the_same_generator_version_promises_the_same_world() -> None:
    """A code from another version decodes, but is not promised to reproduce its world."""
    older = WorldCode("continents", 5, "0.1.2")
    assert decode(encode(older)).generator == "0.1.2"
    assert not reproduces(older)
    assert reproduces(new_code("continents", 5))


def test_random_seeds_differ_and_fit_64_bits() -> None:
    """The default seed is random and valid."""
    seeds = {worldcode.random_seed() for _ in range(20)}
    assert len(seeds) == 20
    assert all(0 <= seed < 1 << 64 for seed in seeds)
