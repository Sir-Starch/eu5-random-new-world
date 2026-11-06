"""Current historical facts used by existing story families, with backward causes."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from rnw.content import RANK_LEVELS, Fallen, HistoricalFacts
from rnw.history_model import END, Action, Factor, HistoryError, Outcome

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rnw.eu5_start import FinalStartPlan
    from rnw.history_model import Actor, History


def country_starts(plan: FinalStartPlan) -> tuple[tuple[str, tuple[str, ...], str, str], ...]:
    """Location-based countries, including landed confederates; never pop countries."""
    return tuple(
        (country.tag, country.members, country.capital, country.religion)
        for country in plan.countries
        if country.kind == "state" or country.landed
    )


def facts(plan: FinalStartPlan) -> HistoricalFacts | None:
    """Surviving bargains and dependency directions, not obsolete bootstrap tags."""
    history = plan.history
    if history is None:
        return None
    tags = {
        country.history_actor: country.tag
        for country in plan.countries
        if country.kind == "state" or country.landed
    }
    living = {actor.key for actor in history.state.actors if actor.living}
    if len(tags) != len(country_starts(plan)) or not set(tags) <= living:
        message = "Story countries have duplicate, missing or retired historical actors"
        raise HistoryError(message)
    cooperation: dict[tuple[str, str], set[str]] = defaultdict(set)
    dependencies: dict[tuple[str, str], str] = {}
    events = {event.key for event in history.events}
    for bond in history.state.bonds:
        if bond.first not in tags or bond.second not in tags:
            continue
        first, second = tags[bond.first], tags[bond.second]
        if bond.cause not in events:
            message = "Story relation has a missing historical cause"
            raise HistoryError(message)
        if bond.kind in {Action.EXCHANGE, Action.PACT, Action.PROTECTION}:
            cooperation[min(first, second), max(first, second)].add(bond.cause)
        elif bond.kind is Action.DEPENDENCY:
            dependencies[second, first] = bond.cause
    for memory in history.state.memories:
        if (
            memory.first in tags
            and memory.second in tags
            and memory.factor in {Factor.TRUST, Factor.AFFINITY}
            and memory.at(END) > 0
        ):
            if memory.cause not in events:
                message = "Story memory has a missing historical cause"
                raise HistoryError(message)
            first, second = tags[memory.first], tags[memory.second]
            cooperation[min(first, second), max(first, second)].add(memory.cause)
    if set(dependencies) != set(plan.vassals):
        message = "Story dependencies differ from the historical start"
        raise HistoryError(message)
    hostile = frozenset((min(first, second), max(first, second)) for first, second in plan.rivals)
    return HistoricalFacts(
        {pair: tuple(sorted(causes)) for pair, causes in sorted(cooperation.items())},
        hostile,
        dependencies,
        frozenset((route.first, route.second) for route in history.geography.routes),
        fallen(plan, tags),
    )


def heights(history: History) -> dict[str, frozenset[str]]:
    """The districts each actor held at its height, replayed from the recorded transfers.

    Every holding begins with a transfer (a foundation transfers from no one), so the replay must
    end in the recorded holdings of 1337; a history where it does not is refused.
    """
    held: dict[str, set[str]] = defaultdict(set)
    best: dict[str, frozenset[str]] = {}
    for event in history.events:
        touched: set[str] = set()
        for transfer in event.effects.transfers:
            if transfer.before:
                held[transfer.before].discard(transfer.district)
            if transfer.after:
                held[transfer.after].add(transfer.district)
            touched.update(key for key in (transfer.before, transfer.after) if key)
        for actor in touched:
            if len(held[actor]) >= len(best.get(actor, frozenset())):
                best[actor] = frozenset(held[actor])
    final = {(holding.district, holding.actor) for holding in history.state.holdings}
    replayed = {(district, actor) for actor, places in held.items() for district in places}
    if replayed != final:
        message = "The recorded transfers do not lead to the holdings of 1337"
        raise HistoryError(message)
    return best


def _ancestors(actors: Mapping[str, Actor], key: str) -> set[str]:
    pending, found = [key], set[str]()
    while pending:
        here = pending.pop()
        if here not in found:
            found.add(here)
            pending.extend(actors[here].parents)
    return found


def fallen(plan: FinalStartPlan, tags: Mapping[str, str]) -> tuple[Fallen, ...]:
    """The realms and unions the history divided, with their living heirs on the map (N7).

    ``tags`` are the living landed actors and their countries. An heir is such a country
    descended from the divided realm, through later unions too.
    """
    history = plan.history
    if history is None:
        return ()
    actors = {actor.key: actor for actor in history.state.actors}
    rank = {
        country.tag: RANK_LEVELS.get(country.rank, 1)
        for country in plan.countries
        if country.tag in tags.values()
    }
    lineages = {actor: _ancestors(actors, actor) for actor in tags}
    height = heights(history)
    found: list[Fallen] = []
    for event in history.events:
        if event.kind is not Action.SEPARATION or event.outcome is not Outcome.ACCEPTED:
            continue
        realm = event.actors[0]
        heirs = sorted(tags[actor] for actor, lineage in lineages.items() if realm in lineage)
        found.append(
            Fallen(
                realm,
                actors[realm].seat,
                tuple(sorted(height.get(realm, frozenset()))),
                tuple(heirs),
                max((rank[tag] for tag in heirs), default=1),
                event.year,
                event.key,
            )
        )
    return tuple(found)
