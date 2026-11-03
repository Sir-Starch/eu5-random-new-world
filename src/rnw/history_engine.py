"""Synchronous deterministic history rounds, sparse effects and exact causal replay.

H2 is an offline core. No exporter calls it until the H4 projection adapter exists.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from typing import TYPE_CHECKING

from rnw.history_actions import (
    MUTUAL,
    PRIORITY,
    Context,
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
    Outcome,
    Partition,
    Proposal,
    Reason,
    Snapshot,
    Transfer,
)
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
    )


def create(geography: Geography, foundings: Sequence[Founding], *, seed: int) -> History:
    """Create causal roots for every supplied actor; no country or population is invented."""
    validate_geography(geography)
    _ = check_seed(seed)
    unique((founding.key for founding in foundings), "founding")
    geography = replace(
        geography,
        districts=tuple(
            sorted(
                (
                    replace(
                        place,
                        cohorts=tuple(
                            sorted(
                                place.cohorts,
                                key=lambda pop: (
                                    pop.culture,
                                    pop.religion,
                                    pop.population,
                                    pop.peasants,
                                ),
                            )
                        ),
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
    )
    canonical = tuple(
        replace(founding, districts=tuple(sorted(founding.districts)))
        for founding in sorted(foundings, key=lambda founding: founding.key)
    )
    state = Snapshot(START)
    events: list[Event] = []
    for founding in canonical:
        unique(founding.districts, "founding district")
        key = f"origin_{derive_seed(seed, 'history', 'origin', founding.key):016x}"
        actor = Actor(
            founding.key,
            founding.tenure,
            founding.seat,
            founding.authority,
            founding.technology,
            START,
            key,
            founding.districts,
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
            ),
        )
        events.append(event)
    state = _apply(state, events)
    validate_snapshot(Index(geography, state, _checkpoint), state)
    return History(geography, seed, canonical, state, tuple(events))


def _validate_proposals(context: Context, proposals: Sequence[Proposal]) -> tuple[Proposal, ...]:
    require(
        all(proposal.kind is not Action.FOUNDATION for proposal in proposals), "No late founding"
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
            (proposal.kind is Action.SEPARATION) == (not proposal.target),
            "Only separation has no partner",
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
    return tuple(sorted(canonical, key=proposal_key))


def advance(
    history: History,
    proposals: Sequence[Proposal],
    *,
    checkpoint: Callable[[], None] = _checkpoint,
) -> History:
    """Evaluate on the same prior state, reserve commitments, then commit one whole round."""
    require(history.state.year < END, "History already reached 1337")
    checkpoint()
    context = Context(history, checkpoint)
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
    for proposal in sorted(proposals, key=order):
        checkpoint()
        event, costs = adjudicate(context, proposal, remaining)
        first, second = proposal.actor, proposal.target
        if proposal.kind in MUTUAL:
            first, second = sorted((first, second))
        reservation = (proposal.kind, first, second, proposal.districts)
        if (
            reservation in reserved
            or {proposal.actor, proposal.target} & retired
            or (proposal.kind is Action.DEPENDENCY and proposal.actor in subjects)
            or (proposal.kind is Action.PACT and {proposal.actor, proposal.target} & subjects)
        ):
            event = replace(
                event, outcome=Outcome.REFUSED, reason=Reason.COMMITTED, effects=Effects()
            )
            costs = {}
        if costs:
            reserved.add(reservation)
            retired.update(event.effects.retired)
            if proposal.kind is Action.DEPENDENCY:
                subjects.add(proposal.actor)
            for key, amount in costs.items():
                remaining[key] -= amount
        events.append(replace(event, commitments=tuple(sorted(costs.items()))))
    events = inherit_round(context, events)
    state = _apply(history.state, events)
    state = replace(state, year=state.year + YEARS)
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
    while pending:
        parent = context.index.actors[pending.pop()]
        if parent.parents:
            pending.extend(parent.parents)
        else:
            roots[parent.key] = parent
    return tuple(roots[key] for key in sorted(roots))


def _local_choices(context: Context, actor: Actor) -> list[Proposal]:
    choices: list[Proposal] = []
    if actor.parents:
        roots = _roots(context, actor)
        parts = tuple(Partition(root.homeland, root.seat, root.authority) for root in roots)
        choices.append(Proposal(Action.SEPARATION, actor.key, partitions=parts))
    for other in sorted(context.reach.get(actor.key, {})):
        context.checkpoint()
        if (actor.key, other) not in context.known:
            choices.append(Proposal(Action.CONTACT, actor.key, other))
            continue
        choices.extend(
            (
                Proposal(Action.EXCHANGE, actor.key, other),
                Proposal(Action.UNION, actor.key, other),
                Proposal(Action.DEPENDENCY, actor.key, other),
            )
        )
        target = context.index.actors[other]
        frontier = {
            key
            for member in context.index.members[actor.key]
            for key in context.index.adjacency[member]
            if context.index.owner.get(key) == other
        }
        choices.extend(
            Proposal(Action.CONFLICT, actor.key, other, (key,))
            for key in sorted(frontier)
            if key != target.seat or len(context.index.members[other]) == 1
        )
        shared = context.reach.get(actor.key, {}).keys() & context.reach.get(other, {}).keys()
        choices.extend(
            Proposal(kind, actor.key, other, threat=threat)
            for threat in sorted(shared - {actor.key, other})
            for kind in (Action.PACT, Action.PROTECTION)
        )
        choices.extend(
            Proposal(Action.ACCESS, actor.key, other, (key,))
            for key in sorted(context.index.members[other])
            if context.index.places[key].sacred
        )
    return [choice for choice in choices if eligible(context, choice) is None]


def propose(context: Context, *, turbulence: int = 500) -> tuple[Proposal, ...]:
    """Bounded local choice policy. Its propensities are provisional until H7 calibration."""
    require(0 <= turbulence <= PERMILLE, "Invalid historical turbulence")
    proposals: list[Proposal] = []
    for actor in context.state.actors:
        context.checkpoint()
        if not actor.living:
            continue
        ranked: list[tuple[int, str, Proposal]] = []
        for choice in _local_choices(context, actor):
            key = proposal_key(choice)
            draw = derive_seed(
                context.history.seed, "history", "choice", str(context.state.year), key
            )
            propensity = (
                (50 + turbulence // 2)
                if choice.kind in {Action.CONFLICT, Action.SEPARATION}
                else 180
            )
            if draw % PERMILLE < propensity:
                ranked.append((draw, key, choice))
        proposals.extend(
            replace(choice, rank=rank)
            for rank, (_, _, choice) in enumerate(sorted(ranked)[:MAX_PROPOSALS])
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
        history = advance(history, proposals, checkpoint=checkpoint)
    return history


def validate_history(history: History, *, checkpoint: Callable[[], None] = _checkpoint) -> None:
    """Replay prerequisites, arbitration and effects; reject invented or superseded final facts."""
    replay = create(history.geography, history.foundings, seed=history.seed)
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


def digest(history: History) -> str:
    """Canonical semantic digest; contains no wording, resource roll, diagnostics or clock."""
    payload = json.dumps(asdict(history), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()
