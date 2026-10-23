"""The colonial names of a generated New World: ``scripted_country_names`` for the regions it has.

Vanilla names a colony after its founder and its land through ``scripted_country_names``: a name,
a trigger on the colony's country (its overlord's language), a trigger on its capital (where it
stands). The eight vanilla names name the real Americas (New Spain, New York and others) and are
closed on generated land by N1; this module writes the generated world's own, in the same format.

For each region of the generated land and each founder's naming tradition one entry makes a
colony whose overlord speaks that language, with its capital in that region, *the New X* of the
tradition, where X is the generated name of the region (a local root, as *New Granada* and *New
Mexico* took theirs). A tradition is a template of its language, not an inflection engine: the
region's name is put after the word for *new* and left as it is.

Whether the game applies a scripted name to a colony made by its own colonization is observed only
for the effect the probe used (it did not, C207, C210); the entries are in the vanilla format and
cost nothing where the game does not use them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

NAMES_FILE: Final[str] = "in_game/common/scripted_country_names/rnw_colonial_names.txt"
LANGUAGES_DIR: Final[str] = "game/in_game/common/languages"
GROUPS_DIR: Final[str] = "game/in_game/common/culture_groups"


class ColonialNameError(ValueError):
    """A language or a culture group that a tradition leans on is gone from the installation."""


@dataclass(frozen=True, slots=True)
class Tradition:
    """How the colonies of one founder's people are named: its trigger and its word for *new*."""

    name: str
    pattern: str
    founder: str
    needs: str


_GROUP: Final[str] = "culture_group:netherlandish_group"
DUTCH: Final[str] = f"any_primary_or_accepted_culture = {{ has_culture_group = {_GROUP} }}"
# ``founder`` is the trigger on the colony's overlord; ``needs`` the vanilla key it leans on.
TRADITIONS: Final[tuple[Tradition, ...]] = (
    Tradition(
        "spanish",
        "Nueva {root}",
        "culture.language = language:spanish_language",
        "spanish_language",
    ),
    Tradition(
        "portuguese",
        "Nova {root}",
        "culture.language = language:portuguese_language",
        "portuguese_language",
    ),
    Tradition(
        "english",
        "New {root}",
        "culture.language = language:english_language",
        "english_language",
    ),
    Tradition(
        "french",
        "Nouvelle-{root}",
        "culture.language = language:french_language",
        "french_language",
    ),
    Tradition(
        "dutch",
        "Nieuw-{root}",
        DUTCH,
        "netherlandish_group",
    ),
)


def entry_id(tradition: Tradition, region: str) -> str:
    """The identifier and localization key of the colonies of ``tradition`` in ``region``."""
    return f"rnw_{tradition.name}_{region}_scripted_country_name"


def check_installation(game_dir: Path) -> None:
    """Raise unless every language and culture group the traditions lean on is defined."""
    text = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for directory in (LANGUAGES_DIR, GROUPS_DIR)
        for path in sorted((game_dir / directory).glob("*.txt"))
    )
    defined = {line.split("=")[0].strip() for line in text.splitlines() if "=" in line}
    for tradition in TRADITIONS:
        if tradition.needs not in defined:
            message = f"{tradition.needs} of the {tradition.name} names is gone from the game"
            raise ColonialNameError(message)


def block(tradition: Tradition, region: str) -> str:
    """The scripted country name of one tradition in one region."""
    return (
        f"{entry_id(tradition, region)} = {{\n"
        f"\tcountry_trigger = {{\n\t\toverlord ?= {{ {tradition.founder} }}\n\t}}\n\n"
        f"\tcapital_trigger = {{\n\t\tregion = region:{region}\n\t}}\n\n"
        "\tlocation_trigger = {\n\t}\n"
        "}\n"
    )


def script(regions: Sequence[str]) -> str:
    """The file of the colonial names: every tradition in every region."""
    return "\n".join(
        block(tradition, region) for region in sorted(regions) for tradition in TRADITIONS
    )


def texts(regions: Mapping[str, str]) -> dict[str, str]:
    """The names and adjectives, by the key the game looks up (the adjective is the name)."""
    found: dict[str, str] = {}
    for region in sorted(regions):
        for tradition in TRADITIONS:
            name = tradition.pattern.format(root=regions[region])
            found[entry_id(tradition, region)] = name
            found[f"{entry_id(tradition, region)}_ADJ"] = name
    return found
