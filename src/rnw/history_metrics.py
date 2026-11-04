"""Predeclared, read-only H7 measurements; never influence construction or repair output.

Conflict and ownership statistics use the fixed LAND polity envelope. Tribal and
community founding counts are reported separately. Physical landmasses include
wasteland and seam edges, never a maritime route between separate landmasses.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rnw.history_archive import build, pack
from rnw.history_context import Context
from rnw.history_model import END, Action, HistoryError, Outcome, Tenure, TrajectoryKind
from rnw.history_text import chronicles
from rnw.history_trajectories import realizations
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
    )
