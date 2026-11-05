"""Synchronous deterministic history rounds, sparse effects and exact causal replay.

The normal H4 exporter projects this private model; presentation never supplies facts.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import fields, is_dataclass, replace
from typing import TYPE_CHECKING, Final, cast

from rnw.history_actions import (
    PRIORITY,
    adjudicate,
    breakaway_seat,
    eligible,
    inherit_round,
    proposal_key,
)
from rnw.history_checks import (
    Index,
    alive_at,
    require,
    unique,
    validate_geography,
    validate_snapshot,
)
from rnw.history_context import MUTUAL, Context
from rnw.history_model import (
    END,
    MAX_PROPOSALS,
    PERMILLE,
    START,
    YEARS,
    Action,
    Actor,
    Authority,
    Effects,
    Event,
    Factor,
    Founding,
    Geography,
    History,
    Holding,
    Military,
    Outcome,
    Partition,
    Proposal,
    Reason,
    Settlement,
    Snapshot,
    Society,
    Tenure,
    Trajectory,
    TrajectoryKind,
    Transfer,
)
from rnw.history_societies import bootstrap, choices, cohorts, propensity
from rnw.history_trajectories import seed_events
from rnw.rng import check_seed, derive_seed

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# Policy biases of seeded aims (D22-D23). They change which eligible proposals an
# actor makes and how persistently, never eligibility, arbitration or outcomes.
CONTESTS: Final[frozenset[Action]] = frozenset({Action.CONFLICT, Action.PRESSURE})
# A regional power's contest propensity: 450 at Calm, 600 at Varied, 750 at Turbulent.
AIM_CONFLICT: Final[int] = 350
HEGEMONY_CONFLICT: Final[int] = 700
# Beyond Varied, each further point of turbulence adds this many thousandths to the
# ordinary contest propensity (the turbulence control's visible upper range).
ESCALATION: Final[int] = 1200
FEAR_RESPONSE: Final[int] = 450
GROUP_BOND: Final[int] = 500
GROUP_EXCHANGE: Final[int] = 400
SACRED_VISIT: Final[int] = 600


def _checkpoint() -> None:
    """Default callback; the generator can supply its existing cancellation checkpoint."""


def _canonical(proposal: Proposal) -> Proposal:
    return replace(
        proposal,
        districts=tuple(sorted(proposal.districts)),
        partitions=tuple(
            replace(part, districts=tuple(sorted(part.districts)))
            for part in sorted(proposal.partitions, key=lambda part: part.seat)
        ),
    )


def _apply(state: Snapshot, events: Sequence[Event]) -> Snapshot:
    """Construct one atomic round result; copy each fact table once, not once per event."""
    actors = {actor.key: actor for actor in state.actors}
    holdings = {holding.district: holding for holding in state.holdings}
    bonds = {(bond.kind, bond.first, bond.second, bond.place): bond for bond in state.bonds}
    knowledge = {(known.first, known.second): known for known in state.knowledge}
    memories = list(state.memories)
    settlements = {place.district: place for place in state.settlements}
    trajectories = list(state.trajectories)
    for event in events:
        effects = event.effects
        for actor in effects.created:
            require(actor.key not in actors, "Actor ID collision")
            actors[actor.key] = actor
        for key in effects.retired:
            require(key in actors and actors[key].living, "Cannot retire an absent/extinct actor")
            actors[key] = replace(actors[key], ended=event.year, end_cause=event.key)
        for transfer in effects.transfers:
            previous = holdings.get(transfer.district)
            require(
                (previous.actor if previous else "") == transfer.before,
                "Territory was reserved more than once or the prior owner is wrong",
            )
            require(transfer.after in actors, "Transfer has no receiving actor")
            holdings[transfer.district] = Holding(transfer.district, transfer.after, event.key)
        for reform in effects.reforms:
            require(
                actors[reform.actor].society == reform.before, "Profile was changed more than once"
            )
            actors[reform.actor] = replace(
                actors[reform.actor], society=reform.after, society_cause=event.key
            )
        for settlement in effects.settlements:
            settlements[settlement.district] = settlement
        trajectories.extend(effects.trajectories)
        if effects.retired:
            retired = set(effects.retired)
            bonds = {
                key: bond
                for key, bond in bonds.items()
                if bond.first not in retired and bond.second not in retired
            }
            knowledge = {
                key: known
                for key, known in knowledge.items()
                if known.first not in retired and known.second not in retired
            }
        for bond in effects.ended:
            key = (bond.kind, bond.first, bond.second, bond.place)
            require(bonds.get(key) == bond, "Cannot end an absent bond")
            del bonds[key]
        for bond in effects.bonds:
            bonds[bond.kind, bond.first, bond.second, bond.place] = bond
        for known in effects.knowledge:
            _ = knowledge.setdefault((known.first, known.second), known)
        memories.extend(effects.memories)
    return Snapshot(
        state.year,
        tuple(actors[key] for key in sorted(actors)),
        tuple(holdings[key] for key in sorted(holdings)),
        tuple(bonds[key] for key in sorted(bonds)),
        tuple(knowledge[key] for key in sorted(knowledge)),
        tuple(memories),
        tuple(settlements[key] for key in sorted(settlements)),
        tuple(trajectories),
    )


def create(  # noqa: PLR0913 - the causal roots and both seeded controls
    geography: Geography,
    foundings: Sequence[Founding],
    *,
    seed: int,
    empire_permille: int = 250,
    turbulence: int = 500,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Create causal roots for every supplied actor; no country or population is invented."""
    validate_geography(geography)
    _ = check_seed(seed)
    require(0 <= empire_permille <= PERMILLE, "Invalid extraordinary trajectory chance")
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    unique((founding.key for founding in foundings), "founding")
    geography = replace(
        geography,
        districts=tuple(
            sorted(
                (
                    replace(
                        place,
                        cohorts=cohorts(place.cohorts),
                    )
                    for place in geography.districts
                ),
                key=lambda place: place.key,
            )
        ),
        routes=tuple(
            sorted(
                (
                    replace(
                        route,
                        first=min(route.first, route.second),
                        second=max(route.first, route.second),
                    )
                    for route in geography.routes
                ),
                key=lambda route: (route.first, route.second),
            )
        ),
        hearths=tuple(
            replace(hearth, domain=tuple(sorted(hearth.domain)))
            for hearth in sorted(geography.hearths, key=lambda hearth: hearth.key)
        ),
    )
    canonical = tuple(
        replace(founding, districts=tuple(sorted(founding.districts)))
        for founding in sorted(foundings, key=lambda founding: founding.key)
    )
    state = Snapshot(START)
    events: list[Event] = []
    places = {place.key: place for place in geography.districts}
    for founding in canonical:
        checkpoint()
        unique(founding.districts, "founding district")
        require(set(founding.districts) <= places.keys(), "Unknown founding district")
        require(
            founding.society is None or founding.society.authority is founding.authority,
            "Founding authority differs from its society profile",
        )
        key = f"origin_{derive_seed(seed, 'history', 'origin', founding.key):016x}"
        actor = Actor(
            founding.key,
            founding.tenure,
            founding.seat,
            bootstrap(founding, places, seed),
            founding.technology,
            START,
            key,
            founding.districts,
            society_cause=key,
        )
        event = Event(
            key,
            START,
            Action.FOUNDATION,
            (founding.key,),
            (),
            Outcome.ACCEPTED,
            Reason.ORIGIN,
            Effects(
                created=(actor,),
                transfers=tuple(Transfer(place, "", founding.key) for place in founding.districts),
                settlements=tuple(
                    Settlement(place, places[place].cohorts, key) for place in founding.districts
                ),
            ),
        )
        events.append(event)
    state = _apply(state, events)
    validate_snapshot(Index(geography, state, checkpoint), state)
    history = History(
        geography,
        seed,
        canonical,
        state,
        tuple(events),
        empire_permille=empire_permille,
        turbulence=turbulence,
    )
    ambitions = seed_events(Context(history, checkpoint), empire_permille, turbulence)
    state = _apply(state, ambitions)
    validate_snapshot(Index(geography, state, checkpoint), state)
    return replace(history, state=state, events=(*events, *ambitions))


def _validate_proposals(context: Context, proposals: Sequence[Proposal]) -> tuple[Proposal, ...]:
    require(
        all(proposal.kind not in {Action.FOUNDATION, Action.TRAJECTORY} for proposal in proposals),
        "No late founding/trajectory",
    )
    require(
        all(
            count <= MAX_PROPOSALS
            for count in Counter(proposal.actor for proposal in proposals).values()
        ),
        "An actor may rank at most three proposals",
    )
    canonical = tuple(_canonical(proposal) for proposal in proposals)
    unique((proposal_key(proposal) for proposal in canonical), "proposal")
    living = {actor.key for actor in context.state.actors if actor.living}
    for proposal in canonical:
        participants = {key for key in (proposal.actor, proposal.target, proposal.threat) if key}
        require(
            participants <= living
            and proposal.actor in living
            and 0 <= proposal.rank < MAX_PROPOSALS
            and (not proposal.target or proposal.target != proposal.actor),
            "Proposal names an absent/extinct actor or invalid rank",
        )
        require(
            (proposal.kind in {Action.SEPARATION, Action.SECESSION, Action.REFORM})
            == (not proposal.target),
            "Only separation/secession/reform has no partner",
        )
        require(
            set(proposal.districts) <= context.index.places.keys()
            and all(
                set(part.districts) <= context.index.places.keys() for part in proposal.partitions
            ),
            "Proposal names an unknown district",
        )
        require(
            len(set(proposal.districts)) == len(proposal.districts), "Duplicate proposed territory"
        )
        require(
            (proposal.kind is Action.REFORM) == (proposal.reform is not None)
            and (proposal.kind is Action.MIGRATION) == (proposal.movement is not None),
            "Action payload differs from its family",
        )
        if proposal.movement is not None:
            require(
                {proposal.movement.source, proposal.movement.destination}
                <= context.index.owner.keys(),
                "Migration names an uninhabited/unknown district",
            )
    return tuple(sorted(canonical, key=proposal_key))


def advance(
    history: History,
    proposals: Sequence[Proposal],
    *,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Evaluate on the same prior state, reserve commitments, then commit one whole round."""
    return _advance(Context(history, checkpoint), proposals)


def _advance(context: Context, proposals: Sequence[Proposal]) -> History:  # noqa: C901, PLR0915 - one atomic arbitration
    history, checkpoint = context.history, context.checkpoint
    require(history.state.year < END, "History already reached 1337")
    checkpoint()
    proposals = _validate_proposals(context, proposals)

    def order(proposal: Proposal) -> tuple[int, int, int, str]:
        key = proposal_key(proposal)
        draw = derive_seed(history.seed, "history", "arbitration", str(history.state.year), key)
        return PRIORITY[proposal.kind], proposal.rank, draw, key

    remaining = {actor.key: PERMILLE for actor in history.state.actors if actor.living}
    reserved: set[tuple[Action, str, str, tuple[str, ...]]] = set()
    events: list[Event] = []
    retired: set[str] = set()
    subjects = set(context.subjects)
    moved: set[str] = set()
    ownership: set[str] = set()
    contested: set[str] = set()
    restructured: set[str] = set()
    reformed: set[str] = set()
    administrations: dict[str, str] = {}
    for proposal in sorted(proposals, key=order):
        checkpoint()
        event, costs = adjudicate(context, proposal, remaining)
        first, second = proposal.actor, proposal.target
        if proposal.kind in MUTUAL:
            first, second = sorted((first, second))
        reservation = (proposal.kind, first, second, proposal.districts)
        participants = {proposal.actor, proposal.target} - {""}
        incompatible = (
            (proposal.kind is Action.REFORM and proposal.actor in reformed)
            or (proposal.kind is Action.MIGRATION and bool(participants & (moved | ownership)))
            or (proposal.kind is Action.CONFLICT and bool(participants & moved))
            or (proposal.kind in CONTESTS and bool(participants & (contested | restructured)))
            or (proposal.kind is Action.SECESSION and bool(participants & contested))
        )
        administrators: set[str] = (
            set(context.administrators(proposal.actor))
            | set(context.administrators(proposal.target))
            if proposal.kind is Action.DEPENDENCY
            else set()
        )
        committed = administrators & administrations.keys()
        if (
            reservation in reserved
            or {proposal.actor, proposal.target} & retired
            or (proposal.kind is Action.DEPENDENCY and proposal.actor in subjects)
            or (proposal.kind is Action.PACT and {proposal.actor, proposal.target} & subjects)
            or incompatible
            or committed
        ):
            event = replace(
                event,
                outcome=Outcome.REFUSED,
                reason=Reason.COMMITTED,
                effects=Effects(),
                causes=tuple(sorted({*event.causes, *(administrations[key] for key in committed)})),
            )
            costs = {}
        if costs:
            reserved.add(reservation)
            retired.update(event.effects.retired)
            if proposal.kind is Action.DEPENDENCY:
                subjects.add(proposal.actor)
                administrations.update(dict.fromkeys(administrators, event.key))
            if proposal.kind is Action.MIGRATION:
                moved.update(participants)
            if proposal.kind is Action.CONFLICT:
                ownership.update(participants)
            if proposal.kind in CONTESTS:
                contested.update(participants)
            if proposal.kind is Action.SECESSION:
                # A realm losing a province this round cannot also fight over its land.
                restructured.update(participants)
            if proposal.kind is Action.REFORM:
                reformed.add(proposal.actor)
            for key, amount in costs.items():
                remaining[key] -= amount
        events.append(replace(event, commitments=tuple(sorted(costs.items()))))
    events = inherit_round(context, events)
    state = _apply(history.state, events)
    year = state.year + YEARS
    state = replace(
        state, year=year, memories=tuple(memory for memory in state.memories if memory.at(year))
    )
    validate_snapshot(Index(history.geography, state, checkpoint, physical=context.index), state)
    return replace(
        history,
        state=state,
        events=(*history.events, *events),
        rounds=(*history.rounds, proposals),
    )


def _roots(context: Context, actor: Actor) -> tuple[Actor, ...]:
    pending = list(actor.parents)
    roots: dict[str, Actor] = {}
    seen: set[str] = set()
    while pending:
        context.checkpoint()
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        parent = context.index.actors[key]
        if parent.parents:
            pending.extend(parent.parents)
        else:
            roots[parent.key] = parent
    return tuple(roots[key] for key in sorted(roots))


def _defence_choices(
    context: Context, first: str, second: str, allowed: frozenset[Action]
) -> list[Proposal]:
    if not (
        (Action.PACT in allowed or Action.PROTECTION in allowed)
        and context.threats.get(first)
        and context.threats.get(second)
    ):
        return []
    shared = (
        context.reach.get(first, {}).keys()
        & context.reach.get(second, {}).keys()
        & context.threats[first]
        & context.threats[second]
    )
    return [
        Proposal(kind, first, second, threat=threat)
        for threat in sorted(shared - {first, second})
        for kind in (Action.PACT, Action.PROTECTION)
        if kind in allowed and (kind is not Action.PACT or not {first, second} & context.subjects)
    ]


def _secession_choices(context: Context, actor: Actor) -> list[Proposal]:
    """Each conquered founder's province of a realm above its unrest threshold."""
    if actor.tenure is not Tenure.LAND or context.burden(actor.key) <= context.unrest(actor.key):
        return []
    lineage = context.ancestry(actor.key)
    provinces: dict[str, list[str]] = {}
    for key in sorted(context.index.members[actor.key]):
        founder = context.founders.get(key, "")
        if founder and founder not in lineage:
            provinces.setdefault(founder, []).append(key)
    result: list[Proposal] = []
    for founder, districts in sorted(provinces.items()):
        away = tuple(districts)
        core = tuple(sorted(context.index.members[actor.key] - set(away)))
        if not core:
            continue
        result.append(
            Proposal(
                Action.SECESSION,
                actor.key,
                partitions=(
                    Partition(core, actor.seat, actor.authority),
                    Partition(
                        away,
                        breakaway_seat(context, away, founder),
                        context.index.actors[founder].authority,
                    ),
                ),
            )
        )
    return result


def _dependency_choices(context: Context, actor: Actor, other: str) -> list[Proposal]:
    """D25: submit to a lord one fears, or to one that can face a recorded threat."""
    result: list[Proposal] = []
    if (actor.key, other, Factor.FEAR) in context.memories:
        result.append(Proposal(Action.DEPENDENCY, actor.key, other))
    reach = context.reach.get(other, {})
    result.extend(
        Proposal(Action.DEPENDENCY, actor.key, other, threat=threat)
        for threat in sorted(context.threats.get(actor.key, set()) - {other, actor.key})
        if threat in reach
    )
    return result


def _local_choices(  # noqa: C901, PLR0912 - every family's necessary local conditions
    context: Context, actor: Actor, kinds: frozenset[Action] | None = None
) -> list[Proposal]:
    # Necessary prior-snapshot conditions only; full eligibility still decides
    # every retained proposal. Avoid allocating impossible roles and duplicates.
    allowed = frozenset(Action) if kinds is None else kinds
    local: list[Proposal] = choices(context, actor, kinds)
    if (
        Action.SEPARATION in allowed
        and actor.parents
        and actor.tenure is Tenure.LAND
        and actor.key not in context.bound
    ):
        roots = _roots(context, actor)
        parts = tuple(Partition(root.homeland, root.seat, root.authority) for root in roots)
        local.append(Proposal(Action.SEPARATION, actor.key, partitions=parts))
    if Action.SECESSION in allowed:
        local.extend(_secession_choices(context, actor))
    lord = context.lords.get(actor.key, "")
    if Action.INDEPENDENCE in allowed and lord:
        local.append(Proposal(Action.INDEPENDENCE, actor.key, lord))
    groups = set(context.groups.get(actor.key, ()))
    for other in sorted(context.reach.get(actor.key, {})):
        context.checkpoint()
        if (actor.key, other) not in context.known:
            if Action.CONTACT in allowed:
                local.append(Proposal(Action.CONTACT, actor.key, other))
            continue
        if (other, actor.key) not in context.known:
            continue
        target = context.index.actors[other]
        if (
            Action.EXCHANGE in allowed
            and tuple(sorted((actor.key, other))) not in context.recent_exchanges
        ):
            local.append(Proposal(Action.EXCHANGE, actor.key, other))
        landed = actor.tenure is Tenure.LAND and target.tenure is Tenure.LAND
        if landed:
            if (
                Action.UNION in allowed
                and actor.key not in context.bound
                and other not in context.bound
                and other in context.near.get(actor.key, {})
            ):
                local.append(Proposal(Action.UNION, actor.key, other))
            if (
                Action.DEPENDENCY in allowed
                and actor.key not in context.subjects
                and actor.key not in context.pact_participants
                and target.technology >= context.history.geography.rules.minimum_overlord_technology
            ):
                local.extend(_dependency_choices(context, actor, other))
        pact = (
            context.has(Action.PACT, actor.key, other)
            if Action.CONFLICT in allowed or Action.PRESSURE in allowed or Action.PACT in allowed
            else False
        )
        conflict = (
            Action.CONFLICT in allowed
            and landed
            and actor.key not in context.subjects
            and other not in context.subjects
            and not pact
        )
        pressure = (
            Action.PRESSURE in allowed
            and actor.tenure is Tenure.LAND
            and target.tenure is not Tenure.LAND
            and actor.key not in context.subjects
            and not pact
            and actor.society.military is Military.OFFENSIVE
        )
        if conflict or pressure:
            frontier = {
                key
                for member in context.index.members[actor.key]
                for key in context.index.adjacency[member]
                if context.index.owner.get(key) == other
            }
            local.extend(
                Proposal(Action.PRESSURE if pressure else Action.CONFLICT, actor.key, other, (key,))
                for key in sorted(frontier)
                if pressure or key != target.seat or len(context.index.members[other]) == 1
            )
            # D23: an expansion aim may seek a whole neighbour at once; the same
            # contest, support and capacity rules decide it.
            if conflict and frontier and actor.key in context.aims:
                held = tuple(sorted(context.index.members[other]))
                if len(held) > 1:
                    local.append(Proposal(Action.CONFLICT, actor.key, other, held))
        local.extend(_defence_choices(context, actor.key, other, allowed))
        if Action.PACT in allowed and not pact and groups & set(context.groups.get(other, ())):
            local.append(Proposal(Action.PACT, actor.key, other))
        if Action.ACCESS in allowed and not context.has(Action.ACCESS, actor.key, other):
            local.extend(
                Proposal(Action.ACCESS, actor.key, other, (key,))
                for key in sorted(context.index.members[other])
                if context.index.places[key].sacred
            )
    return [choice for choice in local if eligible(context, choice) is None]


def _bases(context: Context, actor: Actor, turbulence: int) -> dict[Action, int]:
    """Per-family admission propensity before the society's own orientation."""
    base = dict.fromkeys(Action, 180)
    base[Action.SEPARATION] = turbulence**3 // PERMILLE**2
    base[Action.CONFLICT] = base[Action.PRESSURE] = (
        50 + turbulence // 2 + ESCALATION * max(0, turbulence - 500) // PERMILLE
    )
    base[Action.SECESSION] = 100 + turbulence // 2
    aim = context.aims.get(actor.key)
    if aim is not None:
        # A hegemonic or extraordinary ambition persists whatever the turbulence,
        # which instead decides how much of it holds; rival powers follow the times.
        persistent = (
            HEGEMONY_CONFLICT
            if aim.kind is not TrajectoryKind.REGIONAL_POWER
            else AIM_CONFLICT + turbulence // 2
        )
        base[Action.CONFLICT] = base[Action.PRESSURE] = max(base[Action.CONFLICT], persistent)
    if context.threats.get(actor.key, set()) & context.aims.keys():
        for kind in (Action.PACT, Action.PROTECTION, Action.DEPENDENCY):
            base[kind] = max(base[kind], FEAR_RESPONSE)
    kinds = {item.kind for item in context.groups.get(actor.key, ())}
    if kinds & {TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION}:
        base[Action.PACT] = max(base[Action.PACT], GROUP_BOND)
        base[Action.EXCHANGE] = max(base[Action.EXCHANGE], GROUP_EXCHANGE)
    if TrajectoryKind.SACRED_CENTRE in kinds:
        base[Action.ACCESS] = max(base[Action.ACCESS], SACRED_VISIT)
    return base


def _keeps_aim(context: Context, actor: Actor, after: Society) -> bool:
    """An aim's holder does not reform away from the inclination its aim recorded."""
    before = actor.society
    aim = context.aims.get(actor.key)
    if aim is not None and (
        after.centralization < before.centralization
        or after.integration < before.integration
        or (before.military is Military.OFFENSIVE and after.military is not Military.OFFENSIVE)
        or (before.authority is Authority.RULER and after.authority is not Authority.RULER)
    ):
        return False
    for item in context.groups.get(actor.key, ()):
        if (
            item.kind is TrajectoryKind.SACRED_CENTRE
            and context.index.owner.get(item.anchor) == actor.key
        ):
            if after.authority is not before.authority or (
                after.religious_authority < before.religious_authority
            ):
                return False
        elif item.kind is TrajectoryKind.SEA_LEAGUE and (
            before.authority is Authority.COUNCIL and after.authority is not Authority.COUNCIL
        ):
            return False
    return True


def _domain(context: Context, aim: Trajectory, place: str) -> bool:
    if aim.region:
        return context.index.places[place].region == aim.region
    hearth = next(each for each in context.history.geography.hearths if each.key == aim.hearth)
    return place in hearth.domain


def _preference(context: Context, actor: Actor, choice: Proposal) -> tuple[int, int]:
    """Lower is preferred: (rank across families, order within the family).

    Ordinary choices share rank 1, so without an aim or actual fear the families
    keep their seeded order. An aim's contest in its domain comes first.
    """
    aim = context.aims.get(actor.key)
    if choice.kind in {Action.CONFLICT, Action.PRESSURE} and aim is not None:
        inside = all(_domain(context, aim, place) for place in choice.districts)
        # A paramount prefers to leave a defeated neighbour standing, fearful and
        # free to submit, before it annexes one.
        whole = len(choice.districts) == len(context.index.members[choice.target])
        rank = (0 if inside else 2) + (1 if aim.kind is TrajectoryKind.PARAMOUNT and whole else 0)
        # Pressure takes no land; an aim's holder presses a tribe only when no state
        # of its domain can be contested first (one contest fits a round's budget).
        rank += choice.kind is Action.PRESSURE
        return rank, context.power(choice.target)
    if choice.kind is Action.DEPENDENCY:
        return (0 if choice.target in context.aims else 1), 0
    # Partners of one seeded league or confederation first bargain with each other.
    if (
        choice.kind in {Action.PACT, Action.EXCHANGE}
        and not choice.threat
        and any(
            item.kind in {TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION}
            for item in context.groups.get(actor.key, ())
            if item in context.groups.get(choice.target, ())
        )
    ):
        return 0, 0
    if choice.kind in {Action.PACT, Action.PROTECTION}:
        return (0 if choice.threat in context.aims else 1), 0
    if choice.kind is Action.ACCESS:
        hosts = {
            context.index.owner.get(item.anchor)
            for item in context.groups.get(actor.key, ())
            if item.kind is TrajectoryKind.SACRED_CENTRE
        }
        return (0 if choice.target in hosts else 1), 0
    return 1, 0


def propose(context: Context, *, turbulence: int = 500) -> tuple[Proposal, ...]:
    """Admit action families independently of degree, then rank their eligible choices."""
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    proposals: list[Proposal] = []
    for actor in context.state.actors:
        context.checkpoint()
        if not actor.living:
            continue
        admitted: set[Action] = set()
        bases = _bases(context, actor, turbulence)
        for kind in Action:
            activity = derive_seed(
                context.history.seed,
                "history",
                "activity",
                str(context.state.year),
                actor.key,
                kind.value,
            )
            if activity % PERMILLE < propensity(actor.society, kind, bases[kind]):
                admitted.add(kind)
        best: dict[Action, tuple[tuple[int, int], int, str, Proposal]] = {}
        for choice in _local_choices(context, actor, frozenset(admitted)):
            if choice.kind is Action.REFORM and (
                choice.reform is None or not _keeps_aim(context, actor, choice.reform)
            ):
                continue
            key = proposal_key(choice)
            draw = derive_seed(
                context.history.seed, "history", "choice", str(context.state.year), key
            )
            ranked = (_preference(context, actor, choice), draw, key, choice)
            if choice.kind not in best or ranked[:3] < best[choice.kind][:3]:
                best[choice.kind] = ranked
        # Families compete by rank and their seeded draw, not by a target's strength.
        proposals.extend(
            replace(choice, rank=rank)
            for rank, (_, _, _, choice) in enumerate(
                sorted(best.values(), key=lambda r: (r[0][0], r[1], r[2]))[:MAX_PROPOSALS]
            )
        )
    return tuple(proposals)


def simulate(
    history: History,
    *,
    turbulence: int | None = None,
    policy: Callable[[Context], Sequence[Proposal]] | None = None,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Run every remaining five-year round, including quiet rounds, through 1337.

    The history's own turbulence, which also seeded its settings, is the default.
    """
    turbulence = history.turbulence if turbulence is None else turbulence
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    physical: Index | None = None
    while history.state.year < END:
        context = Context(history, checkpoint, physical=physical)
        physical = context.index
        proposals = (
            policy(context) if policy is not None else propose(context, turbulence=turbulence)
        )
        history = _advance(context, proposals)
    return history


def validate_history(history: History, *, checkpoint: Callable[[], None] = _checkpoint) -> None:
    """Replay prerequisites, arbitration and effects; reject invented or superseded final facts."""
    replay = create(
        history.geography,
        history.foundings,
        seed=history.seed,
        empire_permille=history.empire_permille,
        turbulence=history.turbulence,
        checkpoint=checkpoint,
    )
    seen: dict[str, Event] = {}
    actors = {actor.key: actor for actor in history.state.actors}
    for event in history.events:
        checkpoint()
        require(event.key not in seen, "Duplicate event ID")
        require(
            all(cause in seen and seen[cause].year <= event.year for cause in event.causes),
            "Missing, future or cyclic event cause",
        )
        require(
            all(key in actors and alive_at(actors[key], event.year) for key in event.actors),
            "Event touches an actor outside its lifetime",
        )
        seen[event.key] = event
    physical: Index | None = None
    for proposals in history.rounds:
        context = Context(replay, checkpoint, physical=physical)
        physical = context.index
        replay = _advance(context, proposals)
    require(replay.events == history.events, "Causal event replay differs")
    require(replay.state == history.state, "Final facts differ from causal replay")


def _json_record(value: object) -> dict[str, object]:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: cast("object", getattr(value, field.name)) for field in fields(value)}
    message = f"Unsupported history record: {type(value).__name__}"
    raise TypeError(message)


def digest(history: History, *, checkpoint: Callable[[], None] = _checkpoint) -> str:
    """Canonical semantic digest; contains no wording, resource roll, diagnostics or clock."""

    def record(value: object) -> dict[str, object]:
        checkpoint()
        return _json_record(value)

    payload = json.dumps(
        history, default=record, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()
