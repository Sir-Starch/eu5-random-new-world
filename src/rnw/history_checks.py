"""Construction invariants shared by history transitions and replay validation."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, final

from rnw.history_model import (
    END,
    PERMILLE,
    START,
    YEARS,
    Action,
    Actor,
    Geography,
    HistoryError,
    Snapshot,
    Tenure,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def require(condition: bool, message: str) -> None:  # noqa: FBT001 - invariant predicate
    if not condition:
        raise HistoryError(message)


def unique(keys: Iterable[str], what: str) -> None:
    counts = Counter(keys)
    require(all(key and count == 1 for key, count in counts.items()), f"Duplicate/empty {what}")


def alive_at(actor: Actor, year: int) -> bool:
    end = actor.ended
    return actor.born <= year and (end is None or year <= end)


@final
class Index:
    """Sparse physical graph and per-actor holdings of one immutable round snapshot."""

    def __init__(
        self, geography: Geography, state: Snapshot, checkpoint: Callable[[], None]
    ) -> None:
        self.geography = geography
        self.places = {place.key: place for place in geography.districts}
        self.actors = {actor.key: actor for actor in state.actors}
        self.owner = {holding.district: holding.actor for holding in state.holdings}
        self.members: dict[str, set[str]] = {actor.key: set() for actor in state.actors}
        for holding in state.holdings:
            require(holding.actor in self.members, "Holding refers to an unknown actor")
            self.members[holding.actor].add(holding.district)
        self.adjacency: dict[str, dict[str, int]] = {key: {} for key in self.places}
        for number, route in enumerate(geography.routes):
            if number % 128 == 0:
                checkpoint()
            if route.sea_steps <= geography.rules.max_sea_steps:
                self.adjacency[route.first][route.second] = route.cost
                self.adjacency[route.second][route.first] = route.cost

    def connected(self, members: set[str], seat: str) -> bool:
        if seat not in members:
            return False
        seen, pending = {seat}, [seat]
        while pending:
            for other in self.adjacency[pending.pop()].keys() & members - seen:
                seen.add(other)
                pending.append(other)
        return seen == members

    def supported(self, actor: Actor, members: set[str]) -> bool:
        if not members or not self.connected(members, actor.seat):
            return False
        if any(self.places[key].tenure != actor.tenure for key in members):
            return False
        if actor.tenure is not Tenure.LAND:
            return True
        rules = self.geography.rules

        def viable(keys: set[str]) -> bool:
            people = sum(self.places[key].population for key in keys)
            farmers = sum(self.places[key].peasants for key in keys)
            return farmers >= rules.minimum_peasants and farmers * PERMILLE >= (
                people * rules.minimum_share
            )

        return viable(members) and viable({actor.seat})


def validate_geography(geography: Geography) -> None:
    unique((place.key for place in geography.districts), "district")
    places = {place.key: place for place in geography.districts}
    rules = geography.rules
    require(
        rules.minimum_peasants > 0
        and 0 < rules.minimum_share <= PERMILLE
        and rules.max_sea_steps >= 0
        and 0 < rules.union_trust <= PERMILLE
        and rules.minimum_overlord_technology >= 0,
        "Invalid history rules",
    )
    pairs: set[tuple[str, str]] = set()
    for place in geography.districts:
        require(bool(place.region) and place.defence > 0, "Invalid district conditions")
        for cohort in place.cohorts:
            require(
                bool(cohort.culture)
                and bool(cohort.religion)
                and 0 <= cohort.peasants <= cohort.population
                and cohort.population > 0,
                "Invalid population cohort",
            )
    for route in geography.routes:
        require(
            route.first in places
            and route.second in places
            and route.first != route.second
            and route.cost > 0
            and route.sea_steps >= 0,
            "Invalid physical route",
        )
        pair = (min(route.first, route.second), max(route.first, route.second))
        require(pair not in pairs, "Duplicate physical route")
        pairs.add(pair)
        require(
            not route.sea_steps or (places[route.first].coastal and places[route.second].coastal),
            "A sea route needs two physical coasts",
        )


def validate_snapshot(index: Index, state: Snapshot) -> None:
    require(START <= state.year <= END and (state.year - START) % YEARS == 0, "Invalid round")
    unique((actor.key for actor in state.actors), "actor")
    unique((holding.district for holding in state.holdings), "holding")
    inhabited = {key for key, place in index.places.items() if place.population > 0}
    require(set(index.owner) == inhabited, "Every inhabited district needs exactly one holder")
    for actor in state.actors:
        require(
            START <= actor.born <= state.year
            and bool(actor.origin)
            and actor.technology >= 0
            and bool(actor.homeland)
            and set(actor.homeland) <= index.places.keys(),
            "Invalid actor lifecycle",
        )
        require(
            all(
                parent in index.actors
                and index.actors[parent].ended == actor.born
                and index.actors[parent].born <= actor.born
                for parent in actor.parents
            ),
            "Invalid predecessor lifecycle",
        )
        if actor.living:
            require(not actor.end_cause, "Living actor has an extinction cause")
            require(
                index.supported(actor, index.members[actor.key]), "Unsupported/disconnected actor"
            )
        else:
            require(
                actor.ended is not None
                and actor.born <= actor.ended <= state.year
                and bool(actor.end_cause)
                and not index.members[actor.key],
                "Extinct actor retains holdings or has an invalid lifecycle",
            )
    living = {actor.key for actor in state.actors if actor.living}
    bond_keys: set[tuple[Action, str, str, str]] = set()
    lords: dict[str, str] = {}
    for bond in state.bonds:
        require(
            bond.first in living and bond.second in living and bond.first != bond.second,
            "Bond needs two living actors",
        )
        key = (bond.kind, bond.first, bond.second, bond.place)
        require(key not in bond_keys and bool(bond.cause), "Duplicate/unexplained bond")
        bond_keys.add(key)
        if bond.kind is Action.DEPENDENCY:
            require(bond.first not in lords, "Subject has more than one overlord")
            lords[bond.first] = bond.second
    for subject in lords:
        seen: set[str] = set()
        current = subject
        while current in lords:
            require(current not in seen, "Dependency cycle")
            seen.add(current)
            current = lords[current]
    require(
        all(
            bond.kind is not Action.PACT or not {bond.first, bond.second} & lords.keys()
            for bond in state.bonds
        ),
        "A subject cannot hold an independent defence pact",
    )
    known: set[tuple[str, str]] = set()
    for knowledge in state.knowledge:
        pair = (knowledge.first, knowledge.second)
        require(
            set(pair) <= living
            and knowledge.first != knowledge.second
            and pair not in known
            and bool(knowledge.cause),
            "Invalid/duplicate knowledge",
        )
        known.add(pair)
    for memory in state.memories:
        require(
            all(
                key in index.actors and alive_at(index.actors[key], memory.year)
                for key in (memory.first, memory.second)
            ),
            "Memory touches an actor outside its lifetime",
        )
        require(
            memory.first in index.actors
            and memory.second in index.actors
            and memory.first != memory.second
            and START <= memory.year <= state.year
            and 0 < memory.weight <= PERMILLE
            and memory.decay >= 0
            and bool(memory.cause),
            "Invalid directed memory",
        )
