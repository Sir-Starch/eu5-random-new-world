"""The story templates of the content plan: original events, written once, copied into every world.

A story is a short graph of events about one place and the state that holds it (content plan, N3).
It is *static*: its texts are the project's own English prose (translated by L1), its scripts name
no tag and no location, and every world mod carries the same copy. What is world-specific is only
the binding that starts it for one bearer (``eu5_story``): a hidden event that sets the variable
naming the centre and fires the first node.

Each story is written as data so that its script is generated the same way every time and its
graph can be checked without the game: every node reachable, every branch ended, the variables of
the story removed when it ends, nothing offered that cannot be paid for, no loop.

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
    """A family's story: its nodes, the variables it keeps, the payloads it applies."""

    family: str
    namespace: str
    centre: str
    path: str
    nodes: tuple[Node, ...]
    modifiers: tuple[Modifier, ...] = ()
    privileges: tuple[Privilege, ...] = ()

    def event(self, number: int) -> str:
        """The identifier of node ``number``."""
        return f"{self.namespace}.{number}"

    def cleanup(self) -> tuple[str, ...]:
        """The effects that end a story: its variables go."""
        return (f"remove_variable = {self.centre}", f"remove_variable = {self.path}")


def _prose(text: str) -> str:
    """A localization text from paragraphs separated by blank lines (``\\n\\n`` in the file)."""
    return "\\n\\n".join(" ".join(part.split()) for part in text.strip().split("\n\n"))


def _gold(scale: int) -> str:
    return f"change_gold_effect = {{ scale = {scale} }}"


def _country(name: str, years: int) -> str:
    return f"add_country_modifier = {{ modifier = {name} years = {years} mode = add }}"


def _location(centre: str, name: str, years: int) -> str:
    return (
        f"var:{centre} ?= "
        f"{{ add_location_modifier = {{ modifier = {name} years = {years} mode = add }} }}"
    )


def _set(name: str, value: int) -> str:
    return f"set_variable = {{ name = {name} value = {value} }}"


def _path_is(path: str, number: int) -> tuple[str, ...]:
    return (f"var:{path} >= {number}", f"var:{path} <= {number}")


RIVER_CENTRE_VARIABLE: Final[str] = "rnw_river_centre"
RIVER_PATH_VARIABLE: Final[str] = "rnw_river_path"
SACRED_CENTRE_VARIABLE: Final[str] = "rnw_sacred_centre"
SACRED_PATH_VARIABLE: Final[str] = "rnw_sacred_path"
SACRED_PRIVILEGE_VARIABLE: Final[str] = "rnw_sacred_privilege_open"


def _river() -> Story:
    centre, path = RIVER_CENTRE_VARIABLE, RIVER_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    first = _prose("""
        For generations the great river has fed [target_location.GetNameWithNoTooltip]. Its
        floods laid down the black fields, its barges carried the grain and its landing stages
        made the city rich. Now the channel shifts a little each spring. Silt chokes the old
        canals, the floods reach farther into the lower streets, and the granaries hold less
        than the stewards report.

        The elders of the city have come to the court. They agree that something must be done,
        and agree on nothing else.
    """)
    held = _prose("""
        The spring flood came as it always had, and this year it stopped at the new
        embankments. In the lower streets of [target_location.GetNameWithNoTooltip] the water
        that once stood in the markets for a month never rose past the wharves. The wardens of
        the banks ask what the city should do with the peace it has bought.
    """)
    due = _prose("""
        The tolls have filled the treasury and the banks have been left alone. This spring the
        river rose, found the weakest stretch and went through it. When the water fell the
        lower quarters of [target_location.GetNameWithNoTooltip] lay under mud, the wells were
        fouled and barges stood stranded in the streets. The collectors report that the tolls
        were paid in full, and that nobody is left to pay them next year.
    """)
    wardens = _prose("""
        The guilds of the river quarter have kept the banks for years now. They have done it
        more cheaply than the court could, and they have done it for themselves: their landings
        are better built than the rest and their quarter of
        [target_location.GetNameWithNoTooltip] is richer for it. They ask that their charter be
        written down.
    """)
    nodes = (
        Node(
            1,
            "The River Turns",
            first,
            (
                Option(
                    "a",
                    "Raise embankments and cut new canals.",
                    (
                        _gold(-3),
                        _country("rnw_river_works_levy", 6),
                        _location(centre, "rnw_river_embankments", 15),
                        _set(path, 1),
                    ),
                    50,
                    Follow(2, (36, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Squeeze the river trade and leave the banks as they are.",
                    (_country("rnw_river_toll_regime", 10), _set(path, 2)),
                    30,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Let the guilds of the river quarter keep the banks themselves.",
                    (
                        _location(centre, "rnw_river_guild_wardens", 20),
                        _country("rnw_river_ceded_authority", 10),
                        _set(path, 3),
                    ),
                    20,
                    Follow(4, (36, 72)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Banks Hold",
            held,
            (
                Option(
                    "a",
                    "Build granaries on the new banks.",
                    (_gold(-2), _location(centre, "rnw_river_flood_security", 20), *end),
                    60,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Keep the surplus in the treasury.",
                    (_gold(3), "add_stability = stability_weak_bonus", *end),
                    40,
                ),
            ),
            requires=_path_is(path, 1),
        ),
        Node(
            3,
            "The River Takes Its Due",
            due,
            (
                Option(
                    "a",
                    "Clear the channels at once, whatever it costs.",
                    (
                        _gold(-3),
                        "remove_location_modifier = rnw_river_silted",
                        "add_stability = stability_weak_bonus",
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Move the grain stores to higher ground and let the lower town drain.",
                    ("add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=_path_is(path, 2),
            immediate=(_location(centre, "rnw_river_silted", 15),),
        ),
        Node(
            4,
            "The River Wardens",
            wardens,
            (
                Option(
                    "a",
                    "Confirm the charter.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Take back the banks and the revenues with them.",
                    (
                        "remove_location_modifier = rnw_river_guild_wardens",
                        "add_stability = stability_mild_penalty",
                        _gold(2),
                        *end,
                    ),
                    45,
                ),
            ),
            requires=_path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_river_works_levy",
            COUNTRY,
            Source(STATIC, "chk_funding_woodhenge_restoration"),
            "River Works Levy",
            "The treasury pays for embankments and canals.",
        ),
        Modifier(
            "rnw_river_embankments",
            LOCATION,
            Source(STATIC, "chk_protection_against_flooding"),
            "New Embankments",
            "Raised banks keep the floods out of the streets and take some of the fields.",
        ),
        Modifier(
            "rnw_river_flood_security",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_protected_flooding"),
            "Safe from the Floods",
            "Granaries on the banks and years without floods let the city grow.",
        ),
        Modifier(
            "rnw_river_toll_regime",
            COUNTRY,
            Source(STATIC, "chk_restricted_construction"),
            "River Tolls",
            "Tolls on the river trade fill the treasury while the court builds little.",
        ),
        Modifier(
            "rnw_river_silted",
            LOCATION,
            Source(STATIC, "chk_river_water_polluted"),
            "Silt and Fouled Wells",
            "The flood left mud in the streets and filth in the wells.",
        ),
        Modifier(
            "rnw_river_guild_wardens",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_growth"),
            "Guild Wardens of the Banks",
            "The river quarter keeps its own banks and its quarter grows.",
        ),
        Modifier(
            "rnw_river_ceded_authority",
            COUNTRY,
            Source(STATIC, "chk_exodus_of_cahokia"),
            "Ceded Authority",
            "The care of the river is in the guilds' hands, and their payments cost standing.",
        ),
    )
    return Story("river_centre", "rnw_river", centre, path, nodes, modifiers)


def _sacred() -> Story:
    centre, path = SACRED_CENTRE_VARIABLE, SACRED_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    gate = _prose("""
        Every season more pilgrims come to [target_location.GetNameWithNoTooltip]. They sleep in
        the lanes, they leave offerings at the old stones and they carry the name of the place
        back to villages the court has never heard of. The priests of the shrine say the place
        has outgrown its walls. The stewards say it has outgrown the treasury.
    """)
    prospers = _prose("""
        The endowment has done what the stewards doubted. The road is paved, the hostels are
        full and the pilgrims who come to [target_location.GetNameWithNoTooltip] now stay to
        trade. The priests propose to crown the work with a great temple, and ask the court to
        begin it.
    """)
    murmur = _prose("""
        The tithe has filled the treasury, and the priests of
        [target_location.GetNameWithNoTooltip] have noticed. They say the offerings belong to
        those who made them and to those who tend the stones. Some of them say it from the
        pulpit, and the pilgrims listen.
    """)
    seat = _prose("""
        The high priest of [target_location.GetNameWithNoTooltip] now sits among the estates,
        and the old order of the shrine has a voice in the councils of the
        [ROOT.GetCountry.GetFlavorRank]. The priests are grateful. The others ask what the price
        of a seat will be.
    """)
    nodes = (
        Node(
            1,
            "Pilgrims at the Gate",
            gate,
            (
                Option(
                    "a",
                    "Endow the shrine and the road that leads to it.",
                    (_gold(-3), _location(centre, "rnw_sacred_endowment", 20), _set(path, 1)),
                    50,
                    Follow(2, (30, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Tithe the offerings for the treasury.",
                    (_gold(3), "add_stability = stability_weak_penalty", _set(path, 2)),
                    30,
                    Follow(3, (24, 48)),
                ),
                Option(
                    "c",
                    "Give the high priest of the shrine a seat of his own among the estates.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        _set(SACRED_PRIVILEGE_VARIABLE, 1),
                        _set(path, 3),
                    ),
                    20,
                    Follow(4, (24, 60)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Shrine Prospers",
            prospers,
            (
                Option(
                    "a",
                    "Raise the great temple.",
                    (_gold(-4), _location(centre, "rnw_sacred_great_temple", 40), *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Let the offerings pay for the road and nothing more.",
                    (_gold(2), "add_stability = stability_weak_bonus", *end),
                    45,
                ),
            ),
            requires=_path_is(path, 1),
        ),
        Node(
            3,
            "The Priests Murmur",
            murmur,
            (
                Option(
                    "a",
                    "Return a part of the tithe to the shrine.",
                    (_gold(-2), "add_stability = stability_mild_bonus", *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Hold the tithe and answer the pulpits.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        "add_prestige = prestige_weak_penalty",
                        *end,
                    ),
                    45,
                ),
            ),
            requires=_path_is(path, 2),
        ),
        Node(
            4,
            "A Priesthood With a Seat",
            seat,
            (
                Option(
                    "a",
                    "Welcome the priesthood into the councils.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Confine its power to the shrine and its lands.",
                    (
                        _location(centre, "rnw_sacred_endowment", 20),
                        f"remove_variable = {SACRED_PRIVILEGE_VARIABLE}",
                        *end,
                    ),
                    45,
                ),
            ),
            requires=_path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_sacred_endowment",
            LOCATION,
            Source(BUILDING, "great_temple_of_tenochtitlan", "modifier"),
            "Endowed Shrine",
            "An endowed shrine and a paved road draw pilgrims, and the priests grow in standing.",
        ),
        Modifier(
            "rnw_sacred_great_temple",
            LOCATION,
            Source(BUILDING, "great_temple_of_tenochtitlan", "modifier"),
            "The Great Temple",
            "A temple raised over the old stones holds the faith of the whole country.",
        ),
    )
    privileges = (
        Privilege(
            "rnw_sacred_priesthood",
            CLERGY,
            SACRED_PRIVILEGE_VARIABLE,
            Source(PRIVILEGE, "hurin_qusqu_privilege", "country_modifier"),
            "High Priesthood of the Shrine",
            "The high priest of the shrine serves the faith directly and sits among the estates.",
        ),
    )
    return Story("sacred_centre", "rnw_sacred", centre, path, nodes, modifiers, privileges)


STORIES: Final[tuple[Story, ...]] = (_river(), _sacred())


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
        gate += _lines(node.requires, "\t\t")
        head = [
            f"{event} = {{\n",
            "\ttype = country_event\n",
            f"\ttitle = {event}.title\n",
            f"\tdesc = {event}.desc\n",
            "\toutcome = neutral\n\n",
            f"\ttrigger = {{\n{gate}\t}}\n\n",
            "\timmediate = {\n",
            f"\t\tvar:{centre} ?= {{ save_scope_as = target_location }}\n",
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
