"""C486 administrative burden: one frontier search per held place, kept for equality (C506)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.history_context import INTEGRATION_YEARS
from rnw.history_model import PERMILLE, Action

if TYPE_CHECKING:
    from rnw.history_context import Context


def per_place_burden(context: Context, actor: str, gained: tuple[str, ...] = ()) -> int:
    """Distance, heterogeneity and recent gains consume integration capacity."""
    profile = context.index.actors[actor].society
    seat = context.index.actors[actor].seat
    home = {(pop.culture, pop.religion) for pop in context.index.cohorts(seat)}
    members = context.index.members[actor] | set(gained)
    cost = 0
    for key in sorted(members):
        context.checkpoint()
        people = context.index.population(key)
        foreign = sum(
            pop.population
            for pop in context.index.cohorts(key)
            if (pop.culture, pop.religion) not in home
        )
        distance = context.distance(actor, key, gained)
        if distance >= 1 << 60:
            return PERMILLE + 1
        holding = context.holdings[key]
        recent = key in gained or (
            holding.actor == actor
            and context.event_kinds[holding.cause] is Action.CONFLICT
            and context.state.year - context.event_years[holding.cause] < INTEGRATION_YEARS
        )
        friction = foreign * PERMILLE // people
        cost += (
            (distance // 20 + friction // 4 + (150 if recent else 0))
            * (1500 - profile.integration)
            // PERMILLE
        )
    return cost + profile.centralization * len(members) // 40
