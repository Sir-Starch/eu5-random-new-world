"""Random world types: *Random* draws one of the world types, *Total Chaos* also draws every
Advanced setting within its playable range.

Both are choices of the window, not world types of their own. A draw is made when the player
chooses the type and again with each press of the random button, and what it gives is an
ordinary world of the type drawn, with the values drawn as changes: the world's code, name and
library record carry them, so the world reproduces like any other. A draw is kept inside the
location budget, which every window choice must keep to; the slider's own scale draws each value,
so a value is as likely as any other position on its slider.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Final

from rnw.app import controls
from rnw.settings import WORLD_TYPES, build_settings

if TYPE_CHECKING:
    import random

RANDOM: Final[str] = "random"
CHAOS: Final[str] = "chaos"
MODES: Final[tuple[str, ...]] = (RANDOM, CHAOS)
# The window's list: the two draws first, then the world types in their own order.
CHOICES: Final[tuple[str, ...]] = (*MODES, *WORLD_TYPES)
# Measured on every world type, about one draw in seven goes over the location budget (C118
# estimate); the bound is only a guard, so a draw that is refused every time fails loudly.
ATTEMPTS: Final[int] = 1000


def draw(mode: str, rng: random.Random | None = None) -> tuple[str, dict[str, int]]:
    """A world type and the changes of its controls that ``mode`` draws; the changes are the
    values that differ from the type's own, as the window keeps them."""
    source = rng if rng is not None else secrets.SystemRandom()
    preset = source.choice(WORLD_TYPES)
    if mode == CHAOS:
        return preset, _advanced_changes(preset, source)
    if mode == RANDOM:
        return preset, {}
    message = f"Unknown random world type: {mode!r}"
    raise ValueError(message)


def _advanced_changes(preset: str, rng: random.Random) -> dict[str, int]:
    for _ in range(ATTEMPTS):
        values = {
            control.key: control.value_at(rng.randint(0, controls.STEPS))
            for control in controls.ADVANCED
            if control.group != "wall" or preset == "wall"
        }
        settings = build_settings(preset, controls.nested(values))
        if controls.estimated_locations(settings) <= controls.LOCATION_BUDGET:
            return {
                key: number
                for key, number in values.items()
                if number != controls.BY_KEY[key].default(preset)
            }
    message = f"No Advanced draw for {preset} fits the location budget in {ATTEMPTS} tries"
    raise RuntimeError(message)
