"""Unpruned candidate enumeration before H7 optimization, using the unchanged prerequisites."""

from dataclasses import replace

from rnw.history_actions import eligible
from rnw.history_context import Context
from rnw.history_engine import _roots  # pyright: ignore[reportPrivateUsage]
from rnw.history_model import Action, Actor, Movement, Partition, Proposal
from rnw.history_societies import reforms


def unpruned_society_choices(
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
        for destination in sorted(context.index.adjacency[source]):
            target = context.index.owner.get(destination, "")
            if not target or target == actor.key or (actor.key, target) not in context.known:
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


def unpruned_choices(
    context: Context, actor: Actor, kinds: frozenset[Action] | None = None
) -> list[Proposal]:
    local: list[Proposal] = unpruned_society_choices(context, actor)
    if actor.parents:
        roots = _roots(context, actor)
        parts = tuple(Partition(root.homeland, root.seat, root.authority) for root in roots)
        local.append(Proposal(Action.SEPARATION, actor.key, partitions=parts))
    for other in sorted(context.reach.get(actor.key, {})):
        context.checkpoint()
        if (actor.key, other) not in context.known:
            local.append(Proposal(Action.CONTACT, actor.key, other))
            continue
        local.extend(
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
        local.extend(
            Proposal(Action.PRESSURE, actor.key, other, (key,)) for key in sorted(frontier)
        )
        local.extend(
            Proposal(Action.CONFLICT, actor.key, other, (key,))
            for key in sorted(frontier)
            if key != target.seat or len(context.index.members[other]) == 1
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
        )
        local.extend(
            Proposal(Action.ACCESS, actor.key, other, (key,))
            for key in sorted(context.index.members[other])
            if context.index.places[key].sacred
        )
    return [
        choice
        for choice in local
        if (kinds is None or choice.kind in kinds) and eligible(context, choice) is None
    ]
