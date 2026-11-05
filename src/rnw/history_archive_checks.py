"""Validate portable history against its atlas before presenting any record."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, cast

from rnw.history_archive import AXES, MAX_DEPTH, UNWRITTEN, HistoryArchiveError
from rnw.history_model import END, START, Action, Outcome, Tenure, TrajectoryKind
from rnw.history_text import LIMIT
from rnw.history_values import AXES as VALUE_AXES
from rnw.history_values import BOUND

OPINIONS_PER_PAIR = 4

if TYPE_CHECKING:
    from rnw.history_archive import Archive, AtlasLinks


def _require(condition: bool, message: str) -> None:  # noqa: FBT001 - validation predicate
    if not condition:
        raise HistoryArchiveError(message)


def validate(record: Archive, links: AtlasLinks) -> None:
    """Check references, lifetimes, causal order and sparse ownership replay."""
    actors, events = record.actors, record.events
    _require(bool(re.fullmatch(r"[0-9a-f]{64}", record.digest)), "Invalid history digest")
    _require(bool(actors) == bool(events), "History has no foundation")
    _require(len(links.keys) == len(links.owners), "History atlas columns differ")
    depths: list[int] = []
    for index, event in enumerate(events):
        _require(START <= event.year <= END, "History date is outside its record")
        _require(len(set(event.causes)) == len(event.causes), "Repeated historical cause")
        _require(all(0 <= cause < index for cause in event.causes), "Cyclic or missing cause")
        _require(all(events[cause].year <= event.year for cause in event.causes), "Future cause")
        depth = 1 + max((depths[cause] for cause in event.causes), default=0)
        _require(depth <= MAX_DEPTH, "Historical ancestry is too deep")
        depths.append(depth)
        for group in (event.actors, event.created, event.retired, event.partners):
            _require(len(set(group)) == len(group), "Repeated event participant")
            _require(all(0 <= actor < len(actors) for actor in group), "Missing event actor")
        _require(bool(event.actors), "Event has no actor")
        _require(
            set(event.retired + event.partners) <= set(event.actors),
            "Event roles differ from participants",
        )
        _require(all(place in links.land for place in event.places), "Event has an invalid place")
        _require(event.wording in (0, 1), "Unknown historical wording")
        for actor in event.actors:
            person = actors[actor]
            _require(
                person.born <= event.year <= (person.ended or END), "Event outside actor lifetime"
            )
        _require(
            event.outcome is Outcome.ACCEPTED or not (event.created or event.retired),
            "Failed event changes actors",
        )
    for index, actor in enumerate(actors):
        _require(actor.seat in links.land, "Actor has an invalid seat")
        _require(START <= actor.born <= (actor.ended or END) <= END, "Invalid actor lifetime")
        _require(0 <= actor.origin < len(events), "Missing actor origin")
        origin = events[actor.origin]
        _require(
            origin.year == actor.born and index in origin.created, "Origin does not create actor"
        )
        _require(len(set(actor.parents)) == len(actor.parents), "Repeated predecessor")
        for parent in actor.parents:
            _require(0 <= parent < len(actors) and parent != index, "Invalid predecessor")
            predecessor = actors[parent]
            _require(
                predecessor.born < actor.born and predecessor.ended == actor.born,
                "Cyclic or living predecessor",
            )
            _require(predecessor.end_cause == actor.origin, "Predecessor ends at another event")
        if actor.ended is None:
            _require(actor.end_cause is None, "Living actor has an ending")
        else:
            _require(
                actor.end_cause is not None and 0 <= actor.end_cause < len(events), "Missing ending"
            )
            end = events[cast("int", actor.end_cause)]
            _require(
                end.year == actor.ended and index in end.retired, "Ending does not retire actor"
            )
        _require(len(actor.axis_causes) == len(AXES), "Incomplete society profile")
        for cause in actor.axis_causes:
            _require(0 <= cause < len(events), "Missing profile cause")
            _require(
                index in events[cause].actors + events[cause].created
                and actor.born <= events[cause].year <= (actor.ended or END),
                "Profile cause outside actor lifetime",
            )
    _ownership(record, links)
    _relations(record, links)
    _chronicles(record)
    for group in record.groups:
        _require(
            bool(group.members) and len(set(group.members)) == len(group.members),
            "Invalid historical group",
        )
        _require(
            all(
                0 <= member < len(actors) and actors[member].ended is None
                for member in group.members
            ),
            "Group has a missing or retired member",
        )
        _require(
            bool(group.causes) and all(0 <= cause < len(events) for cause in group.causes),
            "Group has a missing cause",
        )
        _require(all(place in links.land for place in group.hearths), "Group has a missing hearth")
    for aim in record.aims:
        _require(
            aim.anchor in links.land
            and bool(aim.members)
            and len(set(aim.members)) == len(aim.members)
            and all(0 <= member < len(actors) for member in aim.members)
            and 0 <= aim.cause < len(events)
            and events[aim.cause].kind is Action.TRAJECTORY
            and set(aim.members) <= set(events[aim.cause].actors),
            "Invalid seeded aim",
        )


def _ownership(record: Archive, links: AtlasLinks) -> None:
    owners: dict[int, int] = {}
    for place, actor in record.initial:
        _require(place in links.land and place not in owners, "Invalid initial ownership")
        _require(
            0 <= actor < len(record.actors) and record.actors[actor].born == START,
            "Invalid founding owner",
        )
        owners[place] = actor
    changes: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for cause, place, before, after in record.changes:
        _require(0 <= cause < len(record.events), "Ownership change has no cause")
        _require(place in owners, "Change outside founding territory")
        _require(all(0 <= actor < len(record.actors) for actor in (before, after)), "Missing owner")
        event = record.events[cause]
        _require(
            event.outcome is Outcome.ACCEPTED
            and event.kind in {Action.CONFLICT, Action.UNION, Action.SEPARATION, Action.SECESSION},
            "Ownership change has an invalid cause",
        )
        _require(
            before in event.actors and after in event.actors + event.created,
            "Owner absent from event",
        )
        _require(
            record.actors[before].tenure is Tenure.LAND
            and record.actors[after].tenure is Tenure.LAND,
            "Change crosses historical tenure",
        )
        changes[cause].append((place, before, after))
    counts = Counter(owners.values())
    for index, event in sorted(enumerate(record.events), key=lambda row: (row[1].year, row[0])):
        rows = changes.get(index, ())
        _require(
            len({place for place, _, _ in rows}) == len(rows), "Place changed twice in an event"
        )
        for place, before, after in rows:
            _require(owners[place] == before and before != after, "Ownership replay disagrees")
            owners[place] = after
            counts[before] -= 1
            counts[after] += 1
        _require(all(counts[actor] == 0 for actor in event.retired), "Retired actor retains land")
        _require(
            all(owners.get(record.actors[actor].seat) == actor for actor in event.created),
            "Created actor lacks its seat",
        )
    by_tag = {tag: (index, capital) for index, (tag, capital) in enumerate(links.countries)}
    _require(len(by_tag) == len(links.countries), "Repeated atlas tag")
    _require(
        len({c.tag for c in record.countries}) == len(record.countries) == len(by_tag),
        "Country history differs from atlas",
    )
    country_actors: dict[int, int] = {}
    for country in record.countries:
        _require(
            bool(re.fullmatch(r"[A-Z0-9]{3}", country.tag)) and country.tag in by_tag,
            "Missing historical country",
        )
        _require(
            0 <= country.actor < len(record.actors) and country.actor not in country_actors,
            "Repeated or missing country actor",
        )
        actor = record.actors[country.actor]
        number, capital = by_tag[country.tag]
        _require(
            actor.ended is None and actor.tenure is not Tenure.COMMUNITY and actor.seat == capital,
            "Country capital or lifetime differs",
        )
        _require(
            country.landed
            == (
                actor.tenure is Tenure.LAND
                or any(
                    group.kind is TrajectoryKind.HIGHLAND_CONFEDERATION
                    and country.actor in group.members
                    for group in record.groups
                )
            ),
            "Country tenure differs",
        )
        _require(
            bool(re.fullmatch(r"[a-z][a-z0-9_]*", country.government))
            and (not country.rank or bool(re.fullmatch(r"[a-z][a-z0-9_]*", country.rank))),
            "Invalid projected government or rank",
        )
        _require(
            not country.values
            or (
                len(country.values) == len(VALUE_AXES)
                and all(UNWRITTEN <= value <= BOUND for value in country.values)
            ),
            "Invalid projected societal values",
        )
        country_actors[country.actor] = number
    _require(
        all(
            (links.owners[place] == country_actors.get(owners.get(place, -1), -1))
            for place in range(len(links.keys))
        ),
        "Final ownership differs from atlas",
    )


def _relations(record: Archive, links: AtlasLinks) -> None:
    living = {i for i, actor in enumerate(record.actors) if actor.ended is None}
    countries = {country.actor for country in record.countries}
    lineages = {actor: record.lineage(actor) for actor in living}
    for fact in (*record.memories, *record.biases, *record.bonds):
        _require(
            fact.first != fact.second and {fact.first, fact.second} <= living,
            "Relation has a missing or retired partner",
        )
        _require(0 <= fact.cause < len(record.events), "Relation has a missing cause")
        event = record.events[fact.cause]
        _require(
            (any if event.kind in {Action.UNION, Action.SEPARATION} else all)(
                lineages[actor].intersection(event.actors + event.created)
                for actor in (fact.first, fact.second)
            ),
            "Relation partners absent from cause",
        )
    memories = {(m.first, m.second, m.factor, m.cause) for m in record.memories}
    directions: Counter[tuple[int, int]] = Counter()
    for bias in record.biases:
        _require({bias.first, bias.second} <= countries, "Projected opinion lacks a country")
        _require(
            (bias.first, bias.second, bias.factor, bias.cause) in memories,
            "Opinion lacks its remembered cause",
        )
        _require(
            bias.place == -1 or bias.place in record.events[bias.cause].places,
            "Opinion place differs from cause",
        )
        directions[bias.first, bias.second] += 1
    _require(
        all(count <= OPINIONS_PER_PAIR for count in directions.values()),
        "Too many opinions in one direction",
    )
    for bond in record.bonds:
        _require(
            bond.kind
            in {
                Action.CONTACT,
                Action.EXCHANGE,
                Action.DEPENDENCY,
                Action.PROTECTION,
                Action.PACT,
                Action.ACCESS,
            },
            "Invalid historical bond",
        )
        _require(bond.place == -1 or bond.place in links.land, "Bond has an invalid place")
    _require(len(set(record.relations)) == len(record.relations), "Repeated projected relation")
    for _, first, second in record.relations:
        _require(
            first != second and {first, second} <= countries, "Projected relation lacks a country"
        )


def _chronicles(record: Archive) -> None:
    countries = {country.actor for country in record.countries}
    _require(
        len(record.chronicles) == len(countries)
        and {actor for actor, _ in record.chronicles} == countries,
        "Country lacks its chronicle",
    )
    for actor, rows in record.chronicles:
        _require(
            1 <= len(rows) <= LIMIT and len(set(rows)) == len(rows), "Invalid chronicle length"
        )
        _require(
            all(0 <= row < len(record.events) for row in rows), "Chronicle has a missing event"
        )
        _require(record.actors[actor].origin in rows, "Chronicle lacks its origin")
        lineage = record.lineage(actor)
        years = [record.events[row].year for row in rows]
        _require(years == sorted(years), "Chronicle is out of order")
        for row in rows:
            event = record.events[row]
            _require(
                event.outcome is not Outcome.REFUSED
                and event.kind is not Action.TRAJECTORY
                # A breakaway's origin creates it without naming it as a party.
                and bool(lineage.intersection(event.actors + event.created)),
                "Chronicle invents an event",
            )
