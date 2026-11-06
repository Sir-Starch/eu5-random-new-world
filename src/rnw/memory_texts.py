"""The static texts and identifiers of the memory events (``eu5_memories``), free of imports so
that ``game_texts`` can gather them."""

from __future__ import annotations

from typing import Final

NAMESPACE: Final[str] = "rnw_memory"
EVENT_FILE: Final[str] = f"in_game/events/{NAMESPACE}.txt"
LOST_LAND: Final[str] = "lost_land"
OLD_PACT: Final[str] = "old_pact"
KIN: Final[str] = "kin"
SHRINE: Final[str] = "shrine"
HEIR: Final[str] = "heir"
FAMILIES: Final[tuple[str, ...]] = (LOST_LAND, OLD_PACT, KIN, SHRINE, HEIR)
FIRST_YEAR: Final[int] = 1338
SPREAD: Final[int] = 40
WINDOW: Final[int] = 40
CHANCES: Final[tuple[int, ...]] = (2, 3, 4)
RECOGNIZED: Final[str] = "opinion_good_relations"
REFUSED: Final[str] = "opinion_refused_claim"
VALUES: Final[tuple[str, ...]] = (
    "prestige_weak_bonus",
    "prestige_weak_penalty",
    "stability_weak_bonus",
)
BIASES_DIR: Final[str] = "game/in_game/common/biases"
VALUES_DIR: Final[str] = "game/main_menu/common/script_values"

# The English sources of every static text, by key (``game_texts.sources`` gathers them).
TEXTS: Final[dict[str, str]] = {
    f"{NAMESPACE}.{LOST_LAND}.title": "The Loss of [target_location.GetNameWithNoTooltip]",
    f"{NAMESPACE}.{LOST_LAND}.desc": (
        "Our elders still name the fields of [target_location.GetNameWithNoTooltip] as ours, "
        "though [partner.GetNameWithNoTooltip] took them from our grandfathers. The young ask "
        "whether that loss must stand for ever."
    ),
    f"{NAMESPACE}.{LOST_LAND}.a": "What was ours will be ours again.",
    f"{NAMESPACE}.{LOST_LAND}.b": "Let the old wound close.",
    f"{NAMESPACE}.{OLD_PACT}.title": "The Old Pact",
    f"{NAMESPACE}.{OLD_PACT}.desc": (
        "Our people and [partner.GetNameWithNoTooltip] once swore to stand together, and kept "
        "their word. Its envoys have come to ask whether the old promise still binds us."
    ),
    f"{NAMESPACE}.{OLD_PACT}.a": "The old promise binds us still.",
    f"{NAMESPACE}.{OLD_PACT}.b": "That promise was our grandfathers', not ours.",
    f"{NAMESPACE}.{KIN}.title": "Kin Across the Border",
    f"{NAMESPACE}.{KIN}.desc": (
        "Families of our people moved long ago between our land and "
        "[partner.GetNameWithNoTooltip], and settled at [target_location.GetNameWithNoTooltip]. "
        "Their children still remember each other, and ask that the road between them stay open."
    ),
    f"{NAMESPACE}.{KIN}.a": "Our gates are open to our kin.",
    f"{NAMESPACE}.{KIN}.b": "They chose another land; let them keep it.",
    f"{NAMESPACE}.{SHRINE}.title": "Pilgrims to [target_location.GetNameWithNoTooltip]",
    f"{NAMESPACE}.{SHRINE}.desc": (
        "For generations our pilgrims have walked to the shrine of "
        "[target_location.GetNameWithNoTooltip], under the peace that "
        "[partner.GetNameWithNoTooltip] grants them. Some of our priests now say that a holy "
        "place should not belong to strangers."
    ),
    f"{NAMESPACE}.{SHRINE}.a": "Honour the peace of the shrine.",
    f"{NAMESPACE}.{SHRINE}.b": "The shrine should be ours.",
    f"{NAMESPACE}.{HEIR}.title": "The Memory of the Old Realm",
    f"{NAMESPACE}.{HEIR}.desc": (
        "Our chroniclers recall the days when our land was one with its neighbours under a "
        "single crown, seated at [target_location.GetNameWithNoTooltip]. That realm is gone, but "
        "it is not forgotten, and whoever gathers enough of its old land may raise it again."
    ),
    f"{NAMESPACE}.{HEIR}.a": "We will raise the old realm again.",
    f"{NAMESPACE}.{HEIR}.b": "The old realm is gone; let it rest.",
}
