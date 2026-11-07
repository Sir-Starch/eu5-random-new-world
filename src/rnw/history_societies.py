"""Caused society profiles, costly reform and conservative cohort movement.

This module reads physical opportunity and recorded experience, never game identity
templates or a resource roll. Extraordinary ambitions are in history_trajectories.
"""

from __future__ import annotations

from dataclasses import fields, replace
from typing import TYPE_CHECKING, Final

from rnw.history_model import (
    PERMILLE,
    Action,
    Authority,
    Cohort,
    Effects,
    Exchange,
    Factor,
    Livelihood,
    Memory,
    Military,
    Movement,
    Outcome,
    Proposal,
    Reason,
    Reform,
    Settlement,
    Society,
    Tenure,
)
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rnw.history_context import Context
    from rnw.history_model import Actor, District, Event, Founding

FARMING_SHARE: Final[int] = 500
MOBILE_SHARE: Final[int] = 100
OVERLAND_DRAW: Final[int] = 150
REPEATED_ROUNDS: Final[int] = 2
REFORM_INTERVAL: Final[int] = 15
REFUGE_YEARS: Final[int] = 25
MINORITY_INTEGRATION: Final[int] = 500


def _values(profile: Society) -> dict[str, int]:
    return {
        "centralization": profile.centralization,
        "religious_authority": profile.religious_authority,
        "integration": profile.integration,
        "tradition": profile.tradition,
    }


def cohorts(values: Iterable[Cohort]) -> tuple[Cohort, ...]:
    """Merge identical identities using exact integer totals, without assimilation."""
    totals: dict[tuple[str, str], tuple[int, int]] = {}
    for pop in values:
        key = pop.culture, pop.religion
        people, farmers = totals.get(key, (0, 0))
        totals[key] = people + pop.population, farmers + pop.peasants
    return tuple(
        Cohort(culture, religion, people, farmers)
        for (culture, religion), (people, farmers) in sorted(totals.items())
        if people
    )


def bootstrap(founding: Founding, places: dict[str, District], seed: int) -> Society:
    if founding.society is not None:
        return founding.society
    members = [places[key] for key in founding.districts]
    population = sum(place.population for place in members)
    farmers = sum(place.peasants for place in members)
    farming = farmers * PERMILLE // max(1, population)

    def draw(axis: str) -> int:
        return derive_seed(seed, "history", "society", founding.key, axis) % 301

    return Society(
        centralization=250 + farming // 4 + draw("centralization"),
        authority=founding.authority,
        livelihood=Livelihood.FARMING
        if farming >= FARMING_SHARE
        else (Livelihood.MOBILE if farming < MOBILE_SHARE else Livelihood.MIXED),
        exchange=Exchange.COASTAL
        if any(place.coastal for place in members)
        else (Exchange.OVERLAND if draw("exchange") >= OVERLAND_DRAW else Exchange.INWARD),
        religious_authority=350 + draw("religion"),
        military=Military.BALANCED,
        integration=350 + draw("integration"),
        tradition=350 + draw("tradition"),
    )


def merged(context: Context, parents: tuple[str, ...], seat: str, authority: Authority) -> Society:
    """A union bargains for council rule; other dimensions retain weighted experience."""
    weights = {
        key: sum(context.index.population(place) for place in context.index.members[key])
        for key in parents
    }
    total = sum(weights.values())

    def average(axis: str) -> int:
        return (
            sum(
                _values(context.index.actors[key].society)[axis] * weight
                for key, weight in weights.items()
            )
            // total
        )

    base = context.index.actors[context.index.owner[seat]].society
    # D23: a partner holding an expansion aim keeps its administration in the bargain.
    aimed = [context.index.actors[key].society for key in parents if key in context.aims]
    return replace(
        base,
        authority=authority,
        centralization=max([average("centralization"), *(each.centralization for each in aimed)]),
        religious_authority=average("religious_authority"),
        integration=max([average("integration"), *(each.integration for each in aimed)]),
        tradition=average("tradition"),
    )


def successor(context: Context, actor: Actor, seat: str, authority: Authority) -> Society:
    """A local successor retains both common experience and its local founding tradition."""
    founding = next((root for root in context.history.foundings if seat in root.districts), None)
    local = context.index.actors[founding.key].society if founding else actor.society
    shared = actor.society
    return replace(
        local,
        authority=authority,
        centralization=(local.centralization + shared.centralization) // 2,
        religious_authority=(local.religious_authority + shared.religious_authority) // 2,
        integration=(local.integration + shared.integration) // 2,
        tradition=(local.tradition + shared.tradition) // 2,
    )


def _experience(context: Context, actor: Actor, kinds: set[Action]) -> bool:
    since = max(actor.born, context.event_years[actor.society_cause], context.state.year - 75)
    years = {
        event.year
        for event in context.experiences[actor.key]
        if since < event.year < context.state.year
        and event.kind in kinds
        and event.outcome is not Outcome.REFUSED
    }
    return len(years) >= REPEATED_ROUNDS


def reforms(context: Context, actor: Actor) -> tuple[Society, ...]:
    """Cache immutable snapshot candidates, including for repeated eligibility checks."""
    known = context.reform_choices.get(actor.key)
    if known is not None and (known[0] is actor or known[0] == actor):
        return known[1]
    choices = _reforms(context, actor)
    context.reform_choices[actor.key] = actor, choices
    return choices


def _reforms(context: Context, actor: Actor) -> tuple[Society, ...]:  # noqa: C901, PLR0912 - eight independently caused dimensions
    """Only responses to a repeated recorded problem are candidates for reform."""
    if context.state.year - context.event_years[actor.society_cause] < REFORM_INTERVAL or any(
        event.kind is Action.REFORM and event.year > context.state.year - REFORM_INTERVAL
        for event in context.experiences[actor.key]
    ):
        return ()
    profile = actor.society
    cooperation = _experience(context, actor, {Action.EXCHANGE, Action.PACT})
    # Council rule answers collective bargains (pacts, unions, protection), not the
    # routine exchange that every neighbourhood records (D26).
    collective = _experience(context, actor, {Action.PACT, Action.UNION, Action.PROTECTION})
    pressure = _experience(context, actor, {Action.CONFLICT, Action.PRESSURE, Action.MIGRATION})
    sacred = _experience(context, actor, {Action.ACCESS})
    incorporation = _experience(
        context, actor, {Action.CONFLICT, Action.PRESSURE, Action.UNION, Action.MIGRATION}
    )
    candidates: list[Society] = []

    def shift(axis: str, amount: int) -> None:
        value = _values(profile)[axis] + amount
        if 0 <= value <= PERMILLE:
            candidates.append(replace(profile, **{axis: value}))

    if pressure:
        shift("centralization", 100 if actor.tenure is Tenure.LAND else -100)
        shift("tradition", -100)
        candidates.extend(
            (
                replace(profile, military=Military.DEFENSIVE),
                replace(profile, exchange=Exchange.INWARD),
                replace(profile, livelihood=Livelihood.MOBILE),
            )
        )
        if actor.tenure is Tenure.LAND:
            candidates.extend(
                (
                    replace(profile, authority=Authority.RULER),
                    replace(profile, military=Military.OFFENSIVE),
                )
            )
    if cooperation:
        shift("centralization", -100)
        shift("tradition", 100)
        candidates.extend(
            (
                replace(profile, military=Military.BALANCED),
                replace(profile, livelihood=Livelihood.MIXED),
            )
        )
        if collective:
            candidates.append(replace(profile, authority=Authority.COUNCIL))
        if any(context.index.places[key].coastal for key in context.index.members[actor.key]):
            candidates.append(replace(profile, exchange=Exchange.COASTAL))
        if context.land_near.get(actor.key):
            candidates.append(replace(profile, exchange=Exchange.OVERLAND))
        people = sum(context.index.population(key) for key in context.index.members[actor.key])
        farmers = sum(context.index.peasants(key) for key in context.index.members[actor.key])
        if farmers * PERMILLE >= people * 300:
            candidates.append(replace(profile, livelihood=Livelihood.FARMING))
    if incorporation:
        shift("integration", 100)
    if sacred and any(context.index.places[key].sacred for key in context.index.members[actor.key]):
        shift("religious_authority", 100)
        candidates.append(replace(profile, authority=Authority.SACRED))
    if pressure:
        shift("religious_authority", -100)
    if cooperation and profile.authority is Authority.COUNCIL:
        shift("integration", -100)
    if _experience(context, actor, {Action.MIGRATION, Action.SEPARATION}):
        candidates.append(replace(profile, authority=Authority.CUSTOMARY))
    return tuple(
        dict.fromkeys(
            value
            for value in candidates
            if value != profile
            and (value.authority is profile.authority or emulated(context, actor, value.authority))
        )
    )


def emulated(context: Context, actor: Actor, authority: Authority) -> tuple[str, ...]:
    """D26: a society adopts the authority that at least half its land neighbours hold.

    Returns those neighbours (the reform's institutional cause), or nothing.
    """
    neighbours = [
        context.index.actors[other]
        for other in sorted(context.land_near.get(actor.key, set()))
        if context.index.actors[other].living
    ]
    holders = tuple(other.key for other in neighbours if other.authority is authority)
    return holders if holders and 2 * len(holders) >= len(neighbours) else ()


def reform_allowed(context: Context, proposal: Proposal) -> Reason | None:
    desired = proposal.reform
    actor = context.index.actors[proposal.actor]
    if (
        desired is None
        or sum(
            getattr(desired, axis.name) != getattr(actor.society, axis.name)
            for axis in fields(Society)
        )
        != 1
    ):
        return Reason.INELIGIBLE
    return None if desired in reforms(context, actor) else Reason.REPEATED_PROBLEM


def reform_cost(context: Context, proposal: Proposal) -> int:
    actor = context.index.actors[proposal.actor]
    return (
        300
        + actor.society.tradition // 2
        + (actor.society.centralization + actor.society.integration) // 10
    )


def reform_event(context: Context, event: Event, proposal: Proposal) -> Event:
    actor = context.index.actors[proposal.actor]
    desired = proposal.reform
    if desired is None:
        return event
    resistance = derive_seed(context.history.seed, "history", "reform", event.key) % PERMILLE
    if resistance < actor.society.tradition // 2:
        return replace(event, outcome=Outcome.FAILED, reason=Reason.RESISTANCE)
    return replace(event, effects=Effects(reforms=(Reform(actor.key, actor.society, desired),)))


def _moved(context: Context, movement: Movement) -> tuple[tuple[Cohort, ...], tuple[Cohort, ...]]:
    pop = movement.cohort
    origin = cohorts(
        (
            *context.index.cohorts(movement.source),
            replace(pop, population=-pop.population, peasants=-pop.peasants),
        )
    )
    destination = cohorts((*context.index.cohorts(movement.destination), pop))
    return origin, destination


def migration_allowed(context: Context, proposal: Proposal) -> Reason | None:  # noqa: PLR0911
    move = proposal.movement
    if move is None:
        return Reason.INELIGIBLE
    index = context.index
    if (
        index.owner.get(move.source) != proposal.actor
        or index.owner.get(move.destination) != proposal.target
        or move.destination not in index.adjacency.get(move.source, {})
    ):
        return Reason.UNREACHABLE
    pop = move.cohort
    source = next(
        (
            each
            for each in index.cohorts(move.source)
            if (each.culture, each.religion) == (pop.culture, pop.religion)
        ),
        None,
    )
    if (
        source is None
        or not (0 < pop.population <= source.population // 10)
        or (pop.peasants != source.peasants * pop.population // source.population)
    ):
        return Reason.INELIGIBLE
    if index.population(move.destination) + pop.population > index.capacities[move.destination]:
        return Reason.CAPACITY
    holding = context.holdings[move.source]
    displaced = (
        context.event_kinds[holding.cause] is Action.CONFLICT
        and context.state.year - context.event_years[holding.cause] <= REFUGE_YEARS
    )
    afraid = proposal.actor in context.afraid
    if not (
        displaced
        or afraid
        or index.population(move.source) * PERMILLE >= index.capacities[move.source] * 900
    ):
        return Reason.PRESSURE
    host = index.actors[proposal.target].society
    matching = any(
        (each.culture, each.religion) == (pop.culture, pop.religion)
        for each in index.cohorts(move.destination)
    )
    if not matching and host.integration < MINORITY_INTEGRATION:
        return Reason.HOSTILE
    # Keep every inhabited holding and both agrarian seats viable after the exact movement.
    origin, destination = _moved(context, move)
    if not _supports_movement(context, proposal, origin, destination):
        return Reason.SUPPORT
    return None


def _supports_movement(
    context: Context,
    proposal: Proposal,
    origin: tuple[Cohort, ...],
    destination: tuple[Cohort, ...],
) -> bool:
    move = proposal.movement
    if move is None:
        return False
    replacement = {move.source: origin, move.destination: destination}
    index, rules = context.index, context.history.geography.rules
    for key in (proposal.actor, proposal.target):
        actor = index.actors[key]
        if actor.tenure is not Tenure.LAND:
            continue
        for members in (index.members[key], {actor.seat}):
            pops = [
                pop for place in members for pop in replacement.get(place, index.cohorts(place))
            ]
            people, farmers = sum(pop.population for pop in pops), sum(pop.peasants for pop in pops)
            if (
                farmers < rules.minimum_peasants
                or farmers * PERMILLE < people * rules.minimum_share
            ):
                return False
    return True


def migration_effects(context: Context, event: Event, proposal: Proposal) -> Effects:
    move = proposal.movement
    if move is None:
        return Effects()
    origin, destination = _moved(context, move)
    return Effects(
        settlements=(
            Settlement(move.source, origin, event.key),
            Settlement(move.destination, destination, event.key),
        ),
        memories=(
            Memory(
                proposal.actor, proposal.target, Factor.DEPENDENCE, event.year, 80, 1, event.key
            ),
            Memory(proposal.target, proposal.actor, Factor.AFFINITY, event.year, 40, 1, event.key),
        ),
    )


def _hostile(context: Context, first: str, second: str) -> bool:
    return (
        max(
            context.score(first, second, Factor.GRIEVANCE),
            context.score(second, first, Factor.GRIEVANCE),
        )
        >= context.history.geography.rules.union_trust
    )


def choices(
    context: Context, actor: Actor, kinds: frozenset[Action] | None = None
) -> list[Proposal]:
    result = (
        [Proposal(Action.REFORM, actor.key, reform=value) for value in reforms(context, actor)]
        if kinds is None or Action.REFORM in kinds
        else []
    )
    if kinds is not None and Action.MIGRATION not in kinds:
        return result
    for source in sorted(context.index.members[actor.key]):
        context.checkpoint()
        holding = context.holdings[source]
        if not (
            actor.key in context.afraid
            or (
                context.event_kinds[holding.cause] is Action.CONFLICT
                and context.state.year - context.event_years[holding.cause] <= REFUGE_YEARS
            )
            or context.index.population(source) * PERMILLE >= context.index.capacities[source] * 900
        ):
            continue
        for destination in sorted(context.index.adjacency[source]):
            target = context.index.owner.get(destination, "")
            if not target or target == actor.key or (actor.key, target) not in context.known:
                continue
            # Eligibility refuses every move between hostile societies.
            if _hostile(context, actor.key, target):
                continue
            space = context.index.capacities[destination] - context.index.population(destination)
            if space <= 0:
                continue
            for pop in context.index.cohorts(source):
                amount = min(pop.population // 10, space)
                if amount:
                    move = Movement(
                        source,
                        destination,
                        replace(
                            pop, population=amount, peasants=pop.peasants * amount // pop.population
                        ),
                    )
                    result.append(Proposal(Action.MIGRATION, actor.key, target, movement=move))
    return result


def propensity(profile: Society, kind: Action, base: int) -> int:
    """Independent orientations favour different actions, with no guaranteed result."""
    value = base
    if kind in {Action.EXCHANGE, Action.CONTACT}:
        value += 70 if profile.exchange is not Exchange.INWARD else -50
    if kind in {Action.CONFLICT, Action.PRESSURE}:
        value += {Military.OFFENSIVE: 100, Military.BALANCED: 0, Military.DEFENSIVE: -50}[
            profile.military
        ]
    if kind in {Action.PROTECTION, Action.PACT}:
        value += 70 if profile.military is Military.DEFENSIVE else 0
    if kind is Action.UNION:
        value += 70 if profile.authority is Authority.COUNCIL else -30
    if kind is Action.ACCESS:
        value += profile.religious_authority // 5 - 100
    if kind is Action.MIGRATION:
        value += 80 if profile.livelihood is Livelihood.MOBILE else -30
    if kind is Action.REFORM:
        value -= profile.tradition // 5
    return max(0, min(PERMILLE, value))
