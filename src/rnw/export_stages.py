"""The stages of an export, by what a world makes."""

from __future__ import annotations

from typing import Final

# What a world makes of generated geography, which this export never does: the estimate of the
# time left and the bar count these stages as done.
SKIPPED: Final[tuple[str, ...]] = (
    "generate world",
    "vanilla reads",
    "vanilla geometry",
    "vanilla localization keys",
    "vanilla climate",
    "vanilla material levels",
    "settle coasts",
    "water shapes",
    "water textures",
    "biomes and rivers",
    "identities",
    "world checks",
    "slot tables",
    "location rasters",
    "png encoding",
    "terrain decals",
    "vegetation instances",
    "spline network",
    "selection cover",
)
