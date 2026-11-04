"""Synchronous deterministic history rounds, sparse effects and exact causal replay.

The normal H4 exporter projects this private model; presentation never supplies facts.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import fields, is_dataclass, replace
from typing import TYPE_CHECKING, cast

from rnw.history_actions import (
    PRIORITY,
    adjudicate,
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
    Effects,
    Event,
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
    Tenure,
    Transfer,
)
from rnw.history_societies import bootstrap, choices, cohorts, propensity
from rnw.history_trajectories import seed_events
from rnw.rng import check_seed, derive_seed

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


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


def create(
    geography: Geography,
    foundings: Sequence[Founding],
    *,
    seed: int,
    empire_permille: int = 250,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Create causal roots for every supplied actor; no country or population is invented."""
    validate_geography(geography)
    _ = check_seed(seed)
    require(0 <= empire_permille <= PERMILLE, "Invalid extraordinary trajectory chance")
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
        geography, seed, canonical, state, tuple(events), empire_permille=empire_permille
    )
    ambitions = seed_events(Context(history, checkpoint), empire_permille)
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
            (proposal.kind in {Action.SEPARATION, Action.REFORM}) == (not proposal.target),
            "Only separation/reform has no partner",
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


def _advance(context: Context, proposals: Sequence[Proposal]) -> History:
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
    validate_snapshot(Index(history.geography, state, checkpoint), state)
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


def _local_choices(
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
                local.append(Proposal(Action.DEPENDENCY, actor.key, other))
        pact = context.has(Action.PACT, actor.key, other)
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
        shared = (
            context.reach.get(actor.key, {}).keys()
            & context.reach.get(other, {}).keys()
            & context.threats.get(actor.key, set())
            & context.threats.get(other, set())
        )
        local.extend(
            Proposal(kind, actor.key, other, threat=threat)
            for threat in sorted(shared - {actor.key, other})
            for kind in (Action.PACT, Action.PROTECTION)
            if kind in allowed
            and (kind is not Action.PACT or not {actor.key, other} & context.subjects)
        )
        if Action.ACCESS in allowed and not context.has(Action.ACCESS, actor.key, other):
            local.extend(
                Proposal(Action.ACCESS, actor.key, other, (key,))
                for key in sorted(context.index.members[other])
                if context.index.places[key].sacred
            )
    return [choice for choice in local if eligible(context, choice) is None]


def propose(context: Context, *, turbulence: int = 500) -> tuple[Proposal, ...]:
    """Admit action families independently of degree, then rank their eligible choices."""
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    proposals: list[Proposal] = []
    for actor in context.state.actors:
        context.checkpoint()
        if not actor.living:
            continue
        admitted: set[Action] = set()
        for kind in Action:
            base = (
                turbulence**3 // PERMILLE**2
                if kind is Action.SEPARATION
                else (50 + turbulence // 2)
                if kind in {Action.CONFLICT, Action.PRESSURE}
                else 180
            )
            activity = derive_seed(
                context.history.seed,
                "history",
                "activity",
                str(context.state.year),
                actor.key,
                kind.value,
            )
            if activity % PERMILLE < propensity(actor.society, kind, base):
                admitted.add(kind)
        best: dict[Action, tuple[int, str, Proposal]] = {}
        for choice in _local_choices(context, actor, frozenset(admitted)):
            key = proposal_key(choice)
            draw = derive_seed(
                context.history.seed, "history", "choice", str(context.state.year), key
            )
            ranked = (draw, key, choice)
            if choice.kind not in best or ranked[:2] < best[choice.kind][:2]:
                best[choice.kind] = ranked
        proposals.extend(
            replace(choice, rank=rank)
            for rank, (_, _, choice) in enumerate(sorted(best.values())[:MAX_PROPOSALS])
        )
    return tuple(proposals)


def simulate(
    history: History,
    *,
    turbulence: int = 500,
    policy: Callable[[Context], Sequence[Proposal]] | None = None,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Run every remaining five-year round, including quiet rounds, through 1337."""
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    while history.state.year < END:
        context = Context(history, checkpoint)
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
    for proposals in history.rounds:
        replay = advance(replay, proposals, checkpoint=checkpoint)
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
