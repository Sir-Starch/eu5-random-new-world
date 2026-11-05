"""Bounded, factual history presentation shared by the game and future atlas reader.

Names stay structured until rendering. No sentence infers a participant's role
from the sorted actor list: roles come from typed effects, or remain neutral.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import wording
from rnw.history_checks import require
from rnw.history_model import Action, Actor, Event, History, HistoryError, Outcome
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from rnw.eu5_start import FinalStartPlan, HistoricalOpinion
    from rnw.wording import Name

LIMIT: Final[int] = 8


@dataclass(frozen=True, slots=True)
class Sentence:
    source: str
    fields: tuple[tuple[str, Name | int | Sentence], ...] = ()


@dataclass(frozen=True, slots=True)
class ChronicleRow:
    event: str
    year: int
    family: Action
    actors: tuple[str, ...]
    place: str
    text: Sentence


@dataclass(frozen=True, slots=True)
class Chronicle:
    rows: tuple[ChronicleRow, ...]


TEXTS: Final[dict[str, str]] = {
    "rnw_our_history": "Our History",
    "rnw_our_history_desc": "Read the record of our society and its predecessors.",
    "rnw_our_history.a": "Open the chronicle.",
    "rnw_chronicle.1.title": "Our History",
    "rnw_chronicle.1.a": "Close the chronicle.",
    "rnw_history_place": "{text} Recorded place: {place}.",
    "rnw_history_opinion_place": "{text} — place {place}",
    "rnw_history_opinion_trust": "Trust: {cause} ({year})",
    "rnw_history_opinion_grievance": "Grievance: {cause} ({year})",
    "rnw_history_opinion_fear": "Fear: {cause} ({year})",
    "rnw_history_opinion_dependence": "Dependence: {cause} ({year})",
    "rnw_history_opinion_competition": "Rivalry: {cause} ({year})",
    "rnw_history_opinion_affinity": "Affinity: {cause} ({year})",
}

CAUSES: Final[dict[str, str]] = {
    "foundation": "beginning of the record",
    "contact": "contact",
    "exchange": "exchange agreement",
    "union": "union",
    "conflict": "conflict",
    "dependency": "submission",
    "protection": "protection agreement",
    "pact": "defence pact",
    "separation": "division",
    "access": "sacred access agreement",
    "reform": "reform",
    "migration": "migration",
    "trajectory": "institutional change",
    "pressure": "armed pressure",
    "repelled": "repelled attack",
    "resisted": "resisted reform",
    "independence": "independence",
    "secession": "breakaway",
}

# Two factual formulations per displayed family. Bootstrap dates mark the start
# of the record, not an invented foundation; ambitions are not realized events.
TEMPLATES: Final[dict[str, tuple[str, str]]] = {
    "foundation": (
        "{year}: Society {first} is present when the record begins.",
        "{year}: The record opens with society {first} already established.",
    ),
    "contact": (
        "{year}: Societies {first} and {second} came into contact.",
        "{year}: Contact was established between societies {first} and {second}.",
    ),
    "exchange": (
        "{year}: Societies {first} and {second} agreed to exchange goods.",
        "{year}: An exchange agreement joined societies {first} and {second}.",
    ),
    "union": (
        "{year}: Society {first} formed from the union of societies {second} and {third}.",
        "{year}: Societies {second} and {third} united as society {first}.",
    ),
    "conflict": (
        "{year}: Societies {first} and {second} took part in a conflict.",
        "{year}: A conflict involved societies {first} and {second}.",
    ),
    "dependency": (
        "{year}: Society {first} submitted to society {second}.",
        "{year}: Society {first} accepted the overlordship of society {second}.",
    ),
    "protection": (
        "{year}: Society {second} agreed to protect society {first}.",
        "{year}: Society {first} obtained a promise of protection from society {second}.",
    ),
    "pact": (
        "{year}: Societies {first} and {second} made a defence pact.",
        "{year}: A common defence agreement joined societies {first} and {second}.",
    ),
    "separation": (
        "{year}: Society {first} divided into successor societies.",
        "{year}: Successor societies emerged from the division of society {first}.",
    ),
    "access": (
        "{year}: Society {first} obtained access to a sacred place held by society {second}.",
        "{year}: Society {second} granted society {first} access to a sacred place.",
    ),
    "reform": (
        "{year}: Society {first} changed its institutions.",
        "{year}: An institutional reform took effect in society {first}.",
    ),
    "migration": (
        "{year}: People moved from the settlement {first} to the settlement {second}.",
        "{year}: The settlement {second} received people from the settlement {first}.",
    ),
    "pressure": (
        "{year}: Societies {first} and {second} were involved in an armed confrontation.",
        "{year}: Armed pressure involved societies {first} and {second}.",
    ),
    "repelled": (
        "{year}: An attack involving societies {first} and {second} was repelled.",
        "{year}: Societies {first} and {second} took part in a conflict; the attack failed.",
    ),
    "resisted": (
        "{year}: An attempted reform in society {first} met resistance and failed.",
        "{year}: Resistance prevented a proposed institutional change in society {first}.",
    ),
    "independence": (
        "{year}: Society {first} ended its submission to society {second}.",
        "{year}: Society {first} left the overlordship of society {second}.",
    ),
    "secession": (
        "{year}: Society {second} broke away from society {first}.",
        "{year}: Society {first} could no longer hold society {second}, which broke away.",
    ),
}

# D27: lower is more significant. A conquest gained or lost outranks a contest
# that moved no land; a renewed exchange never enters a chronicle.
SIGNIFICANCE: Final[dict[Action, int]] = {
    Action.FOUNDATION: 0,
    Action.UNION: 1,
    Action.SEPARATION: 1,
    Action.INDEPENDENCE: 1,
    Action.SECESSION: 1,
    Action.CONFLICT: 2,
    Action.PRESSURE: 3,
    Action.DEPENDENCY: 3,
    Action.PROTECTION: 3,
    Action.PACT: 4,
    Action.ACCESS: 4,
    Action.REFORM: 6,
    Action.MIGRATION: 7,
    Action.EXCHANGE: 8,
    Action.CONTACT: 9,
}
ROUTINE: Final[frozenset[Action]] = frozenset({Action.EXCHANGE, Action.CONTACT})
# At most this many entries of a family that recurs in ordinary lives. A first
# contact stays in the record; the first exchange agreement is its visible sign.
REPEATED: Final[dict[Action, int]] = {
    Action.EXCHANGE: 1,
    Action.CONTACT: 0,
    Action.MIGRATION: 1,
    Action.REFORM: 2,
}


def sources() -> dict[str, str]:
    return {
        **TEXTS,
        **{f"rnw_history_cause_{key}": text for key, text in CAUSES.items()},
        **{
            f"rnw_history_{key}_{variant}": text
            for key, variants in TEMPLATES.items()
            for variant, text in enumerate(variants)
        },
    }


def source_keys(entry: Sentence | Chronicle) -> Iterator[str]:
    if isinstance(entry, Chronicle):
        for row in entry.rows:
            yield from source_keys(row.text)
    else:
        yield entry.source
        for _, value in entry.fields:
            if isinstance(value, Sentence):
                yield from source_keys(value)


def render(entry: Sentence | Chronicle, language: str, texts: Mapping[str, str]) -> str:
    if isinstance(entry, Chronicle):
        return "\\n\\n".join(render(row.text, language, texts) for row in entry.rows)
    values = {
        key: (
            render(value, language, texts)
            if isinstance(value, Sentence)
            else str(value)
            if isinstance(value, int)
            else wording.render(value, language)
        )
        for key, value in entry.fields
    }
    return texts[entry.source].format_map(values)


def event_family(kind: Action, outcome: Outcome) -> str:
    """The shared factual template family for a recorded outcome."""
    if outcome is Outcome.FAILED:
        return "resisted" if kind is Action.REFORM else "repelled"
    return kind.value


def opinion_text(opinion: HistoricalOpinion, names: Mapping[str, Name], event: Event) -> Sentence:
    require(
        event.key == opinion.cause and event.year == opinion.year and event.kind is opinion.action,
        "An opinion's text differs from its cause",
    )
    text = Sentence(
        f"rnw_history_opinion_{opinion.factor}",
        (
            ("cause", Sentence(f"rnw_history_cause_{event_family(event.kind, event.outcome)}")),
            ("year", event.year),
        ),
    )
    return (
        Sentence("rnw_history_opinion_place", (("text", text), ("place", names[opinion.place])))
        if opinion.place
        else text
    )


def _ancestors(actors: Mapping[str, Actor], actor: str) -> set[str]:
    pending, found = [actor], set[str]()
    while pending:
        key = pending.pop()
        if key not in found:
            found.add(key)
            pending.extend(actors[key].parents)
    return found


def _row(
    plan: FinalStartPlan, event: Event, actors: Mapping[str, Actor], lineage: set[str]
) -> ChronicleRow:
    history = _history(plan)
    participants = event.actors[:2]
    if event.kind in {Action.CONFLICT, Action.PRESSURE}:
        focus = min(lineage.intersection(event.actors))
        participants = (focus, next(key for key in event.actors if key != focus))
    places = sorted(
        {
            *(transfer.district for transfer in event.effects.transfers),
            *(settlement.district for settlement in event.effects.settlements),
            *(bond.place for bond in event.effects.bonds if bond.place),
        }
    )
    if event.kind is Action.UNION:
        created = event.effects.created[0]
        participants = (created.key, *created.parents)
    elif event.kind is Action.SEPARATION:
        participants = event.effects.retired
    elif event.kind is Action.SECESSION:
        participants = (event.actors[0], event.effects.created[0].key)
    elif event.effects.bonds or event.effects.ended:
        bond = (event.effects.bonds or event.effects.ended)[0]
        participants = (bond.first, bond.second)
    elif event.kind is Action.REFORM:
        participants = event.actors[:1]
    labels = [plan.names[actors[key].seat] for key in participants]
    if event.kind is Action.MIGRATION:
        labels = [plan.names[settlement.district] for settlement in event.effects.settlements]
    family = event_family(event.kind, event.outcome)
    variant = derive_seed(history.seed, "history", "wording", event.key) % 2
    text = Sentence(
        f"rnw_history_{family}_{variant}",
        (("year", event.year), *zip(("first", "second", "third"), labels, strict=False)),
    )
    place = places[0] if places else ""
    if place and event.kind is not Action.MIGRATION:
        text = Sentence("rnw_history_place", (("text", text), ("place", plan.names[place])))
    return ChronicleRow(event.key, event.year, event.kind, participants, place, text)


def _history(plan: FinalStartPlan) -> History:
    if plan.history is None:
        msg = "A chronicle has no history"
        raise HistoryError(msg)
    return plan.history


def _significance(event: Event) -> int:
    if event.kind is Action.CONFLICT and not event.effects.transfers:
        return SIGNIFICANCE[Action.PRESSURE]
    return SIGNIFICANCE[event.kind]


def _eligible(history: History) -> tuple[dict[str, list[Event]], set[str]]:
    """Chronicle-worthy events by actor, and the first exchange/contact of each pair."""
    by_actor: dict[str, list[Event]] = defaultdict(list)
    first: set[str] = set()
    pairs: set[tuple[Action, tuple[str, ...]]] = set()
    for event in history.events:
        if event.outcome is Outcome.REFUSED or event.kind is Action.TRAJECTORY:
            continue
        if event.kind in ROUTINE:
            pair = (event.kind, tuple(sorted(event.actors)))
            if pair in pairs:
                continue
            pairs.add(pair)
            first.add(event.key)
        # Only a reform that changed authority, and so the government, is chronicle
        # material; internal dimensions and resisted attempts stay in the record.
        if event.kind is Action.REFORM and not any(
            reform.before.authority is not reform.after.authority
            for reform in event.effects.reforms
        ):
            continue
        for key in event.actors:
            by_actor[key].append(event)
    return by_actor, first


def chronicles(plan: FinalStartPlan) -> dict[str, Chronicle]:
    """At most eight real events per living country, ranked by significance (D27).

    The origin comes first, then divisions, conquests, submissions and agreements.
    Only the first exchange or contact with a partner counts, recurring families
    have small caps, and a quiet past stays short. Refused proposals and seeded
    ambitions are not chronicle facts.
    """
    history = _history(plan)
    actors = {actor.key: actor for actor in history.state.actors}
    events = {event.key: event for event in history.events}
    by_actor, first = _eligible(history)
    lasting = {bond.cause for bond in history.state.bonds}
    lasting.update(opinion.cause for opinion in plan.historical_opinions)
    result: dict[str, Chronicle] = {}
    for actor, tag in sorted(plan.history_tags.items()):
        lineage = _ancestors(actors, actor)
        candidates = {event.key: event for key in lineage for event in by_actor[key]}
        origin = actors[actor].origin
        candidates[origin] = events[origin]
        ranked = sorted(
            candidates.values(),
            key=lambda event: (
                event.key != origin,
                _significance(event),
                event.key not in lasting,
                -event.year,
                event.key,
            ),
        )
        selected: list[Event] = []
        repeated: Counter[Action] = Counter()
        for event in ranked:
            if event.kind in ROUTINE and event.key not in first:
                continue
            if event.kind in REPEATED:
                if repeated[event.kind] >= REPEATED[event.kind]:
                    continue
                repeated[event.kind] += 1
            selected.append(event)
            if len(selected) == LIMIT:
                break
        result[tag] = Chronicle(
            tuple(
                _row(plan, event, actors, lineage)
                for event in sorted(selected, key=lambda e: (e.year, e.key))
            )
        )
    return result
