"""Local history prerequisites and transitions, all evaluated on the prior snapshot."""

from __future__ import annotations

import heapq
import json
from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING, Final, final

from rnw.history_checks import Index
from rnw.history_model import (
    MIN_PARTITIONS,
    PERMILLE,
    Action,
    Actor,
    Authority,
    Bond,
    Effects,
    Event,
    Factor,
    History,
    Knowledge,
    Memory,
    Outcome,
    Partition,
    Proposal,
    Reason,
    Tenure,
    Transfer,
)
from rnw.rng import SplitMix64, derive_seed

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

COST: Final[dict[Action, int]] = {
    Action.CONTACT: 50,
    Action.EXCHANGE: 100,
    Action.UNION: 1000,
    Action.CONFLICT: 600,
    Action.DEPENDENCY: 400,
    Action.PROTECTION: 300,
    Action.PACT: 400,
    Action.SEPARATION: 1000,
    Action.ACCESS: 100,
}
PRIORITY: Final[dict[Action, int]] = {
    Action.SEPARATION: 0,
    Action.UNION: 1,
    Action.CONFLICT: 2,
    Action.DEPENDENCY: 3,
    Action.PROTECTION: 4,
    Action.PACT: 4,
    Action.ACCESS: 5,
    Action.EXCHANGE: 5,
    Action.CONTACT: 6,
}
UNION_SETTLE_YEARS: Final[int] = 25

MUTUAL: Final[frozenset[Action]] = frozenset(
    {Action.CONTACT, Action.EXCHANGE, Action.UNION, Action.PACT}
)


def proposal_key(proposal: Proposal) -> str:
    return json.dumps(
        (
            proposal.kind,
            proposal.actor,
            proposal.target,
            tuple(sorted(proposal.districts)),
            tuple(
                (part.seat, part.authority, tuple(sorted(part.districts)))
                for part in sorted(proposal.partitions, key=lambda part: part.seat)
            ),
            proposal.threat,
            proposal.rank,
        ),
        ensure_ascii=True,
        separators=(",", ":"),
    )


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
            population = sum(self.index.places[place].population for place in members)
            peasants = sum(self.index.places[place].peasants for place in members)
            technology = self.index.actors[key].technology
            self.powers[key] = (population + peasants) * (technology + 1)
        return self.powers[key]

    def distance(self, key: str, target: str) -> int:
        """Travel through the actor's own territory to the attacking/defending frontier."""
        actor = self.index.actors[key]
        members = self.index.members[key]
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
        return tuple(sorted(causes))


def event_key(context: Context, proposal: Proposal) -> str:
    draw = derive_seed(
        context.history.seed, "history", "event", str(context.state.year), proposal_key(proposal)
    )
    return f"h{context.state.year}_{proposal.kind}_{draw:016x}"


def _memory(event: Event, first: str, second: str, factor: Factor, weight: int) -> Memory:
    return Memory(first, second, factor, event.year, weight, 1, event.key)


def _union_allowed(context: Context, proposal: Proposal) -> Reason | None:
    first, second = proposal.actor, proposal.target
    one, other = context.index.actors[first], context.index.actors[second]
    if (
        one.tenure is not Tenure.LAND
        or other.tenure is not Tenure.LAND
        or first in context.bound
        or second in context.bound
        or second not in context.near.get(first, {})
    ):
        return Reason.INELIGIBLE
    threshold = context.history.geography.rules.union_trust
    if (
        max(
            context.score(first, second, Factor.GRIEVANCE),
            context.score(second, first, Factor.GRIEVANCE),
        )
        >= threshold
    ):
        return Reason.HOSTILE
    if min(
        context.score(first, second, Factor.TRUST), context.score(second, first, Factor.TRUST)
    ) < (threshold):
        return Reason.BARGAIN
    return None


def _conflict_allowed(context: Context, proposal: Proposal) -> Reason | None:
    first, second = proposal.actor, proposal.target
    index = context.index
    attacker, defender = index.actors[first], index.actors[second]
    taken = set(proposal.districts)
    if (
        attacker.tenure is not Tenure.LAND
        or defender.tenure is not Tenure.LAND
        or first in context.subjects
        or second in context.subjects
        or not taken
        or not taken <= index.members[second]
        or context.has(Action.PACT, first, second)
    ):
        return Reason.INELIGIBLE
    if not any(index.adjacency[key].keys() & index.members[first] for key in taken):
        return Reason.UNREACHABLE
    remaining = index.members[second] - taken
    if not index.supported(attacker, index.members[first] | taken) or (
        remaining and not index.supported(defender, remaining)
    ):
        return Reason.SUPPORT
    if context.score(first, second, Factor.GRIEVANCE) == 0 and context.power(first) < (
        context.power(second) * 3 // 2
    ):
        return Reason.OPPORTUNITY
    return None


def _separation_allowed(context: Context, proposal: Proposal) -> Reason | None:
    actor = context.index.actors[proposal.actor]
    parts = proposal.partitions
    districts = [key for part in parts for key in part.districts]
    if (
        actor.tenure is not Tenure.LAND
        or not actor.parents
        or proposal.actor in context.bound
        or len(parts) < MIN_PARTITIONS
        or len(set(districts)) != len(districts)
        or set(districts) != context.index.members[actor.key]
        or len({part.seat for part in parts}) != len(parts)
    ):
        return Reason.INELIGIBLE
    distant = any(context.distance(actor.key, key) >= 3 * PERMILLE for key in actor.homeland)
    authorities = {context.index.actors[key].authority for key in actor.parents}
    if context.state.year - actor.born < UNION_SETTLE_YEARS or (
        not distant and len(authorities) == 1
    ):
        return Reason.OBLIGATIONS
    if not all(
        context.index.supported(replace(actor, seat=part.seat), set(part.districts))
        for part in parts
    ):
        return Reason.SUPPORT
    return None


def _dependency_allowed(context: Context, proposal: Proposal) -> Reason | None:
    first, second = proposal.actor, proposal.target
    subject, lord = context.index.actors[first], context.index.actors[second]
    if any(
        bond.kind is Action.PACT and first in (bond.first, bond.second)
        for bond in context.state.bonds
    ):
        return Reason.INELIGIBLE
    if (
        subject.tenure is not Tenure.LAND
        or lord.tenure is not Tenure.LAND
        or lord.technology < context.history.geography.rules.minimum_overlord_technology
        or any(
            bond.kind is Action.DEPENDENCY and bond.first == first for bond in context.state.bonds
        )
        or context.power(second) < 2 * context.power(first)
    ):
        return Reason.IMBALANCE
    lords = {
        bond.first: bond.second for bond in context.state.bonds if bond.kind is Action.DEPENDENCY
    }
    current = second
    while current in lords:
        if current == first:
            return Reason.INELIGIBLE
        current = lords[current]
    return Reason.INELIGIBLE if current == first else None


def _threat_allowed(context: Context, proposal: Proposal) -> Reason | None:
    threat = proposal.threat
    partners = (proposal.actor, proposal.target)
    if not threat or threat in partners:
        return Reason.THREAT
    if not all(threat in context.reach.get(key, {}) for key in partners):
        return Reason.UNREACHABLE
    if not all(
        context.score(key, threat, Factor.FEAR) > 0
        or context.score(key, threat, Factor.GRIEVANCE) > 0
        for key in partners
    ):
        return Reason.THREAT
    return None


def eligible(context: Context, proposal: Proposal) -> Reason | None:  # noqa: C901, PLR0911, PLR0912
    if proposal.kind is Action.SEPARATION:
        return _separation_allowed(context, proposal)
    first, second = proposal.actor, proposal.target
    if second not in context.reach.get(first, {}):
        return Reason.UNREACHABLE
    if proposal.kind is Action.CONTACT:
        return Reason.DUPLICATE if (first, second) in context.known else None
    if (first, second) not in context.known or (second, first) not in context.known:
        return Reason.UNKNOWN
    if proposal.kind is Action.UNION:
        return _union_allowed(context, proposal)
    if proposal.kind is Action.CONFLICT:
        return _conflict_allowed(context, proposal)
    if proposal.kind is Action.DEPENDENCY:
        return _dependency_allowed(context, proposal)
    if proposal.kind in {Action.PACT, Action.PROTECTION}:
        if proposal.kind is Action.PACT and {first, second} & context.subjects:
            return Reason.INELIGIBLE
        reason = _threat_allowed(context, proposal)
        if reason is not None:
            return reason
    if proposal.kind is Action.ACCESS:
        if len(proposal.districts) != 1:
            return Reason.INELIGIBLE
        place = proposal.districts[0]
        if place not in context.index.members[second] or not context.index.places[place].sacred:
            return Reason.SACRED_ACCESS
    if max(
        context.score(first, second, Factor.GRIEVANCE),
        context.score(second, first, Factor.GRIEVANCE),
    ) >= (context.history.geography.rules.union_trust):
        return Reason.HOSTILE
    if context.has(proposal.kind, first, second) and proposal.kind is not Action.EXCHANGE:
        return Reason.DUPLICATE
    if proposal.kind is Action.EXCHANGE and any(
        bond.kind is Action.EXCHANGE
        and {bond.first, bond.second} == {first, second}
        and context.event_years[bond.cause] > context.state.year - 15
        for bond in context.state.bonds
    ):
        return Reason.DUPLICATE
    return None


def inherit_round(context: Context, events: list[Event]) -> list[Event]:  # noqa: C901 - one joint transition for memory and knowledge
    """Construct inheritance from all resolved transitions before committing the round.

    When both endpoints change simultaneously, the later transition holds the joint
    consequence and references the earlier one. Neither proposal sees that consequence.
    """
    changed: dict[str, tuple[str, ...]] = {}
    position: dict[str, int] = {}
    for number, event in enumerate(events):
        for old in event.effects.retired:
            changed[old] = tuple(actor.key for actor in event.effects.created)
            position[old] = number
    memories: dict[int, list[Memory]] = defaultdict(list)
    knowledge: dict[int, dict[tuple[str, str], Knowledge]] = defaultdict(dict)
    causes: dict[int, set[str]] = defaultdict(set)

    def destinations(
        first: str, second: str, cause: str
    ) -> tuple[int, tuple[tuple[str, str], ...]]:
        affected = {position[key] for key in (first, second) if key in changed}
        if not affected or not all(
            key in changed or context.index.actors[key].living for key in (first, second)
        ):
            return -1, ()
        number = max(affected)
        causes[number].add(cause)
        causes[number].update(events[index].key for index in affected if index != number)
        return number, tuple(
            (one, other)
            for one in changed.get(first, (first,))
            for other in changed.get(second, (second,))
            if one != other
        )

    for memory in context.state.memories:
        weight = memory.at(context.state.year)
        if weight:
            number, pairs = destinations(memory.first, memory.second, memory.cause)
            memories[number].extend(
                _memory(events[number], first, second, memory.factor, weight)
                for first, second in pairs
            )
    for known in context.state.knowledge:
        number, pairs = destinations(known.first, known.second, known.cause)
        for first, second in pairs:
            knowledge[number][first, second] = Knowledge(first, second, events[number].key)
    for number, event in enumerate(events):
        for first in event.effects.created:
            for second in event.effects.created:
                if first.key != second.key:
                    knowledge[number][first.key, second.key] = Knowledge(
                        first.key, second.key, event.key
                    )
    return [
        replace(
            event,
            causes=tuple(sorted(set(event.causes) | causes[number])),
            effects=replace(
                event.effects,
                memories=(*event.effects.memories, *memories[number]),
                knowledge=(
                    *event.effects.knowledge,
                    *(knowledge[number][pair] for pair in sorted(knowledge[number])),
                ),
            ),
        )
        for number, event in enumerate(events)
    ]


def _structural(context: Context, event: Event, proposal: Proposal) -> Effects:
    index = context.index
    actor = index.actors[proposal.actor]
    if proposal.kind is Action.UNION:
        retired = tuple(sorted((proposal.actor, proposal.target)))
        members = {place for key in retired for place in index.members[key]}
        # A union keeps a viable existing seat; this is an explicit bargain, not a repair.
        seat = max(
            (index.actors[key].seat for key in retired),
            key=lambda key: (index.places[key].population, key),
        )
        parts = (Partition(tuple(sorted(members)), seat, Authority.COUNCIL),)
    else:
        retired = (proposal.actor,)
        parts = tuple(sorted(proposal.partitions, key=lambda part: part.seat))
    created = tuple(
        Actor(
            f"{event.key}_{number}",
            actor.tenure,
            part.seat,
            part.authority,
            max(index.actors[key].technology for key in retired),
            event.year,
            event.key,
            tuple(sorted(part.districts)),
            retired,
        )
        for number, part in enumerate(parts)
    )
    return Effects(
        created=created,
        retired=retired,
        transfers=tuple(
            Transfer(key, index.owner[key], country.key)
            for country in created
            for key in country.homeland
        ),
    )


def _battle_support(
    context: Context, proposal: Proposal, remaining: Mapping[str, int]
) -> dict[str, dict[str, int]]:
    support: dict[str, dict[str, int]] = {proposal.actor: {}, proposal.target: {}}
    allies = {
        side: {
            bond.second if bond.first == side else bond.first
            for bond in context.state.bonds
            if (bond.kind is Action.PACT and side in (bond.first, bond.second))
            or (bond.kind is Action.DEPENDENCY and bond.second == side)
        }
        for side in support
    }
    for side, allocations in support.items():
        other = proposal.target if side == proposal.actor else proposal.actor
        # Conflicting obligations do not let an ally fight on both sides.
        for ally in sorted(allies[side] - allies[other] - set(support)):
            if side in context.reach.get(ally, {}):
                available = min(300, remaining.get(ally, 0))
                if available:
                    allocations[ally] = available
    return support


def _battle(
    context: Context, event: Event, proposal: Proposal, support: dict[str, dict[str, int]]
) -> Event:
    index = context.index
    first, second = proposal.actor, proposal.target
    place = min(proposal.districts)
    stream = SplitMix64(derive_seed(context.history.seed, "history", "battle", event.key))
    powers: dict[str, int] = {}
    for side in (first, second):
        power = context.power(side) * COST[Action.CONFLICT]
        power += sum(context.power(ally) * amount for ally, amount in support[side].items())
        distance = context.distance(side, place)
        powers[side] = power * (800 + stream.below(401)) // (PERMILLE + distance // 4)
    attack = powers[first]
    defence = powers[second] * index.places[place].defence // PERMILLE
    if attack <= defence:
        return replace(
            event,
            outcome=Outcome.FAILED,
            reason=Reason.REPELLED,
            effects=Effects(
                memories=(
                    _memory(event, first, second, Factor.FEAR, 120),
                    _memory(event, second, first, Factor.GRIEVANCE, 80),
                )
            ),
        )
    remaining = index.members[second] - set(proposal.districts)
    return replace(
        event,
        effects=Effects(
            retired=() if remaining else (second,),
            transfers=tuple(Transfer(key, second, first) for key in sorted(proposal.districts)),
            memories=(
                _memory(event, second, first, Factor.GRIEVANCE, 220),
                _memory(event, second, first, Factor.FEAR, 120),
                _memory(event, first, second, Factor.COMPETITION, 60),
            ),
        ),
    )


def _peaceful(context: Context, event: Event, proposal: Proposal) -> Effects:
    first, second = proposal.actor, proposal.target
    if proposal.kind is Action.CONTACT:
        return Effects(
            knowledge=(Knowledge(first, second, event.key), Knowledge(second, first, event.key)),
            memories=(_memory(event, first, second, Factor.AFFINITY, 20),),
        )
    if proposal.kind in {Action.UNION, Action.SEPARATION}:
        return _structural(context, event, proposal)
    pair = tuple(sorted((first, second))) if proposal.kind in MUTUAL else (first, second)
    bond = Bond(
        proposal.kind,
        pair[0],
        pair[1],
        event.key,
        proposal.districts[0] if proposal.kind is Action.ACCESS else "",
    )
    memories = [_memory(event, first, second, Factor.TRUST, 80)]
    if proposal.kind in {Action.EXCHANGE, Action.PACT}:
        memories.append(_memory(event, second, first, Factor.TRUST, 80))
    if proposal.kind in {Action.DEPENDENCY, Action.PROTECTION}:
        memories.append(_memory(event, first, second, Factor.DEPENDENCE, 100))
    return Effects(bonds=(bond,), memories=tuple(memories))


def adjudicate(
    context: Context, proposal: Proposal, remaining: Mapping[str, int]
) -> tuple[Event, dict[str, int]]:
    reasons = {
        Action.CONTACT: Reason.ENCOUNTER,
        Action.EXCHANGE: Reason.COOPERATION,
        Action.UNION: Reason.BARGAIN,
        Action.SEPARATION: Reason.OBLIGATIONS,
        Action.DEPENDENCY: Reason.IMBALANCE,
        Action.PROTECTION: Reason.THREAT,
        Action.PACT: Reason.THREAT,
        Action.ACCESS: Reason.SACRED_ACCESS,
        Action.CONFLICT: Reason.GRIEVANCE
        if context.score(proposal.actor, proposal.target, Factor.GRIEVANCE)
        else Reason.OPPORTUNITY,
    }
    event = Event(
        event_key(context, proposal),
        context.state.year,
        proposal.kind,
        tuple(sorted({key for key in (proposal.actor, proposal.target, proposal.threat) if key})),
        context.causes(proposal),
        Outcome.ACCEPTED,
        reasons[proposal.kind],
    )
    reason = eligible(context, proposal)
    cost = COST[proposal.kind]
    costs = {proposal.actor: cost}
    if proposal.target:
        costs[proposal.target] = cost
    if reason is None and any(remaining.get(key, 0) < value for key, value in costs.items()):
        reason = Reason.COMMITTED
    if reason is not None:
        return replace(event, outcome=Outcome.REFUSED, reason=reason), {}
    if proposal.kind is Action.CONFLICT:
        support = _battle_support(context, proposal, remaining)
        costs.update(
            {key: value for allocations in support.values() for key, value in allocations.items()}
        )
        event = _battle(context, event, proposal, support)
        # Actual allied commitments are part of the causal event, including their pact.
        allies = set(costs) - {proposal.actor, proposal.target}
        causes = set(event.causes)
        causes.update(context.index.actors[key].origin for key in allies)
        causes.update(
            bond.cause
            for bond in context.state.bonds
            if bond.kind in {Action.PACT, Action.DEPENDENCY}
            and (bond.first in allies or bond.second in allies)
        )
        return replace(
            event, actors=tuple(sorted(set(event.actors) | allies)), causes=tuple(sorted(causes))
        ), costs
    return replace(event, effects=_peaceful(context, event, proposal)), costs
