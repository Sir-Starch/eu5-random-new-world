"""The settings a player may change in the window, within the ranges that make a playable map.

Each control is one integer field of the settings (``rnw.settings``), shown in the unit a
player reads (per cent, a multiple, pixels, a count; the window names the unit). Its range
is what still makes a map EU5 plays well: odd shapes, a sea of islets or scarce gold are a
player's right, a world the generator cannot finish or the game cannot load is not. The
ranges were set from the presets, measured land shapes and exports at their edges (C118);
the one combination they cannot bound alone, the number of locations, is estimated by
``estimated_locations`` and checked before a world is made. Changes are kept as the
difference from the world type and travel in the world code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, cast

from rnw.settings import PRESETS, Settings

STEPS: Final[int] = 1000
# Locations of a world, estimated from its settings (C118): those outside the New World on
# build 26043558, land cells per land share over the location area, sea zones per water
# share over the zone area, and a margin for lakes. The engine refuses more than about
# 32,000 (C84); the window keeps the estimate below LOCATION_BUDGET.
OUTSIDE_LOCATIONS: Final[int] = 21_975
LAND_CELLS: Final[int] = 37_500
SEA_ZONES: Final[int] = 41_000
LAKES: Final[int] = 100
LOCATION_BUDGET: Final[int] = 31_200


@dataclass(frozen=True, slots=True)
class Control:
    """One setting: where it lives, its playable range and how a slider maps onto it."""

    key: str
    group: str
    low: int
    high: int
    logarithmic: bool = False
    factor: int = 1
    decimals: int = 0
    unit: str = ""

    @property
    def section(self) -> str:
        """The settings section: ``new_world`` or ``natives``."""
        return self.key.split(".", 1)[0]

    @property
    def field(self) -> str:
        """The field inside the section."""
        return self.key.split(".", 1)[1]

    def default(self, preset: str) -> int:
        """The value of the world type ``preset``."""
        section = cast("object", getattr(PRESETS[preset], self.section))
        return cast("int", getattr(section, self.field))

    def allows(self, value: int) -> bool:
        """Whether ``value`` lies in the playable range."""
        return self.low <= value <= self.high

    def position(self, value: int) -> int:
        """Where ``value`` sits on a slider of ``STEPS``."""
        value = min(self.high, max(self.low, value))
        if self.logarithmic:
            span = math.log(self.high) - math.log(self.low)
            return round(STEPS * (math.log(value) - math.log(self.low)) / span)
        return round(STEPS * (value - self.low) / (self.high - self.low))

    def value_at(self, position: int) -> int:
        """The value at ``position`` of a slider of ``STEPS``."""
        share = min(STEPS, max(0, position)) / STEPS
        if self.logarithmic:
            value = math.exp(
                math.log(self.low) + share * (math.log(self.high) - math.log(self.low))
            )
        else:
            value = self.low + share * (self.high - self.low)
        return min(self.high, max(self.low, round(value)))

    def shown(self, value: int) -> float:
        """``value`` in the unit the window shows."""
        return value / self.factor

    def stored(self, shown: float) -> int:
        """The setting for a value typed in the window's unit, kept in range."""
        return min(self.high, max(self.low, round(shown * self.factor)))


CONTROLS: Final[tuple[Control, ...]] = (
    Control("new_world.land_permille", "land", 150, 600, factor=10, decimals=1, unit="percent"),
    Control("new_world.feature_px", "land", 250, 4000, logarithmic=True, unit="px"),
    Control("new_world.min_island_px", "land", 100, 8000, logarithmic=True, unit="px"),
    Control("new_world.persistence_permille", "land", 400, 650, factor=1000, decimals=2),
    Control("new_world.octaves", "land", 5, 8),
    Control("new_world.max_lake_px", "land", 1000, 20_000, logarithmic=True, unit="px"),
    Control("new_world.wasteland_permille", "land", 0, 200, factor=10, decimals=1, unit="percent"),
    Control("new_world.precious_permille", "land", 0, 3000, factor=1000, decimals=2, unit="times"),
    Control("new_world.location_px", "map", 40, 90, unit="px"),
    Control("new_world.sea_zone_px", "map", 80, 240, unit="px"),
    Control("new_world.province_size", "map", 3, 10),
    Control(
        "natives.population_permille", "peoples", 250, 3000, factor=1000, decimals=2, unit="times"
    ),
    Control(
        "natives.state_share_permille", "peoples", 30, 300, factor=10, decimals=1, unit="percent"
    ),
    Control(
        "natives.state_spread_permille", "peoples", 0, 600, factor=10, decimals=1, unit="percent"
    ),
    Control("natives.state_locations", "peoples", 2, 10),
    Control(
        "natives.organized_permille", "peoples", 200, 800, factor=10, decimals=1, unit="percent"
    ),
    Control("natives.hearths_per_10k", "peoples", 2, 12),
    Control("natives.culture_locations", "peoples", 5, 40),
    Control("natives.religion_locations", "peoples", 20, 200, logarithmic=True),
    Control("natives.tribe_locations", "peoples", 4, 15),
)
BY_KEY: Final[dict[str, Control]] = {control.key: control for control in CONTROLS}
GROUPS: Final[tuple[str, ...]] = ("land", "map", "peoples")


def estimated_locations(settings: Settings) -> int:
    """Locations the world of ``settings`` will have, roughly (within about 600, C118)."""
    world = settings.new_world
    land = LAND_CELLS * world.land_permille // (world.location_px * world.location_px)
    water = 1000 - world.land_permille
    sea = SEA_ZONES * water // (world.sea_zone_px * world.sea_zone_px)
    return OUTSIDE_LOCATIONS + land + sea + LAKES


def nested(changes: dict[str, int]) -> dict[str, object] | None:
    """Flat ``section.field`` changes as the settings override document; None if none."""
    document: dict[str, dict[str, int]] = {}
    for key, value in sorted(changes.items()):
        section, field = key.split(".", 1)
        document.setdefault(section, {})[field] = value
    return cast("dict[str, object]", document) or None


def flat(document: dict[str, object] | None) -> tuple[dict[str, int], dict[str, object]]:
    """A world code's changes as controls this window shows, and the rest it keeps as they are."""
    shown: dict[str, int] = {}
    other: dict[str, object] = {}
    for section, fields in (document or {}).items():
        if not isinstance(fields, dict):
            other[section] = fields
            continue
        for field, value in cast("dict[str, object]", fields).items():
            key = f"{section}.{field}"
            if key in BY_KEY and isinstance(value, int) and not isinstance(value, bool):
                shown[key] = value
            else:
                section_other = cast("dict[str, object]", other.setdefault(section, {}))
                section_other[field] = value
    return shown, other
