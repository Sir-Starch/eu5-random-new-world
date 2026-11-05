"""Local history prerequisites and transitions, all evaluated on the prior snapshot."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import astuple, replace
from typing import TYPE_CHECKING, Final

from rnw.history_context import MUTUAL, Context
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
    Knowledge,
    Memory,
    Military,
    Outcome,
    Partition,
    Proposal,
    Reason,
    Tenure,
    TrajectoryKind,
    Transfer,
)
from rnw.history_societies import (
    merged,
    migration_allowed,
    migration_effects,
    reform_allowed,
    reform_cost,
    reform_event,
    successor,
)
from rnw.rng import SplitMix64, derive_seed

if TYPE_CHECKING:
    from collections.abc import Mapping

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
    Action.REFORM: 700,
    Action.MIGRATION: 200,
    Action.PRESSURE: 600,
    Action.INDEPENDENCE: 400,
    Action.SECESSION: 1000,
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
    Action.REFORM: 2,
    Action.MIGRATION: 3,
    Action.PRESSURE: 2,
    Action.INDEPENDENCE: 3,
    Action.SECESSION: 0,
}
UNION_SETTLE_YEARS: Final[int] = 25
CLIENT_CAPACITY_MULTIPLIER: Final[int] = 4
# D25: a lord holds at least twice the subject's locations and three times its power;
# a subject may leave once the lord has fallen below twice its power.
LORD_LOCATIONS: Final[int] = 2
LORD_POWER: Final[int] = 3
LEAVE_POWER: Final[int] = 2


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
            astuple(proposal.reform) if proposal.reform else (),
            (
                (
                    proposal.movement.source,
                    proposal.movement.destination,
                    proposal.movement.cohort.culture,
                    proposal.movement.cohort.religion,
                    proposal.movement.cohort.population,
                    proposal.movement.cohort.peasants,
                )
                if proposal.movement
                else None
            ),
        ),
        ensure_ascii=True,
        separators=(",", ":"),
    )


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
    # Without a grievance a society fights only with a clear advantage; the holder of
    # an expansion aim accepts a contest at equal strength (D23: its choice of risk).
    margin = 2 if first in context.aims else 3
    if context.score(first, second, Factor.GRIEVANCE) == 0 and 2 * context.power(first) < (
        context.power(second) * margin
    ):
        return Reason.OPPORTUNITY
    if context.burden(first, proposal.districts) > context.limit(first):
        return Reason.CAPACITY
    return None


def _pressure_allowed(context: Context, proposal: Proposal) -> Reason | None:
    first, second = proposal.actor, proposal.target
    attacker, defender = context.index.actors[first], context.index.actors[second]
    if (
        attacker.tenure is not Tenure.LAND
        or defender.tenure is Tenure.LAND
        or first in context.subjects
        or context.has(Action.PACT, first, second)
        or attacker.society.military is not Military.OFFENSIVE
        or context.power(first) < 2 * context.power(second)
        or len(proposal.districts) != 1
        or not set(proposal.districts) <= context.index.members[second]
    ):
        return Reason.INELIGIBLE
    return (
        None
        if any(
            context.index.adjacency[key].keys() & context.index.members[first]
            for key in proposal.districts
        )
        else Reason.UNREACHABLE
    )


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


def _submission_cause(context: Context, proposal: Proposal) -> Reason | None:
    """D25: a recorded defeat by the lord, or a recorded threat the lord can face.

    A merely larger neighbour is no cause for submission.
    """
    first, second, threat = proposal.actor, proposal.target, proposal.threat
    if not threat:
        return Reason.THREAT if context.score(first, second, Factor.FEAR) == 0 else None
    if threat in (first, second):
        return Reason.THREAT
    if threat not in context.reach.get(first, {}) or threat not in context.reach.get(second, {}):
        return Reason.UNREACHABLE
    if not (
        context.score(first, threat, Factor.FEAR) > 0
        or context.score(first, threat, Factor.GRIEVANCE) > 0
    ):
        return Reason.THREAT
    return Reason.IMBALANCE if context.power(second) < context.power(threat) else None


def _dependency_allowed(context: Context, proposal: Proposal) -> Reason | None:  # noqa: PLR0911
    first, second = proposal.actor, proposal.target
    subject, lord = context.index.actors[first], context.index.actors[second]
    if first in context.pact_participants:
        return Reason.INELIGIBLE
    if (
        subject.tenure is not Tenure.LAND
        or lord.tenure is not Tenure.LAND
        or lord.technology < context.history.geography.rules.minimum_overlord_technology
        or first in context.subjects
        or len(context.index.members[second]) < LORD_LOCATIONS * len(context.index.members[first])
        or context.power(second) < LORD_POWER * context.power(first)
    ):
        return Reason.IMBALANCE
    reason = _submission_cause(context, proposal)
    if reason is not None:
        return reason
    lords = context.lords
    current = second
    while current in lords:
        if current == first:
            return Reason.INELIGIBLE
        current = lords[current]
    if current == first:
        return Reason.INELIGIBLE
    incoming = context.realm(first)
    for ruler in context.administrators(second):
        profile = context.index.actors[ruler].society
        clients = (context.realm(ruler) - {ruler}) | incoming
        load = sum(context.population(key) for key in clients)
        capacity = (
            context.population(ruler)
            * profile.centralization
            * profile.integration
            * CLIENT_CAPACITY_MULTIPLIER
        )
        if load * PERMILLE**2 > capacity:
            return Reason.CAPACITY
    return None


def _independence_allowed(context: Context, proposal: Proposal) -> Reason | None:
    first, second = proposal.actor, proposal.target
    if context.lords.get(first) != second:
        return Reason.INELIGIBLE
    weakened = context.power(second) < LEAVE_POWER * context.power(first)
    overreached = context.burden(second) > context.capacity(second)
    if not (weakened or overreached or context.setbacks(second, first)):
        return Reason.OBLIGATIONS
    return None


def breakaway_seat(context: Context, districts: tuple[str, ...], founder: str) -> str:
    """The founder's own seat when it is part of the province, else its largest place."""
    seat = context.index.actors[founder].seat
    if seat in districts:
        return seat
    return min(districts, key=lambda key: (-context.index.population(key), key))


def _secession_allowed(context: Context, proposal: Proposal) -> Reason | None:
    """D24: a realm beyond its unrest threshold can lose one conquered founder's province."""
    actor = context.index.actors[proposal.actor]
    parts = sorted(proposal.partitions, key=lambda part: part.seat != actor.seat)
    if actor.tenure is not Tenure.LAND or len(parts) != MIN_PARTITIONS:
        return Reason.INELIGIBLE
    core, away = parts
    districts = [*core.districts, *away.districts]
    if (
        core.seat != actor.seat
        or len(set(districts)) != len(districts)
        or set(districts) != context.index.members[actor.key]
        or core.authority is not actor.authority
    ):
        return Reason.INELIGIBLE
    founders = {context.founders.get(key, "") for key in away.districts}
    founder = next(iter(founders)) if len(founders) == 1 else ""
    if (
        not founder
        or founder in context.ancestry(actor.key)
        or context.index.actors[founder].tenure is not Tenure.LAND
        or away.seat != breakaway_seat(context, away.districts, founder)
        or away.authority is not context.index.actors[founder].authority
    ):
        return Reason.INELIGIBLE
    if context.burden(actor.key) <= context.unrest(actor.key):
        return Reason.CAPACITY
    if not context.index.supported(actor, set(core.districts)) or not context.index.supported(
        replace(actor, seat=away.seat), set(away.districts)
    ):
        return Reason.SUPPORT
    return None


def _league_allowed(context: Context, proposal: Proposal) -> Reason | None:
    """D23: members of one seeded league or confederation bargain without a third party."""
    first, second = proposal.actor, proposal.target
    shared = [
        item for item in context.groups.get(first, ()) if item in context.groups.get(second, ())
    ]
    one, other = context.index.actors[first], context.index.actors[second]
    for item in shared:
        if item.kind is TrajectoryKind.SEA_LEAGUE:
            if (
                one.tenure is Tenure.LAND
                and other.tenure is Tenure.LAND
                and context.has(Action.EXCHANGE, first, second)
                and context.score(first, second, Factor.TRUST) > 0
                and context.score(second, first, Factor.TRUST) > 0
            ):
                return None
        elif (
            item.kind is TrajectoryKind.HIGHLAND_CONFEDERATION
            and one.tenure is Tenure.TRIBE
            and other.tenure is Tenure.TRIBE
            and second in context.land_near.get(first, set())
            and bool({first, second} & context.afraid)
        ):
            return None
    return Reason.THREAT


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
    if proposal.kind is Action.REFORM:
        return reform_allowed(context, proposal)
    if proposal.kind is Action.SEPARATION:
        return _separation_allowed(context, proposal)
    if proposal.kind is Action.SECESSION:
        return _secession_allowed(context, proposal)
    if proposal.kind is Action.INDEPENDENCE:
        return _independence_allowed(context, proposal)
    first, second = proposal.actor, proposal.target
    if second not in context.reach.get(first, {}):
        return Reason.UNREACHABLE
    if proposal.kind is Action.CONTACT:
        return Reason.DUPLICATE if (first, second) in context.known else None
    if (first, second) not in context.known or (second, first) not in context.known:
        return Reason.UNKNOWN
    if proposal.kind is Action.MIGRATION:
        if (
            max(
                context.score(first, second, Factor.GRIEVANCE),
                context.score(second, first, Factor.GRIEVANCE),
            )
            >= context.history.geography.rules.union_trust
        ):
            return Reason.HOSTILE
        return migration_allowed(context, proposal)
    if proposal.kind is Action.UNION:
        return _union_allowed(context, proposal)
    if proposal.kind is Action.CONFLICT:
        return _conflict_allowed(context, proposal)
    if proposal.kind is Action.PRESSURE:
        return _pressure_allowed(context, proposal)
    if proposal.kind is Action.DEPENDENCY:
        return _dependency_allowed(context, proposal)
    if proposal.kind in {Action.PACT, Action.PROTECTION}:
        if proposal.kind is Action.PACT and {first, second} & context.subjects:
            return Reason.INELIGIBLE
        reason = (
            _league_allowed(context, proposal)
            if proposal.kind is Action.PACT and not proposal.threat
            else _threat_allowed(context, proposal)
        )
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
    if (
        proposal.kind is Action.EXCHANGE
        and tuple(sorted((first, second))) in context.recent_exchanges
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
            key=lambda key: (index.population(key), key),
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
            (
                merged(context, retired, part.seat, part.authority)
                if proposal.kind is Action.UNION
                else successor(context, actor, part.seat, part.authority)
            ),
            max(index.actors[key].technology for key in retired),
            event.year,
            event.key,
            tuple(sorted(part.districts)),
            retired,
            society_cause=event.key,
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
    frontier = {
        place
        for place in proposal.districts
        if index.adjacency[place].keys() & index.members[first]
    }
    place = min(frontier, key=lambda key: (context.distance(first, key), key))
    stream = SplitMix64(derive_seed(context.history.seed, "history", "battle", event.key))
    powers: dict[str, int] = {}
    for side in (first, second):
        power = context.power(side) * COST[Action.CONFLICT]
        power += sum(context.power(ally) * amount for ally, amount in support[side].items())
        distance = context.distance(side, place)
        profile = index.actors[side].society
        travel = distance * (1500 - profile.centralization) // PERMILLE
        powers[side] = power * (800 + stream.below(401)) // (PERMILLE + travel // 4)
        posture = 1000
        if profile.military is not Military.BALANCED:
            posture = 1150 if (profile.military is Military.OFFENSIVE) == (side == first) else 850
        powers[side] = powers[side] * posture // PERMILLE
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
            retired=() if remaining or proposal.kind is Action.PRESSURE else (second,),
            transfers=(
                tuple(Transfer(key, second, first) for key in sorted(proposal.districts))
                if proposal.kind is Action.CONFLICT
                else ()
            ),
            memories=(
                _memory(event, second, first, Factor.GRIEVANCE, 220),
                _memory(event, second, first, Factor.FEAR, 120),
                _memory(event, first, second, Factor.COMPETITION, 60),
            ),
        ),
    )


def _independence(context: Context, event: Event, proposal: Proposal) -> Effects:
    subject, lord = proposal.actor, proposal.target
    bond = next(
        bond
        for bond in context.state.bonds
        if bond.kind is Action.DEPENDENCY and bond.first == subject and bond.second == lord
    )
    return Effects(
        ended=(bond,),
        memories=(
            _memory(event, lord, subject, Factor.GRIEVANCE, 100),
            _memory(event, subject, lord, Factor.COMPETITION, 60),
        ),
    )


def _secession(context: Context, event: Event, proposal: Proposal) -> Effects:
    realm = context.index.actors[proposal.actor]
    away = next(part for part in proposal.partitions if part.seat != realm.seat)
    founder = context.index.actors[context.founders[away.districts[0]]]
    created = Actor(
        f"{event.key}_0",
        Tenure.LAND,
        away.seat,
        successor(context, realm, away.seat, away.authority),
        founder.technology,
        event.year,
        event.key,
        tuple(sorted(away.districts)),
        society_cause=event.key,
    )
    return Effects(
        created=(created,),
        transfers=tuple(Transfer(key, realm.key, created.key) for key in sorted(away.districts)),
        knowledge=(
            Knowledge(realm.key, created.key, event.key),
            Knowledge(created.key, realm.key, event.key),
        ),
        memories=(
            _memory(event, created.key, realm.key, Factor.GRIEVANCE, 150),
            _memory(event, realm.key, created.key, Factor.GRIEVANCE, 100),
        ),
    )


def _peaceful(context: Context, event: Event, proposal: Proposal) -> Effects:
    first, second = proposal.actor, proposal.target
    if proposal.kind is Action.MIGRATION:
        return migration_effects(context, event, proposal)
    if proposal.kind is Action.INDEPENDENCE:
        return _independence(context, event, proposal)
    if proposal.kind is Action.SECESSION:
        return _secession(context, event, proposal)
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
    trust = 60 + min(context.index.actors[key].society.tradition for key in (first, second)) // 25
    if proposal.kind is Action.ACCESS:
        trust += context.index.actors[second].society.religious_authority // 50
    memories = [_memory(event, first, second, Factor.TRUST, trust)]
    if proposal.kind in {Action.EXCHANGE, Action.PACT}:
        memories.append(_memory(event, second, first, Factor.TRUST, trust))
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
        Action.REFORM: Reason.REPEATED_PROBLEM,
        Action.MIGRATION: Reason.PRESSURE,
        Action.PRESSURE: Reason.PRESSURE,
        Action.INDEPENDENCE: Reason.AUTONOMY,
        Action.SECESSION: Reason.CAPACITY,
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
    if proposal.kind is Action.REFORM:
        cost = reform_cost(context, proposal)
    elif proposal.kind in {Action.CONFLICT, Action.PRESSURE}:
        cost += min(200, context.burden(proposal.actor) // 5)
    costs = {proposal.actor: cost}
    # Submitting to or leaving a lord spends the subject's effort; the lord's load is
    # bounded by its administrative capacity, not by its round's other commitments.
    if proposal.target and proposal.kind not in {Action.INDEPENDENCE, Action.DEPENDENCY}:
        costs[proposal.target] = cost
    if proposal.kind in {Action.CONFLICT, Action.PRESSURE}:
        # A defender spends what it has left: being busy is no shield. Arbitration
        # still allows one contest per participant and round.
        costs[proposal.target] = min(cost, remaining.get(proposal.target, 0))
    if reason is None and any(remaining.get(key, 0) < value for key, value in costs.items()):
        reason = Reason.COMMITTED
    if reason is not None:
        return replace(event, outcome=Outcome.REFUSED, reason=reason), {}
    if proposal.kind is Action.REFORM:
        return reform_event(context, event, proposal), costs
    if proposal.kind in {Action.CONFLICT, Action.PRESSURE}:
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
