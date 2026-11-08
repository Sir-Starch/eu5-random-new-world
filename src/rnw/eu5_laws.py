"""Every law a generated state sees at the start holds a policy where vanilla's countries do.

The owner's sitting of 2026-11-08 found a generated duchy with laws of "No Policy enacted": each
costs political power and months to enact. The installation says why [V-LOCAL, EU5 1.4.7, Steam
build 26377361]:

* A law that an advance unlocks (``unlock_law``) is shown once a country has the advance; any
  other law is shown when its ``potential`` holds. In the age of traditions an advance starts
  researched unless its ``starting_technology_level`` is above the country's (the comment at the
  top of ``advances/0_age_of_traditions.txt``); here an advance also needs every advance it
  ``requires``, and an advance with a ``potential`` of its own is left out. An advance with an
  ``allow`` starts researched only when it holds: ``legalism_advance`` asks for the embraced
  institution of legalism, which no generated country has, and the game set the feudal de jure
  law of 51 generated monarchies and the republican foundation of 31 republics behind it with
  ``Setting a law … that the country doesn't have the advance for`` ([V-GAME] the owner's ATDT
  sitting, 2026-11-08, C522).
* A law that an advance unlocks is not written at a level where vanilla's countries of the same
  government hold laws that advances unlock but never this one. The game removed the aristocratic
  court of all 51 generated monarchies of level 2 (``Removing invalid policy … at game start``,
  the same sitting) though the court's advance needs only writing and codified laws; vanilla's
  190 monarchies of level 2 hold its coinage, distribution of power and mining laws and no royal
  court customs, and 999 of its 1,189 of level 3 hold them. A level whose vanilla countries hold
  no such law (its monarchies of level 0 and 1 hold two laws, neither unlocked) or that vanilla
  lacks (theocracies below 3) is no evidence: the advances decide. The engine's reason is
  [UNKNOWN]; vanilla's 1337 is the evidence.
* The generated states take the vanilla American templates, made for level 2, and write their
  own level (0 to 3, ``natives.md``). Those templates set no royal court customs, feudal de jure
  law or cultural traditions, which 999 of the 1,189 vanilla monarchies of level 3 set; the
  theocracy of a sacred centre writes no template and two laws.
* Vanilla completes a template with the country's own ``laws`` block (``DAN`` sets its legal code
  over ``catholic_monarchy``); the game merges the two.

A law the template leaves without a policy gets one here, at construction. The candidates are the
policies that vanilla's 1337 countries of the same government type hold for that law and whose
``potential`` and ``allow`` hold for the country. The chosen one drifts the country's societal
values (``monthly_towards_<pole>``) furthest toward where the country already stands; then the
one vanilla holds most often; then the name. A condition this reader cannot decide (an estate's
power, a goods supply, a scripted flag) counts as false: such a law is not added and such a
policy not chosen, so nothing is written that the game might refuse.
"""

from __future__ import annotations

import operator
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from rnw.pdx import Block, Entry, parse

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

FIRST_AGE: Final[str] = "age_1_traditions"
ORGANIZATION: Final[str] = "international_organization"
LAW_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "law_category",
        "potential",
        "allow",
        "locked",
        "requires_vote",
        "law_religion_group",
        "law_gov_group",
        "law_country_group",
        "unique",
        "custom_tags",
        "show_tags_in_ui",
        "type",
    }
)
DRIFT: Final[str] = "monthly_towards_"
# A policy is a mainstream choice when at least one in this many vanilla holders of the law hold
# it: civil society (41 of 854 monarchies) is, the itinerant court (9 of 853) and a regional code
# held by one country are not.
MAINSTREAM: Final[int] = 50
COMPARISONS: Final[dict[str, Callable[[int, int], bool]]] = {
    ">=": operator.ge,
    ">": operator.gt,
    "<=": operator.le,
    "<": operator.lt,
    "=": operator.eq,
    "==": operator.eq,
}


class LawError(ValueError):
    """The installed laws, advances or templates lack what the completion reads."""


@dataclass(frozen=True, slots=True)
class Policy:
    """One policy of a law: its conditions and the poles its modifiers drift toward."""

    name: str
    potential: Block | None
    allow: Block | None
    drifts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Law:
    name: str
    potential: Block | None
    policies: tuple[Policy, ...]


@dataclass(frozen=True, slots=True)
class Advance:
    name: str
    level: int | None
    requires: tuple[str, ...]
    gated: bool
    allow: Block | None = None


@dataclass(frozen=True, slots=True, eq=False)
class LawBook:
    """What the installation says about laws at the start, and what vanilla's 1337 holds."""

    laws: Mapping[str, Law]
    unlocked_by: Mapping[str, tuple[str, ...]]
    advances: Mapping[str, Advance]
    templates: Mapping[str, Block]
    held: Mapping[tuple[str, str], Counter[str]]
    axes: tuple[str, ...]
    # The levels at which vanilla's countries of a government hold a law
    # (``starting_technology_level``, their own or a template's).
    held_levels: Mapping[tuple[str, str], frozenset[int]] = field(
        default_factory=dict[tuple[str, str], frozenset[int]]
    )


@dataclass(frozen=True, slots=True)
class Facts:
    """What the completion knows of a country at the start."""

    government: str
    level: int
    religion: str
    culture: str
    values: Mapping[str, int]
    laws: Mapping[str, str]


def _blocks(texts: Sequence[str]) -> list[tuple[str, Block]]:
    return [
        (entry.key, entry.value)
        for text in texts
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    ]


def _drifts(policy: Block) -> tuple[str, ...]:
    found: list[str] = []
    for modifier in policy.find("country_modifier"):
        if isinstance(modifier.value, Block):
            found.extend(
                entry.key.removeprefix(DRIFT)
                for entry in modifier.value.entries
                if entry.key is not None and entry.key.startswith(DRIFT)
            )
    return tuple(found)


def _laws(texts: Sequence[str]) -> dict[str, Law]:
    found: dict[str, Law] = {}
    for name, body in _blocks(texts):
        kind = body.first("type")
        if kind is not None and kind.value == ORGANIZATION:
            continue
        policies = tuple(
            Policy(
                entry.key,
                entry.value.block("potential"),
                entry.value.block("allow"),
                _drifts(entry.value),
            )
            for entry in body.entries
            if entry.key is not None
            and entry.key not in LAW_FIELDS
            and isinstance(entry.value, Block)
        )
        found[name] = Law(name, body.block("potential"), policies)
    return found


def _advances(texts: Sequence[str]) -> tuple[dict[str, Advance], dict[str, tuple[str, ...]]]:
    advances: dict[str, Advance] = {}
    unlocked: dict[str, list[str]] = {}
    for name, body in _blocks(texts):
        for entry in body.find("unlock_law"):
            if isinstance(entry.value, str):
                unlocked.setdefault(entry.value, []).append(name)
        age = body.first("age")
        if age is None or age.value != FIRST_AGE:
            continue
        level = body.first("starting_technology_level")
        advances[name] = Advance(
            name,
            int(str(level.value)) if level is not None else None,
            tuple(str(entry.value) for entry in body.find("requires")),
            body.block("potential") is not None,
            body.block("allow"),
        )
    return advances, {law: tuple(names) for law, names in unlocked.items()}


def _level(block: Block, templates: Mapping[str, Block], trail: tuple[str, ...] = ()) -> int | None:
    """A setup entry's ``starting_technology_level``: its own, else the highest of its includes'
    (as ``eu5_natives.template_levels`` reads the templates)."""
    own = block.first("starting_technology_level")
    if own is not None and isinstance(own.value, str) and own.value.isdigit():
        return int(own.value)
    found = [
        level
        for include in block.find("include")
        if (name := str(include.value).strip('"')) in templates and name not in trail
        if (level := _level(templates[name], templates, (*trail, name))) is not None
    ]
    return max(found) if found else None


def _resolve(
    block: Block, templates: Mapping[str, Block], trail: tuple[str, ...] = ()
) -> tuple[str, dict[str, str], dict[str, str]]:
    """The government type, laws and government fields of a setup entry with its includes."""
    kind, laws, fields = "", dict[str, str](), dict[str, str]()
    for include in block.find("include"):
        name = str(include.value).strip('"')
        if name in trail:
            message = f"The template {name} includes itself"
            raise LawError(message)
        if name not in templates:
            message = f"The template {name} is not installed"
            raise LawError(message)
        inner, more, extra = _resolve(templates[name], templates, (*trail, name))
        kind = inner or kind
        laws.update(more)
        fields.update(extra)
    government = block.block("government")
    if government is not None:
        for entry in government.entries:
            if entry.key == "laws" and isinstance(entry.value, Block):
                laws.update(
                    (law.key, str(law.value))
                    for law in entry.value.entries
                    if law.key is not None and isinstance(law.value, str)
                )
            elif entry.key is not None and isinstance(entry.value, str):
                fields[entry.key] = entry.value
        kind = fields.get("type", kind)
    return kind, laws, fields


def read_book(
    *,
    law_texts: Sequence[str],
    advance_texts: Sequence[str],
    templates: Mapping[str, str],
    setup_text: str,
    value_texts: Sequence[str],
) -> LawBook:
    """Read the laws, the advances of the first age, the templates and the 1337 setup."""
    laws = _laws(law_texts)
    advances, unlocked = _advances(advance_texts)
    if not laws or not advances:
        message = "The installation has no laws or no advances of the age of traditions"
        raise LawError(message)
    parsed = {name: parse(text) for name, text in templates.items()}
    holder = parse(setup_text).block("countries", "countries")
    if holder is None:
        message = "The 1337 setup has no countries"
        raise LawError(message)
    held: dict[tuple[str, str], Counter[str]] = {}
    held_levels: dict[tuple[str, str], set[int]] = {}
    for entry in holder.entries:
        if not isinstance(entry.value, Block) or entry.value.first("type") is not None:
            continue
        kind, written, _ = _resolve(entry.value, parsed)
        level = _level(entry.value, parsed)
        for law, policy in written.items():
            held.setdefault((kind, law), Counter())[policy] += 1
            if level is not None:
                held_levels.setdefault((kind, law), set()).add(level)
    axes = tuple(name for name, _ in _blocks(value_texts))
    return LawBook(
        laws,
        unlocked,
        advances,
        parsed,
        held,
        axes,
        {key: frozenset(found) for key, found in held_levels.items()},
    )


# --- A three-valued reading of the triggers the laws ask at the start ----------------------


def _value(word: object) -> str:
    return str(word).split(":", 1)[1] if ":" in str(word) else str(word)


def _all(results: list[bool | None]) -> bool | None:
    if False in results:
        return False
    return None if None in results else True


def _any(results: list[bool | None]) -> bool | None:
    if True in results:
        return True
    return None if None in results else False


def _none(results: list[bool | None]) -> bool | None:
    """``NOT``: none of ``results`` holds together (the negation of ``AND``)."""
    together = _all(results)
    return None if together is None else not together


def _compare(entry: Entry, actual: int) -> bool | None:
    test = COMPARISONS.get(entry.op or "")
    try:
        wanted = int(float(str(entry.value)))
    except ValueError:
        return None
    return None if test is None else test(actual, wanted)


def _entry(entry: Entry, facts: Facts) -> bool | None:  # noqa: C901, PLR0911, PLR0912 - one case per trigger.
    key, value = entry.key or "", entry.value
    if isinstance(value, Block):
        inner = [_entry(item, facts) for item in value.entries if item.key != "text"]
        if key in {"AND", "custom_tooltip", "trigger_if"}:
            return _all(inner)
        if key == "OR":
            return _any(inner)
        if key == "NOT":
            return _none(inner)
        if key == "NOR":
            together = _any(inner)
            return None if together is None else not together
        if key == "current_age_or_later":
            age = value.first("age")
            return age is not None and str(age.value) == FIRST_AGE
        if key == "pop_type_population_in_country":
            # [V-GAME 1.4.7, 2026-11-08] The laws of a generated duchy without a slave in its
            # locations listed slave conversion (screenshot 20261108045624): the game shows
            # the law at the start whatever the count.
            return True
        return None
    word = str(value)
    if key == "government_type":
        return _value(word) == facts.government
    if key == "has_tribal_government":
        return (facts.government == "tribe") == (word == "yes")
    if key == "religion":
        return _value(word) == facts.religion
    if key == "culture":
        return _value(word) == facts.culture
    if key in {"has_or_had_tag", "tag"}:
        return False
    if key == "current_age":
        return _value(word) == FIRST_AGE
    if key == "has_law":
        return word in facts.laws
    if key == "has_policy":
        return word in facts.laws.values()
    if key == "always":
        return word == "yes"
    if key.startswith("societal_value:"):
        position = facts.values.get(key.split(":", 1)[1])
        return None if position is None else _compare(entry, position)
    return None


def holds(block: Block | None, facts: Facts) -> bool | None:
    """Whether a trigger holds for the country at the start; ``None`` when undecided."""
    if block is None:
        return True
    return _all([_entry(entry, facts) for entry in block.entries])


# --- Which laws a country sees, and which policy it holds ----------------------------------


def _researched(book: LawBook, facts: Facts) -> set[str]:
    """The advances of the age of traditions the country starts with: within its level, with
    every advance they require, and with their ``allow`` holding (an undecided one does not)."""
    done: dict[str, bool] = {}

    def researched(name: str, trail: frozenset[str]) -> bool:
        if name in done:
            return done[name]
        advance = book.advances.get(name)
        ok = (
            advance is not None
            and name not in trail
            and not advance.gated
            and (advance.level is None or advance.level <= facts.level)
            and (advance.allow is None or holds(advance.allow, facts) is True)
            and all(researched(other, trail | {name}) for other in advance.requires)
        )
        done[name] = ok
        return ok

    return {name for name in book.advances if researched(name, frozenset())}


def held_at_level(book: LawBook, law: str, facts: Facts) -> bool:
    """Whether vanilla's 1337 admits ``law`` at the country's level: its countries of the same
    government and level hold it, or hold no law an advance unlocks (no evidence either way)."""

    def held(name: str) -> bool:
        return facts.level in book.held_levels.get((facts.government, name), frozenset())

    return held(law) or not any(held(name) for name in book.unlocked_by)


def shown(book: LawBook, facts: Facts) -> list[str]:
    """The laws the country sees at the start, in the installation's order."""
    researched = _researched(book, facts)
    return [
        name
        for name, law in book.laws.items()
        if holds(law.potential, facts) is True
        and (
            name not in book.unlocked_by
            or any(advance in researched for advance in book.unlocked_by[name])
        )
    ]


def _leaning(values: Mapping[str, int], axes: Sequence[str], pole: str) -> int:
    """How far the country stands toward ``pole`` (positive) or away from it."""
    for axis in axes:
        left, _, right = axis.partition("_vs_")
        if pole == left:
            return -values.get(axis, 0)
        if pole == right:
            return values.get(axis, 0)
    return 0


def choose(book: LawBook, law: str, facts: Facts) -> str:
    """The policy the country holds for ``law``, or ``""`` when no candidate is admissible.

    The candidates are the policies vanilla's countries of the government hold for the law, the
    ones a fiftieth of them hold first: a policy that a handful of vanilla countries hold is
    their own (a regional code, a dynasty's court), not a choice for any country."""
    held = book.held.get((facts.government, law), Counter[str]())
    total = sum(held.values())
    admissible = [
        policy
        for policy in book.laws[law].policies
        if held[policy.name] > 0
        and holds(policy.potential, facts) is True
        and holds(policy.allow, facts) is True
    ]
    candidates = [
        policy for policy in admissible if held[policy.name] * MAINSTREAM >= total
    ] or admissible
    if not candidates:
        return ""
    best = min(
        candidates,
        key=lambda policy: (
            -sum(_leaning(facts.values, book.axes, pole) for pole in policy.drifts),
            -held[policy.name],
            policy.name,
        ),
    )
    return best.name


def positions(book: LawBook, *, include: str, fields: Sequence[tuple[str, str]]) -> dict[str, int]:
    """Where a country stands on each societal value at the start: its template's positions with
    its own in their place (the game merges them as it merges laws)."""
    values: dict[str, str] = {}
    if include:
        if include not in book.templates:
            message = f"The template {include} is not installed"
            raise LawError(message)
        _, _, values = _resolve(book.templates[include], book.templates)
    values.update(fields)
    found: dict[str, int] = {}
    for axis in book.axes:
        if axis in values:
            try:
                found[axis] = int(values[axis])
            except ValueError:
                continue
    return found


def complete(  # noqa: PLR0913 - a country's template, own fields and identity.
    book: LawBook,
    *,
    include: str,
    fields: Sequence[tuple[str, str]],
    laws: Sequence[tuple[str, str]],
    level: int,
    religion: str,
    culture: str,
) -> tuple[tuple[str, str], ...]:
    """The country's own laws with a policy for every law it sees that its template leaves
    empty and that vanilla's countries of its government and level hold, in the order of the
    installation after the ones it already writes."""
    kind, inherited = "", dict[str, str]()
    if include:
        if include not in book.templates:
            message = f"The template {include} is not installed"
            raise LawError(message)
        kind, inherited, _ = _resolve(book.templates[include], book.templates)
    government = dict(fields).get("type", kind)
    if not government:
        message = f"A country of the template {include!r} has no government type"
        raise LawError(message)
    standing = positions(book, include=include, fields=fields)
    current = {**inherited, **dict(laws)}
    written = list(laws)
    facts = Facts(government, level, religion, culture, standing, current)
    for law in shown(book, facts):
        if law in current:
            continue
        if law in book.unlocked_by and not held_at_level(book, law, facts):
            # The game may refuse it at this level (the module's note); vanilla holds none.
            continue
        policy = choose(book, law, facts)
        if policy:
            written.append((law, policy))
            current[law] = policy
            facts = Facts(government, level, religion, culture, standing, current)
    return tuple(written)
