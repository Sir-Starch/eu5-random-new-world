"""Current historical facts used by existing story families, with backward causes."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from rnw.content import HistoricalFacts
from rnw.history_model import END, Action, Factor, HistoryError

if TYPE_CHECKING:
    from rnw.eu5_start import FinalStartPlan


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
    )
