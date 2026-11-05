"""Predeclared, read-only acceptance measurements; never influence construction or output.

Conflict and ownership statistics use the fixed LAND polity envelope. Tribal and
community founding counts are reported separately. Physical landmasses include
wasteland and seam edges, never a maritime route between separate landmasses.
The structural counters (plan §18, D28) describe the 1337 start the player sees:
region classes, aims and their outcomes, subjects, institutions and chronicles.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.history_archive import build, pack
from rnw.history_context import Context
from rnw.history_model import (
    END,
    EXPANSION,
    PERMILLE,
    Action,
    HistoryError,
    Outcome,
    Tenure,
    TrajectoryKind,
)
from rnw.history_text import chronicles
from rnw.history_trajectories import (
    blocs,
    political_regions,
    realizations,
    region_districts,
)
from rnw.model import CellClass

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.eu5_start import Country, FinalStartPlan
    from rnw.newworld import NewWorld


@dataclass(frozen=True, slots=True)
class Dominance:
    landmass: int
    founding_states: int
    founding_tribes: int
    state_locations: int
    largest_bloc: int
    projected_locations: int
    largest_projected_bloc: int


# Region classes in classifier precedence order (plan §18).
GREAT: Final[str] = "great_realm"
PARAMOUNT: Final[str] = "paramount"
LEAGUE: Final[str] = "league"
RIVALS: Final[str] = "rival_powers"
FRACTURED: Final[str] = "fractured"
PATCHWORK: Final[str] = "patchwork"
CLASSES: Final[tuple[str, ...]] = (GREAT, PARAMOUNT, LEAGUE, RIVALS, FRACTURED, PATCHWORK)
RECENT_YEARS: Final[int] = 100
TURMOIL: Final[frozenset[Action]] = frozenset(
    {Action.CONFLICT, Action.SECESSION, Action.SEPARATION}
)


@dataclass(frozen=True, slots=True)
class RegionClass:
    region: str
    polities: int
    kind: str
    largest: int
    second: int
    state_locations: int


@dataclass(frozen=True, slots=True)
class AimOutcome:
    kind: TrajectoryKind
    strategy: str
    realized: bool
    peak: int
    final: int
    successors: bool


@dataclass(frozen=True, slots=True)
class Structure:
    """What the 1337 map looks like, independently of the record's event counts."""

    regions: tuple[RegionClass, ...]
    state_locations: int
    changed_locations: int
    recent_locations: int
    aims: tuple[AimOutcome, ...]
    subjects: int
    scaled_subjects: int
    alliances: int
    states: int
    republics: int
    government_types: int
    assortativity: int
    chronicle_families: tuple[tuple[str, int], ...]
    chronicle_distinct: tuple[int, ...]
    great_blocs: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Observation:
    bootstrap_states: int
    bootstrap_tribes: int
    bootstrap_communities: int
    conflicts: int
    ownership_events: int
    ownership_locations: int
    separations: int
    landed_countries: int
    continuous_countries: int
    projected_relationship_countries: int
    treaty_countries: int
    chronicle_lengths: tuple[int, ...]
    ordinary_sizes: tuple[int, ...]
    government_combinations: int
    great_seeded: int
    great_realized: int
    domination: tuple[Dominance, ...]
    archive_bytes: int
    digest: str
    structure: Structure | None = None


def landmasses(world: NewWorld, keys: Sequence[str]) -> dict[str, int]:
    """Connected dry physical cells, including impassable land and true wrap contacts."""
    if len(keys) != len(world.classes):
        message = "Metric geography columns differ"
        raise HistoryError(message)
    dry = {
        i for i, kind in enumerate(world.classes) if kind in {CellClass.LAND, CellClass.WASTELAND}
    }
    parents = list(range(len(keys)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for first, second in world.edges:
        if first in dry and second in dry:
            one, other = root(first), root(second)
            parents[max(one, other)] = min(one, other)
    return {keys[i]: root(i) for i in sorted(dry)}


def government_combinations(
    countries: Sequence[Country],
    inherited: Mapping[str, tuple[tuple[str, str], ...]],
    positions: Sequence[str],
) -> int:
    """Effective government type and installed ungated positions, including template defaults."""
    signatures: set[tuple[tuple[str, str], ...]] = set()
    for country in countries:
        if country.kind != "state" and not country.landed:
            continue
        fields = dict(inherited.get(country.include, ()))
        fields.update(country.government)
        if "type" not in fields:
            message = "Cannot measure a missing projected government"
            raise HistoryError(message)
        signatures.add(
            tuple((key, fields[key]) for key in ("type", *sorted(positions)) if key in fields)
        )
    return len(signatures)


def _dominance(start: FinalStartPlan, masses: Mapping[str, int]) -> tuple[Dominance, ...]:
    history = start.history
    if history is None:
        message = "Cannot measure invented history"
        raise HistoryError(message)
    lords = {
        bond.first: bond.second for bond in history.state.bonds if bond.kind is Action.DEPENDENCY
    }

    def root(actor: str) -> str:
        seen: set[str] = set()
        while actor in lords:
            if actor in seen:
                message = "Metric dependency cycle"
                raise HistoryError(message)
            seen.add(actor)
            actor = lords[actor]
        return actor

    states: dict[int, set[str]] = defaultdict(set)
    tribes: dict[int, set[str]] = defaultdict(set)
    for founding in history.foundings:
        if founding.tenure is Tenure.COMMUNITY:
            continue
        target = states if founding.tenure is Tenure.LAND else tribes
        for key in founding.districts:
            target[masses[key]].add(founding.key)
    envelope = {place.key for place in history.geography.districts if place.tenure is Tenure.LAND}
    projected = {key for c in start.countries if c.kind == "state" or c.landed for key in c.members}
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    owned: dict[int, Counter[str]] = defaultdict(Counter)
    for holding in history.state.holdings:
        mass, bloc = masses[holding.district], root(holding.actor)
        if holding.district in envelope:
            counts[mass][bloc] += 1
        if holding.district in projected:
            owned[mass][bloc] += 1
    return tuple(
        Dominance(
            mass,
            len(states[mass]),
            len(tribes[mass]),
            sum(counts[mass].values()),
            max(counts[mass].values(), default=0),
            sum(owned[mass].values()),
            max(owned[mass].values(), default=0),
        )
        for mass in sorted(states.keys() | tribes.keys())
    )


def measure(
    start: FinalStartPlan,
    *,
    keys: Sequence[str],
    masses: Mapping[str, int],
    inherited: Mapping[str, tuple[tuple[str, str], ...]],
    positions: Sequence[str],
) -> Observation:
    """Raw counters for S1-S7/S11; no selection of a best seed or threshold adjustment."""
    history = start.history
    if history is None or history.state.year != END:
        message = "Metrics require a completed real history"
        raise HistoryError(message)
    landed = {c.tag: c for c in start.countries if c.kind == "state" or c.landed}
    actors = {actor.key: actor for actor in history.state.actors}
    treaty = {
        tag
        for pairs in (start.vassals, start.alliances, start.rivals, start.protections)
        for pair in pairs
        for tag in pair
    }
    linked = treaty | {
        tag for opinion in start.historical_opinions for tag in (opinion.first, opinion.second)
    }
    written = chronicles(start)
    actual = [event for event in history.events if event.outcome is not Outcome.REFUSED]
    changes = [
        event for event in actual if event.kind is not Action.FOUNDATION and event.effects.transfers
    ]
    great_realized = sum(
        item.kind is TrajectoryKind.GREAT_EMPIRE
        for item in realizations(Context(history, lambda: None))
    )
    archive = build(start, keys)
    # Count the entire JSON wrapper, not only the compressed binary data.
    size = len(
        json.dumps(pack(archive), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    )
    return Observation(
        sum(f.tenure is Tenure.LAND for f in history.foundings),
        sum(f.tenure is Tenure.TRIBE for f in history.foundings),
        sum(f.tenure is Tenure.COMMUNITY for f in history.foundings),
        sum(e.kind is Action.CONFLICT for e in actual),
        len(changes),
        sum(len(e.effects.transfers) for e in changes),
        sum(e.kind is Action.SEPARATION and e.outcome is Outcome.ACCEPTED for e in actual),
        len(landed),
        sum(actors[c.history_actor].born <= END - 100 for c in landed.values()),
        len(linked & landed.keys()),
        len(treaty & landed.keys()),
        tuple(len(written[tag].rows) for tag in sorted(landed)),
        tuple(sorted(len(c.members) for c in start.countries if c.kind == "state" and not c.great)),
        government_combinations(start.countries, inherited, positions),
        sum(t.kind is TrajectoryKind.GREAT_EMPIRE for t in history.state.trajectories),
        great_realized,
        _dominance(start, masses),
        size,
        archive.digest,
        structure(start, inherited=inherited),
    )


def _classify(  # noqa: PLR0913 - one region against the shared 1337 facts
    context: Context,
    region: str,
    polities: int,
    *,
    held: dict[str, frozenset[str]],
    great: list[frozenset[str]],
    groups: list[frozenset[str]],
    successors: list[tuple[frozenset[str], ...]],
) -> RegionClass:
    envelope = region_districts(context, region)
    organized = frozenset(
        place.key
        for place in context.history.geography.districts
        if place.region == region and place.tenure is not Tenure.COMMUNITY
    )
    shares = sorted((len(realm & envelope) for realm in held.values()), reverse=True)
    largest, second = [*shares, 0, 0][:2]
    total = len(envelope)

    def at_least(count: int, permille: int, of: int) -> bool:
        return of > 0 and count * PERMILLE >= of * permille

    kind = PATCHWORK
    if any(at_least(len(realm & envelope), 500, total) for realm in great):
        kind = GREAT
    elif at_least(largest, 400, total) and largest >= 2 * second:
        kind = PARAMOUNT
    elif any(at_least(len(group & organized), 300, len(organized)) for group in groups):
        kind = LEAGUE
    elif sum(at_least(value, 150, total) for value in shares) >= 2:  # noqa: PLR2004
        kind = RIVALS
    elif any(
        len(lineage) >= 2 and at_least(len(frozenset[str]().union(*lineage) & envelope), 300, total)  # noqa: PLR2004
        for lineage in successors
    ):
        kind = FRACTURED
    return RegionClass(region, polities, kind, largest, second, total)


def _aim_outcomes(
    context: Context, found: set[tuple[TrajectoryKind, str]]
) -> tuple[AimOutcome, ...]:
    """Peak and final holdings of each seeded aim's holder, replayed from transfers."""
    history = context.history
    owner = {key: founding.key for founding in history.foundings for key in founding.districts}
    counts: Counter[str] = Counter(owner.values())
    aims = list(history.state.trajectories)
    peaks = dict.fromkeys(range(len(aims)), 0)
    broken = dict.fromkeys(range(len(aims)), False)

    def holder(number: int) -> str:
        key = owner.get(aims[number].anchor, "")
        return key if key and context.ancestry(key) & set(aims[number].members) else ""

    def measure_round() -> None:
        for number in range(len(aims)):
            key = holder(number)
            if key:
                peaks[number] = max(peaks[number], counts[key])

    divisions = [
        event
        for event in history.events
        if event.outcome is Outcome.ACCEPTED and event.kind in {Action.SEPARATION, Action.SECESSION}
    ]
    for number, item in enumerate(aims):
        broken[number] = any(
            context.ancestry(key) & set(item.members) for event in divisions for key in event.actors
        )
    year = -1
    for event in history.events:
        if event.year != year:
            measure_round()
            year = event.year
        if event.kind is Action.FOUNDATION:
            continue
        for transfer in event.effects.transfers:
            counts[owner[transfer.district]] -= 1
            owner[transfer.district] = transfer.after
            counts[transfer.after] += 1
    measure_round()
    result: list[AimOutcome] = []
    for number, item in enumerate(aims):
        key = holder(number)
        realized = (item.kind, key if item.expansion else item.hearth) in found
        result.append(
            AimOutcome(
                item.kind,
                item.strategy.value,
                realized,
                peaks[number],
                counts[key] if key else 0,
                broken[number],
            )
        )
    return tuple(result)


def _assortativity(context: Context, states: Mapping[str, str]) -> int:
    """Newman's categorical assortativity of authority over land-bordering states.

    ``states`` maps each living landed actor to its group; only pairs within one
    group count (one constant group counts every bordering pair).
    """
    authority = {key: context.index.actors[key].authority for key in states}
    pairs: Counter[tuple[str, str]] = Counter()
    for route in context.history.geography.routes:
        if route.sea_steps:
            continue
        first = context.index.owner.get(route.first, "")
        second = context.index.owner.get(route.second, "")
        if (
            first in states
            and second in states
            and first != second
            and states[first] == states[second]
        ):
            pairs[authority[first].value, authority[second].value] += 1
            pairs[authority[second].value, authority[first].value] += 1
    total = sum(pairs.values())
    if not total:
        return 0
    kinds = {kind for pair in pairs for kind in pair}
    diagonal = sum(pairs[kind, kind] for kind in kinds) / total
    margins = {kind: sum(pairs[kind, other] for other in kinds) / total for kind in kinds}
    expected = sum(value * value for value in margins.values())
    return 0 if expected >= 1 else round(PERMILLE * (diagonal - expected) / (1 - expected))


def structure(
    start: FinalStartPlan, *, inherited: Mapping[str, tuple[tuple[str, str], ...]]
) -> Structure:
    """The map-level counters of plan §18 for one completed start."""
    history = start.history
    if history is None or history.state.year != END:
        message = "Structure requires a completed real history"
        raise HistoryError(message)
    context = Context(history, lambda: None)
    held = blocs(context)
    found = realizations(context)
    great = [
        held.get(item.members[0], frozenset())
        for item in found
        if item.kind is TrajectoryKind.GREAT_EMPIRE
    ]
    groups = [
        frozenset(place for key in item.members for place in context.index.members[key])
        for item in found
        if item.kind in {TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION}
    ]
    living = {actor.key for actor in history.state.actors if actor.living}
    successors: list[tuple[frozenset[str], ...]] = []
    for event in history.events:
        if event.outcome is not Outcome.ACCEPTED or event.kind not in {
            Action.SEPARATION,
            Action.SECESSION,
        }:
            continue
        roots = {actor.key for actor in event.effects.created}
        if event.kind is Action.SECESSION:
            roots.update(event.actors)
        lineage = tuple(
            frozenset(context.index.members[key])
            for key in sorted(living)
            if context.index.actors[key].tenure is Tenure.LAND and context.ancestry(key) & roots
        )
        successors.append(lineage)
    regions = tuple(
        _classify(
            context,
            region,
            len(polities),
            held=held,
            great=great,
            groups=groups,
            successors=successors,
        )
        for region, polities in political_regions(context).items()
    )
    land = {place.key for place in history.geography.districts if place.tenure is Tenure.LAND}
    # Land that left its founder's lineage: conquest or breakaway, not a union's
    # or division's inheritance.
    changed = sum(
        context.founders[key] not in context.ancestry(context.index.owner[key])
        for key in sorted(land)
    )
    # Recent turmoil: land whose holder took it by conquest, breakaway or division
    # in the last RECENT_YEARS of the record.
    recent = sum(
        context.event_years[context.holdings[key].cause] >= END - RECENT_YEARS
        and context.event_kinds[context.holdings[key].cause] in TURMOIL
        for key in sorted(land)
    )
    outcomes = _aim_outcomes(
        context,
        {(item.kind, item.members[0] if item.kind in EXPANSION else item.hearth) for item in found},
    )
    size = {country.tag: len(country.members) for country in start.countries}
    kinds = {country.tag: country.kind for country in start.countries}
    scaled = sum(
        size.get(lord, 0) >= 2 * size.get(subject, 0)
        for lord, subject in start.vassals
        if kinds.get(subject) == "state"
    )
    states = [country for country in start.countries if country.kind == "state"]
    types: Counter[str] = Counter()
    for country in states:
        fields = dict(inherited.get(country.include, ()))
        fields.update(country.government)
        types[fields.get("type", "")] += 1
    rows = chronicles(start)
    families: Counter[str] = Counter(
        row.family.value for chronicle in rows.values() for row in chronicle.rows
    )
    return Structure(
        regions,
        len(land),
        changed,
        recent,
        outcomes,
        len(start.vassals),
        scaled,
        len(start.alliances),
        len(states),
        types.get("republic", 0),
        len(types),
        _assortativity(
            context,
            {country.history_actor: "" for country in states if country.history_actor in living},
        ),
        tuple(sorted(families.items())),
        tuple(
            len({row.family for row in chronicle.rows})
            for chronicle in rows.values()
            if len(chronicle.rows) >= 5  # noqa: PLR2004 - Q12's long chronicle
        ),
        tuple(sorted(len(realm) for realm in great)),
    )
