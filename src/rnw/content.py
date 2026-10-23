"""The content model of a generated New World: who is offered which story or formable, and why not.

Generate geography and societies first; then find the opportunities that world holds (content plan,
N3): a populous city on a big river, a sacred centre that a state of the same faith holds, a river
basin whose centres lie under several states. This module is the game-independent core of that
step. It reads a ``Facts`` description of the finished world and returns a ``ContentPlan``: for
each family the opportunities with their bearers, and for each family that finds none the reason.

Rules the plan keeps:

* Randomness chooses among the *eligible*, never the reverse: a family is never rerolled until a
  preferred analogue appears, and no family has a fixed slot.
* A family that finds no bearer is a result with a recorded reason, not an error; a place or a
  state that does not meet a requirement is never substituted.
* Every draw comes from a stream of its own, derived from the peoples seed and the names of the
  family and of the object (``derive_seed``), so it consumes nothing from the society stream,
  does not depend on the order of the inputs, and adding a family moves no other.
* A place is the centre of at most one story, a union's territory overlaps no other union's, and a
  state bears at most ``MAX_CHAINS`` chains.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

RIVER_CENTRE: Final[str] = "river_centre"
SACRED_CENTRE: Final[str] = "sacred_centre"
RIVER_UNION: Final[str] = "river_union"
FAMILIES: Final[tuple[str, ...]] = (RIVER_CENTRE, SACRED_CENTRE, RIVER_UNION)
STATE: Final[str] = "state"
CENTRE_RANKS: Final[frozenset[str]] = frozenset({"city", "town"})
# The smallest river a centre must stand on, in river pixels of its cell.
MIN_RIVER: Final[int] = 1
MAX_RIVER_CENTRES: Final[int] = 4
MAX_SACRED_CENTRES: Final[int] = 4
MAX_UNIONS: Final[int] = 2
MAX_CHAINS: Final[int] = 2
# A union needs room for several centres under several states.
MIN_UNION_PLACES: Final[int] = 12
MIN_UNION_CENTRES: Final[int] = 3
MIN_UNION_STATES: Final[int] = 2
UNION_TERRITORY: Final[int] = 30
MAX_UNION_STATES: Final[int] = 8
# A story starts between this many years after 1337 and the same plus its window.
EARLIEST_OFFSET: Final[int] = 3
LATEST_OFFSET: Final[int] = 60
WINDOW_YEARS: Final[int] = 45
CHANCES: Final[tuple[int, ...]] = (2, 3, 4, 5)
START_YEAR: Final[int] = 1337


@dataclass(frozen=True, slots=True)
class Place:
    """One inhabited generated location and what the plan reads of it."""

    key: str
    population: int
    river: int
    rank: str
    religion: str
    owner: str


@dataclass(frozen=True, slots=True)
class State:
    """A generated country that owns locations (a tribe holds none and is no bearer)."""

    tag: str
    capital: str
    religion: str


@dataclass(frozen=True, slots=True)
class Facts:
    """What the plan reads: the places, the states, the holy places and the adjacency."""

    places: Mapping[str, Place]
    states: Mapping[str, State]
    holy: frozenset[str]
    links: frozenset[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class Start:
    """When a story may begin for its bearer: a window of years and a monthly chance."""

    year: int
    until: int
    chance: int


@dataclass(frozen=True, slots=True)
class Opportunity:
    """One story offered to one state at one place."""

    family: str
    bearer: str
    centre: str
    start: Start

    @property
    def ident(self) -> str:
        """A stable identifier among the opportunities of a world."""
        return f"{self.family}:{self.bearer}"


@dataclass(frozen=True, slots=True)
class Union:
    """One river-basin union offered to the states whose capitals lie in its basin."""

    index: int
    places: tuple[str, ...]
    centres: tuple[str, ...]
    states: tuple[str, ...]
    seat: str

    @property
    def ident(self) -> str:
        """A stable identifier among the unions of a world."""
        return f"{RIVER_UNION}:{self.seat}"


@dataclass(frozen=True, slots=True)
class Absence:
    """A family that found no bearer, with the reason."""

    family: str
    reason: str


@dataclass(frozen=True, slots=True)
class ContentPlan:
    """The opportunities of a world and the families that had none."""

    opportunities: tuple[Opportunity, ...]
    unions: tuple[Union, ...]
    absences: tuple[Absence, ...]

    def count(self) -> dict[str, int]:
        """How many opportunities each family holds."""
        found: dict[str, int] = dict.fromkeys(FAMILIES, 0)
        for opportunity in self.opportunities:
            found[opportunity.family] += 1
        found[RIVER_UNION] = len(self.unions)
        return found


def _rank(seed: int, family: str, *labels: str) -> int:
    """A number for ordering candidates, from a stream named by family and object."""
    return derive_seed(seed, "content", family, *labels)


def _percentile(values: Iterable[int], share: int) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, len(ordered) * share // 100)] if ordered else 0


def _start(seed: int, family: str, bearer: str) -> Start:
    """When the story of ``bearer`` may begin, drawn from the stream of its own."""
    draw = _rank(seed, family, bearer, "start")
    span = LATEST_OFFSET - EARLIEST_OFFSET + 1
    year = START_YEAR + EARLIEST_OFFSET + draw % span
    chance = CHANCES[(draw >> 20) % len(CHANCES)]
    return Start(year, year + WINDOW_YEARS, chance)


def _centres(facts: Facts) -> frozenset[str]:
    """Places that are cities or towns, or among the most populous of the states."""
    owned = [place for place in facts.places.values() if place.owner in facts.states]
    cutoff = _percentile((place.population for place in owned), 75)
    return frozenset(
        place.key for place in owned if place.rank in CENTRE_RANKS or place.population >= cutoff
    )


@dataclass(slots=True)
class Tally:
    """What the families already took: places used as centres and chains per state."""

    chains: dict[str, int]
    used: set[str]
    years: dict[str, set[int]]


def _chosen(
    seed: int, family: str, candidates: Iterable[Place], limit: int, tally: Tally
) -> list[Opportunity]:
    """Up to ``limit`` bearers, one place each, in the order the family's stream gives."""
    ordered = sorted(candidates, key=lambda place: (_rank(seed, family, place.key), place.key))
    found: list[Opportunity] = []
    for place in ordered:
        if len(found) == limit:
            break
        if place.key in tally.used or tally.chains.get(place.owner, 0) >= MAX_CHAINS:
            continue
        if any(opportunity.bearer == place.owner for opportunity in found):
            continue
        start = _start(seed, family, place.owner)
        taken = tally.years.setdefault(place.owner, set())
        while start.year in taken:  # a state begins at most one story a year
            start = Start(start.year + 1, start.until + 1, start.chance)
        taken.add(start.year)
        found.append(Opportunity(family, place.owner, place.key, start))
        tally.used.add(place.key)
        tally.chains[place.owner] = tally.chains.get(place.owner, 0) + 1
    return found


def river_centres(facts: Facts) -> list[Place]:
    """Places eligible as the centre of a river story: a state's centre on a river."""
    centres = _centres(facts)
    return [
        place
        for place in facts.places.values()
        if place.key in centres and place.river >= MIN_RIVER and place.owner in facts.states
    ]


def sacred_centres(facts: Facts) -> list[Place]:
    """Places eligible as a sacred centre: a holy place held by a state of its faith."""
    found: list[Place] = []
    for key in sorted(facts.holy):
        place = facts.places.get(key)
        state = facts.states.get(place.owner) if place is not None else None
        if place is not None and state is not None and state.religion == place.religion:
            found.append(place)
    return found


def _grow(
    seat: str, free: set[str], near: Mapping[str, Sequence[str]], population: Mapping[str, int]
) -> list[str]:
    """Up to ``UNION_TERRITORY`` places joined to ``seat`` through ``free`` ones, nearest first."""
    order = [seat]
    seen = {seat}
    head = 0
    while head < len(order) and len(order) < UNION_TERRITORY:
        around = sorted(near.get(order[head], ()), key=lambda key: (-population[key], key))
        for other in around:
            if other in free and other not in seen and len(order) < UNION_TERRITORY:
                seen.add(other)
                order.append(other)
        head += 1
    return order


def river_unions(facts: Facts, seed: int) -> tuple[list[Union], str]:
    """River basins with room for a union, and why there is none when there is none.

    A union grows from a centre along the places a river serves, up to ``UNION_TERRITORY`` of
    them, so its territory is connected and its states are its neighbours.
    """
    served = {key for key, place in facts.places.items() if place.river >= MIN_RIVER}
    population = {key: place.population for key, place in facts.places.items()}
    centres = _centres(facts)
    near: dict[str, list[str]] = {key: [] for key in served}
    for first, second in sorted(facts.links):
        if first in served and second in served:
            near[first].append(second)
            near[second].append(first)
    seats = sorted(
        (key for key in served if key in centres),
        key=lambda key: (_rank(seed, RIVER_UNION, key), key),
    )
    reason = "no river basin joins enough populated places"
    taken: set[str] = set()
    chosen: list[Union] = []
    for seat in seats:
        if len(chosen) == MAX_UNIONS:
            break
        if seat in taken:
            continue
        territory = _grow(seat, served - taken, near, population)
        if len(territory) < MIN_UNION_PLACES:
            continue
        held = [key for key in territory if key in centres]
        owners: dict[str, int] = {}
        for key in territory:
            owner = facts.places[key].owner
            if owner in facts.states:
                owners[owner] = owners.get(owner, 0) + 1
        if len(held) < MIN_UNION_CENTRES:
            reason = "no river basin holds enough centres"
            continue
        if len(owners) < MIN_UNION_STATES:
            reason = "no river basin lies under more than one state"
            continue
        seated = {tag for tag in owners if facts.states[tag].capital in territory}
        if len(seated) < MIN_UNION_STATES:
            reason = "no river basin holds the capitals of more than one state"
            continue
        ranked = sorted(seated, key=lambda tag: (-owners[tag], tag))[:MAX_UNION_STATES]
        taken.update(territory)
        chosen.append(
            Union(len(chosen), tuple(sorted(territory)), tuple(held), tuple(sorted(ranked)), seat)
        )
    return chosen, reason


def plan_content(facts: Facts, seed: int) -> ContentPlan:
    """The opportunities of a world.

    ``seed`` is the peoples seed of the world. The result depends on the facts and the seed
    only, whatever the order in which the facts are given.
    """
    tally = Tally({}, set(), {})
    absences: list[Absence] = []
    river = _chosen(seed, RIVER_CENTRE, river_centres(facts), MAX_RIVER_CENTRES, tally)
    if not river:
        absences.append(Absence(RIVER_CENTRE, "no centre of a state lies on a river"))
    sacred = _chosen(seed, SACRED_CENTRE, sacred_centres(facts), MAX_SACRED_CENTRES, tally)
    if not sacred:
        absences.append(Absence(SACRED_CENTRE, "no holy place lies in a state of its own faith"))
    unions, reason = river_unions(facts, seed)
    if not unions:
        absences.append(Absence(RIVER_UNION, reason))
    return ContentPlan(tuple(river + sacred), tuple(unions), tuple(absences))
