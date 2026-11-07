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
    Strategy,
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
# D22: a political region holds at least this many 1037 landed polities.
POLITICAL_REGION: Final[int] = 8
# Design weights (permille) of the ordinary regional settings at Calm, Varied and
# Turbulent; turbulence interpolates linearly between them. Not fitted values.
SETTINGS: Final[dict[str, tuple[int, int, int]]] = {
    "patchwork": (300, 400, 500),
    "rival_powers": (300, 350, 350),
    "paramount": (400, 250, 150),
}
# D23: the share of prudent expansion aims at Calm, Varied and Turbulent.
PRUDENT: Final[tuple[int, int, int]] = (800, 450, 300)
RIVAL_SPACING: Final[int] = 3
FRONTIER: Final[int] = 2
LARGE_REGION: Final[int] = 16
# Rival regional powers seeded in a region below and at or above LARGE_REGION polities.
RIVAL_COUNT: Final[tuple[int, int]] = (2, 3)
# D24 recognition: a region's share of state locations; a regional power's multiple
# of the region's median state (in halves: 4 = 2x); a paramount's multiple of the
# next bloc; a great realm's bloc holds at least
# GREAT_SHARE permille of all land locations, the share of the largest vanilla
# 1337 American state (C117).
REGIONAL_SHARE: Final[int] = 80
PARAMOUNT_SHARE: Final[int] = 300
LEAD_HALVES: Final[int] = 4
PARAMOUNT_LEAD: Final[int] = 2
GREAT_SHARE: Final[int] = 5


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
    if kind is TrajectoryKind.REGIONAL_POWER:
        return replace(
            profile,
            centralization=max(750, profile.centralization),
            integration=max(700, profile.integration),
            military=Military.OFFENSIVE,
        )
    if kind is TrajectoryKind.PARAMOUNT:
        return replace(
            profile,
            centralization=max(800, profile.centralization),
            integration=max(800, profile.integration),
            authority=Authority.RULER,
            military=Military.OFFENSIVE,
        )
    if kind is TrajectoryKind.GREAT_EMPIRE:
        return replace(
            profile,
            centralization=max(850, profile.centralization),
            integration=max(850, profile.integration),
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


def interpolate(values: tuple[int, int, int], turbulence: int) -> int:
    """A design value at Calm (200), Varied (500) and Turbulent (800), linear between."""
    calm, varied, turbulent = values
    if turbulence <= 200:  # noqa: PLR2004 - the Calm quick choice
        return calm
    if turbulence <= 500:  # noqa: PLR2004 - the Varied quick choice
        return calm + (varied - calm) * (turbulence - 200) // 300
    if turbulence <= 800:  # noqa: PLR2004 - the Turbulent quick choice
        return varied + (turbulent - varied) * (turbulence - 500) // 300
    return turbulent


def _strategy(draw: int, anchor: str, turbulence: int) -> Strategy:
    prudent = derive_seed(draw, "strategy", anchor) % PERMILLE < interpolate(PRUDENT, turbulence)
    return Strategy.PRUDENT if prudent else Strategy.OVERREACHING


def seed_events(context: Context, chance: int, turbulence: int = 500) -> list[Event]:
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
        if kind is TrajectoryKind.GREAT_EMPIRE:
            chosen = replace(chosen, strategy=_strategy(draw, chosen.anchor, turbulence))
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
    events.extend(_regional_events(context, events, profiles, prior_changes, turbulence))
    return events


def political_regions(context: Context) -> dict[str, tuple[str, ...]]:
    """Generated regions holding at least eight 1037 landed polities, with those polities."""
    found: dict[str, list[str]] = {}
    for founding in context.history.foundings:
        if founding.tenure is Tenure.LAND:
            region = context.index.places[founding.seat].region
            found.setdefault(region, []).append(founding.key)
    return {
        region: tuple(sorted(keys))
        for region, keys in sorted(found.items())
        if len(keys) >= POLITICAL_REGION
    }


def _land(context: Context) -> dict[str, set[str]]:
    land: dict[str, set[str]] = {}
    for route in context.history.geography.routes:
        if not route.sea_steps:
            land.setdefault(route.first, set()).add(route.second)
            land.setdefault(route.second, set()).add(route.first)
    return land


def _land_steps(land: dict[str, set[str]], seats: set[str], limit: int) -> set[str]:
    """Districts fewer than ``limit`` land steps from any of ``seats``."""
    near, frontier = set(seats), set(seats)
    for _ in range(limit - 1):
        frontier = {other for key in frontier for other in land.get(key, set())} - near
        near |= frontier
    return near


def _centres(
    context: Context,
    land: dict[str, set[str]],
    envelope: frozenset[str],
    polities: tuple[str, ...],
    candidates: list[str],
) -> tuple[set[str], list[str]]:
    """Centres with physically reachable room for a regional or paramount aim."""
    parts = [
        frozenset(group)
        for group in _connected(envelope, lambda key: land.get(key, set()) & envelope)
    ]
    components = {place: group for group in parts for place in group}
    sizes = sorted(len(context.index.members[key]) for key in polities)
    median = sizes[(len(sizes) - 1) // 2]
    # An isolated centre cannot act on the rest of a region. Give each aim
    # enough reachable state land for its recognition share and scale; this
    # grants neither the land nor a successful contest (D6, D22-D24).
    regional = {
        key
        for key in candidates
        if len(components[context.index.actors[key].seat]) * PERMILLE
        >= len(envelope) * REGIONAL_SHARE
        and 2 * len(components[context.index.actors[key].seat]) >= LEAD_HALVES * median
    }
    paramounts = [
        key
        for key in candidates
        if len(components[context.index.actors[key].seat]) * PERMILLE
        >= len(envelope) * PARAMOUNT_SHARE
        and len(components[context.index.actors[key].seat])
        >= PARAMOUNT_LEAD
        * max(
            (
                len(held & (envelope - components[context.index.actors[key].seat]))
                for other, held in context.index.members.items()
                if other != key and context.index.actors[other].tenure is Tenure.LAND
            ),
            default=0,
        )
    ]
    return regional, paramounts


def _regional_events(
    context: Context,
    extraordinary: list[Event],
    profiles: dict[str, Society],
    prior_changes: dict[str, str],
    turbulence: int,
) -> list[Event]:
    """D22: one feasible ordinary setting per political region without an extraordinary aim."""
    covered = {
        context.index.places[context.index.actors[member].seat].region
        for event in extraordinary
        for item in event.effects.trajectories
        for member in item.members
    }
    taken = {
        member
        for event in extraordinary
        for item in event.effects.trajectories
        for member in item.members
    }
    land = _land(context)
    events: list[Event] = []
    for region, polities in political_regions(context).items():
        context.checkpoint()
        if region in covered:
            continue
        # An aim needs room to act: a land border with at least two landed polities.
        candidates = sorted(
            (
                key
                for key in polities
                if key not in taken
                and sum(
                    context.index.actors[other].tenure is Tenure.LAND
                    for other in context.land_near.get(key, set())
                )
                >= FRONTIER
            ),
            key=lambda key: (-context.power(key), key),
        )
        envelope = region_districts(context, region)
        regional, paramounts = _centres(context, land, envelope, polities, candidates)
        rivals: list[str] = []
        blocked: set[str] = set()
        count = RIVAL_COUNT[len(polities) >= LARGE_REGION]
        for key in candidates:
            if key not in regional:
                continue
            seat = context.index.actors[key].seat
            if seat in blocked:
                continue
            rivals.append(key)
            if len(rivals) == count:
                break
            blocked = _land_steps(
                land, {context.index.actors[k].seat for k in rivals}, RIVAL_SPACING
            )
        feasible = {
            "patchwork": True,
            "rival_powers": len(rivals) >= 2,  # noqa: PLR2004 - rivals come in pairs or more
            "paramount": bool(paramounts),
        }
        weights = {
            name: interpolate(values, turbulence) if feasible[name] else 0
            for name, values in SETTINGS.items()
        }
        draw = derive_seed(context.history.seed, "history", "setting", region)
        point = draw % sum(weights.values())
        setting = "patchwork"
        for name, weight in weights.items():
            if point < weight:
                setting = name
                break
            point -= weight
        if setting == "patchwork":
            continue
        kind = TrajectoryKind.PARAMOUNT if setting == "paramount" else TrajectoryKind.REGIONAL_POWER
        chosen = paramounts[:1] if setting == "paramount" else rivals
        for member in chosen:
            anchor = context.index.actors[member].seat
            key = f"aim_{derive_seed(draw, str(kind), anchor):016x}"
            before = profiles[member]
            after = _inclined(before, kind)
            causes = {context.index.actors[member].origin}
            if member in prior_changes:
                causes.add(prior_changes[member])
            profiles[member] = after
            prior_changes[member] = key
            taken.add(member)
            item = Trajectory(
                kind,
                "",
                anchor,
                (member,),
                key,
                _strategy(draw, anchor, turbulence),
                region,
            )
            events.append(
                Event(
                    key,
                    context.state.year,
                    Action.TRAJECTORY,
                    (member,),
                    tuple(sorted(causes)),
                    Outcome.ACCEPTED,
                    Reason.AMBITION,
                    Effects(reforms=(Reform(member, before, after),), trajectories=(item,)),
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
    """The largest pact network of a seeded group's living descendants that holds its anchor.

    Recognition reads the recorded facts about the seeded members' successors; the
    eligibility predicates that chose the members at 1037 do not apply again.
    """
    league = trajectory.kind is TrajectoryKind.SEA_LEAGUE
    tenure = Tenure.LAND if league else Tenure.TRIBE
    nodes = {
        key
        for key, items in context.groups.items()
        if trajectory in items
        and key not in context.subjects
        and context.index.actors[key].tenure is tenure
        and (
            context.index.actors[key].authority is Authority.COUNCIL
            if league
            else _agrarian(context, key)
        )
    }
    if owner not in nodes:
        return (), []
    pacts = [
        bond
        for bond in context.state.bonds
        if bond.kind is Action.PACT and {bond.first, bond.second} <= nodes
    ]
    exchanges = [
        bond
        for bond in context.state.bonds
        if bond.kind is Action.EXCHANGE and {bond.first, bond.second} <= nodes
    ]
    for component in sorted(
        _connected(
            nodes,
            lambda key: {
                bond.second if bond.first == key else bond.first
                for bond in pacts
                if key in (bond.first, bond.second)
            },
        ),
        key=lambda found: (-len(found), found),
    ):
        members = set(component)
        if owner not in members or len(members) < GROUP_MIN:
            continue
        if league and not _network(
            members, [bond for bond in exchanges if {bond.first, bond.second} <= members]
        ):
            continue
        # Landed confederates keep the installed density prerequisite of 1037's selection.
        if not league and sum(_population(context, key) for key in members) < (
            context.history.geography.rules.confederation_density
            * sum(len(context.index.members[key]) for key in members)
        ):
            continue
        return _ranked(context, members), [
            bond for bond in (*pacts, *exchanges) if {bond.first, bond.second} <= members
        ]
    return (), []


def blocs(context: Context) -> dict[str, frozenset[str]]:
    """Each independent landed actor's realm: its own and its subjects' state locations."""
    return {
        actor.key: frozenset(
            place for member in context.realm(actor.key) for place in context.index.members[member]
        )
        for actor in context.state.actors
        if actor.living and actor.tenure is Tenure.LAND and actor.key not in context.subjects
    }


def region_districts(context: Context, region: str) -> frozenset[str]:
    """The fixed state-location envelope of one generated region."""
    return frozenset(
        place.key
        for place in context.history.geography.districts
        if place.region == region and place.tenure is Tenure.LAND
    )


def _regional(context: Context, trajectory: Trajectory, owner: str) -> bool:
    if owner in context.subjects:
        return False
    envelope = region_districts(context, trajectory.region)
    shares = {key: len(held & envelope) for key, held in blocs(context).items()}
    own = shares.get(owner, 0)
    if trajectory.kind is TrajectoryKind.PARAMOUNT:
        others = max((value for key, value in shares.items() if key != owner), default=0)
        return own * PERMILLE >= len(envelope) * PARAMOUNT_SHARE and own >= PARAMOUNT_LEAD * others
    sizes = sorted(
        len(context.index.members[actor.key])
        for actor in context.state.actors
        if actor.living
        and actor.tenure is Tenure.LAND
        and context.index.places[actor.seat].region == trajectory.region
    )
    median = sizes[(len(sizes) - 1) // 2] if sizes else 0
    return own * PERMILLE >= len(envelope) * REGIONAL_SHARE and 2 * own >= LEAD_HALVES * median


def _realized(  # noqa: PLR0911 - one recognition rule per kind
    context: Context, trajectory: Trajectory
) -> tuple[tuple[str, ...], list[Bond]]:
    owner = context.index.owner[trajectory.anchor]
    if not _descends(context, owner, set(trajectory.members)):
        return (), []
    actor = context.index.actors[owner]
    if trajectory.kind in {TrajectoryKind.REGIONAL_POWER, TrajectoryKind.PARAMOUNT}:
        return (
            ((owner,), [])
            if actor.tenure is Tenure.LAND and _regional(context, trajectory, owner)
            else ((), [])
        )
    if trajectory.kind is TrajectoryKind.GREAT_EMPIRE:
        held = blocs(context).get(owner, frozenset())
        if (
            actor.tenure is Tenure.LAND
            and actor.society.centralization >= REALIZED_AUTHORITY
            and len(context.index.members[owner])
            >= context.history.geography.rules.empire_locations
            and len(held) * PERMILLE >= len(context.history.geography.districts) * GREAT_SHARE
        ):
            return (owner,), []
    elif trajectory.kind in {TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION}:
        return _realized_group(context, trajectory, owner)
    elif trajectory.kind is TrajectoryKind.SACRED_CENTRE:
        if actor.tenure is not Tenure.LAND or not context.index.places[trajectory.anchor].sacred:
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
