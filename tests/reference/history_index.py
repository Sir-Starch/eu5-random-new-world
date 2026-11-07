"""C486 uncached sparse index, retained independently for whole-history equality.

The geography's facts that the index now keeps for every round (C506) are made again
for each snapshot here, and no settlement counts as checked before.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, final

from rnw.history_checks import _population_totals, require  # pyright: ignore[reportPrivateUsage]
from rnw.history_model import PERMILLE, Actor, Cohort, Geography, Settlement, Snapshot, Tenure

if TYPE_CHECKING:
    from collections.abc import Callable


@final
class UncachedIndex:
    """Sparse physical graph and per-actor holdings of one immutable round snapshot."""

    def __init__(
        self,
        geography: Geography,
        state: Snapshot,
        checkpoint: Callable[[], None],
        *,
        physical: object = None,
    ) -> None:
        _ = physical  # Accept the optimized index's argument, but always build from scratch.
        self.geography = geography
        self.places = {place.key: place for place in geography.districts}
        self.settlements = {place.district: place for place in state.settlements}
        self.capacities = {
            place.key: place.population + place.headroom for place in geography.districts
        }
        self.actors = {actor.key: actor for actor in state.actors}
        self.owner = {holding.district: holding.actor for holding in state.holdings}
        self.members: dict[str, set[str]] = {actor.key: set() for actor in state.actors}
        for holding in state.holdings:
            require(holding.actor in self.members, "Holding refers to an unknown actor")
            self.members[holding.actor].add(holding.district)
        self.adjacency: dict[str, dict[str, int]] = {key: {} for key in self.places}
        for number, route in enumerate(geography.routes):
            if number % 128 == 0:
                checkpoint()
            if route.sea_steps <= geography.rules.max_sea_steps:
                self.adjacency[route.first][route.second] = route.cost
                self.adjacency[route.second][route.first] = route.cost
        self.passages = tuple(
            (route.first, route.second, route.cost, route.sea_steps)
            for route in geography.routes
            if route.sea_steps <= geography.rules.max_sea_steps
        )
        self.inhabited = frozenset(key for key, place in self.places.items() if place.population)
        self.budget = _population_totals(
            pop for place in geography.districts for pop in place.cohorts
        )
        self.valid_settlements: dict[int, Settlement] = {}

    def cohorts(self, key: str) -> tuple[Cohort, ...]:
        return self.settlements[key].cohorts

    def population(self, key: str) -> int:
        return sum(pop.population for pop in self.cohorts(key))

    def peasants(self, key: str) -> int:
        return sum(pop.peasants for pop in self.cohorts(key))

    def connected(self, members: set[str], seat: str) -> bool:
        if seat not in members:
            return False
        seen, pending = {seat}, [seat]
        while pending:
            for other in self.adjacency[pending.pop()].keys() & members - seen:
                seen.add(other)
                pending.append(other)
        return seen == members

    def supported(self, actor: Actor, members: set[str]) -> bool:
        if not members or not self.connected(members, actor.seat):
            return False
        if any(self.places[key].tenure != actor.tenure for key in members):
            return False
        if actor.tenure is not Tenure.LAND:
            return True
        rules = self.geography.rules

        def viable(keys: set[str]) -> bool:
            people = sum(self.population(key) for key in keys)
            farmers = sum(self.peasants(key) for key in keys)
            return farmers >= rules.minimum_peasants and farmers * PERMILLE >= (
                people * rules.minimum_share
            )

        return viable(members) and viable({actor.seat})
