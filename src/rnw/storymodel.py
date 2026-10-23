"""The model of a story: the data it is written in, its script, and the checks of its graph.

A story is a short graph of events about one place (sometimes two) and the state that holds it
(content plan, N3 and N4). It is *static*: its texts are the project's own English prose
(translated by L1), its scripts name no tag and no location, and every world mod carries the same
copy. What is world-specific is only the binding that starts it for one bearer (``eu5_story``): a
hidden event that sets the variable naming the centre and fires the first node.

Each story is written as data so that its script is generated the same way every time and its
graph can be checked without the game: every node reachable, every branch ended, the variables of
the story removed when it ends, nothing offered that cannot be paid for, no loop. The stories
themselves are in ``stories`` and ``stories_n4``.

Vanilla supplies what the choices do. Every modifier a story applies copies the *payload* of a
vanilla modifier, building or privilege chosen for its effect (``Source``), under a name and a text
of the mod's own; the copy is made at generation time from the installation, never committed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

COUNTRY: Final[str] = "country"
LOCATION: Final[str] = "location"
STATIC: Final[str] = "static"
BUILDING: Final[str] = "building"
PRIVILEGE: Final[str] = "privilege"
CLERGY: Final[str] = "clergy_estate"
# An option that costs gold is offered only to a state that has some.
AFFORD: Final[str] = "gold > 100"
CLEANUP: Final[int] = 9
CLEANUP_MONTHS: Final[int] = 180


@dataclass(frozen=True, slots=True)
class Source:
    """Where a modifier's payload comes from in the installation."""

    kind: str
    name: str
    block: str = ""


@dataclass(frozen=True, slots=True)
class Modifier:
    """A static modifier of the mod with the payload of a vanilla source."""

    name: str
    category: str
    source: Source
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Privilege:
    """An estate privilege of the mod that the story opens by a variable."""

    name: str
    estate: str
    opened_by: str
    source: Source
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Follow:
    """The next node, fired after a delay in months drawn between two bounds."""

    node: int
    months: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Option:
    """One choice of a node: its text, what it does, who prefers it and where it leads."""

    key: str
    text: str
    effects: tuple[str, ...]
    ai: int
    follow: Follow | None = None
    trigger: str = ""


@dataclass(frozen=True, slots=True)
class Node:
    """One event of a story."""

    number: int
    title: str
    desc: str
    options: tuple[Option, ...]
    requires: tuple[str, ...] = ()
    immediate: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Story:
    """A family's story: its nodes, the variables it keeps, the payloads it applies.

    ``centre`` names the variable that holds the place the story is about; ``other`` the variable
    of a second place (the far end of a route, a neighbour's capital) when the family has one.
    ``immediate`` are the effects every event of the story begins with, ``gate`` the conditions
    every event of it asks besides the owner of the centre; ``holds_other`` says the bearer must
    own the second place too when the story starts (the far end of a route is its own).
    """

    family: str
    namespace: str
    centre: str
    path: str
    nodes: tuple[Node, ...]
    modifiers: tuple[Modifier, ...] = ()
    privileges: tuple[Privilege, ...] = ()
    other: str = ""
    immediate: tuple[str, ...] = ()
    gate: tuple[str, ...] = ()
    holds_other: bool = False

    def event(self, number: int) -> str:
        """The identifier of node ``number``."""
        return f"{self.namespace}.{number}"

    def variables(self) -> tuple[str, ...]:
        """The variables the story keeps while it runs."""
        return (self.centre, self.path, *([self.other] if self.other else []))

    def cleanup(self) -> tuple[str, ...]:
        """The effects that end a story: its variables go."""
        return tuple(f"remove_variable = {name}" for name in self.variables())


def prose(text: str) -> str:
    """A localization text from paragraphs separated by blank lines (``\\n\\n`` in the file)."""
    return "\\n\\n".join(" ".join(part.split()) for part in text.strip().split("\n\n"))


def gold(scale: int) -> str:
    return f"change_gold_effect = {{ scale = {scale} }}"


def country(name: str, years: int) -> str:
    return f"add_country_modifier = {{ modifier = {name} years = {years} mode = add }}"


def location(centre: str, name: str, years: int) -> str:
    return (
        f"var:{centre} ?= "
        f"{{ add_location_modifier = {{ modifier = {name} years = {years} mode = add }} }}"
    )


def unlocation(centre: str, name: str) -> str:
    return f"var:{centre} ?= {{ remove_location_modifier = {name} }}"


def set_to(name: str, value: int) -> str:
    return f"set_variable = {{ name = {name} value = {value} }}"


def path_is(path: str, number: int) -> tuple[str, ...]:
    return (f"var:{path} >= {number}", f"var:{path} <= {number}")


def event_keys(story: Story) -> dict[str, str]:
    """The localization of a story's events, modifiers and privileges."""
    found: dict[str, str] = {}
    for node in story.nodes:
        base = story.event(node.number)
        found[f"{base}.title"] = node.title
        found[f"{base}.desc"] = node.desc
        for option in node.options:
            found[f"{base}.{option.key}"] = option.text
    for modifier in story.modifiers:
        found[f"STATIC_MODIFIER_NAME_{modifier.name}"] = modifier.title
        found[f"STATIC_MODIFIER_DESC_{modifier.name}"] = modifier.text
    for privilege in story.privileges:
        found[privilege.name] = privilege.title
        found[f"{privilege.name}_desc"] = privilege.text
    return found


def _lines(effects: tuple[str, ...], indent: str) -> str:
    return "".join(f"{indent}{effect}\n" for effect in effects)


def render_cleanup(story: Story) -> str:
    """The hidden event that clears a story's variables if it never reached an ending.

    A story ends by an option; one whose place changed hands or whose chain was cut by war
    never does, so the start of the story schedules this event long after it could have ended.
    """
    return (
        f"{story.event(CLEANUP)} = {{\n"
        "\ttype = country_event\n"
        "\thidden = yes\n\n"
        f"\ttrigger = {{\n\t\thas_variable = {story.centre}\n\t}}\n\n"
        f"\timmediate = {{\n{_lines(story.cleanup(), chr(9) * 2)}\t}}\n"
        "}\n"
    )


def render_events(story: Story) -> str:
    """The script of a story's events."""
    centre = story.centre
    out = [f"namespace = {story.namespace}\n\n"]
    for node in story.nodes:
        event = story.event(node.number)
        gate = f"\t\texists = var:{centre}\n\t\tvar:{centre} ?= {{ owner ?= root }}\n"
        if story.other:
            gate += f"\t\texists = var:{story.other}\n"
        gate += _lines(story.gate, "\t\t") + _lines(node.requires, "\t\t")
        head = [
            f"{event} = {{\n",
            "\ttype = country_event\n",
            f"\ttitle = {event}.title\n",
            f"\tdesc = {event}.desc\n",
            "\toutcome = neutral\n\n",
            f"\ttrigger = {{\n{gate}\t}}\n\n",
            "\timmediate = {\n",
            f"\t\tvar:{centre} ?= {{ save_scope_as = target_location }}\n",
            _lines(story.immediate, chr(9) * 2),
            _lines(node.immediate, chr(9) * 2),
            "\t}\n",
        ]
        out.append("".join(head))
        for option in node.options:
            out.append(f"\n\toption = {{\n\t\tname = {event}.{option.key}\n")
            if option.trigger:
                out.append(f"\t\ttrigger = {{ {option.trigger} }}\n")
            out.append(_lines(option.effects, "\t\t"))
            if option.follow is not None:
                low, high = option.follow.months
                target = story.event(option.follow.node)
                delay = f"months = {{ {low} {high} }}"
                out.append(f"\t\ttrigger_event_non_silently = {{ id = {target} {delay} }}\n")
            out.append(f"\t\tai_chance = {{ base = {option.ai} }}\n\t}}\n")
        out.append("}\n\n")
    out.append(render_cleanup(story))
    return "".join(out)


def reachable(story: Story) -> set[int]:
    """The nodes a story can reach from its first node."""
    by_number = {node.number: node for node in story.nodes}
    seen: set[int] = set()
    stack = [story.nodes[0].number]
    while stack:
        number = stack.pop()
        if number in seen:
            continue
        seen.add(number)
        stack.extend(
            option.follow.node for option in by_number[number].options if option.follow is not None
        )
    return seen


def outcomes(story: Story) -> list[tuple[str, ...]]:
    """Every path through a story from its first node to an ending, as option keys."""
    by_number = {node.number: node for node in story.nodes}
    found: list[tuple[str, ...]] = []

    def walk(number: int, taken: tuple[str, ...]) -> None:
        for option in by_number[number].options:
            here = (*taken, f"{number}{option.key}")
            if option.follow is None:
                found.append(here)
            else:
                walk(option.follow.node, here)

    walk(story.nodes[0].number, ())
    return found
