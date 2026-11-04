"""Seed extraordinary ambitions per hearth; recognize realized historical structures.

The adapter supplies installed technology/density floors. Physical routes replace
the static selector's common sea-zone proxy; no ambition grants land or agreements.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Final

from rnw.history_model import (
    PERMILLE,
    Action,
    Authority,
    Bond,
    Effects,
    Event,
    Exchange,
    Military,
    Outcome,
    Realization,
    Reason,
    Reform,
    Tenure,
    Trajectory,
    TrajectoryKind,
)
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from rnw.history_context import Context
    from rnw.history_model import Hearth, Society

GROUP_MIN: Final[int] = 3
LEAGUE_MAX: Final[int] = 5
CONFEDERATION_MAX: Final[int] = 6
CENTRE_PEERS: Final[int] = 2
REALM_MAX: Final[int] = 4
REALM_RATIO: Final[int] = 3
COMPLEX_CENTRE: Final[int] = 500
REALIZED_AUTHORITY: Final[int] = 650


def _place_faith(context: Context, place: str) -> str:
    totals: dict[str, int] = {}
    for pop in context.index.cohorts(place):
        totals[pop.religion] = totals.get(pop.religion, 0) + pop.population
    return min(totals, key=lambda key: (-totals[key], key))


def _faith(context: Context, actor: str) -> str:
    return _place_faith(context, context.index.actors[actor].seat)


def _population(context: Context, actor: str) -> int:
    return sum(context.index.population(key) for key in context.index.members[actor])


def _agrarian(context: Context, actor: str) -> bool:
    """Landed confederates keep the installed aggregate farming prerequisite."""
    people = _population(context, actor)
    farmers = sum(context.index.peasants(key) for key in context.index.members[actor])
    rules = context.history.geography.rules
    return farmers >= rules.minimum_peasants and (
        farmers * PERMILLE >= people * rules.minimum_share
    )


def _connected(nodes: Iterable[str], adjacent: Callable[[str], set[str]]) -> list[tuple[str, ...]]:
    left = set(nodes)
    groups: list[tuple[str, ...]] = []
    while left:
        start = min(left)
        pending, seen = [start], {start}
        while pending:
            for other in sorted(adjacent(pending.pop()) & left - seen):
                seen.add(other)
                pending.append(other)
        left -= seen
        groups.append(tuple(sorted(seen)))
    return groups


def _ranked(context: Context, nodes: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(nodes, key=lambda key: (-_population(context, key), key)))


def _land_near(context: Context, actor: str) -> set[str]:
    return context.land_near.get(actor, set())


def _bounded(
    context: Context, group: tuple[str, ...], limit: int, adjacent: Callable[[str], set[str]]
) -> tuple[str, ...]:
    chosen = {_ranked(context, group)[0]}
    while len(chosen) < min(limit, len(group)):
        frontier = {
            other
            for key in chosen
            for other in adjacent(key)
            if other in group and other not in chosen
        }
        chosen.add(_ranked(context, frontier)[0])
    return _ranked(context, chosen)


def _eligible(context: Context, hearth: Hearth) -> tuple[str, ...]:
    return tuple(
        actor.key
        for actor in context.state.actors
        if actor.living and actor.seat in hearth.domain and actor.key not in context.bound
    )


def _options(context: Context, hearth: Hearth) -> tuple[Trajectory, ...]:
    actors = _eligible(context, hearth)
    landed = {key for key in actors if context.index.actors[key].tenure is Tenure.LAND}
    rules = context.history.geography.rules
    result: list[Trajectory] = []

    def add(kind: TrajectoryKind, members: Iterable[str]) -> None:
        ranked = _ranked(context, members)
        result.append(
            Trajectory(kind, hearth.key, context.index.actors[ranked[0]].seat, ranked, "")
        )

    for group in _connected(landed, lambda key: set(context.near.get(key, {}))):
        if sum(len(context.index.members[key]) for key in group) >= rules.empire_locations:
            for key in group:
                if (
                    context.index.places[context.index.actors[key].seat].complexity
                    >= COMPLEX_CENTRE
                ):
                    add(TrajectoryKind.GREAT_EMPIRE, (key,))
    coastal = {
        key
        for key in landed
        if context.index.actors[key].technology >= rules.league_technology
        and any(context.index.places[place].coastal for place in context.index.members[key])
    }
    for group in _connected(coastal, lambda key: set(context.near.get(key, {}))):
        ranked = _bounded(context, group, LEAGUE_MAX, lambda key: set(context.near.get(key, {})))
        if (
            len(ranked) >= GROUP_MIN
            and any(
                second not in _land_near(context, first)
                for first in ranked
                for second in ranked
                if first != second
            )
            and any(context.sea_near.get(key, set()) & set(ranked) for key in ranked)
        ):
            add(TrajectoryKind.SEA_LEAGUE, ranked)
    tribes = {
        key
        for key in actors
        if context.index.actors[key].tenure is Tenure.TRIBE
        and _agrarian(context, key)
        and sum(context.index.places[place].highland for place in context.index.members[key])
        * PERMILLE
        >= len(context.index.members[key]) * 600
    }
    for group in _connected(
        tribes,
        lambda key: {
            other
            for other in _land_near(context, key)
            if _faith(context, other) == _faith(context, key)
        },
    ):
        ranked = _bounded(
            context,
            group,
            CONFEDERATION_MAX,
            lambda key: {
                other
                for other in _land_near(context, key)
                if _faith(context, other) == _faith(context, key)
            },
        )
        if len(ranked) >= GROUP_MIN and sum(_population(context, key) for key in ranked) >= (
            rules.confederation_density * sum(len(context.index.members[key]) for key in ranked)
        ):
            add(TrajectoryKind.HIGHLAND_CONFEDERATION, ranked)
    result.extend(_sacred_options(context, hearth, landed))
    return tuple(sorted(result, key=lambda item: (item.kind, item.anchor, item.members)))


def _sacred_options(context: Context, hearth: Hearth, landed: set[str]) -> list[Trajectory]:
    result: list[Trajectory] = []
    population = sorted(
        _population(context, actor.key)
        for actor in context.state.actors
        if actor.living and actor.tenure is Tenure.LAND and actor.key not in context.bound
    )
    threshold = population[len(population) * 3 // 4] if population else 0
    for key in sorted(landed):
        context.checkpoint()
        sacred = [
            place for place in context.index.members[key] if context.index.places[place].sacred
        ]
        if not sacred:
            continue
        peers = {
            other
            for other in _land_near(context, key) & landed
            if _faith(context, other) == _faith(context, key)
        }
        # The place is the most populous actual centre of its faith, not a randomly assigned shrine.
        zone = [
            place
            for place in context.index.places
            if place in context.index.owner and _place_faith(context, place) == _faith(context, key)
        ]
        centre = min(zone, key=lambda place: (-context.index.population(place), place))
        if (
            sacred
            and centre in sacred
            and _population(context, key) >= threshold
            and len(peers) >= CENTRE_PEERS
        ):
            members = (key, *_ranked(context, peers)[:3])
            result.append(Trajectory(TrajectoryKind.SACRED_CENTRE, hearth.key, centre, members, ""))
    return result


def _inclined(profile: Society, kind: TrajectoryKind) -> Society:
    if kind is TrajectoryKind.GREAT_EMPIRE:
        return replace(
            profile,
            centralization=max(900, profile.centralization),
            integration=max(900, profile.integration),
            authority=Authority.RULER,
            military=Military.OFFENSIVE,
        )
    if kind is TrajectoryKind.SEA_LEAGUE:
        return replace(
            profile,
            authority=Authority.COUNCIL,
            exchange=Exchange.COASTAL,
            military=Military.DEFENSIVE,
        )
    if kind is TrajectoryKind.HIGHLAND_CONFEDERATION:
        return replace(profile, authority=Authority.CUSTOMARY, military=Military.DEFENSIVE)
    return replace(
        profile,
        authority=Authority.SACRED,
        religious_authority=max(800, profile.religious_authority),
    )


def seed_events(context: Context, chance: int) -> list[Event]:
    events: list[Event] = []
    # One named stream per hearth keeps chance monotone even when another domain is ineligible.
    profiles = {actor.key: actor.society for actor in context.state.actors}
    prior_changes: dict[str, str] = {}
    for hearth in context.history.geography.hearths:
        context.checkpoint()
        draw = derive_seed(context.history.seed, "history", "trajectory", hearth.key, "chance")
        if draw % PERMILLE >= chance:
            continue
        options = _options(context, hearth)
        kinds = sorted({option.kind for option in options})
        if not kinds:
            continue
        kind = kinds[derive_seed(draw, "kind") % len(kinds)]
        pool = [option for option in options if option.kind is kind]
        chosen = (
            min(pool, key=lambda option: (-context.power(option.members[0]), option.anchor))
            if kind is TrajectoryKind.GREAT_EMPIRE
            else pool[derive_seed(draw, "option") % len(pool)]
        )
        key = f"ambition_{derive_seed(draw, str(kind), chosen.anchor):016x}"
        reforms: list[Reform] = []
        causes = {context.index.actors[member].origin for member in chosen.members}
        for member in chosen.members:
            # Rivals of a sacred centre get no sacred authority from living next door.
            if (
                kind is TrajectoryKind.SACRED_CENTRE
                and context.index.owner[chosen.anchor] != member
            ):
                continue
            if member in prior_changes:
                causes.add(prior_changes[member])
            after = _inclined(profiles[member], kind)
            reforms.append(Reform(member, profiles[member], after))
            profiles[member] = after
            prior_changes[member] = key
        events.append(
            Event(
                key,
                context.state.year,
                Action.TRAJECTORY,
                tuple(sorted(chosen.members)),
                tuple(sorted(causes)),
                Outcome.ACCEPTED,
                Reason.AMBITION,
                Effects(reforms=tuple(reforms), trajectories=(replace(chosen, cause=key),)),
            )
        )
    return events


def _descends(context: Context, actor: str, ancestors: set[str]) -> bool:
    pending, seen = [actor], set[str]()
    while pending:
        key = pending.pop()
        if key in ancestors:
            return True
        if key not in seen:
            seen.add(key)
            pending.extend(context.index.actors[key].parents)
    return False


def _network(nodes: set[str], bonds: list[Bond]) -> bool:
    return (
        len(
            _connected(
                nodes,
                lambda key: {
                    bond.second if bond.first == key else bond.first
                    for bond in bonds
                    if key in (bond.first, bond.second)
                },
            )
        )
        == 1
    )


def _realized_group(
    context: Context, trajectory: Trajectory, owner: str
) -> tuple[tuple[str, ...], list[Bond]]:
    hearth = next(
        each for each in context.history.geography.hearths if each.key == trajectory.hearth
    )
    for option in _options(context, hearth):
        if option.kind is not trajectory.kind or owner not in option.members:
            continue
        nodes = set(option.members)
        pacts = [
            bond
            for bond in context.state.bonds
            if bond.kind is Action.PACT and {bond.first, bond.second} <= nodes
        ]
        if not _network(nodes, pacts):
            continue
        exchanges = [
            bond
            for bond in context.state.bonds
            if bond.kind is Action.EXCHANGE and {bond.first, bond.second} <= nodes
        ]
        if trajectory.kind is TrajectoryKind.SEA_LEAGUE and (
            any(context.index.actors[key].authority is not Authority.COUNCIL for key in nodes)
            or not _network(nodes, exchanges)
        ):
            continue
        return option.members, [*pacts, *exchanges]
    return (), []


def _realized(context: Context, trajectory: Trajectory) -> tuple[tuple[str, ...], list[Bond]]:
    owner = context.index.owner[trajectory.anchor]
    if not _descends(context, owner, set(trajectory.members)):
        return (), []
    actor = context.index.actors[owner]
    if trajectory.kind is TrajectoryKind.GREAT_EMPIRE:
        if (
            actor.tenure is Tenure.LAND
            and actor.society.centralization >= REALIZED_AUTHORITY
            and len(context.index.members[owner])
            >= context.history.geography.rules.empire_locations
            and context.burden(owner) <= PERMILLE
        ):
            return (owner,), []
    elif trajectory.kind in {TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION}:
        return _realized_group(context, trajectory, owner)
    elif trajectory.kind is TrajectoryKind.SACRED_CENTRE:
        hearth = next(
            each for each in context.history.geography.hearths if each.key == trajectory.hearth
        )
        if not any(
            option.kind is TrajectoryKind.SACRED_CENTRE
            and option.anchor == trajectory.anchor
            and owner in option.members
            for option in _options(context, hearth)
        ):
            return (), []
        accesses = [
            bond
            for bond in context.state.bonds
            if bond.kind is Action.ACCESS
            and bond.second == owner
            and bond.place == trajectory.anchor
        ]
        if (
            actor.authority is Authority.SACRED
            and actor.society.religious_authority >= REALIZED_AUTHORITY
            and len({bond.first for bond in accesses}) >= CENTRE_PEERS
        ):
            return (owner, *_ranked(context, {bond.first for bond in accesses})), accesses
    return (), []


def _fractured(context: Context, event: Event) -> tuple[str, ...]:
    successors = tuple(
        actor.key for actor in event.effects.created if context.index.actors[actor.key].living
    )
    if not GROUP_MIN <= len(successors) <= REALM_MAX:
        return ()
    if any(
        key in context.bound
        or context.index.actors[key].tenure is not Tenure.LAND
        or context.index.places[context.index.actors[key].seat].complexity < COMPLEX_CENTRE
        for key in successors
    ):
        return ()
    if len({_faith(context, key) for key in successors}) != 1:
        return ()
    populations = [_population(context, key) for key in successors]
    if max(populations) > min(populations) * REALM_RATIO:
        return ()
    if (
        sum(len(context.index.members[key]) for key in successors)
        < context.history.geography.rules.empire_locations
    ):
        return ()
    return (
        successors if len(_connected(successors, lambda key: _land_near(context, key))) == 1 else ()
    )


def realizations(context: Context) -> tuple[Realization, ...]:
    """Recognize facts in the current snapshot; never construct a desired outcome."""
    found: list[Realization] = []
    for trajectory in context.state.trajectories:
        context.checkpoint()
        members, bonds = _realized(context, trajectory)
        if members:
            causes = {trajectory.cause, *(bond.cause for bond in bonds)}
            causes.update(context.index.actors[key].society_cause for key in members)
            causes.update(
                context.holdings[place].cause
                for key in members
                for place in context.index.members[key]
            )
            found.append(
                Realization(trajectory.kind, members, tuple(sorted(causes)), trajectory.hearth)
            )
    for event in context.history.events:
        if event.kind is not Action.SEPARATION or event.outcome is not Outcome.ACCEPTED:
            continue
        parent = context.index.actors[event.actors[0]]
        # Separation is already restricted to a real union in the transition rules.
        successors = _fractured(context, event)
        if successors and parent.parents:
            causes = {event.key, *(context.index.actors[key].society_cause for key in successors)}
            causes.update(
                context.holdings[place].cause
                for key in successors
                for place in context.index.members[key]
            )
            found.append(
                Realization(TrajectoryKind.FRACTURED_REALM, successors, tuple(sorted(causes)))
            )
    return tuple(sorted(found, key=lambda item: (item.kind, item.hearth, item.members)))


def report(context: Context) -> dict[str, dict[str, int]]:
    realized = realizations(context)
    return {
        kind: {
            "seeded": sum(item.kind is kind for item in context.state.trajectories),
            "realized": sum(item.kind is kind for item in realized),
        }
        for kind in TrajectoryKind
    }
