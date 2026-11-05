"""Portable society and regional summaries, rendered once for either window."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final, final

from rnw import history_text, translations, wording
from rnw.history_archive import AXES, UNWRITTEN
from rnw.history_model import Action
from rnw.history_values import AXES as VALUE_AXES
from rnw.history_values import SOURCE, poles

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.atlas import Atlas
    from rnw.history_archive import Archive, CountryFact
    from rnw.history_model import Society

SOURCES: Final[dict[str, str]] = {
    "history.title": "Society and history",
    "history.region": "Regional history",
    "history.none": "No recorded history",
    "history.profile": "Organization in 1337",
    "history.chronicle": "Chronicle",
    "history.relations": "Relationships and reasons",
    "history.inheritance": "Shared inheritances",
    "history.projected": "EU5: {relations}",
    "history.memory": "Memory: {reason}",
    "history.position": "Government: {government} · Rank: {rank} · Technology: {level}",
    "history.axis": "{axis}: {value} — {cause} ({year})",
    "history.shared": "{kind}: {members}",
    "history.changes": "{year} · Locations changing historical owner: {count}",
    "history.centralization": "Centralization",
    "history.authority": "Authority",
    "history.livelihood": "Livelihood",
    "history.exchange": "Exchange",
    "history.religious_authority": "Religious authority",
    "history.military": "Military orientation",
    "history.integration": "Integration",
    "history.tradition": "Tradition",
    "history.council": "Council",
    "history.ruler": "Personal rule",
    "history.sacred": "Sacred authority",
    "history.customary": "Customary authority",
    "history.farming": "Farming",
    "history.mixed": "Mixed subsistence",
    "history.mobile": "Mobile subsistence",
    "history.inward": "Local exchange",
    "history.overland": "Overland exchange",
    "history.coastal": "Coastal exchange",
    "history.balanced": "Balanced",
    "history.offensive": "Offensive",
    "history.defensive": "Defensive",
    "history.vassal": "Subject relationship",
    "history.alliance": "Alliance",
    "history.rival": "Rivalry",
    "history.guarantee": "Guarantee",
    "history.trade": "Exchange agreement",
    "history.great_empire": "Great empire",
    "history.sea_league": "Sea league",
    "history.highland_confederation": "Highland confederation",
    "history.sacred_centre": "Sacred centre",
    "history.fractured_realm": "Divided realm",
    "history.regional_power": "Regional power",
    "history.paramount": "Paramount realm",
    "history.ambitions": "Ambitions",
    "history.ambition": "{kind} — {name}: {status}",
    "history.fulfilled": "fulfilled",
    "history.unfulfilled": "not fulfilled",
    "history.monarchy": "Monarchy",
    "history.republic": "Republic",
    "history.theocracy": "Theocracy",
    "history.tribe": "Tribe",
    # The Tauri window's society panel (structured data, `dossier` and `place`).
    "history.tab_place": "Place",
    "history.tab_society": "Society",
    "history.tab_relations": "Relations",
    "history.origin": "Origin",
    "history.technology": "Technology {level}",
    "history.society_note": (
        "How this society was organized in 1337, and the event that last shaped each trait."
    ),
    "history.chronicle_note": "The most significant recorded events, oldest first.",
    "history.relations_note": (
        "The strongest remembered ties, with their reasons, and the current agreements."
    ),
    "history.remembered": "Remembered ties",
    "history.agreements": "Other agreements",
    "history.lord": "Overlord",
    "history.subject": "Subject",
    "history.guarantor": "Guarantor",
    "history.protected": "Guaranteed",
    "history.trust": "Trust",
    "history.grievance": "Grievance",
    "history.fear": "Fear",
    "history.dependence": "Dependence",
    "history.competition": "Rivalry",
    "history.affinity": "Affinity",
    "history.effect": "Opinion in EU5",
    "history.no_relations": "No recorded relationships",
    "history.owner_changes": "Locations changing historical owner",
    "history.values": "Societal values",
    "history.trade_note": "Shown in the game as roads and market links, not as a treaty.",
}

# The year opens every chronicle sentence in every language, followed by a colon (fullwidth in
# Chinese and Japanese) and, in those two and Korean, a unit mark (年, 년); the timeline shows the
# year in its own column. ``tests/test_history_dossier.py`` checks that every translation keeps
# the shape, so a drifting translation fails there, not in a window.
YEAR_PREFIX: Final[str] = r"^{year}\s*[年년]?\s*[:\uff1a]\s*"
# A partner's standing is read from the viewed country's side: the partner's role toward it.
STANDING_ORDER: Final[tuple[str, ...]] = (
    "lord",
    "subject",
    "alliance",
    "rival",
    "guarantor",
    "protected",
    "trade",
)
PARTNERS: Final[int] = 3
AGREEMENTS: Final[int] = 24


@dataclass(frozen=True, slots=True)
class Line:
    text: str
    place: int = -1


@dataclass(frozen=True, slots=True)
class Section:
    title: str
    lines: tuple[Line, ...]


def data(sections: tuple[Section, ...]) -> list[dict[str, object]]:
    return [
        {
            "title": section.title,
            "lines": [{"text": row.text, "place": row.place} for row in section.lines],
        }
        for section in sections
    ]


@dataclass(frozen=True, slots=True)
class Entry:
    """One recorded event as a timeline row: the year apart from the sentence and its place."""

    year: int
    kind: str
    label: str
    text: str
    place: int = -1


@dataclass(frozen=True, slots=True)
class Axis:
    """One trait of a society: a 0-1000 scale (``number``) or a named value (``word``)."""

    key: str
    label: str
    number: int
    word: str
    kind: str
    cause: str
    year: int
    place: int


@dataclass(frozen=True, slots=True)
class Value:
    """A societal value as EU5 shows it: a position between two poles, and what shaped it."""

    key: str
    label: str
    left: str
    right: str
    position: int
    kind: str
    cause: str
    year: int
    place: int


@dataclass(frozen=True, slots=True)
class Standing:
    kind: str
    label: str


@dataclass(frozen=True, slots=True)
class Reason:
    factor: str
    label: str
    cause: str
    year: int
    place: int
    effect: int


@dataclass(frozen=True, slots=True)
class Partner:
    name: str
    place: int
    tag: str
    standing: tuple[Standing, ...]
    reasons: tuple[Reason, ...]


@dataclass(frozen=True, slots=True)
class Dossier:
    """A country's society, chronicle and relationships, ready to draw."""

    government: str
    rank: str
    technology: str
    origin: Entry
    values: tuple[Value, ...]
    axes: tuple[Axis, ...]
    chronicle: tuple[Entry, ...]
    partners: tuple[Partner, ...]
    more: int


@dataclass(frozen=True, slots=True)
class Link:
    name: str
    place: int


@dataclass(frozen=True, slots=True)
class Change:
    year: int
    count: int
    place: int


@dataclass(frozen=True, slots=True)
class Heritage:
    """Societies that share one or more inheritances: what they share, and who they are."""

    labels: tuple[str, ...]
    members: tuple[Link, ...]


@dataclass(frozen=True, slots=True)
class Ambition:
    kind: str
    label: str
    name: str
    place: int
    realized: bool


@dataclass(frozen=True, slots=True)
class RegionHistory:
    changes: tuple[Change, ...]
    heritage: tuple[Heritage, ...]
    ambitions: tuple[Ambition, ...]


def encode(value: Dossier | RegionHistory) -> dict[str, object]:
    """A dossier or a region's history as the plain data the window receives."""
    return asdict(value)


def _traits(society: Society) -> dict[str, int | str]:
    """A society's eight traits by axis name, in the archive's axis order."""
    return dict(
        zip(
            AXES,
            (
                society.centralization,
                society.authority,
                society.livelihood,
                society.exchange,
                society.religious_authority,
                society.military,
                society.integration,
                society.tradition,
            ),
            strict=True,
        )
    )


def _standing(kind: str, *, first: bool) -> str:
    """The partner's role toward the viewed country in one projected agreement.

    ``vassal`` pairs are (overlord, subject) and ``guarantee`` pairs (guarantor, protected);
    ``first`` says the viewed country stands in the pair's first place.
    """
    if kind == "vassal":
        return "subject" if first else "lord"
    if kind == "guarantee":
        return "protected" if first else "guarantor"
    return "trade" if kind == "exchange" else kind


@final
class Reader:
    """A revealed atlas, with bounded indexes shared by both presentation surfaces."""

    def __init__(self, atlas: Atlas, language: str, key: Callable[[str], str]) -> None:
        self.atlas = atlas
        self.language = language
        self.key = key
        self.texts = translations.translate(translations.WINDOW, language, SOURCES)
        self.game = translations.translate(translations.GAME, language, history_text.sources())
        self.countries = {c.tag: c for c in atlas.history.countries} if atlas.history else {}
        self.tags = {c.actor: c.tag for c in self.countries.values()}
        # A society that is a country on the map is named as the map names it (as the game's
        # chronicle does); a predecessor keeps the name of its seat.
        named = {c.tag: c.name or c.tag for c in atlas.countries}
        self.called: dict[int, wording.Name] = {
            actor: named.get(tag, tag) for actor, tag in self.tags.items()
        }
        self.memories: dict[int, list[int]] = defaultdict(list)
        self.regional: dict[str, Counter[int]] = defaultdict(Counter)
        if atlas.history:
            for i, memory in enumerate(atlas.history.memories):
                self.memories[memory.first].append(i)
            for event, place, _, _ in atlas.history.changes:
                self.regional[self.name(atlas.regions[place])][event] += 1

    def name(self, value: wording.Name) -> str:
        return wording.render(value, self.language)

    def society(self, record: Archive, actor: int) -> wording.Name:
        """What the actor is called: its country's name on the map, else the name of its seat."""
        return self.called.get(actor) or self.atlas.names[record.actors[actor].seat]

    def say(self, key: str, **fields: str | int) -> str:
        return self.texts[f"history.{key}"].format_map(fields)

    def sentence(self, record: Archive, index: int, actor: int) -> Line:
        text, place = self._told(record, index, actor)
        if place >= 0 and record.events[index].kind is not Action.MIGRATION:
            text = history_text.Sentence(
                "rnw_history_place", (("text", text), ("place", self.atlas.names[place]))
            )
        return Line(history_text.render(text, self.language, self.game), place)

    def entry(self, record: Archive, index: int, actor: int) -> Entry:
        """A timeline row: the sentence without its year and its place, which are drawn apart."""
        event = record.events[index]
        text, place = self._told(record, index, actor)
        family = history_text.event_family(event.kind, event.outcome)
        written = history_text.render(text, self.language, self.game)
        return Entry(
            event.year,
            family,
            self.game[f"rnw_history_cause_{family}"],
            re.sub(YEAR_PREFIX.format(year=event.year), "", written, count=1),
            place,
        )

    def _told(self, record: Archive, index: int, actor: int) -> tuple[history_text.Sentence, int]:
        event = record.events[index]
        participants = event.actors[:2]
        if event.kind in {Action.CONFLICT, Action.PRESSURE}:
            focus = min(record.lineage(actor).intersection(event.actors))
            participants = (focus, next(key for key in event.actors if key != focus))
        if event.kind is Action.UNION:
            created = event.created[0]
            participants = (created, *record.actors[created].parents)
        elif event.kind is Action.SEPARATION:
            participants = event.retired
        elif event.kind is Action.SECESSION:
            participants = (event.actors[0], event.created[0])
        elif event.partners:
            participants = event.partners
        elif event.kind is Action.REFORM:
            participants = event.actors[:1]
        labels = [self.society(record, key) for key in participants]
        if event.kind is Action.MIGRATION:
            labels = [self.atlas.names[place] for place in event.places]
        family = history_text.event_family(event.kind, event.outcome)
        text = history_text.Sentence(
            f"rnw_history_{family}_{event.wording}",
            (("year", event.year), *zip(("first", "second", "third"), labels, strict=False)),
        )
        return text, event.places[0] if event.places else -1

    def country(self, tag: str) -> tuple[Section, ...]:
        record = self.atlas.history
        if record is None:
            return (Section(self.say("title"), (Line(self.say("none")),)),)
        country = self.countries[tag]
        actor = record.actors[country.actor]
        profile = [
            self.sentence(record, actor.origin, country.actor),
            Line(
                self.say(
                    "position",
                    government=self.texts.get(
                        f"history.{country.government}", self.key(country.government)
                    ),
                    rank=self.key(country.rank) or "—",
                    level=country.level,
                )
            ),
        ]
        traits = _traits(actor.society)
        for axis, cause in zip(AXES, actor.axis_causes, strict=True):
            value = traits[axis]
            written = str(value) if isinstance(value, int) else self.say(str(value))
            event = record.events[cause]
            family = history_text.event_family(event.kind, event.outcome)
            profile.append(
                Line(
                    self.say(
                        "axis",
                        axis=self.say(axis),
                        value=written,
                        cause=self.game[f"rnw_history_cause_{family}"],
                        year=event.year,
                    ),
                    event.places[0] if event.places else -1,
                )
            )
        rows = dict(record.chronicles)[country.actor]
        return (
            Section(self.say("profile"), tuple(profile)),
            Section(self.say("relations"), self._relationships(record, country.actor)),
            Section(
                self.say("chronicle"),
                tuple(self.sentence(record, row, country.actor) for row in rows),
            ),
        )

    def _relationships(self, record: Archive, actor: int) -> tuple[Line, ...]:
        partners: Counter[int] = Counter()
        for index in self.memories.get(actor, ()):
            memory = record.memories[index]
            partners[memory.second] += memory.amount
        rows: list[Line] = []
        for partner, _ in sorted(partners.items(), key=lambda pair: (-pair[1], pair[0]))[:3]:
            rows.append(
                Line(
                    self.name(self.society(record, partner)),
                    record.actors[partner].seat,
                )
            )
            projected: list[str] = []
            for kind, first, second in record.relations:
                if {first, second} == {actor, partner}:
                    arrow = "↔" if kind in {"alliance", "rival", "exchange"} else "→"
                    names = (
                        f"{self.name(self.society(record, first))} {arrow} "
                        f"{self.name(self.society(record, second))}"
                    )
                    projected.append(
                        f"{self.say('trade' if kind == 'exchange' else kind)} · {names}"
                    )
            if projected:
                rows.append(Line(self.say("projected", relations=", ".join(sorted(projected)))))
            reasons = sorted(
                (
                    record.memories[i]
                    for i in self.memories[actor]
                    if record.memories[i].second == partner
                ),
                key=lambda memory: (-memory.amount, memory.factor, memory.cause),
            )[:3]
            for memory in reasons:
                event = record.events[memory.cause]
                family = history_text.event_family(event.kind, event.outcome)
                reason = history_text.Sentence(
                    f"rnw_history_opinion_{memory.factor}",
                    (
                        (
                            "cause",
                            history_text.Sentence(f"rnw_history_cause_{family}"),
                        ),
                        ("year", event.year),
                    ),
                )
                rows.append(
                    Line(
                        self.say(
                            "memory", reason=history_text.render(reason, self.language, self.game)
                        ),
                        event.places[0] if event.places else -1,
                    )
                )
                for bias in record.biases:
                    if (bias.first, bias.second, bias.factor, bias.cause) == (
                        actor,
                        partner,
                        memory.factor,
                        memory.cause,
                    ):
                        shown = history_text.render(reason, self.language, self.game)
                        rows.append(
                            Line(self.say("projected", relations=f"{shown} ({bias.value:+d})"))
                        )
        return tuple(rows)

    def region(self, region: str) -> tuple[Section, ...]:
        record = self.atlas.history
        if record is None:
            return (Section(self.say("region"), (Line(self.say("none")),)),)
        changes = self.regional.get(region, Counter())
        rows = tuple(
            Line(
                self.say("changes", year=record.events[event].year, count=count),
                record.events[event].places[0],
            )
            for event, count in sorted(
                changes.items(), key=lambda pair: (-pair[1], -record.events[pair[0]].year, pair[0])
            )[:5]
        )
        inheritances = [
            Line(
                self.say(
                    "shared",
                    kind=label,
                    members=", ".join(
                        self.name(self.atlas.names[record.actors[member].seat])
                        for member in members[:8]
                    ),
                ),
                anchor,
            )
            for label, members, anchor in self._heritage(record, region)
        ]
        # D23: a seeded aim stays readable whether or not history fulfilled it.
        ambitions = tuple(
            Line(
                self.say(
                    "ambition",
                    kind=self.say(aim.kind),
                    name=self.name(self.atlas.names[record.actors[aim.members[0]].seat]),
                    status=self.say("fulfilled" if aim.realized else "unfulfilled"),
                ),
                aim.anchor,
            )
            for aim in record.aims
            if self.name(self.atlas.regions[aim.anchor]) == region
        )
        sections = (
            Section(self.say("region"), rows),
            Section(self.say("inheritance"), tuple(inheritances[:8])),
        )
        return (*sections, Section(self.say("ambitions"), ambitions[:8])) if ambitions else sections

    def _heritage(self, record: Archive, region: str) -> list[tuple[str, list[int], int]]:
        """(label, member actors, place) of each inheritance shared by the region's societies."""
        found: list[tuple[str, list[int], int]] = []
        for group in record.groups:
            members = [
                member
                for member in group.members
                if self.name(self.atlas.regions[record.actors[member].seat]) == region
            ]
            if len(members) > 1:
                found.append((self.say(group.kind), members, record.actors[members[0]].seat))
        predecessors: dict[int, list[int]] = defaultdict(list)
        for country in record.countries:
            if self.name(self.atlas.regions[record.actors[country.actor].seat]) == region:
                for parent in record.lineage(country.actor) - {country.actor}:
                    predecessors[parent].append(country.actor)
        for parent, descendants in sorted(
            predecessors.items(), key=lambda item: (-len(item[1]), item[0])
        ):
            if len(descendants) > 1:
                ancestor = record.actors[parent]
                label = (
                    f"{self.name(self.atlas.names[ancestor.seat])} "
                    f"({ancestor.born}\N{EN DASH}{ancestor.ended})"
                )
                found.append((label, descendants, ancestor.seat))
        return found

    def dossier(self, tag: str) -> Dossier | None:
        """The country's society, chronicle and relationships; None when no history was kept."""
        record = self.atlas.history
        if record is None:
            return None
        country = self.countries[tag]
        actor = record.actors[country.actor]
        traits = _traits(actor.society)
        axes: list[Axis] = []
        for axis, cause in zip(AXES, actor.axis_causes, strict=True):
            value = traits[axis]
            event = record.events[cause]
            family = history_text.event_family(event.kind, event.outcome)
            axes.append(
                Axis(
                    axis,
                    self.say(axis),
                    value if isinstance(value, int) else -1,
                    "" if isinstance(value, int) else self.say(value),
                    family,
                    self.game[f"rnw_history_cause_{family}"],
                    event.year,
                    event.places[0] if event.places else -1,
                )
            )
        values = self._values(country, axes)
        shown = {value.key for value in values}
        # A trait that a written value already shows (with the same cause) is not shown twice.
        represented = {SOURCE[key] for key in shown}
        partners, more = self._partners(record, country.actor)
        return Dossier(
            government=self.texts.get(
                f"history.{country.government}", self.key(country.government)
            ),
            rank=self.key(country.rank) if country.rank else "",
            technology=""
            if country.government == "tribe"
            else self.say("technology", level=country.level),
            origin=self.entry(record, actor.origin, country.actor),
            values=values,
            axes=tuple(axis for axis in axes if axis.key not in represented),
            chronicle=tuple(
                self.entry(record, row, country.actor)
                for row in dict(record.chronicles)[country.actor]
            ),
            partners=partners,
            more=more,
        )

    def _values(self, country: CountryFact, axes: list[Axis]) -> tuple[Value, ...]:
        """The societal values written for the country, named as the game names them."""
        by_trait = {axis.key: axis for axis in axes}
        found: list[Value] = []
        for key, position in zip(VALUE_AXES, country.values, strict=False):
            if position == UNWRITTEN:
                continue
            left, right = poles(key)
            cause = by_trait[SOURCE[key]]
            found.append(
                Value(
                    key,
                    self.key(key),
                    self.key(left),
                    self.key(right),
                    position,
                    cause.kind,
                    cause.cause,
                    cause.year,
                    cause.place,
                )
            )
        return tuple(found)

    def _partners(self, record: Archive, actor: int) -> tuple[tuple[Partner, ...], int]:
        """Remembered partners with their reasons, then the other agreements, and how many more."""
        amounts: Counter[int] = Counter()
        for index in self.memories.get(actor, ()):
            memory = record.memories[index]
            amounts[memory.second] += memory.amount
        remembered = [
            partner
            for partner, _ in sorted(amounts.items(), key=lambda pair: (-pair[1], pair[0]))[
                :PARTNERS
            ]
        ]
        agreements: dict[int, set[str]] = defaultdict(set)
        for kind, first, second in record.relations:
            if actor in {first, second}:
                other = second if first == actor else first
                agreements[other].add(_standing(kind, first=first == actor))
        others = sorted(
            (partner for partner in agreements if partner not in remembered),
            key=lambda partner: (
                min(STANDING_ORDER.index(k) for k in agreements[partner]),
                partner,
            ),
        )
        shown = [
            self._partner(record, actor, partner, agreements.get(partner, set()), reasons=True)
            for partner in remembered
        ] + [
            self._partner(record, actor, partner, agreements[partner], reasons=False)
            for partner in others[:AGREEMENTS]
        ]
        return tuple(shown), max(len(others) - AGREEMENTS, 0)

    def _partner(
        self, record: Archive, actor: int, partner: int, kinds: set[str], *, reasons: bool
    ) -> Partner:
        fact = record.actors[partner]
        return Partner(
            name=self.name(self.society(record, partner)),
            place=fact.seat,
            tag=self.tags.get(partner, ""),
            standing=tuple(
                Standing(kind, self.say(kind)) for kind in sorted(kinds, key=STANDING_ORDER.index)
            ),
            reasons=self._reasons(record, actor, partner) if reasons else (),
        )

    def _reasons(self, record: Archive, actor: int, partner: int) -> tuple[Reason, ...]:
        """The strongest remembered causes between two actors, with what EU5 receives for each."""
        memories = sorted(
            (
                record.memories[i]
                for i in self.memories.get(actor, ())
                if record.memories[i].second == partner
            ),
            key=lambda memory: (-memory.amount, memory.factor, memory.cause),
        )[:3]
        found: list[Reason] = []
        for memory in memories:
            event = record.events[memory.cause]
            family = history_text.event_family(event.kind, event.outcome)
            effect = next(
                (
                    bias.value
                    for bias in record.biases
                    if (bias.first, bias.second, bias.factor, bias.cause)
                    == (actor, partner, memory.factor, memory.cause)
                ),
                0,
            )
            found.append(
                Reason(
                    str(memory.factor),
                    self.say(memory.factor),
                    self.game[f"rnw_history_cause_{family}"],
                    event.year,
                    event.places[0] if event.places else -1,
                    effect,
                )
            )
        return tuple(found)

    def _shared(self, record: Archive, region: str) -> tuple[Heritage, ...]:
        """Inheritances grouped by the societies that hold them, in the order first met."""
        groups: dict[tuple[int, ...], list[str]] = {}
        for label, members, _ in self._heritage(record, region):
            groups.setdefault(tuple(members[:8]), []).append(label)
        return tuple(
            Heritage(
                tuple(labels),
                tuple(
                    Link(
                        self.name(self.atlas.names[record.actors[member].seat]),
                        record.actors[member].seat,
                    )
                    for member in members
                ),
            )
            for members, labels in groups.items()
        )[:8]

    def place(self, region: str) -> RegionHistory | None:
        """A region's ownership changes, shared inheritances and aims; None without history."""
        record = self.atlas.history
        if record is None:
            return None
        changes = self.regional.get(region, Counter())
        return RegionHistory(
            changes=tuple(
                Change(record.events[event].year, count, record.events[event].places[0])
                for event, count in sorted(
                    changes.items(),
                    key=lambda pair: (-pair[1], -record.events[pair[0]].year, pair[0]),
                )[:5]
            ),
            heritage=self._shared(record, region),
            ambitions=tuple(
                Ambition(
                    str(aim.kind),
                    self.say(aim.kind),
                    self.name(self.atlas.names[record.actors[aim.members[0]].seat]),
                    aim.anchor,
                    aim.realized,
                )
                for aim in record.aims
                if self.name(self.atlas.regions[aim.anchor]) == region
            )[:8],
        )
