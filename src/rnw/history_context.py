"""Sparse facts, causal lookup and capacity calculations for one immutable round."""

from __future__ import annotations

import heapq
from collections import defaultdict
from typing import TYPE_CHECKING, Final, final

from rnw.history_checks import Index
from rnw.history_model import (
    PERMILLE,
    Action,
    Event,
    Factor,
    History,
    Livelihood,
    Memory,
    Outcome,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.history_model import Proposal

MUTUAL = frozenset({Action.CONTACT, Action.EXCHANGE, Action.UNION, Action.PACT})
INTEGRATION_YEARS: Final[int] = 25


@final
class Context:
    def __init__(self, history: History, checkpoint: Callable[[], None]) -> None:
        self.history = history
        self.state = history.state
        self.index = Index(history.geography, history.state, checkpoint)
        self.checkpoint = checkpoint
        self.known = {(each.first, each.second) for each in self.state.knowledge}
        self.memories: dict[tuple[str, str, Factor], list[Memory]] = defaultdict(list)
        self.causes_by_actor: dict[str, set[str]] = defaultdict(set)
        self.event_years = {event.key: event.year for event in history.events}
        self.event_kinds = {event.key: event.kind for event in history.events}
        self.holdings = {holding.district: holding for holding in self.state.holdings}
        self.experiences: dict[str, list[Event]] = defaultdict(list)
        for event in history.events:
            for key in event.actors:
                self.experiences[key].append(event)
        for actor in self.state.actors:
            self.causes_by_actor[actor.key].add(actor.society_cause)
        for settlement in self.state.settlements:
            self.causes_by_actor[self.index.owner[settlement.district]].add(settlement.cause)
        for holding in self.state.holdings:
            self.causes_by_actor[holding.actor].add(holding.cause)
        for memory in self.state.memories:
            self.memories[memory.first, memory.second, memory.factor].append(memory)
            if memory.at(self.state.year):
                self.causes_by_actor[memory.first].add(memory.cause)
                self.causes_by_actor[memory.second].add(memory.cause)
        for known in self.state.knowledge:
            self.causes_by_actor[known.first].add(known.cause)
            self.causes_by_actor[known.second].add(known.cause)
        for bond in self.state.bonds:
            self.causes_by_actor[bond.first].add(bond.cause)
            self.causes_by_actor[bond.second].add(bond.cause)
        self.scores: dict[tuple[str, str, Factor], int] = {}
        self.powers: dict[str, int] = {}
        self.burdens: dict[tuple[str, tuple[str, ...]], int] = {}
        self.distances: dict[tuple[str, str, tuple[str, ...]], int] = {}
        self.bond_pairs = {(bond.kind, bond.first, bond.second) for bond in self.state.bonds}
        self._contacts()
        self.bound = {
            key
            for bond in self.state.bonds
            if bond.kind is Action.DEPENDENCY
            for key in (bond.first, bond.second)
        }
        self.subjects = {bond.first for bond in self.state.bonds if bond.kind is Action.DEPENDENCY}

    def _contacts(self) -> None:
        self.near: dict[str, dict[str, int]] = defaultdict(dict)
        self.land_near: dict[str, set[str]] = defaultdict(set)
        self.sea_near: dict[str, set[str]] = defaultdict(set)
        for number, route in enumerate(self.history.geography.routes):
            if number % 128 == 0:
                self.checkpoint()
            first, second = self.index.owner.get(route.first), self.index.owner.get(route.second)
            if (
                first
                and second
                and first != second
                and route.sea_steps <= (self.history.geography.rules.max_sea_steps)
            ):
                for one, other in ((first, second), (second, first)):
                    self.near[one][other] = min(route.cost, self.near[one].get(other, route.cost))
                    (self.sea_near if route.sea_steps else self.land_near)[one].add(other)
        self.reach = {key: dict(near) for key, near in self.near.items()}
        # Exchange supplies one intermediary, over verified physical contacts, not sea labels.
        for bond in self.state.bonds:
            if bond.kind is Action.EXCHANGE:
                for one, hub in ((bond.first, bond.second), (bond.second, bond.first)):
                    if hub not in self.near.get(one, {}):
                        continue
                    for other, cost in self.near.get(hub, {}).items():
                        if other != one:
                            distance = cost + self.near[one][hub]
                            current = self.reach.setdefault(one, {}).get(other, distance)
                            self.reach[one][other] = min(current, distance)
                            reverse = self.reach.setdefault(other, {}).get(one, distance)
                            self.reach[other][one] = min(reverse, distance)

    def score(self, first: str, second: str, factor: Factor) -> int:
        key = first, second, factor
        if key not in self.scores:
            self.scores[key] = min(
                PERMILLE, sum(memory.at(self.state.year) for memory in self.memories[key])
            )
        return self.scores[key]

    def has(self, kind: Action, first: str, second: str) -> bool:
        if kind in MUTUAL:
            first, second = sorted((first, second))
        return (kind, first, second) in self.bond_pairs

    def power(self, key: str) -> int:
        if key not in self.powers:
            members = self.index.members[key]
            population = sum(self.index.population(place) for place in members)
            peasants = sum(self.index.peasants(place) for place in members)
            technology = self.index.actors[key].technology
            self.powers[key] = (
                (population + peasants) * (technology + 1) * _coordination(self, key) // PERMILLE
            )
        return self.powers[key]

    def burden(self, key: str, gained: tuple[str, ...] = ()) -> int:
        cache = key, gained
        if cache not in self.burdens:
            self.burdens[cache] = _burden(self, key, gained)
        return self.burdens[cache]

    def distance(self, key: str, target: str, through: tuple[str, ...] = ()) -> int:
        """Travel through the actor's own territory to the attacking/defending frontier."""
        pair = key, target, through
        if pair not in self.distances:
            self.distances[pair] = self._distance(key, target, through)
        return self.distances[pair]

    def _distance(self, key: str, target: str, through: tuple[str, ...]) -> int:
        actor = self.index.actors[key]
        members = self.index.members[key] | set(through)
        costs = {actor.seat: 0}
        pending = [(0, actor.seat)]
        while pending:
            self.checkpoint()
            cost, place = heapq.heappop(pending)
            if cost != costs[place]:
                continue
            if place == target:
                return cost
            for other, step in self.index.adjacency[place].items():
                if (other in members or other == target) and cost + step < costs.get(
                    other, 1 << 60
                ):
                    costs[other] = cost + step
                    heapq.heappush(pending, (cost + step, other))
        return 1 << 60

    def causes(self, proposal: Proposal) -> tuple[str, ...]:
        actors = {key for key in (proposal.actor, proposal.target, proposal.threat) if key}
        causes = {self.index.actors[key].origin for key in actors}
        for key in actors:
            causes.update(self.causes_by_actor[key])
        if proposal.kind is Action.REFORM:
            causes.update(
                event.key
                for event in self.experiences[proposal.actor]
                if event.year >= self.state.year - 75 and event.outcome is not Outcome.REFUSED
            )
        if proposal.kind is Action.SEPARATION:
            seats = {part.seat for part in proposal.partitions}
            causes.update(
                self.index.actors[root.key].society_cause
                for root in self.history.foundings
                if seats & set(root.districts)
            )
        return tuple(sorted(causes))


def _burden(context: Context, actor: str, gained: tuple[str, ...] = ()) -> int:
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
        # New frontier districts can be reached directly; no traversal through foreign interiors.
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
    # Concentrated administration has continuing overhead, including at a homogeneous centre.
    return cost + profile.centralization * len(members) // 40


def _coordination(context: Context, actor: str) -> int:
    profile = context.index.actors[actor].society
    farmers = sum(context.index.peasants(key) for key in context.index.members[actor])
    population = sum(context.index.population(key) for key in context.index.members[actor])
    support = farmers * PERMILLE // population
    livelihood = {
        Livelihood.FARMING: support // 4,
        Livelihood.MIXED: 75,
        Livelihood.MOBILE: 25,
    }[profile.livelihood]
    return max(300, 700 + profile.centralization // 4 + livelihood - context.burden(actor) // 3)
