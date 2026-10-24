"""The game's own records for the extraordinary societies other than the empire (R7d).

NOT GAME VALIDATED. ``rnw.archetypes`` decides which polities form a sea league, a highland
confederation, a fractured realm or a sacred centre. This module reads what the vanilla 1337 setup
gives them and writes it, each with a precedent in the setup of the Americas or the Old World
[V-LOCAL C251]:

* **Republic** (sea league): Tlaxcala is the one American republic. Its template is
  ``amerindian_advanced_republic_not_nahuatl_no_coast`` and its entry adds ``type = republic`` and
  ``heir_selection = oligarchic_elective``. The league's members take the same.
* **Alliances** (sea league): ``scripted_mutual = { ... type = alliance }`` of ``12_diplomacy``, 22
  of them in the Old World; the ring of a league gives every member two.
* **Tribal confederation** (highland): the five Haudenosaunee nations, landed tribes of 3 to 11
  locations, are members of an ``add_international_organization`` of that type in
  ``15_international_organizations`` and write the same ``currency_data``.
* **Rivals** (fractured realm, sacred centre): ``rival = { first second }`` of ``20_rivals``, as the
  Burke feud of Connacht, four countries that are each other's rivals.
* **Theocracy** (sacred centre): Tibet and Venda are the 1337 theocracies of a faith that is not
  Christian, both with ``heir_selection = theocratic_elective``.
* **Societal values**: a country's government block sets its position on the game's axes; vanilla's
  American templates range from -90 to 60 on ``land_vs_naval``. The league leans to the naval end,
  the centre to the spiritualist and traditionalist end, never beyond what a vanilla American
  template already holds. Each end has a cost in the game's own definition.

Pure functions on texts, like ``eu5_empires``; all arithmetic is integer.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.archetypes import (
    FRACTURED_REALM,
    HIGHLAND_CONFEDERATION,
    KINDS,
    SACRED_CENTRE,
    SEA_LEAGUE,
)
from rnw.eu5_empires import written_discoveries
from rnw.eu5_technology import american_states, written_records
from rnw.pdx import Block, Entry, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

HEADERS: Final[dict[str, str]] = {
    "alliances": "\n\t# RNW generated sea leagues\n",
    "rivals": "\n\t# RNW generated rivalries\n",
    "confederations": "\n\t# RNW generated confederations\n",
}
CONFEDERATION: Final[str] = "tribal_confederation"
ALLIANCE: Final[str] = "alliance"
REPUBLIC: Final[str] = "republic"
THEOCRACY: Final[str] = "theocracy"
# The axes each kind leans along, and the end it leans to: "high" is the right pole of the axis
# (naval), "low" the left (spiritualist, traditionalist) [V-LOCAL C251]. The axes whose
# definitions hold an age (``mercantilism_vs_free_trade``, ``outward_vs_inward``) are left out,
# and so is ``aristocracy_vs_plutocracy``: the republic template already holds the vanilla
# American extreme of it.
AXES: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    SEA_LEAGUE: (("land_vs_naval", "high"),),
    SACRED_CENTRE: (("spiritualist_vs_humanist", "low"), ("traditionalist_vs_innovative", "low")),
}
SLIDER_BOUND: Final[int] = 100
INTEGER: Final[re.Pattern[str]] = re.compile(r"-?\d+")
POLITY_OWNING: Final[tuple[str, ...]] = ("own_control_core", "own_control_integrated")


class ArchetypeError(ValueError):
    """Vanilla data an extraordinary society is calibrated on is missing or inconsistent."""


@dataclass(frozen=True, slots=True, eq=False)
class ArchetypeCalibration:
    """What the vanilla data gives the four societies: governments, organisation, positions."""

    republic_include: str
    republic_government: tuple[tuple[str, str], ...]
    republic_level: int
    theocracy: tuple[tuple[str, str], ...]
    confederation_date: str
    cohesion: tuple[tuple[str, int], ...]
    confederate_density: int
    sliders: Mapping[str, tuple[tuple[str, int], ...]]
    alliances: int
    rivals: int
    confederations: int


def _includes(block: Block) -> list[str]:
    """Templates a country entry includes, the exploration templates (``expl_``) left out."""
    return [
        name
        for include in block.find("include")
        if isinstance(include.value, str)
        if not (name := include.value.strip('"')).startswith("expl_")
    ]


def _words(block: Block | None) -> list[str]:
    return [word.value for word in block.words() if isinstance(word.value, str)] if block else []


def _entries(block: Block | None, key: str) -> list[Entry]:
    return list(block.find(key)) if block is not None else []


def republic_template(
    setup_text: str,
    american: Collection[str],
    governments: Mapping[str, tuple[tuple[str, str], ...]],
    levels: Mapping[str, int],
) -> tuple[str, tuple[tuple[str, str], ...], int]:
    """Template, government fields and level of vanilla's American republic.

    Fails unless the American republics share one template and the generator can write its
    government (it sets a type, itself or through the entries that use it).
    """
    found: set[str] = set()
    for _, block in american_states(setup_text, american):
        government = block.block("government")
        kind = government.first("type") if government is not None else None
        if kind is not None and kind.value == REPUBLIC:
            found |= set(_includes(block))
    if len(found) != 1:
        message = f"The vanilla American republics use {len(found)} templates, not one"
        raise ArchetypeError(message)
    name = next(iter(found))
    fields = governments.get(name, ())
    if (("type", REPUBLIC)) not in fields:
        message = f"The template {name} of the American republic gives no republic government"
        raise ArchetypeError(message)
    return name, fields, levels.get(name, 0)


def theocracy_government(
    setup_text: str, government_texts: Sequence[str]
) -> tuple[tuple[str, str], ...]:
    """The government fields of vanilla's theocracies that write a heir selection.

    The heir selection is the one such entries write most often, and the government types must
    allow it: Tibet and Venda write ``theocratic_elective`` and are not Christian.
    """
    holder = parse(setup_text).block("countries", "countries")
    heirs: Counter[str] = Counter()
    for entry in holder.entries if holder is not None else []:
        government = entry.value.block("government") if isinstance(entry.value, Block) else None
        kind = government.first("type") if government is not None else None
        heir = government.first("heir_selection") if government is not None else None
        if (
            kind is not None
            and kind.value == THEOCRACY
            and heir is not None
            and isinstance(heir.value, str)
        ):
            heirs[heir.value] += 1
    if not heirs:
        message = "No vanilla theocracy writes a heir selection"
        raise ArchetypeError(message)
    heir = min(heirs, key=lambda name: (-heirs[name], name))
    allowed = {
        entry.value
        for text in government_texts
        for entry in _entries(parse(text).block(THEOCRACY), "heir_selection")
        if isinstance(entry.value, str)
    }
    if heir not in allowed:
        message = f"The government type {THEOCRACY} does not allow the heir selection {heir}"
        raise ArchetypeError(message)
    return (("type", THEOCRACY), ("heir_selection", heir))


def _currency(block: Block) -> tuple[tuple[str, int], ...]:
    held = block.block("currency_data")
    return tuple(
        (entry.key, int(entry.value))
        for entry in (held.entries if held is not None else [])
        if entry.key is not None and isinstance(entry.value, str) and INTEGER.fullmatch(entry.value)
    )


def confederation_calibration(
    io_text: str,
    setup_text: str,
    american: Collection[str],
    io_type_texts: Sequence[str],
    pops: Mapping[str, Sequence[tuple[str, int, str, str]]],
) -> tuple[tuple[tuple[str, int], ...], int, int]:
    """The ``currency_data`` of vanilla's American confederates, their number and their density.

    The density is the milli-pops a location of theirs holds (``pops``: the 1337 pops by location).

    A confederation is American if every member is a landed American country. The type must be
    defined, and the currency the members write is the one most of them write; it must hold
    ``tribal_cohesion``.
    """
    if not any(
        entry.key == CONFEDERATION for text in io_type_texts for entry in parse(text).entries
    ):
        message = f"No international organization type {CONFEDERATION} is defined"
        raise ArchetypeError(message)
    landed = dict(american_states(setup_text, american))
    manager = parse(io_text).block("international_organization_manager")
    members: list[list[str]] = []
    for entry in manager.find("add_international_organization") if manager is not None else ():
        if not isinstance(entry.value, Block):
            continue
        kind = entry.value.first("type")
        names = _words(entry.value.block("members"))
        if kind is not None and kind.value == CONFEDERATION and names and set(names) <= set(landed):
            members.append(names)
    if not members:
        message = f"No American {CONFEDERATION} is set up in 1337"
        raise ArchetypeError(message)
    currencies = Counter(_currency(landed[tag]) for names in members for tag in names)
    best = min(currencies, key=lambda value: (-currencies[value], value))
    if not any(key == "tribal_cohesion" for key, _ in best):
        message = f"The American confederates write no tribal_cohesion in {best}"
        raise ArchetypeError(message)
    locations = [
        place
        for names in members
        for tag in names
        for place in _words(landed[tag].block("own_control_core"))
    ]
    held = sum(row[1] for place in locations for row in pops.get(place, ()))
    return best, len(members), held // max(1, len(locations))


def american_includes(setup_text: str, american: Collection[str]) -> set[str]:
    """Templates the vanilla American countries, landed or pop, include."""
    holder = parse(setup_text).block("countries", "countries")
    found: set[str] = set()
    for entry in holder.entries if holder is not None else []:
        if not isinstance(entry.value, Block):
            continue
        held = [
            word
            for key in (*POLITY_OWNING, "add_pops_from_locations")
            for word in _words(entry.value.block(key))
        ]
        if held and set(held) <= set(american):
            found |= set(_includes(entry.value))
    return found


def _axis_value(text: str, axis: str) -> int | None:
    government = parse(text).block("government")
    entry = government.first(axis) if government is not None else None
    if entry is None or not isinstance(entry.value, str) or not INTEGER.fullmatch(entry.value):
        return None
    return int(entry.value)


def slider_targets(
    templates: Mapping[str, str], used: Collection[str], value_texts: Sequence[str]
) -> dict[str, tuple[tuple[str, int], ...]]:
    """The positions each kind takes on its axes: the vanilla American extreme in its direction.

    A position beyond what any vanilla American template holds is never written, and an axis
    the game does not define fails the build.
    """
    defined = {
        entry.key
        for text in value_texts
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    }
    targets: dict[str, tuple[tuple[str, int], ...]] = {}
    for kind, axes in AXES.items():
        chosen: list[tuple[str, int]] = []
        for axis, end in axes:
            if axis not in defined:
                message = f"The societal value {axis} is not defined"
                raise ArchetypeError(message)
            values = [
                value
                for name in sorted(used)
                if name in templates and (value := _axis_value(templates[name], axis)) is not None
            ]
            if not values:
                message = f"No vanilla American template sets {axis}"
                raise ArchetypeError(message)
            target = max(values) if end == "high" else min(values)
            if abs(target) > SLIDER_BOUND:
                message = f"The position {target} on {axis} is out of range"
                raise ArchetypeError(message)
            chosen.append((axis, target))
        targets[kind] = tuple(chosen)
    return targets


def archetype_calibration(  # noqa: PLR0913 - the calibration reads every vanilla file it names.
    *,
    setup_text: str,
    diplomacy_text: str,
    rivals_text: str,
    io_text: str,
    american: Collection[str],
    governments: Mapping[str, tuple[tuple[str, str], ...]],
    levels: Mapping[str, int],
    templates: Mapping[str, str],
    government_texts: Sequence[str],
    value_texts: Sequence[str],
    io_type_texts: Sequence[str],
    pops: Mapping[str, Sequence[tuple[str, int, str, str]]],
    year: str,
) -> ArchetypeCalibration:
    """Republic, theocracy, confederation, positions and the counts of vanilla's precedents.

    Fails if a vanilla value is missing, or if vanilla's setup holds no alliance or rival record
    to take the form of the generated ones from.
    """
    name, fields, level = republic_template(setup_text, american, governments, levels)
    cohesion, confederations, density = confederation_calibration(
        io_text, setup_text, american, io_type_texts, pops
    )
    alliances = len(written_pairs(diplomacy_text, "scripted_mutual", ALLIANCE))
    rivals = len(written_pairs(rivals_text, "rival"))
    if not alliances or not rivals:
        message = "Vanilla's 1337 setup holds no alliance or no rival record to follow"
        raise ArchetypeError(message)
    return ArchetypeCalibration(
        republic_include=name,
        republic_government=fields,
        republic_level=level,
        theocracy=theocracy_government(setup_text, government_texts),
        confederation_date=f"{year}.1.1",
        cohesion=cohesion,
        confederate_density=density,
        sliders=slider_targets(templates, american_includes(setup_text, american), value_texts),
        alliances=alliances,
        rivals=rivals,
        confederations=confederations,
    )


def government_fields(
    base: Sequence[tuple[str, str]],
    fields: Sequence[tuple[str, str]],
    sliders: Sequence[tuple[str, int]],
) -> tuple[tuple[str, str], ...]:
    """A country's government fields with ``fields`` in place of the same keys and the positions."""
    replaced = {key for key, _ in fields} | {key for key, _ in sliders}
    return (
        *((key, value) for key, value in base if key not in replaced),
        *fields,
        *((key, str(value)) for key, value in sliders),
    )


def partner_knowledge(
    pairs: Sequence[tuple[str, str]], capital_areas: Mapping[str, str]
) -> dict[str, frozenset[str]]:
    """The areas each holder of a relation has to have discovered: those of its partners' capitals.

    The game warns of a scripted relation toward a country whose capital the holder has not
    discovered (C170); a generated country knows its religion zone and its own areas only.
    """
    needed: dict[str, set[str]] = {}
    for holder, partner in pairs:
        needed.setdefault(holder, set()).add(capital_areas[partner])
    return {tag: frozenset(areas) for tag, areas in needed.items()}


def merge_knowledge(*maps: Mapping[str, frozenset[str]]) -> dict[str, frozenset[str]]:
    """The union of several maps of discovered areas."""
    merged: dict[str, set[str]] = {}
    for each in maps:
        for tag, areas in each.items():
            merged.setdefault(tag, set()).update(areas)
    return {tag: frozenset(areas) for tag, areas in merged.items()}


def alliance_lines(pairs: Sequence[tuple[str, str]]) -> str:
    """Entries for ``diplomacy_manager = { ... }`` of ``12_diplomacy.txt``."""
    body = "".join(
        f"\tscripted_mutual = {{ first = {first} second = {second} type = {ALLIANCE} }}\n"
        for first, second in pairs
    )
    return HEADERS["alliances"] + body if body else ""


def rival_lines(pairs: Sequence[tuple[str, str]]) -> str:
    """Entries for ``diplomacy_manager = { ... }`` of ``20_rivals.txt``."""
    body = "".join(
        f"\trival = {{ first = {first} second = {second} }}\n" for first, second in pairs
    )
    return HEADERS["rivals"] + body if body else ""


def confederation_lines(date: str, groups: Sequence[Sequence[str]]) -> str:
    """Entries for ``international_organization_manager = { ... }`` of the organization setup."""
    lines = [
        line
        for members in groups
        for line in (
            "\tadd_international_organization = {",
            f"\t\ttype = {CONFEDERATION}",
            f"\t\tcreation_date = {date}",
            f"\t\tmembers = {{ {' '.join(members)} }}",
            "\t}",
        )
    ]
    body = "".join(f"{line}\n" for line in lines)
    return HEADERS["confederations"] + body if body else ""


def currency_lines(cohesion: Sequence[tuple[str, int]]) -> str:
    """The ``currency_data`` block of a confederate's country record."""
    body = "".join(f"\t\t\t{key} = {value}\n" for key, value in cohesion)
    return f"\t\tcurrency_data = {{\n{body}\t\t}}\n"


def _fields(entry_value: str | Block) -> dict[str, str]:
    if not isinstance(entry_value, Block):
        return {}
    return {
        entry.key: entry.value
        for entry in entry_value.entries
        if entry.key is not None and isinstance(entry.value, str)
    }


def written_pairs(text: str, key: str, kind: str = "") -> list[tuple[str, str]]:
    """(first, second) of the ``key`` records of ``diplomacy_manager`` of the type ``kind``."""
    holder = parse(text).block("diplomacy_manager")
    found: list[tuple[str, str]] = []
    for entry in holder.find(key) if holder is not None else ():
        fields = _fields(entry.value)
        if not kind or fields.get("type") == kind:
            found.append((fields.get("first", ""), fields.get("second", "")))
    return found


def written_confederations(text: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """(type, creation date, members) of the confederations of the organization setup."""
    manager = parse(text).block("international_organization_manager")
    found: list[tuple[str, str, tuple[str, ...]]] = []
    for entry in manager.find("add_international_organization") if manager is not None else ():
        if not isinstance(entry.value, Block):
            continue
        fields = _fields(entry.value)
        if fields.get("type") == CONFEDERATION:
            found.append(
                (
                    CONFEDERATION,
                    fields.get("creation_date", ""),
                    tuple(_words(entry.value.block("members"))),
                )
            )
    return found


def named_organizations(text: str, tags: Collection[str]) -> list[str]:
    """The types of the organizations that name one of ``tags`` among their members."""
    manager = parse(text).block("international_organization_manager")
    return [
        _fields(entry.value).get("type", "")
        for entry in (manager.find("add_international_organization") if manager is not None else ())
        if isinstance(entry.value, Block) and set(_words(entry.value.block("members"))) & set(tags)
    ]


@dataclass(frozen=True, slots=True)
class WrittenCountry:
    """What a country record of ``10_countries.txt`` writes of its government and its land."""

    government: dict[str, str]
    currency: tuple[tuple[str, int], ...]
    pop: bool
    owned: tuple[str, ...]
    capital: str


def written_countries(text: str, tags: Collection[str]) -> dict[str, WrittenCountry]:
    """Government fields, currency, holding and capital of the country records of ``tags``."""
    holder = parse(text).block("countries", "countries")
    found: dict[str, WrittenCountry] = {}
    for entry in holder.entries if holder is not None else []:
        if entry.key is None or entry.key not in tags or not isinstance(entry.value, Block):
            continue
        government = entry.value.block("government")
        kind = entry.value.first("type")
        capital = entry.value.first("capital")
        found[entry.key] = WrittenCountry(
            government=_fields(government) if government is not None else {},
            currency=_currency(entry.value),
            pop=kind is not None and kind.value == "pop",
            owned=tuple(_words(entry.value.block("own_control_core"))),
            capital=capital.value if capital is not None and isinstance(capital.value, str) else "",
        )
    return found


def archetype_report(
    calibration: ArchetypeCalibration,
    options: Mapping[str, int],
    groups: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """The ``archetypes`` section of ``report.json``."""
    return {
        "calibration": {
            "republic_template": calibration.republic_include,
            "republic_government": dict(calibration.republic_government),
            "theocracy": dict(calibration.theocracy),
            "confederation_date": calibration.confederation_date,
            "confederate_currency": dict(calibration.cohesion),
            "confederate_density_milli": calibration.confederate_density,
            "positions": {kind: dict(axes) for kind, axes in sorted(calibration.sliders.items())},
            "vanilla_alliances": calibration.alliances,
            "vanilla_rivals": calibration.rivals,
            "vanilla_confederations": calibration.confederations,
        },
        "options": dict(options),
        "groups": [dict(group) for group in groups],
    }


@dataclass(frozen=True, slots=True)
class Expected:
    """A generated country as the plan has it, for the checks of the written files."""

    tag: str
    state: bool
    landed: bool
    include: str
    government: tuple[tuple[str, str], ...]
    currency: tuple[tuple[str, int], ...]
    members: tuple[str, ...]
    capital: str
    archetype: str
    free: bool


@dataclass(frozen=True, slots=True)
class Bonds:
    """The groups (kind and tags, the hub first) and relations of the plan, as tags."""

    groups: tuple[tuple[str, tuple[str, ...]], ...]
    alliances: tuple[tuple[str, str], ...]
    rivals: tuple[tuple[str, str], ...]
    confederations: tuple[tuple[str, ...], ...]

    def knowledge(self) -> list[tuple[str, str]]:
        """(holder, partner): who has to have discovered whose capital."""
        pairs = [*self.alliances, *((b, a) for a, b in self.alliances), *self.rivals]
        for members in self.confederations:
            pairs += [(a, b) for a in members for b in members if a != b]
        return pairs


def _unordered(pairs: Sequence[tuple[str, str]]) -> set[tuple[str, str]]:
    return {(min(a, b), max(a, b)) for a, b in pairs}


def _record_problems(text: str, countries: Mapping[str, Expected]) -> list[str]:
    """The templates, governments, holdings and currency the records write are the plan's."""
    written = written_countries(text, set(countries))
    includes = written_records(text, set(countries))
    problems: list[str] = []
    for tag, expected in countries.items():
        record = written.get(tag)
        if record is None:
            problems.append(f"{tag} has no country record")
            continue
        if includes[tag][0] != [expected.include]:
            problems.append(f"{tag} does not write its template {expected.include}")
        if any(record.government.get(key) != value for key, value in expected.government):
            problems.append(f"{tag} writes the government {record.government}")
        if record.currency != expected.currency:
            problems.append(f"{tag} writes the currency {record.currency}")
        if expected.state or expected.landed:
            if record.pop or record.owned != expected.members or record.capital != expected.capital:
                problems.append(f"{tag} does not own its locations and its capital")
        elif not record.pop or record.owned:
            problems.append(f"{tag} owns locations as a tribe that holds pops")
    return problems


def _group_problems(
    bonds: Bonds, countries: Mapping[str, Expected], calibration: ArchetypeCalibration
) -> list[str]:
    """Groups are disjoint, free and of one kind; each kind's relations are its own."""
    problems: list[str] = []
    seen: set[str] = set()
    alliances = _unordered(bonds.alliances)
    rivals = set(bonds.rivals)
    for kind, tags in bonds.groups:
        members = [countries[tag] for tag in tags if tag in countries]
        if len(members) != len(tags) or len(set(tags)) != len(tags) or seen & set(tags):
            problems.append(f"The {kind} group {tags} repeats or lacks a country")
            continue
        seen |= set(tags)
        if kind not in KINDS or any(m.archetype != kind or not m.free for m in members):
            problems.append(f"The {kind} group {tags} holds a bound country or one of another kind")
            continue
        inside = {(a, b) for a in tags for b in tags if a != b}
        if kind == SEA_LEAGUE:
            ring = {(min(a, b), max(a, b)) for a, b in zip(tags, (*tags[1:], tags[0]), strict=True)}
            fields = dict(calibration.republic_government)
            if (
                not all(m.state and m.include == calibration.republic_include for m in members)
                or any(dict(m.government).get(k) != v for m in members for k, v in fields.items())
                or {pair for pair in alliances if set(pair) <= set(tags)} != ring
            ):
                problems.append(f"The sea league {tags} is not a ring of republics")
        elif kind == HIGHLAND_CONFEDERATION:
            if tags not in bonds.confederations or any(
                m.state or not m.landed or m.currency != calibration.cohesion for m in members
            ):
                problems.append(f"The confederation {tags} is not made of confederate tribes")
        elif kind == SACRED_CENTRE:
            fields = dict(calibration.theocracy)
            wanted = {(tags[0], other) for other in tags[1:]}
            if any(dict(members[0].government).get(k) != v for k, v in fields.items()) or {
                pair for pair in rivals if set(pair) <= set(tags)
            } != wanted | {(b, a) for a, b in wanted}:
                problems.append(f"The sacred centre {tags} is not a theocracy with rivals")
        elif {pair for pair in rivals if set(pair) <= set(tags)} - inside:
            problems.append(f"The fractured realm {tags} has rivals outside it")
    return problems


def _relation_problems(bonds: Bonds) -> list[str]:
    """Every alliance and rivalry joins members of one group of the kind that has them."""
    group_of = {tag: (kind, tags) for kind, tags in bonds.groups for tag in tags}
    problems: list[str] = []
    for first, second in bonds.alliances:
        if group_of.get(first, ("", ()))[0] != SEA_LEAGUE or group_of.get(second) != group_of.get(
            first
        ):
            problems.append(f"The alliance {first} {second} does not join a sea league")
    for first, second in bonds.rivals:
        found = group_of.get(first, ("", ()))
        if found[0] not in {FRACTURED_REALM, SACRED_CENTRE} or group_of.get(second) != found:
            problems.append(f"The rivalry {first} {second} does not join a realm or a centre")
        if (second, first) not in bonds.rivals:
            problems.append(f"The rivalry {first} {second} is not returned")
    problems += [
        f"The confederation {members} is not a group"
        for members in bonds.confederations
        if any(group_of.get(tag, ("", ()))[1] != members for tag in members)
    ]
    if len(_unordered(bonds.alliances)) != len(bonds.alliances):
        problems.append("The alliances repeat a pair")
    if len(set(bonds.rivals)) != len(bonds.rivals):
        problems.append("The rivalries repeat a pair")
    return problems


def _file_problems(  # noqa: PLR0913 - three files, each with its plan and its vanilla text.
    texts: Mapping[str, str],
    originals: Mapping[str, str],
    *,
    bonds: Bonds,
    calibration: ArchetypeCalibration,
    generated: Collection[str],
    gone: Collection[str],
) -> list[str]:
    """The setup files hold the planned alliances, rivalries and confederations, once each, and
    the Old World's entries of vanilla."""
    names = set(generated)
    problems: list[str] = []
    for name, key, kind, planned in (
        ("12_diplomacy.txt", "scripted_mutual", ALLIANCE, _unordered(bonds.alliances)),
        ("20_rivals.txt", "rival", "", set(bonds.rivals)),
    ):
        found = written_pairs(texts[name], key, kind)
        added = [pair for pair in found if set(pair) & names]
        counted = _unordered(added) if key != "rival" else set(added)
        if len(added) != len(counted) or counted != planned:
            problems.append(f"{name} repeats or lacks a generated record")
        kept = [
            pair for pair in written_pairs(originals[name], key, kind) if not set(pair) & set(gone)
        ]
        if [pair for pair in found if not set(pair) & names] != kept:
            problems.append(f"The Old World records of {name} differ from vanilla")
    organizations = "15_international_organizations.txt"
    wanted = [
        (CONFEDERATION, calibration.confederation_date, tuple(m)) for m in bonds.confederations
    ]
    found_io = [row for row in written_confederations(texts[organizations]) if set(row[2]) & names]
    if sorted(found_io) != sorted(wanted) or named_organizations(texts[organizations], names) != [
        CONFEDERATION
    ] * len(wanted):
        problems.append("The organizations repeat or lack a planned confederation")
    return problems


def _knowledge_problems(text: str, bonds: Bonds, capital_areas: Mapping[str, str]) -> list[str]:
    """Every holder of a relation has discovered the area of its partner's capital."""
    known = written_discoveries(text, set(capital_areas))
    return [
        f"{holder} is bound to {partner} without discovering its capital"
        for holder, partner in bonds.knowledge()
        if capital_areas[partner] not in known.get(holder, ("", frozenset()))[1]
    ]


def archetype_problems(  # noqa: PLR0913 - every record of the plan is checked on the final texts.
    *,
    texts: Mapping[str, str],
    originals: Mapping[str, str],
    countries: Mapping[str, Expected],
    bonds: Bonds,
    calibration: ArchetypeCalibration,
    capital_areas: Mapping[str, str],
    gone: Collection[str],
) -> list[str]:
    """What is wrong in the written setup of the extraordinary societies, if anything.

    ``texts`` and ``originals`` hold the final and the vanilla text of ``10_countries.txt``,
    ``12_diplomacy.txt``, ``20_rivals.txt`` and ``15_international_organizations.txt`` by file name;
    ``gone`` holds the tags and locations the export removed.
    """
    return [
        *_record_problems(texts["10_countries.txt"], countries),
        *_group_problems(bonds, countries, calibration),
        *_relation_problems(bonds),
        *_file_problems(
            texts,
            originals,
            bonds=bonds,
            calibration=calibration,
            generated=set(countries),
            gone=gone,
        ),
        *_knowledge_problems(texts["10_countries.txt"], bonds, capital_areas),
    ]
