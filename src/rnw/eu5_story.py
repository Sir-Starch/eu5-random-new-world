"""The files of the content plan's stories and unions for one world (content plan, N3).

``content`` decides who is offered what; ``stories`` holds the static story texts. This module
turns the two into the world's mod:

* the events of each family that has a bearer (static, copied) and, per bearer, a hidden *start*
  event bound to the bearer's tag and centre;
* the static modifiers and the estate privilege the stories apply, with the payload copied from the
  vanilla modifier, building or privilege named as their source;
* for each river union a formable of a tag the game does not define, with the flag, the coat of
  arms, the colour and the names that the vanilla formable-only tag ``ADU`` has (C175);
* the localization of all of it, in every language.

Nothing here reads the game more than the sources it copies; a source that is gone stops the
export (``StoryError``) instead of being replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.content import (
    RIVER_CENTRE,
    SACRED_CENTRE,
    ContentPlan,
    Facts,
    Opportunity,
    Place,
    State,
    Union,
)
from rnw.eu5_natives import hsv_rgb
from rnw.pdx import Block, parse
from rnw.rng import derive_seed
from rnw.stories import (
    BUILDING,
    CLEANUP,
    CLEANUP_MONTHS,
    PRIVILEGE,
    RIVER_CENTRE_VARIABLE,
    SACRED_CENTRE_VARIABLE,
    STATIC,
    STORIES,
    Modifier,
    Privilege,
    Source,
    Story,
    event_keys,
    render_events,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

NAMESPACE: Final[str] = "rnw_story"
FIRST_START: Final[int] = 1001
STATIC_DIR: Final[str] = "game/main_menu/common/static_modifiers"
BUILDING_DIR: Final[str] = "game/in_game/common/building_types"
PRIVILEGE_DIR: Final[str] = "game/in_game/common/estate_privileges"
MODIFIERS_FILE: Final[str] = "main_menu/common/static_modifiers/rnw_story_modifiers.txt"
PRIVILEGES_FILE: Final[str] = "in_game/common/estate_privileges/rnw_story.txt"
EVENTS_DIR: Final[str] = "in_game/events"
START_FILE: Final[str] = f"{EVENTS_DIR}/rnw_story.txt"
UNION_FILE: Final[str] = "in_game/common/formable_countries/rnw_union.txt"
FLAGS_FILE: Final[str] = "main_menu/common/flag_definitions/rnw_union.txt"
ARMS_FILE: Final[str] = "main_menu/common/coat_of_arms/coat_of_arms/rnw_union.txt"
COLORS_FILE: Final[str] = "main_menu/common/named_colors/rnw_union.txt"
LOCALIZATION: Final[str] = "main_menu/localization"
CENTRE_VARIABLES: Final[Mapping[str, str]] = {
    RIVER_CENTRE: RIVER_CENTRE_VARIABLE,
    SACRED_CENTRE: SACRED_CENTRE_VARIABLE,
}
UNION_FRACTION: Final[str] = "0.6"
UNION_LEVEL: Final[int] = 3
# Names the vanilla coat of arms of ``ADU`` uses; a union takes two distinct colours of these.
ARMS_PATTERN: Final[str] = "pattern_solid.dds"
ARMS_EMBLEM: Final[str] = "ce_checky_15_points.dds"
ARMS_COLOURS: Final[tuple[str, ...]] = ("green", "white", "red", "blue", "yellow", "black")


class StoryError(ValueError):
    """A source, a colour or a name that the stories lean on is gone from the installation."""


@dataclass(frozen=True, slots=True)
class Payload:
    """The effect lines of a vanilla source, and its declared category and decay."""

    lines: tuple[str, ...]
    category: str
    decaying: bool


@dataclass(frozen=True, slots=True)
class UnionIdentity:
    """What a union needs of the world besides its places: a tag, a name, a colour."""

    tag: str
    name: str
    adjective: str
    colour: tuple[int, int, int]
    colours: tuple[str, str]


@dataclass(frozen=True, slots=True)
class Written:
    """The files of the stories and unions of a world, and what they hold."""

    files: dict[str, bytes]
    stats: dict[str, object]


def _entries(directory: Path) -> dict[str, tuple[str, Block]]:
    """Every top-level block of the ``.txt`` files in ``directory`` with its file's text."""
    found: dict[str, tuple[str, Block]] = {}
    for path in sorted(directory.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        for entry in parse(text).entries:
            if entry.key is not None and isinstance(entry.value, Block):
                _ = found.setdefault(entry.key, (text, entry.value))
    return found


def _lines(text: str, block: Block, skip: frozenset[str]) -> tuple[str, ...]:
    return tuple(
        text[entry.start : entry.end].strip() for entry in block.entries if entry.key not in skip
    )


def payload(game_dir: Path, source: Source) -> Payload:
    """The effect lines of ``source`` in the installation; raises if it is gone or empty."""
    directory = {STATIC: STATIC_DIR, BUILDING: BUILDING_DIR, PRIVILEGE: PRIVILEGE_DIR}[source.kind]
    found = _entries(game_dir / directory).get(source.name)
    if found is None:
        message = f"The {source.kind} {source.name} is gone from the installation"
        raise StoryError(message)
    text, block = found
    category = ""
    decaying = False
    if source.kind == STATIC:
        data = block.block("game_data")
        if data is not None:
            kind = data.first("category")
            category = kind.value if kind is not None and isinstance(kind.value, str) else ""
            flag = data.first("decaying")
            decaying = flag is not None and flag.value == "yes"
        lines = _lines(text, block, frozenset({"game_data"}))
    else:
        inner = block.block(source.block)
        if inner is None:
            message = f"The {source.kind} {source.name} has no {source.block}"
            raise StoryError(message)
        lines = _lines(text, inner, frozenset())
    if not lines:
        message = f"The {source.kind} {source.name} has nothing to copy"
        raise StoryError(message)
    return Payload(lines, category, decaying)


def modifier_block(modifier: Modifier, copied: Payload) -> str:
    """One static modifier of the mod: its category and the copied effect lines."""
    if copied.category and copied.category != modifier.category:
        message = f"{modifier.name} is {modifier.category} but its source is {copied.category}"
        raise StoryError(message)
    head = [f"{modifier.name} = {{", "\tgame_data = {", f"\t\tcategory = {modifier.category}"]
    if copied.decaying:
        head.append("\t\tdecaying = yes")
    head.append("\t}")
    return "\n".join([*head, *(f"\t{line}" for line in copied.lines), "}"]) + "\n"


def privilege_block(privilege: Privilege, copied: Payload) -> str:
    """One estate privilege of the mod, opened by a variable, with the copied modifier."""
    inner = "\n".join(f"\t\t{line}" for line in copied.lines)
    return (
        f"{privilege.name} = {{\n"
        f"\testate = {privilege.estate}\n\n"
        f"\tpotential = {{\n\t\thas_variable = {privilege.opened_by}\n\t}}\n\n"
        f"\tcountry_modifier = {{\n{inner}\n\t}}\n"
        "}\n"
    )


def start_event(number: int, opportunity: Opportunity, story: Story) -> str:
    """The hidden event that starts a story for its bearer at its centre."""
    start = opportunity.start
    variable = CENTRE_VARIABLES[opportunity.family]
    opening, closing = story.event(story.nodes[0].number), story.event(CLEANUP)
    return (
        f"{NAMESPACE}.{number} = {{\n"
        "\ttype = country_event\n"
        "\thidden = yes\n"
        "\tfire_only_once = yes\n\n"
        "\tdynamic_historical_event = {\n"
        f"\t\ttag = {opportunity.bearer}\n"
        f"\t\tfrom = {start.year}.1.1\n"
        f"\t\tto = {start.until}.1.1\n"
        f"\t\tmonthly_chance = {start.chance}\n"
        "\t}\n\n"
        f"\ttrigger = {{\n\t\towns = location:{opportunity.centre}\n\t}}\n\n"
        "\timmediate = {\n"
        f"\t\tset_variable = {{ name = {variable} value = location:{opportunity.centre} }}\n"
        f"\t\ttrigger_event_non_silently = {{ id = {opening} }}\n"
        f"\t\ttrigger_event_silently = {{ id = {closing} months = {CLEANUP_MONTHS} }}\n"
        "\t}\n"
        "}\n"
    )


def start_events(plan: ContentPlan) -> tuple[str, dict[str, str]]:
    """The script of the start events, and which event starts which opportunity."""
    by_family = {story.family: story for story in STORIES}
    ordered = sorted(plan.opportunities, key=lambda item: (item.family, item.bearer))
    blocks = [f"namespace = {NAMESPACE}\n\n"]
    ids: dict[str, str] = {}
    for offset, opportunity in enumerate(ordered):
        number = FIRST_START + offset
        ids[opportunity.ident] = f"{NAMESPACE}.{number}"
        blocks.append(start_event(number, opportunity, by_family[opportunity.family]) + "\n")
    return "".join(blocks).rstrip("\n") + "\n", ids


def union_block(union: Union, identity: UnionIdentity) -> str:
    """The formable of one river union: a tag the game does not define, as ``ADU`` is."""
    owners = "\n".join(f"\t\t\ttag = {tag}" for tag in union.states)
    places = "\n".join(f"\t\t{key}" for key in union.places)
    return (
        f"rnw_union_{union.index + 1}_f = {{\n"
        f"\tlevel = {UNION_LEVEL}\n"
        f"\trequired_locations_fraction = {UNION_FRACTION}\n"
        "\trule = plausible\n"
        "\tcapital_required = yes\n\n"
        f"\tpotential = {{\n\t\tOR = {{\n{owners}\n\t\t}}\n\t}}\n\n"
        "\tallow = {\n\t}\n\n"
        f"\tname = {identity.tag}\n"
        f"\tflag = {identity.tag}\n"
        f"\tadjective = {identity.tag}_ADJ\n"
        f"\ttag = {identity.tag}\n"
        f"\tcolor = map_{identity.tag}\n\n"
        f"\tlocations = {{\n{places}\n\t}}\n"
        "\tform_effect = {\n"
        "\t\tif = {\n\t\t\tlimit = { country_rank_level < 3 }\n"
        "\t\t\tset_country_rank_effect = { rank = country_rank:rank_kingdom }\n\t\t}\n"
        "\t}\n"
        "}\n"
    )


def union_files(unions: Sequence[Union], identities: Sequence[UnionIdentity]) -> dict[str, str]:
    """The script files of the unions: formables, flags, coats of arms and colours."""
    formables = "\n".join(
        union_block(union, identity) for union, identity in zip(unions, identities, strict=True)
    )
    flags = "\n".join(
        f"{i.tag} = {{\n\tflag_definition = {{\n\t\tcoa = {i.tag}\n\t\tpriority = 1\n\t}}\n}}\n"
        for i in identities
    )
    arms = "\n".join(
        (
            f"{i.tag} = {{\n"
            f'\tpattern = "{ARMS_PATTERN}"\n'
            f'\tcolor1 = "{i.colours[0]}"\n'
            f'\tcolor2 = "{i.colours[1]}"\n\n'
            "\tcolored_emblem = {\n"
            f'\t\ttexture = "{ARMS_EMBLEM}"\n'
            "\t\tcolor1 = color1\n\t\tcolor2 = color2\n\t}\n}\n"
        )
        for i in identities
    )
    colours = (
        "colors = {\n"
        + "".join(
            f"\tmap_{i.tag} = rgb {{ {i.colour[0]} {i.colour[1]} {i.colour[2]} }}\n"
            for i in identities
        )
        + "}\n"
    )
    return {UNION_FILE: formables, FLAGS_FILE: flags, ARMS_FILE: arms, COLORS_FILE: colours}


def union_identities(
    unions: Sequence[Union],
    names: Mapping[str, str],
    tags: Sequence[str],
    seed: int,
    taken: frozenset[tuple[int, int, int]],
) -> list[UnionIdentity]:
    """A tag, a name, a map colour and two heraldic colours for each union."""
    found: list[UnionIdentity] = []
    used = set(taken)
    for union, tag in zip(unions, tags, strict=True):
        seat = names.get(union.seat, union.seat)
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
            UnionIdentity(
                tag, f"{seat} Union", seat, colour, (ARMS_COLOURS[first], ARMS_COLOURS[second])
            )
        )
    return found


def _yaml(language: str, entries: Mapping[str, str]) -> bytes:
    lines = [f"l_{language}:"] + [f' {key}: "{value}"' for key, value in entries.items()]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def build(  # noqa: PLR0913 - the stories need the plan, the installation and the world's identities.
    game_dir: Path,
    plan: ContentPlan,
    *,
    names: Mapping[str, str],
    tags: Sequence[str],
    languages: Sequence[str],
    seed: int,
    taken: frozenset[tuple[int, int, int]],
) -> Written:
    """Every file of the stories and unions of one world."""
    files: dict[str, bytes] = {}
    texts: dict[str, str] = {}
    present = {opportunity.family for opportunity in plan.opportunities}
    stories = [story for story in STORIES if story.family in present]
    modifiers: list[str] = []
    privileges: list[str] = []
    for story in stories:
        files[f"{EVENTS_DIR}/{story.namespace}.txt"] = render_events(story).encode("utf-8-sig")
        texts.update(event_keys(story))
        modifiers += [modifier_block(m, payload(game_dir, m.source)) for m in story.modifiers]
        privileges += [privilege_block(p, payload(game_dir, p.source)) for p in story.privileges]
    ids: dict[str, str] = {}
    if plan.opportunities:
        script, ids = start_events(plan)
        files[START_FILE] = script.encode("utf-8-sig")
    if modifiers:
        files[MODIFIERS_FILE] = "\n".join(modifiers).encode("utf-8-sig")
    if privileges:
        files[PRIVILEGES_FILE] = "\n".join(privileges).encode("utf-8-sig")
    identities: list[UnionIdentity] = []
    if plan.unions:
        identities = union_identities(plan.unions, names, tags, seed, taken)
        for path, text in union_files(plan.unions, identities).items():
            files[path] = text.encode("utf-8-sig")
        for identity in identities:
            texts[identity.tag] = identity.name
            texts[f"{identity.tag}_ADJ"] = identity.adjective
    if texts:
        for language in languages:
            files[f"{LOCALIZATION}/{language}/rnw_story_l_{language}.yml"] = _yaml(language, texts)
    stats: dict[str, object] = {
        "opportunities": plan.count(),
        "starts": ids,
        "absences": {absence.family: absence.reason for absence in plan.absences},
        "unions": {
            identity.tag: {
                "name": identity.name,
                "places": len(union.places),
                "states": list(union.states),
            }
            for union, identity in zip(plan.unions, identities, strict=True)
        },
    }
    return Written(files, stats)


def facts_of(  # noqa: PLR0913 - the plan reads the countries, the cells, the rivers and the holy places.
    *,
    keys: Sequence[str],
    population: Mapping[str, int],
    ranks: Mapping[str, str],
    religion: Mapping[str, str],
    river: Mapping[str, int],
    states: Sequence[tuple[str, tuple[str, ...], str, str]],
    holy: Sequence[str],
    links: Sequence[tuple[str, str]],
) -> Facts:
    """The facts of a world from its parts: ``states`` are (tag, members, capital, religion)."""
    owner: dict[str, str] = {}
    table: dict[str, State] = {}
    for tag, members, capital, faith in states:
        table[tag] = State(tag, capital, faith)
        owner.update(dict.fromkeys(members, tag))
    places = {
        key: Place(
            key,
            population[key],
            river.get(key, 0),
            ranks.get(key, ""),
            religion.get(key, ""),
            owner.get(key, ""),
        )
        for key in keys
        if population.get(key, 0) > 0
    }
    present = frozenset(places)
    return Facts(
        places,
        table,
        frozenset(key for key in holy if key in present),
        frozenset((a, b) for a, b in links if a in present and b in present),
    )
