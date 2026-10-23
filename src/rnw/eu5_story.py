"""The files of the content plan's stories and unions for one world (content plan, N3).

``content`` decides who is offered what; ``stories`` holds the static story texts. This module
turns the two into the world's mod:

* the events of each family that has a bearer (static, copied) and, per bearer, a hidden *start*
  event bound to the bearer's tag and centre;
* the static modifiers and the estate privilege the stories apply, with the payload copied from the
  vanilla modifier, building or privilege named as their source;
* for each formation a formable of a tag the game does not define (``eu5_formation``) and the
  founding modifier of its family;
* the localization of all of it, in every language.

Nothing here reads the game more than the sources it copies; a source that is gone stops the
export (``StoryError``) instead of being replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import eu5_formation
from rnw.content import (
    RIVER_CENTRE,
    SACRED_CENTRE,
    ContentPlan,
    Facts,
    Opportunity,
    Place,
    State,
)
from rnw.formations import SPECS
from rnw.pdx import Block, parse
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
    from collections.abc import Collection, Mapping, Sequence
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
LOCALIZATION: Final[str] = "main_menu/localization"
CENTRE_VARIABLES: Final[Mapping[str, str]] = {
    RIVER_CENTRE: RIVER_CENTRE_VARIABLE,
    SACRED_CENTRE: SACRED_CENTRE_VARIABLE,
}


class StoryError(ValueError):
    """A source, a colour or a name that the stories lean on is gone from the installation."""


@dataclass(frozen=True, slots=True)
class Payload:
    """The effect lines of a vanilla source, and its declared category and decay."""

    lines: tuple[str, ...]
    category: str
    decaying: bool


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
    """Every file of the stories and formables of one world."""
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
    identities: list[eu5_formation.Identity] = []
    if plan.formations:
        families = {formation.family for formation in plan.formations}
        specs = [spec for spec in SPECS if spec.family in families]
        eu5_formation.check_installation(game_dir, specs)
        identities = eu5_formation.identities(plan.formations, names, tags, seed, taken)
        for path, text in eu5_formation.files(plan.formations, identities).items():
            files[path] = text.encode("utf-8-sig")
        texts.update(eu5_formation.texts(plan.formations, identities))
        for spec in specs:
            modifiers.append(modifier_block(spec.modifier, payload(game_dir, spec.modifier.source)))
            texts[f"STATIC_MODIFIER_NAME_{spec.modifier.name}"] = spec.modifier.title
            texts[f"STATIC_MODIFIER_DESC_{spec.modifier.name}"] = spec.modifier.text
    if modifiers:
        files[MODIFIERS_FILE] = "\n".join(modifiers).encode("utf-8-sig")
    if privileges:
        files[PRIVILEGES_FILE] = "\n".join(privileges).encode("utf-8-sig")
    if texts:
        for language in languages:
            files[f"{LOCALIZATION}/{language}/rnw_story_l_{language}.yml"] = _yaml(language, texts)
    stats: dict[str, object] = {
        "opportunities": plan.count(),
        "starts": ids,
        "absences": {absence.family: absence.reason for absence in plan.absences},
        "formations": {
            identity.tag: {
                "family": formation.family,
                "name": identity.name,
                "places": len(formation.places),
                "states": list(formation.states),
                **({"basis": formation.basis} if formation.basis else {}),
            }
            for formation, identity in zip(plan.formations, identities, strict=True)
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
    relief: Mapping[str, str] | None = None,
    culture: Mapping[str, str] | None = None,
    seas: Mapping[str, Collection[str]] | None = None,
    groups: Mapping[str, Collection[str]] | None = None,
) -> Facts:
    """The facts of a world from its parts: ``states`` are (tag, members, capital, religion)."""
    owner: dict[str, str] = {}
    table: dict[str, State] = {}
    for tag, members, capital, faith in states:
        table[tag] = State(tag, capital, faith)
        owner.update(dict.fromkeys(members, tag))
    relief = relief or {}
    culture = culture or {}
    seas = seas or {}
    places = {
        key: Place(
            key,
            population[key],
            river.get(key, 0),
            ranks.get(key, ""),
            religion.get(key, ""),
            owner.get(key, ""),
            relief.get(key, ""),
            culture.get(key, ""),
            frozenset(seas.get(key, ())),
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
        {name: frozenset(found) for name, found in (groups or {}).items()},
    )
