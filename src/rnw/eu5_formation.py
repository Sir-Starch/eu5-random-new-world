"""The files of the formables of one world: the territory, the tag, the flag and the words (N3, N4).

``content`` decides which territories exist and to whom they are offered (``Formation``);
``formations`` holds what each family is (``Spec``). This module turns the two into the world's
mod, in the manner of the vanilla formable-only tag ``ADU`` (C175): a formable entry of a tag that
no country file defines, with a flag definition, a coat of arms, a named colour and name and
adjective keys, and no country in 1337. The founding modifier copies the payload of a vanilla
modifier under a name of the mod's own (``eu5_story.payload``).

Who may form it is decided in play (history plan §22, N6): ``capital_required`` and vanilla's
``potential_requires_own`` keep the list to the holders of the territory; a commonwealth also asks
for its people's culture group from anyone but the states of 1337, the federation for settlers and
the empire for a court on its continent. A realm asks for its region's throne. A formation gives
cores on the locations of its territory that others hold (one tooltip line, the work hidden), so
that vanilla's ``cb_conquer_province`` (``casus_belli/conquest.txt``) opens against each holder.

A rank or an emblem that the installation does not have stops the export (``FormationError``)
instead of being replaced.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import wording
from rnw.colonial_names import TRADITIONS
from rnw.eu5_empires import rank_levels
from rnw.eu5_natives import hsv_rgb
from rnw.formations import (
    BY_FAMILY,
    CORES_TOOLTIP,
    EMPIRE_ADJECTIVE,
    EXTRA_TEXTS,
    HEIRS_TOOLTIP,
    RESTORATION_EVENT,
    Spec,
)
from rnw.game_texts import Described, Text, formation_description
from rnw.rng import derive_seed
from rnw.wording import Phrase

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from rnw.content import Formation
    from rnw.game_texts import Entry
    from rnw.wording import Name

FORMABLES_FILE: Final[str] = "in_game/common/formable_countries/rnw_formations.txt"
RESTORATION_FILE: Final[str] = f"in_game/events/{RESTORATION_EVENT}.txt"
GEOGRAPHY_FILE: Final[str] = "in_game/common/scripted_geography/rnw_formations.txt"
# What the other heirs gain or give by their answer: vanilla opinions and prestige values.
RECOGNIZED: Final[str] = "opinion_good_relations"
CONTESTED: Final[str] = "opinion_refused_claim"
BIASES_DIR: Final[str] = "game/in_game/common/biases"
VALUES_DIR: Final[str] = "game/main_menu/common/script_values"
PRESTIGE: Final[tuple[str, str]] = ("prestige_weak_penalty", "prestige_weak_bonus")
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
    """What a formation needs of the world besides its places: a tag, a name, a colour.

    The name is the family's term with the seat's word, written by each language its own way
    (``wording``: *Kaira Union*, *Кайрский союз*, *Unia Kairańska*), and so is the adjective.
    """

    tag: str
    name: Phrase
    adjective: Phrase | Text
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
    if any(spec.heirs for spec in specs):
        defined = {
            line.split("=")[0].strip()
            for directory in (BIASES_DIR, VALUES_DIR)
            for path in sorted((game_dir / directory).glob("*.txt"))
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if "=" in line
        }
        for needed in (RECOGNIZED, CONTESTED, *PRESTIGE):
            if needed not in defined:
                message = f"The {needed} that the restorations lean on is gone from the game"
                raise FormationError(message)
    for spec in specs:
        if levels.get(spec.rank) != spec.rank_level:
            message = (
                f"The rank {spec.rank} of {spec.family} is not level {spec.rank_level} in the game"
            )
            raise FormationError(message)
        for directory, name in ((EMBLEM_DIR, spec.emblem), (PATTERN_DIR, ARMS_PATTERN)):
            if not (game_dir / directory / name).is_file():
                message = f"The picture {name} of {spec.family} is gone from the installation"
                raise FormationError(message)


def potential(formation: Formation) -> list[str]:
    """The lines of a formation's ``potential`` (the AI's goals ask the same), unindented."""
    return textwrap.dedent(_potential(formation, BY_FAMILY[formation.family])).splitlines()


def _potential(formation: Formation, spec: Spec) -> str:
    """Who sees the formable besides the holders of its territory, decided in play."""
    if spec.potential:
        return "".join(f"\t\t{line}\n" for line in spec.potential)
    if spec.heirs:
        owners = "".join(f"\t\t\thas_or_had_tag = {tag}\n" for tag in formation.states)
        return f"\t\tOR = {{\n{owners}\t\t}}\n"
    if formation.basis:
        owners = "".join(f"\t\t\ttag = {tag}\n" for tag in formation.states)
        people = f"culture ?= {{ has_culture_group = culture_group:{formation.basis} }}"
        return f"\t\tOR = {{\n{owners}\t\t\t{people}\n\t\t}}\n"
    if formation.continent:
        return f"\t\tcapital.continent = continent:{formation.continent}\n"
    return ""


def _territory(formation: Formation) -> str:
    """The region, the continent or the locations whose share the founder must hold."""
    if formation.region:
        return f"\tregions = {{\n\t\t{formation.region}\n\t}}\n"
    if formation.continent:
        return f"\tcontinents = {{\n\t\t{formation.continent}\n\t}}\n"
    places = "\n".join(f"\t\t{key}" for key in formation.places)
    return f"\tlocations = {{\n{places}\n\t}}\n"


# A location of the territory that another country holds and that is not yet the founder's core.
FOREIGN: Final[tuple[str, ...]] = (
    "owner ?= { NOT = { this = root } }",
    "NOT = { is_core_of = root }",
)


def _indented(lines: Sequence[str], depth: int) -> str:
    return "".join("\t" * depth + line + "\n" for line in lines)


def geography(formation: Formation) -> str:
    """The key of a formation's territory as a ``scripted_geography`` (its cores, the AI's goal)."""
    return f"{key_of(formation)}_geography"


def geographies(formations: Sequence[Formation]) -> str:
    """The territory of every formation as a scripted geography: its region, continent or places.

    Vanilla's ``scripted_geography.info`` allows any level of the hierarchy in one geography.
    """
    out: list[str] = []
    for formation in formations:
        if formation.region:
            kind, keys = "region", [formation.region]
        elif formation.continent:
            kind, keys = "continent", [formation.continent]
        else:
            kind, keys = "location", list(formation.places)
        lines = [f"{geography(formation)} = {{", f"\t{kind} = {{", *(f"\t\t{k}" for k in keys)]
        out.append(_indented([*lines, "\t}", "}"], 0))
    return "\n".join(out)


def _cores(formation: Formation) -> str:
    """The founder's cores on the rest of the territory, under one line of tooltip."""
    work = (
        _indented(
            [
                f"scripted_geography:{geography(formation)} = {{",
                "\tevery_location_in_scripted_geography = {",
                "\t\tlimit = {",
            ],
            3,
        )
        + _indented(FOREIGN, 6)
        + _indented(["\t\t}", "\t\tadd_core = root", "\t}", "}"], 3)
    )
    return f"\t\tcustom_tooltip = {CORES_TOOLTIP}\n\t\thidden_effect = {{\n{work}\t\t}}\n"


def nation_key(tag: str, tradition: str) -> str:
    """The key of the name a founder of ``tradition`` takes (``change_country_name``)."""
    return f"{tag}_{tradition}"


def _renaming(tag: str) -> str:
    """The founder takes the name of its tradition, the first one its culture meets."""
    return "".join(
        _indented(
            [
                f"{'if' if number == 0 else 'else_if'} = {{",
                f"\tlimit = {{ {tradition.founder} }}",
                f"\tchange_country_name = {nation_key(tag, tradition.name)}",
                "}",
            ],
            2,
        )
        for number, tradition in enumerate(TRADITIONS)
    )


def restoration_event(formation: Formation) -> str:
    """The identifier of the event the other heirs of a restoration receive."""
    return f"{RESTORATION_EVENT}.{formation.index + 1}"


def _summons(formation: Formation) -> str:
    """The other heirs are asked to recognize or contest the restoration."""
    heirs = [f"\t\thas_or_had_tag = {tag}" for tag in formation.states]
    return _indented(
        [
            f"custom_tooltip = {HEIRS_TOOLTIP}",
            "hidden_effect = {",
            "\tevery_country = {",
            "\t\tlimit = {",
            "\t\t\tOR = {",
            *(f"\t\t{line}" for line in heirs),
            "\t\t\t}",
            "\t\t\tNOT = { this = root }",
            "\t\t}",
            f"\t\ttrigger_event_non_silently = {{ id = {restoration_event(formation)} }}",
            "\t}",
            "}",
        ],
        2,
    )


def _answer(name: str, prestige: str, opinion: str, *, rival: bool, ai: int) -> list[str]:
    return [
        "option = {",
        f"\tname = {RESTORATION_EVENT}.{name}",
        f"\tadd_prestige = {prestige}",
        *(["\tadd_rival = scope:restorer"] if rival else []),
        f"\tadd_opinion = {{ target = scope:restorer modifier = {opinion} }}",
        f"\tscope:restorer = {{ add_opinion = {{ target = root modifier = {opinion} }} }}",
        f"\tai_chance = {{ base = {ai} }}",
        "}",
    ]


def restoration_events(pairs: Sequence[tuple[Formation, Identity]]) -> str:
    """The events of the other heirs: recognize the restored crown, or deny it as its rival."""
    out = [f"namespace = {RESTORATION_EVENT}\n"]
    lose, gain = PRESTIGE
    for formation, identity in pairs:
        if not BY_FAMILY[formation.family].heirs:
            continue
        tag = identity.tag
        lines = [
            f"{restoration_event(formation)} = {{",
            "\ttype = country_event",
            f"\ttitle = {RESTORATION_EVENT}.title",
            f"\tdesc = {RESTORATION_EVENT}.desc",
            "\toutcome = neutral",
            "",
            "\ttrigger = {",
            f"\t\tcountry_exists = c:{tag}",
            f"\t\tNOT = {{ tag = {tag} }}",
            "\t}",
            "",
            "\timmediate = {",
            f"\t\tc:{tag} = {{ save_scope_as = restorer }}",
            "\t}",
            "",
            *(f"\t{line}" for line in _answer("a", lose, RECOGNIZED, rival=False, ai=40)),
            "",
            *(f"\t{line}" for line in _answer("b", gain, CONTESTED, rival=True, ai=60)),
            "}",
        ]
        out.append("\n" + _indented(lines, 0))
    return "".join(out)


def _unlock(spec: Spec) -> str:
    """The family's reform opens to the founder (vanilla's ``unlock_government_reform_effect``)."""
    if spec.reform is None:
        return ""
    return f"\t\tunlock_government_reform_effect = {{ type = {spec.reform.name} }}\n"


def block(formation: Formation, identity: Identity) -> str:
    """The formable of one formation: a tag the game does not define, as ``ADU`` is."""
    spec = BY_FAMILY[formation.family]
    asks = [*spec.allow, *([f"owns = location:{formation.throne}"] if formation.throne else [])]
    allow = "".join(f"\t\t{line}\n" for line in asks)
    return (
        f"{key_of(formation)} = {{\n"
        f"\tlevel = {spec.level}\n"
        f"\trequired_locations_fraction = {spec.fraction}\n"
        f"\trule = {spec.rule}\n"
        "\tcapital_required = yes\n\n"
        f"\tpotential = {{\n{_potential(formation, spec)}\t}}\n\n"
        f"\tallow = {{\n{allow}\t}}\n\n"
        f"\tname = {identity.tag}\n"
        f"\tflag = {identity.tag}\n"
        f"\tadjective = {identity.tag}_ADJ\n"
        f"\ttag = {identity.tag}\n"
        f"\tcolor = map_{identity.tag}\n\n"
        f"{_territory(formation)}"
        "\tform_effect = {\n"
        f"\t\tif = {{\n\t\t\tlimit = {{ country_rank_level < {spec.rank_level} }}\n"
        f"\t\t\tset_country_rank_effect = {{ rank = country_rank:{spec.rank} }}\n\t\t}}\n"
        "\t\tadd_country_modifier = {\n"
        f"\t\t\tmodifier = {spec.modifier.name}\n"
        f"\t\t\tyears = {spec.years}\n"
        "\t\t\tmode = add\n\t\t}\n"
        f"{_unlock(spec)}"
        f"{_cores(formation) if spec.cores else ''}"
        f"{_renaming(identity.tag) if spec.renamed else ''}"
        f"{_summons(formation) if spec.heirs else ''}"
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
    found = {
        FORMABLES_FILE: formables,
        FLAGS_FILE: flags,
        ARMS_FILE: arms,
        COLORS_FILE: colours,
        GEOGRAPHY_FILE: geographies(formations),
    }
    if any(BY_FAMILY[formation.family].heirs for formation in formations):
        found[RESTORATION_FILE] = restoration_events(pairs)
    return found


def _naming(
    formation: Formation, names: Mapping[str, Name], regions: Mapping[str, Name]
) -> tuple[Phrase, Phrase | Text]:
    """A formation's name and adjective: the continent's own text for the empire, the region's
    word for a realm, the seat's for the others."""
    if formation.continent:
        return wording.reference(formation.continent), Text(EMPIRE_ADJECTIVE)
    region = formation.region or formation.named_by
    key, table = (region, regions) if region else (formation.seat, names)
    word = table.get(key, key)
    if not isinstance(word, str):
        message = f"The place {key} of a formation has the composed name {word}"
        raise FormationError(message)
    stem = BY_FAMILY[formation.family].stem
    return Phrase(wording.FORMATION + stem, word), wording.adjective(word)


def identities(  # noqa: PLR0913 - the formations, the world's names and its colour and tag draws.
    formations: Sequence[Formation],
    names: Mapping[str, Name],
    tags: Sequence[str],
    seed: int,
    taken: frozenset[tuple[int, int, int]],
    *,
    regions: Mapping[str, Name] | None = None,
) -> list[Identity]:
    """A tag, a name, a map colour and two heraldic colours for each formation.

    ``regions`` name the generated regions, which name the realms.
    """
    found: list[Identity] = []
    used = set(taken)
    for formation, tag in zip(formations, tags, strict=True):
        name, adjective = _naming(formation, names, regions or {})
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
        found.append(
            Identity(tag, name, adjective, colour, (ARMS_COLOURS[first], ARMS_COLOURS[second]))
        )
    return found


def texts(formations: Sequence[Formation], identities_of: Sequence[Identity]) -> dict[str, Entry]:
    """The localization of the formations: names, adjectives, formable keys and descriptions."""
    found: dict[str, Entry] = {}
    for formation, identity in zip(formations, identities_of, strict=True):
        key = key_of(formation)
        found[identity.tag] = identity.name
        found[f"{identity.tag}_ADJ"] = identity.adjective
        # The formables list asks for the formable's own key (vanilla: ``SWI_f: "$SWI$"``);
        # without it the game shows the key and logs it as a missing localization.
        found[key] = wording.reference(identity.tag)
        found[f"{key}_desc"] = Described(formation_description(formation.family), identity.name)
        spec = BY_FAMILY[formation.family]
        if spec.cores:
            found[CORES_TOOLTIP] = Text(CORES_TOOLTIP)
        if spec.heirs:
            for text in (
                HEIRS_TOOLTIP,
                *(k for k in EXTRA_TEXTS if k.startswith(RESTORATION_EVENT)),
            ):
                found[text] = Text(text)
        if spec.renamed:
            for tradition in TRADITIONS:
                found[nation_key(identity.tag, tradition.name)] = Phrase(
                    wording.NATION + tradition.name, identity.name.word
                )
    return found
