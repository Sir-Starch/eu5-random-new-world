"""The parts of a world and the seed of each (ADR 0010, A).

A world has three parts, each drawn from its own seed so that one can be made again while the
others stay as they were:

* **land**: the shape, relief, climate, rivers, biomes and vegetation, the locations, areas and
  regions; its seed is the world's seed;
* **resources**: the raw material of every location, gold and silver;
* **peoples**: societies, cultures, religions, countries, their names, and the start state that
  follows from them.

Resources and peoples read the land and never the other way round, and do not read each other
(``rnw.eu5_biomes`` draws the materials from the land's biomes; ``rnw.eu5_natives`` the peoples).
A part has a *roll*, a counter in the settings (``Settings.rolls``): at 0 its seed is the world's
own, so every world made before rolls exist is unchanged; at ``n`` it is a seed derived from the
world's and ``n``. The land is changed by a new seed, which starts every roll again at 0.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import TYPE_CHECKING, Final, cast

from rnw.rng import derive_seed

if TYPE_CHECKING:
    from rnw.settings import Settings

RESOURCES: Final[str] = "resources"
PEOPLES: Final[str] = "peoples"
PARTS: Final[tuple[str, ...]] = (RESOURCES, PEOPLES)
LAND_KEY_LENGTH: Final[int] = 10


def layer_seed(seed: int, part: str, roll: int) -> int:
    """The seed a part is drawn from: the world's own at roll 0, a derived one after."""
    if part not in PARTS:
        message = f"Unknown part {part!r}; choose one of {', '.join(PARTS)}"
        raise ValueError(message)
    if roll < 0:
        message = f"A roll counts from 0, not {roll}"
        raise ValueError(message)
    return seed if roll == 0 else derive_seed(seed, "roll", part, str(roll))


def rolls_of(settings: Settings) -> dict[str, int]:
    """The roll of each part."""
    return {RESOURCES: settings.rolls.resources, PEOPLES: settings.rolls.peoples}


def land_key(settings: Settings, seed: int) -> str:
    """Names the land of a world: its seed and the settings that shape it.

    Worlds that differ only in their peoples or resources, their rolls or the settings of
    those, have the same key and are shown together as versions of one continent. Of the New
    World's settings only the share of precious metals belongs to the resources.
    """
    shape = cast("dict[str, object]", asdict(settings.new_world))
    _ = shape.pop("precious_permille")
    text = repr((seed, settings.mask.id, sorted(shape.items())))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:LAND_KEY_LENGTH]
