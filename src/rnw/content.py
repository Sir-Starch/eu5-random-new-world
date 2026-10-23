"""The content model of a generated New World: who is offered which story or formable, and why not.

Generate geography and societies first; then find the opportunities that world holds (content plan,
N3 and N4): a populous city on a big river, a sacred centre that a state of the same faith holds, a
river basin, a mountain range, a stretch of coast, a related people or a whole region whose centres
lie under several states. This module is the game-independent core of that step. It reads a
``Facts`` description of the finished world and returns a ``ContentPlan``: for each family the
opportunities with their bearers, and for each family that finds none the reason.

Rules the plan keeps:

* Randomness chooses among the *eligible*, never the reverse: a family is never rerolled until a
  preferred analogue appears, and no family has a fixed slot.
* A family that finds no bearer is a result with a recorded reason, not an error; a place or a
  state that does not meet a requirement is never substituted.
* Every draw comes from a stream of its own, derived from the peoples seed and the names of the
  family and of the object (``derive_seed``), so it consumes nothing from the society stream,
  does not depend on the order of the inputs, and adding a family moves no other.
* A place is the centre of at most one story, the territories of one family of formables overlap
  no other of its own (families may overlap: each is a different political path over the same
  land, and the formables' levels order them), and a state bears at most ``MAX_CHAINS`` chains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

RIVER_CENTRE: Final[str] = "river_centre"
SACRED_CENTRE: Final[str] = "sacred_centre"
HARVEST: Final[str] = "harvest"
ROUTE_MARKET: Final[str] = "route_market"
GREAT_ALLIANCE: Final[str] = "great_alliance"
EMPIRE_PERIPHERY: Final[str] = "empire_periphery"
RIVER_UNION: Final[str] = "river_union"
HIGHLAND_CONFEDERATION: Final[str] = "highland_confederation"
MARITIME_LEAGUE: Final[str] = "maritime_league"
CULTURAL_UNION: Final[str] = "cultural_union"
REGIONAL_REALM: Final[str] = "regional_realm"
STORY_FAMILIES: Final[tuple[str, ...]] = (
    RIVER_CENTRE,
    SACRED_CENTRE,
    HARVEST,
    ROUTE_MARKET,
    GREAT_ALLIANCE,
    EMPIRE_PERIPHERY,
)
FORMABLE_FAMILIES: Final[tuple[str, ...]] = (
    RIVER_UNION,
    HIGHLAND_CONFEDERATION,
    MARITIME_LEAGUE,
    CULTURAL_UNION,
    REGIONAL_REALM,
)
FAMILIES: Final[tuple[str, ...]] = (*STORY_FAMILIES, *FORMABLE_FAMILIES)
STATE: Final[str] = "state"
CENTRE_RANKS: Final[frozenset[str]] = frozenset({"city", "town"})
# Above this percentile of the population of the states' places a place is a centre, unless a
# family asks for a lower bar.
CENTRE_CUTOFF: Final[int] = 75
# The smallest river a centre must stand on, in river pixels of its cell.
MIN_RIVER: Final[int] = 1
MAX_RIVER_CENTRES: Final[int] = 4
MAX_SACRED_CENTRES: Final[int] = 4
MAX_HARVESTS: Final[int] = 3
MAX_ROUTES: Final[int] = 3
MAX_ALLIANCES: Final[int] = 3
MAX_EMPIRES: Final[int] = 2
# A harvest story is about a centre among the most populous (this percentile of the states'
# places) or on high ground, where the land around cannot easily feed it.
HUNGRY_CUTOFF: Final[int] = 90
# A route joins two centres of one state that are this many steps apart over its own places.
ROUTE_MIN_STEPS: Final[int] = 2
ROUTE_MAX_STEPS: Final[int] = 8
MAX_UNIONS: Final[int] = 2
MAX_CHAINS: Final[int] = 2
# A union needs room for several centres under several states.
MIN_UNION_PLACES: Final[int] = 12
MIN_UNION_CENTRES: Final[int] = 3
MIN_UNION_STATES: Final[int] = 2
UNION_TERRITORY: Final[int] = 30
MAX_UNION_STATES: Final[int] = 8
# The relief of a highland place, and the share of a confederation's places that must stand on
# high ground (mountains or a plateau), so that a range of low hills is no confederation.
HIGHLAND_RELIEF: Final[frozenset[str]] = frozenset({"mountains", "hills", "plateau"})
HIGH_RELIEF: Final[frozenset[str]] = frozenset({"mountains", "plateau"})
HIGH_SHARE: Final[int] = 34
# A story starts between this many years after 1337 and the same plus its window.
EARLIEST_OFFSET: Final[int] = 3
LATEST_OFFSET: Final[int] = 60
WINDOW_YEARS: Final[int] = 45
CHANCES: Final[tuple[int, ...]] = (2, 3, 4, 5)
START_YEAR: Final[int] = 1337


@dataclass(frozen=True, slots=True)
class Rule:
    """How one family of formables picks its territory and whom it offers it to.

    ``thing`` names what the territory is, for the reason a family gives when it finds none;
    ``cutoff`` is the percentile of the states' places above which a place counts as a centre, a
    lower bar where the land (a range, a coast) holds few cities.
    """

    family: str
    thing: str
    limit: int
    territory: int
    places: int
    centres: int
    states: int
    bearers: int
    cutoff: int = CENTRE_CUTOFF


RULES: Final[Mapping[str, Rule]] = {
    rule.family: rule
    for rule in (
        Rule(
            RIVER_UNION,
            "river basin",
            MAX_UNIONS,
            UNION_TERRITORY,
            MIN_UNION_PLACES,
            MIN_UNION_CENTRES,
            MIN_UNION_STATES,
            MAX_UNION_STATES,
        ),
        Rule(HIGHLAND_CONFEDERATION, "range of highlands", 2, 24, 10, 3, 2, MAX_UNION_STATES, 50),
        Rule(MARITIME_LEAGUE, "stretch of coast", 2, 18, 8, 3, 2, MAX_UNION_STATES, 50),
        Rule(CULTURAL_UNION, "related people", 2, 30, 12, 3, 2, MAX_UNION_STATES),
        Rule(REGIONAL_REALM, "region", 1, 48, 24, 4, 3, MAX_UNION_STATES),
    )
}


@dataclass(frozen=True, slots=True)
class Place:
    """One inhabited generated location and what the plan reads of it.

    ``seas`` are the sea zones the place touches (a coast; empty inland), ``culture`` the culture
    of its main population and ``relief`` its topography.
    """

    key: str
    population: int
    river: int
    rank: str
    religion: str
    owner: str
    relief: str = ""
    culture: str = ""
    seas: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class State:
    """A generated country that owns locations (a tribe holds none and is no bearer)."""

    tag: str
    capital: str
    religion: str


@dataclass(frozen=True, slots=True)
class Facts:
    """What the plan reads: the places, the states, the holy places, the adjacency, the groups.

    ``groups`` maps a culture to the culture groups the game puts it in; ``subjects`` are the
    (overlord, subject) pairs of the start.
    """

    places: Mapping[str, Place]
    states: Mapping[str, State]
    holy: frozenset[str]
    links: frozenset[tuple[str, str]]
    groups: Mapping[str, frozenset[str]] = field(default_factory=dict[str, frozenset[str]])
    subjects: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True, slots=True)
class Start:
    """When a story may begin for its bearer: a window of years and a monthly chance."""

    year: int
    until: int
    chance: int


@dataclass(frozen=True, slots=True)
class Opportunity:
    """One story offered to one state at one place (and, for some, a second place)."""

    family: str
    bearer: str
    centre: str
    start: Start
    other: str = ""

    @property
    def ident(self) -> str:
        """A stable identifier among the opportunities of a world."""
        return f"{self.family}:{self.bearer}"


@dataclass(frozen=True, slots=True)
class Formation:
    """One formable offered to the states whose capitals lie in its territory.

    ``basis`` is what the territory is built on beyond the land itself: the culture group of a
    cultural union, empty for the other families.
    """

    family: str
    index: int
    places: tuple[str, ...]
    centres: tuple[str, ...]
    states: tuple[str, ...]
    seat: str
    basis: str = ""

    @property
    def ident(self) -> str:
        """A stable identifier among the formations of a world."""
        return f"{self.family}:{self.seat}"


@dataclass(frozen=True, slots=True)
class Absence:
    """A family that found no bearer, with the reason."""

    family: str
    reason: str


@dataclass(frozen=True, slots=True)
class ContentPlan:
    """The opportunities of a world and the families that had none."""

    opportunities: tuple[Opportunity, ...]
    formations: tuple[Formation, ...]
    absences: tuple[Absence, ...]

    def count(self) -> dict[str, int]:
        """How many opportunities each family holds."""
        found: dict[str, int] = dict.fromkeys(FAMILIES, 0)
        for opportunity in self.opportunities:
            found[opportunity.family] += 1
        for formation in self.formations:
            found[formation.family] += 1
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


def _centres(facts: Facts, share: int = CENTRE_CUTOFF) -> frozenset[str]:
    """Places that are cities or towns, or among the most populous of the states."""
    owned = [place for place in facts.places.values() if place.owner in facts.states]
    cutoff = _percentile((place.population for place in owned), share)
    return frozenset(
        place.key for place in owned if place.rank in CENTRE_RANKS or place.population >= cutoff
    )


@dataclass(slots=True)
class Tally:
    """What the families already took: places used as centres and chains per state."""

    chains: dict[str, int]
    used: set[str]
    years: dict[str, set[int]]


def _begin(  # noqa: PLR0913 - the stream, the place, its partner, the tally and the claim.
    seed: int, family: str, place: Place, other: str, tally: Tally, *, claim: bool
) -> Opportunity:
    """The opportunity of the owner of ``place`` there: when it begins, and what it takes."""
    owner = place.owner
    start = _start(seed, family, owner)
    taken = tally.years.setdefault(owner, set())
    while start.year in taken:  # a state begins at most one story a year
        start = Start(start.year + 1, start.until + 1, start.chance)
    taken.add(start.year)
    if claim:
        tally.used.add(place.key)
    tally.chains[owner] = tally.chains.get(owner, 0) + 1
    return Opportunity(family, owner, place.key, start, other)


def _chosen(  # noqa: PLR0913 - the candidates, their partner places and the rules of the family.
    seed: int,
    family: str,
    candidates: Iterable[Place],
    limit: int,
    tally: Tally,
    *,
    others: Mapping[str, str] | None = None,
    claim: bool = True,
) -> list[Opportunity]:
    """Up to ``limit`` bearers, one place each, in the order the family's stream gives.

    ``others`` gives a second place for some candidates; a place that ``claim`` takes is the
    centre of no other story, an anchor (a capital) is not.
    """
    ordered = sorted(candidates, key=lambda place: (_rank(seed, family, place.key), place.key))
    found: list[Opportunity] = []
    for place in ordered:
        if len(found) == limit:
            break
        if claim and place.key in tally.used:
            continue
        if tally.chains.get(place.owner, 0) >= MAX_CHAINS:
            continue
        if any(opportunity.bearer == place.owner for opportunity in found):
            continue
        other = (others or {}).get(place.key, "")
        found.append(_begin(seed, family, place, other, tally, claim=claim))
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


def harvest_centres(facts: Facts) -> list[Place]:
    """Centres the land around cannot easily feed: on high ground or among the most populous."""
    centres = _centres(facts)
    owned = [place.population for place in facts.places.values() if place.owner in facts.states]
    cutoff = _percentile(owned, HUNGRY_CUTOFF)
    return [
        place
        for place in facts.places.values()
        if place.key in centres
        and place.owner in facts.states
        and (place.relief in HIGHLAND_RELIEF or place.population >= cutoff)
    ]


def _steps(start: str, reach: Mapping[str, Sequence[str]], limit: int) -> dict[str, int]:
    """How many steps each place within ``limit`` is from ``start``, over the given contacts."""
    steps = {start: 0}
    frontier = [start]
    while frontier:
        following: list[str] = []
        for here in frontier:
            if steps[here] == limit:
                continue
            for other in reach.get(here, ()):
                if other not in steps:
                    steps[other] = steps[here] + 1
                    following.append(other)
        frontier = following
    return steps


def _contacts(facts: Facts) -> dict[str, list[str]]:
    near: dict[str, list[str]] = {key: [] for key in facts.places}
    for first, second in sorted(facts.links):
        near[first].append(second)
        near[second].append(first)
    return near


def routes(facts: Facts, seed: int) -> dict[str, str]:
    """For centres of states, the centre of the same state a route would join them to.

    The two lie ``ROUTE_MIN_STEPS`` to ``ROUTE_MAX_STEPS`` steps apart over places the state
    holds, so there is a real way between them; the other end is drawn from the family's stream.
    """
    centres = _centres(facts)
    near = _contacts(facts)
    found: dict[str, str] = {}
    for key in sorted(centres):
        owner = facts.places[key].owner
        own = {tag: [o for o in near[tag] if facts.places[o].owner == owner] for tag in near}
        steps = _steps(
            key,
            {here: own[here] for here in own if facts.places[here].owner == owner},
            ROUTE_MAX_STEPS,
        )
        ends = [
            other
            for other, count in steps.items()
            if other in centres and count >= ROUTE_MIN_STEPS and other != key
        ]
        if ends:
            found[key] = min(ends, key=lambda other: (_rank(seed, ROUTE_MARKET, key, other), other))
    return found


def alliances(facts: Facts, seed: int) -> dict[str, str]:
    """For the capital of a state, the capital of the neighbour it might form a council with.

    Neighbours share a border and a faith or a main culture, and neither is the other's subject;
    of the several the stream of the pair picks one.
    """
    capital = {tag: facts.places.get(state.capital) for tag, state in facts.states.items()}
    borders: dict[str, set[str]] = {}
    for first, second in facts.links:
        one, two = facts.places[first].owner, facts.places[second].owner
        if one != two and one in facts.states and two in facts.states:
            borders.setdefault(one, set()).add(two)
            borders.setdefault(two, set()).add(one)
    found: dict[str, str] = {}
    for tag in sorted(borders):
        mine = capital[tag]
        if mine is None:
            continue
        options: list[tuple[int, str]] = []
        for neighbour in sorted(borders[tag]):
            theirs = capital[neighbour]
            if (
                theirs is None
                or (tag, neighbour) in facts.subjects
                or (neighbour, tag) in facts.subjects
            ):
                continue
            same_faith = facts.states[tag].religion == facts.states[neighbour].religion
            same_people = bool(mine.culture) and mine.culture == theirs.culture
            if same_faith or same_people:
                options.append((_rank(seed, GREAT_ALLIANCE, tag, neighbour), theirs.key))
        if options:
            found[mine.key] = min(options)[1]
    # two neighbours that would each choose the other make one council, the lower tag's
    seated = {state.capital: tag for tag, state in facts.states.items()}
    return {
        mine: theirs
        for mine, theirs in found.items()
        if not (found.get(theirs) == mine and seated[mine] > seated[theirs])
    }


def peripheries(facts: Facts) -> dict[str, str]:
    """For the capital of a state with subjects, the capital of its most distant subject."""
    near = _contacts(facts)
    found: dict[str, str] = {}
    for tag, state in sorted(facts.states.items()):
        subjects = [
            subject for lord, subject in facts.subjects if lord == tag and subject in facts.states
        ]
        if state.capital not in facts.places or not subjects:
            continue
        steps = _steps(state.capital, near, len(facts.places))
        far = [
            (steps.get(facts.states[subject].capital, -1), facts.states[subject].capital)
            for subject in subjects
            if facts.states[subject].capital in facts.places
        ]
        if far:
            found[state.capital] = max(far, key=lambda item: (item[0], item[1]))[1]
    return found


def _grow(
    seat: str,
    free: set[str],
    near: Mapping[str, Sequence[str]],
    population: Mapping[str, int],
    size: int,
) -> list[str]:
    """Up to ``size`` places joined to ``seat`` through ``free`` ones, the most populous first."""
    order = [seat]
    seen = {seat}
    head = 0
    while head < len(order) and len(order) < size:
        around = sorted(near.get(order[head], ()), key=lambda key: (-population[key], key))
        for other in around:
            if other in free and other not in seen and len(order) < size:
                seen.add(other)
                order.append(other)
        head += 1
    return order


def _adjacency(facts: Facts, family: str) -> dict[str, list[str]]:
    """Which places a territory of ``family`` may step between.

    Land contacts for every family; a league also steps between coastal places that touch the
    same sea zone, which is what joins ports across a bay or a strait.
    """
    near: dict[str, list[str]] = {key: [] for key in facts.places}
    for first, second in sorted(facts.links):
        near[first].append(second)
        near[second].append(first)
    if family == MARITIME_LEAGUE:
        by_sea: dict[str, list[str]] = {}
        for key in sorted(facts.places):
            for sea in sorted(facts.places[key].seas):
                by_sea.setdefault(sea, []).append(key)
        for members in by_sea.values():
            for first in members:
                near[first].extend(second for second in members if second != first)
    return near


def _group_sizes(facts: Facts) -> dict[str, int]:
    """How many places of this world each culture group has."""
    held: dict[str, int] = {}
    for place in facts.places.values():
        for group in facts.groups.get(place.culture, ()):
            held[group] = held.get(group, 0) + 1
    return held


def _culture_group(facts: Facts, culture: str, held: Mapping[str, int], minimum: int) -> str:
    """The narrowest culture group of ``culture`` that this world has ``minimum`` places of."""
    fitting = [
        (held[group], group) for group in facts.groups.get(culture, ()) if held[group] >= minimum
    ]
    return min(fitting)[1] if fitting else ""


def _served(facts: Facts, family: str, group: str = "") -> set[str]:
    """The places a territory of ``family`` may take in (the group fixes a cultural union's)."""
    places = facts.places
    if family == RIVER_UNION:
        return {key for key, place in places.items() if place.river >= MIN_RIVER}
    if family == HIGHLAND_CONFEDERATION:
        return {key for key, place in places.items() if place.relief in HIGHLAND_RELIEF}
    if family == MARITIME_LEAGUE:
        return {key for key, place in places.items() if place.seas}
    if family == CULTURAL_UNION:
        return {
            key for key, place in places.items() if group in facts.groups.get(place.culture, ())
        }
    return set(places)


def _states_text(count: int) -> str:
    return "more than one state" if count == 2 else f"at least {count} states"  # noqa: PLR2004


def _obstacle(
    facts: Facts, rule: Rule, territory: Sequence[str], centres: frozenset[str]
) -> tuple[str, dict[str, int]]:
    """Why ``territory`` cannot be a formable of ``rule`` (empty if it can) and who owns it."""
    owners: dict[str, int] = {}
    for key in territory:
        owner = facts.places[key].owner
        if owner in facts.states:
            owners[owner] = owners.get(owner, 0) + 1
    high = sum(1 for key in territory if facts.places[key].relief in HIGH_RELIEF)
    if sum(1 for key in territory if key in centres) < rule.centres:
        return f"no {rule.thing} holds enough centres", owners
    if rule.family == HIGHLAND_CONFEDERATION and high * 100 < len(territory) * HIGH_SHARE:
        return f"no {rule.thing} has enough high ground", owners
    if len(owners) < rule.states:
        return f"no {rule.thing} lies under {_states_text(rule.states)}", owners
    seated = sum(1 for tag in owners if facts.states[tag].capital in territory)
    if seated < rule.states:
        return f"no {rule.thing} holds the capitals of {_states_text(rule.states)}", owners
    return "", owners


def formations(facts: Facts, seed: int, family: str) -> tuple[list[Formation], str]:
    """The formables of ``family`` with room for them, and why there is none when there is none.

    A territory grows from a centre along the places the family serves, so it is connected and its
    states are neighbours. The seat is drawn from a stream of the family's own; a seat that cannot
    hold the family's minimums is passed over, and the last obstacle met is the reason given.
    """
    rule = RULES[family]
    centres = _centres(facts, rule.cutoff)
    population = {key: place.population for key, place in facts.places.items()}
    near = _adjacency(facts, family)
    cultural = family == CULTURAL_UNION
    served: set[str] = set() if cultural else _served(facts, family)
    held = _group_sizes(facts) if cultural else {}
    by_group: dict[str, set[str]] = {}
    seats = sorted(
        (key for key in centres if cultural or key in served),
        key=lambda key: (_rank(seed, family, key), key),
    )
    reason = f"no {rule.thing} joins enough populated places"
    taken: set[str] = set()
    chosen: list[Formation] = []
    for seat in seats:
        if len(chosen) == rule.limit:
            break
        if seat in taken:
            continue
        group = ""
        if cultural:
            group = _culture_group(facts, facts.places[seat].culture, held, rule.places)
            if not group:
                reason = f"no {rule.thing} has enough places of one culture group"
                continue
            served = by_group.setdefault(group, _served(facts, family, group))
        territory = _grow(seat, served - taken, near, population, rule.territory)
        if len(territory) < rule.places:
            continue
        obstacle, owners = _obstacle(facts, rule, territory, centres)
        if obstacle:
            reason = obstacle
            continue
        seated = {tag for tag in owners if facts.states[tag].capital in territory}
        ranked = sorted(seated, key=lambda tag: (-owners[tag], tag))[: rule.bearers]
        taken.update(territory)
        inside = tuple(key for key in territory if key in centres)
        chosen.append(
            Formation(
                family,
                len(chosen),
                tuple(sorted(territory)),
                inside,
                tuple(sorted(ranked)),
                seat,
                group,
            )
        )
    return chosen, reason


def plan_content(facts: Facts, seed: int) -> ContentPlan:
    """The opportunities of a world.

    ``seed`` is the peoples seed of the world. The result depends on the facts and the seed
    only, whatever the order in which the facts are given.
    """
    tally = Tally({}, set(), {})
    absences: list[Absence] = []
    stories: list[Opportunity] = []

    def take(family: str, found: list[Opportunity], reason: str) -> None:
        stories.extend(found)
        if not found:
            absences.append(Absence(family, reason))

    take(
        RIVER_CENTRE,
        _chosen(seed, RIVER_CENTRE, river_centres(facts), MAX_RIVER_CENTRES, tally),
        "no centre of a state lies on a river",
    )
    take(
        SACRED_CENTRE,
        _chosen(seed, SACRED_CENTRE, sacred_centres(facts), MAX_SACRED_CENTRES, tally),
        "no holy place lies in a state of its own faith",
    )
    take(
        HARVEST,
        _chosen(seed, HARVEST, harvest_centres(facts), MAX_HARVESTS, tally),
        "no centre of a state lies on high ground or among the most populous",
    )
    joined = routes(facts, seed)
    take(
        ROUTE_MARKET,
        _chosen(
            seed,
            ROUTE_MARKET,
            [facts.places[key] for key in joined],
            MAX_ROUTES,
            tally,
            others=joined,
        ),
        "no state holds two centres joined by places of its own",
    )
    paired = alliances(facts, seed)
    take(
        GREAT_ALLIANCE,
        _chosen(
            seed,
            GREAT_ALLIANCE,
            [facts.places[key] for key in paired],
            MAX_ALLIANCES,
            tally,
            others=paired,
            claim=False,
        ),
        "no two neighbouring states share a faith or a people",
    )
    far = peripheries(facts)
    take(
        EMPIRE_PERIPHERY,
        _chosen(
            seed,
            EMPIRE_PERIPHERY,
            [facts.places[key] for key in far],
            MAX_EMPIRES,
            tally,
            others=far,
            claim=False,
        ),
        "no state holds subjects",
    )
    formable: list[Formation] = []
    for family in FORMABLE_FAMILIES:
        found, reason = formations(facts, seed, family)
        formable.extend(found)
        if not found:
            absences.append(Absence(family, reason))
    return ContentPlan(tuple(stories), tuple(formable), tuple(absences))
