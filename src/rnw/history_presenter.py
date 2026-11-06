"""Portable society and regional summaries, rendered once for either window."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final, final

from rnw import history_text, translations, wording
from rnw.history_archive import AXES, UNWRITTEN
from rnw.history_model import Action, TrajectoryKind
from rnw.history_values import AXES as VALUE_AXES
from rnw.history_values import SOURCE, poles
from rnw.opinions import treaty_opinions

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.atlas import Atlas
    from rnw.history_archive import Archive, BiasFact, CountryFact
    from rnw.history_model import Society

SOURCES: Final[dict[str, str]] = {
    "history.title": "Society and history",
    "history.region": "Regional history",
    "history.none": "No recorded history",
    "history.profile": "Society in 1337",
    "history.chronicle": "Chronicle",
    "history.relations": "Opinions on the first day",
    "history.inheritance": "Shared inheritances",
    "history.opinion_of": "{name}: {total}",
    "history.opinion_line": "{label}: {value}",
    "history.opinion_fading": "{label}: {value}, {fade} a year",
    "history.position": "Government: {government} · Country Rank: {rank}",
    "history.axis": "{axis}: {value} — {cause} ({year})",
    "history.shared": "{kind}: {members}",
    "history.changes": "{year} · Locations changing historical owner: {count}",
    "history.great_empire": "Great empire",
    "history.sea_league": "Sea league",
    "history.highland_confederation": "Highland confederation",
    "history.sacred_centre": "Sacred centre",
    "history.fractured_realm": "Divided realm",
    "history.ambitions": "Extraordinary peoples",
    "history.ambition": "{kind} — {name}: {status}",
    "history.fulfilled": "took shape and survived to 1337",
    "history.unfulfilled": "did not survive to 1337",
    # The Tauri window's society panel (structured data, `dossier` and `place`).
    "history.tab_place": "Place",
    "history.tab_society": "Society",
    "history.tab_relations": "Relations",
    "history.origin": "Origin",
    "history.society_note": (
        "Its government, rank and societal values in 1337 as the game shows them, and the event "
        "that last shaped each value."
    ),
    "history.chronicle_note": "The most significant recorded events, oldest first.",
    "history.relations_note": (
        "Its opinion of other countries on the first day, line by line as the game lists it: "
        "the opinions its treaties give and those of its recorded past. The game adds its own "
        "for culture, religion, language, borders and more."
    ),
    "history.total": "The sum of these lines",
    "history.yearly": "{value} a year",
    "history.no_relations": "No opinion of another country is set at the start",
    "history.owner_changes": "Locations changing historical owner",
    "history.values": "Societal values",
    "history.no_values": (
        "This world was made before its societal values were recorded. "
        "Make a new world to see them."
    ),
}

# The year opens every chronicle sentence in every language, followed by a colon (fullwidth in
# Chinese and Japanese) and, in those two and Korean, a unit mark (年, 년); the timeline shows the
# year in its own column. ``tests/test_history_dossier.py`` checks that every translation keeps
# the shape, so a drifting translation fails there, not in a window.
YEAR_PREFIX: Final[str] = r"^{year}\s*[年년]?\s*[:\uff1a]\s*"
# The trajectories of the *Extraordinary peoples* setting: a region shows whether they took
# shape. The ordinary regional aims (D22) are the model's own and are not shown (plan D31).
EXTRAORDINARY: Final[frozenset[TrajectoryKind]] = frozenset(
    {
        TrajectoryKind.GREAT_EMPIRE,
        TrajectoryKind.SEA_LEAGUE,
        TrajectoryKind.HIGHLAND_CONFEDERATION,
        TrajectoryKind.SACRED_CENTRE,
        TrajectoryKind.FRACTURED_REALM,
    }
)
# The countries a dossier lists, those of the largest opinion first; the rest are counted.
PARTNERS: Final[int] = 24


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
class Opinion:
    """One line of a country's opinion of another as the game lists it: its name in the game,
    its value on the first day, how much of it fades a year (0 while its treaty lasts) and the
    place its cause names."""

    label: str
    value: int
    decay: int
    place: int


@dataclass(frozen=True, slots=True)
class Partner:
    """Another country, and the viewed country's opinion of it: the lines and their sum."""

    name: str
    place: int
    tag: str
    total: int
    opinions: tuple[Opinion, ...]


@dataclass(frozen=True, slots=True)
class Dossier:
    """A country's government, rank and societal values, chronicle and opinions, as the game
    names them, ready to draw."""

    government: str
    rank: str
    origin: Entry
    values: tuple[Value, ...]
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


def signed(value: int) -> str:
    """A whole number with a real minus sign, and a plus where it is positive."""
    return f"+{value}" if value > 0 else f"\N{MINUS SIGN}{-value}" if value < 0 else "0"


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
        self.regional: dict[str, Counter[int]] = defaultdict(Counter)
        if atlas.history:
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
                    government=self.key(country.government),
                    rank=self.key(country.rank) or "\N{EM DASH}",
                )
            ),
        ]
        values = self._values(country, self._axes(record, country.actor))
        for value in values:
            lean = value.left if value.position < 0 else value.right if value.position else ""
            shown = f"{lean} {abs(value.position)}" if lean else "0"
            profile.append(
                Line(
                    self.say(
                        "axis", axis=value.label, value=shown, cause=value.cause, year=value.year
                    ),
                    value.place,
                )
            )
        if not values:
            profile.append(Line(self.say("no_values")))
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
        """The dossier's opinions as text: each country and its sum, then its lines."""
        partners, more = self._partners(record, actor)
        rows: list[Line] = []
        for partner in partners:
            rows.append(
                Line(
                    self.say("opinion_of", name=partner.name, total=signed(partner.total)),
                    partner.place,
                )
            )
            for line in partner.opinions:
                if line.decay:
                    text = self.say(
                        "opinion_fading",
                        label=line.label,
                        value=signed(line.value),
                        fade=signed(-line.decay),
                    )
                else:
                    text = self.say("opinion_line", label=line.label, value=signed(line.value))
                rows.append(Line(text, line.place))
        if more:
            rows.append(Line(f"+{more}"))
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
            if aim.kind in EXTRAORDINARY and self.name(self.atlas.regions[aim.anchor]) == region
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
            if group.kind not in EXTRAORDINARY:
                continue
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
        partners, more = self._partners(record, country.actor)
        return Dossier(
            government=self.key(country.government),
            rank=self.key(country.rank) if country.rank else "",
            origin=self.entry(record, actor.origin, country.actor),
            values=self._values(country, self._axes(record, country.actor)),
            chronicle=tuple(
                self.entry(record, row, country.actor)
                for row in dict(record.chronicles)[country.actor]
            ),
            partners=partners,
            more=more,
        )

    def _axes(self, record: Archive, actor: int) -> list[Axis]:
        """The society model's traits of ``actor``, each with the event that last shaped it: the
        causes of the societal values written from them (``history_values.SOURCE``)."""
        traits = _traits(record.actors[actor].society)
        axes: list[Axis] = []
        for axis, cause in zip(AXES, record.actors[actor].axis_causes, strict=True):
            value = traits[axis]
            event = record.events[cause]
            family = history_text.event_family(event.kind, event.outcome)
            axes.append(
                Axis(
                    axis,
                    axis,
                    value if isinstance(value, int) else -1,
                    "" if isinstance(value, int) else str(value),
                    family,
                    self.game[f"rnw_history_cause_{family}"],
                    event.year,
                    event.places[0] if event.places else -1,
                )
            )
        return axes

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
        """The viewed country's opinion of each other country on the first day, as the game
        lists it, the largest sums first; and how many more countries it has an opinion of.

        A treaty's lines are the engine's opinions of the side the country holds (``vassal``
        pairs are (overlord, subject), ``guarantee`` (guarantor, protected), ``rival`` (the
        country that rivals, its rival)); the historical lines are the opinions the world
        writes, under their names in the game.
        """
        lines: dict[int, list[Opinion]] = defaultdict(list)
        for kind, first, second in record.relations:
            if actor not in {first, second}:
                continue
            other = second if first == actor else first
            lines[other].extend(
                Opinion(self.key(treaty.key), treaty.value, 0, -1)
                for treaty in treaty_opinions(kind, first=first == actor)
            )
        biases = sorted(
            (bias for bias in record.biases if bias.first == actor),
            key=lambda bias: (-abs(bias.value), bias.cause, bias.factor),
        )
        for bias in biases:
            lines[bias.second].append(
                Opinion(self._bias_name(record, bias), bias.value, bias.decay, bias.place)
            )
        partners = sorted(
            (
                Partner(
                    name=self.name(self.society(record, other)),
                    place=record.actors[other].seat,
                    tag=self.tags.get(other, ""),
                    total=sum(line.value for line in found),
                    opinions=tuple(found),
                )
                for other, found in lines.items()
                if found
            ),
            key=lambda partner: (-abs(partner.total), partner.name, partner.tag),
        )
        return tuple(partners[:PARTNERS]), max(len(partners) - PARTNERS, 0)

    def _bias_name(self, record: Archive, bias: BiasFact) -> str:
        """A historical opinion's name as the game shows it (``history_text.opinion_text``)."""
        event = record.events[bias.cause]
        family = history_text.event_family(event.kind, event.outcome)
        text = history_text.Sentence(
            f"rnw_history_opinion_{bias.factor}",
            (("cause", history_text.Sentence(f"rnw_history_cause_{family}")), ("year", event.year)),
        )
        if bias.place >= 0:
            text = history_text.Sentence(
                "rnw_history_opinion_place",
                (("text", text), ("place", self.atlas.names[bias.place])),
            )
        return history_text.render(text, self.language, self.game)

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
                if aim.kind in EXTRAORDINARY and self.name(self.atlas.regions[aim.anchor]) == region
            )[:8],
        )
