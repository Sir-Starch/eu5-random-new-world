"""The societal values EU5 shows, by name: the axes a society profile is projected onto.

Only names and the table of which trait feeds which value, so the window can read a world
without the code that reads the game (``eu5_history_values`` projects and checks them).
"""

from __future__ import annotations

from typing import Final

CENTRAL: Final[str] = "centralization_vs_decentralization"
TRADITION: Final[str] = "traditionalist_vs_innovative"
SPIRITUAL: Final[str] = "spiritualist_vs_humanist"
MYSTICISM: Final[str] = "mysticism_vs_jurisprudence"
POSTURE: Final[str] = "offensive_vs_defensive"
BELLIGERENCE: Final[str] = "belligerent_vs_conciliatory"
QUALITY: Final[str] = "quality_vs_quantity"
EXCHANGE: Final[str] = "land_vs_naval"
AXES: Final[tuple[str, ...]] = (
    CENTRAL,
    TRADITION,
    SPIRITUAL,
    MYSTICISM,
    POSTURE,
    BELLIGERENCE,
    QUALITY,
    EXCHANGE,
)
# The society trait each value is projected from (``profile_positions`` below): what the window
# names as the cause of a value, and which traits it need not show a second time.
SOURCE: Final[dict[str, str]] = {
    CENTRAL: "centralization",
    TRADITION: "tradition",
    SPIRITUAL: "religious_authority",
    MYSTICISM: "religious_authority",
    POSTURE: "military",
    BELLIGERENCE: "military",
    QUALITY: "military",
    EXCHANGE: "exchange",
}
BOUND: Final[int] = 100
# The societal values the game shows a generated country in the age of traditions, in the order
# of its own list (``in_game/common/societal_values/00_default.txt``, [V-LOCAL] EU5 1.4.7, Steam
# build 26377361): the file's order without the values an age opens later (mercantilism and free
# trade, outward and inward) and those a modifier or a country opens (sinicized, absolutism,
# mysticism, latinization).
# The owner's screenshot of 2026-11-08 shows these eleven in this order. The export checks the
# order against the installation (``eu5_history_values.check_shown``).
SHOWN: Final[tuple[str, ...]] = (
    CENTRAL,
    TRADITION,
    SPIRITUAL,
    "aristocracy_vs_plutocracy",
    "serfdom_vs_free_subjects",
    BELLIGERENCE,
    QUALITY,
    POSTURE,
    EXCHANGE,
    "capital_economy_vs_traditional_economy",
    "individualism_vs_communalism",
)


def poles(axis: str) -> tuple[str, str]:
    """The game's identifiers of an axis's left and right poles (``traditionalist_focus``...)."""
    left, right = axis.split("_vs_")
    return f"{left}_focus", f"{right}_focus"
