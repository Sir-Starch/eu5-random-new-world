"""Extraordinary societies other than the great empire: who forms one (R7d).

NOT GAME VALIDATED. Game-independent: the input is what the generated peoples look like (one entry
per polity), the output the groups of polities that form a sea league, a highland confederation, a
fractured realm or a sacred centre. An archetype follows geography and social structure, and
randomness only chooses among suitable combinations [content plan, R7d]:

* **Sea league.** Three to five states with a port on one sea zone, at least two of them parted by
  land (the sea joins what the land does not). Strength: ports, trade, the republic. Weakness: the
  members are allied, not led, and are separated by water.
* **Highland confederation.** Three to six touching tribes of one religion zone on hills, mountains
  or plateau, as populous per location as vanilla's confederates. Strength: the confederation's
  mutual defence. Weakness: no head, no technology.
* **Fractured realm.** Three or four touching states of one religion zone and complex capitals,
  none dominant, holding together the land of an empire. Strength: one faith in a dense region.
  Weakness: every centre is the rival of its neighbours.
* **Sacred centre.** The state that holds the most populous location of a religion zone, if it is
  among the most populous quarter of the states, with two or three neighbouring states of the
  same religion as competitors. Strength: the faith's capital. Weakness: the competitors are its
  rivals.

Which of these a world gets is drawn once per hearth, by the hearths' own stream: the chance is the
rare-empire control (``empire_permille``), so a chance of 0 leaves every byte of a world without
them. All arithmetic is integer; the numbers below are design choices [INFERRED design].
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, Final

from rnw.rng import SplitMix64, derive_seed
from rnw.societies import EMPIRE_FLOOR

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

SEA_LEAGUE: Final[str] = "sea_league"
HIGHLAND_CONFEDERATION: Final[str] = "highland_confederation"
FRACTURED_REALM: Final[str] = "fractured_realm"
SACRED_CENTRE: Final[str] = "sacred_centre"
KINDS: Final[tuple[str, ...]] = (
    SEA_LEAGUE,
    HIGHLAND_CONFEDERATION,
    FRACTURED_REALM,
    SACRED_CENTRE,
)
PERMILLE: Final[int] = 1000
# Members of a group: (least, most).
LEAGUE_MEMBERS: Final[tuple[int, int]] = (3, 5)
CONFEDERATES: Final[tuple[int, int]] = (3, 6)
REALM_MEMBERS: Final[tuple[int, int]] = (3, 4)
COMPETITORS: Final[tuple[int, int]] = (2, 3)
# A tribe is highland if this share of its locations lies on hills, mountains or plateau. The
# five Haudenosaunee nations of vanilla's confederation hold 3 to 11 locations each.
HIGHLAND_PERMILLE: Final[int] = 600
# No centre of a fractured realm is more than this many times as populous as the biggest.
REALM_RATIO: Final[int] = 3
# Together the centres hold the land a great empire takes at least.
REALM_LOCATIONS: Final[int] = EMPIRE_FLOOR
# The state of a sacred centre is among the most populous quarter of the free states.
CENTRE_QUANTILE: Final[int] = 750
# The capital of every centre of a fractured realm is at least this complex: the realm lies where
# an empire could have risen.
REALM_COMPLEXITY: Final[int] = 500


@dataclass(frozen=True, slots=True, eq=False)
class Structure:
    """What the selection reads of the generated peoples: one entry per polity.

    ``state`` tells a state from a tribe and ``free`` whether the polity may join a group (it is
    no great empire and no lord or vassal). ``level`` is the starting technology level of a state.
    ``locations`` is the number of locations, ``near`` holds the polities in land contact,
    ``religion`` the religion zone of the capital,
    ``complexity`` the permille of the capital, ``highland`` the permille of locations on hills,
    mountains or plateau, ``ports`` for each sea zone a polity touches its most populous location
    there, ``domain`` the domain of the capital (``domains`` of them) and ``cradle`` the polities
    that hold the most populous location of a religion zone.
    """

    state: Sequence[bool]
    free: Sequence[bool]
    level: Sequence[int]
    population: Sequence[int]
    locations: Sequence[int]
    near: Sequence[Collection[int]]
    religion: Sequence[int]
    complexity: Sequence[int]
    highland: Sequence[int]
    ports: Sequence[Mapping[int, int]]
    domain: Sequence[int]
    domains: int
    cradle: frozenset[int]


@dataclass(frozen=True, slots=True)
class Rules:
    """What the vanilla data sets for the selection: the republic's level and the confederates'
    population per location (milli-pops)."""

    level: int
    density: int


@dataclass(frozen=True, slots=True)
class Group:
    """One extraordinary society: its polities (the hub first, then by falling population)."""

    kind: str
    hub: int
    members: tuple[int, ...]
    domain: int
    zone: int = -1
    ports: tuple[int, ...] = ()


def _ranked(structure: Structure, nodes: Collection[int]) -> list[int]:
    """The polities by falling population, ties by number."""
    return sorted(nodes, key=lambda n: (-structure.population[n], n))


def _group(structure: Structure, kind: str, nodes: Collection[int], zone: int = -1) -> Group:
    members = _ranked(structure, nodes)
    return Group(kind, members[0], tuple(members), structure.domain[members[0]], zone)


def _density(structure: Structure, group: Group) -> int:
    """Milli-pops a location of the group's polities hold."""
    return sum(structure.population[n] for n in group.members) // sum(
        structure.locations[n] for n in group.members
    )


def sea_leagues(structure: Structure, level: int) -> list[Group]:
    """Groups of states with a port on one sea zone, the sea joining at least two the land parts.

    A state needs the technology ``level`` of the republic's template. Of the states at a zone
    the most populous few form the league; each member's port there, its most populous location
    on the zone, is where the league trades.
    """
    at_zone: defaultdict[int, list[int]] = defaultdict(list)
    for node, is_state in enumerate(structure.state):
        if is_state and structure.free[node] and structure.level[node] >= level:
            for zone in structure.ports[node]:
                at_zone[zone].append(node)
    found: dict[tuple[int, ...], Group] = {}
    for zone in sorted(at_zone):
        members = _ranked(structure, at_zone[zone])[: LEAGUE_MEMBERS[1]]
        apart = any(b not in structure.near[a] for a, b in combinations(members, 2))
        key = tuple(sorted(members))
        if len(members) >= LEAGUE_MEMBERS[0] and apart and key not in found:
            group = _group(structure, SEA_LEAGUE, members, zone)
            ports = tuple(structure.ports[member][zone] for member in group.members)
            found[key] = Group(group.kind, group.hub, group.members, group.domain, zone, ports)
    return list(found.values())


def highland_confederations(structure: Structure, density: int) -> list[Group]:
    """Groups of touching highland tribes of one religion zone, grown from the most populous.

    A group holds ``density`` milli-pops a location at least.
    """
    eligible = {
        node
        for node, is_state in enumerate(structure.state)
        if not is_state and structure.free[node] and structure.highland[node] >= HIGHLAND_PERMILLE
    }
    seen: set[int] = set()
    found: list[Group] = []
    for start in _ranked(structure, eligible):
        if start in seen:
            continue
        component = {start}
        stack = [start]
        while stack:
            for other in structure.near[stack.pop()]:
                if (
                    other in eligible
                    and other not in component
                    and structure.religion[other] == structure.religion[start]
                ):
                    component.add(other)
                    stack.append(other)
        seen |= component
        if len(component) < CONFEDERATES[0]:
            continue
        members = [start]
        while len(members) < min(len(component), CONFEDERATES[1]):
            border = {
                other
                for member in members
                for other in structure.near[member]
                if other in component and other not in members
            }
            members.append(_ranked(structure, border)[0])
        group = _group(structure, HIGHLAND_CONFEDERATION, members)
        if _density(structure, group) >= density:
            found.append(group)
    return found


def fractured_realms(structure: Structure) -> list[Group]:
    """Groups of touching states of one religion zone around the most populous, none dominant."""
    eligible = {
        node
        for node, is_state in enumerate(structure.state)
        if is_state and structure.free[node] and structure.complexity[node] >= REALM_COMPLEXITY
    }
    found: dict[tuple[int, ...], Group] = {}
    for start in _ranked(structure, eligible):
        peers = _ranked(
            structure,
            {
                other
                for other in structure.near[start]
                if other in eligible
                and structure.religion[other] == structure.religion[start]
                and REALM_RATIO * structure.population[other] >= structure.population[start]
            },
        )
        members = [start, *peers[: REALM_MEMBERS[1] - 1]]
        key = tuple(sorted(members))
        if (
            len(members) >= REALM_MEMBERS[0]
            and sum(structure.locations[n] for n in members) >= REALM_LOCATIONS
            and key not in found
        ):
            found[key] = _group(structure, FRACTURED_REALM, members)
    return list(found.values())


def sacred_centres(structure: Structure) -> list[Group]:
    """The cradle states of a religion with two or three neighbouring states of its faith.

    The state is among the most populous quarter of the free states.
    """
    known = sorted(
        structure.population[n]
        for n, is_state in enumerate(structure.state)
        if is_state and structure.free[n]
    )
    great = known[len(known) * CENTRE_QUANTILE // PERMILLE] if known else 0
    found: list[Group] = []
    for hub in sorted(structure.cradle):
        if not (structure.state[hub] and structure.free[hub]) or structure.population[hub] < great:
            continue
        rivals = _ranked(
            structure,
            {
                other
                for other in structure.near[hub]
                if structure.state[other]
                and structure.free[other]
                and structure.religion[other] == structure.religion[hub]
            },
        )[: COMPETITORS[1]]
        if len(rivals) >= COMPETITORS[0]:
            found.append(Group(SACRED_CENTRE, hub, (hub, *rivals), structure.domain[hub]))
    return found


def options(structure: Structure, rules: Rules) -> dict[str, list[Group]]:
    """Every group the world allows, by kind, the biggest first (ties by hub)."""
    found = {
        SEA_LEAGUE: sea_leagues(structure, rules.level),
        HIGHLAND_CONFEDERATION: highland_confederations(structure, rules.density),
        FRACTURED_REALM: fractured_realms(structure),
        SACRED_CENTRE: sacred_centres(structure),
    }
    return {
        kind: sorted(
            groups,
            key=lambda g: (-sum(structure.population[n] for n in g.members), g.hub, g.members),
        )
        for kind, groups in found.items()
    }


def plan_archetypes(
    structure: Structure, rules: Rules, *, chance: int, seed: int
) -> tuple[Group, ...]:
    """The extraordinary societies of a world: at most one for each hearth's domain.

    A stream of its own draws three numbers for every domain whether or not anything rises: the
    chance, the kind among those the domain allows and the group among those of the kind. A chance
    of 0 therefore chooses nothing, and a higher one chooses in the same domains and more. A
    group never takes a polity an earlier one holds.
    """
    rng = SplitMix64(derive_seed(seed, "archetypes"))
    found = options(structure, rules)
    taken: set[int] = set()
    chosen: list[Group] = []
    for domain in range(structure.domains):
        draw, kind_pick, group_pick = (rng.below(PERMILLE) for _ in range(3))
        if draw >= chance:
            continue
        available = {
            kind: [
                group
                for group in found[kind]
                if group.domain == domain and not taken.intersection(group.members)
            ]
            for kind in KINDS
        }
        kinds = [kind for kind in KINDS if available[kind]]
        if not kinds:
            continue
        pool = available[kinds[kind_pick * len(kinds) // PERMILLE]]
        group = pool[group_pick * len(pool) // PERMILLE]
        chosen.append(group)
        taken.update(group.members)
    return tuple(chosen)


def alliance_pairs(group: Group) -> tuple[tuple[int, int], ...]:
    """The alliances of a sea league: a ring from the hub through the members and back.

    Every member holds two. Counts alone do not bound vanilla's variable alliance upkeep
    (TR46-L07; experiment 059). A group has at least three members, so the pairs are distinct.
    """
    if group.kind != SEA_LEAGUE:
        return ()
    members = group.members
    ring = (
        (min(a, b), max(a, b)) for a, b in zip(members, (*members[1:], members[0]), strict=True)
    )
    return tuple(sorted(ring))


def rival_pairs(group: Group, near: Sequence[Collection[int]]) -> tuple[tuple[int, int], ...]:
    """Directed rivalries: each touching pair of a fractured realm, the centre and each competitor.

    Both directions are listed, as vanilla's Burke feud lists them.
    """
    if group.kind == FRACTURED_REALM:
        pairs = [(a, b) for a, b in combinations(group.members, 2) if b in near[a]]
    elif group.kind == SACRED_CENTRE:
        pairs = [(group.hub, other) for other in group.members[1:]]
    else:
        return ()
    return tuple(sorted({*pairs, *((b, a) for a, b in pairs)}))
