"""Sparse facts, causal lookup and capacity calculations for one immutable round."""

from __future__ import annotations

import heapq
from collections import defaultdict
from typing import TYPE_CHECKING, Final, final

from rnw.history_checks import Index, require
from rnw.history_model import (
    PERMILLE,
    YEARS,
    Action,
    Event,
    Factor,
    History,
    Livelihood,
    Memory,
    Outcome,
    Strategy,
    Trajectory,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.history_model import Actor, Proposal, Society

MUTUAL = frozenset({Action.CONTACT, Action.EXCHANGE, Action.UNION, Action.PACT})
INTEGRATION_YEARS: Final[int] = 25
# Administrative capacity (plan D24). Centralization and integration above this
# combined score double the surplus capacity every CAPACITY_DOUBLING points;
# technology above level 1 multiplies the surplus by half a level each. A society
# at or below the threshold keeps the 1.1.0-calibrated ordinary limit of 1,000.
CAPACITY_THRESHOLD: Final[int] = 1100
CAPACITY_DOUBLING: Final[int] = 200
OVERREACH_FACTOR: Final[int] = 2
UNREST_SLOPE: Final[int] = 450


@final
class Context:
    def __init__(
        self,
        history: History,
        checkpoint: Callable[[], None],
        *,
        physical: Index | None = None,
        previous: Context | None = None,
    ) -> None:
        """``previous`` may be the context of an earlier round of the same history; its
        event tables are then extended instead of rebuilt. Either way they are the same.
        """
        if physical is None and previous is not None:
            physical = previous.index
        self.history = history
        self.state = history.state
        self.index = Index(history.geography, history.state, checkpoint, physical=physical)
        self.checkpoint = checkpoint
        self.known = {(each.first, each.second) for each in self.state.knowledge}
        self.memories: dict[tuple[str, str, Factor], list[Memory]] = defaultdict(list)
        self.afraid: set[str] = set()
        self.threats: dict[str, set[str]] = defaultdict(set)
        self.causes_by_actor: dict[str, set[str]] = defaultdict(set)
        self._events(history, previous)
        self.frontiers: dict[str, tuple[str, ...]] = {}
        self.reform_choices: dict[str, tuple[Actor, tuple[Society, ...]]] = {}
        self.holdings = {holding.district: holding for holding in self.state.holdings}
        for actor in self.state.actors:
            self.causes_by_actor[actor.key].add(actor.society_cause)
        for settlement in self.state.settlements:
            self.causes_by_actor[self.index.owner[settlement.district]].add(settlement.cause)
        for holding in self.state.holdings:
            self.causes_by_actor[holding.actor].add(holding.cause)
        for memory in self.state.memories:
            self.memories[memory.first, memory.second, memory.factor].append(memory)
            if memory.at(self.state.year):
                if memory.factor in {Factor.FEAR, Factor.GRIEVANCE}:
                    self.afraid.add(memory.first)
                    self.threats[memory.first].add(memory.second)
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
        self.lords = {
            bond.first: bond.second for bond in self.state.bonds if bond.kind is Action.DEPENDENCY
        }
        self.clients: dict[str, set[str]] = defaultdict(set)
        for subject, lord in self.lords.items():
            self.clients[lord].add(subject)
        self.realms: dict[str, frozenset[str]] = {}
        self.people: dict[str, int] = {}
        self.pact_participants = {
            key
            for bond in self.state.bonds
            if bond.kind is Action.PACT
            for key in (bond.first, bond.second)
        }
        self.recent_exchanges = {
            tuple(sorted((bond.first, bond.second)))
            for bond in self.state.bonds
            if bond.kind is Action.EXCHANGE and self.event_years[bond.cause] > self.state.year - 15
        }
        self._contacts()
        self.bound = {
            key
            for bond in self.state.bonds
            if bond.kind is Action.DEPENDENCY
            for key in (bond.first, bond.second)
        }
        self.subjects = set(self.lords)
        self._alliances: tuple[dict[str, set[str]], dict[str, set[str]]] | None = None
        self._aims: dict[str, Trajectory] | None = None
        self._groups: dict[str, tuple[Trajectory, ...]] | None = None
        self._founders: dict[str, str] | None = None
        self.ancestries: dict[str, frozenset[str]] = {}

    def _events(self, history: History, previous: Context | None) -> None:
        """Year, kind and record of every event, and each actor's events in order."""
        shared = 0
        if previous is not None and previous.history.geography is history.geography:
            earlier = previous.history.events
            if len(earlier) <= len(history.events) and history.events[: len(earlier)] == earlier:
                shared = len(earlier)
        self.event_years: dict[str, int]
        self.event_kinds: dict[str, Action]
        self.events: dict[str, Event]
        self.experiences: dict[str, list[Event]]
        if shared and previous is not None:
            self.event_years = previous.event_years.copy()
            self.event_kinds = previous.event_kinds.copy()
            self.events = previous.events.copy()
            # The earlier lists are shared until an actor gains an event; none is changed.
            self.experiences = defaultdict(list, previous.experiences)
        else:
            self.event_years = {}
            self.event_kinds = {}
            self.events = {}
            self.experiences = defaultdict(list)
        copied: set[str] = set()
        experiences = self.experiences
        for event in history.events[shared:]:
            self.event_years[event.key] = event.year
            self.event_kinds[event.key] = event.kind
            self.events[event.key] = event
            for key in event.actors:
                if shared and key not in copied:
                    copied.add(key)
                    experiences[key] = [*experiences.get(key, ())]
                experiences[key].append(event)

    def _contacts(self) -> None:
        self.near: dict[str, dict[str, int]] = defaultdict(dict)
        self.land_near: dict[str, set[str]] = defaultdict(set)
        self.sea_near: dict[str, set[str]] = defaultdict(set)
        owner, near = self.index.owner, self.near
        for number, (one, two, cost, sea) in enumerate(self.index.passages):
            if number % 128 == 0:
                self.checkpoint()
            first, second = owner.get(one), owner.get(two)
            if first and second and first != second:
                previous = near[first].get(second)
                if previous is None or cost < previous:
                    near[first][second] = cost
                    near[second][first] = cost
                contacts = self.sea_near if sea else self.land_near
                contacts[first].add(second)
                contacts[second].add(first)
        self.reach = {key: dict(near) for key, near in self.near.items()}
        # Exchange supplies one intermediary, over verified physical contacts, not sea labels.
        for bond in self.state.bonds:
            if bond.kind is Action.EXCHANGE:
                for one, hub in ((bond.first, bond.second), (bond.second, bond.first)):
                    direct = self.near.get(one, {})
                    if hub not in direct:
                        continue
                    reached, step = self.reach[one], direct[hub]
                    for other, cost in self.near[hub].items():
                        if other != one:
                            distance = cost + step
                            previous = reached.get(other)
                            # Physical contacts and each admitted two-hop contact are mutual.
                            # Both directions already have the same minimum; update them once.
                            if previous is None or distance < previous:
                                reached[other] = distance
                                self.reach[other][one] = distance

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

    def population(self, key: str) -> int:
        if key not in self.people:
            self.people[key] = sum(
                self.index.population(place) for place in self.index.members[key]
            )
        return self.people[key]

    def realm(self, key: str) -> frozenset[str]:
        """The actor and its actual recursive clients in this immutable prior snapshot."""
        if key not in self.realms:
            found, pending = {key}, [key]
            while pending:
                self.checkpoint()
                for subject in self.clients.get(pending.pop(), set()):
                    require(subject not in found, "Dependency cycle in realm")
                    found.add(subject)
                    pending.append(subject)
            self.realms[key] = frozenset(found)
        return self.realms[key]

    def administrators(self, key: str) -> tuple[str, ...]:
        """Each ruler whose administrative capacity an admission would consume."""
        found: list[str] = []
        while key:
            require(key not in found, "Dependency cycle in administration")
            found.append(key)
            key = self.lords.get(key, "")
        return tuple(found)

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

    def capacity(self, key: str) -> int:
        """Administrative capacity from centralization, integration and technology (D24)."""
        actor = self.index.actors[key]
        surplus = actor.society.centralization + actor.society.integration - CAPACITY_THRESHOLD
        if surplus <= 0:
            return PERMILLE
        doublings, rest = divmod(surplus, CAPACITY_DOUBLING)
        # Piecewise-linear 2**(surplus / doubling), continuous at every doubling.
        factor = (1 << doublings) * (PERMILLE + rest * PERMILLE // CAPACITY_DOUBLING)
        technology = max(PERMILLE, (actor.technology + 1) * PERMILLE // 2)
        return PERMILLE + (factor - PERMILLE) * technology // PERMILLE

    def unrest(self, key: str) -> int:
        """The burden above which conquered provinces may break away.

        Historical turbulence lowers it: unrest and contested successions make
        holdings harder to keep (91% of capacity at Calm, 77.5% at Varied, 64% at
        Turbulent), while conquest itself remains bounded by capacity.
        """
        tolerance = PERMILLE - UNREST_SLOPE * self.history.turbulence // PERMILLE
        return self.capacity(key) * tolerance // PERMILLE

    def strain(self, key: str) -> int:
        """Administrative load as a fraction of this realm's capacity, in thousandths."""
        return self.burden(key) * PERMILLE // self.capacity(key)

    def limit(self, key: str) -> int:
        """The burden a conquest may reach: twice capacity only for an overreaching aim."""
        aim = self.aims.get(key)
        factor = (
            OVERREACH_FACTOR if aim is not None and aim.strategy is Strategy.OVERREACHING else 1
        )
        return self.capacity(key) * factor

    def ancestry(self, key: str) -> frozenset[str]:
        """The actor and every recorded predecessor."""
        if key not in self.ancestries:
            pending, seen = [key], set[str]()
            while pending:
                current = pending.pop()
                if current not in seen:
                    seen.add(current)
                    pending.extend(self.index.actors[current].parents)
            self.ancestries[key] = frozenset(seen)
        return self.ancestries[key]

    def _alliance_tables(self) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        if self._alliances is None:
            allies: dict[str, set[str]] = defaultdict(set)
            causes: dict[str, set[str]] = defaultdict(set)
            for bond in self.state.bonds:
                if bond.kind is Action.PACT:
                    allies[bond.first].add(bond.second)
                    allies[bond.second].add(bond.first)
                elif bond.kind is Action.DEPENDENCY:
                    allies[bond.second].add(bond.first)
                else:
                    continue
                causes[bond.first].add(bond.cause)
                causes[bond.second].add(bond.cause)
            self._alliances = allies, causes
        return self._alliances

    def allies(self, key: str) -> frozenset[str]:
        """Who fights beside the actor: its pact partners and its subjects."""
        return frozenset(self._alliance_tables()[0].get(key, ()))

    def alliance_causes(self, key: str) -> frozenset[str]:
        """The causes of every pact and dependency the actor is part of."""
        return frozenset(self._alliance_tables()[1].get(key, ()))

    @property
    def aims(self) -> dict[str, Trajectory]:
        """Living holders of an expansion aim: the anchor's owner, descended from its members."""
        if self._aims is None:
            found: dict[str, Trajectory] = {}
            for item in self.state.trajectories:
                owner = self.index.owner.get(item.anchor, "")
                if (
                    item.expansion
                    and owner
                    and self.index.actors[owner].living
                    and self.ancestry(owner) & set(item.members)
                ):
                    _ = found.setdefault(owner, item)
            self._aims = found
        return self._aims

    @property
    def groups(self) -> dict[str, tuple[Trajectory, ...]]:
        """League, confederation and sacred aims of each living descendant of a member."""
        if self._groups is None:
            found: dict[str, list[Trajectory]] = defaultdict(list)
            seeded = [item for item in self.state.trajectories if not item.expansion]
            if seeded:
                for actor in self.state.actors:
                    if actor.living:
                        lineage = self.ancestry(actor.key)
                        found[actor.key].extend(
                            item for item in seeded if lineage & set(item.members)
                        )
            self._groups = {key: tuple(items) for key, items in found.items() if items}
        return self._groups

    @property
    def founders(self) -> dict[str, str]:
        """The 1037 founding actor of every organized district."""
        if self._founders is None:
            self._founders = {
                place: founding.key
                for founding in self.history.foundings
                for place in founding.districts
            }
        return self._founders

    def distance(self, key: str, target: str, through: tuple[str, ...] = ()) -> int:
        """Travel through the actor's own territory to the attacking/defending frontier."""
        pair = key, target, through
        if pair not in self.distances:
            self.distances[pair] = self._distance(key, target, through)
        return self.distances[pair]

    def travel(self, key: str, through: tuple[str, ...] = ()) -> dict[str, int]:
        """Least travel cost from the actor's seat to every place of its territory and
        ``through`` that it reaches there: ``distance`` to each of them at once.
        """
        actor = self.index.actors[key]
        members = self.index.members[key] | set(through)
        adjacency = self.index.adjacency
        costs = {actor.seat: 0}
        pending = [(0, actor.seat)]
        while pending:
            self.checkpoint()
            cost, place = heapq.heappop(pending)
            if cost != costs[place]:
                continue
            for other, step in adjacency[place].items():
                if other in members and cost + step < costs.get(other, 1 << 60):
                    costs[other] = cost + step
                    heapq.heappush(pending, (cost + step, other))
        return costs

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

    def setbacks(self, lord: str, subject: str) -> tuple[str, ...]:
        """The lord's defeats of the previous round against anyone but the subject.

        A defeat is a repelled attack by the lord or land the lord lost. The
        contest's directed memories name its principal sides; supporting allies,
        including the subject itself, are not sides.
        """
        found: list[str] = []
        for event in self.experiences[lord]:
            if (
                event.year != self.state.year - YEARS
                or event.kind not in {Action.CONFLICT, Action.PRESSURE}
                or event.outcome is Outcome.REFUSED
            ):
                continue
            sides = {
                key for memory in event.effects.memories for key in (memory.first, memory.second)
            }
            if lord not in sides or subject in sides:
                continue
            repelled = event.outcome is Outcome.FAILED and any(
                memory.first == lord and memory.factor is Factor.FEAR
                for memory in event.effects.memories
            )
            lost = any(transfer.before == lord for transfer in event.effects.transfers)
            if repelled or lost:
                found.append(event.key)
        return tuple(sorted(found))

    def causes(self, proposal: Proposal) -> tuple[str, ...]:
        actors = {key for key in (proposal.actor, proposal.target, proposal.threat) if key}
        if proposal.kind is Action.DEPENDENCY:
            actors.update(self.realm(proposal.actor))
            for lord in self.administrators(proposal.target):
                actors.update(self.realm(lord))
        causes = {self.index.actors[key].origin for key in actors}
        for key in actors:
            causes.update(self.actor_causes(key))
        if proposal.kind is Action.INDEPENDENCE and proposal.target:
            causes.update(self.setbacks(proposal.target, proposal.actor))
        if proposal.kind is Action.PACT and not proposal.threat and proposal.target:
            shared = set(self.groups.get(proposal.actor, ())) & set(
                self.groups.get(proposal.target, ())
            )
            causes.update(item.cause for item in shared)
        if proposal.kind is Action.SECESSION:
            founders = {
                self.founders[key]
                for part in proposal.partitions
                for key in part.districts
                if key in self.founders
            }
            causes.update(self.index.actors[key].origin for key in founders)
        if proposal.kind is Action.REFORM:
            causes.update(
                event.key
                for event in self.experiences[proposal.actor]
                if event.year >= self.state.year - 75 and event.outcome is not Outcome.REFUSED
            )
            authority = proposal.reform.authority if proposal.reform else None
            if (
                authority is not None
                and authority is not self.index.actors[proposal.actor].authority
            ):
                # The neighbours whose institutions the reform adopts (D26).
                causes.update(
                    self.index.actors[other].society_cause
                    for other in self.land_near.get(proposal.actor, set())
                    if self.index.actors[other].living
                    and self.index.actors[other].authority is authority
                )
        if proposal.kind is Action.SEPARATION:
            seats = {part.seat for part in proposal.partitions}
            causes.update(
                self.index.actors[root.key].society_cause
                for root in self.history.foundings
                if seats & set(root.districts)
            )
        return tuple(sorted(causes))

    def actor_causes(self, key: str) -> tuple[str, ...]:
        """A temporal frontier with exactly the same ancestral closure as all facts.

        An event involving this actor already cites its prior snapshot's facts.
        A current fact caused by such an event therefore covers older facts;
        facts from the same round remain explicit because proposals are parallel.
        Created actors are covered by their origin's complete parent context.
        """
        if key not in self.frontiers:
            facts = self.causes_by_actor[key]
            year = max(
                (
                    self.event_years[cause]
                    for cause in facts
                    if (
                        key in self.events[cause].actors
                        and self.events[cause].kind not in {Action.CONFLICT, Action.PRESSURE}
                    )
                    or any(actor.key == key for actor in self.events[cause].effects.created)
                ),
                default=-1,
            )
            self.frontiers[key] = tuple(
                sorted(cause for cause in facts if self.event_years[cause] >= year)
            )
        return self.frontiers[key]


def _burden(context: Context, actor: str, gained: tuple[str, ...] = ()) -> int:
    """Distance, heterogeneity and recent gains consume integration capacity."""
    profile = context.index.actors[actor].society
    seat = context.index.actors[actor].seat
    home = {(pop.culture, pop.religion) for pop in context.index.cohorts(seat)}
    members = context.index.members[actor] | set(gained)
    travel = context.travel(actor, gained)
    cost = 0
    for key in sorted(members):
        context.checkpoint()
        people = context.index.population(key)
        foreign = sum(
            pop.population
            for pop in context.index.cohorts(key)
            if (pop.culture, pop.religion) not in home
        )
        distance = travel.get(key, 1 << 60)
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
    return max(300, 700 + profile.centralization // 4 + livelihood - context.strain(actor) // 3)
