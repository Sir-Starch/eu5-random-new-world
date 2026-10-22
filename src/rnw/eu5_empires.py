"""Great empires with causes and weaknesses (R7c).

NOT GAME VALIDATED. A great empire used to be only large: 58 locations and the first pick of
vassals, with the level and the template of an ordinary state, no rank, no roads and no weakness
[V-EXEC C156]. Each cause and weakness below uses a mechanism that the vanilla 1337 setup already
uses, in the Americas or, for roads, in the Old World [V-LOCAL C158]:

* **Technology.** The empire level is ``min(T, S + 1)``, ``T`` the highest level any vanilla
  template or country entry gives and ``S`` the highest vanilla American state level.
* **Rank.** ``country_rank`` of the highest rank a vanilla American landed country starts with.
* **Royal roads.** ``road_network`` pairs on the shortest land routes from the capital to the
  capitals of its vassals, its ranked and market locations and the most populous location of every
  area it holds. All 1,646 vanilla pairs join locations in pixel contact, so only contacts are used.
* **Fear.** The independent states in land contact hold ``opinion_threatens_conquest`` of the
  empire and it holds ``opinion_prey_to_conquest`` of them (the Andes block of ``18_opinions``).
* **Resentment.** Its vassals hold ``opinion_tyrant_overlord`` of it and it holds
  ``opinion_irritated`` of them (the Mayapan block).
* **Knowledge.** The holder of an opinion has discovered the area of its partner's capital, as
  every country of vanilla's Andes block has through its regional exploration template (C170).

Diversity (the pops keep the cultures and religions of the zones the empire spans) and reach
(control falls with distance from the capital [INFERRED]) write nothing; they are reported.
Pure functions on texts and lists, like ``eu5_development``; all arithmetic is integer.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_technology import american_states
from rnw.pdx import Block, parse
from rnw.societies import PERMILLE, STEP_COST, land_routes, trunk_roads

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.societies import LandGraph

FEAR: Final[str] = "opinion_threatens_conquest"
PREY: Final[str] = "opinion_prey_to_conquest"
TYRANT: Final[str] = "opinion_tyrant_overlord"
IRRITATED: Final[str] = "opinion_irritated"
OPINION_TYPES: Final[tuple[str, ...]] = (FEAR, PREY, TYRANT, IRRITATED)
HEADER: Final[str] = "\n\t# RNW generated natives\n"
# Keys of a country entry that name locations the country owns or controls.
OWNING: Final[tuple[str, ...]] = (
    "own_control_core",
    "own_control_integrated",
    "own_control_conquered",
    "own_control_colony",
    "own_core",
    "control",
)
ROAD_PERCENTILE: Final[int] = 90
LARGEST: Final[int] = 5


class EmpireError(ValueError):
    """Vanilla data a great empire is calibrated on is missing or inconsistent."""


@dataclass(frozen=True, slots=True)
class VanillaState:
    """A vanilla American state, for comparison: its locations and pops outside its culture."""

    tag: str
    locations: int
    foreign_culture_permille: int


@dataclass(frozen=True, slots=True)
class EmpireCalibration:
    """What the vanilla data gives a great empire: level, rank, road bound and its opinions."""

    level: int
    rank: str
    road_permille: int
    opinions: tuple[str, ...]
    largest: tuple[VanillaState, ...] = ()


def highest_level(levels: Mapping[str, int], setup_text: str) -> int:
    """The highest starting technology level any template or country entry gives (T)."""
    holder = parse(setup_text).block("countries", "countries")
    found = list(levels.values())
    for entry in holder.entries if holder is not None else []:
        own = (
            entry.value.first("starting_technology_level")
            if isinstance(entry.value, Block)
            else None
        )
        if own is not None and isinstance(own.value, str) and own.value.isdigit():
            found.append(int(own.value))
    if not found:
        message = "No vanilla template or country gives a starting technology level"
        raise EmpireError(message)
    return max(found)


def rank_levels(texts: Sequence[str]) -> dict[str, int]:
    """Level of each country rank of ``in_game/common/country_ranks``."""
    ranks: dict[str, int] = {}
    for text in texts:
        for entry in parse(text).entries:
            level = entry.value.first("level") if isinstance(entry.value, Block) else None
            if (
                entry.key
                and level is not None
                and isinstance(level.value, str)
                and level.value.isdigit()
            ):
                ranks[entry.key] = int(level.value)
    return ranks


def american_rank(setup_text: str, ranks: Mapping[str, int], american: Collection[str]) -> str:
    """The highest rank any vanilla American landed country starts with."""
    held: set[str] = set()
    for _, block in american_states(setup_text, american):
        rank = block.first("country_rank")
        if rank is not None and isinstance(rank.value, str):
            held.add(rank.value)
    unknown = sorted(held - set(ranks))
    if unknown:
        message = f"Rank {unknown[0]} of a vanilla American country is not a country rank"
        raise EmpireError(message)
    if not held:
        message = "No vanilla American landed country starts with a country rank"
        raise EmpireError(message)
    return min(held, key=lambda name: (-ranks[name], name))


def defined_biases(texts: Sequence[str]) -> frozenset[str]:
    """Keys of the biases of ``in_game/common/biases``."""
    return frozenset(
        entry.key
        for text in texts
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    )


def road_density(setup_text: str, roads_text: str) -> int:
    """The 90th percentile, in permille, of road pairs per owned location among vanilla countries.

    A pair belongs to the country that owns its first location; only countries with a pair
    count. Vanilla's Old World roads give 1,000 on 1.4.3 [V-EXEC C158].
    """
    roads = parse(roads_text).block("road_network")
    holder = parse(setup_text).block("countries", "countries")
    owner: dict[str, str] = {}
    owned: Counter[str] = Counter()
    for entry in holder.entries if holder is not None else []:
        pop = entry.value.first("type") if isinstance(entry.value, Block) else None
        if entry.key is None or not isinstance(entry.value, Block) or (pop and pop.value == "pop"):
            continue
        for key in OWNING:
            locations = entry.value.block(key)
            for word in locations.words() if locations is not None else ():
                if isinstance(word.value, str) and word.value not in owner:
                    owner[word.value] = entry.key
                    owned[entry.key] += 1
    pairs: Counter[str] = Counter(
        owner[entry.key]
        for entry in (roads.entries if roads is not None else [])
        if entry.key in owner and isinstance(entry.value, str)
    )
    if not pairs:
        message = "No vanilla country owns a road"
        raise EmpireError(message)
    ratios = sorted(count * PERMILLE // owned[tag] for tag, count in pairs.items())
    return ratios[(ROAD_PERCENTILE * len(ratios) + 99) // 100 - 1]


def largest_states(
    setup_text: str,
    american: Collection[str],
    pops: Mapping[str, Sequence[tuple[str, int, str, str]]],
    cultures: Mapping[str, str],
) -> tuple[VanillaState, ...]:
    """The five vanilla American states with most locations (ties by tag), for comparison."""
    states: list[VanillaState] = []
    for tag, block in american_states(setup_text, american):
        locations = [
            word.value
            for key in OWNING
            if (held := block.block(key)) is not None
            for word in held.words()
            if isinstance(word.value, str)
        ]
        people = [
            (size, culture) for where in locations for _, size, culture, _ in pops.get(where, ())
        ]
        total = sum(size for size, _ in people)
        foreign = sum(size for size, culture in people if culture != cultures.get(tag, ""))
        states.append(
            VanillaState(tag, len(locations), foreign * PERMILLE // total if total else 0)
        )
    return tuple(sorted(states, key=lambda state: (-state.locations, state.tag))[:LARGEST])


def empire_calibration(  # noqa: PLR0913 - the calibration reads every vanilla file it names.
    *,
    levels: Mapping[str, int],
    state_levels: Sequence[int],
    setup_text: str,
    rank_texts: Sequence[str],
    roads_text: str,
    bias_texts: Sequence[str],
    american: Collection[str],
    pops: Mapping[str, Sequence[tuple[str, int, str, str]]],
    cultures: Mapping[str, str],
) -> EmpireCalibration:
    """Level ``min(T, S + 1)``, the highest American rank, the road bound and the four opinions.

    Fails if a vanilla value is missing or one of the four opinion types is not a bias.
    """
    if not state_levels:
        message = "No vanilla American state level to take S from"
        raise EmpireError(message)
    missing = sorted(set(OPINION_TYPES) - defined_biases(bias_texts))
    if missing:
        message = f"Opinion type {missing[0]} is not defined in the biases"
        raise EmpireError(message)
    return EmpireCalibration(
        level=min(highest_level(levels, setup_text), max(state_levels) + 1),
        rank=american_rank(setup_text, rank_levels(rank_texts), american),
        road_permille=road_density(setup_text, roads_text),
        opinions=OPINION_TYPES,
        largest=largest_states(setup_text, american, pops, cultures),
    )


def road_targets(  # noqa: PLR0913 - a target set reads the empire, its vassals and its locations.
    *,
    capital: int,
    vassal_capitals: Collection[int],
    members: Collection[int],
    ranked: Collection[int],
    markets: Collection[int],
    areas: Sequence[str],
    population: Sequence[int],
    keys: Sequence[str],
) -> tuple[int, ...]:
    """Locations the royal roads must reach, the capital left out.

    The capital of each vassal, each ranked location and market centre of the empire, and in
    each area the empire holds its most populous location there (ties by key).
    """
    own = set(members)
    targets = set(vassal_capitals) | (own & set(ranked)) | (own & set(markets))
    by_area: defaultdict[str, list[int]] = defaultdict(list)
    for node in sorted(own):
        by_area[areas[node]].append(node)
    targets |= {min(nodes, key=lambda n: (-population[n], keys[n])) for nodes in by_area.values()}
    return tuple(sorted(targets - {capital}))


def empire_roads(
    graph: LandGraph,
    *,
    capital: int,
    members: Collection[int],
    vassal_members: Collection[int],
    targets: Collection[int],
) -> tuple[tuple[int, int], ...]:
    """Road pairs from the capital through the empire's and its vassals' locations."""
    return trunk_roads(graph, set(members) | set(vassal_members), capital, targets)


def unlinked(
    roads: Collection[tuple[int, int]], capital: int, targets: Collection[int]
) -> tuple[int, ...]:
    """Targets that no road reaches."""
    linked = {capital} | {node for pair in roads for node in pair}
    return tuple(sorted(set(targets) - linked))


def empire_opinions(
    empire: str, neighbours: Collection[str], vassals: Collection[str]
) -> tuple[tuple[str, str, str], ...]:
    """(first, second, type) of the fear of an empire's neighbours and of its vassals' resentment.

    ``first`` holds the opinion of ``second``. A vassal is never a feared neighbour, and no
    triple repeats.
    """
    feared = sorted(set(neighbours) - set(vassals) - {empire})
    opinions = [triple for tag in feared for triple in ((tag, empire, FEAR), (empire, tag, PREY))]
    opinions += [
        triple
        for tag in sorted(set(vassals))
        for triple in ((tag, empire, TYRANT), (empire, tag, IRRITATED))
    ]
    return tuple(opinions)


def opinion_knowledge(
    opinions: Sequence[tuple[str, str, str]], capital_areas: Mapping[str, str]
) -> dict[str, frozenset[str]]:
    """The areas each holder of an opinion has to have discovered: those of its partners' capitals.

    The game warns of a scripted bias toward a country whose capital the holder has not
    discovered (``diplomacy_manager.cpp``) [V-LOCAL C170], and what it then does with the bias is
    [UNKNOWN]. Vanilla's countries never meet it: an exploration template such as ``expl_andean``
    lists every area of the region, so the Andes block of ``18_opinions`` names capitals all of
    them know [V-LOCAL]. A generated country knows its religion zone and its own areas only, so
    the opinion's holder discovers the area of the capital instead.
    """
    needed: dict[str, set[str]] = defaultdict(set)
    for first, second, _ in opinions:
        needed[first].add(capital_areas[second])
    return {tag: frozenset(areas) for tag, areas in needed.items()}


def road_lines(roads: Sequence[tuple[str, str]]) -> str:
    """Entries for ``road_network = { ... }`` of ``09_roads.txt``, each pair once, sorted by key."""
    pairs = sorted({(min(a, b), max(a, b)) for a, b in roads})
    body = "".join(f"\t{first} = {second}\n" for first, second in pairs)
    return HEADER + body if body else ""


def opinion_lines(opinions: Sequence[tuple[str, str, str]]) -> str:
    """Entries for ``diplomacy_manager = { ... }`` of ``18_opinions.txt``."""
    body = "".join(
        f"\topinion = {{ first = {first} second = {second} type = {kind} }}\n"
        for first, second, kind in opinions
    )
    return HEADER + body if body else ""


def written_ranks(text: str, tags: Collection[str]) -> dict[str, list[str]]:
    """Written ``country_rank`` values of the country records of ``tags``."""
    holder = parse(text).block("countries", "countries")
    return {
        entry.key: [
            rank.value for rank in entry.value.find("country_rank") if isinstance(rank.value, str)
        ]
        for entry in (holder.entries if holder is not None else [])
        if entry.key is not None and entry.key in tags and isinstance(entry.value, Block)
    }


def written_discoveries(text: str, tags: Collection[str]) -> dict[str, tuple[str, frozenset[str]]]:
    """Written ``capital`` and ``discovered_areas`` of the country records of ``tags``."""
    holder = parse(text).block("countries", "countries")
    found: dict[str, tuple[str, frozenset[str]]] = {}
    for entry in holder.entries if holder is not None else []:
        if entry.key is None or entry.key not in tags or not isinstance(entry.value, Block):
            continue
        capital = entry.value.first("capital")
        areas = entry.value.block("discovered_areas")
        found[entry.key] = (
            capital.value if capital is not None and isinstance(capital.value, str) else "",
            frozenset(
                word.value
                for word in (areas.words() if areas is not None else ())
                if isinstance(word.value, str)
            ),
        )
    return found


def median(values: Sequence[int]) -> int:
    """The upper median of a non-empty sequence, 0 for an empty one."""
    return sorted(values)[len(values) // 2] if values else 0


def share(part: int, whole: int) -> int:
    """Permille of ``whole`` that ``part`` is."""
    return part * PERMILLE // whole if whole else 0


def travel_steps(
    graph: LandGraph, allowed: Collection[int], capital: int, nodes: Collection[int]
) -> list[int]:
    """Travel cost, in whole steps, from the capital to each of ``nodes`` it can reach."""
    cost, _ = land_routes(graph, allowed, capital)
    return [
        (int(cost[node]) + STEP_COST // 2) // STEP_COST for node in sorted(nodes) if cost[node] >= 0
    ]


def extraordinary_report(
    calibration: EmpireCalibration, empires: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    """The ``extraordinary`` section of ``report.json``."""
    return {
        "calibration": {
            "level": calibration.level,
            "rank": calibration.rank,
            "opinion_types": list(calibration.opinions),
            "road_bound_permille": calibration.road_permille,
        },
        "empires": [dict(empire) for empire in empires],
        "vanilla_largest_states": [
            {
                "tag": state.tag,
                "locations": state.locations,
                "foreign_culture_permille": state.foreign_culture_permille,
            }
            for state in calibration.largest
        ],
    }
