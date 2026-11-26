"""Quick settings: a few questions a player answers in a word, over the window's controls.

EU4's random New World asked the player little: whether its fantasy empires were never,
seldom, sometimes or often, and whether it showed in the lobby. Here a question is a quick
setting (how much land, how many peoples, how many great empires) and each answer is a
level: a value for every control it touches, either the world type's own value times a
factor (the land of a supercontinent is not the land of an archipelago) or a fixed value.
A level adds nothing to the settings or to the world code: choosing one sets the controls,
and the quick setting shows the level whose values the controls hold now, or none when the
player moved a slider in between (custom).

Every continent has the same questions. America's levels start from its world type; another
continent's start from its own resolved defaults (``RegionalSettings`` of its type, whose
state share is the continent's own) and keep to the ranges its controls play in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.app import controls
from rnw.epoch import CURRENT

if TYPE_CHECKING:
    from rnw.settings import RegionalSettings

PERMILLE: Final[int] = 1000


@dataclass(frozen=True, slots=True)
class Part:
    """One control a level sets: the world type's value times ``scale``, or ``fixed``."""

    key: str
    scale: int = PERMILLE
    fixed: int | None = None

    def value(
        self,
        preset: str,
        defaults: RegionalSettings | None = None,
        *,
        algorithm: int = CURRENT,
        composed: bool = False,
    ) -> int:
        """The control's value for ``preset``, kept in the control's playable range; for another
        continent than America, ``defaults`` are the values of its own type."""
        if defaults is None:
            control = controls.BY_KEY[self.key]
            base = control.default(preset, algorithm=algorithm, composed=composed)
        else:
            control = controls.REGION_BY_KEY[self.key]
            base = controls.region_value(control, defaults)
        number = self.fixed if self.fixed is not None else base * self.scale // PERMILLE
        return min(control.high, max(control.low, number))


@dataclass(frozen=True, slots=True)
class Level:
    """One answer: a name and what it sets."""

    name: str
    parts: tuple[Part, ...]

    def values(
        self,
        preset: str,
        defaults: RegionalSettings | None = None,
        *,
        algorithm: int = CURRENT,
        composed: bool = False,
    ) -> dict[str, int]:
        """Control key -> value of this level for ``preset`` (a continent's ``defaults``)."""
        return {
            part.key: part.value(preset, defaults, algorithm=algorithm, composed=composed)
            for part in self.parts
        }


@dataclass(frozen=True, slots=True)
class Quick:
    """One question and its levels, in the order the window shows them."""

    name: str
    levels: tuple[Level, ...]

    def level(self, name: str) -> Level:
        """The level called ``name``."""
        return next(level for level in self.levels if level.name == name)

    def touched(self) -> frozenset[str]:
        """The controls any level of this question sets."""
        return frozenset(part.key for level in self.levels for part in level.parts)

    def current(
        self,
        preset: str,
        values: dict[str, int],
        defaults: RegionalSettings | None = None,
        *,
        algorithm: int = CURRENT,
        composed: bool = False,
    ) -> str | None:
        """The level whose values every touched control holds in ``values``; None: custom."""
        for level in self.levels:
            if all(
                values.get(key) == number
                for key, number in level.values(
                    preset, defaults, algorithm=algorithm, composed=composed
                ).items()
            ):
                return level.name
        return None


def _scaled(key: str, *scales: tuple[str, int]) -> tuple[Level, ...]:
    return tuple(Level(name, (Part(key, scale),)) for name, scale in scales)


QUICK: Final[tuple[Quick, ...]] = (
    Quick(
        "land",
        tuple(
            Level(
                name,
                (Part("new_world.land_permille", land), Part("new_world.location_px", size)),
            )
            for name, land, size in (
                ("little", 750, 1000),
                ("normal", 1000, 1000),
                # More land in locations of the same size would pass the engine's cap of
                # about 32,000 locations, so the locations grow with the square root of it.
                ("much", 1250, 1118),
            )
        ),
    ),
    Quick(
        "peoples",
        tuple(
            Level(
                name,
                (
                    Part("natives.population_permille", people),
                    Part("natives.hearths_per_10k", hearths),
                ),
            )
            for name, people, hearths in (
                ("few", 500, 500),
                ("normal", 1000, 1000),
                ("many", 1800, 1500),
            )
        ),
    ),
    Quick(
        "states",
        _scaled("natives.state_share_permille", ("few", 500), ("normal", 1000), ("many", 4000)),
    ),
    Quick(
        "empires",
        tuple(
            Level(name, (Part("natives.empire_permille", fixed=number),))
            for name, number in (
                ("never", 0),
                ("seldom", 250),
                ("sometimes", 500),
                ("often", 800),
            )
        ),
    ),
    Quick(
        "turbulence",
        tuple(
            Level(name, (Part("natives.turbulence_permille", fixed=number),))
            for name, number in (("calm", 200), ("varied", 500), ("turbulent", 800))
        ),
    ),
    Quick(
        "wealth",
        _scaled("new_world.precious_permille", ("scarce", 350), ("normal", 1000), ("rich", 2000)),
    ),
)
BY_NAME: Final[dict[str, Quick]] = {quick.name: quick for quick in QUICK}
