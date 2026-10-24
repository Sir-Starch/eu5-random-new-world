"""Random world types: Random draws a world type, Total Chaos also its Advanced values."""

from __future__ import annotations

import random

import pytest

from rnw.app import controls, random_types
from rnw.app.worldcode import decode, encode, new_code
from rnw.settings import WORLD_TYPES, build_settings

DRAWS = range(200)


def _rng(seed: int) -> random.Random:
    return random.Random(seed)  # noqa: S311 - a fixed test draw, not a secret


def test_the_window_offers_both_draws_before_the_world_types() -> None:
    """The list starts with the two draws, then the five world types in their own order."""
    assert (*random_types.MODES, *WORLD_TYPES) == random_types.CHOICES
    assert random_types.MODES == ("random", "chaos")


@pytest.mark.parametrize("seed", DRAWS)
def test_random_draws_one_world_type_and_keeps_its_own_values(seed: int) -> None:
    """Random is one of the five types, with none of the type's values changed."""
    preset, changes = random_types.draw(random_types.RANDOM, _rng(seed))
    assert preset in WORLD_TYPES
    assert changes == {}


@pytest.mark.parametrize("seed", DRAWS)
def test_total_chaos_draws_every_advanced_value_inside_its_range_and_budget(seed: int) -> None:
    """Each Advanced control gets a value of its playable range, the world stays within the
    location budget, and a value equal to the type's own is not kept as a change."""
    preset, changes = random_types.draw(random_types.CHAOS, _rng(seed))
    assert preset in WORLD_TYPES
    advanced = {control.key: control for control in controls.ADVANCED}
    assert set(changes) <= set(advanced)
    for key, number in changes.items():
        assert advanced[key].allows(number), key
        assert number != advanced[key].default(preset), key
    settings = build_settings(preset, controls.nested(changes))
    assert controls.estimated_locations(settings) <= controls.LOCATION_BUDGET


def test_total_chaos_reaches_every_advanced_control_and_never_the_ocean_checkbox() -> None:
    """Over many draws each Advanced control moves; the ocean checkbox is not one of them."""
    moved: set[str] = set()
    for seed in range(300):
        _, changes = random_types.draw(random_types.CHAOS, _rng(seed))
        moved |= set(changes)
    assert moved == {control.key for control in controls.ADVANCED}
    assert "new_world.expand_oceans" not in moved


def test_a_drawn_world_reproduces_from_its_code() -> None:
    """The drawn type and values are an ordinary world: their code brings them back."""
    preset, changes = random_types.draw(random_types.CHAOS, _rng(7))
    code = encode(new_code(preset, 12345, controls.nested(changes)))
    again = decode(code)
    assert again.preset == preset
    shown, other = controls.flat(again.resolved_changes())
    assert shown == changes
    assert other == {}


def test_an_unknown_mode_is_refused() -> None:
    """A mode is one of the two draws; anything else is a bug and says so."""
    with pytest.raises(ValueError, match="Unknown random world type"):
        _ = random_types.draw("lottery", _rng(0))
