"""Portable society and regional summaries, rendered once for either window."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

from rnw import history_text, translations, wording
from rnw.history_archive import AXES
from rnw.history_model import Action

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.atlas import Atlas
    from rnw.history_archive import Archive

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
    "history.monarchy": "Monarchy",
    "history.republic": "Republic",
    "history.theocracy": "Theocracy",
    "history.tribe": "Tribe",
}


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
        self.memories: dict[int, list[int]] = defaultdict(list)
        self.regional: dict[str, Counter[int]] = defaultdict(Counter)
        if atlas.history:
            for i, memory in enumerate(atlas.history.memories):
                self.memories[memory.first].append(i)
            for event, place, _, _ in atlas.history.changes:
                self.regional[self.name(atlas.regions[place])][event] += 1

    def name(self, value: wording.Name) -> str:
        return wording.render(value, self.language)

    def say(self, key: str, **fields: str | int) -> str:
        return self.texts[f"history.{key}"].format_map(fields)

    def sentence(self, record: Archive, index: int, actor: int) -> Line:
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
        elif event.partners:
            participants = event.partners
        elif event.kind is Action.REFORM:
            participants = event.actors[:1]
        labels = [self.atlas.names[record.actors[key].seat] for key in participants]
        if event.kind is Action.MIGRATION:
            labels = [self.atlas.names[place] for place in event.places]
        family = history_text.event_family(event.kind, event.outcome)
        text = history_text.Sentence(
            f"rnw_history_{family}_{event.wording}",
            (("year", event.year), *zip(("first", "second", "third"), labels, strict=False)),
        )
        place = event.places[0] if event.places else -1
        if place >= 0 and event.kind is not Action.MIGRATION:
            text = history_text.Sentence(
                "rnw_history_place", (("text", text), ("place", self.atlas.names[place]))
            )
        return Line(history_text.render(text, self.language, self.game), place)

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
        for axis, cause in zip(AXES, actor.axis_causes, strict=True):
            value: int | str = dict(
                zip(
                    AXES,
                    (
                        actor.society.centralization,
                        actor.society.authority,
                        actor.society.livelihood,
                        actor.society.exchange,
                        actor.society.religious_authority,
                        actor.society.military,
                        actor.society.integration,
                        actor.society.tradition,
                    ),
                    strict=True,
                )
            )[axis]
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
                    self.name(self.atlas.names[record.actors[partner].seat]),
                    record.actors[partner].seat,
                )
            )
            projected: list[str] = []
            for kind, first, second in record.relations:
                if {first, second} == {actor, partner}:
                    arrow = "↔" if kind in {"alliance", "rival", "exchange"} else "→"
                    names = (
                        f"{self.name(self.atlas.names[record.actors[first].seat])} {arrow} "
                        f"{self.name(self.atlas.names[record.actors[second].seat])}"
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
        inheritances: list[Line] = []
        for group in record.groups:
            members = [
                member
                for member in group.members
                if self.name(self.atlas.regions[record.actors[member].seat]) == region
            ]
            if len(members) > 1:
                names = ", ".join(
                    self.name(self.atlas.names[record.actors[member].seat])
                    for member in members[:8]
                )
                inheritances.append(
                    Line(
                        self.say("shared", kind=self.say(group.kind), members=names),
                        record.actors[members[0]].seat,
                    )
                )
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
                names = ", ".join(
                    self.name(self.atlas.names[record.actors[member].seat])
                    for member in descendants[:8]
                )
                inheritances.append(
                    Line(
                        self.say(
                            "shared",
                            kind=(
                                f"{self.name(self.atlas.names[ancestor.seat])} "
                                f"({ancestor.born}\N{EN DASH}{ancestor.ended})"
                            ),
                            members=names,
                        ),
                        record.actors[parent].seat,
                    )
                )
        return (
            Section(self.say("region"), rows),
            Section(self.say("inheritance"), tuple(inheritances[:8])),
        )
