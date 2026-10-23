"""The files of the formables of one world: the territory, the tag, the flag and the words (N3, N4).

``content`` decides which territories exist and to whom they are offered (``Formation``);
``formations`` holds what each family is (``Spec``). This module turns the two into the world's
mod, in the manner of the vanilla formable-only tag ``ADU`` (C175): a formable entry of a tag that
no country file defines, with a flag definition, a coat of arms, a named colour and name and
adjective keys, and no country in 1337. The founding modifier copies the payload of a vanilla
modifier under a name of the mod's own (``eu5_story.payload``).

A rank or an emblem that the installation does not have stops the export (``FormationError``)
instead of being replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_empires import rank_levels
from rnw.eu5_natives import hsv_rgb
from rnw.formations import BY_FAMILY, Spec
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from rnw.content import Formation

FORMABLES_FILE: Final[str] = "in_game/common/formable_countries/rnw_formations.txt"
FLAGS_FILE: Final[str] = "main_menu/common/flag_definitions/rnw_formations.txt"
ARMS_FILE: Final[str] = "main_menu/common/coat_of_arms/coat_of_arms/rnw_formations.txt"
COLORS_FILE: Final[str] = "main_menu/common/named_colors/rnw_formations.txt"
RANKS_DIR: Final[str] = "game/in_game/common/country_ranks"
EMBLEM_DIR: Final[str] = "game/main_menu/gfx/coat_of_arms/colored_emblems"
PATTERN_DIR: Final[str] = "game/main_menu/gfx/coat_of_arms/patterns"
ARMS_PATTERN: Final[str] = "pattern_solid.dds"
# Colours of the vanilla coat of arms of ``ADU``; a formation takes two distinct ones of these.
ARMS_COLOURS: Final[tuple[str, ...]] = ("green", "white", "red", "blue", "yellow", "black")


class FormationError(ValueError):
    """A rank or an emblem that the formables lean on is gone from the installation."""


@dataclass(frozen=True, slots=True)
class Identity:
    """What a formation needs of the world besides its places: a tag, a name, a colour."""

    tag: str
    name: str
    adjective: str
    colour: tuple[int, int, int]
    colours: tuple[str, str]


def key_of(formation: Formation) -> str:
    """The key of a formation's formable, which names it in the formables list and its text."""
    return f"rnw_{BY_FAMILY[formation.family].stem}_{formation.index + 1}_f"


def check_installation(game_dir: Path, specs: Sequence[Spec]) -> None:
    """Raise unless every rank and emblem of ``specs`` is in the installation, as written."""
    levels = rank_levels(
        [
            path.read_text(encoding="utf-8-sig")
            for path in sorted((game_dir / RANKS_DIR).glob("*.txt"))
        ]
    )
    for spec in specs:
        if levels.get(spec.rank) != spec.level:
            message = f"The rank {spec.rank} of {spec.family} is not level {spec.level} in the game"
            raise FormationError(message)
        for directory, name in ((EMBLEM_DIR, spec.emblem), (PATTERN_DIR, ARMS_PATTERN)):
            if not (game_dir / directory / name).is_file():
                message = f"The picture {name} of {spec.family} is gone from the installation"
                raise FormationError(message)


def block(formation: Formation, identity: Identity) -> str:
    """The formable of one formation: a tag the game does not define, as ``ADU`` is."""
    spec = BY_FAMILY[formation.family]
    owners = "\n".join(f"\t\t\ttag = {tag}" for tag in formation.states)
    places = "\n".join(f"\t\t{key}" for key in formation.places)
    allow = "".join(f"\t\t{line}\n" for line in spec.allow)
    return (
        f"{key_of(formation)} = {{\n"
        f"\tlevel = {spec.level}\n"
        f"\trequired_locations_fraction = {spec.fraction}\n"
        "\trule = plausible\n"
        "\tcapital_required = yes\n\n"
        f"\tpotential = {{\n\t\tOR = {{\n{owners}\n\t\t}}\n\t}}\n\n"
        f"\tallow = {{\n{allow}\t}}\n\n"
        f"\tname = {identity.tag}\n"
        f"\tflag = {identity.tag}\n"
        f"\tadjective = {identity.tag}_ADJ\n"
        f"\ttag = {identity.tag}\n"
        f"\tcolor = map_{identity.tag}\n\n"
        f"\tlocations = {{\n{places}\n\t}}\n"
        "\tform_effect = {\n"
        f"\t\tif = {{\n\t\t\tlimit = {{ country_rank_level < {spec.level} }}\n"
        f"\t\t\tset_country_rank_effect = {{ rank = country_rank:{spec.rank} }}\n\t\t}}\n"
        "\t\tadd_country_modifier = {\n"
        f"\t\t\tmodifier = {spec.modifier.name}\n"
        f"\t\t\tyears = {spec.years}\n"
        "\t\t\tmode = add\n\t\t}\n"
        "\t}\n"
        "}\n"
    )


def files(formations: Sequence[Formation], identities: Sequence[Identity]) -> dict[str, str]:
    """The script files of the formations: formables, flags, coats of arms and colours."""
    pairs = list(zip(formations, identities, strict=True))
    formables = "\n".join(block(formation, identity) for formation, identity in pairs)
    flags = "\n".join(
        f"{i.tag} = {{\n\tflag_definition = {{\n\t\tcoa = {i.tag}\n\t\tpriority = 1\n\t}}\n}}\n"
        for _, i in pairs
    )
    arms = "\n".join(
        (
            f"{i.tag} = {{\n"
            f'\tpattern = "{ARMS_PATTERN}"\n'
            f'\tcolor1 = "{i.colours[0]}"\n'
            f'\tcolor2 = "{i.colours[1]}"\n\n'
            "\tcolored_emblem = {\n"
            f'\t\ttexture = "{BY_FAMILY[f.family].emblem}"\n'
            "\t\tcolor1 = color1\n\t\tcolor2 = color2\n\t}\n}\n"
        )
        for f, i in pairs
    )
    colours = (
        "colors = {\n"
        + "".join(
            f"\tmap_{i.tag} = rgb {{ {i.colour[0]} {i.colour[1]} {i.colour[2]} }}\n"
            for _, i in pairs
        )
        + "}\n"
    )
    return {FORMABLES_FILE: formables, FLAGS_FILE: flags, ARMS_FILE: arms, COLORS_FILE: colours}


def identities(
    formations: Sequence[Formation],
    names: Mapping[str, str],
    tags: Sequence[str],
    seed: int,
    taken: frozenset[tuple[int, int, int]],
) -> list[Identity]:
    """A tag, a name, a map colour and two heraldic colours for each formation."""
    found: list[Identity] = []
    used = set(taken)
    for formation, tag in zip(formations, tags, strict=True):
        seat = names.get(formation.seat, formation.seat)
        draw = derive_seed(seed, "content", "union", tag)
        colour = (0, 0, 0)
        for step in range(360):
            hue = (draw + step * 7) % 360
            colour = hsv_rgb(hue, 550 + (draw >> 12) % 300, 550 + (draw >> 24) % 300)
            if colour not in used:
                break
        used.add(colour)
        count = len(ARMS_COLOURS)
        first = (draw >> 8) % count
        second = (first + 1 + (draw >> 16) % (count - 1)) % count
        suffix = BY_FAMILY[formation.family].suffix
        found.append(
            Identity(
                tag, f"{seat} {suffix}", seat, colour, (ARMS_COLOURS[first], ARMS_COLOURS[second])
            )
        )
    return found


def texts(formations: Sequence[Formation], identities_of: Sequence[Identity]) -> dict[str, str]:
    """The localization of the formations: names, adjectives, formable keys and descriptions."""
    found: dict[str, str] = {}
    for formation, identity in zip(formations, identities_of, strict=True):
        spec = BY_FAMILY[formation.family]
        key = key_of(formation)
        found[identity.tag] = identity.name
        found[f"{identity.tag}_ADJ"] = identity.adjective
        # The formables list asks for the formable's own key (vanilla: ``SWI_f: "$SWI$"``);
        # without it the game shows the key and logs it as a missing localization.
        found[key] = f"${identity.tag}$"
        found[f"{key}_desc"] = spec.description.format(name=identity.name)
    return found
